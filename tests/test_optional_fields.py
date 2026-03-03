"""Tests for OptionalOrdinal field support (backward/forward compatibility)."""

from typing import Annotated

from pydantic import BaseModel

from blueberry_serde import (
    serialize_message,
    deserialize_message,
    OptionalOrdinal,
)
from blueberry_serde.types import UInt8, UInt32


SP_MODULE = 0x01
SP_MSG = 0x02


class SmallPotato(BaseModel):
    a: Annotated[int, UInt8]
    b: Annotated[int, UInt32]


class SmallPotatoV1Flat(BaseModel):
    a: Annotated[int, UInt8]
    c: Annotated[int, UInt8]
    b: Annotated[int, UInt32]


class SmallPotatoV2Flat(BaseModel):
    a: Annotated[int, UInt8]
    c: Annotated[int, UInt8]
    d: Annotated[int, UInt8]
    b: Annotated[int, UInt32]


class SmallPotatoV3Flat(BaseModel):
    a: Annotated[int, UInt8]
    c: Annotated[int, UInt8]
    d: Annotated[int, UInt8]
    e: Annotated[int, UInt8]
    b: Annotated[int, UInt32]


class SmallPotatoV4Flat(BaseModel):
    a: Annotated[int, UInt8]
    c: Annotated[int, UInt8]
    d: Annotated[int, UInt8]
    e: Annotated[int, UInt8]
    b: Annotated[int, UInt32]
    f: Annotated[int, UInt32]


class SmallPotatoOptional(BaseModel):
    a: Annotated[int, UInt8]
    c: Annotated[int | None, UInt8, OptionalOrdinal(3)] = None
    d: Annotated[int | None, UInt8, OptionalOrdinal(4)] = None
    e: Annotated[int | None, UInt8, OptionalOrdinal(5)] = None
    b: Annotated[int, UInt32]
    f: Annotated[int | None, UInt32, OptionalOrdinal(6)] = None


SP_GOLD_BASE = bytes([
    0x02, 0x00, 0x01, 0x00,  # header word 0: module_message_key
    0x04, 0x00, 0x04, 0x00,  # header word 1: length=4, max_ordinal=4, tbd=0
    0x01, 0x00, 0x00, 0x00,  # a=1 + 3 bytes alignment padding for b
    0x02, 0x00, 0x00, 0x00,  # b=2
])

SP_GOLD_V1 = bytes([
    0x02, 0x00, 0x01, 0x00,  # header word 0
    0x04, 0x00, 0x05, 0x00,  # header word 1: length=4, max_ordinal=5, tbd=0
    0x01, 0x03, 0x00, 0x00,  # a=1, c=3 + 2 bytes padding for b
    0x02, 0x00, 0x00, 0x00,  # b=2
])

SP_GOLD_V2 = bytes([
    0x02, 0x00, 0x01, 0x00,  # header word 0
    0x04, 0x00, 0x06, 0x00,  # header word 1: length=4, max_ordinal=6, tbd=0
    0x01, 0x03, 0x04, 0x00,  # a=1, c=3, d=4 + 1 byte padding for b
    0x02, 0x00, 0x00, 0x00,  # b=2
])

SP_GOLD_V3 = bytes([
    0x02, 0x00, 0x01, 0x00,  # header word 0
    0x04, 0x00, 0x07, 0x00,  # header word 1: length=4, max_ordinal=7, tbd=0
    0x01, 0x03, 0x04, 0x05,  # a=1, c=3, d=4, e=5 (fills gap exactly)
    0x02, 0x00, 0x00, 0x00,  # b=2
])

SP_GOLD_V4 = bytes([
    0x02, 0x00, 0x01, 0x00,  # header word 0
    0x05, 0x00, 0x08, 0x00,  # header word 1: length=5, max_ordinal=8, tbd=0
    0x01, 0x03, 0x04, 0x05,  # a=1, c=3, d=4, e=5
    0x02, 0x00, 0x00, 0x00,  # b=2
    0x06, 0x00, 0x00, 0x00,  # f=6
])


# -- Gold-wired serialization verification -----------------------------------

def test_sp_gold_base_serialize():
    val = SmallPotato(a=1, b=2)
    data = serialize_message(val, SP_MODULE, SP_MSG)
    assert data == SP_GOLD_BASE


def test_sp_gold_v1_serialize():
    val = SmallPotatoV1Flat(a=1, c=3, b=2)
    data = serialize_message(val, SP_MODULE, SP_MSG)
    assert data == SP_GOLD_V1


def test_sp_gold_v2_serialize():
    val = SmallPotatoV2Flat(a=1, c=3, d=4, b=2)
    data = serialize_message(val, SP_MODULE, SP_MSG)
    assert data == SP_GOLD_V2


def test_sp_gold_v3_serialize():
    val = SmallPotatoV3Flat(a=1, c=3, d=4, e=5, b=2)
    data = serialize_message(val, SP_MODULE, SP_MSG)
    assert data == SP_GOLD_V3


def test_sp_gold_v4_serialize():
    val = SmallPotatoV4Flat(a=1, c=3, d=4, e=5, b=2, f=6)
    data = serialize_message(val, SP_MODULE, SP_MSG)
    assert data == SP_GOLD_V4


