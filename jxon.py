from xml.etree import ElementTree as ET

DIGITS = set("0123456789")
LETTERS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

SINGLE_CHAR_ESCAPES = {
    '"': '"',
    '\\': '\\',
    '/': '/',
    'b': '\b',
    'f': '\f',
    'n': '\n',
    'r': '\r',
    't': '\t'
}


XML_ENTITIES = {
    'lt': '<',
    'gt': '>',
    'amp': '&',
    'apos': '\'',
    'quot': '"'
}


class JXONParseException(BaseException):
    pass


class JXONEncodeException(BaseException):
    pass


class JXONSchemaValidityException(BaseException):
    pass


class JXONType:
    SIMPLE_TYPES = {int, float, bool, str, ET.Element}

    def __init__(self, type, subtype=None):
        if type in JXONType.SIMPLE_TYPES:
            if subtype is not None:
                raise ValueError("Subtype should not be supplied for simple type")

        elif type is list:
            if subtype is not None and type(subtype) is not JXONType:
                raise ValueError("Array subtype must be a JXON type")

        elif type is dict:
            if type(subtype) is not dict:
                raise ValueError("Object subtype must be a dictionary")
            for key, value in subtype.items():
                if value is not None and type(value) is not JXONType:
                    raise ValueError("Invalid object member type: " + repr(type(value)))

        elif type is set:
            if type(subtype) is not set:
                raise ValueError("Expected set subtype")
            member_types = [type(e) for e in subtype]
            if member_types[0] not in (int, float, str):
                raise ValueError("Invalid set member type: " + repr(member_types[0]))
            elif any(t is not member_types[0] for t in member_types):
                raise ValueError("Inconsistent set member types")

        else:
            raise ValueError("Invalid type: " + repr(type))

        self.type = type
        self.subtype = subtype

    def is_jxon_instance(self, obj, fill_null=False):
        if obj is None:
            return True

        if self.type in JXONType.SIMPLE_TYPES:
            return type(obj) is self.type

        elif self.type is list:
            if type(obj) is not list:
                return False

            if self.subtype is None:
                if not fill_null:
                    return True

                self.subtype = JXONType.parse_type(obj[0])

            return all(self.subtype.is_jxon_instance(e) for e in obj)

        elif self.type is dict:
            if type(obj) is not dict:
                return False

            if set(self.subtype.keys()) != set(obj.keys()):
                return False

            for key, jxon_type in self.subtype.items():
                if jxon_type is None:
                    if fill_null:
                        self.subtype[key] = JXONType.parse_type(obj[key])

                elif not jxon_type.is_jxon_instance(obj[key]):
                    return False

            return True

        elif self.type is set:
            return obj in self.subtype

        else:
            raise RuntimeError("??")

    @staticmethod
    def parse_type(obj):
        if obj is None:
            return None

        elif type(obj) in JXONType.SIMPLE_TYPES:
            return JXONType(type(obj))

        elif type(obj) is list:
            if len(obj) == 0:
                return JXONType(list, None)

            jxon_type = JXONType.parse_type(obj[0])
            if not all(jxon_type.is_jxon_instance(e) for e in obj):
                raise JXONSchemaValidityException("Inconsistent list element type")

            return JXONType(list, jxon_type)

        elif type(obj) is dict:
            d = {}
            for key, value in obj.items():
                jxon_type = JXONType.parse_type(value)
                d[key] = jxon_type

            return JXONType(dict, d)

        else:
            raise JXONSchemaValidityException("Not parseable as JXON type: " + repr(type(obj)))



