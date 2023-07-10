

_tag_system = None
_tag_code = None

def InitMetaTag(system, code):
    global _tag_system, _tag_code

    _tag_system = system
    _tag_code = code


def MetaTag():
    return [{
            "system": _tag_system,
            "code": _tag_code
    }]
