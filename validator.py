"""Replay of simulation output against every rule of the subject.

The validator is independent from the engine: it reads the produced
movement lines and re-checks adjacency, zone capacity, link capacity,
restricted-zone transit and delivery, reporting every violation it
finds. An empty report means the output is valid.
"""
from link import Link
from network import Network
from zone import ZoneType


class OutputValidator:
    """Checks simulation output lines against the movement rules."""

    def __init__(self, network: Network, nb_drones: int,
                 lines: list[str]) -> None:
        self.network = network
        self.lines = lines
        self.position: dict[str, str] = {
            f"D{i}": network.start.name for i in range(1, nb_drones + 1)}
        self.on_link: dict[str, Link] = {}
        self.delivered: set[str] = set()
        self.link_names = {link.name: link for link in network.links}
        self.violations: list[str] = []

    def validate(self) -> list[str]:
        """Replay every line; return the list of violations found."""
        for turn, line in enumerate(self.lines, start=1):
            self._play_line(turn, line)
        remaining = set(self.position) - self.delivered
        if remaining:
            self._flag(len(self.lines),
                       f"never delivered: {sorted(remaining)}")
        return self.violations

    def _play_line(self, turn: int, line: str) -> None:
        """Validate one turn worth of movement tokens."""
        pending = set(self.on_link)
        seen: set[str] = set()
        link_load: dict[str, int] = {}
        for token in line.split():
            label, _, rest = token.partition("-")
            if label in seen:
                self._flag(turn, f"{label} moved twice")
                continue
            seen.add(label)
            self._play_token(turn, label, rest, link_load)
        for label in pending - seen:
            self._flag(turn, f"{label} stalled on a link")
        self._check_occupancy(turn)
        for name, load in link_load.items():
            capacity = self.link_names[name].capacity
            if load > capacity:
                self._flag(turn, f"link {name} used {load}x, "
                                 f"capacity {capacity}")

    def _play_token(self, turn: int, label: str, rest: str,
                    link_load: dict[str, int]) -> None:
        """Validate one movement token and apply it to the state."""
        if label not in self.position:
            self._flag(turn, f"unknown drone {label}")
            return
        if label in self.delivered:
            self._flag(turn, f"{label} moved after delivery")
            return
        if label in self.on_link:
            self._finish_transit(turn, label, rest, link_load)
            return
        here = self.network.get_zone(self.position[label])
        if self.network.has_zone(rest):
            target = self.network.get_zone(rest)
            try:
                link = self.network.link_between(here, target)
            except ValueError:
                self._flag(turn, f"{label}: {here.name} and {rest} "
                                 "are not connected")
                return
            if target.zone_type is ZoneType.RESTRICTED:
                self._flag(turn, f"{label} entered restricted {rest} "
                                 "in a single turn")
                return
            if not target.is_passable:
                self._flag(turn, f"{label} entered blocked {rest}")
                return
            link_load[link.name] = link_load.get(link.name, 0) + 1
            self.position[label] = rest
            if target is self.network.end:
                self.delivered.add(label)
        elif rest in self.link_names:
            self._start_transit(turn, label, rest, here.name, link_load)
        else:
            self._flag(turn, f"{label} moved to unknown place {rest!r}")

    def _start_transit(self, turn: int, label: str, name: str,
                       here: str, link_load: dict[str, int]) -> None:
        """Validate the launch of a two-turn move onto a link."""
        link = self.link_names[name]
        if here not in (link.zone_a.name, link.zone_b.name):
            self._flag(turn, f"{label} launched onto {name} "
                             f"from non-endpoint {here}")
            return
        far = link.other_end(self.network.get_zone(here))
        if far.zone_type is not ZoneType.RESTRICTED:
            self._flag(turn, f"{label} used a link token toward "
                             f"non-restricted {far.name}")
            return
        link_load[name] = link_load.get(name, 0) + 1
        self.on_link[label] = link

    def _finish_transit(self, turn: int, label: str, rest: str,
                        link_load: dict[str, int]) -> None:
        """Validate the mandatory arrival after a turn on a link."""
        link = self.on_link[label]
        origin = self.network.get_zone(self.position[label])
        expected = link.other_end(origin)
        if rest != expected.name:
            self._flag(turn, f"{label} must arrive at {expected.name}, "
                             f"moved to {rest}")
            return
        link_load[link.name] = link_load.get(link.name, 0) + 1
        del self.on_link[label]
        self.position[label] = rest
        if expected is self.network.end:
            self.delivered.add(label)

    def _check_occupancy(self, turn: int) -> None:
        """Check zone capacities at the end of a turn."""
        counts: dict[str, int] = {}
        for label, zone_name in self.position.items():
            if label in self.delivered or label in self.on_link:
                continue
            counts[zone_name] = counts.get(zone_name, 0) + 1
        for name, count in counts.items():
            zone = self.network.get_zone(name)
            if zone is self.network.start or zone is self.network.end:
                continue
            if not zone.has_room(count - 1):
                self._flag(turn, f"zone {name} holds {count}, "
                                 f"capacity {zone.capacity}")

    def _flag(self, turn: int, reason: str) -> None:
        """Record one violation."""
        self.violations.append(f"turn {turn}: {reason}")