class JXONParser:
    def __init__(self, s):
        self.lines = s.split("\n")
        self.line_no = 0
        self.col_no = 0

    def next(self, n=1):
        if self.eof():
            raise JXONParseException("EOF while parsing JXON")
        elif self.eol():
            self.throw_exception("Unexpected EOL")

        return self.lines[self.line_no][self.col_no: self.col_no+n]

    def advance(self, n=1):
        self.col_no += n

    def eol(self):
        return self.col_no >= len(self.lines[self.line_no])

    def eof(self):
        return self.line_no >= len(self.lines)

    def throw_exception(self, message):
        message = ("(line %s, col %s) " % (self.line_no+1, self.col_no+1)) +\
                  message + "\n" + self.lines[self.line_no] + "\n" + " "*self.col_no + "^"
        raise JXONParseException(message)

    def expect(self, c):
        if self.next() == c:
            self.advance()
        else:
            self.throw_exception("Expected " + repr(c))

    def pass_whitespace(self):
        if self.eof():
            return
        elif self.eol():
            self.col_no = 0
            self.line_no += 1
            self.pass_whitespace()
        elif self.next() in {' ', '\t', '\r'}:
            self.advance()
            self.pass_whitespace()

    def parse(self):
        return self.grab_element()

    def grab_value(self):
        if self.next() == "{":
            return self.grab_object()
        elif self.next() == "[":
            return self.grab_array()
        elif self.next() == '"':
            return self.grab_string()
        elif self.next() in DIGITS:
            return self.grab_number()
        elif self.next() == '<':
            return self.grab_xml(allow_tail=False)

        elif self.next(4) == "true":
            self.advance(4)
            return True
        elif self.next(5) == "false":
            self.advance(5)
            return False
        elif self.next(4) == "null":
            self.advance(4)
            return None

        else:
            self.throw_exception("Unknown expression type")

    def grab_object(self):
        self.expect("{")

        self.pass_whitespace()
        if self.next() == "}":
            return {}

        d = self.grab_members({})

        self.expect('}')

        return d

    def grab_member(self):
        self.pass_whitespace()
        key = self.grab_string()
        self.pass_whitespace()
        self.expect(':')
        value = self.grab_element()

        return key, value

    def grab_members(self, members):
        key, value = self.grab_member()

        if key in members:
            self.throw_exception("Repeat key: " + repr(key))
        else:
            members[key] = value

        if self.next() == ',':
            self.advance()
            return self.grab_members(members)
        else:
            return members

    def grab_array(self):
        self.expect("[")

        self.pass_whitespace()
        if self.next() == "]":
            return []

        d = self.grab_elements()

        self.expect(']')

        return d

    def grab_elements(self):
        e = self.grab_element()

        if self.next() == ',':
            self.advance()
            elements = self.grab_elements()
        else:
            elements = []

        return [e] + elements

    def grab_element(self):
        self.pass_whitespace()
        e = self.grab_value()
        self.pass_whitespace()
        return e

    def grab_string(self):
        self.expect('"')
        s = self.grab_characters()
        self.expect('"')
        return s

    def grab_characters(self):
        s = ""
        while self.next() != '"':
            s += self.grab_character()
        return s

    def grab_character(self):
        if self.next() == '\\':
            self.advance()
            return self.grab_escape()
        elif self.next() == '"':
            self.throw_exception("Expected a character")
        else:
            c = self.next()
            self.advance()
            return c

    def grab_escape(self):
        if self.next() in SINGLE_CHAR_ESCAPES:
            c = SINGLE_CHAR_ESCAPES[self.next()]
            self.advance()
            return c
        elif self.next() == 'u':
            pass
            # TODO: hex escapes
        else:
            self.throw_exception("Invalid escape sequence.")

    def grab_number(self):
        s = ""
        while self.next() in DIGITS:
            s += self.next()
            self.advance()

        # TODO: actual number parsing
        return int(s)

    def grab_xml(self, allow_tail):
        self.expect("<")
        name = self.grab_xml_name()
        self.pass_whitespace()

        attributes = {}
        while self.next() not in ('/', '>'):
            key, value = self.grab_xml_attribute()
            if key in attributes:
                self.throw_exception("Repeated attribute name")
            attributes[key] = value

        e = ET.Element(name, attrib=attributes)

        if self.next() == '/':
            self.advance()
            self.expect('>')

        else:
            self.expect('>')
            e.text = self.grab_xml_text()
            while self.next(2) != "</":
                # TODO: pull into own function?
                if self.next(2) == "<!":
                    self.pass_comment()
                e.append(self.grab_xml(allow_tail=True))

            self.expect('<')
            self.expect('/')
            close_name = self.grab_xml_name()
            if close_name != name:
                self.throw_exception("Mismatched XML tag, expecting a " + name)
            self.pass_whitespace()
            self.expect('>')

        if allow_tail:
            e.tail = self.grab_xml_text()

        return e

    def grab_xml_name(self):
        if self.next() not in (LETTERS | {':', '_'}):
            self.throw_exception("Invalid start to XML name")

        s = ""
        while self.next() in (LETTERS | DIGITS | {':', '_', '.', '-'}):
            # TODO: CombiningChar, Extender
            s += self.next()
            self.advance()

        return s

    def grab_xml_attribute(self):
        key = self.grab_xml_name()
        # TODO: keep whitespace allowance here?
        self.pass_whitespace()
        self.expect('=')
        self.pass_whitespace()
        self.expect('"')

        value = ""
        while self.next() != '"':
            value += self.grab_xml_attr_char()
        self.expect('"')

        return key, value

    def grab_xml_attr_char(self):
        if self.next() == '<':
            self.throw_exception("'<' cannot occur in XML attribute")

        elif self.next() == '&':
            return self.grab_xml_reference()

        else:
            c = self.next()
            self.advance()
            return c

    def grab_xml_reference(self):
        self.expect('&')
        if self.next() == '#':
            # TODO: CharRef
            pass
        else:
            entity = self.grab_xml_name()
            c = self.resolve_entity(entity)

        self.expect(';')
        return c

    def resolve_entity(self, entity):
        if entity in XML_ENTITIES:
            return XML_ENTITIES[entity]
        else:
            # TODO: Entity Declaration
            self.throw_exception('Invalid entity')

    def grab_xml_text(self):
        value = ""
        while self.eol() or self.next() != '<':
            if self.eol():
                self.pass_whitespace()
                value += ' '
            else:
                value += self.grab_xml_attr_char()
            # TODO: Proper content parsing
        return value

    def pass_comment(self):
        self.expect('<')
        self.expect('!')
        self.expect('-')
        self.expect('-')
        self.pass_whitespace()
        while self.next(3) != "-->":
            self.advance()
        self.advance(3)
        self.pass_whitespace()


