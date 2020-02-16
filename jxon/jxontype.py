from xml.etree import ElementTree as ET


class JXONSchemaValidityException(BaseException):
    pass


class JXONType:
    SIMPLE_TYPES = {int, float, bool, str, ET.Element}

    def __init__(self, jxon_type, subtype=None):
        if jxon_type in JXONType.SIMPLE_TYPES:
            if subtype is not None:
                raise ValueError("Subtype should not be supplied for simple type")

        elif jxon_type is list:
            if subtype is not None and type(subtype) is not JXONType:
                raise ValueError("Array subtype must be a JXON type")

        elif jxon_type is dict:
            if type(subtype) is not dict:
                raise ValueError("Object subtype must be a dictionary")
            for key, value in subtype.items():
                if value is not None and type(value) is not JXONType:
                    raise ValueError("Invalid object member type: " + repr(type(value)))

        elif jxon_type is set:
            if type(subtype) is not set:
                raise ValueError("Expected set subtype")
            member_types = [type(e) for e in subtype]
            if member_types[0] not in (int, float, str):
                raise ValueError("Invalid set member type: " + repr(member_types[0]))
            elif any(t is not member_types[0] for t in member_types):
                raise ValueError("Inconsistent Enum member types")

        else:
            raise ValueError("Invalid type: " + repr(jxon_type))

        self.jxon_type = jxon_type
        self.subtype = subtype

    def is_jxon_instance(self, obj, fill_null=False):
        if obj is None:
            return True

        if self.jxon_type in JXONType.SIMPLE_TYPES:
            return type(obj) is self.jxon_type

        elif self.jxon_type is list:
            if type(obj) is not list:
                return False

            if self.subtype is None:
                if not fill_null:
                    return True

                self.subtype = parse_type(obj[0])

            return all(self.subtype.is_jxon_instance(e) for e in obj)

        elif self.jxon_type is dict:
            if type(obj) is not dict:
                return False

            if set(self.subtype.keys()) != set(obj.keys()):
                return False

            for key, jxon_type in self.subtype.items():
                if jxon_type is None:
                    if fill_null:
                        self.subtype[key] = parse_type(obj[key])

                elif not jxon_type.is_jxon_instance(obj[key]):
                    return False

            return True

        elif self.jxon_type is set:
            return obj in self.subtype

        else:
            raise RuntimeError("??")


def parse_type(obj):
    if obj is None:
        return None

    elif type(obj) in JXONType.SIMPLE_TYPES:
        return JXONType(type(obj))

    elif type(obj) is list:
        if len(obj) == 0:
            return JXONType(list, None)

        jxon_type = parse_type(obj[0])
        if not all(jxon_type.is_jxon_instance(e) for e in obj):
            raise JXONSchemaValidityException("Inconsistent list element type")

        return JXONType(list, jxon_type)

    elif type(obj) is dict:
        d = {}
        for key, value in obj.items():
            jxon_type = parse_type(value)
            d[key] = jxon_type

        return JXONType(dict, d)

    else:
        raise JXONSchemaValidityException("Not parseable as JXON type: " + repr(type(obj)))


def has_consistent_schema(obj):
    try:
        parse_type(obj)
        return True
    except JXONSchemaValidityException:
        return False
