# blueberry-serde (Python)

Python implementation of the Blueberry binary wire format, compatible with pydantic models.

## Installation

```bash
uv sync
```

## Quick start

Define messages as pydantic models with explicit wire-type annotations:

```python
from typing import Annotated
from pydantic import BaseModel
from blueberry_serde import serialize_message, deserialize_message, serialize_packet, deserialize_packet
from blueberry_serde.types import UInt16, UInt32, Float32

class SensorReading(BaseModel):
    sensor_id: Annotated[int, UInt32]
    temperature: Annotated[float, Float32]
    humidity: Annotated[int, UInt16]
    alert_high: bool
    alert_low: bool

# Serialize
msg = serialize_message(SensorReading(sensor_id=42, temperature=23.5, humidity=65, alert_high=True, alert_low=False),
                        module_key=0x01, message_key=0x42)
pkt = serialize_packet([msg])

# Deserialize
pkt_hdr, message_slices = deserialize_packet(pkt)
hdr, reading = deserialize_message(message_slices[0], SensorReading)
```

See `examples/basic.py` for a full walkthrough:

```bash
uv run python examples/basic.py
```

## Wire types

Fields default to `int → u32` and `float → f32`. Use `Annotated` to override:

| Annotation | Wire type | Size |
|------------|-----------|------|
| `UInt8`    | u8        | 1    |
| `Int8`     | i8        | 1    |
| `UInt16`   | u16       | 2    |
| `Int16`    | i16       | 2    |
| `UInt32`   | u32       | 4    |
| `Int32`    | i32       | 4    |
| `UInt64`   | u64       | 8    |
| `Int64`    | i64       | 8    |
| `Float32`  | f32       | 4    |
| `Float64`  | f64       | 8    |

Consecutive `bool` fields are bit-packed into bytes (LSb first), matching the Rust implementation.

## Talking to a device over serial

Sync with the `examples` extra to pull in `pyserial`:

```bash
uv sync --extra examples
```

Then run the device example:

```bash
uv run python examples/device.py
```

This opens `/dev/ttyACM0` at 115200 baud and requests `IdMessage`, `VersionMessage`, and `WhosThereMessage` from a connected Blueberry device.

## Running tests

```bash
uv sync --extra dev
uv run pytest
```

## Requirements

- Python >= 3.10
- pydantic >= 2.0
