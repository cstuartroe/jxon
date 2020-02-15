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


class Parser:
    def __init__(self, s, exception_class):
        self.lines = s.split("\n")
        self.line_no = 0
        self.col_no = 0
        self.exception_class = exception_class

    def next(self, n=1):
        if self.eof():
            raise self.exception_class("EOF while parsing JXON")
        elif self.eol():
            self.throw_exception("Unexpected EOL")

        return self.lines[self.line_no][self.col_no: self.col_no+n]

    def advance(self, n=1):
        self.col_no += n

    def eol(self):
        return self.col_no >= len(self.lines[self.line_no])

    def eof(self):
        return self.line_no >= len(self.lines)

    def throw_exception( self, message):
        message = ("(line %s, col %s) " % (self.line_no+1, self.col_no+1)) +\
                  message + "\n" + self.lines[self.line_no] + "\n" + " "*self.col_no + "^"
        raise self.exception_class(message)

    def expect(self, s):
        if self.next(len(s)) == s:
            self.advance(len(s))
        else:
            self.throw_exception("Expected " + repr(s))

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

    def grab_element(self):
        self.pass_whitespace()
        e = self.grab_value()
        self.pass_whitespace()
        return e

    def grab_elements(self):
        e = self.grab_element()

        if self.next() == ',':
            self.advance()
            elements = self.grab_elements()
        else:
            elements = []

        return [e] + elements

    def grab_value(self):
        raise NotImplementedError()

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


def jxon_string_escape(s):
    for escape, char in SINGLE_CHAR_ESCAPES.items():
        if char != '/':
            s = s.replace(char, '\\' + escape)
    return s  # TODO: more?
