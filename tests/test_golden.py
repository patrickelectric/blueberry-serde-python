"""Golden tests matching the Rust golden byte vectors from tests/packets.rs."""

from typing import Annotated

from pydantic import BaseModel

from blueberry_serde import (
    serialize_message,
    serialize_packet,
    deserialize_message,
    deserialize_packet,
    crc16_ccitt,
)
from blueberry_serde.types import UInt16, UInt32, Float32


# ── Models matching the Rust test structs ─────────────────────────────


class SensorReading(BaseModel):
    sensor_id: Annotated[int, UInt32]
    temperature: Annotated[float, Float32]
    humidity: Annotated[int, UInt16]
    alert_high: bool
    alert_low: bool


class DeviceStatusU16Readings(BaseModel):
    device_id: Annotated[int, UInt32]
    name: str
    readings: list[Annotated[int, UInt16]]
    online: bool
    calibrated: bool


# ── Golden byte vectors ──────────────────────────────────────────────

SENSOR_READING_PACKET = bytes(
    [
        0x42, 0x6C, 0x75, 0x65, 0x07, 0x00, 0xFF, 0x9B,
        0x42, 0x00, 0x01, 0x00, 0x05, 0x00, 0x07, 0x00,
        0x2A, 0x00, 0x00, 0x00, 0x00, 0x00, 0xBC, 0x41,
        0x41, 0x00, 0x01, 0x00,
    ]
)

DEVICE_STATUS_PACKET = bytes(
    [
        0x42, 0x6C, 0x75, 0x65, 0x0E, 0x00, 0x72, 0xF4,
        0x42, 0x00, 0x01, 0x00, 0x0C, 0x00, 0x07, 0x00,
        0x64, 0x00, 0x00, 0x00, 0x14, 0x00, 0x24, 0x00,
        0x02, 0x00, 0x01, 0x00, 0x0C, 0x00, 0x00, 0x00,
        0x73, 0x65, 0x6E, 0x73, 0x6F, 0x72, 0x2D, 0x61,
        0x6C, 0x70, 0x68, 0x61, 0x03, 0x00, 0x00, 0x00,
        0xFF, 0x03, 0xFF, 0x07, 0xFF, 0x0F, 0x00, 0x00,
    ]
)


# ── Tests ─────────────────────────────────────────────────────────────


def test_sensor_reading_packet_matches_expected_wire_bytes():
    reading = SensorReading(
        sensor_id=42,
        temperature=23.5,
        humidity=65,
        alert_high=True,
        alert_low=False,
    )
    msg = serialize_message(reading, module_key=0x01, message_key=0x42)
    pkt = serialize_packet([msg])

    assert pkt == SENSOR_READING_PACKET, _diff(SENSOR_READING_PACKET, pkt)


def test_device_status_packet_matches_expected_wire_bytes():
    device = DeviceStatusU16Readings(
        device_id=100,
        name="sensor-alpha",
        readings=[1023, 2047, 4095],
        online=True,
        calibrated=False,
    )
    msg = serialize_message(device, module_key=0x01, message_key=0x42)
    pkt = serialize_packet([msg])

    assert pkt == DEVICE_STATUS_PACKET, _diff(DEVICE_STATUS_PACKET, pkt)


def test_sensor_reading_roundtrip():
    pkt_hdr, msgs = deserialize_packet(SENSOR_READING_PACKET)
    assert len(msgs) == 1
    hdr, reading = deserialize_message(msgs[0], SensorReading)
    assert reading.sensor_id == 42
    assert reading.temperature == 23.5
    assert reading.humidity == 65
    assert reading.alert_high is True
    assert reading.alert_low is False


def test_device_status_roundtrip():
    pkt_hdr, msgs = deserialize_packet(DEVICE_STATUS_PACKET)
    assert len(msgs) == 1
    hdr, device = deserialize_message(msgs[0], DeviceStatusU16Readings)
    assert device.device_id == 100
    assert device.name == "sensor-alpha"
    assert device.readings == [1023, 2047, 4095]
    assert device.online is True
    assert device.calibrated is False


def test_crc16_ccitt_sensor():
    payload = SENSOR_READING_PACKET[8:]
    expected_crc = int.from_bytes(SENSOR_READING_PACKET[6:8], "little")
    assert crc16_ccitt(payload) == expected_crc


def test_crc16_ccitt_device():
    payload = DEVICE_STATUS_PACKET[8:]
    expected_crc = int.from_bytes(DEVICE_STATUS_PACKET[6:8], "little")
    assert crc16_ccitt(payload) == expected_crc


# ── Helpers ───────────────────────────────────────────────────────────


def _diff(expected: bytes, actual: bytes) -> str:
    lines = ["Byte mismatch:"]
    max_len = max(len(expected), len(actual))
    for i in range(max_len):
        e = f"0x{expected[i]:02X}" if i < len(expected) else "---"
        a = f"0x{actual[i]:02X}" if i < len(actual) else "---"
        marker = " <<" if e != a else ""
        lines.append(f"  [{i:3d}] expected={e}  actual={a}{marker}")
    lines.append(f"  expected len={len(expected)}, actual len={len(actual)}")
    return "\n".join(lines)
