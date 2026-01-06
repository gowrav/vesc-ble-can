from typing import Optional

def crc16_ccitt_init0(data: bytes, start: int = 0, length: Optional[int] = None) -> int:
    if length is None:
        length = len(data) - start
    crc = 0
    for i in range(start, start + length):
        b = data[i]
        crc ^= (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc
