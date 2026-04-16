from __future__ import annotations

from ElliptecBase.elliptec_base import (
    ElliptecAddressedDeviceBase,
    ElliptecClosedLoopTuningMixin,
    ElliptecMillimetreUnitsMixin,
)


class ElliptecLinearStage(ElliptecAddressedDeviceBase, ElliptecClosedLoopTuningMixin, ElliptecMillimetreUnitsMixin):
    """
    Shared-bus base for Thorlabs Elliptec closed-loop linear stages (ELL17, ELL20, …).

    Subclasses must set ``MODEL_CODE`` and ``MODEL_FAMILY_NAME`` class attributes.
    """
