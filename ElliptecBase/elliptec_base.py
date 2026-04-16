from __future__ import annotations

"""
Shared Elliptec device abstractions: parsing helpers and mixins composed by each product family.

**How family bases use this module** (see the corresponding ``*_base.py`` under each package):

* **Rotary** (``ElliptecRotaryStages/rotary_base.py`` — ``ElliptecRotaryStage``):
  ``ElliptecAddressedDeviceBase`` + ``ElliptecClosedLoopTuningMixin`` +
  ``ElliptecDegreeUnitsMixin``. Closed-loop motion uses ``gp``/``PO`` and ``gs``;
  tuning adds search/scan/skip/clean. Optional ``ElliptecRotaryMotorPeriods`` mixin
  on specific models (e.g. ELL14, ELL18) for ``fN``/``bN`` period commands.

* **Linear** (``ElliptecLinearStages/linear_base.py`` — ``ElliptecLinearStage``):
  ``ElliptecAddressedDeviceBase`` + ``ElliptecClosedLoopTuningMixin`` +
  ``ElliptecMillimetreUnitsMixin``. Same closed-loop pulse stack as rotary, with
  mm helpers from ``pulses_per_unit`` on the ``IN`` packet.

* **IRIS** (``ElliptecMotorized_IRIS/iris_base.py``):
  ``ElliptecIrisBase`` = ``ElliptecAddressedDeviceBase`` +
  ``ElliptecClosedLoopActuatorMixin`` + ``ElliptecMillimetreUnitsMixin`` (core motion
  and optimize; no search/scan/skip/clean). ``ElliptecIrisExtendedBase`` swaps in
  ``ElliptecClosedLoopTuningMixin`` for ELL15Z-style tuning/clean commands.

* **Slider** (``ElliptecMultiPositionSlider/slider_base.py`` — ``ElliptecSliderBase``):
  ``ElliptecAddressedDeviceBase`` + ``ElliptecGsQueriesMixin`` only. Indexed moves
  use ``fw``/``bw`` and BO/BS/GS completion paths defined on the slider base itself,
  not the closed-loop PO/GS wait mixins.

Parsing helpers at module level (``parse_in_device_info``, ``parse_gs_status``, etc.)
are used by the mixins and may be reused elsewhere.
"""

import dataclasses
import logging
import time
from typing import ClassVar, Iterable, List, Optional, Tuple, Type, TypeVar, Union

from ElliptecBus.elliptec_bus import (
    STATUS_MESSAGES,
    ElliptecBus,
    ElliptecDeviceError,
    ElliptecError,
    ElliptecProtocolError,
    ElliptecTimeoutError,
    Packet,
)
from ElliptecBus.elliptec_models import DeviceInfo, MotorInfo

LOGGER = logging.getLogger(__name__)

TDev = TypeVar("TDev", bound="ElliptecAddressedDeviceBase")


# ---------------------------------------------------------------------------
# Protocol parsing (shared by all device family bases)
# ---------------------------------------------------------------------------


def parse_in_device_info(packet: Packet) -> DeviceInfo:
    """Parse an ``IN`` reply frame into ``DeviceInfo`` fields.

    Args:
        packet (Packet): Input value for this operation.

    Returns:
        DeviceInfo: Result produced by this function.

    Example:
        >>> # Example
        >>> # parse_in_device_info(...)
    """
    if packet.command != "IN" or len(packet.data) != 30:
        raise ElliptecProtocolError(f"Unexpected IN packet: {packet.raw}")

    model_code = int(packet.data[0:2], 16)
    serial_number = packet.data[2:10]
    year = int(packet.data[10:14])
    firmware_raw = packet.data[14:16]
    hardware_raw = int(packet.data[16:18], 16)
    travel = int(packet.data[18:22], 16)
    pulses_per_unit = int(packet.data[22:30], 16)

    return DeviceInfo(
        address=packet.address,
        model_code=model_code,
        serial_number=serial_number,
        year=year,
        firmware_release=f"0x{firmware_raw}",
        hardware_release=hardware_raw & 0x7F,
        is_imperial=bool(hardware_raw & 0x80),
        travel=travel,
        pulses_per_unit=pulses_per_unit,
    )


