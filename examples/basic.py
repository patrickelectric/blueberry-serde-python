"""Basic example demonstrating Blueberry serialization with pydantic models.

Matches the Rust `examples/basic.rs` golden test vectors.
"""

from typing import Annotated

from pydantic import BaseModel

from blueberry_serde import (
    serialize_message,
    deserialize_message,
    serialize_packet,
    deserialize_packet,
    empty_message,
    crc16_ccitt,
    BLUEBERRY_PORT,
)
from blueberry_serde.types import UInt16, UInt32, Float32


class SensorReading(BaseModel):
    sensor_id: Annotated[int, UInt32]
    temperature: Annotated[float, Float32]
    humidity: Annotated[int, UInt16]
    alert_high: bool
    alert_low: bool


class DeviceStatusU16Readings(BaseModel):
    """DeviceStatus with u16 readings (matches Rust golden test)."""
    device_id: Annotated[int, UInt32]
    name: str
    readings: list[Annotated[int, UInt16]]
    online: bool
    calibrated: bool


class DeviceStatusU32Readings(BaseModel):
    """DeviceStatus with u32 readings (matches Rust basic example)."""
    device_id: Annotated[int, UInt32]
    name: str
    readings: list[Annotated[int, UInt32]]
    online: bool
    calibrated: bool


def hex_dump(data: bytes, label: str = "") -> None:
    if label:
        print(f"\n  {label}")
    for i in range(0, len(data), 16):
        hex_values = " ".join(f"{b:02x}" for b in data[i : i + 16])
        print(f"  {i:04x}: {hex_values}")


def main() -> None:
    print("=" * 60)
    print("  Blueberry Serde — Python / Pydantic Example")
    print(f"  Protocol port: {BLUEBERRY_PORT} (0x{BLUEBERRY_PORT:04X})")
    print("=" * 60)

    reading = SensorReading(
        sensor_id=42,
        temperature=23.5,
        humidity=65,
        alert_high=True,
        alert_low=False,
    )
    print(f"\nSensorReading: {reading}")

    msg = serialize_message(reading, module_key=0x01, message_key=0x42)
    pkt = serialize_packet([msg])
    hex_dump(pkt, "Packet bytes:")

    # Verify CRC
    pkt_hdr, message_slices = deserialize_packet(pkt)
    print(f"  Packet length: {pkt_hdr.length_words} words, CRC: 0x{pkt_hdr.crc:04X}")

    hdr, rt = deserialize_message(message_slices[0], SensorReading)
    print(f"  Roundtrip: {rt}")

    device_u16 = DeviceStatusU16Readings(
        device_id=100,
        name="sensor-alpha",
        readings=[1023, 2047, 4095],
        online=True,
        calibrated=False,
    )
    print(f"\nDeviceStatus (u16 readings): {device_u16}")

    msg_u16 = serialize_message(device_u16, module_key=0x01, message_key=0x42)
    pkt_u16 = serialize_packet([msg_u16])
    hex_dump(pkt_u16, "Packet bytes:")

    pkt_hdr_u16, msgs_u16 = deserialize_packet(pkt_u16)
    hdr_u16, rt_u16 = deserialize_message(msgs_u16[0], DeviceStatusU16Readings)
    print(f"  Roundtrip: {rt_u16}")

    device_u32 = DeviceStatusU32Readings(
        device_id=100,
        name="sensor-alpha",
        readings=[1023, 2047, 4095],
        online=True,
        calibrated=False,
    )
    print(f"\nDeviceStatus (u32 readings): {device_u32}")

    msg_u32 = serialize_message(device_u32, module_key=0x01, message_key=0x42)
    pkt_u32 = serialize_packet([msg_u32])
    hex_dump(pkt_u32, "Packet bytes:")

    pkt_hdr_u32, msgs_u32 = deserialize_packet(pkt_u32)
    hdr_u32, rt_u32 = deserialize_message(msgs_u32[0], DeviceStatusU32Readings)
    print(f"  Roundtrip: {rt_u32}")

    print("\nEmpty message (request-response mode):")
    empty = empty_message(module_key=0x01, message_key=0x42)
    pkt_empty = serialize_packet([empty])
    hex_dump(pkt_empty, "Packet bytes:")

    print("\nMultiple messages in one packet:")
    msg1 = serialize_message(reading, module_key=0x01, message_key=0x42)
    msg2 = serialize_message(device_u16, module_key=0x01, message_key=0x42)
    pkt_multi = serialize_packet([msg1, msg2])
    hex_dump(pkt_multi, "Packet bytes:")

    pkt_hdr_m, msgs = deserialize_packet(pkt_multi)
    print(f"  Packet has {len(msgs)} messages, {pkt_hdr_m.length_words} words")


if __name__ == "__main__":
    main()
