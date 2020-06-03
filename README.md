# JXON (JavaScript and XML Object Notation)

JXON is a data interchange format which is *mostly* a superset of XML and *mostly* a superset of JSON. 
It looks like JSON, but with a few key feature adds:

* XML as a primitive type
* comments
* multiline strings
* enforced schema consistency, and a schema language JXSD
* variables and imports

This library provides an API to perform a number of JXON-related tasks:
* parsing JXON into standard Python object types and dumping to strings and files, with an API analogous to the `json` standard library API
* checking schema consistency of JXON
* parsing JXSD (JXON Schema Definition) files and using them to enforce schemas
* parsing the schema of JXON files, and exporting them as JXSD

The last bullet point includes a major utility of this library that doesn't involve
JXON at all - it can be used to extract the schema from JSON files, as long as they
use a schema consistently.

## XML as a primitive type

In JXON, XML can be written directly in a file as a primitive object type:

```
{
  "name": "Conor Stuart Roe",
  "age": 23,
  "blurb": <div class="col-6 col-md-12">
    <h1>Hello, World!</h1>
    <br/>
    <p>This is part of valid JXON</p>
  </div>
}
```

I'm using the Python standard `xml` library to represent XML elements, 
but I'd like to eventually add support for `lxml` and maybe other XML
libraries.

Just as any valid JSON value, even a number or a string, is considered to constitute 
valid JSON in itself, a single XML element (including any children) constitutes
valid JXON, so that many XML documents can be parsed as valid JXON! However,
XML preambles are cannot be parsed by the JXON engine, which is why JXON is
only *mostly* a superset of XML.

## Comments

Pretty straightforward. JXON and JXSD mark single-line comments with `//`, and multline comments with `/*`...`*/`.

## Multiline strings

JSON doesn't allow line breaks in the middle of a string, but JXON does. In general, whitespace before a line
break is preserved, whitespace after a line break is ignored, and if there is no whitespace before a line break,
a single space is inserted.

## Enforced schema consistency

Informally, most JSON found in the wild follows a consistent schema, but JXON formalizes 
that tendency, so the following is valid JSON but invalid JXON:

```
{
  "some_list": [
    3,
    "Hello",
    true
  ]
}
```

Arrays are really the only data type in JSON that can break schema consistency
(by having element of different types). The type of a JXON object is not simply "Object",
but is defined by its set of key->type mappings, so that the following is not valid JXON:

```
{
  "some_list": [
    {
      "name": "Conor Stuart Roe",
      "age": 23
    },
    {
      "name": "Orville Redenbacher"
    }
  ]
}
```

while the following is:

```
{
  "some_list": [
    {
      "name": "Conor Stuart Roe",
      "age": 23
    },
    {
      "name": "Orville Redenbacher",
      "age": 100
    }
  ]
}
```

`null` is considered to match any type, so that the following is still valid JXON:

```
{
  "some_list": [
    {
      "name": "Conor Stuart Roe",
      "age": 23
    },
    {
      "name": null,
      "age": 100
    }
  ]
}
```

In practice, most JSON follows these rules anyway, and formalizing them allows us to 
make stronger assumptions about JXON. However, some JSON out there does not follow these
rules, which is why JXON is only *mostly* a superset of JSON.

JXON schemas can be defined using a related format called JXSD (JXON Schema Definition).
For instance, the schema of the above object is, in JXSD format,

``` 
{
  "some_list": [{
    "name": String,
    "age": Integer
  }]
}
```

JXSD has five primitive types: `String`, `Integer`, `Float`, `Boolean`, and `XML`.
Although array and object members determine JXON schema, XML children do not; all
XML elements simply have `XML` type, so that the following is considered to have a
consistent JXON schema:

``` 
[
  {
    "some_xml": <p>Hi there!</p>
  },
  {
    "some_xml": <div>
      <p>There is a lot of content here.</p>
      <br/>
      <p>More than the last one, anyway.</p>
    </div>
  }
]
```

