DIGITS = set("0123456789")

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


class JXONParseException(BaseException):
    pass


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

    def advance(self):
        self.col_no += 1

    def eol(self):
        return self.col_no >= len(self.lines[self.line_no])

    def eof(self):
        return self.line_no >= len(self.lines)

    def throw_exception(self, message):
        message = "(line %s, col %s) " + message + "\n" + self.lines[self.line_no] + "\n" + " "*self.col_no + "^"
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
        elif self.next(4) == "true":
            return True
        elif self.next(5) == "false":
            return False
        elif self.next(4) == "null":
            return None
        else:
            self.throw_exception("Unknown expression type")

    def grab_object(self):
        self.expect("{")

        self.pass_whitespace()
        if self.next() == "}":
            return {}

        d = self.grab_members()

        self.expect('}')

        return d

    def grab_member(self):
        self.pass_whitespace()
        key = self.grab_string()
        self.pass_whitespace()
        self.expect(':')
        value = self.grab_element()

        return key, value

    def grab_members(self):
        key, value = self.grab_member()

        if self.next() == ',':
            self.advance()
            members = self.grab_members()
        else:
            members = {}

        if key in members:
            self.throw_exception("Repeat key: " + repr(key))
        else:
            members[key] = value
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


def loads(s):
    parser = JXONParser(s)
    return parser.parse()