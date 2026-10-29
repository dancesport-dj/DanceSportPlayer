#!/usr/bin/env python3
"""Deep-audio embeddings: the store, the two backends, the index build, ranking.

Run:  py -m unittest tests.planner.music.test_embeddings -v

`planner.music.embeddings` caches one vector per (content fingerprint, model) in the
shared DB, computes it with MERT or the librosa chroma descriptor, builds an
index over a pool (deduplicated, cancelable, too-short clips skipped) and ranks
a pool by cosine to a source. The DB is an in-memory SQLite connection, and
transformers / librosa are fakes in `sys.modules`; numpy is the real one.
"""
import contextlib
import importlib.util
import io
import logging
import sqlite3
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from planner.music import embeddings as ae

_M = ae.MODEL_MERT


def _entry(name, dance="CC", is_xmas=False):
    return SimpleNamespace(path=Path(f"/music/{name}.mp3"), dance=dance, is_xmas=is_xmas)


class _Store:
    """The slice of EmbeddingStore that build_index and the ranking use."""

    def __init__(self, fps=None, vecs=None):
        self.fp_of = dict(fps or {})
        self.vecs = dict(vecs or {})
        self.saves = 0

    def fingerprint(self, path):
        return self.fp_of.get(path.stem)

    def has(self, fp, model):
        return (fp, model) in self.vecs

    def fps(self, model):
        return {fp for fp, m in self.vecs if m == model}

    def get_by_fp(self, fp, model):
        return self.vecs.get((fp, model)) if fp else None

    def put(self, fp, model, vec):
        self.vecs[(fp, model)] = list(vec)

    def save(self):
        self.saves += 1


class _Backend:
    """embed_file answers from `vectors`; an exception instance is raised."""

    def __init__(self, vectors):
        self.vectors = vectors
        self.calls = []
        self.fetches = []
        self.fetch_error = None

    def fetch(self, cb=None):
        """Records the listener and how many titles were embedded before."""
        self.fetches.append((cb, len(self.calls)))
        if self.fetch_error:
            raise self.fetch_error

    def embed_file(self, path):
        self.calls.append(path.stem)
        out = self.vectors[path.stem]
        if isinstance(out, Exception):
            raise out
        return out


class _Base(unittest.TestCase):

    def patch(self, target, name, **kw):
        patcher = mock.patch.object(target, name, **kw)
        found = patcher.start()
        self.addCleanup(patcher.stop)
        return found

    def modules(self, **mods):
        patcher = mock.patch.dict(sys.modules, mods)
        patcher.start()
        self.addCleanup(patcher.stop)

    def backend(self, vectors):
        backend = _Backend(vectors)
        self.patch(ae, "get_backend", return_value=backend)
        return backend


class SystemCertsTest(_Base):

    def setUp(self):
        self.patch(ae, "_certs_injected", new=False)

    def test_truststore_is_injected_once(self):
        truststore = mock.Mock()
        self.modules(truststore=truststore)
        with self.assertLogs(ae.logger, "INFO") as logs:
            ae._enable_system_certs()
        ae._enable_system_certs()
        truststore.inject_into_ssl.assert_called_once()
        self.assertIn("OS certificate store", logs.output[0])

    def test_without_truststore_the_default_bundle_stays(self):
        self.modules(truststore=None)
        with self.assertLogs(ae.logger, "DEBUG") as logs:
            ae._enable_system_certs()
        self.assertTrue(ae._certs_injected)
        self.assertIn("truststore not active", logs.output[0])


class AvailabilityTest(_Base):

    def test_install_hints(self):
        self.assertIn("pip install librosa", ae.install_hint(ae.MODEL_CHROMA))
        self.assertIn("pip install torch transformers", ae.install_hint(_M))

    def test_the_probes_look_for_the_packages_without_importing(self):
        found = {"librosa", "torch"}
        self.patch(ae.importlib.util, "find_spec", side_effect=lambda name: name in found)
        self.assertTrue(ae.chroma_available())
        self.assertFalse(ae.mert_available())   # transformers is missing
        found.add("transformers")
        self.assertTrue(ae.mert_available())

    def test_each_model_has_its_backend(self):
        self.assertIs(ae.get_backend(ae.MODEL_CHROMA), ae._chroma)
        self.assertIs(ae.get_backend(_M), ae._mert)


