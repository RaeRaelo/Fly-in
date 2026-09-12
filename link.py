"""Connections between zones."""
from zone import Zone


class Link:
    """A bidirectional connection between two zones."""

    def __init__(self, zone_a: Zone, zone_b: Zone, capacity: int):
        self.zone_a = zone_a
        self.zone_b = zone_b
        self.capacity = capacity
        if capacity < 1:
            raise ValueError("Link capacity cannot be less than 1")

    def other_end(self, zone: Zone) -> Zone:
        """Return the endpoint that is not the given zone."""
        if zone is self.zone_a:
            return self.zone_b
        if zone is self.zone_b:
            return self.zone_a
        raise ValueError(f"{zone.name} is not an endpoint of {self.name}")

    @property
    def name(self) -> str:
        """Derived connection name, in declaration order."""
        return f"{self.zone_a.name}-{self.zone_b.name}"

    def __repr__(self) -> str:
        """Debug representation."""
        return f"Link({self.name}, cap={self.capacity})"
