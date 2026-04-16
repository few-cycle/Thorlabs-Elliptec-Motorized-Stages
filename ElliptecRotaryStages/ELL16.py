from __future__ import annotations

from ElliptecBus.elliptec_models import DeviceInfo, MotorInfo
from ElliptecRotaryStages.rotary_base import ElliptecRotaryStage

__all__ = ["DeviceInfo", "Ell16", "MotorInfo"]


class Ell16(ElliptecRotaryStage):
    """
    Shared-bus wrapper for a Thorlabs Elliptec ELL16 device.

    This wrapper does not own the COM port. It uses an ElliptecBus instance
    and communicates only through addressed transactions on that shared bus.
    """

    MODEL_CODE = 0x10
    MODEL_FAMILY_NAME = "ELL16"
