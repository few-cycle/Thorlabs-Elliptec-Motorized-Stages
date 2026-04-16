# Thorlabs Elliptec Motorized Stages

Python wrappers for Thorlabs Elliptec ELLx modules, organized by device family and built on a shared serial-bus architecture.

This project provides:

- a shared RS-232 transport layer (`ElliptecBus`)
- common protocol/motion mixins (`ElliptecBase`)
- device-family APIs for rotary, linear, slider, and iris modules
- a practical bench test script for ELL16 (`ell16_bench_test.py`)

---

## Project Structure

- `ElliptecBus/`
  - `elliptec_bus.py`: low-level bus I/O, packet parsing, address handling, status checks
  - `elliptec_models.py`: `DeviceInfo` and `MotorInfo` data models
- `ElliptecBase/`
  - `elliptec_base.py`: shared parsing helpers and base mixins used by all families
- `ElliptecRotaryStages/`
  - `ELL14.py`, `ELL16.py`, `ELL18.py`, `ELL21.py`, `rotary_base.py`
- `ElliptecLinearStages/`
  - `ELL17.py`, `ELL20.py`, `linear_base.py`
- `ElliptecMultiPositionSlider/`
  - `ELL6.py`, `ELL6B.py`, `ELL9.py`, `ELL12.py`, `slider_base.py`
- `ElliptecMotorized_IRIS/`
  - `ELL15.py`, `ELL15Z.py`, `iris_base.py`
- `ell16_bench_test.py`: CLI smoke test for ELL16

---

## Supported Device Groups

### Rotary

- `Ell14`
- `Ell16`
- `Ell18`
- `Ell21`

### Linear

- `Ell17`
- `Ell20`

### Multi-Position Slider

- `Ell6`
- `Ell6B`
- `Ell9`
- `Ell12`

### Iris

- `Ell15`
- `Ell15Z`

---

## Requirements

- Python 3.9+ recommended
- `pyserial`

Install runtime dependency:

```bash
pip install pyserial
```

## PyPI Installation (Planned)

When the package is published to PyPI, install it with:

```bash
pip install <YOUR_PACKAGE_NAME>
```

Placeholders:

- PyPI package name: `<YOUR_PACKAGE_NAME>`
- PyPI project URL: `<ADD_YOUR_PYPI_URL_HERE>`

---

## Quick Start

### 1) Connect to a bus

```python
from ElliptecBus.elliptec_bus import ElliptecBus
from ElliptecRotaryStages.ELL16 import Ell16

with ElliptecBus("COM18") as bus:
    stage = Ell16(bus, address="0")
    print(stage.get_info())
    print(stage.get_status())
    print(stage.get_position_degrees())
```

### 2) Typical motion calls

```python
with ElliptecBus("COM18") as bus:
    stage = Ell16(bus, address="0")
    stage.home(direction="cw")
    stage.move_absolute_degrees(90.0)
    stage.set_jog_step_degrees(5.0)
    stage.jog_forward()
```

---

## Bench Validation Script (ELL16)

Use the included test helper:

```bash
python ell16_bench_test.py COM18
python ell16_bench_test.py COM18 --home --move 90
python ell16_bench_test.py COM18 --jog-forward 5
python ell16_bench_test.py COM18 --jog-backward 2
```

Useful options:

- `--address` (default `0`)
- `--motion-timeout`
- `--auto-validate-model`

> On Windows, find your COM port in **Device Manager** (Ports (COM & LPT)).

---

## Addressing and Bus Behavior

- Elliptec device addresses are hexadecimal: `0` to `F`.
- One serial bus can host multiple modules on different addresses.
- The wrappers are designed for addressed communication over one shared bus object.

---

## Communication protocol

For the complete communication protocol covering all Thorlabs ELLx models, see the official Thorlabs manual:
- [ELLx Modules Protocol Manual (PDF)](./ellx-modules-protocol-manual.pdf)

---

## Error Handling

Core exceptions from `ElliptecBus`:

- `ElliptecError`: base exception
- `ElliptecTimeoutError`: no response in time
- `ElliptecProtocolError`: malformed/unexpected packet
- `ElliptecDeviceError`: non-zero `GS` status code returned by device

`STATUS_MESSAGES` maps known `GS` codes to human-readable descriptions.

---

## Documentation (Sphinx / Read the Docs)

Sphinx docs are included in `docs/` and configured via:

- `.readthedocs.yaml`
- `requirements-docs.txt`
- `docs/conf.py`
- `docs/index.rst`
- `docs/api.rst`

Local docs build:

```bash
pip install -r requirements-docs.txt
python -m sphinx -b html docs docs/_build/html
```

Documentation:

[https://thorlabs-elliptec-motorized-stages.readthedocs.io/en/latest/](https://thorlabs-elliptec-motorized-stages.readthedocs.io/en/latest/)

---

## License

This project is licensed under the Apache License 2.0.

See the `LICENSE` file for full terms.

---

## Notes

- This project focuses on command/control protocol behavior for ELLx modules.
- Always verify device model/address before issuing motion commands on shared buses.
- For production integrations, consider adding application-level retries, logging, and safety interlocks.
