*This project has been created as part of the 42 curriculum by <adahadda>.*

# Fly-in

## Description

Fly-in routes a fleet of drones from a start hub to an end hub across a
network of connected zones, in as few simulation turns as possible. The
program parses a map file describing zones, connections, capacities and
zone types, plans routes for every drone, then plays the simulation turn
by turn while enforcing every movement rule: zone capacity, connection
capacity, two-turn transit into restricted zones, and blocked zones.

Each simulation turn is printed as one line of space-separated movements
(`D1-roof1 D2-corridorA`), exactly as required by the subject.

## Instructions

```
python3 -m venv .venv && source .venv/bin/activate
make install                       # install dependencies
make run                           # run the default map
make run MAP=maps/hard/02_capacity_hell.txt
make lint                          # flake8 + mypy (subject flags)
```

Options:

```
python3 main.py <map> --validate   # parse only, print a map summary
python3 main.py <map> --visual     # colored per-turn frames on stderr
python3 main.py <map> --no-color   # disable ANSI colors
python3 main.py <map> --gui        # animated replay window (arcade)
```

Movement lines go to stdout; the legend, colored frames and statistics
go to stderr, so `python3 main.py map.txt 2>/dev/null` yields the pure
machine-readable log.

## Algorithm choices and implementation strategy

**Time-expanded search.** The core problem is multi-agent pathfinding
under capacity constraints: a plain per-drone shortest path would send
every drone through the same bottleneck at the same time. Instead, the
planner runs Dijkstra over **(zone, turn)** states — "standing in zone
Z at the end of turn T". Because every movement cost in this project is
measured in turns, the Dijkstra cost of a state *is* the arrival turn.
Waiting is modelled as an ordinary move (same zone, one turn later), so
the search decides by itself when a drone should wait and when it
should reroute — no special-case logic. Priority zones are preferred
through a secondary tie-break key, keeping turn arithmetic exact.

**Reservation table.** All planned occupancy is recorded per
(zone, turn) and (connection, turn). Before the search generates a
successor state it checks the table: destination zone below
`max_drones` at the arrival turn, connection below `max_link_capacity`
on every turn of the traversal (both turns for a two-turn restricted
transit, during which the drone occupies the connection). Illegal
states are simply never generated, so conflicts are impossible by
construction and no runtime conflict resolution is needed.

**Prioritized planning.** Drones are planned sequentially in id order;
each search sees every reservation committed by earlier drones, then
commits its own. This is simpler than optimal multi-agent search
(e.g. Conflict-Based Search) yet meets or beats every reference target,
including the optional Challenger map (43 turns vs the 45-turn
record). Complexity: O(V·H log(V·H)) per drone, where H is the search
horizon (bounded by map size plus fleet size); reservation checks are
O(1) dictionary lookups. Routes are planned once — the simulation
merely replays them, so playback is linear in the output size.

**Self-validation.** An independent `OutputValidator` replays the
produced output against every rule of the subject and reports any
violation on stderr. It shares no logic with the planner, so a bug in
one is caught by the other.

Benchmark results (all reference targets met or beaten):

| map | turns | target |
|---|---|---|
| easy 1 / 2 / 3 | 4 / 4 / 4 | 6 / 8 / 6 |
| medium 1 / 2 / 3 | 8 / 15 / 7 | 12 / 15 / 12 |
| hard 1 / 2 / 3 | 13 / 16 / 26 | 30 / 35 / 45 |
| challenger | 43 | record 45 |

## Visual representation

Two complementary systems:

* **Colored terminal output** (`--visual`): a legend describing every
  zone in its map color, then one frame per turn showing which drones
  occupy which zones and connections. Frames are written to stderr so
  the stdout log stays clean; `--no-color` disables ANSI codes.
* **Graphical replay** (`--gui`): an `arcade` window drawing the
  network to scale (links weighted by capacity, start and end ringed in
  green and yellow) and replaying the recorded turns. SPACE pauses,
  LEFT/RIGHT step turn by turn, ESC quits.

Both make capacity conflicts and waiting visible: you can watch drones
queue in front of a bottleneck and advance as a train.

## Example

Input (`maps/easy/02_simple_fork.txt`, 4 drones, forked route):

```
nb_drones: 4
start_hub: start 0 0 [color=green]
hub: junction 2 1 [color=yellow max_drones=2]
...
```

Output:

```
D1-junction D2-junction
D1-path_a D2-path_b D3-junction D4-junction
D1-goal D2-goal D3-path_a D4-path_b
D3-goal D4-goal
```

4 turns; the fleet splits across both branches of the fork.

## Resources

* Dijkstra's algorithm: Introduction to Algorithms (CLRS), chapter 24;
  https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm
* Python `heapq` documentation: https://docs.python.org/3/library/heapq.html
* PEP 257 (docstrings), PEP 484 (type hints), mypy documentation:
  https://mypy.readthedocs.io/
* The arcade library: https://api.arcade.academy/
* The lem-in family of problems (multi-agent routing on graphs) for the
  drone distribution idea.
* https://www.geeksforgeeks.org/dsa/dijkstras-shortest-path-algorithm-greedy-algo-7/

**How AI was used.** Claude was used as a tutor throughout
the project: proposing the architecture and build order, explaining
concepts (Dijkstra, heaps, enum behaviour, mypy typing patterns), and
reviewing each hand-written module (`zone`, `link`, `network`, `path`,
`main`) with concrete bug reports.
