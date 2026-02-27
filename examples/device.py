"""Communicate with a real Blueberry device over serial.

Sends requests for IdMessage, VersionMessage, and WhosThereMessage
and prints the decoded responses.
"""

import struct
from enum import IntEnum
from typing import Annotated, Type, TypeVar

import serial
from pydantic import BaseModel

from blueberry_serde import (
    PACKET_HEADER_SIZE,
    PACKET_MAGIC,
    deserialize_message,
    deserialize_packet,
    empty_message,
    serialize_packet,
)
from blueberry_serde.types import UInt8, UInt16, UInt32, Float32

T = TypeVar("T", bound=BaseModel)

class IdMessage(BaseModel):
    id: Annotated[int, UInt32]

    def __str__(self) -> str:
        return f"Device ID: {self.id} (0x{self.id:08X})"


class HwType(IntEnum):
    UNDEFINED = 65535
    SFDQ = 0
    BLUE_SERVO = 1
    LUMEN = 2
    NUCLEO = 3
    BLUE_ESC = 4
    GIGABOARD = 5
    BLUE_BRIDGE = 6


class McuType(IntEnum):
    UNDEFINED = 255
    STM32F446 = 1
    STM32H563 = 2
    STM32H573 = 3
    STM32G071 = 4


class VersionMessage(BaseModel):
    firmwareVersion: Annotated[int, UInt32]
    hardwareRev: Annotated[int, UInt8]
    mcuType: Annotated[int, UInt8]
    hardwareType: Annotated[int, UInt16]

    def __str__(self) -> str:
        try:
            hw = HwType(self.hardwareType).name
        except ValueError:
            hw = f"UNKNOWN({self.hardwareType})"
        try:
            mcu = McuType(self.mcuType).name
        except ValueError:
            mcu = f"UNKNOWN({self.mcuType})"
        return (
            f"Firmware: {self.firmwareVersion} (0x{self.firmwareVersion:08X})\n"
            f"HW Rev:   {self.hardwareRev}\n"
            f"HW Type:  {hw}\n"
            f"MCU Type: {mcu}"
        )


class WhosThereMessage(BaseModel):
    def __str__(self) -> str:
        return "WhosThereMessage"


class BlueberrySerial:
    """Blueberry protocol over a serial port."""

    def __init__(self, port: str = "/dev/ttyACM0", baudrate: int = 115200, timeout: float = 2.0):
        print(f"Opening {port} @ {baudrate} baud...")
        self.port = serial.Serial(port, baudrate, timeout=timeout)

    def close(self) -> None:
        self.port.close()

    def __enter__(self) -> "BlueberrySerial":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def send_request(self, module_key: int, message_key: int) -> None:
        """Send an empty-message request packet."""
        msg = empty_message(module_key=module_key, message_key=message_key)
        pkt = serialize_packet([msg])
        self.port.write(pkt)
        self.port.flush()

    def receive_packet(self) -> bytes | None:
        """Read a complete Blueberry packet from the serial port.

        Scans for the 'Blue' magic, reads the 8-byte header, then reads the
        remaining payload based on the length field.  Returns None on timeout.
        """
        ring = bytearray(4)
        while True:
            b = self.port.read(1)
            if not b:
                return None
            ring.pop(0)
            ring.append(b[0])
            if bytes(ring) == PACKET_MAGIC:
                break

        header_tail = self.port.read(4)
        if len(header_tail) < 4:
            return None

        length_words = struct.unpack_from("<H", header_tail, 0)[0]
        payload_size = length_words * 4 - PACKET_HEADER_SIZE
        if payload_size < 0:
            return None

        payload = self.port.read(payload_size)
        if len(payload) < payload_size:
            return None

        return PACKET_MAGIC + header_tail + payload

    def request(self, model_type: Type[T], module_key: int, message_key: int) -> T | None:
        """Send a request and return the decoded response model, or None on timeout."""
        self.send_request(module_key, message_key)
        raw = self.receive_packet()
        if raw is None:
            return None

        _, messages = deserialize_packet(raw)
        if not messages:
            return None

        _hdr, msg = deserialize_message(messages[0], model_type)
        return msg


REQUESTS: list[tuple[type, int, int]] = [
    # Type, Module Key, Message Key
    (IdMessage,        0x4242, 0x0000),
    (VersionMessage,   0x4242, 0x0002),
    (WhosThereMessage, 0x4242, 0x0003),
]


def main() -> None:
    with BlueberrySerial("/dev/ttyACM0", 115200) as bus:
        for model_type, module_key, message_key in REQUESTS:
            print(f"\nRequesting: {model_type.__name__} (module=0x{module_key:04X} msg=0x{message_key:04X})")
            msg = bus.request(model_type, module_key, message_key)
            if msg is None:
                print("  (no response)")
                continue
            print(msg)


if __name__ == "__main__":
    main()