def parse_motor_info_ix(packet: Packet, motor_index: int) -> MotorInfo:
    """Parse ``I1``/``I2`` motor info reply into normalized ``MotorInfo`` values.

    Args:
        packet (Packet): Input value for this operation.
        motor_index (int): Input value for this operation.

    Returns:
        MotorInfo: Result produced by this function.

    Example:
        >>> # Example
        >>> # parse_motor_info_ix(...)
    """
    expected = f"I{motor_index}"
    if packet.command != expected:
        raise ElliptecProtocolError(f"Unexpected {expected} packet: {packet.raw}")

    if len(packet.data) != 22:
        raise ElliptecProtocolError(f"Unexpected {expected} data length: {packet.raw}")

    loop_on = packet.data[0] == "1"
    motor_ok = packet.data[1] == "1"
    current_raw = int(packet.data[2:6], 16)
    current_amps = current_raw / 1866.0
    forward_period = int(packet.data[14:18], 16)
    backward_period = int(packet.data[18:22], 16)

    return MotorInfo(
        address=packet.address,
        motor_index=motor_index,
        loop_on=loop_on,
        motor_ok=motor_ok,
        current_raw=current_raw,
        current_amps=current_amps,
        forward_period=forward_period,
        backward_period=backward_period,
    )


def parse_gs_status(packet: Packet) -> int:
    """Parse ``GS`` status/error code from a 2-hex-digit data payload.

    Args:
        packet (Packet): Input value for this operation.

    Returns:
        int: Result produced by this function.

    Example:
        >>> # Example
        >>> # parse_gs_status(...)
    """
    if packet.command != "GS" or len(packet.data) != 2:
        raise ElliptecProtocolError(f"Unexpected GS packet: {packet.raw}")
    return int(packet.data, 16)


def parse_gs_or_bs_status(packet: Packet) -> int:
    """Parse status code from either ``GS`` or button-status ``BS`` packet.

    Args:
        packet (Packet): Input value for this operation.

    Returns:
        int: Result produced by this function.

    Example:
        >>> # Example
        >>> # parse_gs_or_bs_status(...)
    """
    if packet.command not in {"GS", "BS"} or len(packet.data) != 2:
        raise ElliptecProtocolError(f"Unexpected status-like packet: {packet.raw}")
    return int(packet.data, 16)


def parse_long_payload(packet: Packet, *, expected_command: str) -> int:
    """Parse signed 32-bit payload encoded as 8 ASCII hex chars.

    Args:
        packet (Packet): Input value for this operation.
        expected_command (str): Input value for this operation.

    Returns:
        int: Result produced by this function.

    Example:
        >>> # Example
        >>> # parse_long_payload(...)
    """
    if packet.command != expected_command or len(packet.data) != 8:
        raise ElliptecProtocolError(f"Unexpected {expected_command} packet: {packet.raw}")
    return ElliptecBus.decode_long(packet.data)


def parse_po_position(packet: Packet) -> int:
    """Parse a ``PO`` packet position as signed 32-bit pulses.

    Args:
        packet (Packet): Input value for this operation.

    Returns:
        int: Result produced by this function.

    Example:
        >>> # Example
        >>> # parse_po_position(...)
    """
    return parse_long_payload(packet, expected_command="PO")


def validate_motor_index_dual(motor_index: int) -> None:
    """Validate that motor index is for dual-motor devices (1 or 2).

    Args:
        motor_index (int): Input value for this operation.

    Returns:
        None: This function does not return a value.

    Example:
        >>> # Example
        >>> # validate_motor_index_dual(...)
    """
    if motor_index not in (1, 2):
        raise ValueError("motor_index must be 1 or 2")


def validate_motor_index_in(motor_index: int, motors: tuple[int, ...]) -> None:
    """Validate that motor index is one of the supported indices for a family.

    Args:
        motor_index (int): Input value for this operation.
        motors (tuple[int, ...]): Input value for this operation.

    Returns:
        None: This function does not return a value.

    Example:
        >>> # Example
        >>> # validate_motor_index_in(...)
    """
    if motor_index not in motors:
        raise ValueError(f"motor_index must be one of {motors}")


# ---------------------------------------------------------------------------
# Bus address + discovery + IN packet
# ---------------------------------------------------------------------------


