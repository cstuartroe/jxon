import json
import unittest

from jxon import jxsd
from jxon import combined as jxon
from jxon.jxontype import JXONType

TEST_JXON = [
    # "test.jxon",
]

TEST_XML = [
    # "artelevanto.xml"
]

TEST_JSON = [
    # "random.json",
    "data.json"
]

TEST_JXSD = [
    # "test.jxsd"
]

ALL_TESTS = TEST_JXON + TEST_JSON


class JSONBackwardsCompatibilityTests(unittest.TestCase):

    def test_json(self):
        for test_file in TEST_JSON:
            fullpath = 'tests/' + test_file
            with open(fullpath, 'r') as fh:
                jxon_raw = fh.read()

            self.assertEqual(json.loads(jxon_raw), jxon.loads(jxon_raw))

    def test_idempotence(self):
        for test_file in ALL_TESTS:
            fullpath = 'tests/' + test_file
            with open(fullpath, 'r') as fh:
                o = jxon.load(fh)

            self.assertTrue(jxon.jxon_equal(o, jxon.loads(jxon.dumps(o))))
            self.assertTrue(jxon.jxon_equal(o, jxon.loads(jxon.dumps(o, indent=2))))


if __name__ == "__main__":
    # unittest.main()
    with open("tests/data.json", "r") as fh:
        data = jxon.load(fh)

    schema = jxsd.parse_type(data)
    print(jxsd.dumps(schema, 2))