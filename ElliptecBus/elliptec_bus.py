from __future__ import annotations

import dataclasses
import threading
import time
from contextlib import contextmanager
from typing import Iterable, Iterator, List, Optional, Union

import serial
from serial import Serial
from serial.tools import list_ports


_ADDRESS_CHARS = "0123456789ABCDEF"


class ElliptecError(Exception):
    """Base exception for Elliptec communication and device errors."""


class ElliptecTimeoutError(ElliptecError):
    """Raised when the device does not respond in time."""


class ElliptecProtocolError(ElliptecError):
    """Raised when an unexpected or malformed packet is received."""


class ElliptecDeviceError(ElliptecError):
    """Raised when a device returns a non-zero GS status."""

    def __init__(self, code: int, message: str):
        """Build an exception from a GS status code and its text description.

        Args:
            code (int): Input value for this operation.
            message (str): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # __init__(...)
        """
        super().__init__(f"Elliptec status {code}: {message}")
        self.code = code
        self.status_message = message


STATUS_MESSAGES = {
    0: "OK, no error",
    1: "Communication time out",
    2: "Mechanical time out",
    3: "Command error or not supported",
    4: "Value out of range",
    5: "Module isolated",
    6: "Module out of isolation",
    7: "Initializing error",
    8: "Thermal error",
    9: "Busy",
    10: "Sensor error",
    11: "Motor error",
    12: "Out of range",
    13: "Over current error",
}


@dataclasses.dataclass(frozen=True)
class Packet:
    """Parsed Elliptec frame: ``<address><command><hex-ascii-data>``."""

    raw: str
    address: str
    command: str
    data: str


