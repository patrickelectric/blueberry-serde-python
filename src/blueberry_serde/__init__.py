"""Blueberry binary wire format serialization for pydantic models."""

from blueberry_serde.codec import (
    serialize,
    deserialize,
    serialize_message,
    deserialize_message,
    serialize_packet,
    deserialize_packet,
    empty_message,
)
from blueberry_serde.header import MessageHeader, PacketHeader
from blueberry_serde.crc import crc16_ccitt
from blueberry_serde.constants import (
    PACKET_MAGIC,
    PACKET_HEADER_SIZE,
    HEADER_SIZE,
    HEADER_FIELD_COUNT,
    BLUEBERRY_PORT,
)

__all__ = [
    "serialize",
    "deserialize",
    "serialize_message",
    "deserialize_message",
    "serialize_packet",
    "deserialize_packet",
    "empty_message",
    "MessageHeader",
    "PacketHeader",
    "crc16_ccitt",
    "PACKET_MAGIC",
    "PACKET_HEADER_SIZE",
    "HEADER_SIZE",
    "HEADER_FIELD_COUNT",
    "BLUEBERRY_PORT",
]
