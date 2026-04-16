from __future__ import annotations

import dataclasses
import time
from typing import ClassVar, Optional, Tuple, Union

from ElliptecBase.elliptec_base import (
    ElliptecAddressedDeviceBase,
    ElliptecGsQueriesMixin,
    parse_gs_or_bs_status,
    validate_motor_index_in,
)
from ElliptecBus.elliptec_bus import (
    STATUS_MESSAGES,
    ElliptecDeviceError,
    ElliptecProtocolError,
    ElliptecTimeoutError,
    Packet,
)
from ElliptecBus.elliptec_models import MotorInfo


class ElliptecSliderBase(ElliptecAddressedDeviceBase, ElliptecGsQueriesMixin):
    """
    Shared-bus base for Thorlabs Elliptec multi-position sliders (ELL6 family, ELL9, ELL12, …).

    Subclasses must set ``MODEL_CODE``, ``MODEL_FAMILY_NAME``, and ``MOTORS`` (indices
    supported by ``iN`` / ``sN`` / ``cN`` on that hardware).
    """

    MOTORS: ClassVar[tuple[int, ...]] = (1, 2)

    def forward(self, *, wait: bool = True, timeout: Optional[float] = None) -> Optional[Packet]:
        """Forward.

        Args:
            wait (bool): Input value for this operation.
            timeout (Optional[float]): Input value for this operation.

        Returns:
            Optional[Packet]: Result produced by this function.

        Example:
            >>> # Example
            >>> # forward(...)
        """
        with self.bus.transaction():
            self.bus.write("fw", address=self.address)
            if not wait:
                return None
            return self._await_indexed_motion_completion_locked(timeout=timeout)

    def backward(self, *, wait: bool = True, timeout: Optional[float] = None) -> Optional[Packet]:
        """Backward.

        Args:
            wait (bool): Input value for this operation.
            timeout (Optional[float]): Input value for this operation.

        Returns:
            Optional[Packet]: Result produced by this function.

        Example:
            >>> # Example
            >>> # backward(...)
        """
        with self.bus.transaction():
            self.bus.write("bw", address=self.address)
            if not wait:
                return None
            return self._await_indexed_motion_completion_locked(timeout=timeout)

    def stop(self, *, timeout: Optional[float] = None) -> Tuple[int, str]:
        """Stop.

        Args:
            timeout (Optional[float]): Input value for this operation.

        Returns:
            Tuple[int, str]: Result produced by this function.

        Example:
            >>> # Example
            >>> # stop(...)
        """
        with self.bus.transaction():
            self.bus.write("st", address=self.address)
            code = self._await_status_completion_locked(timeout=timeout)
            return code, STATUS_MESSAGES.get(code, f"Reserved/unknown status {code}")

    def get_velocity_percent(self) -> int:
        """Get velocity percent.

        Returns:
            int: Result produced by this function.

        Example:
            >>> # Example
            >>> # get_velocity_percent(...)
        """
        with self.bus.transaction():
            packet = self.bus.query_expect("gv", address=self.address, expected_command="GV")
            if len(packet.data) != 2:
                raise ElliptecProtocolError(f"Unexpected GV packet: {packet.raw}")
            return int(packet.data, 16)

    def set_velocity_percent(self, percent: int) -> None:
        """Set velocity percent.

        Args:
            percent (int): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # set_velocity_percent(...)
        """
        if not 0 <= percent <= 100:
            raise ValueError("Velocity must be between 0 and 100 percent.")
        with self.bus.transaction():
            self.bus.command_expect_ok("sv" + f"{percent:02X}", address=self.address)

    def save_user_data(self) -> None:
        """Save user data.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # save_user_data(...)
        """
        with self.bus.transaction():
            self.bus.command_expect_ok("us", address=self.address)

    def skip_frequency_search(self) -> None:
        """Skip frequency search.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # skip_frequency_search(...)
        """
        with self.bus.transaction():
            self.bus.command_expect_ok("sk", address=self.address)

    def change_address(self, new_address: Union[str, int]) -> None:
        """Change address.

        Args:
            new_address (Union[str, int]): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # change_address(...)
        """
        normalized = self._normalize_address(new_address)
        with self.bus.transaction():
            packet = self.bus.query_expect("ca" + normalized, address=self.address, expected_command="GS")
            code = self._parse_status_packet(packet)
            if code != 0:
                raise ElliptecDeviceError(code, STATUS_MESSAGES.get(code, "Unknown status"))

        self.address = normalized
        if self._device_info is not None:
            self._device_info = dataclasses.replace(self._device_info, address=normalized)

    def get_motor_info(self, motor_index: int) -> MotorInfo:
        """Get motor info.

        Args:
            motor_index (int): Input value for this operation.

        Returns:
            MotorInfo: Result produced by this function.

        Example:
            >>> # Example
            >>> # get_motor_info(...)
        """
        self._validate_motor_index(motor_index)
        with self.bus.transaction():
            packet = self.bus.query_expect(
                f"i{motor_index}",
                address=self.address,
                expected_command=f"I{motor_index}",
            )
            return self._parse_motor_info_packet(packet, motor_index)

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
        self._validate_motor_index(motor_index)
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
        self._validate_motor_index(motor_index)
        if not 0 <= period <= 0xFFFF:
            raise ValueError("Backward period must fit in unsigned 16-bit range (0..65535).")
        with self.bus.transaction():
            self.bus.command_expect_ok(f"b{motor_index}{period:04X}", address=self.address)

    def search_frequency(self, motor_index: int, *, timeout: float = 20.0) -> None:
        """Search frequency.

        Args:
            motor_index (int): Input value for this operation.
            timeout (float): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # search_frequency(...)
        """
        self._validate_motor_index(motor_index)
        with self.bus.transaction():
            self.bus.write(f"s{motor_index}", address=self.address)
            code = self._await_status_completion_locked(timeout=max(timeout, self.motion_timeout))
            if code != 0:
                raise ElliptecDeviceError(code, STATUS_MESSAGES.get(code, "Unknown status"))

    def scan_current_curve(self, motor_index: int, *, timeout: float = 20.0) -> Packet:
        """Scan current curve.

        Args:
            motor_index (int): Input value for this operation.
            timeout (float): Input value for this operation.

        Returns:
            Packet: Result produced by this function.

        Example:
            >>> # Example
            >>> # scan_current_curve(...)
        """
        self._validate_motor_index(motor_index)
        expected = f"C{motor_index}"

        with self.bus.transaction():
            self.bus.write(f"c{motor_index}", address=self.address)
            code = self._await_status_completion_locked(timeout=max(timeout, self.motion_timeout))
            if code != 0:
                raise ElliptecDeviceError(code, STATUS_MESSAGES.get(code, "Unknown status"))

            packet = self.bus.read_packet(timeout=max(15.0, timeout))
            if packet.address != self.address or packet.command != expected:
                raise ElliptecProtocolError(f"Expected {self.address}{expected}, got {packet.raw}")
            return packet

    def optimize_motors(self, *, timeout: float = 300.0) -> None:
        """Optimize motors.

        Args:
            timeout (float): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # optimize_motors(...)
        """
        with self.bus.transaction():
            self.bus.write("om", address=self.address)
            code = self._await_status_completion_locked(timeout=timeout)
            if code != 0:
                raise ElliptecDeviceError(code, STATUS_MESSAGES.get(code, "Unknown status"))

    def clean_mechanics(self, *, timeout: float = 300.0) -> None:
        """Clean mechanics.

        Args:
            timeout (float): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # clean_mechanics(...)
        """
        with self.bus.transaction():
            self.bus.write("cm", address=self.address)
            code = self._await_status_completion_locked(timeout=timeout)
            if code != 0:
                raise ElliptecDeviceError(code, STATUS_MESSAGES.get(code, "Unknown status"))

    def read_button_event(self, *, timeout: Optional[float] = None) -> Packet:
        """Read button event.

        Args:
            timeout (Optional[float]): Input value for this operation.

        Returns:
            Packet: Result produced by this function.

        Example:
            >>> # Example
            >>> # read_button_event(...)
        """
        with self.bus.transaction():
            packet = self.bus.read_packet(timeout=timeout)
            if packet.address != self.address:
                raise ElliptecProtocolError(
                    f"Received packet for address {packet.address} while expecting {self.address}: {packet.raw}"
                )
            if packet.command not in {"BS", "BO"}:
                raise ElliptecProtocolError(f"Expected BS or BO packet, got {packet.raw}")
            return packet

    def _await_indexed_motion_completion_locked(
        self,
        *,
        timeout: Optional[float] = None,
    ) -> Packet:
        """ await indexed motion completion locked.

        Args:
            timeout (Optional[float]): Input value for this operation.

        Returns:
            Packet: Result produced by this function.

        Example:
            >>> # Example
            >>> # _await_indexed_motion_completion_locked(...)
        """
        deadline = time.monotonic() + (timeout if timeout is not None else self.motion_timeout)

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ElliptecTimeoutError("Timed out waiting for indexed move completion.")

            try:
                packet = self.bus.read_packet(timeout=min(0.5, max(0.05, remaining)))
            except ElliptecTimeoutError:
                status_packet = self.bus.query_expect("gs", address=self.address, expected_command="GS", timeout=0.5)
                code = self._parse_status_packet(status_packet)

                if code == 9:
                    time.sleep(0.05)
                    continue

                if code == 0:
                    return status_packet

                raise ElliptecDeviceError(code, STATUS_MESSAGES.get(code, "Unknown status"))

            if packet.address != self.address:
                raise ElliptecProtocolError(
                    f"Received packet for address {packet.address} while waiting for address {self.address}: {packet.raw}"
                )

            if packet.command == "BO":
                return packet

            if packet.command in {"BS", "GS"}:
                code = self._parse_status_like_packet(packet)
                if code == 9:
                    continue
                if code == 0:
                    return packet
                raise ElliptecDeviceError(code, STATUS_MESSAGES.get(code, "Unknown status"))

            raise ElliptecProtocolError(f"Unexpected packet while waiting for indexed move completion: {packet.raw}")

    def _await_status_completion_locked(
        self,
        *,
        timeout: Optional[float] = None,
    ) -> int:
        """ await status completion locked.

        Args:
            timeout (Optional[float]): Input value for this operation.

        Returns:
            int: Result produced by this function.

        Example:
            >>> # Example
            >>> # _await_status_completion_locked(...)
        """
        deadline = time.monotonic() + (timeout if timeout is not None else self.motion_timeout)

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ElliptecTimeoutError("Timed out waiting for status completion.")

            packet = self.bus.read_packet(timeout=max(0.05, min(0.5, remaining)))

            if packet.address != self.address:
                raise ElliptecProtocolError(
                    f"Received packet for address {packet.address} while waiting for address {self.address}: {packet.raw}"
                )

            if packet.command == "BO":
                return 0

            if packet.command in {"GS", "BS"}:
                code = self._parse_status_like_packet(packet)
                if code == 9:
                    continue
                return code

            raise ElliptecProtocolError(f"Unexpected packet while waiting for status completion: {packet.raw}")

    @classmethod
    def _validate_motor_index(cls, motor_index: int) -> None:
        """ validate motor index.

        Args:
            motor_index (int): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # _validate_motor_index(...)
        """
        validate_motor_index_in(motor_index, cls.MOTORS)

    @staticmethod
    def _parse_status_like_packet(packet: Packet) -> int:
        """ parse status like packet.

        Args:
            packet (Packet): Input value for this operation.

        Returns:
            int: Result produced by this function.

        Example:
            >>> # Example
            >>> # _parse_status_like_packet(...)
        """
        return parse_gs_or_bs_status(packet)
