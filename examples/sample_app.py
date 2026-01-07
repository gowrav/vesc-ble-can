#!/usr/bin/env python3
import argparse
import asyncio
import signal
import sys
import termios
import tty

from vesc_ble_can import VescBleCanClient


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Sample app using vesc_ble_can library")
    p.add_argument("--address", default=None, help="BLE address/identifier (macOS: UUID-like)")
    p.add_argument("--name", default=None, help="BLE advertised name (optional)")
    p.add_argument("--scan-seconds", type=float, default=10.0, help="Scan duration")
    p.add_argument("--can-start", type=int, default=1, help="Start CAN ID (inclusive)")
    p.add_argument("--can-end", type=int, default=50, help="End CAN ID (inclusive)")
    p.add_argument("--interval", type=float, default=0.5, help="GET_VALUES polling interval (s)")
    p.add_argument("--local-fw", action="store_true", help="Try local FW sanity request + print result")
    return p


# -------------------------------
# Terminal helpers
# -------------------------------

def print_telemetry_and_prompt(line: str):
    sys.stdout.write("\r" + " " * 160 + "\r")
    print(line)
    sys.stdout.write("> ")
    sys.stdout.flush()


# -------------------------------
# Raw key reader (no Enter)
# -------------------------------

async def keyboard_custom_data_loop(
    client: VescBleCanClient,
    stop_event: asyncio.Event,
    active_can_id: int,
):
    """
    Immediate keypress handler (no Enter required).
    Uses raw terminal mode.
    """
    print(
        "\nCustom input enabled:\n"
        "  Press 0–9  → send COMM_CUSTOM_APP_DATA immediately\n"
        "  q          → quit\n"
    )
    sys.stdout.write("> ")
    sys.stdout.flush()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setcbreak(fd)  # raw-ish mode, no Enter needed

        loop = asyncio.get_running_loop()

        while not stop_event.is_set():
            ch = await loop.run_in_executor(None, sys.stdin.read, 1)
            if not ch:
                continue

            if ch.lower() == "q":
                print("\nQuit requested.")
                stop_event.set()
                return

            if ch.isdigit():
                key_num = ord(ch) - ord("0")   # '0'→0, '1'→1, ..., '9'→9
                cmd_value = key_num & 0x0F     # ensure 0x00–0x09

                try:
                    await client.send_custom_app_data_can(active_can_id, cmd_value)
                    print(
                        f"\n[TX] CAN {active_can_id} → COMM_CUSTOM_APP_DATA "
                        f"[0x01, 0x{cmd_value:02X}]"
                    )
                except Exception as e:
                    print(f"\n❌ Failed to send custom data: {e}")

            sys.stdout.write("> ")
            sys.stdout.flush()

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


async def app(args) -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_stop():
        stop_event.set()

    try:
        loop.add_signal_handler(signal.SIGINT, _request_stop)
        loop.add_signal_handler(signal.SIGTERM, _request_stop)
    except NotImplementedError:
        pass

    client = VescBleCanClient(
        target_name=args.name,
        address=args.address,
        scan_seconds=args.scan_seconds,
    )

    keyboard_task = None

    try:
        await client.connect()
        print("Connected ✅")

        if args.local_fw:
            fw = await client.local_fw_info(timeout_s=1.0)
            if fw:
                print(
                    f"Local FW: {fw.fwVersionMajor}.{fw.fwVersionMinor} | "
                    f"HW: {fw.hardwareName} | UUID: {fw.uuid}"
                )

        nodes = await client.discover_can_nodes(
            can_start=args.can_start,
            can_end=args.can_end,
            per_id_timeout=0.25,
            retries=3,
            gap_s=0.02,
        )

        if not nodes:
            print("❌ No CAN nodes found.")
            return

        can_ids = sorted(nodes.keys())
        active_can_id = can_ids[0]

        print("\nDiscovered CAN nodes:", can_ids)
        print(f"Using CAN ID {active_can_id} for custom app commands")

        await client.start_polling_get_values(
            can_ids=can_ids,
            interval_s=args.interval,
        )

        print(
            f"\nPolling telemetry every {args.interval * 1000:.0f} ms "
            "(Ctrl+C to stop)"
        )

        keyboard_task = asyncio.create_task(
            keyboard_custom_data_loop(client, stop_event, active_can_id)
        )

        while not stop_event.is_set():
            try:
                vals = await asyncio.wait_for(client.get_next_values(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if not vals:
                continue

            vesc_id = vals.get("vescId", -1)

            line = (
                f"VESC {vesc_id:3d} | "
                f"Vin={vals['vIn']:.1f}V | "
                f"RPM={vals['rpm']:.0f} | "
                f"Iq={vals['iq']:.2f}A | "
                f"Id={vals['id']:.2f}A | "
                f"Imotor={vals['currentMotor']:.2f}A | "
                f"Tmos={vals['tempMos']:.1f}C | "
                f"Tmot={vals['tempMotor']:.1f}C | "
                f"Fault={vals['faultName']}"
            )

            print_telemetry_and_prompt(line)

    finally:
        stop_event.set()
        if keyboard_task:
            keyboard_task.cancel()
        await client.disconnect()
        print("\nDisconnected ✅")


def main():
    args = build_parser().parse_args()

    with asyncio.Runner() as runner:
        runner.run(app(args))


if __name__ == "__main__":
    main()