class ElliptecAddressedDeviceBase:
    """
    Shared Elliptec stack wiring: bus, address, ``IN`` discovery, and ``DeviceInfo`` cache.

    Subclasses must define ``MODEL_CODE`` and ``MODEL_FAMILY_NAME``.
    """

    MODEL_CODE: ClassVar[int]
    MODEL_FAMILY_NAME: ClassVar[str]

    DEFAULT_MOTION_TIMEOUT = 30.0

    def __init__(
        self,
        bus: ElliptecBus,
        address: Union[str, int] = "0",
        *,
        motion_timeout: float = DEFAULT_MOTION_TIMEOUT,
        auto_validate_model: bool = False,
    ) -> None:
        """Store bus/address settings and optionally verify reported model via ``IN``.

        Args:
            bus (ElliptecBus): Input value for this operation.
            address (Union[str, int]): Input value for this operation.
            motion_timeout (float): Input value for this operation.
            auto_validate_model (bool): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # __init__(...)
        """
        self.bus = bus
        self.address = self._normalize_address(address)
        self.motion_timeout = motion_timeout
        self._device_info: Optional[DeviceInfo] = None

        if auto_validate_model:
            info = self.get_info()
            if info.model_code != self.MODEL_CODE:
                raise ElliptecProtocolError(
                    f"Address {self.address} reports model {info.model_name}, not {self.MODEL_FAMILY_NAME}."
                )

    @property
    def is_connected(self) -> bool:
        """Return whether the shared serial bus is currently connected.

        Returns:
            bool: Result produced by this function.

        Example:
            >>> # Example
            >>> # is_connected(...)
        """
        return self.bus.is_connected

    @property
    def device_info(self) -> DeviceInfo:
        """Return cached ``DeviceInfo``; read once from ``IN`` when first accessed.

        Returns:
            DeviceInfo: Result produced by this function.

        Example:
            >>> # Example
            >>> # device_info(...)
        """
        if self._device_info is None:
            self._device_info = self.get_info()
        return self._device_info

    @classmethod
    def find_devices_on_bus(
        cls: Type[TDev],
        bus: ElliptecBus,
        *,
        addresses: Iterable[Union[str, int]] = "0123456789ABCDEF",
    ) -> List[TDev]:
        """Probe candidate addresses with ``in`` and construct family-matching instances.

        Args:
            bus (ElliptecBus): Input value for this operation.
            addresses (Iterable[Union[str, int]]): Input value for this operation.

        Returns:
            List[TDev]: Result produced by this function.

        Example:
            >>> # Example
            >>> # find_devices_on_bus(...)
        """
        devices: List[TDev] = []
        with bus.transaction():
            for address in addresses:
                normalized = bus.normalize_address(address)
                try:
                    pkt = bus.query("in", address=normalized, timeout=0.15)
                    info = cls._parse_info_packet(pkt)
                    if info.model_code == cls.MODEL_CODE:
                        dev = cls(bus=bus, address=normalized)
                        dev._device_info = info
                        devices.append(dev)
                except ElliptecError:
                    continue
        return devices

    def get_info(self) -> DeviceInfo:
        """Query ``in`` for this device address and return parsed ``DeviceInfo``.

        Returns:
            DeviceInfo: Result produced by this function.

        Example:
            >>> # Example
            >>> # get_info(...)
        """
        with self.bus.transaction():
            packet = self.bus.query_expect("in", address=self.address, expected_command="IN")
            info = self._parse_info_packet(packet)
            self._device_info = info
            if info.model_code != self.MODEL_CODE:
                LOGGER.warning(
                    "Device at address %s reports model %s, not %s.",
                    self.address,
                    info.model_name,
                    self.MODEL_FAMILY_NAME,
                )
            return info

    @staticmethod
    def _parse_info_packet(packet: Packet) -> DeviceInfo:
        """Parse the protocol ``IN`` payload to ``DeviceInfo``.

        Args:
            packet (Packet): Input value for this operation.

        Returns:
            DeviceInfo: Result produced by this function.

        Example:
            >>> # Example
            >>> # _parse_info_packet(...)
        """
        return parse_in_device_info(packet)

    @staticmethod
    def _parse_motor_info_packet(packet: Packet, motor_index: int) -> MotorInfo:
        """Parse ``I1``/``I2`` payload to ``MotorInfo``.

        Args:
            packet (Packet): Input value for this operation.
            motor_index (int): Input value for this operation.

        Returns:
            MotorInfo: Result produced by this function.

        Example:
            >>> # Example
            >>> # _parse_motor_info_packet(...)
        """
        return parse_motor_info_ix(packet, motor_index)

    @staticmethod
    def _normalize_address(address: Union[str, int]) -> str:
        """Normalize integer/str address input to one uppercase hex char.

        Args:
            address (Union[str, int]): Input value for this operation.

        Returns:
            str: Result produced by this function.

        Example:
            >>> # Example
            >>> # _normalize_address(...)
        """
        return ElliptecBus.normalize_address(address)

    @staticmethod
    def _encode_long(value: int) -> str:
        """Encode signed 32-bit integer as protocol ASCII hex long.

        Args:
            value (int): Input value for this operation.

        Returns:
            str: Result produced by this function.

        Example:
            >>> # Example
            >>> # _encode_long(...)
        """
        return ElliptecBus.encode_long(value)