def has_consistent_schema(obj):
    try:
        JXONType.parse_type(obj)
        return True
    except JXONSchemaValidityException:
        return False


def jxon_equal(o1, o2):
    if type(o1) is not type(o2):
        return False
    t = type(o1)

    if t in {int, float, str, bool}:
        return o1 == o2
    elif t is list:
        return all(jxon_equal(*pair) for pair in zip(o1, o2))
    elif t is dict:
        return set(o1.keys()) == set(o2.keys()) and all(jxon_equal(o1[key], o2[key]) for key in o1)
    elif t is ET.Element:
        if o1.tag != o2.tag:
            return False
        if dict(o1.items()) != dict(o2.items()):
            return False
        if o1.text != o2.text:
            return False
        if o1.tail != o2.tail:
            return False
        return all(jxon_equal(*pair) for pair in zip(o1, o2))
    else:
        raise JXONEncodeException("Not parseable as a JXON type: " + repr(t))


def loads(s):
    parser = JXONParser(s)
    return parser.parse()


def load(fp):
    return loads(fp.read())


def jxon_string_escape(s):
    return s  # TODO


def xml_text_escape(s):
    return s  # TODO


def dumps_helper(o, indent, sort_keys, indent_level):
    if type(o) is int:
        return str(o)
    elif type(o) is float:
        return str(o)
    elif type(o) is str:
        return '"' + jxon_string_escape(o) + '"'
    elif type(o) is bool:
        return 'true' if o else 'false'
    elif o is None:
        return 'null'

    elif type(o) is ET.Element:
        s = "<"
        s += o.tag
        for key, value in o.items():
            s += ' ' + key + '="' + jxon_string_escape(value) + '"'

        if o.text is None and len(list(o)) == 0:
            s += '/>'
        else:
            s += '>'
            if o.text:
                if indent is not None:
                    s += '\n'
                    s += ' ' * (indent * (indent_level+1))

                s += xml_text_escape(o.text)

            if list(o):
                for e in o:
                    if indent is not None:
                        s += '\n'
                        s += ' ' * (indent * (indent_level+1))

                    s += dumps_helper(e, indent=indent, sort_keys=sort_keys, indent_level=indent_level+1)

            if indent is not None:
                s += '\n'
                s += ' ' * (indent * indent_level)

            s += "</" + o.tag + '>'

        if o.tail:
            if indent is not None:
                s += '\n'
                s += ' ' * (indent * indent_level)

            s += xml_text_escape(o.tail)

        return s

    elif type(o) is dict:
        s = '{'
        if indent is not None:
            s += '\n'

        items = o.items()
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

    elif type(o) is list:
        s = '['
        if indent is not None:
            s += '\n'

        for e in o:
            if indent is not None:
                s += ' ' * (indent * (indent_level+1))

            s += dumps_helper(e, indent=indent, sort_keys=sort_keys, indent_level=indent_level+1)
            s += ','

            if indent is not None:
                s += '\n'
            else:
                s += ' '

        s = s[:-2]
        if indent is not None:
            s += '\n' + ' ' * (indent * indent_level)

        s += ']'

        return s

    else:
        raise JXONEncodeException(repr(o) + " cannot be encoded into JXON")


def dumps(obj, indent=None, sort_keys=False):
    return dumps_helper(obj, indent=indent, sort_keys=sort_keys, indent_level=0)


def dump(obj, fp, indent=None, sort_keys=False):
    fp.write(dumps(obj, indent=indent, sort_keys=sort_keys))
