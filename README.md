## Install (editable)
python3 -m venv venv
source venv/bin/activate
pip install -U pip
pip install -e .

## Run CLI
vesc-ble-can --name STAR-EXP --scan-seconds 10 --can-start 1 --can-end 50 --interval 0.5

## Run as module (optional)
python -m vesc_ble_can.cli --name STAR-EXP