# ---------------------------------------------------------------------------
# GS query (all families that support ``gs``)
# ---------------------------------------------------------------------------


class ElliptecGsQueriesMixin:
    """``gs`` read and GS packet parsing."""

    bus: ElliptecBus
    address: str

    def get_status(self) -> Tuple[int, str]:
        """Read module status using ``gs`` and return numeric code plus message.

        Returns:
            Tuple[int, str]: Result produced by this function.

        Example:
            >>> # Example
            >>> # get_status(...)
        """
        with self.bus.transaction():
            packet = self.bus.query_expect("gs", address=self.address, expected_command="GS")
            code = self._parse_status_packet(packet)
            return code, STATUS_MESSAGES.get(code, f"Reserved/unknown status {code}")

    def clear_error(self) -> Tuple[int, str]:
        """Read and clear the current status/error value via ``gs``.

        Returns:
            Tuple[int, str]: Result produced by this function.

        Example:
            >>> # Example
            >>> # clear_error(...)
        """
        return self.get_status()

    @staticmethod
    def _parse_status_packet(packet: Packet) -> int:
        """Parse a ``GS`` packet and return its status code.

        Args:
            packet (Packet): Input value for this operation.

        Returns:
            int: Result produced by this function.

        Example:
            >>> # Example
            >>> # _parse_status_packet(...)
        """
        return parse_gs_status(packet)


# ---------------------------------------------------------------------------
# Closed-loop ``gp``→``PO`` motion completion (rotary, linear, iris)
# ---------------------------------------------------------------------------


