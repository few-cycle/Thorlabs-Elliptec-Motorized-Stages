from __future__ import annotations

from ElliptecBase.elliptec_base import (
    ElliptecAddressedDeviceBase,
    ElliptecClosedLoopTuningMixin,
    ElliptecDegreeUnitsMixin,
    validate_motor_index_dual,
)
from ElliptecBus.elliptec_bus import ElliptecBus


class ElliptecRotaryMotorPeriods:
    """
    Optional rotary commands for devices that support per-motor forward/backward period.

    Not all Elliptec rotary devices expose f1/b1/f2/b2 in the protocol (for example ELL16
    and ELL21 omit these in this library).
    """

    bus: ElliptecBus
    address: str

    def set_forward_period(self, motor_index: int, period: int) -> None:
        """Set forward period.

        Args:
            motor_index (int): Input value for this operation.
            period (int): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # set_forward_period(...)
        """
        validate_motor_index_dual(motor_index)
        if not 0 <= period <= 0xFFFF:
            raise ValueError("Forward period must fit in unsigned 16-bit range (0..65535).")
        with self.bus.transaction():
            self.bus.command_expect_ok(f"f{motor_index}{period:04X}", address=self.address)

    def set_backward_period(self, motor_index: int, period: int) -> None:
        """Set backward period.

        Args:
            motor_index (int): Input value for this operation.
            period (int): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # set_backward_period(...)
        """
        validate_motor_index_dual(motor_index)
        if not 0 <= period <= 0xFFFF:
            raise ValueError("Backward period must fit in unsigned 16-bit range (0..65535).")
        with self.bus.transaction():
            self.bus.command_expect_ok(f"b{motor_index}{period:04X}", address=self.address)


class ElliptecRotaryStage(ElliptecAddressedDeviceBase, ElliptecClosedLoopTuningMixin, ElliptecDegreeUnitsMixin):
    """
    Shared-bus base for Thorlabs Elliptec closed-loop rotary stages (ELL14 family, etc.).

    Subclasses must set ``MODEL_CODE`` and ``MODEL_FAMILY_NAME`` class attributes.
    """