class EmbeddingStoreTest(_Base):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.addCleanup(self.conn.close)
        self.patch(ae, "_db", return_value=self.conn)
        self.cache = mock.Mock()
        self.cache.fingerprint.side_effect = lambda p: {"a": "fa", "b": "fb"}.get(p.stem)
        self.cache.recorded_fingerprint.side_effect = lambda p: {"a": "fa"}.get(p.stem)

    def test_a_vector_is_found_by_path_fingerprint_or_record(self):
        store = ae.EmbeddingStore(self.cache)
        store.put("fa", _M, (0.5, 0.25))
        store.save()
        a, nowhere = Path("/m/a.mp3"), Path("/m/zz.mp3")
        self.assertEqual(store.fingerprint(a), "fa")
        self.assertEqual(store.get(a, _M), [0.5, 0.25])
        self.assertIsNone(store.get(nowhere, _M))
        self.assertIsNone(store.get(Path("/m/b.mp3"), _M))
        self.assertEqual(store.get_by_fp("fa", _M), [0.5, 0.25])
        self.assertIsNone(store.get_by_fp(None, _M))
        self.assertEqual(store.recorded(a, _M), [0.5, 0.25])
        self.assertTrue(store.has("fa", _M))
        self.assertFalse(store.has("fa", ae.MODEL_CHROMA))
        self.assertEqual(store.count(_M), 1)
        self.assertEqual(store.fps(_M), {"fa"})

    def test_a_fresh_store_reads_what_was_saved(self):
        first = ae.EmbeddingStore(self.cache)
        first.put("fa", _M, [1.0])
        first.put("fb", _M, [2.0])
        first.put("fb", ae.MODEL_CHROMA, [3.0])
        first.save()
        again = ae.EmbeddingStore(self.cache)
        self.assertEqual(again.fps(_M), {"fa", "fb"})   # keys alone, no mirror yet
        self.assertNotIn(_M, again._mirror)
        self.assertEqual(again.count(ae.MODEL_CHROMA), 1)
        self.assertEqual(again.get_by_fp("fb", _M), [2.0])


