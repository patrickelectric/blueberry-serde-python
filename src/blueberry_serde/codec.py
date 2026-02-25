"""Top-level serialize/deserialize functions for messages and packets."""

from __future__ import annotations

from typing import Type, TypeVar

from pydantic import BaseModel

from blueberry_serde.constants import HEADER_FIELD_COUNT, HEADER_SIZE, PACKET_HEADER_SIZE
from blueberry_serde.crc import crc16_ccitt
from blueberry_serde.deserializer import Deserializer
from blueberry_serde.header import MessageHeader, PacketHeader
from blueberry_serde.serializer import Serializer

T = TypeVar("T", bound=BaseModel)


def serialize(model: BaseModel) -> bytes:
    """Serialize a pydantic model to raw bytes (no message header)."""
    ser = Serializer()
    ser.serialize_model(model)
    return bytes(ser.finalize())


def deserialize(data: bytes | bytearray, model_type: Type[T]) -> T:
    """Deserialize raw bytes into a pydantic model (no message header)."""
    de = Deserializer(data)
    return de.deserialize_model(model_type)


def serialize_message(model: BaseModel, module_key: int, message_key: int) -> bytes:
    """Serialize a pydantic model with a Blueberry message header."""
    ser = Serializer()
    ser.set_base_offset(HEADER_SIZE)
    ser.serialize_model(model)
    field_count = ser.field_count
    body = ser.finalize()

    total_bytes = HEADER_SIZE + len(body)
    padded_bytes = (total_bytes + 3) & ~3
    length_words = padded_bytes // 4
    max_ordinal = field_count + HEADER_FIELD_COUNT - 1

    header = MessageHeader(
        module_key=module_key,
        message_key=message_key,
        length=length_words,
        max_ordinal=max_ordinal,
        tbd=0,
    )

    result = bytearray(padded_bytes)
    header.encode_into(result, 0)
    result[HEADER_SIZE : HEADER_SIZE + len(body)] = body
    return bytes(result)


def deserialize_message(data: bytes | bytearray, model_type: Type[T]) -> tuple[MessageHeader, T]:
    """Deserialize bytes with a message header into (header, model)."""
    header = MessageHeader.decode(data)
    if header is None:
        raise ValueError("Invalid message header")
    message_byte_len = header.length * 4

    de = Deserializer.with_message_context(data, HEADER_SIZE, message_byte_len)
    model = de.deserialize_model(model_type)
    return header, model


def empty_message(module_key: int, message_key: int) -> bytes:
    """Create an empty message (header only) for request-response."""
    header = MessageHeader(
        module_key=module_key,
        message_key=message_key,
        length=HEADER_SIZE // 4,
        max_ordinal=HEADER_FIELD_COUNT - 1,
        tbd=0,
    )
    return header.encode()


def serialize_packet(messages: list[bytes | bytearray]) -> bytes:
    """Pack one or more serialized messages into a Blueberry packet."""
    message_data = bytearray()
    for msg in messages:
        message_data.extend(msg)

    total_bytes = PACKET_HEADER_SIZE + len(message_data)
    padded_bytes = (total_bytes + 3) & ~3
    length_words = padded_bytes // 4

    # Pad message data
    if len(message_data) < padded_bytes - PACKET_HEADER_SIZE:
        message_data.extend(b"\x00" * (padded_bytes - PACKET_HEADER_SIZE - len(message_data)))

    crc = crc16_ccitt(bytes(message_data))
    pkt_header = PacketHeader(length_words=length_words, crc=crc)

    result = bytearray(pkt_header.encode())
    result.extend(message_data)
    return bytes(result)


def deserialize_packet(data: bytes | bytearray) -> tuple[PacketHeader, list[bytes]]:
    """Parse a packet, validate CRC, return (header, list of message byte slices)."""
    pkt_header = PacketHeader.decode(data)
    if pkt_header is None:
        raise ValueError("Invalid packet header (missing or bad magic)")

    total_bytes = pkt_header.length_words * 4
    if len(data) < total_bytes:
        raise ValueError("Unexpected EOF: packet data too short")

    message_data = data[PACKET_HEADER_SIZE:total_bytes]
    expected_crc = crc16_ccitt(bytes(message_data))
    if pkt_header.crc != expected_crc:
        raise ValueError(
            f"CRC mismatch: expected 0x{expected_crc:04X}, got 0x{pkt_header.crc:04X}"
        )

    messages: list[bytes] = []
    offset = PACKET_HEADER_SIZE
    while offset + HEADER_SIZE <= total_bytes:
        msg_header = MessageHeader.decode(data, offset)
        if msg_header is None:
            break
        msg_byte_len = msg_header.length * 4
        if msg_byte_len < HEADER_SIZE:
            break
        msg_end = offset + msg_byte_len
        if msg_end > total_bytes:
            raise ValueError("Unexpected EOF: message extends beyond packet")
        messages.append(bytes(data[offset:msg_end]))
        offset = msg_end

    return pkt_header, messages
