import unittest
from coggle.span_detection import detect_spans


class TestSpanDetectionExamples(unittest.TestCase):
    examples = [
        ("find all jpgs starting with X", [["all", "jpgs"], ["starting", "with", "X"]]),
        (
            "move all files modified before 2022 to archive folder",
            [
                ["all", "files"],
                ["modified", "before", "2022"],
                ["to", "archive", "folder"],
            ],
        ),
        (
            "delete all logs older than 30 days",
            [["all", "logs"], ["older", "than", "30", "days"]],
        ),
        (
            "rename all files starting with tmp to start with backup",
            [
                ["all", "files"],
                ["starting", "with", "tmp"],
                ["to", "start", "with", "backup"],
            ],
        ),
        # ("find and delete all jpgs", [["find"], ["and"], ["delete"], ["all", "jpgs"]]),
        (
            "create a new file called notes.txt",[
            ["a", "new", "file"],
            ["called", "notes.txt"],]
        ),
        (
            "copy everything in documents to backup",
            [["everything"],
            ["in", "documents"],
            ["to", "backup"],]
        ),
        (
            "make a symlink to this config file",
            [["a", "symlink"], ["to", "this", "config", "file"]],
        ),
        ("truncate the error log", [["the", "error", "log"]]),
        (
            "hardlink this file to that location",
            [["this", "file"], ["to", "that", "location"]],
        ),
    ]

    def test_examples(self):
        for query, spans in self.examples:
            with self.subTest(query=query):
                result = detect_spans(query)
                self.assertEqual(result, spans)


if __name__ == "__main__":
    unittest.main()
