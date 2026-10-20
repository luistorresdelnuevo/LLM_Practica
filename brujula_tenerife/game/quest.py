"""Misión «Sellos de la brújula», controlada solo por Python."""

from __future__ import annotations

REQUIRED_ZONES: tuple[str, ...] = ("Anaga", "Teide", "Santa Cruz")


class StampBook:
    """Concede un sello por zona tras una conversación completada."""

    def __init__(self, zones: tuple[str, ...] = REQUIRED_ZONES) -> None:
        self.zones = zones
        self.stamps: set[str] = set()

    def award(self, zone: str) -> bool:
        """Añade el sello de ``zone``; devuelve ``True`` si es nuevo."""
        if zone not in self.zones or zone in self.stamps:
            return False
        self.stamps.add(zone)
        return True

    def has(self, zone: str) -> bool:
        """Indica si ya se consiguió el sello de la zona."""
        return zone in self.stamps

    @property
    def count(self) -> int:
        """Número de sellos conseguidos."""
        return len(self.stamps)

    @property
    def complete(self) -> bool:
        """La misión termina con un sello en cada zona."""
        return self.count == len(self.zones)