class ElliptecClosedLoopPoGsMixin(ElliptecGsQueriesMixin):
    """``gp`` position read and PO/GS motion completion."""

    bus: ElliptecBus
    address: str
    motion_timeout: float

    def get_position_pulses(self) -> int:
        """Query ``gp`` and return current pulse position from the ``PO`` reply.

        Returns:
            int: Result produced by this function.

        Example:
            >>> # Example
            >>> # get_position_pulses(...)
        """
        with self.bus.transaction():
            packet = self.bus.query_expect("gp", address=self.address, expected_command="PO")
            return self._parse_position_packet(packet)

    def _await_motion_completion_locked(self, *, timeout: Optional[float] = None) -> int:
        """Wait for move completion, accepting asynchronous ``GS`` busy or final ``PO``.

        Args:
            timeout (Optional[float]): Input value for this operation.

        Returns:
            int: Result produced by this function.

        Example:
            >>> # Example
            >>> # _await_motion_completion_locked(...)
        """
        deadline = time.monotonic() + (timeout if timeout is not None else self.motion_timeout)

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ElliptecTimeoutError("Timed out waiting for move completion.")

            try:
                packet = self.bus.read_packet(timeout=min(0.5, max(0.05, remaining)))
            except ElliptecTimeoutError:
                status_packet = self.bus.query_expect("gs", address=self.address, expected_command="GS", timeout=0.5)
                code = self._parse_status_packet(status_packet)

                if code == 9:
                    time.sleep(0.05)
                    continue

                if code == 0:
                    pos_packet = self.bus.query_expect("gp", address=self.address, expected_command="PO", timeout=0.5)
                    return self._parse_position_packet(pos_packet)

                raise ElliptecDeviceError(code, STATUS_MESSAGES.get(code, "Unknown status"))

            if packet.address != self.address:
                raise ElliptecProtocolError(
                    f"Received packet for address {packet.address} while waiting for address {self.address}: {packet.raw}"
                )

            if packet.command == "PO":
                return self._parse_position_packet(packet)

            if packet.command == "GS":
                code = self._parse_status_packet(packet)
                if code == 9:
                    continue
                if code == 0:
                    pos_packet = self.bus.query_expect("gp", address=self.address, expected_command="PO", timeout=0.5)
                    return self._parse_position_packet(pos_packet)
                raise ElliptecDeviceError(code, STATUS_MESSAGES.get(code, "Unknown status"))

            raise ElliptecProtocolError(f"Unexpected packet while waiting for motion completion: {packet.raw}")

    def _await_status_completion_locked(self, *, timeout: Optional[float] = None) -> int:
        """Wait until ``GS`` is no longer busy (or ``PO`` arrives) and return final status.

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

            if packet.command == "PO":
                return 0

            if packet.command != "GS":
                raise ElliptecProtocolError(f"Unexpected packet while waiting for GS completion: {packet.raw}")

            code = self._parse_status_packet(packet)
            if code == 9:
                continue
            return code

    @staticmethod
    def _parse_position_packet(packet: Packet) -> int:
        """Parse a ``PO`` packet to signed pulse position.

        Args:
            packet (Packet): Input value for this operation.

        Returns:
            int: Result produced by this function.

        Example:
            >>> # Example
            >>> # _parse_position_packet(...)
        """
        return parse_po_position(packet)

    @staticmethod
    def _parse_long_data(packet: Packet, *, expected_command: str) -> int:
        """Parse a command-specific long payload from an 8-hex-digit data field.

        Args:
            packet (Packet): Input value for this operation.
            expected_command (str): Input value for this operation.

        Returns:
            int: Result produced by this function.

        Example:
            >>> # Example
            >>> # _parse_long_data(...)
        """
        return parse_long_payload(packet, expected_command=expected_command)


# ---------------------------------------------------------------------------
# Common closed-loop actuator commands (degrees/mm-neutral pulse layer)
# ---------------------------------------------------------------------------


class ElliptecClosedLoopActuatorMixin(ElliptecClosedLoopPoGsMixin):
    """Home, jog, absolute/relative moves, offsets, velocity, EEPROM, dual-motor info, optimize."""

    bus: ElliptecBus
    address: str
    motion_timeout: float
    _device_info: Optional[DeviceInfo]

    def home(self, direction: str = "cw", *, wait: bool = True, timeout: Optional[float] = None) -> Optional[int]:
        """Send ``ho`` to move to home; optionally wait and return final pulse position.

        Args:
            direction (str): Input value for this operation.
            wait (bool): Input value for this operation.
            timeout (Optional[float]): Input value for this operation.

        Returns:
            Optional[int]: Result produced by this function.

        Example:
            >>> # Example
            >>> # home(...)
        """
        dir_code = "0" if direction.lower() in {"cw", "clockwise", "0"} else "1"
        with self.bus.transaction():
            self.bus.write("ho" + dir_code, address=self.address)
            if not wait:
                return None
            return self._await_motion_completion_locked(timeout=timeout)

    def move_absolute_pulses(self, position: int, *, wait: bool = True, timeout: Optional[float] = None) -> Optional[int]:
        
        """Send ``ma`` absolute move in pulses; optionally wait for final ``PO``.

        Args:
            position (int): Input value for this operation.
            wait (bool): Input value for this operation.
            timeout (Optional[float]): Input value for this operation.

        Returns:
            Optional[int]: Result produced by this function.

        Example:
            >>> # Example
            >>> # move_absolute_pulses(...)
        """
        with self.bus.transaction():
            self.bus.write("ma" + self._encode_long(position), address=self.address)
            if not wait:
                return None
            return self._await_motion_completion_locked(timeout=timeout)

    def move_relative_pulses(
        self,
        delta: int,
        *,
        wait: bool = True,
        timeout: Optional[float] = None,
    ) -> Optional[int]:
        """Send ``mr`` relative move in pulses; optionally wait for final ``PO``.

        Args:
            delta (int): Input value for this operation.
            wait (bool): Input value for this operation.
            timeout (Optional[float]): Input value for this operation.

        Returns:
            Optional[int]: Result produced by this function.

        Example:
            >>> # Example
            >>> # move_relative_pulses(...)
        """
        with self.bus.transaction():
            self.bus.write("mr" + self._encode_long(delta), address=self.address)
            if not wait:
                return None
            return self._await_motion_completion_locked(timeout=timeout)

    def jog_forward(self, *, wait: bool = True, timeout: Optional[float] = None) -> Optional[int]:
        """Send ``fw`` jog/forward command and optionally wait for completion.

        Args:
            wait (bool): Input value for this operation.
            timeout (Optional[float]): Input value for this operation.

        Returns:
            Optional[int]: Result produced by this function.

        Example:
            >>> # Example
            >>> # jog_forward(...)
        """
        with self.bus.transaction():
            self.bus.write("fw", address=self.address)
            if not wait:
                return None
            return self._await_motion_completion_locked(timeout=timeout)

    def jog_backward(self, *, wait: bool = True, timeout: Optional[float] = None) -> Optional[int]:
        """Send ``bw`` jog/backward command and optionally wait for completion.

        Args:
            wait (bool): Input value for this operation.
            timeout (Optional[float]): Input value for this operation.

        Returns:
            Optional[int]: Result produced by this function.

        Example:
            >>> # Example
            >>> # jog_backward(...)
        """
        with self.bus.transaction():
            self.bus.write("bw", address=self.address)
            if not wait:
                return None
            return self._await_motion_completion_locked(timeout=timeout)

    def stop(self, *, timeout: Optional[float] = None) -> Tuple[int, str]:
        """Send ``st`` motion-stop command and return resulting status tuple.

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

    def get_home_offset_pulses(self) -> int:
        """Query ``go`` and return home offset in pulses from ``HO`` reply.

        Returns:
            int: Result produced by this function.

        Example:
            >>> # Example
            >>> # get_home_offset_pulses(...)
        """
        with self.bus.transaction():
            packet = self.bus.query_expect("go", address=self.address, expected_command="HO")
            return self._parse_long_data(packet, expected_command="HO")

    def set_home_offset_pulses(self, offset: int) -> None:
        """Set home offset in pulses with ``so`` and require ``GS00`` acknowledgement.

        Args:
            offset (int): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # set_home_offset_pulses(...)
        """
        with self.bus.transaction():
            self.bus.command_expect_ok("so" + self._encode_long(offset), address=self.address)

    def get_jog_step_pulses(self) -> int:
        """Query ``gj`` and return jog step size in pulses from ``GJ`` reply.

        Returns:
            int: Result produced by this function.

        Example:
            >>> # Example
            >>> # get_jog_step_pulses(...)
        """
        with self.bus.transaction():
            packet = self.bus.query_expect("gj", address=self.address, expected_command="GJ")
            return self._parse_long_data(packet, expected_command="GJ")

    def set_jog_step_pulses(self, step: int) -> None:
        """Set jog step size in pulses with ``sj`` and require ``GS00``.

        Args:
            step (int): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # set_jog_step_pulses(...)
        """
        with self.bus.transaction():
            self.bus.command_expect_ok("sj" + self._encode_long(step), address=self.address)

    def get_velocity_percent(self) -> int:
        """Query ``gv`` and return velocity/power compensation as a percentage.

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
        """Set velocity/power compensation using ``sv`` (0..100 percent).

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
        """Persist current user/motor parameters to non-volatile memory via ``us``.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # save_user_data(...)
        """
        with self.bus.transaction():
            self.bus.command_expect_ok("us", address=self.address)

    def change_address(self, new_address: Union[str, int]) -> None:
        """Change module address with ``ca`` and update local wrapper state.

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
        """Query ``i1``/``i2`` and return parsed motor diagnostics/settings.

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
        """Set resonant forward period using ``f1``/``f2`` and require ``GS00``.

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
        """Set resonant backward period using ``b1``/``b2`` and require ``GS00``.

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

    def optimize_motors(self, *, timeout: float = 300.0) -> None:
        """Run long optimization cycle via ``om`` until non-busy completion.

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

    @staticmethod
    def _validate_motor_index(motor_index: int) -> None:
        """Default motor-index validator for dual-motor closed-loop devices.

        Args:
            motor_index (int): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # _validate_motor_index(...)
        """
        validate_motor_index_dual(motor_index)


class ElliptecClosedLoopTuningMixin(ElliptecClosedLoopActuatorMixin):
    """Frequency search, current-curve scan, skip, and clean mechanics (not on all iris models)."""

    def search_frequency(self, motor_index: int, *, timeout: float = 20.0) -> None:
        """Run resonance search for one motor using ``s1``/``s2``.

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
        """Run current-curve scan (``c1``/``c2``) and return ``C1``/``C2`` packet.

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

    def skip_frequency_search(self) -> None:
        """Enable startup skip-frequency behavior using the ``sk`` command.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # skip_frequency_search(...)
        """
        with self.bus.transaction():
            self.bus.command_expect_ok("sk", address=self.address)

    def clean_mechanics(self, *, timeout: float = 300.0) -> None:
        """Run maintenance cleaning cycle via ``cm`` until completion.

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


