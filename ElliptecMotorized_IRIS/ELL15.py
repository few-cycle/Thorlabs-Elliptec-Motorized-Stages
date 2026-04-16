from __future__ import annotations

from typing import Optional

from ElliptecBus.elliptec_models import DeviceInfo, MotorInfo
from ElliptecMotorized_IRIS.iris_base import ElliptecIrisBase

__all__ = ["DeviceInfo", "Ell15", "MotorInfo"]


class Ell15(ElliptecIrisBase):
    """
    Shared-bus wrapper for a Thorlabs Elliptec ELL15 motorized iris.

    This wrapper does not own the COM port. It uses an ElliptecBus instance
    and communicates only through addressed transactions on that shared bus.

    Design notes:

    - Treats the device as a position-based closed-loop unit using the IN packet
      scaling factor.
    - Adds the ELL15-only auto-homing command "ah".
    - Intentionally omits clean_mechanics(), because the manual section for "cm"
      does not list ELL15.
    """

    MODEL_CODE = 0x0F
    MODEL_FAMILY_NAME = "ELL15"

    def set_auto_homing(self, enabled: bool, *, timeout: Optional[float] = None) -> Optional[int]:
        """ELL15-only auto-home-at-startup setting.

        Args:
            enabled (bool): Input value for this operation.
            timeout (Optional[float]): Input value for this operation.

        Returns:
            Optional[int]: Result produced by this function.

        Example:
            >>> # Example
            >>> # set_auto_homing(...)
        """
        value = "1" if enabled else "0"
        with self.bus.transaction():
            self.bus.write("ah" + value, address=self.address)
            return self._await_motion_completion_locked(timeout=timeout)
