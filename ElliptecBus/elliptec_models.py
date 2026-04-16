from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class DeviceInfo:
    address: str
    model_code: int
    serial_number: str
    year: int
    firmware_release: str
    hardware_release: int
    is_imperial: bool
    travel: int
    pulses_per_unit: int

    @property
    def model_name(self) -> str:
        """Model name.

        Returns:
            str: Result produced by this function.

        Example:
            >>> # Example
            >>> # model_name(...)
        """
        return f"ELL{self.model_code}"


@dataclasses.dataclass(frozen=True)
class MotorInfo:
    address: str
    motor_index: int
    loop_on: bool
    motor_ok: bool
    current_raw: int
    current_amps: float
    forward_period: int
    backward_period: int
