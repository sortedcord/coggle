import os
import unittest
from coggle.execution.resolver import check_path
from coggle.exceptions import PathNotFoundError, InvalidPathError, UnresolvablePathError

class TestPathResolution(unittest.TestCase):
    example_paths = [
        ("downloads", "unresolvable"),
        ("/downloads", "fuzzy"),
        ("~/Downloads/", "exact"),
        ("downloads/", "unresolvable"),
        ("./downloads", "unresolvable"),
        ("../downloads", "unresolvable"),
        (".../downloads", "invalid"),
        ("../Downloads/", "unresolvable")
    ]
    def test_paths(self):
        for index, example in enumerate(self.example_paths):
            expected = self.example_paths[index][1]
            path = example[0]
            if expected == "unresolvable":
                with self.assertRaises(UnresolvablePathError):
                    check_path(path)
            elif expected == "fuzzy":
                with self.assertRaises(PathNotFoundError):
                    check_path(path)
            elif expected == "invalid":
                with self.assertRaises(InvalidPathError):
                    check_path(path)
            else:
                pathname = check_path(path)
                exists = os.path.exists(pathname) if pathname else None
                self.assertEqual(exists, True) 

if __name__ == "__main__":
    unittest.main()
