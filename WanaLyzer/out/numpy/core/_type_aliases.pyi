from numpy import complexfloating as complexfloating, floating as floating, generic as generic, signedinteger as signedinteger, unsignedinteger as unsignedinteger
from typing import Any, TypedDict

class _SCTypes(TypedDict):
    int: list[type[signedinteger[Any]]]
    uint: list[type[unsignedinteger[Any]]]
    float: list[type[floating[Any]]]
    complex: list[type[complexfloating[Any, Any]]]
    others: list[type]

sctypeDict: dict[int | str, type[generic]]
sctypes: _SCTypes
