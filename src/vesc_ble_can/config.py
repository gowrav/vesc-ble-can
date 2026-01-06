TARGET_NAME = "STAR-EXP"
SCAN_SECONDS = 5.0

# Nordic UART Service (service UUID)
NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"

# NUS UUIDs
NUS_RX_WRITE  = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
NUS_TX_NOTIFY = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

BLE_CHUNK = 20

# COMM IDs (your enum ordering)
COMM_FW_VERSION  = 0
COMM_GET_VALUES  = 4
COMM_FORWARD_CAN = 34
COMM_CUSTOM_APP_DATA = 36

COMM_NAMES = {
    0: "COMM_FW_VERSION",
    4: "COMM_GET_VALUES",
    34: "COMM_FORWARD_CAN",
}

# EXACT local FW request (works with your device)
FW_REQ_EXACT = bytes([0x02, 0x01, 0x00, 0x00, 0x00, 0x03])

# CAN scan defaults
CAN_START = 1
CAN_END   = 50       # bump to 254 if needed
PER_ID_TIMEOUT = 0.10
RETRIES = 2
GAP = 0.02
