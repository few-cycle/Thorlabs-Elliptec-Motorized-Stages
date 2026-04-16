from __future__ import annotations

"""
Minimal CLI to exercise an ELL16 on a serial port (bench / smoke test).

Run from the project root (so ``ElliptecBus`` / ``ElliptecRotaryStages`` resolve), e.g.::

    python ell16_bench_test.py COM4 --home
    python ell16_bench_test.py COM4 --address 1 --move 45
    python ell16_bench_test.py COM4 --jog-forward 5
"""

import argparse
import logging

from ElliptecBus.elliptec_bus import ElliptecBus
from ElliptecRotaryStages.ELL16 import Ell16


def demo() -> None:
    """Tiny manual test helper for bench validation."""
    parser = argparse.ArgumentParser(description="Minimal ELL16 bench test")
    parser.add_argument("port", help="Serial COM port, e.g. COM4 or /dev/ttyUSB0")
    parser.add_argument("--address", default="0", help="Elliptec address, default 0")
    parser.add_argument("--home", action="store_true", help="Home the stage first")
    parser.add_argument("--move", type=float, default=None, help="Move absolute in degrees")
    parser.add_argument(
        "--jog",
        type=float,
        default=None,
        help="Legacy alias: set jog step in degrees and jog forward (negative = backward)",
    )
    parser.add_argument(
        "--jog-forward",
        type=float,
        default=None,
        dest="jog_forward_deg",
        help="Set jog step in degrees and jog forward",
    )
    parser.add_argument(
        "--jog-backward",
        type=float,
        default=None,
        dest="jog_backward_deg",
        help="Set jog step in degrees and jog backward",
    )
    parser.add_argument(
        "--motion-timeout",
        type=float,
        default=None,
        help="Motion wait timeout in seconds (default: library default, usually 30)",
    )
    parser.add_argument(
        "--auto-validate-model",
        action="store_true",
        help="Fail at startup if IN reports a model other than ELL16",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    motion_timeout = (
        args.motion_timeout if args.motion_timeout is not None else Ell16.DEFAULT_MOTION_TIMEOUT
    )

    with ElliptecBus(args.port) as bus:
        stage = Ell16(
            bus,
            address=args.address,
            motion_timeout=motion_timeout,
            auto_validate_model=args.auto_validate_model,
        )
        info = stage.get_info()
        print("Connected:", info)
        status = stage.get_status()
        print("Status:", status)
        print("Position [deg]:", stage.get_position_degrees())

        if args.home:
            pos = stage.home(direction="cw")
            if pos is not None:
                print("Homed to pulses:", pos, "deg:", stage.pulses_to_degrees(pos))
            else:
                print("Home issued (wait=False would return None; unexpected with default wait)")

        if args.move is not None:
            pos_deg = stage.move_absolute_degrees(args.move)
            print("Moved to [deg]:", pos_deg)

        if args.jog is not None:
            stage.set_jog_step_degrees(abs(args.jog))
            if args.jog < 0:
                pos = stage.jog_backward()
            else:
                pos = stage.jog_forward()
            if pos is not None:
                print("Jog result [deg]:", stage.pulses_to_degrees(pos))
            else:
                print("Jog issued without wait (no position returned)")

        if args.jog_forward_deg is not None:
            stage.set_jog_step_degrees(args.jog_forward_deg)
            pos = stage.jog_forward()
            if pos is not None:
                print("Jog forward result [deg]:", stage.pulses_to_degrees(pos))
            else:
                print("Jog forward issued without wait")

        if args.jog_backward_deg is not None:
            stage.set_jog_step_degrees(args.jog_backward_deg)
            pos = stage.jog_backward()
            if pos is not None:
                print("Jog backward result [deg]:", stage.pulses_to_degrees(pos))
            else:
                print("Jog backward issued without wait")


if __name__ == "__main__":
    demo()
