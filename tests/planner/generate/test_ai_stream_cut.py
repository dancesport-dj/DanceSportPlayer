"""A truncated SSE data line is a cut answer, not a JSON traceback (#71)."""
import io
import unittest

from planner.generate import ai


class StreamCutTest(unittest.TestCase):

    def reply(self, lines):
        resp = io.BytesIO(b"".join(line + b"\n" for line in lines))
        return ai._stream_reply(resp, "host", 1e9, 1e9)

    def test_a_cut_json_line_is_a_connection_error(self):
        with self.assertRaises(ConnectionError):
            self.reply([b'data: {"choices": [{"delta": {"conte'])

    def test_a_whole_stream_still_reads(self):
        out = self.reply([b'data: {"choices": [{"delta": {"content": "hi"}}]}',
                          b"data: [DONE]"])
        self.assertEqual(out["choices"][0]["message"]["content"], "hi")


if __name__ == "__main__":
    unittest.main()
