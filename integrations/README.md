
# Integrations

This directory contains **reference integrations** for `vesc-ble-can`
across firmware and UI layers.
  
These files are **not installed via pip** and are intended to be used
alongside the Python library.

---

## Architecture Overview
Python CLI / Script. 
|. 
| BLE (NUS). 
v. 
VESC Express (BLE ↔ CAN). 
|. 
| CAN. 
v. 
VESC Motor Controller (Lisp).  

The same command protocol is used by:  
- Python (`vesc-ble-can`). 
- VESC Tool QML UI. 
- VESC firmware (Lisp). 

---

## Command Protocol

Transport:
- `COMM_CUSTOM_APP_DATA`
- Forwarded over CAN via `COMM_FORWARD_CAN`

Payload:
- Length: **1 byte**
- Meaning defined by firmware. 

### Command Mapping

| Value | Action  |
|------:|---------|
| 0x00  | Stop    |
| 0x01  | Forward |
| 0x02  | Reverse |

This mapping is shared across **Python, QML, and Lisp**.

---

## VESC Lisp (Firmware)

Location:  
integrations/vesc_lisp/custom_cmd_listener.lisp. 

Purpose:
- Receives custom app data events
- Decodes single-byte commands
- Performs short-duration RPM control
- Restores previous app mode after execution

Notes:
- Uses `event-data-rx`
- Intended for CAN-connected VESC nodes
- Designed as a reference implementation

---

## QML (VESC Tool UI)

Location:  
integrations/qml/custom_cmd_panel.qml  

Purpose:
- Simple control panel for VESC Tool
- Sends custom app data via BLE
- Matches the same command protocol as Python and Lisp

Usage:
- Load into VESC Tool QML environment
- Use buttons to send commands instantly

---

## Compatibility Notes

- Requires VESC Express acting as BLE ↔ CAN gateway
- Firmware behavior depends on the Lisp script loaded
- UI and Python tools can be used independently or together

---

## Disclaimer

These integrations are provided as **examples**.
Review and adapt them before using in production systems.
