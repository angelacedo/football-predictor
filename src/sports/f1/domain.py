"""F1 domain vocabulary - no ML/DB/ingest dependencies. F1's analogue of footy.domain."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DriverRanking:
    """Predicted finishing order for one session.

    Wraps a driver_number -> predicted (continuous) finishing position map.
    Lower predicted value = predicted to finish higher.
    """

    predicted_position: dict[int, float]

    def ranking(self) -> list[int]:
        """Driver numbers ordered by predicted finish, best (lowest) first."""
        return sorted(self.predicted_position, key=lambda d: self.predicted_position[d])

    def position_of(self, driver_number: int) -> float:
        """Predicted continuous position for one driver."""
        return self.predicted_position[driver_number]
