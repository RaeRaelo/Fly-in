"""Zone types and zones of the drone network.

A zone is a node of the network graph. Its type decides how expensive
it is to enter and whether it can be entered at all. Its capacity
decides how many drones may occupy it at the same time.
"""
from enum import Enum


class ZoneType(Enum):
    """The four zone categories defined by the subject."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @property
    def movement_cost(self) -> int:
        """Turns charged for entering a zone of this type.

        Raises:
            ValueError: For blocked zones, which cannot be entered.
                Callers must check is_passable first.
        """
        match self:
            case ZoneType.NORMAL | ZoneType.PRIORITY:
                return 1
            case ZoneType.RESTRICTED:
                return 2
            case ZoneType.BLOCKED:
                raise ValueError(f"{self.value} zones cannot be entered")
        raise ValueError("unknown zone type")

    @property
    def is_passable(self) -> bool:
        """True when drones are allowed to enter this zone type."""
        return self is not ZoneType.BLOCKED

    @property
    def is_preferred(self) -> bool:
        """True for priority zones, preferred on equal-cost routes."""
        return self is ZoneType.PRIORITY


class Zone:
    """A single zone of the network.

    Attributes:
        name: Unique identifier used in map files and output.
        x: Horizontal coordinate, used for graphical display.
        y: Vertical coordinate, used for graphical display.
        zone_type: Category deciding cost and passability.
        color: Optional display color from the map file.
        capacity: Maximum simultaneous drones, or None for unlimited
            (the start and end hubs).
    """

    def __init__(self, name: str, x: int, y: int,
                 zone_type: ZoneType, color: str | None,
                 capacity: int | None):
        if capacity is not None and capacity < 1:
            raise ValueError(f"capacity cannot be {capacity}")
        self.name = name
        self.x = x
        self.y = y
        self.zone_type = zone_type
        self.color = color
        self.capacity = capacity

    def has_room(self, occupants: int) -> bool:
        """True when one more drone fits given the current occupants."""
        return self.capacity is None or self.capacity > occupants

    @property
    def is_passable(self) -> bool:
        """True when drones are allowed to enter this zone."""
        return self.zone_type.is_passable

    def __repr__(self) -> str:
        """Debug representation."""
        return f"Zone({self.name}, {self.x}, {self.y}, {self.zone_type.value})"
