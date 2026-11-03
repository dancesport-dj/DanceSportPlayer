"""🧠 A second embedding rank replaces the first cleanly (#65)."""
import unittest
from types import SimpleNamespace
from unittest import mock

from gui.dialogs import similar_dialog
from gui.dialogs.similar_dialog import SimilarTracksDialog


class RankRerunTest(unittest.TestCase):

    def start_two(self):
        busies, workers = [], []

        def make_busy(*_a, **_k):
            busies.append(mock.Mock())
            return busies[-1]

        def make_worker(*_a, **_k):
            workers.append(mock.Mock())
            return workers[-1]

        dlg = SimpleNamespace(
            _method="mert", _source=object(), _emb_busy=None, _rank_worker=None,
            _get_store=lambda: object(), _emb_pool=list,
            _emb_info=lambda m: ("mert", True, "MERT"),
            _on_embedding_ranked=mock.Mock(), _on_embed_error=mock.Mock())
        with (mock.patch.object(similar_dialog, "BusyDialog", side_effect=make_busy),
              mock.patch.object(similar_dialog, "EmbeddingRankWorker", side_effect=make_worker)):
            SimilarTracksDialog._run_embedding_rank(dlg)
            SimilarTracksDialog._run_embedding_rank(dlg)
        return dlg, busies, workers

    def test_the_first_busy_dialog_is_closed_by_the_second_run(self):
        _dlg, busies, _workers = self.start_two()
        busies[0].finish.assert_called_once_with()
        busies[1].finish.assert_not_called()

    def test_only_the_latest_worker_reports(self):
        dlg, _busies, workers = self.start_two()
        workers[0].done.connect.call_args.args[0]("src", ["old"])
        dlg._on_embedding_ranked.assert_not_called()
        workers[1].done.connect.call_args.args[0]("src", ["new"])
        dlg._on_embedding_ranked.assert_called_once_with("src", ["new"])
        workers[0].error.connect.call_args.args[0]("boom")
        dlg._on_embed_error.assert_not_called()


class ChainedDropTest(unittest.TestCase):
    """A dropped file waits while an embedding index build or rank is running (#73)."""

    def drop(self, emb_busy):
        dlg = SimpleNamespace(_worker=None, _emb_busy=emb_busy, _status=mock.Mock(),
                             _lib=object(), _cache=object(),
                             _on_worker_done=mock.Mock(), _on_worker_error=mock.Mock())
        dlg._limits = lambda: (50, 0.5)
        dlg._round_only = lambda: False
        with (mock.patch.object(similar_dialog, "SimilarFromFileWorker") as worker,
              mock.patch.object(similar_dialog, "BusyDialog")):
            SimilarTracksDialog._on_dropped(dlg, "x.mp3")
        return worker

    def test_a_running_embedding_job_refuses_the_drop(self):
        self.drop(mock.Mock()).assert_not_called()


class DuplicateHidingTest(unittest.TestCase):
    """Tracks whose title key is empty are not duplicates of each other (#75)."""

    def test_empty_keys_are_all_kept(self):
        dlg = SimpleNamespace(_dedup_chk=mock.Mock())
        dlg._dedup_chk.isChecked.return_value = True
        a = SimpleNamespace(path="a.mp3", title="")
        b = SimpleNamespace(path="b.mp3", title="")
        c = SimpleNamespace(path="c.mp3", title="")
        keys = {"a.mp3": "", "b.mp3": "", "c.mp3": "song"}
        with mock.patch.object(similar_dialog, "song_title_key", side_effect=keys.get):
            out, hidden = SimilarTracksDialog._visible_results(dlg, [(0.9, a), (0.8, b), (0.7, c)])
        self.assertEqual([e.path for _s, e in out], ["a.mp3", "b.mp3", "c.mp3"])
        self.assertEqual(hidden, 0)


if __name__ == "__main__":
    unittest.main()
