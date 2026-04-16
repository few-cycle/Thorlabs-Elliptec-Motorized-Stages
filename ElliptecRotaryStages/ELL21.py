from __future__ import annotations

from ElliptecBus.elliptec_models import DeviceInfo, MotorInfo
from ElliptecRotaryStages.rotary_base import ElliptecRotaryStage

__all__ = ["DeviceInfo", "Ell21", "MotorInfo"]


class Ell21(ElliptecRotaryStage):
    """
    Shared-bus wrapper for a Thorlabs Elliptec ELL21 rotary stage.

    This wrapper does not own the COM port. It uses an ElliptecBus instance
    and communicates only through addressed transactions on that shared bus.

    Important ELL21-specific note:

    - f1, b1, f2, b2 are intentionally omitted because the protocol marks them
      as not applicable to ELL21.
    """

    MODEL_CODE = 0x15
    MODEL_FAMILY_NAME = "ELL21"
