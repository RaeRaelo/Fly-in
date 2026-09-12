"""Playback of planned routes into the required output format.

Routing decisions are made ahead of time by the Planner; this class
only replays the flight plans: it merges every drone's events into
one line per turn, and records where every drone stands after each
turn for the visual displays.
"""
from drone import Drone
from network import Network

Snapshot = list[tuple[str, str, bool]]


class SimulationError(Exception):
    """Raised when the planned routes cannot form valid output."""


class Simulation:
    """Builds the turn-by-turn output and history from flight plans.

    Attributes:
        turn_lines: One output line per turn.
        history: Drone locations after every turn (index 0 is the
            initial state); each entry lists (label, place, on_link)
            for every undelivered drone.
    """

    def __init__(self, network: Network, drones: list[Drone]) -> None:
        self.network = network
        self.drones = drones
        self.turn_lines: list[str] = []
        self.history: list[Snapshot] = []

    def run(self) -> list[str]:
        """Assemble the output lines and per-turn snapshots."""
        total = max((d.delivered_turn for d in self.drones), default=0)
        events = {d.drone_id: dict(self._by_turn(d)) for d in self.drones}
        location = {d.drone_id: (self.network.start.name, False)
                    for d in self.drones}
        self.history = [self._snapshot(location, 0)]
        for turn in range(1, total + 1):
            tokens: list[str] = []
            for drone in self.drones:
                event = events[drone.drone_id].get(turn)
                if event is None:
                    continue
                place, on_link = event
                location[drone.drone_id] = (place, on_link)
                tokens.append(f"{drone.label}-{place}")
            if not tokens:
                raise SimulationError(f"planned turn {turn} is empty")
            self.turn_lines.append(" ".join(tokens))
            self.history.append(self._snapshot(location, turn))
        return self.turn_lines

    def _by_turn(self, drone: Drone) -> list[
            tuple[int, tuple[str, bool]]]:
        """Index one drone's events by turn number."""
        return [(turn, (place, on_link))
                for turn, place, on_link in drone.plan.events]

    def _snapshot(self, location: dict[int, tuple[str, bool]],
                  turn: int) -> Snapshot:
        """Locations of every drone not yet delivered after a turn."""
        return [(d.label,) + location[d.drone_id]
                for d in self.drones if d.delivered_turn > turn]
