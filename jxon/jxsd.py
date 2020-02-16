from .parser import SIMPLE_TYPE_KEYWORDS, Parser, LETTERS, jxon_string_escape, loads_factory, load_factory
from .jxontype import JXONType, parse_type, has_consistent_schema
from . import jxon


class JXSDParseException(BaseException):
    pass


class JXSDParser(Parser):
    exception_class = JXSDParseException
    permit_type_annotation = False
    native_extension = ".jxsd"

    def grab_value(self):
        if self.next() == "{":
            d = self.grab_object()
            return JXONType(dict, d)
        elif self.next() == "[":
            return self.grab_array()
        elif self.next(4) == "Enum":
            return self.grab_enum()

        elif self.next() in LETTERS | {'_'}:
            return self.resolve_variable()

        self.throw_exception("Unknown expression type")

    def grab_array(self):
        self.expect('[')
        jxon_type = self.grab_element()
        self.expect(']')
        return JXONType(list, subtype=jxon_type)

    def grab_enum(self):
        self.expect("Enum")
        self.expect('(')

        jxon_parser = jxon.JXONParser('')
        jxon_parser.lines = self.lines
        jxon_parser.line_no = self.line_no
        jxon_parser.col_no = self.col_no

        els = jxon_parser.grab_elements()

        self.line_no = jxon_parser.line_no
        self.col_no = jxon_parser.col_no

        if type(els[0]) not in JXONType.SIMPLE_TYPES:
            self.throw_exception("Enum members can only be primitive types")
            # TODO?

        self.expect(')')

        return JXONType(set, set(els))


loads = loads_factory(JXSDParser)
load = load_factory(JXSDParser)


class JXSDEncodeException(BaseException):
    pass


def dumps_helper(jxon_type: JXONType, indent, sort_keys, indent_level):
    for key, value in SIMPLE_TYPE_KEYWORDS.items():
        if jxon_type.jxon_type is value.jxon_type:
            return key

    if jxon_type.jxon_type is list:
        return "[%s]" % dumps_helper(jxon_type.subtype, indent=indent, sort_keys=sort_keys, indent_level=indent_level)

    elif jxon_type.jxon_type is dict:
        s = '{'
        if indent is not None:
            s += '\n'

        items = jxon_type.subtype.items()
        if sort_keys:
            items = sorted(list(items), key=lambda x: x[0])
        for key, value in items:
            if indent is not None:
                s += ' ' * (indent * (indent_level+1))

            s += '"' + jxon_string_escape(key) + '"'
            s += ': '
            s += dumps_helper(value, indent=indent, sort_keys=sort_keys, indent_level=indent_level+1)
            s += ','

            if indent is not None:
                s += '\n'
            else:
                s += ' '

        s = s[:-2]
        if indent is not None:
            s += '\n' + ' ' * (indent * indent_level)

        s += '}'

        return s

    elif jxon_type.jxon_type is set:
        l = list(jxon_type.subtype)
        if sort_keys:
            l.sort()

        s = jxon.dumps_helper(l, indent=indent, sort_keys=sort_keys, indent_level=indent_level)
        return "Enum(%s)" % s[1:-1]

    else:
        raise ValueError("??")


def dumps(jxon_type, indent=None, sort_keys=False):
    if type(jxon_type) is not JXONType:
        raise JXSDEncodeException("Cannot dump something other than a JXONType object")

    return dumps_helper(jxon_type, indent=indent, sort_keys=sort_keys, indent_level=0)


def dump(jxon_type, fp, indent=None, sort_keys=False):
    fp.write(dumps(jxon_type, indent=indent, sort_keys=sort_keys))