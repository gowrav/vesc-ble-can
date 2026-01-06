from dataclasses import dataclass
from typing import List

from .vesc_crc import crc16_ccitt_init0

@dataclass
class BLEPacket:
    payload: bytes

class BLEHelperPy:
    def __init__(self):
        self.counter = 0
        self.endMessage = 512
        self.messageRead = False
        self.messageReceived = bytearray(512)
        self.lenPayload = 0
        self.payload = bytearray(512)
        self.payloadStart = 0

    def getPayload(self) -> bytes:
        return bytes(self.payload[: self.lenPayload])

    def resetPacket(self):
        self.messageRead = False
        self.counter = 0
        self.endMessage = 512
        self.lenPayload = 0
        self.payloadStart = 0
        for i in range(512):
            self.messageReceived[i] = 0
            self.payload[i] = 0

    def unpackPayload(self) -> bool:
        crcMessage = (self.messageReceived[self.endMessage - 3] << 8) | self.messageReceived[self.endMessage - 2]

        for i in range(self.lenPayload):
            self.payload[i] = self.messageReceived[i + self.payloadStart]

        crcPayload = crc16_ccitt_init0(self.payload, 0, self.lenPayload)
        return crcPayload == crcMessage

    def processIncomingBytes(self, incomingData: List[int]) -> int:
        for b in incomingData:
            self.messageReceived[self.counter] = b
            self.counter += 1

            if self.counter == 2:
                start_byte = self.messageReceived[0]
                if start_byte == 2:
                    self.lenPayload = self.messageReceived[1]
                    self.endMessage = self.lenPayload + 5
                    self.payloadStart = 2
                elif start_byte == 3:
                    if self.counter < 3:
                        continue
                    self.lenPayload = (self.messageReceived[1] << 8) | self.messageReceived[2]
                    self.endMessage = self.lenPayload + 6
                    self.payloadStart = 3
                else:
                    self.resetPacket()
                    return 0

            if self.counter >= len(self.messageReceived):
                self.resetPacket()
                break

            if self.counter == self.endMessage and self.messageReceived[self.endMessage - 1] == 3:
                self.messageRead = True
                break

        if self.messageRead:
            return self.lenPayload if self.unpackPayload() else 0
        return 0
