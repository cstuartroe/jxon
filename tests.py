import json
import unittest

import jxon

TEST_JXON = [
    "test.jxon"
]

TEST_XML = [
    "artelevanto.xml"
]

TEST_JSON = [
    "random.json"
]

ALL_TESTS = TEST_JXON + TEST_XML + TEST_JSON


class JSONBackwardsCompatibilityTests(unittest.TestCase):

    def test_all(self):
        for test_file in TEST_JSON:
            fullpath = 'tests/' + test_file
            with open(fullpath, 'r') as fh:
                jxon_raw = fh.read()

            self.assertEqual(json.loads(jxon_raw), jxon.loads(jxon_raw))

    def test_idempotence(self):
        for test_file in ALL_TESTS:
            fullpath = 'tests/' + test_file
            with open(fullpath, 'r') as fh:
                raw = fh.read()
            o = jxon.loads(raw)

            self.assertTrue(jxon.jxon_equal(o, jxon.loads(jxon.dumps(o))))


if __name__ == "__main__":
    for test_file in ALL_TESTS:
        fullpath = 'tests/' + test_file
        with open(fullpath, 'r') as fh:
            jxon.load(fh)

    unittest.main()