JXSD also allows for enumerated types, which must still be a set of all one type:

```
{
  "host": String,
  "port": Integer
  "path": String,
  "method": Enum("GET", "POST", "PUT", "DELETE"),
  "data": String
}
```

Currently, `Enum`s must be composed of primitives, but I'd like to implement enumerated array and
object types at some point.

## Variables, imports, and exports

JXON and JXSD don't have to simply consist of a single expression. They share a set of syntax for importing
and exporting based on JavaScript, as well as the ability to set variables.

A valid JXON or JXSD file contains the following sections in order, each of which is optional: 
imports, variables, default variable, and exports.

### Imports

There are several ways to import information from other files, but to understand these one first has to
be familiar with the JavaScript concepts of exports and default exports. Every file may *export* any number
of variables, which makes them available for import by other files. Variables exported in this way
retain their name in all subsequent imports unless explicitly renamed at import. In addition to these
named exports, every file may export one unnamed *default* variable, which had a different syntax for 
imports.

JXON/JXSD retains almost all JavaScript syntax for importing:

```
import test_schema, {School} from "./test.jxsd";
import * as names from "./names.jxon";
```

In the above, `test_schema` is the name being given `test.jxsd`'s default export, and `School` is one of the named
exports of `test.jxsd`. It is possible to import several named exports at once with the syntax
`import {foo, bar, baz} from example.jxon;`, and I'd like to implement the capability to rename named
exports with the syntax `import {foo as bar} from example.jxon`.

`*` is used to import an entire file as a variable, so that its named exports can then be accessed, e.g.:

```
import * as test from "./test.jxsd";

test.School
```

Another way to import a whole file is with *inline imports*, which don't enable access to named exports, but 
simply return a file's default export. For instance, `import("./test.jxsd")` returns the same value as
`test_schema` has in the earlier example. Inline imports are not used in the import section, but are
expressions evaluated in the next two sections:

### Variables

After imports, JXON and JXSD files have a section in which variables can be set. Variable assignments simply use 
`=` and don't require a semicolon. Variables names consist of alphanumeric characters and underscores, and 
can be used both as named exports and in other expressions:

```
School = {
  "name": String,
  "type": Enum("Primary", "Secondary", "Postsecondary")
}

MySchema = {
  "name": String,
  "age": Integer,
  "schools": [School],
  "intro": XML
}
```

In JXON, all variable assignments must evaluate to JXON values, not types. In JXSD, the opposite is true - all expressions
must evaluate to a type.

In JXSD, type annotations may also be added with `:` before the `=`. 

```
NCSSM: School = import("./ncssm.json")

me: test_schema = {
  "name": names.conor,
  "age": 23,
  "schools": [
    import("./ncssm.json"),
    {
      "name": "Haverford College",
      "type": "Postsecondary"
    }
  ],
  "intro": <div class="col-6 col-md-12">
    <h1>Conor Stuart Roe</h1>
    <br/>
    <p>Hi! my name is <b>Conor</b> and I like to boogie.</p>
    <p>What happens if there are<b>no spaces</b>around a child element?</p>
  </div>
}
```

These are both for ease of reading, and will be enforced as parse time - JXON parsing will fail if the 
expression a variable is assigned to does not match its type annotation, so the following will not parse:

```
NCSSM: School = {
  "name": "NCSSM",
  "something_else": 99.9
}
```

In JXON/JXSD, variable names are all final, and cannot be reassigned. This includes the name of any imports.

### Default variable

This section simply consists of an expression. JSON and XML files parsed as JXON are essentially regarded by the
JXON parser as only having this section. This section becomes the default export of the file.

### Exports

JXON and JXSD simply have one piece of syntax for changing the set of named exports, and another piece of syntax
for setting the default export:

```
export {foo, bar};
export default baz;
```

