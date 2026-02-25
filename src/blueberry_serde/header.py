"""Message and packet header encoding/decoding."""

from __future__ import annotations

import struct
from dataclasses import dataclass

from blueberry_serde.constants import HEADER_SIZE, PACKET_HEADER_SIZE, PACKET_MAGIC


@dataclass
class MessageHeader:
    """8-byte message header.

    Wire layout (little-endian):
        Word 0: uint32 module_message_key (high=module_key, low=message_key)
        Word 1: uint16 length | uint8 max_ordinal | uint8 tbd
    """

    module_key: int
    message_key: int
    length: int  # total message length in 4-byte words
    max_ordinal: int
    tbd: int = 0

    def encode(self) -> bytes:
        module_message_key = ((self.module_key & 0xFFFF) << 16) | (self.message_key & 0xFFFF)
        return struct.pack("<IHBB", module_message_key, self.length, self.max_ordinal, self.tbd)

    def encode_into(self, buf: bytearray, offset: int = 0) -> None:
        module_message_key = ((self.module_key & 0xFFFF) << 16) | (self.message_key & 0xFFFF)
        struct.pack_into("<IHBB", buf, offset, module_message_key, self.length, self.max_ordinal, self.tbd)

    @classmethod
    def decode(cls, data: bytes | bytearray, offset: int = 0) -> MessageHeader | None:
        if len(data) - offset < HEADER_SIZE:
            return None
        module_message_key, length, max_ordinal, tbd = struct.unpack_from("<IHBB", data, offset)
        module_key = (module_message_key >> 16) & 0xFFFF
        message_key = module_message_key & 0xFFFF
        return cls(
            module_key=module_key,
            message_key=message_key,
            length=length,
            max_ordinal=max_ordinal,
            tbd=tbd,
        )


@dataclass
class PacketHeader:
    """8-byte packet header.

    Wire layout (little-endian):
        Bytes 0..4: Magic {'B','l','u','e'}
        Bytes 4..6: uint16 total packet length in 4-byte words
        Bytes 6..8: uint16 CRC-16-CCITT
    """

    length_words: int
    crc: int

    def encode(self) -> bytes:
        return PACKET_MAGIC + struct.pack("<HH", self.length_words, self.crc)

    @classmethod
    def decode(cls, data: bytes | bytearray, offset: int = 0) -> PacketHeader | None:
        if len(data) - offset < PACKET_HEADER_SIZE:
            return None
        if data[offset : offset + 4] != PACKET_MAGIC:
            return None
        length_words, crc = struct.unpack_from("<HH", data, offset + 4)
        return cls(length_words=length_words, crc=crc)
