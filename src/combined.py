from .jxon import JXONParser, dumps, dump, jxon_equal
from .jxsd import JXSDParser


class CombinedParser(JXONParser):
    subparser_classes = {
        ".jxsd": JXSDParser,
        ".xml": JXONParser,
        ".json": JXONParser
    }


def loads(s):
    parser = CombinedParser(s)
    return parser.parse()


def load(fp):
    return loads(fp.read())
