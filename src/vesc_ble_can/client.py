import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Awaitable

from bleak import BleakClient

from .ble_helper import BLEHelperPy
from .ble_io import find_device, ble_write_chunked, poll_get_values_periodic
from .config import (
    NUS_TX_NOTIFY,
    FW_REQ_EXACT,
    COMM_FW_VERSION,
    COMM_GET_VALUES,
)
from .vesc_decode import (
    FirmwareInfo,
    decode_fw_version_payload,
    decode_get_values_payload_dart_style,
)
from .vesc_packet import make_forward_can_fw_req


@dataclass
class DiscoveredNode:
    can_id: int
    info: FirmwareInfo


class VescBleCanClient:
    """
    High-level client:
      - connect to BLE device by address or name (or auto-pick)
      - discover CAN nodes (forward FW_VERSION)
      - poll GET_VALUES periodically
    """

    def __init__(
        self,
        target_name: Optional[str] = None,
        scan_seconds: float = 5.0,
        address: Optional[str] = None,
    ):
        self.target_name = target_name
        self.address = address
        self.scan_seconds = scan_seconds

        # Always initialize these, so callbacks/cleanup never crash
        self._ble_helper = BLEHelperPy()

        self._client: Optional[BleakClient] = None
        self._poll_task: Optional[asyncio.Task] = None

        self._fw_q: asyncio.Queue[bytes] = asyncio.Queue()
        self._values_q: asyncio.Queue[bytes] = asyncio.Queue()

        self.nodes: Dict[int, FirmwareInfo] = {}

    @property
    def is_connected(self) -> bool:
        return bool(self._client and self._client.is_connected)

    async def connect(self) -> None:
        dev = await find_device(
            address=self.address,
            name=self.target_name,
            timeout_s=self.scan_seconds,
        )
        if not dev:
            raise RuntimeError(
                f"BLE device not found (address={self.address!r}, name={self.target_name!r})"
            )

        print(f"Selected: {dev.name} [{dev.address}]")

        self._client = BleakClient(dev)

        def on_notify(_, value: bytearray):
            # Defensive: callback can fire at awkward times; never throw here.
            try:
                n = self._ble_helper.processIncomingBytes(list(value))
                if n > 0:
                    payload = self._ble_helper.getPayload()
                    pkt = payload[0]

                    if pkt == COMM_FW_VERSION:
                        self._fw_q.put_nowait(payload)
                    elif pkt == COMM_GET_VALUES:
                        self._values_q.put_nowait(payload)

                    self._ble_helper.resetPacket()
            except Exception:
                # Swallow to avoid crashing Bleak's internal callback loop
                pass

        await self._client.connect()
        await asyncio.sleep(5)
        await self._client.start_notify(NUS_TX_NOTIFY, on_notify)

        # Sanity: local FW request
        await ble_write_chunked(self._client, FW_REQ_EXACT, without_response=False)

    async def disconnect(self) -> None:
        poll_task = self._poll_task
        if poll_task:
            poll_task.cancel()
            self._poll_task = None

        client = self._client
        if client:
            try:
                await client.stop_notify(NUS_TX_NOTIFY)
            except Exception:
                pass
            try:
                await client.disconnect()
            finally:
                self._client = None

    async def _flush_queue(self, q: asyncio.Queue):
        try:
            while True:
                q.get_nowait()
        except asyncio.QueueEmpty:
            pass

    async def local_fw_info(self, timeout_s: float = 1.0) -> Optional[FirmwareInfo]:
        await self._flush_queue(self._fw_q)
        try:
            payload = await asyncio.wait_for(self._fw_q.get(), timeout=timeout_s)
            return decode_fw_version_payload(payload)
        except asyncio.TimeoutError:
            return None

    async def discover_can_nodes(
        self,
        can_start: int = 1,
        can_end: int = 50,
        per_id_timeout: float = 0.20,
        retries: int = 2,
        gap_s: float = 0.02,
    ) -> Dict[int, FirmwareInfo]:
        if not self._client:
            raise RuntimeError("Not connected")

        found: Dict[int, FirmwareInfo] = {}

        for can_id in range(can_start, can_end + 1):
            await self._flush_queue(self._fw_q)

            for _ in range(retries):
                req = make_forward_can_fw_req(can_id)
                await ble_write_chunked(self._client, req, without_response=True)
                try:
                    resp = await asyncio.wait_for(self._fw_q.get(), timeout=per_id_timeout)
                    info = decode_fw_version_payload(resp)
                    if info:
                        found[can_id] = info
                        break
                except asyncio.TimeoutError:
                    pass

            await asyncio.sleep(gap_s)

        self.nodes = found
        return found

    async def start_polling_get_values(self, can_ids: List[int], interval_s: float = 0.5) -> None:
        if not self._client:
            raise RuntimeError("Not connected")

        if self._poll_task:
            self._poll_task.cancel()

        self._poll_task = asyncio.create_task(
            poll_get_values_periodic(self._client, can_ids, interval_s=interval_s)
        )

    async def get_next_values(self) -> Optional[dict]:
        try:
            payload = await self._values_q.get()
        except asyncio.CancelledError:
            return None
        return decode_get_values_payload_dart_style(payload)

    async def run_values_loop(self, on_values: Callable[[dict], Awaitable[None]]) -> None:
        while True:
            vals = await self.get_next_values()
            if vals:
                await on_values(vals)

    async def send_custom_app_data_can(self, can_id: int, value: int):
        """
        Send COMM_CUSTOM_APP_DATA to a CAN node via VESC Express.

        Payload format matches Flutter:
        [0x01, value]
        """
        if not self._client or not self._client.is_connected:
            raise RuntimeError("BLE client not connected")

        from .vesc_packet import make_forward_can_custom_app_data
        from .ble_io import ble_write_chunked

        payload = bytes([value])
        pkt = make_forward_can_custom_app_data(can_id, payload)

        # Strong debug proof (keep for now)
        print(f"[TX] CAN {can_id} CUSTOM_APP_DATA → {pkt.hex()}")

        await ble_write_chunked(
            self._client,
            pkt,
            without_response=True,
        )