Neither statement is needed, and they don't interact. If no named export statement is included, all variables 
imported or defined in the file are available for import. If no default export statement is included,
then the default export comes from the default export section, or is simply null if there is no default
export section. 

If there is a default export section, but a different variable is named in a default export
statement, then the original default export is inaccessible:

```
foo = {
  "foo": "bar"
}

// this object is unavailable for import by other files
{
  "spam": "eggs"
}

export default foo;
```

# Using this library

`jxon` is available on PyPI, so to install it simply run:

``` 
pip install jxon
```

The API for this library is intended to be as analogous to the standard `json` library
as possible, though it includes a few more addons like the `jxsd` module.

### Reading a JXON file or string

```
import jxon

s = """
{
  "name": "Conor Stuart Roe",
  "some_xml": <p>Hello, World!</p>
}
"""

obj = jxon.loads(s)

with open("example.jxon", "r") as fh:
    obj2 = jxon.load(fh)
```

Like the `json` library, this package makes a function `loads` available for 
parsing a string as JXON, and a function `load` for parsing JXON from a file-like
object.

If you use imports beginning with `"./"` in your JXON, make sure to use `load`!
Otherwise, the parser has no way to determine the original directory of your file.

default export

### Exporting a JXON object to a file or string

```
from xml.etree import ElementTree as ET
import jxon

obj = {
    "name": "Conor Stuart Roe",
    "some_xml": ET.Element("p")
}

s = jxon.dumps(obj)

with open("example.jxon", "w") as fh:
    jxon.dump(obj, fh, indent=2, sort_keys=True)
```

Also like the `json` library, this package has a function `dumps` for exporting
a JXON object as a string, and `dump` for exporting into a file-like object.

Both `dump` and `dumps` permit two arguments, `indent` and `sort_keys`. If you don't
specify `indent`, then no newline characters will be put into your string/file. `indent`
can be set to an integer, which will then be how many spaces it inserts per level of
indentation. If `sort_keys` is not set, keys in JXON objects will be exported in their 
original order. If it is set to `True`, all keys in all objects will be in alphabetical
order.

no imports/whatev

### Checking the equality of JXON objects

If you want to check whether two JXON objects are equal, use `jxon_equal`

``` 
from jxon import jxon_equal

jxon_equal(5, 5)

jxon_equal({"name": "Alice"}, 5)
```

## Using JXSD

`jxon.jxsd` has functions `load`, `loads`, `dump`, and `dumps` which all
behave similarly to the `jxon` functions, but they deal with JXONType objects.

``` 
from jxon import jxsd

with open("example.jxsd", "r") as fh:
    example_schema = jxsd.load(fh)

type(example_schema)  # JXONType
```

### Checking the equality of JXON objects

JXON object validity is already checked when loading or dumping - syntax errors when
loading, objects not castable to JXON when dumping, and inconsistent array element
types when doing either, will all raise Python exceptions. However, if you want
to check whether some object has a valid JXON schema without loading or dumping,
you can use the function `jxsd.has_consistent_schema`

``` 
from jxon import jxsd

jxsd.has_consistent_schema([
    {
        "name": "Alice"
    },
    {
        "name": "Bob"
    }
])
```

### Parsing the type of a JXON object

Say you have a large JSON or JXON file and you just want to know its schema.
Look no further than `parse_type`:

``` 
import jxon
from jxon import jxsd

with open("bigdata.json", "r") as fh:
    obj = jxon.load(fh)

big_schema = jxsd.parse_type(obj)

with open("bigdata.jxsd", "w") as fh:
    jxsd.dump(big_schema, fh, indent=2)
```

Now you can take a peek at `bigdata.jxsd` to see what your JSON's schema is!

### Checking whether a JXON object is an instance of a JXONType

```
with open("bigdata2.json", "r") as fh:
    obj2 = jxon.load(fh)

big_schema.is_jxon_instance(obj2)
```

