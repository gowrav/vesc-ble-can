from .vesc_crc import crc16_ccitt_init0
from .config import (
    COMM_FORWARD_CAN,
    COMM_FW_VERSION,
    COMM_GET_VALUES,
    COMM_CUSTOM_APP_DATA,
)

def vesc_pack_short(payload: bytes) -> bytes:
    if len(payload) >= 256:
        raise ValueError("Short pack only (<256 payload).")
    crc = crc16_ccitt_init0(payload, 0, len(payload))
    return bytes([0x02, len(payload)]) + payload + bytes([(crc >> 8) & 0xFF, crc & 0xFF]) + bytes([0x03])

def make_forward_can_fw_req(can_id: int) -> bytes:
    payload = bytes([COMM_FORWARD_CAN, can_id & 0xFF, COMM_FW_VERSION])
    return vesc_pack_short(payload)

def make_forward_can_get_values(can_id: int) -> bytes:
    payload = bytes([COMM_FORWARD_CAN, can_id & 0xFF, COMM_GET_VALUES])
    return vesc_pack_short(payload)

def make_custom_app_data(data: bytes) -> bytes:
    """
    Build COMM_CUSTOM_APP_DATA packet (local, not CAN-forwarded)

    Equivalent to:
      simpleVESCRequest(COMM_CUSTOM_APP_DATA, data: Uint8List)
    """
    payload = bytes([COMM_CUSTOM_APP_DATA]) + data
    return vesc_pack_short(payload)


def make_forward_can_custom_app_data(can_id: int, data: bytes) -> bytes:
    """
    Build CAN-forwarded COMM_CUSTOM_APP_DATA packet

    Equivalent to:
      simpleVESCRequest(
        COMM_CUSTOM_APP_DATA,
        data: ...,
        optionalCANID: can_id
      )
    """
    payload = bytes([COMM_FORWARD_CAN, can_id & 0xFF, COMM_CUSTOM_APP_DATA]) + data
    return vesc_pack_short(payload)
