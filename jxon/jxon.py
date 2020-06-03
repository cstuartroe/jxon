from xml.etree import ElementTree as ET

from .parser import Parser, DIGITS, LETTERS, jxon_string_escape


XML_ENTITIES = {
    'lt': '<',
    'gt': '>',
    'amp': '&',
    'apos': '\'',
    'quot': '"'
}


class JXONParseException(BaseException):
    pass


class JXONParser(Parser):
    exception_class = JXONParseException
    permit_type_annotation = True

    def grab_value(self):
        if self.next() == "{":
            return self.grab_object()
        elif self.next() == "[":
            return self.grab_array()
        elif self.next() == '"':
            return self.grab_string(allow_lb=True)
        elif self.next() in DIGITS | {'-'}:
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

        elif self.next() in LETTERS | {'_'}:
            return self.resolve_variable()

        else:
            self.throw_exception("Unknown expression type")

    def grab_array(self):
        self.expect("[")

        self.pass_whitespace()
        if self.next() == "]":
            return []

        d = self.grab_elements()

        self.expect(']')

        return d

    def grab_number(self):
        s = ""
        if self.next() == '-':
            s += '-'
            self.advance()

        s += self.grab_digits()

        if self.next() == '.':
            s += '.'
            self.advance()
            s += self.grab_digits(zerostart=True)

        if self.next() in 'Ee':
            s += 'e'
            self.advance()
            if self.next() in '+-':
                s += self.next()
                self.advance()
            else:
                self.throw_exception("Exponent must be followed by sign")
            s += self.grab_digits(zerostart=True)

        return eval(s)

    def grab_digits(self, zerostart=False):
        if (not zerostart) and self.next() == '0':
            self.advance()
            return '0'

        s = ''
        while self.next(permit_eol=True) in DIGITS:
            s += self.next()
            self.advance()
        return s

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
            self.pass_whitespace()

        e = ET.Element(name, attrib=attributes)

        if self.next() == '/':
            self.advance()
            self.expect('>')

        else:
            self.expect('>')
            self.pass_whitespace()
            e.text = self.grab_xml_text()

            children = []
            while self.next(2) != "</":
                # TODO: pull into own function?
                if self.next(2) == "<!":
                    self.pass_comment()
                children.append(self.grab_xml(allow_tail=True))
            if len(children) > 0:
                children[-1].tail = children[-1].tail.rstrip()
                e.extend(children)
            else:
                e.text = e.text.rstrip()

            self.expect('</')
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
        self.expect('<!--')
        self.pass_whitespace()
        while self.next(3) != "-->":
            self.advance()
        self.advance(3)
        self.pass_whitespace()


class JXONEncodeException(BaseException):
    pass


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
            print(o1.tag, o2.tag)
            return False
        if dict(o1.items()) != dict(o2.items()):
            return False
        if o1.text != o2.text:
            print("text", o1.tag, repr(o1.text), repr(o2.text))
            return False
        if o1.tail != o2.tail:
            print("tail", o1.tag, repr(o1.tail), repr(o2.tail))
            return False
        return all(jxon_equal(*pair) for pair in zip(o1, o2))
    else:
        raise JXONEncodeException("Not parseable as a JXON type: " + repr(t))


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

        if not o.text and len(list(o)) == 0:
            s += '/>'
        else:
            s += '>'
            if o.text:
                if indent is not None:
                    s += '\n'
                    s += ' ' * (indent * (indent_level+1))

                s += xml_text_escape(o.text)

            if list(o):
                if indent is not None and (o.text == "" or o.text[-1] in {' ', '\t', '\r', '\n'}):
                    s = s.rstrip()
                    s += '\n'
                    s += ' ' * (indent * (indent_level+1))

                for i, e in enumerate(o):
                    if indent is not None and i != 0:
                        s += '\n'
                        s += ' ' * (indent * (indent_level+1))

                    s += dumps_helper(e, indent=indent, sort_keys=sort_keys, indent_level=indent_level+1)

            if indent is not None:
                s += '\n'
                s += ' ' * (indent * indent_level)

            s += "</" + o.tag + '>'

        if o.tail:
            if indent is not None and o.tail[0] in {' ', '\t', '\r', '\n'}:
                s += '\n'
                s += ' ' * (indent * indent_level)
                s += xml_text_escape(o.tail.lstrip())
            else:
                s += xml_text_escape(o.tail)

            if indent is not None:
                s = s.rstrip()

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
