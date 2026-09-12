"""Graphical display of the simulation using the arcade library.

The window replays the recorded per-turn history. Controls: SPACE
pauses and resumes the automatic playback, LEFT and RIGHT step one
turn, ESCAPE closes the window.
"""
from typing import Any

import arcade

from network import Network
from simulation import Snapshot
from zone import ZoneType

WIDTH = 960
HEIGHT = 720
MARGIN = 90
ZONE_RADIUS = 16
TURN_SECONDS = 0.8

TYPE_OUTLINES = {
    ZoneType.NORMAL: (120, 124, 134),
    ZoneType.PRIORITY: (90, 230, 140),
    ZoneType.RESTRICTED: (240, 120, 60),
    ZoneType.BLOCKED: (30, 30, 34),
}

TYPE_COLORS = {
    ZoneType.NORMAL: (200, 200, 210),
    ZoneType.PRIORITY: (80, 200, 120),
    ZoneType.RESTRICTED: (230, 170, 60),
    ZoneType.BLOCKED: (90, 90, 95),
}


class SimulationWindow(arcade.Window):
    """Window replaying the simulation turn by turn."""

    def __init__(self, network: Network,
                 history: list[Snapshot], title: str) -> None:
        super().__init__(WIDTH, HEIGHT, title)
        self.background_color = (24, 26, 32)
        self.network = network
        self.history = history
        self.turn = 0
        self.playing = True
        self.elapsed = 0.0
        self.pixels = self._compute_pixels()

    def _compute_pixels(self) -> dict[str, tuple[float, float]]:
        """Scale map coordinates into window pixels."""
        xs = [zone.x for zone in self.network.zones.values()]
        ys = [zone.y for zone in self.network.zones.values()]
        span_x = max(xs) - min(xs) or 1
        span_y = max(ys) - min(ys) or 1
        pixels = {}
        for zone in self.network.zones.values():
            px = MARGIN + (zone.x - min(xs)) / span_x * (WIDTH - 2 * MARGIN)
            py = MARGIN + (zone.y - min(ys)) / span_y * (HEIGHT - 2 * MARGIN)
            pixels[zone.name] = (px, py)
        return pixels

    def _zone_color(self, name: str) -> Any:
        """Pick a fill color: the declared color, else the type color."""
        zone = self.network.get_zone(name)
        if zone.color:
            declared = getattr(arcade.color, zone.color.upper(), None)
            if declared is not None:
                return declared
        return TYPE_COLORS[zone.zone_type]

    def on_draw(self) -> None:
        """Draw links, zones, drones and the status line."""
        self.clear()
        for link in self.network.links:
            ax, ay = self.pixels[link.zone_a.name]
            bx, by = self.pixels[link.zone_b.name]
            arcade.draw_line(ax, ay, bx, by, (70, 74, 84),
                             1 + link.capacity)
        for zone in self.network.zones.values():
            px, py = self.pixels[zone.name]
            arcade.draw_circle_filled(px, py, ZONE_RADIUS,
                                      self._zone_color(zone.name))
            arcade.draw_circle_outline(px, py, ZONE_RADIUS + 1,
                                       TYPE_OUTLINES[zone.zone_type], 2)
            if zone is self.network.start:
                arcade.draw_circle_outline(px, py, ZONE_RADIUS + 4,
                                           (80, 220, 120), 3)
            if zone is self.network.end:
                arcade.draw_circle_outline(px, py, ZONE_RADIUS + 4,
                                           (240, 220, 90), 3)
            arcade.draw_text(zone.name, px - 40, py - ZONE_RADIUS - 16,
                             (160, 165, 175), 9, width=80,
                             align="center")
        self._draw_drones()
        status = (f"turn {self.turn}/{len(self.history) - 1}   "
                  f"{'playing' if self.playing else 'paused'}   "
                  "space=pause  arrows=step  esc=quit")
        arcade.draw_text(status, 20, HEIGHT - 30, (220, 220, 230), 12)

    def _draw_drones(self) -> None:
        """Draw every drone of the current turn snapshot."""
        stacked: dict[str, int] = {}
        for label, place, on_link in self.history[self.turn]:
            if on_link:
                link = next(k for k in self.network.links
                            if k.name == place)
                ax, ay = self.pixels[link.zone_a.name]
                bx, by = self.pixels[link.zone_b.name]
                px, py = (ax + bx) / 2, (ay + by) / 2
            else:
                px, py = self.pixels[place]
            offset = stacked.get(place, 0)
            stacked[place] = offset + 1
            px += (offset % 3) * 10 - 10
            py += (offset // 3) * 10
            arcade.draw_circle_filled(px, py, 6, (235, 80, 90))
            arcade.draw_text(label, px - 10, py + 7,
                             (240, 240, 245), 8)

    def on_update(self, delta_time: float) -> None:
        """Advance the playback clock."""
        if not self.playing:
            return
        self.elapsed += delta_time
        if self.elapsed >= TURN_SECONDS:
            self.elapsed = 0.0
            if self.turn < len(self.history) - 1:
                self.turn += 1
            else:
                self.playing = False

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        """Handle pause, stepping and quitting."""
        if symbol == arcade.key.SPACE:
            self.playing = not self.playing
        elif symbol == arcade.key.RIGHT:
            self.playing = False
            self.turn = min(self.turn + 1, len(self.history) - 1)
        elif symbol == arcade.key.LEFT:
            self.playing = False
            self.turn = max(self.turn - 1, 0)
        elif symbol == arcade.key.ESCAPE:
            self.close()


def launch_gui(network: Network, history: list[Snapshot],
               title: str) -> None:
    """Open the replay window and hand control to arcade."""
    SimulationWindow(network, history, title)
    arcade.run()
