from __future__ import annotations

from ElliptecBus.elliptec_models import DeviceInfo, MotorInfo
from ElliptecLinearStages.linear_base import ElliptecLinearStage

__all__ = ["DeviceInfo", "Ell20", "MotorInfo"]


class Ell20(ElliptecLinearStage):
    """
    Shared-bus wrapper for a Thorlabs Elliptec ELL20 linear stage.

    This wrapper does not own the COM port. It uses an ElliptecBus instance
    and communicates only through addressed transactions on that shared bus.
    """

    MODEL_CODE = 0x14
    MODEL_FAMILY_NAME = "ELL20"
