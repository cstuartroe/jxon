from .parser import load_factory, loads_factory
from .jxon import JXONParser, dumps, dump, jxon_equal
from .jxsd import JXSDParser


class CombinedParser(JXONParser):
    native_extension = ".jxon"

    subparser_classes = {
        ".jxsd": JXSDParser,
        ".xml": JXONParser,
        ".json": JXONParser
    }


loads = loads_factory(CombinedParser)
load = load_factory(CombinedParser)
