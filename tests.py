import json
import unittest

import jxon


class JSONBackwardsCompatibilityTests(unittest.TestCase):
    TEST_FILES = [
        "test.jxon"
    ]

    def test_all(self):
        for test_file in JSONBackwardsCompatibilityTests.TEST_FILES:
            fullpath = 'tests/' + test_file
            with open(fullpath, 'r') as fh:
                jxon_raw = fh.read()
            self.assertEqual(json.loads(jxon_raw), jxon.loads(jxon_raw))


if __name__ == "__main__":
    unittest.main()