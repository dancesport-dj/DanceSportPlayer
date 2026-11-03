"""One damaged cell or blob must cost one re-read, not the whole library
(review items 5, 6, 33, 34)."""
import os
import tempfile
import unittest
from array import array

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR", tempfile.mkdtemp(prefix="dp_cells_"))

import planner.music.db as pdb
from planner.music import embeddings, tag_edits


class RowToMetaTests(unittest.TestCase):
    def row(self, classes_ok, comment_tags):
        return ("t", "TG", 30, 2000, None, classes_ok, 0, 0, "t", "a", 100.0, "alb",
                comment_tags, None, None, None, None, None)

    def test_damaged_json_cells_read_as_not_read_yet(self):
        meta = pdb.row_to_meta(self.row("{", '{"a": 1}'))
        self.assertIsNone(meta["classes_ok"])
        self.assertIsNone(meta["comment_tags"])

    def test_good_cells_still_decode(self):
        meta = pdb.row_to_meta(self.row('["S"]', "[]"))
        self.assertEqual(meta["classes_ok"], ["S"])
        self.assertEqual(meta["comment_tags"], [])


class BlobTests(unittest.TestCase):
    def test_cut_off_feature_blob_is_not_a_vector(self):
        self.assertIsNone(pdb.AudioCache._unpack_mfcc(b"abcde"))
        good = array("f", [1.0, 2.0]).tobytes()
        self.assertEqual(list(pdb.AudioCache._unpack_mfcc(good)), [1.0, 2.0])

    def test_cut_off_embedding_blob_is_skipped(self):
        with self.assertRaises(ValueError):
            embeddings.EmbeddingStore._unpack(b"abcde")


class TagEditTests(unittest.TestCase):
    def test_damaged_list_cell_drops_only_that_field(self):
        fields = tag_edits.EDIT_FIELDS
        row = [None] * len(fields)
        list_field = next(f for f in fields if f in tag_edits._LIST_FIELDS)
        row[fields.index(list_field)] = "{"
        text_field = next(f for f in fields if f in tag_edits._TEXT_FIELDS)
        row[fields.index(text_field)] = "kept"
        self.assertEqual(tag_edits._unpack(tuple(row)), {text_field: "kept"})


if __name__ == "__main__":
    unittest.main()
