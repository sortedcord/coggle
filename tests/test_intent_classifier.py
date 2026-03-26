import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from coggle.intent_classifier import classify, Intent


class TestIdClassifierExamples(unittest.TestCase):
    examples = [
        ("find all jpgs starting with X", (Intent.LIST, True)),
        ("move all files modified before 2022 to archive folder", (Intent.MOVE, True)),
        ("delete all logs older than 30 days", (Intent.DELETE, True)),
        (
            "rename all files starting with tmp to start with backup",
            (Intent.RENAME, True),
        ),
        ("find and delete all jpgs", (None, False)),  # compound — should reject
        ("create a new file called notes.txt", (Intent.CREATE, True)),
        ("copy everything in documents to backup", (Intent.COPY, True)),
        ("make a symlink to this config file", (Intent.SYMLINK, True)),
        ("truncate the error log", (Intent.TRUNCATE, True)),
        ("what should i have for lunch", (None, False)),  # no intent
        ("hardlink this file to that location", (Intent.HARDLINK, True)),
    ]

    def test_examples(self):
        for query, (intent_expected, success_expected) in self.examples:
            with self.subTest(query=query):
                result = classify(query)
                self.assertEqual(result.success, success_expected)
                if success_expected:
                    self.assertEqual(result.intent, intent_expected)
                else:
                    self.assertIsNone(result.intent)


if __name__ == "__main__":
    unittest.main()
