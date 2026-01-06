import asyncio
import time
from typing import Optional

from bleak import BleakClient, BleakScanner

from .config import NUS_RX_WRITE, BLE_CHUNK, NUS_SERVICE_UUID
from .vesc_packet import make_forward_can_get_values, make_custom_app_data, make_forward_can_custom_app_data

async def find_device(
    *,
    address: Optional[str] = None,
    name: Optional[str] = None,
    timeout_s: float = 5.0,
):
    """
    Robust scanner that works across Bleak versions on macOS.
    Priority:
      1) address match (macOS uses UUID-like address string)
      2) exact name match
      3) first device advertising NUS service UUID
      4) first device seen
    """
    address = address.strip().lower() if address else None
    name = name.strip() if name else None

    found_by_addr = None
    found_by_name = None
    found_by_nus = None
    first_seen = None

    def cb(device, adv):
        nonlocal found_by_addr, found_by_name, found_by_nus, first_seen

        # Some odd callbacks may pass unexpected objects; guard hard.
        dev_addr = getattr(device, "address", None)
        dev_name = getattr(device, "name", None)

        if first_seen is None and dev_addr is not None:
            first_seen = device

        if address and dev_addr and dev_addr.strip().lower() == address:
            found_by_addr = device
            return

        adv_name = getattr(adv, "local_name", None) if adv else None
        if name:
            if (dev_name and dev_name.strip() == name) or (adv_name and adv_name.strip() == name):
                found_by_name = device

        # Check service UUIDs for NUS
        uuids = getattr(adv, "service_uuids", None) if adv else None
        if uuids:
            for u in uuids:
                if isinstance(u, str) and u.lower() == NUS_SERVICE_UUID.lower():
                    if found_by_nus is None:
                        found_by_nus = device

    print(f"Scanning ({timeout_s:.0f}s)...")
    scanner = BleakScanner(cb)
    await scanner.start()

    t0 = time.time()
    try:
        while time.time() - t0 < timeout_s:
            if found_by_addr:
                return found_by_addr
            await asyncio.sleep(0.1)
    finally:
        await scanner.stop()

    if found_by_addr:
        return found_by_addr
    if found_by_name:
        return found_by_name
    if found_by_nus:
        return found_by_nus
    return first_seen


async def ble_write_chunked(client: BleakClient, data: bytes, without_response: bool = True):
    for i in range(0, len(data), BLE_CHUNK):
        chunk = data[i:i + BLE_CHUNK]
        await client.write_gatt_char(NUS_RX_WRITE, chunk, response=not without_response)
        await asyncio.sleep(0.03)


async def poll_get_values_periodic(
    client: BleakClient,
    can_ids,
    interval_s: float = 0.5,
):
    try:
        while True:
            for cid in can_ids:
                req = make_forward_can_get_values(cid)
                await ble_write_chunked(client, req, without_response=True)
                await asyncio.sleep(0.01)
            await asyncio.sleep(interval_s)
    except asyncio.CancelledError:
        pass
