"""Deserializer: Blueberry wire bytes → pydantic model."""

from __future__ import annotations

import struct
from typing import Any, Type, TypeVar, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from blueberry_serde.types import (
    WireType,
    get_wire_type,
    is_list_type,
    is_pydantic_model,
    is_int_enum,
    list_element_type,
)


def _effective_annotation(field_info: FieldInfo) -> Any:
    """Get effective annotation, checking pydantic metadata for WireType."""
    for m in field_info.metadata:
        if isinstance(m, WireType):
            return m
    return field_info.annotation


T = TypeVar("T", bound=BaseModel)


class Deserializer:
    """Reads values from a byte buffer using the Blueberry wire format."""

    def __init__(self, data: bytes | bytearray, pos: int = 0) -> None:
        self.data = data
        self.pos = pos
        self.bool_bit_pos = 0
        self.bool_byte: int | None = None
        self.in_seq_data = False
        self.message_byte_len: int | None = None
        self.message_start = 0

    @classmethod
    def with_message_context(cls, data: bytes | bytearray, body_start: int, message_byte_len: int) -> Deserializer:
        d = cls(data, body_start)
        d.message_byte_len = message_byte_len
        return d


    def _read_padding(self, size: int) -> None:
        if self.in_seq_data or size <= 1:
            return
        align = 4 if size >= 8 else size
        rem = self.pos % align
        if rem:
            self.pos += align - rem


    def _flush_bools(self) -> None:
        self.bool_bit_pos = 0
        self.bool_byte = None

    def _read_bool(self) -> bool:
        if self.bool_byte is not None:
            v = bool((self.bool_byte >> self.bool_bit_pos) & 1)
            self.bool_bit_pos += 1
            if self.bool_bit_pos >= 8:
                self.bool_bit_pos = 0
                self.bool_byte = None
            return v
        else:
            self._read_padding(1)
            byte = self.data[self.pos]
            self.pos += 1
            v = bool(byte & 1)
            self.bool_bit_pos = 1
            self.bool_byte = byte
            return v


    def _read_primitive(self, fmt: str, size: int) -> Any:
        self._flush_bools()
        self._read_padding(size)
        (value,) = struct.unpack_from(fmt, self.data, self.pos)
        self.pos += size
        return value


    def _read_string(self) -> str:
        self._flush_bools()
        self._read_padding(2)
        index = struct.unpack_from("<H", self.data, self.pos)[0]
        self.pos += 2

        if index == 0:
            return ""

        data_start = self.message_start + index
        count = struct.unpack_from("<I", self.data, data_start)[0]
        bytes_start = data_start + 4
        return self.data[bytes_start : bytes_start + count].decode("utf-8")


    def _read_sequence(self, elem_annotation: Any) -> list:
        self._flush_bools()
        self._read_padding(2)
        index = struct.unpack_from("<H", self.data, self.pos)[0]
        elem_byte_len = struct.unpack_from("<H", self.data, self.pos + 2)[0]
        self.pos += 4

        if index == 0 and elem_byte_len == 0:
            return []

        data_start = self.message_start + index
        count = struct.unpack_from("<I", self.data, data_start)[0]
        elem_pos = data_start + 4

        result = []
        for _ in range(count):
            val, elem_pos = self._read_element_from_block(elem_pos, elem_annotation)
            result.append(val)

        return result

    def _read_element_from_block(self, pos: int, annotation: Any) -> tuple[Any, int]:
        """Read a single element from a data block at the given position."""
        if isinstance(annotation, WireType):
            (val,) = struct.unpack_from(annotation.fmt, self.data, pos)
            return val, pos + annotation.size
        elif is_pydantic_model(annotation):
            return self._read_model_from_block(pos, annotation)
        elif annotation is bool:
            v = bool(self.data[pos] & 1)
            return v, pos + 1
        else:
            fmt, size = _resolve_primitive(annotation)
            (val,) = struct.unpack_from(fmt, self.data, pos)
            return val, pos + size

    def _read_model_from_block(self, pos: int, model_type: type) -> tuple[Any, int]:
        """Read a pydantic model from a data block (packed, no alignment)."""
        kwargs = {}
        for field_name, field_info in model_type.model_fields.items():
            ann = _effective_annotation(field_info)
            val, pos = self._read_element_from_block(pos, ann)
            kwargs[field_name] = val
        return model_type(**kwargs), pos


    def _skip_to_message_end(self) -> None:
        if self.message_byte_len is not None:
            end = self.message_start + self.message_byte_len
            if self.pos < end:
                self.pos = end


    def deserialize_model(self, model_type: Type[T]) -> T:
        kwargs: dict[str, Any] = {}
        for field_name, field_info in model_type.model_fields.items():
            annotation = _effective_annotation(field_info)
            kwargs[field_name] = self._deserialize_field(annotation)
        self._skip_to_message_end()
        return model_type(**kwargs)

    def _deserialize_field(self, annotation: Any) -> Any:
        if isinstance(annotation, WireType):
            return self._read_primitive(annotation.fmt, annotation.size)
        elif annotation is bool:
            return self._read_bool()
        elif annotation is str:
            return self._read_string()
        elif is_list_type(annotation):
            elem_type = list_element_type(annotation)
            return self._read_sequence(elem_type)
        elif is_pydantic_model(annotation):
            return self.deserialize_model(annotation)
        else:
            fmt, size = _resolve_primitive(annotation)
            return self._read_primitive(fmt, size)


def _resolve_primitive(annotation: Any) -> tuple[str, int]:
    if isinstance(annotation, WireType):
        return annotation.fmt, annotation.size

    wt = get_wire_type(annotation)
    if wt is not None:
        return wt.fmt, wt.size

    origin = get_origin(annotation)
    if origin is not None:
        args = get_args(annotation)
        if args:
            return _resolve_primitive(args[0])

    if annotation is int:
        return "<I", 4
    if annotation is float:
        return "<d", 8
    if annotation is bool:
        return "?", 1

    raise TypeError(f"Cannot resolve wire format for {annotation}")
