from __future__ import annotations

from ElliptecBus.elliptec_models import DeviceInfo, MotorInfo
from ElliptecMultiPositionSlider.slider_base import ElliptecSliderBase

__all__ = ["DeviceInfo", "Ell9", "MotorInfo"]


class Ell9(ElliptecSliderBase):
    """
    Shared-bus wrapper for a Thorlabs Elliptec ELL9 multi-position slider.

    This wrapper does not own the COM port. It uses an ElliptecBus instance
    and communicates only through addressed transactions on that shared bus.

    It intentionally excludes continuous-position commands that do not apply
    to multi-position slider devices.
    """

    MODEL_CODE = 0x09
    MODEL_FAMILY_NAME = "ELL9"
