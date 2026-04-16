from __future__ import annotations

from ElliptecBase.elliptec_base import (
    ElliptecAddressedDeviceBase,
    ElliptecClosedLoopActuatorMixin,
    ElliptecClosedLoopTuningMixin,
    ElliptecMillimetreUnitsMixin,
)


class ElliptecIrisBase(ElliptecAddressedDeviceBase, ElliptecClosedLoopActuatorMixin, ElliptecMillimetreUnitsMixin):
    """
    Shared-bus base for Thorlabs Elliptec motorized iris devices (ELL15, ELL15Z, …).

    Uses the same closed-loop mm / pulse motion model as linear stages. Some iris
    models omit certain maintenance / tuning commands; those live on
    :class:`ElliptecIrisExtendedBase`.

    Subclasses must set ``MODEL_CODE`` and ``MODEL_FAMILY_NAME`` class attributes.
    """

    def get_iris_value_mm(self) -> float:
        """Get iris value mm.

        Returns:
            float: Result produced by this function.

        Example:
            >>> # Example
            >>> # get_iris_value_mm(...)
        """
        return self.get_position_mm()


class ElliptecIrisExtendedBase(
    ElliptecAddressedDeviceBase,
    ElliptecClosedLoopTuningMixin,
    ElliptecMillimetreUnitsMixin,
):
    """Iris devices that also expose frequency search, current-curve scan, skip, and clean mechanics."""

    def get_iris_value_mm(self) -> float:
        """Get iris value mm.

        Returns:
            float: Result produced by this function.

        Example:
            >>> # Example
            >>> # get_iris_value_mm(...)
        """
        return self.get_position_mm()
