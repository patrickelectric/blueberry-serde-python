"""Serializer: pydantic model → Blueberry wire bytes."""

from __future__ import annotations

import struct
from typing import Any, get_args, get_origin

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


class Serializer:
    """Writes values into a bytearray using the Blueberry wire format."""

    def __init__(self) -> None:
        self.buf = bytearray()
        self.pos = 0
        self.seq_data_blocks: list[bytearray] = []
        self.seq_fixups: list[tuple[int, int]] = []
        self.bool_bit_pos = 0
        self.bool_byte_offset: int | None = None
        self.in_seq_data = False
        self.field_count = 0
        self.base_offset = 0

    def set_base_offset(self, offset: int) -> None:
        self.base_offset = offset


    @staticmethod
    def _pad_block(block: bytearray) -> None:
        padded = (len(block) + 3) & ~3
        if len(block) < padded:
            block.extend(b"\x00" * (padded - len(block)))

    def finalize(self) -> bytearray:
        self._flush_bools()

        if self.seq_data_blocks:
            body_padded = (len(self.buf) + 3) & ~3
            if len(self.buf) < body_padded:
                self.buf.extend(b"\x00" * (body_padded - len(self.buf)))
                self.pos = body_padded

        body_len = len(self.buf)
        data_offset = self.base_offset + body_len

        for header_offset, block_idx in self.seq_fixups:
            block = self.seq_data_blocks[block_idx]
            struct.pack_into("<H", self.buf, header_offset, data_offset)
            data_offset += len(block)

        for block in self.seq_data_blocks:
            self.buf.extend(block)

        return self.buf


    def _write_padding(self, size: int) -> None:
        if self.in_seq_data or size <= 1:
            return
        align = 4 if size >= 8 else size
        rem = self.pos % align
        if rem:
            pad = align - rem
            self.buf.extend(b"\x00" * pad)
            self.pos += pad


    def _flush_bools(self) -> None:
        self.bool_bit_pos = 0
        self.bool_byte_offset = None

    def _write_bool(self, v: bool) -> None:
        if self.bool_byte_offset is not None:
            if v:
                self.buf[self.bool_byte_offset] |= 1 << self.bool_bit_pos
            self.bool_bit_pos += 1
            if self.bool_bit_pos >= 8:
                self.bool_bit_pos = 0
                self.bool_byte_offset = None
        else:
            self._write_padding(1)
            offset = len(self.buf)
            self.buf.append(1 if v else 0)
            self.pos += 1
            self.bool_bit_pos = 1
            self.bool_byte_offset = offset


    def _write_primitive(self, fmt: str, size: int, value: Any) -> None:
        self._flush_bools()
        self._write_padding(size)
        self.buf.extend(struct.pack(fmt, value))
        self.pos += size


    def _write_string(self, value: str) -> None:
        encoded = value.encode("utf-8")
        self._flush_bools()
        self._write_padding(2)
        header_offset = len(self.buf)
        self.buf.extend(b"\x00\x00")
        self.pos += 2

        block = bytearray(struct.pack("<I", len(encoded)))
        block.extend(encoded)
        self._pad_block(block)

        block_idx = len(self.seq_data_blocks)
        self.seq_data_blocks.append(block)
        self.seq_fixups.append((header_offset, block_idx))


    def _write_sequence(self, values: list, elem_annotation: Any) -> None:
        self._flush_bools()
        self._write_padding(2)
        header_offset = len(self.buf)
        self.buf.extend(b"\x00\x00\x00\x00")
        self.pos += 4

        block = bytearray()
        first_elem_size: int | None = None

        for val in values:
            start = len(block)
            self._serialize_value_into_block(block, val, elem_annotation)
            if first_elem_size is None:
                first_elem_size = len(block) - start

        count_buf = struct.pack("<I", len(values))
        block = bytearray(count_buf) + block
        self._pad_block(block)

        elem_byte_len = first_elem_size or 0
        struct.pack_into("<H", self.buf, header_offset + 2, elem_byte_len)

        block_idx = len(self.seq_data_blocks)
        self.seq_data_blocks.append(block)
        self.seq_fixups.append((header_offset, block_idx))

    def _serialize_value_into_block(self, block: bytearray, value: Any, annotation: Any) -> None:
        """Serialize a single value into a data block (no alignment padding)."""
        if isinstance(annotation, WireType):
            block.extend(struct.pack(annotation.fmt, value))
        elif is_pydantic_model(annotation):
            self._serialize_model_into_block(block, value, annotation)
        elif annotation is bool or isinstance(value, bool):
            block.append(1 if value else 0)
        else:
            fmt, size = _resolve_primitive(annotation)
            block.extend(struct.pack(fmt, value))

    def _serialize_model_into_block(self, block: bytearray, model: BaseModel, model_type: type) -> None:
        """Serialize a pydantic model into a data block (packed, no alignment)."""
        for field_name, field_info in model_type.model_fields.items():
            value = getattr(model, field_name)
            annotation = _effective_annotation(field_info)
            self._serialize_value_into_block(block, value, annotation)


    def serialize_model(self, model: BaseModel) -> None:
        for field_name, field_info in type(model).model_fields.items():
            self.field_count += 1
            value = getattr(model, field_name)
            annotation = _effective_annotation(field_info)
            self._serialize_field(value, annotation)

    def _serialize_field(self, value: Any, annotation: Any) -> None:
        if isinstance(annotation, WireType):
            self._write_primitive(annotation.fmt, annotation.size, value)
        elif annotation is bool or (isinstance(value, bool) and not is_int_enum(type(value))):
            self._write_bool(value)
        elif annotation is str or isinstance(value, str):
            self._write_string(value)
        elif is_list_type(annotation):
            elem_type = list_element_type(annotation)
            self._write_sequence(value, elem_type)
        elif is_pydantic_model(annotation):
            nested = value
            for fn, fi in annotation.model_fields.items():
                self.field_count += 1
                self._serialize_field(getattr(nested, fn), _effective_annotation(fi))
        elif is_int_enum(type(value)):
            self._flush_bools()
            self._write_padding(4)
            self.buf.extend(struct.pack("<I", int(value)))
            self.pos += 4
        else:
            fmt, size = _resolve_primitive(annotation)
            self._write_primitive(fmt, size, value)


def _resolve_primitive(annotation: Any) -> tuple[str, int]:
    """Resolve annotation to (struct_format, byte_size)."""
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
