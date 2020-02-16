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
