import struct
from dataclasses import dataclass
from typing import Optional, Dict

from .config import COMM_FW_VERSION, COMM_GET_VALUES

@dataclass
class FirmwareInfo:
    fwVersionMajor: int
    fwVersionMinor: int
    hardwareName: str
    uuid: str  # hex string

def decode_fw_version_payload(payload: bytes) -> Optional[FirmwareInfo]:
    if not payload or payload[0] != COMM_FW_VERSION or len(payload) < 3:
        return None

    major = payload[1]
    minor = payload[2]

    i = 3
    name_bytes = bytearray()
    while i < len(payload) and payload[i] != 0:
        name_bytes.append(payload[i])
        i += 1
    hardware = name_bytes.decode(errors="ignore").strip() or "Unknown"

    rem = payload[i + 1 :] if i < len(payload) else b""

    uuid_hex = "Unknown"
    if len(rem) >= 16:
        uuid_hex = rem[-16:].hex()
    elif len(rem) >= 12:
        uuid_hex = rem[-12:].hex()
    elif len(rem) > 0:
        uuid_hex = rem.hex()

    return FirmwareInfo(major, minor, hardware, uuid_hex)

def buffer_get_int16(payload: bytes, index: int) -> int:
    return struct.unpack_from(">h", payload, index)[0]

def buffer_get_int32(payload: bytes, index: int) -> int:
    return struct.unpack_from(">i", payload, index)[0]

def buffer_get_float16(payload: bytes, index: int, scale: float) -> float:
    return buffer_get_int16(payload, index) / float(scale)

def buffer_get_float32(payload: bytes, index: int, scale: float) -> float:
    return buffer_get_int32(payload, index) / float(scale)

MC_FAULT_NAMES: Dict[int, str] = {
    0: "FAULT_CODE_NONE",
    1: "FAULT_CODE_OVER_VOLTAGE",
    2: "FAULT_CODE_UNDER_VOLTAGE",
    3: "FAULT_CODE_DRV",
    4: "FAULT_CODE_ABS_OVER_CURRENT",
    5: "FAULT_CODE_OVER_TEMP_FET",
    6: "FAULT_CODE_OVER_TEMP_MOTOR",
    7: "FAULT_CODE_GATE_DRIVER_OVER_VOLTAGE",
    8: "FAULT_CODE_GATE_DRIVER_UNDER_VOLTAGE",
    9: "FAULT_CODE_MCU_UNDER_VOLTAGE",
    10: "FAULT_CODE_BOOTING_FROM_WATCHDOG_RESET",
    11: "FAULT_CODE_ENCODER_SPI",
    12: "FAULT_CODE_ENCODER_SINCOS_BELOW_MIN_AMPLITUDE",
    13: "FAULT_CODE_ENCODER_SINCOS_ABOVE_MAX_AMPLITUDE",
    14: "FAULT_CODE_FLASH_CORRUPTION",
    15: "FAULT_CODE_HIGH_OFFSET_CURRENT_SENSOR_1",
    16: "FAULT_CODE_HIGH_OFFSET_CURRENT_SENSOR_2",
    17: "FAULT_CODE_HIGH_OFFSET_CURRENT_SENSOR_3",
    18: "FAULT_CODE_UNBALANCED_CURRENTS",
    19: "FAULT_CODE_BRK",
    20: "FAULT_CODE_RESOLVER_LOT",
    21: "FAULT_CODE_RESOLVER_DOS",
    22: "FAULT_CODE_RESOLVER_LOS",
    23: "FAULT_CODE_FLASH_CORRUPTION_APP_CFG",
    24: "FAULT_CODE_FLASH_CORRUPTION_MC_CFG",
    25: "FAULT_CODE_ENCODER_NO_MAGNET",
    26: "FAULT_CODE_ENCODER_MAGNET_TOO_STRONG",
    27: "FAULT_CODE_PHASE_FILTER",
}

def decode_get_values_payload_dart_style(payload: bytes) -> Optional[dict]:
    if not payload or payload[0] != COMM_GET_VALUES:
        return None

    try:
        index = 1
        out = {}

        out["tempMos"] = buffer_get_float16(payload, index, 10.0); index += 2
        out["tempMotor"] = buffer_get_float16(payload, index, 10.0); index += 2
        out["currentMotor"] = buffer_get_float32(payload, index, 100.0); index += 4
        out["currentIn"] = buffer_get_float32(payload, index, 100.0); index += 4
        out["id"] = buffer_get_float32(payload, index, 100.0); index += 4
        out["iq"] = buffer_get_float32(payload, index, 100.0); index += 4
        out["dutyNow"] = buffer_get_float16(payload, index, 1000.0); index += 2
        out["rpm"] = buffer_get_float32(payload, index, 1.0); index += 4
        out["vIn"] = buffer_get_float16(payload, index, 10.0); index += 2
        out["ampHours"] = buffer_get_float32(payload, index, 10000.0); index += 4
        out["ampHoursCharged"] = buffer_get_float32(payload, index, 10000.0); index += 4
        out["wattHours"] = buffer_get_float32(payload, index, 10000.0); index += 4
        out["wattHoursCharged"] = buffer_get_float32(payload, index, 10000.0); index += 4
        out["tachometer"] = buffer_get_int32(payload, index); index += 4
        out["tachometerAbs"] = buffer_get_int32(payload, index); index += 4

        fault_code = payload[index]; index += 1
        out["faultCode"] = fault_code
        out["faultName"] = MC_FAULT_NAMES.get(fault_code, f"FAULT_CODE[{fault_code}]")

        out["position"] = buffer_get_float32(payload, index, 1000000.0); index += 4
        out["vescId"] = payload[index]; index += 1
        out["tempMos1"] = buffer_get_float16(payload, index, 10.0); index += 2
        out["tempMos2"] = buffer_get_float16(payload, index, 10.0); index += 2
        out["tempMos3"] = buffer_get_float16(payload, index, 10.0); index += 2
        out["vd"] = buffer_get_float32(payload, index, 100.0); index += 4
        out["vq"] = buffer_get_float32(payload, index, 100.0); index += 4

        out["_decoded_len"] = index
        out["_payload_len"] = len(payload)
        return out

    except Exception:
        return None