class ElliptecBus:
    """
    Shared serial bus for one ELLC / ELLB / distribution-board connection.

    One bus instance owns exactly one COM port. Multiple device wrappers
    can share this bus safely by using addressed commands and bus transactions.
    """

    DEFAULT_BAUDRATE = 9600
    DEFAULT_TIMEOUT = 0.25
    DEFAULT_WRITE_TIMEOUT = 1.0
    DEFAULT_SETTLE_DELAY = 0.02

    def __init__(self, port: str, *, baudrate: int = DEFAULT_BAUDRATE, timeout: float = DEFAULT_TIMEOUT, write_timeout: float = DEFAULT_WRITE_TIMEOUT, settle_delay: float = DEFAULT_SETTLE_DELAY, auto_connect: bool = True) -> None:
        """Create a bus bound to one serial interface.

        Args:
            port (str): Input value for this operation.
            baudrate (int): Input value for this operation.
            timeout (float): Input value for this operation.
            write_timeout (float): Input value for this operation.
            settle_delay (float): Input value for this operation.
            auto_connect (bool): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # __init__(...)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.write_timeout = write_timeout
        self.settle_delay = settle_delay

        self._serial: Optional[Serial] = None
        self._lock = threading.RLock()

        if auto_connect:
            self.connect()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    def connect(self) -> None:
        """Open the serial port and initialize bus buffers.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # connect(...)
        """
        with self._lock:
            if self.is_connected:
                return

            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
                write_timeout=self.write_timeout,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
            )
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            time.sleep(self.settle_delay)

    def close(self) -> None:
        """Close the serial port owned by this bus instance.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # close(...)
        """
        with self._lock:
            if self._serial is not None:
                self._serial.close()
                self._serial = None

    def __enter__(self) -> "ElliptecBus":
        """Context-manager entry: ensure the serial transport is connected.

        Returns:
            'ElliptecBus': Result produced by this function.

        Example:
            >>> # Example
            >>> # __enter__(...)
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """Context-manager exit: close the serial transport.

        Args:
            exc_type (Any): Input value for this operation.
            exc (Any): Input value for this operation.
            tb (Any): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # __exit__(...)
        """
        self.close()

    @property
    def is_connected(self) -> bool:
        """Return ``True`` when the underlying serial handle is open.

        Returns:
            bool: Result produced by this function.

        Example:
            >>> # Example
            >>> # is_connected(...)
        """
        return self._serial is not None and self._serial.is_open

    @classmethod
    def available_ports(cls) -> List[str]:
        """Enumerate serial ports currently visible to the OS.

        Returns:
            List[str]: Result produced by this function.

        Example:
            >>> # Example
            >>> # available_ports(...)
        """
        return [p.device for p in list_ports.comports()]

    def flush_buffers(self) -> None:
        """Purge RX/TX buffers to discard pending bytes on the transport.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # flush_buffers(...)
        """
        with self._lock:
            ser = self._require_serial()
            ser.reset_input_buffer()
            ser.reset_output_buffer()

    # ------------------------------------------------------------------
    # Transaction
    # ------------------------------------------------------------------
    @contextmanager
    def transaction(self) -> Iterator["ElliptecBus"]:
        """Hold exclusive access to the shared bus for a full multi-step exchange.

        Returns:
            Iterator['ElliptecBus']: Result produced by this function.

        Example:
            >>> # Example
            >>> # transaction(...)
        """
        with self._lock:
            yield self

    # ------------------------------------------------------------------
    # Low-level operations
    # ------------------------------------------------------------------
    def write(self, payload: str, *, address: Optional[Union[str, int]] = None) -> None:
        """Send one host command frame.

        Args:
            payload (str): Input value for this operation.
            address (Optional[Union[str, int]]): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # write(...)
        """
        ser = self._require_serial()
        message = self._build_message(payload, address=address)
        ser.write(message.encode("ascii"))
        ser.flush()

    def read_packet(self, *, timeout: Optional[float] = None) -> Packet:
        """Read one device frame terminated by ``CRLF`` and parse it.

        Args:
            timeout (Optional[float]): Input value for this operation.

        Returns:
            Packet: Result produced by this function.

        Example:
            >>> # Example
            >>> # read_packet(...)
        """
        ser = self._require_serial()
        line = self._readline(ser, timeout)
        return self.parse_packet(line)

    def query(self, payload: str, *, address: Union[str, int], timeout: Optional[float] = None) -> Packet:
        """Send one command and return the next parsed packet response.

        Args:
            payload (str): Input value for this operation.
            address (Union[str, int]): Input value for this operation.
            timeout (Optional[float]): Input value for this operation.

        Returns:
            Packet: Result produced by this function.

        Example:
            >>> # Example
            >>> # query(...)
        """
        self.write(payload, address=address)
        return self.read_packet(timeout=timeout)

    def query_expect(
        self,
        payload: str,
        *,
        address: Union[str, int],
        expected_command: str,
        timeout: Optional[float] = None,
    ) -> Packet:
        """Send one command and validate the response address and command mnemonic.

        Args:
            payload (str): Input value for this operation.
            address (Union[str, int]): Input value for this operation.
            expected_command (str): Input value for this operation.
            timeout (Optional[float]): Input value for this operation.

        Returns:
            Packet: Result produced by this function.

        Example:
            >>> # Example
            >>> # query_expect(...)
        """
        packet = self.query(payload, address=address, timeout=timeout)
        normalized = self._normalize_address(address)

        if packet.address != normalized:
            raise ElliptecProtocolError(
                f"Expected address {normalized!r}, got {packet.address!r} in packet {packet.raw!r}."
            )
        if packet.command != expected_command.upper():
            raise ElliptecProtocolError(
                f"Expected command {expected_command.upper()!r}, got {packet.command!r} in packet {packet.raw!r}."
            )
        return packet

    def command_expect_ok(
        self,
        payload: str,
        *,
        address: Union[str, int],
        timeout: Optional[float] = None,
    ) -> None:
        """Send a command that is expected to acknowledge with ``GS00``.

        Args:
            payload (str): Input value for this operation.
            address (Union[str, int]): Input value for this operation.
            timeout (Optional[float]): Input value for this operation.

        Returns:
            None: This function does not return a value.

        Example:
            >>> # Example
            >>> # command_expect_ok(...)
        """
        packet = self.query_expect(payload, address=address, expected_command="GS", timeout=timeout)
        if len(packet.data) != 2:
            raise ElliptecProtocolError(f"Unexpected GS packet: {packet.raw!r}")
        code = int(packet.data, 16)
        if code != 0:
            raise ElliptecDeviceError(code, STATUS_MESSAGES.get(code, "Unknown status"))

    def scan_addresses(
        self,
        addresses: Iterable[Union[str, int]] = _ADDRESS_CHARS,
        *,
        timeout: float = 0.15,
    ) -> List[str]:
        """Probe candidate addresses using ``in`` and return addresses that reply with ``IN``.

        Args:
            addresses (Iterable[Union[str, int]]): Input value for this operation.
            timeout (float): Input value for this operation.

        Returns:
            List[str]: Result produced by this function.

        Example:
            >>> # Example
            >>> # scan_addresses(...)
        """
        found: List[str] = []
        with self.transaction():
            for address in addresses:
                normalized = self._normalize_address(address)
                try:
                    packet = self.query("in", address=normalized, timeout=timeout)
                except ElliptecError:
                    continue
                if packet.command == "IN" and packet.address == normalized:
                    found.append(normalized)
        return found

    # ------------------------------------------------------------------
    # Parsing / encoding helpers
    # ------------------------------------------------------------------
    @staticmethod
    def parse_packet(raw: str) -> Packet:
        """Parse one raw ASCII line into ``Packet(address, command, data)``.

        Args:
            raw (str): Input value for this operation.

        Returns:
            Packet: Result produced by this function.

        Example:
            >>> # Example
            >>> # parse_packet(...)
        """
        raw = raw.strip()
        if len(raw) < 3:
            raise ElliptecProtocolError(f"Packet too short: {raw!r}")

        address = raw[0].upper()
        if address not in _ADDRESS_CHARS:
            raise ElliptecProtocolError(f"Invalid packet address: {raw!r}")

        command = raw[1:3].upper()
        data = raw[3:].upper()
        return Packet(raw=raw, address=address, command=command, data=data)

    @staticmethod
    def normalize_address(address: Union[str, int]) -> str:
        """Normalize address input to a single uppercase hex nibble ``0..F``.

        Args:
            address (Union[str, int]): Input value for this operation.

        Returns:
            str: Result produced by this function.

        Example:
            >>> # Example
            >>> # normalize_address(...)
        """
        return ElliptecBus._normalize_address(address)

    @staticmethod
    def encode_long(value: int) -> str:
        """Encode signed 32-bit value as 8 ASCII hex chars (two's complement).

        Args:
            value (int): Input value for this operation.

        Returns:
            str: Result produced by this function.

        Example:
            >>> # Example
            >>> # encode_long(...)
        """
        if not -(2**31) <= value < 2**31:
            raise ValueError("Value does not fit in signed 32-bit range.")
        return f"{(value & 0xFFFFFFFF):08X}"

    @staticmethod
    def decode_long(hex_ascii: str) -> int:
        """Decode 8 ASCII hex chars into a signed 32-bit integer.

        Args:
            hex_ascii (str): Input value for this operation.

        Returns:
            int: Result produced by this function.

        Example:
            >>> # Example
            >>> # decode_long(...)
        """
        if len(hex_ascii) != 8:
            raise ElliptecProtocolError(f"Expected 8 hex chars for long, got {hex_ascii!r}")
        unsigned = int(hex_ascii, 16)
        return unsigned - 0x100000000 if unsigned & 0x80000000 else unsigned

    @staticmethod
    def decode_word(hex_ascii: str) -> int:
        """Decode 4 ASCII hex chars into an unsigned 16-bit integer.

        Args:
            hex_ascii (str): Input value for this operation.

        Returns:
            int: Result produced by this function.

        Example:
            >>> # Example
            >>> # decode_word(...)
        """
        if len(hex_ascii) != 4:
            raise ElliptecProtocolError(f"Expected 4 hex chars for word, got {hex_ascii!r}")
        return int(hex_ascii, 16)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _require_serial(self) -> Serial:
        """Return the live serial handle or raise if the bus is disconnected.

        Returns:
            Serial: Result produced by this function.

        Example:
            >>> # Example
            >>> # _require_serial(...)
        """
        if not self.is_connected:
            raise ElliptecError("Elliptec bus is not connected.")
        assert self._serial is not None
        return self._serial

    @staticmethod
    def _normalize_address(address: Union[str, int]) -> str:
        """Internal address normalizer shared by public and private call paths.

        Args:
            address (Union[str, int]): Input value for this operation.

        Returns:
            str: Result produced by this function.

        Example:
            >>> # Example
            >>> # _normalize_address(...)
        """
        if isinstance(address, int):
            if not 0 <= address <= 15:
                raise ValueError("Address integer must be in range 0..15.")
            return _ADDRESS_CHARS[address]

        address_str = str(address).strip().upper()
        if len(address_str) != 1 or address_str not in _ADDRESS_CHARS:
            raise ValueError(f"Address must be a single hex character in 0-F, got {address!r}.")
        return address_str

    @staticmethod
    def _build_message(payload: str, *, address: Optional[Union[str, int]]) -> str:
        """Build the final command string to send on the wire.

        Args:
            payload (str): Input value for this operation.
            address (Optional[Union[str, int]]): Input value for this operation.

        Returns:
            str: Result produced by this function.

        Example:
            >>> # Example
            >>> # _build_message(...)
        """
        payload = str(payload).strip()
        if not payload:
            raise ValueError("Payload cannot be empty.")

        # If caller already provided a full addressed message like "0gp",
        # keep it as-is.
        if len(payload) >= 3 and payload[0].upper() in _ADDRESS_CHARS:
            return payload

        if address is None:
            raise ValueError("Address is required when payload is not already addressed.")

        return ElliptecBus._normalize_address(address) + payload

    @staticmethod
    def _readline(ser: Serial, timeout: Optional[float]) -> str:
        """Read until protocol terminator ``CRLF`` and decode as strict ASCII.

        Args:
            ser (Serial): Input value for this operation.
            timeout (Optional[float]): Input value for this operation.

        Returns:
            str: Result produced by this function.

        Example:
            >>> # Example
            >>> # _readline(...)
        """
        old_timeout = ser.timeout
        if timeout is not None:
            ser.timeout = timeout

        try:
            line = ser.read_until(b"\r\n")
        finally:
            if timeout is not None:
                ser.timeout = old_timeout

        if not line:
            raise ElliptecTimeoutError("Timed out waiting for Elliptec response.")

        try:
            return line.decode("ascii", errors="strict").strip()
        except UnicodeDecodeError as exc:
            raise ElliptecProtocolError("Received non-ASCII data from Elliptec bus.") from exc