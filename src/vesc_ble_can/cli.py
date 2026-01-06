import argparse
import asyncio
from typing import List

from .client import VescBleCanClient

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="VESC Express BLE->CAN discovery + GET_VALUES polling")
    p.add_argument("--address", default=None, help="BLE address/identifier (macOS uses UUID-like address)")
    p.add_argument("--name", default="STAR-EXP", help="BLE advertised name (default: STAR-EXP)")
    p.add_argument("--scan-seconds", type=float, default=10.0, help="BLE scan duration")
    p.add_argument("--can-start", type=int, default=1, help="Start CAN ID (inclusive)")
    p.add_argument("--can-end", type=int, default=50, help="End CAN ID (inclusive)")
    p.add_argument("--interval", type=float, default=0.5, help="GET_VALUES polling interval in seconds")
    return p

async def _amain(args) -> int:
    c = VescBleCanClient(
    target_name=args.name,
    scan_seconds=args.scan_seconds,
    address=args.address,
    )

    try:
        await c.connect()
        info = await c.local_fw_info(timeout_s=1.0)
        if info:
            print(f"Local FW: {info.fwVersionMajor}.{info.fwVersionMinor} | HW: {info.hardwareName} | UUID: {info.uuid}")
        else:
            print("⚠️ Local FW: no response")

        print(f"\nDiscovering CAN IDs {args.can_start}..{args.can_end} ...")
        nodes = await c.discover_can_nodes(
            can_start=args.can_start,
            can_end=args.can_end,
        )

        if not nodes:
            print("❌ No CAN nodes found.")
            return 2

        print("\n=== CAN Summary ===")
        for cid in sorted(nodes.keys()):
            i = nodes[cid]
            print(f"CAN {cid:3d}: {i.hardwareName} | {i.fwVersionMajor}.{i.fwVersionMinor} | {i.uuid}")

        can_list: List[int] = sorted(nodes.keys())
        print(f"\nPolling COMM_GET_VALUES every {args.interval*1000:.0f} ms... (Ctrl+C to stop)\n")
        await c.start_polling_get_values(can_list, interval_s=args.interval)

        while True:
            vals = await c.get_next_values()
            if not vals:
                continue

            vesc_id = vals.get("vescId", -1)
            print(
                f"VESC {vesc_id:3d}: "
                f"Vin={vals['vIn']:.1f}V  "
                f"RPM={vals['rpm']:.0f}  "
                f"Duty={vals['dutyNow']:.3f}  "
                f"Iq={vals['iq']:.2f}A  "
                f"Id={vals['id']:.2f}A  "
                f"Iin={vals['currentIn']:.2f}A  "
                f"Imotor={vals['currentMotor']:.2f}A  "
                f"Tmos={vals['tempMos']:.1f}C  "
                f"Tmot={vals['tempMotor']:.1f}C  "
                f"Fault={vals['faultName']}"
            )

    except KeyboardInterrupt:
        print("\nStopping...")
        return 0
    finally:
        await c.disconnect()

def main():
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_amain(args)))
