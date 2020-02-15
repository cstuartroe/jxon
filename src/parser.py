import os

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


class VariableResolutionException(BaseException):
    pass


class Module:
    def __init__(self, default_export=None, exports={}):
        self.default_export = default_export
        self.exports = exports

    def set(self, key, value):
        if key in self.exports:
            raise ValueError("Variable name already set: " + repr(key))
        self.exports[key] = value

    def resolve_variable_chain(self, labels):
        if labels[0] in self.exports:
            value = self.exports[labels[0]]
        else:
            raise VariableResolutionException("Name not found: " + labels[0])

        if len(labels) == 1:
            return value
        else:
            if not isinstance(value, Module):
                raise VariableResolutionException("Not a module: " + labels[0])

            return value.resolve_variable_chain(labels[1:])


class Parser:
    exception_class = None
    permit_type_annotation = None
    native_extension = None
    subparser_classes = {}

    def __init__(self, s):
        self.lines = s.split("\n")
        self.line_no = 0
        self.col_no = 0
        self.module = Module()

    def next(self, n=1, permit_eol=True):
        if self.eof():
            if permit_eol:
                return chr(0)
            else:
                raise self.exception_class("EOF while parsing JXON")
        elif self.eol():
            if permit_eol:
                return chr(0)
            else:
                self.throw_exception("Unexpected EOL")

        return self.lines[self.line_no][self.col_no: self.col_no+n]

    def advance(self, n=1):
        self.col_no += n

    def eol(self):
        return self.col_no >= len(self.lines[self.line_no])

    def eof(self):
        return self.line_no >= len(self.lines)

    def breakpoint(self):
        return self.line_no, self.col_no

    def jump(self, bp):
        self.line_no, self.col_no = bp

    def throw_exception(self, message, bp=None):
        if bp:
            self.jump(bp)

        if self.eof():
            self.line_no = len(self.lines) - 1
            self.col_no = len(self.lines[-1]) - 1

        message = ("(line %s, col %s) " % (self.line_no+1, self.col_no+1)) +\
                  message + "\n" + self.lines[self.line_no] + "\n" + " "*self.col_no + "^"
        raise self.exception_class(message)

    def expect(self, s):
        if self.next(len(s)) == s:
            self.advance(len(s))
        else:
            self.throw_exception("Expected " + repr(s))

    def expect_whitespace(self):
        if not self.eol() and self.next() not in {' ', '\t', '\r'}:
            self.throw_exception("Expected whitespace")

        self.pass_whitespace()

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
        module = self.parse_as_module()
        return module.default_export

    def parse_as_module(self):
        self.pass_whitespace()
        self.read_imports()
        self.read_variables()
        if not self.eof() and self.next(6) != "export":
            self.module.default_export = self.grab_element()
        if not self.eof():
            self.read_exports()
        return self.module

    def read_imports(self):
        while self.next(6) == "import":
            self.advance(6)
            self.expect(' ')
            self.pass_whitespace()

            defaultExportLabel = None
            moduleLabel = None
            moduleImports = None

            if self.next() in LETTERS | {'_'}:
                defaultExportLabel = self.grab_label()
                self.pass_whitespace()

            if defaultExportLabel is None or self.next() == ',':
                if self.next() == ',':
                    self.advance()
                    self.pass_whitespace()

                if self.next() == '*':
                    self.advance()
                    self.expect_whitespace()
                    self.expect('as')
                    self.expect_whitespace()
                    moduleLabel = self.grab_label()
                    if moduleLabel == '':
                        self.throw_exception("Must specify a name to give module")
                else:
                    self.expect('{')
                    self.pass_whitespace()
                    moduleImports = self.grab_labels()
                    # TODO: support for import {foo as bar} from "example.jxon"
                    self.pass_whitespace()
                    self.expect('}')

                self.pass_whitespace()

            self.expect('from')
            self.expect_whitespace()

            filepath = self.grab_string()
            submodule = self.load_submodule(filepath)

            if defaultExportLabel:
                if submodule.default_export is None:
                    self.throw_exception("Module " + filepath + " has no default export")
                self.module.set(defaultExportLabel, submodule.default_export)

            if moduleLabel:
                self.module.set(moduleLabel, submodule)

            if moduleImports:
                for label in moduleImports:
                    if label not in submodule.exports:
                        self.throw_exception("Module " + filepath + " has no export called " + label)
                    self.module.set(label, submodule.exports[label])

            self.expect(';')
            self.expect_whitespace()

    def load_submodule(self, filepath):
        _, extension = os.path.splitext(filepath)
        with open(filepath, 'r') as fh:
            s = fh.read()

        subparser_class = self.resolve_subparser_class(extension)
        subparser = subparser_class(s)
        submodule = subparser.parse_as_module()
        return submodule

    def resolve_subparser_class(self, extension):
        if extension == self.native_extension:
            return type(self)
        elif extension in self.subparser_classes:
            return self.subparser_classes[extension]
        else:
            self.throw_exception("Unknown file extension: " + extension)

    def read_variables(self):
        while not self.eof() and self.next() in LETTERS | {'_'}:
            bp = self.breakpoint()
            label = self.grab_label()
            if label == "export":
                self.jump(bp)
                return

            self.pass_whitespace()

            if self.next() == ':':
                if not self.permit_type_annotation:
                    self.throw_exception("Cannot provide type annotations in JXSD")

                self.advance()
                self.pass_whitespace()
                jxon_type = self.resolve_variable()
                self.pass_whitespace()
            else:
                jxon_type = None

            self.expect('=')
            value = self.grab_element()
            if jxon_type is not None and not jxon_type.is_jxon_instance(value):
                self.throw_exception("Type does not match annotation")

            self.module.set(label, value)

    def resolve_variable(self):
        labels = [self.grab_label()]
        while self.next(permit_eol=True) == '.':
            self.advance()
            labels.append(self.grab_label())

        return self.module.resolve_variable_chain(labels)

    def read_exports(self):
        exports = None
        default_export = None

        while self.next(6) == "export":
            self.advance(6)
            self.expect_whitespace()

            if self.next(7) == "default":
                self.advance(7)
                self.expect_whitespace()
                default_export = self.resolve_variable()

            elif self.next() in LETTERS | {'_'}:
                label = self.grab_label()
                exports[label] = self.module.resolve_variable_chain([label])

            else:
                self.expect('{')
                self.pass_whitespace()
                for label in self.grab_labels():
                    exports[label] = self.module.resolve_variable_chain([label])
                self.expect('}')

            self.pass_whitespace()
            self.expect(';')
            self.pass_whitespace()

        self.module.default_export = default_export
        self.module.exports = exports

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

    def grab_labels(self):
        label = self.grab_label()
        if label == '':
            self.throw_exception("Expected label")

        self.pass_whitespace()

        if self.next() == ',':
            self.advance()
            self.pass_whitespace()
            labels = self.grab_labels()
        else:
            labels = []

        return [label] + labels

    def grab_label(self):
        s = ""
        while self.next(permit_eol=True) in LETTERS | DIGITS | {'_'}:
            s += self.next()
            self.advance()
        return s


def jxon_string_escape(s):
    for escape, char in SINGLE_CHAR_ESCAPES.items():
        if char != '/':
            s = s.replace(char, '\\' + escape)
    return s  # TODO: more?
