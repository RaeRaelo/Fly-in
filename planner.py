"""Time-expanded route planning with a shared reservation table.

Instead of searching over zones alone, the planner searches over
(zone, turn) states: "being in zone Z at the end of turn T". Because
every movement cost in this project is measured in turns, the Dijkstra
cost of a state IS the turn at which the drone gets there. Waiting in
place is just another move (same zone, one turn later), so the search
decides by itself when a drone should wait and when it should reroute.

Drones are planned one at a time, in id order. Every reservation made
by earlier drones is visible to later searches through the shared
ReservationTable, so conflicts are impossible by construction: a state
that would break a capacity rule is simply never generated.
"""
import heapq
from itertools import count

from drone import Drone, FlightPlan
from link import Link
from network import Network
from zone import Zone, ZoneType

State = tuple[str, int]


class PlanningError(Exception):
    """Raised when no valid route exists within the search horizon."""


class ReservationTable:
    """Turn-indexed occupancy bookkeeping for zones and links.

    Keys are (name, turn). A zone reservation means "one drone stands
    in this zone at the end of this turn"; a link reservation means
    "one drone traverses this connection during this turn".
    """

    def __init__(self) -> None:
        self._zones: dict[tuple[str, int], int] = {}
        self._links: dict[tuple[str, int], int] = {}

    def zone_free(self, zone: Zone, turn: int) -> bool:
        """True when the zone can host one more drone at that turn."""
        return zone.has_room(self._zones.get((zone.name, turn), 0))

    def link_free(self, link: Link, turn: int) -> bool:
        """True when the link can carry one more drone that turn."""
        return self._links.get((link.name, turn), 0) < link.capacity

    def reserve_zone(self, zone: Zone, turn: int) -> None:
        """Record one drone in the zone at the end of the turn."""
        key = (zone.name, turn)
        self._zones[key] = self._zones.get(key, 0) + 1

    def reserve_link(self, link: Link, turn: int) -> None:
        """Record one drone on the link during the turn."""
        key = (link.name, turn)
        self._links[key] = self._links.get(key, 0) + 1


class Planner:
    """Plans conflict-free timed routes for a whole fleet."""

    def __init__(self, network: Network) -> None:
        self.network = network
        self.table = ReservationTable()

    def plan_fleet(self, nb_drones: int) -> list[Drone]:
        """Plan every drone sequentially against shared reservations."""
        horizon = 2 * len(self.network.zones) + 2 * nb_drones + 30
        drones: list[Drone] = []
        for drone_id in range(1, nb_drones + 1):
            chain = self._search(horizon)
            if chain is None:
                raise PlanningError("no route from start to end")
            self._commit(chain)
            drones.append(Drone(drone_id, self._build_plan(chain)))
        return drones

    def _search(self, horizon: int) -> list[State] | None:
        """Dijkstra over (zone, turn) states; returns the state chain.

        The heap orders states by (turn, penalty, sequence): turn is
        the cost being minimised, penalty counts non-priority actions
        so equal-turn routes prefer priority zones, and the sequence
        number keeps comparisons away from Zone objects and makes the
        search deterministic.
        """
        start = self.network.start
        end = self.network.end
        counter = count()
        came_from: dict[State, State] = {}
        visited: set[State] = set()
        heap: list[tuple[int, int, int, Zone]] = [
            (0, 0, next(counter), start)]
        while heap:
            turn, penalty, _, zone = heapq.heappop(heap)
            state = (zone.name, turn)
            if state in visited:
                continue
            visited.add(state)
            if zone is end:
                return self._chain(came_from, state)
            if turn >= horizon:
                continue
            self._expand(zone, turn, penalty, heap, came_from,
                         visited, counter)
        return None

    def _expand(self, zone: Zone, turn: int, penalty: int,
                heap: list[tuple[int, int, int, Zone]],
                came_from: dict[State, State], visited: set[State],
                counter: "count[int]") -> None:
        """Push every legal successor of one (zone, turn) state."""
        here: State = (zone.name, turn)

        def push(target: Zone, arrival: int, extra: int) -> None:
            state = (target.name, arrival)
            if state in visited or state in came_from:
                return
            came_from[state] = here
            heapq.heappush(
                heap, (arrival, penalty + extra, next(counter), target))

        if self.table.zone_free(zone, turn + 1):
            push(zone, turn + 1, 1)                     # wait
        for link in self.network.links_from(zone):
            neighbour = link.other_end(zone)
            if not neighbour.is_passable:
                continue
            if neighbour.zone_type is ZoneType.RESTRICTED:
                if (self.table.link_free(link, turn + 1)
                        and self.table.link_free(link, turn + 2)
                        and self.table.zone_free(neighbour, turn + 2)):
                    push(neighbour, turn + 2, 1)        # 2-turn transit
            else:
                if (self.table.link_free(link, turn + 1)
                        and self.table.zone_free(neighbour, turn + 1)):
                    push(neighbour, turn + 1,
                         0 if neighbour.zone_type.is_preferred else 1)

    def _chain(self, came_from: dict[State, State],
               last: State) -> list[State]:
        """Walk predecessors back to the initial state and reverse."""
        chain = [last]
        while chain[-1] in came_from:
            chain.append(came_from[chain[-1]])
        chain.reverse()
        return chain

    def _commit(self, chain: list[State]) -> None:
        """Write one accepted route into the reservation table."""
        for previous, current in zip(chain, chain[1:]):
            (prev_name, prev_turn), (name, turn) = previous, current
            zone = self.network.get_zone(name)
            if name == prev_name:                       # wait
                self.table.reserve_zone(zone, turn)
                continue
            link = self.network.link_between(
                self.network.get_zone(prev_name), zone)
            if turn - prev_turn == 2:                   # transit
                self.table.reserve_link(link, turn - 1)
            self.table.reserve_link(link, turn)
            self.table.reserve_zone(zone, turn)

    def _build_plan(self, chain: list[State]) -> FlightPlan:
        """Convert a state chain into output events and a path cost."""
        events: list[tuple[int, str, bool]] = []
        cost = 0
        for previous, current in zip(chain, chain[1:]):
            (prev_name, prev_turn), (name, turn) = previous, current
            if name == prev_name:
                continue
            zone = self.network.get_zone(name)
            cost += zone.zone_type.movement_cost
            if turn - prev_turn == 2:
                link = self.network.link_between(
                    self.network.get_zone(prev_name), zone)
                events.append((turn - 1, link.name, True))
            events.append((turn, name, False))
        return FlightPlan(events, cost)
