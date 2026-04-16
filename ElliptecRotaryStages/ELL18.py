from __future__ import annotations

from ElliptecBus.elliptec_models import DeviceInfo, MotorInfo
from ElliptecRotaryStages.rotary_base import ElliptecRotaryMotorPeriods, ElliptecRotaryStage

__all__ = ["DeviceInfo", "Ell18", "MotorInfo"]


class Ell18(ElliptecRotaryStage, ElliptecRotaryMotorPeriods):
    """
    Shared-bus wrapper for a Thorlabs Elliptec ELL18 rotary stage.

    This wrapper does not own the COM port. It uses an ElliptecBus instance
    and communicates only through addressed transactions on that shared bus.
    """

    MODEL_CODE = 0x12
    MODEL_FAMILY_NAME = "ELL18"
