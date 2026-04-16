from __future__ import annotations

from ElliptecBus.elliptec_models import DeviceInfo, MotorInfo
from ElliptecBus.elliptec_bus import Packet
from ElliptecMultiPositionSlider.slider_base import ElliptecSliderBase

__all__ = ["DeviceInfo", "Ell6", "MotorInfo"]


class Ell6(ElliptecSliderBase):
    """
    Shared-bus wrapper for a Thorlabs Elliptec ELL6 multi-position slider.

    This wrapper does not own the COM port. It uses an ElliptecBus instance
    and communicates only through addressed transactions on that shared bus.

    ELL6 is a single-motor slider, so only motor-1-specific commands are exposed.
    """

    MODEL_CODE = 0x06
    MODEL_FAMILY_NAME = "ELL6"
    MOTORS = (1,)

    def get_motor_info(self) -> MotorInfo:
        """Get motor info.

        Returns:
            MotorInfo: Result produced by this function.

        Example:
            >>> # Example
            >>> # get_motor_info(...)
        """
        return super().get_motor_info(1)

    def set_forward_period(self, period: int) -> None:
        """Set forward period.

        Args:
            period (int): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # set_forward_period(...)
        """
        super().set_forward_period(1, period)

    def set_backward_period(self, period: int) -> None:
        """Set backward period.

        Args:
            period (int): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # set_backward_period(...)
        """
        super().set_backward_period(1, period)

    def search_frequency(self, *, timeout: float = 20.0) -> None:
        """Search frequency.

        Args:
            timeout (float): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # search_frequency(...)
        """
        super().search_frequency(1, timeout=timeout)

    def scan_current_curve(self, *, timeout: float = 20.0) -> Packet:
        """Scan current curve.

        Args:
            timeout (float): Input value for this operation.

        Returns:
            Packet: Result produced by this function.

        Example:
            >>> # Example
            >>> # scan_current_curve(...)
        """
        return super().scan_current_curve(1, timeout=timeout)
