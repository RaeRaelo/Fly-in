"""Colored terminal display of the simulation.

The movement lines required by the subject stay plain and go to
stdout. Everything visual (legend, per-turn frames, final statistics)
is colored with ANSI escape codes and written to stderr, so the two
streams can be redirected independently.
"""
from drone import Drone
from network import Network
from simulation import Simulation, Snapshot
from zone import ZoneType

ANSI_CODES = {
    "red": "31", "green": "32", "yellow": "33", "blue": "34",
    "magenta": "35", "purple": "35", "pink": "95", "cyan": "36",
    "lightblue": "96", "white": "37", "gray": "90", "grey": "90",
    "black": "90", "orange": "33", "darkgray": "90",
}

TYPE_CODES = {
    ZoneType.NORMAL: "37",
    ZoneType.PRIORITY: "32",
    ZoneType.RESTRICTED: "33",
    ZoneType.BLOCKED: "31",
}


class Renderer:
    """Formats colored terminal output for the simulation."""

    def __init__(self, network: Network, use_color: bool) -> None:
        self.network = network
        self.use_color = use_color

    def paint(self, text: str, code: str | None) -> str:
        """Wrap text in an ANSI color code when colors are enabled."""
        if not self.use_color or code is None:
            return text
        return f"\033[{code}m{text}\033[0m"

    def _zone_code(self, name: str) -> str | None:
        """Pick a color for a zone: its declared color, else its type."""
        zone = self.network.get_zone(name)
        if zone.color and zone.color in ANSI_CODES:
            return ANSI_CODES[zone.color]
        return TYPE_CODES[zone.zone_type]

    def legend(self) -> str:
        """Describe every zone with its color, type and capacity."""
        parts = []
        for zone in self.network.zones.values():
            tags = []
            if zone is self.network.start:
                tags.append("start")
            if zone is self.network.end:
                tags.append("end")
            if zone.zone_type is not ZoneType.NORMAL:
                tags.append(zone.zone_type.value)
            if zone.capacity not in (None, 1):
                tags.append(f"cap={zone.capacity}")
            suffix = f"({', '.join(tags)})" if tags else ""
            parts.append(self.paint(zone.name, self._zone_code(zone.name))
                         + suffix)
        return "map: " + "  ".join(parts)

    def frame(self, turn: int, snapshot: Snapshot) -> str:
        """One colored line showing where every drone stands."""
        groups: dict[str, list[str]] = {}
        links: dict[str, list[str]] = {}
        for label, place, on_link in snapshot:
            table = links if on_link else groups
            table.setdefault(place, []).append(label)
        parts = []
        for name in self.network.zones:
            if name in groups:
                zone_text = self.paint(name, self._zone_code(name))
                parts.append(f"{zone_text}[{','.join(groups[name])}]")
        for name, labels in links.items():
            link_text = self.paint(f"~{name}~", "90")
            parts.append(f"{link_text}[{','.join(labels)}]")
        return f"turn {turn:>3} | " + "  ".join(parts)

    def statistics(self, simulation: Simulation,
                   drones: list[Drone]) -> str:
        """Summary of the run: turns, averages and total path cost."""
        turns = len(simulation.turn_lines)
        moves = sum(len(line.split()) for line in simulation.turn_lines)
        finished = [d.delivered_turn for d in drones
                    if d.delivered_turn is not None]
        average = sum(finished) / len(finished) if finished else 0.0
        total_cost = sum(d.plan.cost for d in drones)
        header = self.paint("result", "36")
        return (f"{header}: {turns} turns | {len(drones)} drones | "
                f"{moves / turns:.1f} moves/turn | "
                f"{average:.1f} avg turns/drone | "
                f"total path cost {total_cost}")