def test_sp_v4_as_base():
    _, d = deserialize_message(SP_GOLD_V4, SmallPotato)
    assert d.a == 1
    assert d.b == 2


def test_sp_v4_as_v1():
    _, d = deserialize_message(SP_GOLD_V4, SmallPotatoV1Flat)
    assert d.a == 1
    assert d.c == 3
    assert d.b == 2


def test_sp_v4_as_v2():
    _, d = deserialize_message(SP_GOLD_V4, SmallPotatoV2Flat)
    assert d.a == 1
    assert d.c == 3
    assert d.d == 4
    assert d.b == 2


def test_sp_v4_as_v3():
    _, d = deserialize_message(SP_GOLD_V4, SmallPotatoV3Flat)
    assert d.a == 1
    assert d.c == 3
    assert d.d == 4
    assert d.e == 5
    assert d.b == 2


def test_sp_v3_as_base():
    _, d = deserialize_message(SP_GOLD_V3, SmallPotato)
    assert d.a == 1
    assert d.b == 2


def test_sp_base_roundtrip():
    val = SmallPotato(a=1, b=2)
    data = serialize_message(val, SP_MODULE, SP_MSG)
    _, d = deserialize_message(data, SmallPotato)
    assert d.a == val.a
    assert d.b == val.b


def test_sp_v1_roundtrip():
    val = SmallPotatoV1Flat(a=1, c=3, b=2)
    data = serialize_message(val, SP_MODULE, SP_MSG)
    _, d = deserialize_message(data, SmallPotatoV1Flat)
    assert d.a == val.a
    assert d.c == val.c
    assert d.b == val.b


def test_sp_v3_roundtrip():
    val = SmallPotatoV3Flat(a=1, c=3, d=4, e=5, b=2)
    data = serialize_message(val, SP_MODULE, SP_MSG)
    _, d = deserialize_message(data, SmallPotatoV3Flat)
    assert d == val


def test_sp_v4_roundtrip():
    val = SmallPotatoV4Flat(a=1, c=3, d=4, e=5, b=2, f=6)
    data = serialize_message(val, SP_MODULE, SP_MSG)
    _, d = deserialize_message(data, SmallPotatoV4Flat)
    assert d == val


def test_sp_optional_roundtrip():
    val = SmallPotatoOptional(a=1, c=3, d=4, e=5, b=2, f=6)
    data = serialize_message(val, SP_MODULE, SP_MSG)
    _, d = deserialize_message(data, SmallPotatoOptional)
    assert d.a == 1
    assert d.c == 3
    assert d.d == 4
    assert d.e == 5
    assert d.b == 2
    assert d.f == 6


def test_sp_optional_roundtrip_none():
    val = SmallPotatoOptional(a=1, b=2)
    data = serialize_message(val, SP_MODULE, SP_MSG)
    _, d = deserialize_message(data, SmallPotatoOptional)
    assert d.a == 1
    assert d.c is None
    assert d.d is None
    assert d.e is None
    assert d.b == 2
    assert d.f is None


def test_sp_optional_as_v4():
    _, d = deserialize_message(SP_GOLD_V4, SmallPotatoOptional)
    assert d.a == 1
    assert d.c == 3
    assert d.d == 4
    assert d.e == 5
    assert d.b == 2
    assert d.f == 6


def test_sp_optional_as_gold_base():
    _, d = deserialize_message(SP_GOLD_BASE, SmallPotatoOptional)
    assert d.a == 1
    assert d.b == 2
    assert d.c is None
    assert d.d is None
    assert d.e is None
    assert d.f is None


def test_sp_optional_serializes_as_gold_v4():
    """OptionalOrdinal with all-Some should produce the same bytes as V4Flat."""
    val = SmallPotatoOptional(a=1, c=3, d=4, e=5, b=2, f=6)
    data = serialize_message(val, SP_MODULE, SP_MSG)
    assert data == SP_GOLD_V4


def test_sp_optional_serializes_as_gold_base():
    """OptionalOrdinal with all-None should produce the same bytes as base."""
    val = SmallPotatoOptional(a=1, b=2)
    data = serialize_message(val, SP_MODULE, SP_MSG)
    assert data == SP_GOLD_BASE


def test_sp_optional_as_gold_v1():
    """Deserialize V1 gold wire as SmallPotatoOptional: c=Some, rest None."""
    _, d = deserialize_message(SP_GOLD_V1, SmallPotatoOptional)
    assert d.a == 1
    assert d.c == 3
    assert d.d is None
    assert d.e is None
    assert d.b == 2
    assert d.f is None


def test_sp_optional_as_gold_v2():
    """Deserialize V2 gold wire as SmallPotatoOptional: c,d=Some, rest None."""
    _, d = deserialize_message(SP_GOLD_V2, SmallPotatoOptional)
    assert d.a == 1
    assert d.c == 3
    assert d.d == 4
    assert d.e is None
    assert d.b == 2
    assert d.f is None


def test_sp_optional_as_gold_v3():
    """Deserialize V3 gold wire as SmallPotatoOptional: c,d,e=Some, f=None."""
    _, d = deserialize_message(SP_GOLD_V3, SmallPotatoOptional)
    assert d.a == 1
    assert d.c == 3
    assert d.d == 4
    assert d.e == 5
    assert d.b == 2
    assert d.f is None