# ---------------------------------------------------------------------------
# Millimetre helpers (linear + iris)
# ---------------------------------------------------------------------------


class ElliptecMillimetreUnitsMixin:
    """``pulses_per_unit`` from ``IN`` interpreted as pulses per millimetre."""

    device_info: DeviceInfo

    def pulses_per_mm(self) -> int:
        """Return pulses-per-millimetre conversion factor from ``IN`` info.

        Returns:
            int: Result produced by this function.

        Example:
            >>> # Example
            >>> # pulses_per_mm(...)
        """
        return self.device_info.pulses_per_unit

    def mm_to_pulses(self, mm: float) -> int:
        """Convert physical distance in mm to integer pulse units.

        Args:
            mm (float): Input value for this operation.

        Returns:
            int: Result produced by this function.

        Example:
            >>> # Example
            >>> # mm_to_pulses(...)
        """
        return int(round(mm * self.pulses_per_mm()))

    def pulses_to_mm(self, pulses: int) -> float:
        """Convert pulse counts to physical distance in mm.

        Args:
            pulses (int): Input value for this operation.

        Returns:
            float: Result produced by this function.

        Example:
            >>> # Example
            >>> # pulses_to_mm(...)
        """
        return pulses / self.pulses_per_mm()

    def get_position_mm(self) -> float:
        """Return current position converted from pulses to millimetres.

        Returns:
            float: Result produced by this function.

        Example:
            >>> # Example
            >>> # get_position_mm(...)
        """
        return self.pulses_to_mm(self.get_position_pulses())

    def move_absolute_mm(self, mm: float, *, wait: bool = True, timeout: Optional[float] = None) -> Optional[float]:
        """Move to an absolute millimetre position using pulse conversion helpers.

        Args:
            mm (float): Input value for this operation.
            wait (bool): Input value for this operation.
            timeout (Optional[float]): Input value for this operation.

        Returns:
            Optional[float]: Result produced by this function.

        Example:
            >>> # Example
            >>> # move_absolute_mm(...)
        """
        result = self.move_absolute_pulses(self.mm_to_pulses(mm), wait=wait, timeout=timeout)
        return None if result is None else self.pulses_to_mm(result)

    def move_relative_mm(self, delta_mm: float, *, wait: bool = True, timeout: Optional[float] = None) -> Optional[float]:
        """Move by a relative millimetre offset using pulse conversion helpers.

        Args:
            delta_mm (float): Input value for this operation.
            wait (bool): Input value for this operation.
            timeout (Optional[float]): Input value for this operation.

        Returns:
            Optional[float]: Result produced by this function.

        Example:
            >>> # Example
            >>> # move_relative_mm(...)
        """
        result = self.move_relative_pulses(self.mm_to_pulses(delta_mm), wait=wait, timeout=timeout)
        return None if result is None else self.pulses_to_mm(result)

    def get_home_offset_mm(self) -> float:
        """Return home offset converted from pulses to millimetres.

        Returns:
            float: Result produced by this function.

        Example:
            >>> # Example
            >>> # get_home_offset_mm(...)
        """
        return self.pulses_to_mm(self.get_home_offset_pulses())

    def set_home_offset_mm(self, mm: float) -> None:
        """Set home offset from millimetres after pulse conversion.

        Args:
            mm (float): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # set_home_offset_mm(...)
        """
        self.set_home_offset_pulses(self.mm_to_pulses(mm))

    def get_jog_step_mm(self) -> float:
        """Return jog step converted from pulses to millimetres.

        Returns:
            float: Result produced by this function.

        Example:
            >>> # Example
            >>> # get_jog_step_mm(...)
        """
        return self.pulses_to_mm(self.get_jog_step_pulses())

    def set_jog_step_mm(self, mm: float) -> None:
        """Set jog step in millimetres after pulse conversion.

        Args:
            mm (float): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # set_jog_step_mm(...)
        """
        self.set_jog_step_pulses(self.mm_to_pulses(mm))


