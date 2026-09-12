"""The zone graph: zones, links and adjacency.

This class replaces any graph library. It stores every zone by name,
every link once, and an adjacency list mapping each zone name to the
links touching it.
"""
from link import Link
from zone import Zone


class Network:
    """A graph of zones connected by bidirectional links."""

    def __init__(self) -> None:
        self.zones: dict[str, Zone] = {}
        self.links: list[Link] = []
        self.adjacency: dict[str, list[Link]] = {}
        self._start: Zone | None = None
        self._end: Zone | None = None
        self._link_keys: set[frozenset[str]] = set()

    def add_zone(self, zone: Zone) -> None:
        """Register a zone, enforcing name uniqueness."""
        if zone.name in self.zones:
            raise ValueError(f"zone {zone.name!r} already exists")
        self.zones[zone.name] = zone
        self.adjacency[zone.name] = []

    def set_start(self, zone: Zone) -> None:
        """Mark the unique start hub."""
        if self._start is not None:
            raise ValueError("start zone already defined")
        self._start = zone

    def set_end(self, zone: Zone) -> None:
        """Mark the unique end hub."""
        if self._end is not None:
            raise ValueError("end zone already defined")
        self._end = zone

    @property
    def start(self) -> Zone:
        """The start hub. Raises if the map never defined one."""
        if self._start is None:
            raise ValueError("no start zone defined")
        return self._start

    @property
    def end(self) -> Zone:
        """The end hub. Raises if the map never defined one."""
        if self._end is None:
            raise ValueError("no end zone defined")
        return self._end

    def add_link(self, link: Link) -> None:
        """Register a link, enforcing the connection rules."""
        if link.zone_a.name == link.zone_b.name:
            raise ValueError("a link requires two different zones")
        for zone in (link.zone_a, link.zone_b):
            if zone.name not in self.zones:
                raise ValueError(
                    f"connection uses undefined zone {zone.name!r}")
        key = frozenset({link.zone_a.name, link.zone_b.name})
        if key in self._link_keys:
            raise ValueError(f"duplicate connection {link.name!r}")
        self._link_keys.add(key)
        self.links.append(link)
        self.adjacency[link.zone_a.name].append(link)
        self.adjacency[link.zone_b.name].append(link)

    def get_zone(self, name: str) -> Zone:
        """Look a zone up by name."""
        try:
            return self.zones[name]
        except KeyError:
            raise ValueError(f"zone {name!r} doesn't exist") from None

    def has_zone(self, name: str) -> bool:
        """True when a zone with this name exists."""
        return name in self.zones

    def links_from(self, zone: Zone) -> list[Link]:
        """All links touching the given zone."""
        return self.adjacency.get(zone.name, [])

    def link_between(self, zone_a: Zone, zone_b: Zone) -> Link:
        """The link joining two adjacent zones."""
        for link in self.links_from(zone_a):
            if link.other_end(zone_a) is zone_b:
                return link
        raise ValueError(
            f"no link between {zone_a.name!r} and {zone_b.name!r}")

    def __repr__(self) -> str:
        """Debug representation with counts only."""
        start = self._start.name if self._start else "?"
        end = self._end.name if self._end else "?"
        return (f"Network(zones={len(self.zones)}, "
                f"links={len(self.links)}, start={start}, end={end})")
