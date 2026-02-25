"""Tests for primitive serialization, alignment, and bool packing."""

import struct
from typing import Annotated

from pydantic import BaseModel

from blueberry_serde import serialize, deserialize
from blueberry_serde.types import UInt8, UInt16, UInt32, Int32, UInt64, Float64


class TwoInts(BaseModel):
    a: Annotated[int, UInt32]
    b: Annotated[int, UInt32]


class MixedPrimitive(BaseModel):
    byte_val: Annotated[int, UInt8]
    short_val: Annotated[int, UInt16]
    int_val: Annotated[int, UInt32]


class BoolPack(BaseModel):
    a: bool
    b: bool
    c: bool
    x: Annotated[int, UInt16]
    d: bool


class AllBools(BaseModel):
    b0: bool
    b1: bool
    b2: bool
    b3: bool
    b4: bool
    b5: bool
    b6: bool
    b7: bool


def test_two_ints_roundtrip():
    m = TwoInts(a=1, b=2)
    data = serialize(m)
    assert len(data) == 8
    rt = deserialize(data, TwoInts)
    assert rt.a == 1
    assert rt.b == 2


def test_mixed_primitive_alignment():
    m = MixedPrimitive(byte_val=0xFF, short_val=0x1234, int_val=0xDEADBEEF)
    data = serialize(m)
    rt = deserialize(data, MixedPrimitive)
    assert rt.byte_val == 0xFF
    assert rt.short_val == 0x1234
    assert rt.int_val == 0xDEADBEEF


def test_bool_packing():
    m = BoolPack(a=True, b=False, c=True, x=0x1234, d=True)
    data = serialize(m)
    rt = deserialize(data, BoolPack)
    assert rt.a is True
    assert rt.b is False
    assert rt.c is True
    assert rt.x == 0x1234
    assert rt.d is True

    # First byte should be 0b00000101 = 5 (a=1, b=0, c=1 packed LSb first)
    assert data[0] == 0x05


def test_all_bools_pack_into_one_byte():
    m = AllBools(b0=True, b1=False, b2=True, b3=False, b4=True, b5=True, b6=False, b7=True)
    data = serialize(m)
    assert len(data) == 1
    # LSb first: b0=1, b1=0, b2=1, b3=0, b4=1, b5=1, b6=0, b7=1 = 0b10110101 = 0xB5
    assert data[0] == 0xB5
    rt = deserialize(data, AllBools)
    assert rt.b0 is True
    assert rt.b1 is False
    assert rt.b2 is True
    assert rt.b3 is False
    assert rt.b4 is True
    assert rt.b5 is True
    assert rt.b6 is False
    assert rt.b7 is True
