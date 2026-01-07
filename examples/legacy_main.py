#!/usr/bin/env python3
"""
Legacy reference script.

This file shows the original end-to-end BLE + CAN workflow.
Not used by the library or CLI.
"""

import asyncio
from typing import Dict, List

from bleak import BleakClient

from .config import (
    TARGET_NAME, SCAN_SECONDS,
    NUS_TX_NOTIFY, FW_REQ_EXACT,
    CAN_START, CAN_END, PER_ID_TIMEOUT, RETRIES, GAP,
    COMM_FW_VERSION, COMM_GET_VALUES
)
from .ble_helper import BLEHelperPy
from .ble_io import find_device_by_name, ble_write_chunked, poll_get_values_periodic
from .vesc_packet import make_forward_can_fw_req
from .vesc_decode import decode_fw_version_payload, decode_get_values_payload_dart_style, FirmwareInfo

async def main():
    dev = await find_device_by_name(TARGET_NAME, SCAN_SECONDS)
    if not dev:
        print(f"Not found: {TARGET_NAME}")
        return

    print(f"Found: {dev.name} [{dev.address}]")

    bleHelper = BLEHelperPy()
    fw_payload_queue: asyncio.Queue[bytes] = asyncio.Queue()
    values_payload_queue: asyncio.Queue[bytes] = asyncio.Queue()

    def on_notify(_, value: bytearray):
        n = bleHelper.processIncomingBytes(list(value))
        if n > 0:
            payload = bleHelper.getPayload()
            packetId = payload[0]

            if packetId == COMM_FW_VERSION:
                fw_payload_queue.put_nowait(payload)
            elif packetId == COMM_GET_VALUES:
                values_payload_queue.put_nowait(payload)

            bleHelper.resetPacket()

    async with BleakClient(dev) as client:
        print("Connected ✅")
        await client.start_notify(NUS_TX_NOTIFY, on_notify)
        print("Notifications enabled ✅")

        # 0) Local FW sanity
        await ble_write_chunked(client, FW_REQ_EXACT, without_response=False)
        try:
            p = await asyncio.wait_for(fw_payload_queue.get(), timeout=1.0)
            info = decode_fw_version_payload(p)
            if info:
                print(f"Local FW: {info.fwVersionMajor}.{info.fwVersionMinor} | HW: {info.hardwareName} | UUID: {info.uuid}")
        except asyncio.TimeoutError:
            print("⚠️ Local FW request timed out (continuing).")

        # 1) CAN discovery
        print(f"\nPinging CAN bus (forward COMM_FW_VERSION) for IDs {CAN_START}..{CAN_END} ...\n")
        found_nodes: Dict[int, FirmwareInfo] = {}

        async def flush_queue(q: asyncio.Queue):
            try:
                while True:
                    q.get_nowait()
            except asyncio.QueueEmpty:
                pass

        for can_id in range(CAN_START, CAN_END + 1):
            await flush_queue(fw_payload_queue)

            ok = False
            for _ in range(RETRIES):
                req = make_forward_can_fw_req(can_id)
                await ble_write_chunked(client, req, without_response=True)

                try:
                    resp = await asyncio.wait_for(fw_payload_queue.get(), timeout=PER_ID_TIMEOUT)
                    info = decode_fw_version_payload(resp)
                    if info:
                        found_nodes[can_id] = info
                        ok = True
                        break
                except asyncio.TimeoutError:
                    pass

            if ok:
                info = found_nodes[can_id]
                print(f"✅ CAN {can_id:3d}  FW {info.fwVersionMajor}.{info.fwVersionMinor}  HW '{info.hardwareName}'  UUID {info.uuid}")
            await asyncio.sleep(GAP)

        if not found_nodes:
            print("\n❌ No CAN nodes found in this range.")
            print("Next checks: CAN baud/mode, termination, IDs; expand CAN_END.")
            await client.stop_notify(NUS_TX_NOTIFY)
            return

        print("\n=== Summary (FW) ===")
        for cid in sorted(found_nodes.keys()):
            i = found_nodes[cid]
            print(f"CAN {cid:3d}: {i.hardwareName} | {i.fwVersionMajor}.{i.fwVersionMinor} | {i.uuid}")

        # 2) Start periodic polling every 500ms
        can_id_list: List[int] = sorted(found_nodes.keys())
        print("\nStarting COMM_GET_VALUES polling every 500 ms... (Ctrl+C to stop)\n")

        poll_task = asyncio.create_task(poll_get_values_periodic(client, can_id_list, interval_s=0.5))

        try:
            while True:
                resp = await values_payload_queue.get()
                vals = decode_get_values_payload_dart_style(resp)
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
            print("\nStopping polling...")

        finally:
            poll_task.cancel()
            await client.stop_notify(NUS_TX_NOTIFY)

if __name__ == "__main__":
    asyncio.run(main())