# ---------------------------------------------------------------------------
# Degrees helpers (rotary)
# ---------------------------------------------------------------------------


class ElliptecDegreeUnitsMixin:
    """``pulses_per_unit`` from ``IN`` interpreted as pulses per revolution."""

    device_info: DeviceInfo

    def pulses_per_revolution(self) -> int:
        """Return pulses-per-revolution conversion factor from ``IN`` info.

        Returns:
            int: Result produced by this function.

        Example:
            >>> # Example
            >>> # pulses_per_revolution(...)
        """
        return self.device_info.pulses_per_unit

    def degrees_to_pulses(self, degrees: float) -> int:
        """Convert degrees to integer pulse counts for rotary devices.

        Args:
            degrees (float): Input value for this operation.

        Returns:
            int: Result produced by this function.

        Example:
            >>> # Example
            >>> # degrees_to_pulses(...)
        """
        return int(round((degrees / 360.0) * self.pulses_per_revolution()))

    def pulses_to_degrees(self, pulses: int) -> float:
        """Convert pulse counts to degrees for rotary devices.

        Args:
            pulses (int): Input value for this operation.

        Returns:
            float: Result produced by this function.

        Example:
            >>> # Example
            >>> # pulses_to_degrees(...)
        """
        return (pulses / self.pulses_per_revolution()) * 360.0

    def get_position_degrees(self) -> float:
        """Return current position converted from pulses to degrees.

        Returns:
            float: Result produced by this function.

        Example:
            >>> # Example
            >>> # get_position_degrees(...)
        """
        return self.pulses_to_degrees(self.get_position_pulses())

    def move_absolute_degrees(self, degrees: float, *, wait: bool = True, timeout: Optional[float] = None) -> Optional[float]:
        """Move to an absolute angle in degrees using pulse conversion helpers.

        Args:
            degrees (float): Input value for this operation.
            wait (bool): Input value for this operation.
            timeout (Optional[float]): Input value for this operation.

        Returns:
            Optional[float]: Result produced by this function.

        Example:
            >>> # Example
            >>> # move_absolute_degrees(...)
        """
        result = self.move_absolute_pulses(self.degrees_to_pulses(degrees), wait=wait, timeout=timeout)
        return None if result is None else self.pulses_to_degrees(result)

    def move_relative_degrees(self, delta_degrees: float, *, wait: bool = True, timeout: Optional[float] = None) -> Optional[float]:
    
        """Move by a relative angular offset in degrees.

        Args:
            delta_degrees (float): Input value for this operation.
            wait (bool): Input value for this operation.
            timeout (Optional[float]): Input value for this operation.

        Returns:
            Optional[float]: Result produced by this function.

        Example:
            >>> # Example
            >>> # move_relative_degrees(...)
        """
        result = self.move_relative_pulses(self.degrees_to_pulses(delta_degrees), wait=wait, timeout=timeout)
        return None if result is None else self.pulses_to_degrees(result)

    def get_home_offset_degrees(self) -> float:
        """Return home offset converted from pulses to degrees.

        Returns:
            float: Result produced by this function.

        Example:
            >>> # Example
            >>> # get_home_offset_degrees(...)
        """
        return self.pulses_to_degrees(self.get_home_offset_pulses())

    def set_home_offset_degrees(self, degrees: float) -> None:
        """Set home offset in degrees after conversion to pulses.

        Args:
            degrees (float): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # set_home_offset_degrees(...)
        """
        self.set_home_offset_pulses(self.degrees_to_pulses(degrees))

    def get_jog_step_degrees(self) -> float:
        """Return jog step converted from pulses to degrees.

        Returns:
            float: Result produced by this function.

        Example:
            >>> # Example
            >>> # get_jog_step_degrees(...)
        """
        return self.pulses_to_degrees(self.get_jog_step_pulses())

    def set_jog_step_degrees(self, degrees: float) -> None:
        """Set jog step in degrees after conversion to pulses.

        Args:
            degrees (float): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # set_jog_step_degrees(...)
        """
        self.set_jog_step_pulses(self.degrees_to_pulses(degrees))
