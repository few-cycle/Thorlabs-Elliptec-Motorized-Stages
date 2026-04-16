from __future__ import annotations

from ElliptecBus.elliptec_models import DeviceInfo, MotorInfo
from ElliptecMotorized_IRIS.iris_base import ElliptecIrisExtendedBase

__all__ = ["DeviceInfo", "Ell15Z", "MotorInfo"]


class Ell15Z(ElliptecIrisExtendedBase):
    """
    Shared-bus wrapper for a Thorlabs Elliptec ELL15Z motorized iris.

    This wrapper does not own the COM port. It uses an ElliptecBus instance
    and communicates only through addressed transactions on that shared bus.

    Design notes:

    - Treats the device as a position-based closed-loop unit using the IN packet
      scaling factor.
    - Intentionally does NOT include the "ah" command, because that command was
      treated as ELL15-only in the original wrapper.
    """

    MODEL_CODE = 0x1F
    MODEL_FAMILY_NAME = "ELL15Z"
