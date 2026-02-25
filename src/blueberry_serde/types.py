"""Type annotation helpers for mapping Python/pydantic types to wire types."""

from __future__ import annotations

import sys
from enum import IntEnum
from typing import Any, get_args, get_origin

if sys.version_info >= (3, 10):
    from types import UnionType
else:
    UnionType = None

from pydantic import BaseModel


def is_list_type(annotation: Any) -> bool:
    return get_origin(annotation) is list


def list_element_type(annotation: Any) -> Any:
    args = get_args(annotation)
    return args[0] if args else Any


def is_pydantic_model(tp: Any) -> bool:
    try:
        return isinstance(tp, type) and issubclass(tp, BaseModel)
    except TypeError:
        return False


def is_int_enum(tp: Any) -> bool:
    try:
        return isinstance(tp, type) and issubclass(tp, IntEnum)
    except TypeError:
        return False


# Maps Python type annotations to (struct format char, byte size).
# Uses little-endian packing.
PRIMITIVE_FORMATS: dict[Any, tuple[str, int]] = {
    int: ("<i", 4),    # default int → i32
    float: ("<d", 8),  # default float → f64 (Python float is always 64-bit)
    bool: ("?", 1),    # handled specially via bit-packing
}

# Extended type annotations for explicit wire sizes.
# Users annotate fields like:  value: Annotated[int, UInt16]


class WireType:
    """Marker for explicit wire type annotation."""

    def __init__(self, fmt: str, size: int):
        self.fmt = fmt
        self.size = size


UInt8 = WireType("<B", 1)
Int8 = WireType("<b", 1)
UInt16 = WireType("<H", 2)
Int16 = WireType("<h", 2)
UInt32 = WireType("<I", 4)
Int32 = WireType("<i", 4)
UInt64 = WireType("<Q", 8)
Int64 = WireType("<q", 8)
Float32 = WireType("<f", 4)
Float64 = WireType("<d", 8)


def get_wire_type(annotation: Any) -> WireType | None:
    """Extract WireType from Annotated[int, UInt16] style annotations."""
    args = get_args(annotation)
    for arg in args:
        if isinstance(arg, WireType):
            return arg
    return None


def resolve_wire_format(annotation: Any) -> tuple[str, int]:
    """Resolve a field annotation to (struct_format, byte_size).

    Returns the format for a primitive type, or raises for compound types.
    """
    wt = get_wire_type(annotation)
    if wt is not None:
        return wt.fmt, wt.size

    origin = get_origin(annotation)
    if origin is not None:
        # Annotated without WireType, or other generic — unwrap
        args = get_args(annotation)
        if args:
            base = args[0]
            if base in PRIMITIVE_FORMATS:
                return PRIMITIVE_FORMATS[base]

    if annotation is bool:
        return "?", 1
    if annotation is int:
        return "<I", 4  # default: u32
    if annotation is float:
        return "<f", 4  # default: f32

    raise TypeError(f"Cannot resolve wire format for {annotation}")
