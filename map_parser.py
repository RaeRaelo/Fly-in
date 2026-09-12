"""Parsing of drone network map files into Network objects."""
from typing import NoReturn

from link import Link
from network import Network
from zone import Zone, ZoneType


class ParseError(Exception):
    """Raised when a map file is malformed.

    Attributes:
        line: 1-based line number where the problem was found, 0 if the
            problem concerns the file as a whole.
        reason: Human readable description of the problem.
    """

    def __init__(self, line: int, reason: str) -> None:
        self.line = line
        self.reason = reason
        where = f"line {line}: " if line else ""
        super().__init__(f"{where}{reason}")


class MapParser:
    """Reads a map file and builds the Network it describes."""

    ZONE_PREFIXES = ("start_hub", "end_hub", "hub")
    ZONE_KEYS = frozenset({"zone", "color", "max_drones"})
    LINK_KEYS = frozenset({"max_link_capacity"})

    def __init__(self, path: str) -> None:
        self.path = path
        self._network = Network()
        self._nb_drones: int | None = None
        self._line_no = 0

    @property
    def nb_drones(self) -> int:
        """Number of drones declared in the file."""
        if self._nb_drones is None:
            raise ValueError("map has not been parsed yet")
        return self._nb_drones

    def parse(self) -> Network:
        """Parse the file and return the resulting network."""
        try:
            with open(self.path, encoding="utf-8") as handle:
                lines = handle.readlines()
        except OSError as exc:
            raise ParseError(0, f"cannot read {self.path}: {exc}") from exc

        for line_no, raw in enumerate(lines, start=1):
            self._line_no = line_no
            cleaned = raw.split("#", 1)[0].strip()
            if not cleaned:
                continue
            self._dispatch(cleaned)

        self._line_no = 0
        if self._nb_drones is None:
            self._fail("no nb_drones line found")
        try:
            self._network.start
            self._network.end
        except ValueError as exc:
            self._fail(str(exc))
        return self._network

    def _fail(self, reason: str) -> NoReturn:
        """Raise a ParseError for the line currently being read."""
        raise ParseError(self._line_no, reason)

    def _dispatch(self, line: str) -> None:
        """Route a cleaned line to the handler for its keyword."""
        keyword, separator, rest = line.partition(":")
        if not separator:
            self._fail(f"missing ':' in {line!r}")
        keyword = keyword.strip()
        rest = rest.strip()
        if keyword == "nb_drones":
            self._parse_drone_count(rest)
        elif keyword in self.ZONE_PREFIXES:
            self._parse_zone(keyword, rest)
        elif keyword == "connection":
            self._parse_connection(rest)
        else:
            self._fail(f"unknown keyword {keyword!r}")

    def _parse_drone_count(self, rest: str) -> None:
        """Handle a nb_drones line."""
        if self._nb_drones is not None:
            self._fail("nb_drones declared more than once")
        self._nb_drones = self._to_positive(rest, "nb_drones")

    def _parse_zone(self, keyword: str, rest: str) -> None:
        """Handle a start_hub, end_hub or hub line."""
        self._require_drone_count()
        body, tags = self._split_metadata(rest, self.ZONE_KEYS)
        parts = body.split()
        if len(parts) != 3:
            self._fail(f"expected '<name> <x> <y>', got {body!r}")
        name, x_text, y_text = parts
        self._check_name(name)

        type_text = tags.get("zone", "normal")
        try:
            zone_type = ZoneType(type_text)
        except ValueError:
            self._fail(f"unknown zone type {type_text!r}")

        capacity: int | None = None
        if keyword == "hub":
            capacity = self._to_positive(
                tags.get("max_drones", "1"), "max_drones")

        zone = Zone(name, self._to_int(x_text, "x"),
                    self._to_int(y_text, "y"),
                    zone_type, tags.get("color"), capacity)
        try:
            self._network.add_zone(zone)
            if keyword == "start_hub":
                self._network.set_start(zone)
            elif keyword == "end_hub":
                self._network.set_end(zone)
        except ValueError as exc:
            self._fail(str(exc))

    def _parse_connection(self, rest: str) -> None:
        """Handle a connection line."""
        self._require_drone_count()
        body, tags = self._split_metadata(rest, self.LINK_KEYS)
        parts = body.split()
        if len(parts) != 1:
            self._fail(f"expected '<zone1>-<zone2>', got {body!r}")
        endpoints = parts[0].split("-")
        if len(endpoints) != 2 or not all(endpoints):
            self._fail(f"expected '<zone1>-<zone2>', got {parts[0]!r}")
        capacity = self._to_positive(
            tags.get("max_link_capacity", "1"), "max_link_capacity")
        for name in endpoints:
            if not self._network.has_zone(name):
                self._fail(f"connection uses undefined zone {name!r}")
        link = Link(self._network.get_zone(endpoints[0]),
                    self._network.get_zone(endpoints[1]), capacity)
        try:
            self._network.add_link(link)
        except ValueError as exc:
            self._fail(str(exc))

    def _split_metadata(self, rest: str,
                        allowed: frozenset[str]) -> tuple[str, dict[str, str]]:
        """Split a line into its body and its optional [key=value] block."""
        if "[" not in rest:
            if "]" in rest:
                self._fail("closing ']' without opening '['")
            return rest, {}
        if not rest.endswith("]"):
            self._fail("metadata block must be closed with ']'")
        opening = rest.index("[")
        body = rest[opening + 1:-1]
        if "[" in body or "]" in body:
            self._fail("unbalanced brackets in metadata")
        return rest[:opening].strip(), self._parse_metadata(body, allowed)

    def _parse_metadata(self, body: str,
                        allowed: frozenset[str]) -> dict[str, str]:
        """Parse the inside of a metadata block into a dict."""
        tags: dict[str, str] = {}
        for token in body.split():
            key, separator, value = token.partition("=")
            if not separator or not key or not value:
                self._fail(f"malformed metadata tag {token!r}")
            if key not in allowed:
                self._fail(f"unknown metadata key {key!r}")
            if key in tags:
                self._fail(f"duplicate metadata key {key!r}")
            tags[key] = value
        return tags

    def _require_drone_count(self) -> None:
        """Enforce that nb_drones appears before any zone or connection."""
        if self._nb_drones is None:
            self._fail("nb_drones must be declared first")

    def _check_name(self, name: str) -> None:
        """Reject zone names that break the connection syntax."""
        if "-" in name:
            self._fail(f"zone name {name!r} must not contain a dash")
        if "[" in name or "]" in name:
            self._fail(f"zone name {name!r} must not contain brackets")

    def _to_int(self, text: str, field: str) -> int:
        """Convert text to an int, failing with a located error."""
        try:
            return int(text)
        except ValueError:
            self._fail(f"{field} must be an integer, got {text!r}")

    def _to_positive(self, text: str, field: str) -> int:
        """Convert text to an int of at least 1."""
        value = self._to_int(text, field)
        if value < 1:
            self._fail(f"{field} must be positive, got {value}")
        return value
