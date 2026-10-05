#!/usr/bin/env python3
"""Picking the OpenL3 / Chroma method counts the indexed pool without reading it.

Run:  py -m unittest tests.gui.test_embedding_pool_no_hash -v

Before ranking, the Similar-Tracks dialog counts how many pool tracks already
have an embedding, to decide whether to offer building the index. It resolved
each track through `fingerprint()` — a stat per track, and a full read and
hash of every track never fingerprinted, all on the GUI thread. The count only
gates a question; the fingerprint on record is enough.
"""

import unittest
from types import SimpleNamespace
from unittest import mock

import planner.db as pdb
from planner import embeddings as ae
from gui.similar_dialog import SimilarTracksDialog
from tests.gui.test_edit_no_stat import _ScratchCache


class EmbeddingPoolCountTest(_ScratchCache):

    def test_the_indexed_count_reads_no_file(self):
        store = ae.EmbeddingStore(self.cache)
        for p in self.tracks:
            store.put(self.cache.fingerprint(p), ae.MODEL_OPENL3, [0.1, 0.2])
        fresh = self.dir / "fresh.mp3"
        fresh.write_bytes(b"never fingerprinted")
        pool = [SimpleNamespace(path=p) for p in (*self.tracks, fresh)]
        dlg = SimpleNamespace(
            _method="openl3", _cache=self.cache, _lib=object(),
            _emb_info=lambda m: (ae.MODEL_OPENL3, True, "OpenL3"),
            _get_store=lambda: store, _emb_pool=lambda: pool,
            _run_embedding_rank=mock.Mock())
        calls = self.stats()
        with mock.patch.object(pdb, "_fingerprints", wraps=pdb._fingerprints) as hashing:
            SimilarTracksDialog._rank_embedding(dlg)
        dlg._run_embedding_rank.assert_called_once_with()
        hashing.assert_not_called()
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
