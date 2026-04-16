Overview
========

This project provides protocol-level and device-family abstractions for the
Thorlabs Elliptec ELLx ecosystem.

Main packages:

- ``ElliptecBus``: serial transport, packet parsing, protocol encoding helpers.
- ``ElliptecBase``: shared base mixins for motion/status/discovery behavior.
- ``ElliptecRotaryStages``: rotary-family wrappers (ELL14, ELL16, ELL18, ELL21).
- ``ElliptecLinearStages``: linear-family wrappers (ELL17, ELL20).
- ``ElliptecMultiPositionSlider``: slider-family wrappers (ELL6, ELL6B, ELL9, ELL12).
- ``ElliptecMotorized_IRIS``: iris-family wrappers (ELL15, ELL15Z).

The API docs are generated directly from in-code docstrings.