@unittest.skipUnless(importlib.util.find_spec("torch"), "MERT runs on torch")
class MertBackendTest(_Base):
    """The model is a fake `transformers`; torch is the real one, as the
    layer arithmetic is torch's."""

    def setUp(self):
        import torch
        self.torch = torch
        self.librosa = mock.Mock()
        self.librosa.load.return_value = (np.zeros(ae._MERT_SR * 2), ae._MERT_SR)
        self.model = mock.Mock()
        self.model.eval.return_value = self.model
        self.proc = mock.Mock(return_value={"input_values": "wave"})
        self.transformers = mock.Mock()
        self.transformers.AutoModel.from_pretrained.return_value = self.model
        self.transformers.Wav2Vec2FeatureExtractor.from_pretrained.return_value = self.proc
        self.modules(transformers=self.transformers, librosa=self.librosa)
        self.patch(ae, "quiet_native_stderr", new=contextlib.nullcontext)
        self.certs = self.patch(ae, "_enable_system_certs")
        self.quiet = self.patch(ae, "_quiet_model_chatter")

    def layers(self, *frames):
        """hidden_states as MERT returns them: (1, frames, dims) per layer."""
        self.model.return_value = SimpleNamespace(hidden_states=tuple(
            self.torch.tensor([f], dtype=self.torch.float32) for f in frames))

    def test_the_layers_are_averaged_normalised_and_the_model_loaded_once(self):
        # Layer 0, the convolutional front end, is left out: [99, 99] would
        # pull the vector off the 3:4 direction of the two music layers.
        self.layers([[99.0, 99.0]], [[3.0, 0.0], [3.0, 0.0]], [[3.0, 8.0], [3.0, 8.0]])
        backend = ae._MertBackend()
        backend.embed_file(Path("/m/a.mp3"))
        np.testing.assert_allclose(backend.embed_file(Path("/m/b.mp3")), [0.6, 0.8])
        self.transformers.AutoModel.from_pretrained.assert_called_once_with(
            ae._MERT_REPO, revision=ae._MERT_REVISION, trust_remote_code=True)
        self.model.assert_called_with(input_values="wave", output_hidden_states=True)
        self.certs.assert_called_once()
        self.assertEqual(self.librosa.load.call_args.kwargs,
                         {"sr": ae._MERT_SR, "mono": True, "offset": 0.0,
                          "duration": ae._MERT_SECONDS})
        self.assertEqual(self.proc.call_args.kwargs["sampling_rate"], ae._MERT_SR)

    def test_the_model_load_keeps_the_log_and_the_console_quiet(self):
        """The model's own code prints its nnAudio hint, transformers draws
        a "Loading weights" bar: neither belongs in the app's console."""
        def load(*args, **kwargs):
            print("WARNING: feature_extractor_cqt requires the libray 'nnAudio'")
            return self.model
        self.transformers.AutoModel.from_pretrained.side_effect = load
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ae._MertBackend()._ensure_model()
        self.assertEqual(out.getvalue(), "")
        self.quiet.assert_called_once()
        self.transformers.utils.logging.disable_progress_bar.assert_called_once()

    def test_the_remote_code_is_pinned(self):
        """trust_remote_code runs the repo's own Python — never a version
        nobody has looked at."""
        self.assertRegex(ae._MERT_REVISION, r"^[0-9a-f]{40}$")

    def test_a_silent_track_keeps_its_zero_vector(self):
        self.layers([[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]])
        self.assertEqual(ae._MertBackend().embed_file(Path("/m/a.mp3")), [0.0, 0.0, 0.0])

    def test_a_clip_under_a_second_is_skipped_not_failed(self):
        self.librosa.load.return_value = (np.zeros(100), ae._MERT_SR)
        with self.assertRaises(ae.AudioTooShort):
            ae._MertBackend().embed_file(Path("/m/swish.mp3"))
        self.transformers.AutoModel.from_pretrained.assert_not_called()


