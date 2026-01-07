# vesc-ble-can

`vesc-ble-can` is a Python library and CLI for communicating with **VESC Express**
devices over **BLE (Nordic UART Service)** and forwarding commands over **CAN**
to VESC motor controllers.

It is designed to be:
- clean and reusable as a **library**
- convenient as an **interactive CLI**
- suitable for **testing, diagnostics, and tooling**

---

## Features

- 🔍 BLE discovery (macOS / Linux)
- 🔁 BLE ↔ CAN bridge via VESC Express
- 📡 CAN node discovery (`COMM_FW_VERSION`)
- 📊 Telemetry polling (`COMM_GET_VALUES`)
- 🎛 Custom application data (`COMM_CUSTOM_APP_DATA`) over CAN
- ⌨️ Interactive CLI with instant keypress input (no Enter required)
- 🧩 Clean separation of protocol, transport, and application layers
- ⚙️ Async-first design (Python ≥ 3.9)

---

## Installation

### From PyPI (recommended)

```bash
pip install vesc-ble-can
```

### Editable install (for development)
#### Use this if you are developing or modifying the library.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -U pip
pip install -e .
```

### CLI Usage
#### Basic usage
```bash
vesc-ble-can \
  --name STAR-EXP \
  --scan-seconds 10 \
  --can-start 1 \
  --can-end 50 \
  --interval 0.5
```

This will:  
Discover the BLE device  
Query local firmware  
Scan the CAN bus for nodes  
Start periodic telemetry polling  
  
Keyboard controls (CLI)  
Key	Action  
0–9	Send COMM_CUSTOM_APP_DATA over CAN  
q	Quit  
  
Commands are sent immediately on key press  
Numeric keys map directly to payload values:  
0 → 0x00  
1 → 0x01  
2 → 0x02  
…  
  
  
  
### Run as module (optional)
#### Useful for debugging or running directly from source.
```bash
python -m vesc_ble_can.cli \
  --name STAR-EXP
```


### Python API Example
#### Minimal example showing how to use the library directly.
```bash
import asyncio
from vesc_ble_can import VescBleCanClient

async def main():
    client = VescBleCanClient(
        target_name="STAR-EXP",
        scan_seconds=10.0,
    )

    await client.connect()
    print("Connected")

    # Optional: local firmware sanity check
    fw = await client.local_fw_info(timeout_s=1.0)
    if fw:
        print(
            f"FW {fw.fwVersionMajor}.{fw.fwVersionMinor} | "
            f"HW {fw.hardwareName} | UUID {fw.uuid}"
        )

    # Discover CAN nodes
    nodes = await client.discover_can_nodes(
        can_start=1,
        can_end=50,
    )

    print("CAN nodes:", sorted(nodes.keys()))

    # Start telemetry polling
    await client.start_polling_get_values(
        can_ids=sorted(nodes.keys()),
        interval_s=0.5,
    )

    while True:
        vals = await client.get_next_values()
        if not vals:
            continue

        print(
            f"VESC {vals['vescId']:3d} | "
            f"Vin={vals['vIn']:.1f}V | "
            f"RPM={vals['rpm']:.0f} | "
            f"Iq={vals['iq']:.2f}A | "
            f"Id={vals['id']:.2f}A | "
            f"Tmos={vals['tempMos']:.1f}C | "
            f"Tmot={vals['tempMotor']:.1f}C | "
            f"Fault={vals['faultName']}"
        )

asyncio.run(main())
```

### Supported Platforms  
macOS (tested)  
Linux (tested)  
Windows (BLE support depends on system drivers and BLE stack)  

### Notes  
  
This library assumes VESC Express is acting as the BLE ↔ CAN gateway.  
All CAN commands are forwarded using COMM_FORWARD_CAN.  
The meaning of custom application data depends on the firmware running on the CAN node.  
Designed for tooling, diagnostics, and integration, not real-time motor control loops.  
