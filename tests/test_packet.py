"""Tests for packet framing, CRC, and multi-message packets."""

from typing import Annotated

from pydantic import BaseModel

import pytest

from blueberry_serde import (
    serialize_message,
    deserialize_message,
    serialize_packet,
    deserialize_packet,
    empty_message,
    crc16_ccitt,
    PACKET_MAGIC,
    PACKET_HEADER_SIZE,
    BLUEBERRY_PORT,
)
from blueberry_serde.types import UInt32


class Simple(BaseModel):
    value: Annotated[int, UInt32]


def test_packet_starts_with_magic():
    msg = serialize_message(Simple(value=1), module_key=0, message_key=0)
    pkt = serialize_packet([msg])
    assert pkt[:4] == PACKET_MAGIC


def test_packet_is_multiple_of_4():
    msg = serialize_message(Simple(value=1), module_key=0, message_key=0)
    pkt = serialize_packet([msg])
    assert len(pkt) % 4 == 0


def test_packet_length_in_words():
    msg = serialize_message(Simple(value=1), module_key=0, message_key=0)
    pkt = serialize_packet([msg])
    import struct
    length_words = struct.unpack_from("<H", pkt, 4)[0]
    assert length_words * 4 == len(pkt)


def test_packet_crc_validates():
    msg = serialize_message(Simple(value=42), module_key=1, message_key=2)
    pkt = serialize_packet([msg])
    hdr, msgs = deserialize_packet(pkt)
    assert len(msgs) == 1


def test_packet_crc_mismatch_detected():
    msg = serialize_message(Simple(value=42), module_key=1, message_key=2)
    pkt = bytearray(serialize_packet([msg]))
    pkt[6] ^= 0xFF  # corrupt CRC
    with pytest.raises(ValueError, match="CRC mismatch"):
        deserialize_packet(pkt)


def test_packet_bad_magic_rejected():
    msg = serialize_message(Simple(value=42), module_key=1, message_key=2)
    pkt = bytearray(serialize_packet([msg]))
    pkt[0] = 0xFF  # corrupt magic
    with pytest.raises(ValueError, match="Invalid packet header"):
        deserialize_packet(pkt)


def test_empty_message_is_header_only():
    empty = empty_message(module_key=1, message_key=2)
    assert len(empty) == 8


def test_empty_message_in_packet():
    empty = empty_message(module_key=1, message_key=2)
    pkt = serialize_packet([empty])
    hdr, msgs = deserialize_packet(pkt)
    assert len(msgs) == 1
    assert len(msgs[0]) == 8


def test_multiple_messages_in_packet():
    msg1 = serialize_message(Simple(value=1), module_key=1, message_key=1)
    msg2 = serialize_message(Simple(value=2), module_key=2, message_key=2)
    pkt = serialize_packet([msg1, msg2])
    hdr, msgs = deserialize_packet(pkt)
    assert len(msgs) == 2
    _, s1 = deserialize_message(msgs[0], Simple)
    _, s2 = deserialize_message(msgs[1], Simple)
    assert s1.value == 1
    assert s2.value == 2


def test_blueberry_port_constant():
    assert BLUEBERRY_PORT == 16962
    assert BLUEBERRY_PORT == 0x4242


def test_packet_header_size_constant():
    assert PACKET_HEADER_SIZE == 8
