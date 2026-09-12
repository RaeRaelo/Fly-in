"""Command line entry point of the Fly-in drone routing simulator."""
import argparse
import sys

from planner import Planner, PlanningError
from map_parser import MapParser, ParseError
from network import Network
from renderer import Renderer
from simulation import Simulation, SimulationError
from validator import OutputValidator
from zone import ZoneType


class Application:
    """Parses arguments, runs the simulation and prints the result."""

    def run(self) -> int:
        """Run the program; return the process exit code."""
        try:
            args = self._build_arguments()
            parser = MapParser(args.map_file)
            network = parser.parse()
            if args.validate:
                self._print_summary(parser, network)
                return 0
            drones = Planner(network).plan_fleet(parser.nb_drones)
            simulation = Simulation(network, drones)
            lines = simulation.run()
            renderer = Renderer(network, use_color=not args.no_color)
            self._print_output(args, renderer, simulation, lines)
            self._self_check(network, parser.nb_drones, lines)
            print(renderer.statistics(simulation, drones),
                  file=sys.stderr)
            if args.gui:
                self._launch_gui(network, simulation, args.map_file)
            return 0
        except ParseError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        except (SimulationError, PlanningError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            return 130

    def _build_arguments(self) -> argparse.Namespace:
        """Define and parse the command line interface."""
        parser = argparse.ArgumentParser(
            description="Route a fleet of drones through a zone map.")
        parser.add_argument("map_file", help="path to the map file")
        parser.add_argument("--validate", action="store_true",
                            help="parse the map and print a summary")
        parser.add_argument("--visual", action="store_true",
                            help="show colored per-turn frames (stderr)")
        parser.add_argument("--no-color", action="store_true",
                            help="disable ANSI colors")
        parser.add_argument("--gui", action="store_true",
                            help="replay the simulation in a window")
        return parser.parse_args()

    def _print_output(self, args: argparse.Namespace, renderer: Renderer,
                      simulation: Simulation, lines: list[str]) -> None:
        """Print movement lines to stdout, visuals to stderr."""
        if args.visual:
            print(renderer.legend(), file=sys.stderr)
        for turn, line in enumerate(lines, start=1):
            print(line)
            if args.visual:
                print(renderer.frame(turn, simulation.history[turn]),
                      file=sys.stderr)

    def _print_summary(self, parser: MapParser,
                       network: Network) -> None:
        """Print the --validate summary of a parsed map."""
        counts: dict[str, int] = {}
        for zone in network.zones.values():
            key = zone.zone_type.value
            counts[key] = counts.get(key, 0) + 1
        breakdown = ", ".join(
            f"{counts.get(t.value, 0)} {t.value}" for t in ZoneType)
        print(f"drones: {parser.nb_drones}\n"
              f"zones:  {len(network.zones)} ({breakdown})\n"
              f"links:  {len(network.links)}\n"
              f"start:  {network.start.name}\n"
              f"end:    {network.end.name}")

    def _self_check(self, network: Network, nb_drones: int,
                    lines: list[str]) -> None:
        """Re-validate our own output; warn on stderr if it breaks."""
        violations = OutputValidator(network, nb_drones, lines).validate()
        for violation in violations:
            print(f"self-check: {violation}", file=sys.stderr)

    def _launch_gui(self, network: Network, simulation: Simulation,
                    title: str) -> None:
        """Open the arcade window, with a clear error if unavailable."""
        try:
            from gui import launch_gui
        except ImportError as exc:
            raise ValueError(
                "the arcade library is not installed; "
                "run 'make install' first") from exc
        launch_gui(network, simulation.history, title)


if __name__ == "__main__":
    sys.exit(Application().run())