@unittest.skipUnless(importlib.util.find_spec("tqdm"), "the download bar is tqdm's")
class MertFetchTest(_Base):
    """Marcel: "for mert if it analyze and needs to download show it in the
    progress dialog so he user can note if download happens or analysis".
    The model's files come down before the first title, one by one, their
    bytes reported. `huggingface_hub` is a fake, tqdm the real one."""

    SIZES = {"pytorch_model.bin": 3000}

    def setUp(self):
        self.cached = set()
        self.hub = mock.Mock()
        self.hub.try_to_load_from_cache.side_effect = (
            lambda repo, name, revision: f"/hub/{name}" if name in self.cached else None)
        self.hub.hf_hub_download.side_effect = self.download
        self.modules(huggingface_hub=self.hub)
        self.certs = self.patch(ae, "_enable_system_certs")
        self.patch(ae, "_quiet_model_chatter")
        self.got = []

    def download(self, repo, name, revision, tqdm_class):
        """As huggingface_hub does: a bar per file, the bytes as they land,
        and on Xet its network bytes besides, ahead of those on disk."""
        size = self.SIZES.get(name, 10)
        with tqdm_class(total=size, initial=0, desc=name, unit="B", unit_scale=True) as bar:
            bar.update_transfer(size // 3)
            bar.update(size // 2)
            bar.set_postfix_str("1 MB/s", refresh=False)
            bar.set_transfer_postfix_str("1 MB/s", refresh=False)
            bar.update(size - size // 2)
            bar.update_transfer(size)       # more on the wire than on disk
        return f"/hub/{name}"

    def test_only_the_missing_files_come_down_with_their_bytes(self):
        self.cached = {"config.json"}
        ae._MertBackend().fetch(lambda done, total: self.got.append((done, total)))
        calls = self.hub.hf_hub_download.call_args_list
        self.assertEqual([c.args for c in calls],
                         [(ae._MERT_REPO, n) for n in ("configuration_MERT.py", "modeling_MERT.py",
                                                       "preprocessor_config.json",
                                                       "pytorch_model.bin")])
        self.assertEqual({c.kwargs["revision"] for c in calls}, {ae._MERT_REVISION})
        self.assertIn((30, 3030), self.got)        # the weights' size, before a byte
        self.assertIn((1030, 3030), self.got)      # on the wire, not yet on disk
        self.assertIn((1530, 3030), self.got)      # half the weights
        self.assertEqual(self.got[-1], (3030, 3030))
        self.assertTrue(all(done <= total for done, total in self.got))
        self.certs.assert_called_once()

    def test_a_cached_model_downloads_nothing(self):
        self.cached = set(ae._MERT_FILES)
        ae._MertBackend().fetch(self.got.append)
        self.hub.hf_hub_download.assert_not_called()
        self.assertEqual(self.got, [])
        self.certs.assert_not_called()

    def test_without_a_listener_it_still_downloads(self):
        ae._MertBackend().fetch()
        self.assertEqual(self.hub.hf_hub_download.call_count, len(ae._MERT_FILES))


class QuietChatterTest(unittest.TestCase):
    """Marcel's log carried every HEAD request to the hub, the hub's hint to
    log in and transformers' deprecation notes."""

    def setUp(self):
        for name in ("httpx", "huggingface_hub", "transformers"):
            log = logging.getLogger(name)
            self.addCleanup(log.setLevel, log.level)
        self.addCleanup(logging.getLogger("httpx").removeFilter, ae._HUB_REQUESTS)

    def test_the_hubs_requests_leave_the_log_and_others_stay(self):
        ae._quiet_model_chatter()
        httpx = logging.getLogger("httpx")
        line = 'HTTP Request: %s %s "%s %d %s"'
        with self.assertLogs(httpx, "INFO") as logs:
            httpx.info(line, "HEAD", "https://huggingface.co/m-a-p/MERT-v1-95M/resolve/"
                       "12af/model.safetensors", "HTTP/1.1", 404, "Not Found")
            httpx.info(line, "POST", "https://api.anthropic.com/v1/messages",
                       "HTTP/1.1", 200, "OK")
        self.assertEqual(len(logs.output), 1)
        self.assertIn("api.anthropic.com", logs.output[0])

    def test_the_hub_and_transformers_keep_only_their_errors(self):
        ae._quiet_model_chatter()
        for name in ("huggingface_hub.utils._http", "transformers.configuration_utils"):
            log = logging.getLogger(name)
            self.assertFalse(log.isEnabledFor(logging.WARNING), name)
            self.assertTrue(log.isEnabledFor(logging.ERROR), name)


class ChromaBackendTest(_Base):

    def setUp(self):
        self.librosa = mock.Mock()
        self.librosa.load.return_value = (np.zeros(2 * ae._CHROMA_SR), ae._CHROMA_SR)
        self.modules(librosa=self.librosa)
        self.patch(ae, "quiet_native_stderr", new=contextlib.nullcontext)

    def test_there_is_no_model_to_fetch(self):
        cb = mock.Mock()
        ae._ChromaBackend().fetch(cb)
        cb.assert_not_called()

    def test_clips_too_short_are_a_skip(self):
        backend = ae._ChromaBackend()
        self.librosa.load.return_value = (np.zeros(100), ae._CHROMA_SR)
        with self.assertRaisesRegex(ae.AudioTooShort, "audio too short"):
            backend.embed_file(Path("/m/a.mp3"))
        self.librosa.load.return_value = (np.zeros(2 * ae._CHROMA_SR), ae._CHROMA_SR)
        self.librosa.feature.chroma_cens.return_value = np.ones((12, 7))
        with self.assertRaisesRegex(ae.AudioTooShort, "chromagram too short"):
            backend.embed_file(Path("/m/a.mp3"))

    def test_the_descriptor_is_unit_length_and_key_invariant(self):
        rng = np.random.default_rng(7)
        chroma = rng.random((12, 50))
        self.librosa.feature.chroma_cens.return_value = chroma
        vec = ae._ChromaBackend().embed_file(Path("/m/a.mp3"))
        self.assertEqual(len(vec), 12 * ae._CHROMA_KEEP_FREQ)
        self.assertAlmostEqual(float(np.linalg.norm(vec)), 1.0)
        self.librosa.feature.chroma_cens.return_value = np.roll(chroma, 3, axis=0)
        shifted = ae._ChromaBackend().embed_file(Path("/m/a.mp3"))
        np.testing.assert_allclose(shifted, vec, atol=1e-9)

    def test_a_flat_chromagram_keeps_its_zero_vector(self):
        self.librosa.feature.chroma_cens.return_value = np.zeros((12, 20))
        vec = ae._ChromaBackend().embed_file(Path("/m/a.mp3"))
        self.assertEqual(set(vec), {0.0})


class BuildIndexTest(_Base):

    def test_one_embedding_per_unique_audio_not_yet_indexed(self):
        store = _Store(fps={"a": "fa", "a_copy": "fa", "b": "fb", "old": "fo"},
                       vecs={("fo", _M): [1.0]})
        backend = self.backend({"a": [0.1], "b": [0.2]})
        entries = [_entry(n) for n in ("a", "a_copy", "b", "old", "unknown")]
        progress = []
        result = ae.build_index(entries, _M, store,
                                progress_cb=lambda *a: progress.append(a))
        self.assertEqual(result, (2, 0, None))
        self.assertEqual(backend.calls, ["a", "b"])
        self.assertEqual(store.vecs[("fb", _M)], [0.2])
        self.assertEqual(progress, [(1, 2, "a.mp3"), (2, 2, "b.mp3")])
        self.assertEqual(store.saves, 1)

    def test_failures_are_counted_and_the_first_one_kept(self):
        store = _Store(fps={n: f"f{n}" for n in ("short", "bad1", "bad2", "ok")})
        self.backend({"short": ae.AudioTooShort("2 s jingle"), "bad1": RuntimeError("no model"),
                      "bad2": OSError("locked"), "ok": [0.3]})
        entries = [_entry(n) for n in ("short", "bad1", "bad2", "ok")]
        with self.assertLogs(ae.logger, "INFO") as logs:
            result = ae.build_index(entries, _M, store)
        self.assertEqual(result, (1, 2, "RuntimeError: no model"))
        text = "\n".join(logs.output)
        self.assertIn("Too short to embed", text)
        self.assertIn("Embedding failed", text)
        self.assertIn("Skipped (mert): bad2.mp3\nOSError: locked", text)
        self.assertIn("too short to embed: 1", text)

    def test_long_runs_save_every_50_and_report_every_10(self):
        names = [f"t{i:03d}" for i in range(55)]
        store = _Store(fps={n: n for n in names})
        self.backend(dict.fromkeys(names, [0.5]))
        progress = []
        ae.build_index([_entry(n) for n in names], _M, store,
                       progress_cb=lambda i, total, name: progress.append(i))
        self.assertEqual(progress, [1, 10, 20, 30, 40, 50, 55])
        self.assertEqual(store.saves, 2)

    def test_a_cancel_stops_before_the_next_track(self):
        store = _Store(fps={"a": "fa", "b": "fb"})
        backend = self.backend({"a": [0.1], "b": [0.2]})
        asked = iter([False, True])
        self.assertEqual(ae.build_index([_entry("a"), _entry("b")], _M, store,
                                        should_cancel=lambda: next(asked)), (1, 0, None))
        self.assertEqual(backend.calls, ["a"])

    def test_the_model_is_fetched_once_before_the_first_title(self):
        store = _Store(fps={"a": "fa", "b": "fb"})
        backend = self.backend({"a": [0.1], "b": [0.2]})
        cb = mock.Mock()
        self.assertEqual(ae.build_index([_entry("a"), _entry("b")], _M, store,
                                        download_cb=cb), (2, 0, None))
        self.assertEqual(backend.fetches, [(cb, 0)])

    def test_nothing_to_index_fetches_nothing(self):
        store = _Store(fps={"a": "fa"}, vecs={("fa", _M): [1.0]})
        backend = self.backend({})
        ae.build_index([_entry("a")], _M, store)
        self.assertEqual(backend.fetches, [])

    def test_a_failed_download_fails_the_run_once_not_every_title(self):
        store = _Store(fps={"a": "fa", "b": "fb"})
        backend = self.backend({"a": [0.1], "b": [0.2]})
        backend.fetch_error = OSError("offline")
        with self.assertLogs(ae.logger, "ERROR") as logs:
            result = ae.build_index([_entry("a"), _entry("b")], _M, store)
        self.assertEqual(result, (0, 2, "OSError: offline"))
        self.assertEqual(backend.calls, [])
        self.assertIn("Model download failed", logs.output[0])

    def test_a_single_entry_already_indexed_is_not_recomputed(self):
        store = _Store(fps={"a": "fa"}, vecs={("fa", _M): [1.0]})
        backend = self.backend({})
        self.assertFalse(ae._embed_entry(_entry("a"), _M, store))
        self.assertFalse(ae._embed_entry(_entry("nofp"), _M, store))
        self.assertEqual(backend.calls, [])


class SimilarityTest(_Base):

    def test_cosine(self):
        self.assertEqual(ae._cosine([0, 0], [1, 1]), 0.0)
        self.assertAlmostEqual(ae._cosine([1, 0], [1, 0]), 1.0)
        self.assertAlmostEqual(ae._cosine([1, 0], [0, 2]), 0.0)

    def test_only_comparable_tracks_are_ranked(self):
        source = _entry("src")
        store = _Store(
            fps={"src": "fs", "twin": "fs", "close": "fc", "far": "ff", "xmas": "fx",
                 "sa": "fsa", "novec": "fn"},
            vecs={("fs", _M): [1.0, 0.0], ("fc", _M): [1.0, 0.2], ("ff", _M): [-1.0, 0.0],
                  ("fx", _M): [1.0, 0.0], ("fsa", _M): [1.0, 0.0]})
        pool = [source, _entry("twin"), _entry("close"), _entry("far"),
                _entry("xmas", is_xmas=True), _entry("sa", dance="SA"), _entry("novec"),
                _entry("nofp")]
        ranked = ae.embedding_similar(source, pool, store, _M)
        self.assertEqual([e.path.stem for _, e in ranked], ["close", "far"])
        self.assertAlmostEqual(ranked[1][0], 0.0)
        across = ae.embedding_similar(source, pool, store, _M, same_dance=False, n=1)
        self.assertEqual([e.path.stem for _, e in across], ["sa"])

    def test_a_larger_pool_is_standardised_before_the_cosine(self):
        source = _entry("src")
        names = ["n1", "n2", "n3", "n4"]
        vecs = {("src", _M): [1.0, 0.9, 5.0], ("n1", _M): [1.0, 1.0, 5.0],
                ("n2", _M): [0.9, 1.0, 5.0], ("n3", _M): [0.0, 0.1, 5.0],
                ("n4", _M): [0.1, 0.0, 5.0]}
        store = _Store(fps={n: n for n in ["src"] + names}, vecs=vecs)
        ranked = ae.embedding_similar(source, [_entry(n) for n in names], store, _M)
        self.assertEqual([e.path.stem for _, e in ranked][:2], ["n1", "n2"])
        self.assertTrue(all(0.0 <= s <= 1.0 for s, _ in ranked))
        self.assertLess(ranked[-1][0], 0.2)   # raw cosines all sit near 1

    def test_an_uncached_source_is_embedded_live(self):
        source = _entry("src")
        store = _Store(fps={"src": "fs", "a": "fa"}, vecs={("fa", _M): [1.0, 0.0]})
        self.backend({"src": [1.0, 0.0]})
        ranked = ae.embedding_similar(source, [_entry("a")], store, _M)
        self.assertEqual(store.vecs[("fs", _M)], [1.0, 0.0])
        self.assertEqual(store.saves, 1)
        self.assertAlmostEqual(ranked[0][0], 1.0)

    def test_no_source_vector_or_no_candidate_ranks_nothing(self):
        store = _Store(fps={"src": "fs"}, vecs={("fs", _M): [1.0]})
        self.assertEqual(ae.embedding_similar(_entry("nofp"), [_entry("src")], store, _M), [])
        self.assertEqual(ae.embedding_similar(_entry("src"), [_entry("nofp")], store, _M), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
