"""A drone and its planned, timed route."""

Event = tuple[int, str, bool]


class FlightPlan:
    """The timed route of one drone.

    Attributes:
        events: Output events, ordered by turn. Each is (turn, place
            name, on_link): a zone arrival, or the launch onto a
            connection toward a restricted zone. Turns with no event
            are waits and produce no output.
        cost: Sum of the movement costs of every zone entered.
    """

    def __init__(self, events: list[Event], cost: int) -> None:
        self.events = events
        self.cost = cost

    @property
    def delivered_turn(self) -> int:
        """The turn on which the drone reaches the end hub."""
        return self.events[-1][0] if self.events else 0


class Drone:
    """One drone of the fleet, bound to its flight plan."""

    def __init__(self, drone_id: int, plan: FlightPlan) -> None:
        self.drone_id = drone_id
        self.plan = plan

    @property
    def label(self) -> str:
        """Identifier used in the simulation output, e.g. 'D3'."""
        return f"D{self.drone_id}"

    @property
    def delivered_turn(self) -> int:
        """The turn on which this drone is delivered."""
        return self.plan.delivered_turn

    def __repr__(self) -> str:
        """Debug representation."""
        return (f"Drone({self.label}, {len(self.plan.events)} events, "
                f"delivered turn {self.delivered_turn})")
