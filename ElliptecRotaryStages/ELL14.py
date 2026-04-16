from __future__ import annotations

from typing import Optional

from ElliptecBus.elliptec_models import DeviceInfo, MotorInfo
from ElliptecRotaryStages.rotary_base import ElliptecRotaryMotorPeriods, ElliptecRotaryStage

__all__ = ["DeviceInfo", "Ell14", "MotorInfo"]


class Ell14(ElliptecRotaryStage, ElliptecRotaryMotorPeriods):
    """
    Shared-bus wrapper for a Thorlabs Elliptec ELL14 rotary stage.

    This wrapper does not own the COM port. It uses an ElliptecBus instance
    and communicates only through addressed transactions on that shared bus.
    """

    MODEL_CODE = 0x0E
    MODEL_FAMILY_NAME = "ELL14"

    def enable_continuous_mode(self, *, velocity_percent: int = 50) -> None:
        """ELL14-only convenience helper:.

        Args:
            velocity_percent (int): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # enable_continuous_mode(...)
        """
        if not 50 <= velocity_percent <= 70:
            raise ValueError("ELL14 continuous mode should use velocity in the 50..70% range.")
        self.set_velocity_percent(velocity_percent)
        self.set_jog_step_pulses(0)

    def disable_continuous_mode(self, *, jog_step_pulses: Optional[int] = None) -> None:
        """Leave continuous mode by restoring a non-zero jog step.

        Args:
            jog_step_pulses (Optional[int]): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # disable_continuous_mode(...)
        """
        if jog_step_pulses is not None:
            if jog_step_pulses <= 0:
                raise ValueError("jog_step_pulses must be > 0 to disable continuous mode.")
            self.set_jog_step_pulses(jog_step_pulses)
