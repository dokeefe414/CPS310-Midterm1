# CPS 310 — Midterm #1: Decoupling State Storage from the Zombie Game

**Student:** Daniel O'Keefe  
**Course:** CPS 310, Fall 2026  
**Instructor:** Dr. Fanchao Meng  
**Work:** Individual midterm adaptation of the group project

## Overview

This midterm is based on our existing group repository, [CPS310-Zombie-Game](https://github.com/dokeefe414/CPS310-Zombie-Game), especially its `Zombie_Game.py` implementation. It adapts the **actual class names, entity types, and gameplay mechanics** to show how simulation logic can stay independent of the storage technology. It is a **focused adaptation**, not a verbatim copy of the entire original GUI, multiprocessing, or PostgreSQL application.

The original project includes `Agent`, `Human`, `ArmedHuman`, `Zombie`, and `SimulationPlayground`, with movement, fleeing, armed attacks, zombie starvation and biting, conversion, and a 1200x1200 arena. The midterm retains those core concepts while introducing a storage interface and two interchangeable implementations.

## Files

- **midterm1.py** — complete OOP implementation, storage backends, and two-simulation demonstration
- **test_midterm1.py** — automated tests for equivalence, isolation, and persistence
- **game_state.json** — example JSON snapshot; running the demo regenerates it
- **README.md** — design explanation and defense notes

## Run

Python 3.10+ is required. No external packages, GUI, or PostgreSQL are required.

```bash
python midterm1.py
python -m unittest -v
```

The demonstration starts two independent simulations from identical agent, environment, and runtime states. It advances each once per loop and asserts that their complete states match after every tick. **Side by side** means sequential lockstep comparison, not parallel threads and not writing to two backends from one simulation instance.

## Design diagram

```text
                SimulationPlayground
                /                 \\
      coordinates agent         load() / save()
          behavior                   |
             |                 StateStorage (ABC)
           Agent                /             \\
         /   |   \\       MemoryStorage    JSONFileStorage
      Human  |  Zombie      (RAM)          (disk)
         |   |
     ArmedHuman
```

The `SimulationPlayground` class depends on **only** the `StateStorage` abstraction through `load()` and `save(state)`. The constructor accepts a backend, rather than constructing one internally.

## Detailed classes and responsibilities

**StateStorage (abstract base class):** defines `load()` and `save()`. It is the contract between simulation and persistence.

**MemoryStorage:** stores a deep-copied dictionary in RAM. This is fast and needs no file, but is temporary.

**JSONFileStorage:** serializes/deserializes the same dictionary to/from a JSON file, preserving state on disk. It writes through a temporary file then replaces the destination to avoid partially written snapshots.

**Agent:** abstract base class, adapted from the group's original code. Provides position, Euclidean distance, bounded movement, and damage.

**Human:** flees nearby zombies (perception radius 25) or wanders.

**ArmedHuman:** inherits from `Human`, attacks zombies within range 35 for 45 damage with a six-tick cooldown, and flees.

**Zombie:** chases humans within radius 120, loses 0.05 health per tick, bites within range 3.2 for 40 damage, and converts a killed human into a zombie.

**SimulationPlayground:** rebuilds live agent objects from the saved snapshot at the start of each tick, updates the agents, removes dead agents, adds newly converted zombies, increments the runtime counter, and saves the complete updated snapshot. It contains no JSON or dictionary persistence implementation.

## What was adapted from the group project

| Feature | Original Zombie Game | Midterm adaptation |
| --- | --- | --- |
| Agent hierarchy | Agent, Human, ArmedHuman, Zombie | Same conceptual hierarchy |
| Environment | 1200 x 1200 playground | Same default dimensions |
| Human movement | flee or wander | flee or wander |
| Armed humans | attack and cooldown | attack and cooldown |
| Zombies | chase, starve, bite, convert | same simplified rules |
| Nearest-agent search | spatial grid and optional multiprocessing | simple linear search for clarity |
| User interface | Tkinter visualization | console comparison |
| Database | PostgreSQL for run/history persistence | JSON state snapshots and in-memory snapshots |
| Live state | Python objects held by playground | serialized snapshots loaded through storage abstraction |

This distinction matters: the original PostgreSQL manager is used for recording run/history information, while this midterm specifically demonstrates storage of **live agent, environment, and runtime state**. They are related but not identical responsibilities.

## State structure

Each saved snapshot has:
- **agents:** a list of dictionaries with IDs, type, x/y coordinates, speed, health, and cooldown where applicable
- **environment:** width, height, and terrain label
- **runtime:** tick count, random seed, and next agent ID

Agent records are reconstructed as class instances each tick. The game rules operate on `Agent` subclasses; the storage classes operate only on generic state dictionaries.

## Why the design decouples the layers

1. **Abstraction:** `StateStorage` hides whether state lives in RAM or JSON.
2. **Polymorphism:** both backends implement the same methods.
3. **Dependency injection:** the backend is passed to `SimulationPlayground` at construction.
4. **Dependency inversion:** game rules rely on the interface rather than a specific backend.
5. **Single responsibility:** agents handle behavior, the playground coordinates ticks, and storage classes handle saving/loading.
6. **Extensibility:** a third backend (for example, a SQLite or PostgreSQL state repository) can implement the interface without rewriting `step()`.

To switch, only the setup changes (with `from pathlib import Path`):

```python
game = SimulationPlayground(MemoryStorage(initial_state()))
# OR
game = SimulationPlayground(JSONFileStorage(Path("game_state.json"), initial_state()))
```

Both execute `game.step()` unchanged.

## Testing and demonstration

Run `python -m unittest -v`. Tests cover:
- 20 identical ticks across memory and JSON
- copy isolation for in-memory snapshots
- persistence of agents, environment, and runtime in the JSON file
- preservation of the three agent types and first-tick execution\n- armed-human shooting and cooldown\n- zombie bite and conversion of a human\n- isolation between independent simulation instances
- execution of the complete comparison demo

The main demo also checks `memory_state == file_state == memory.load() == file_storage.load()` after each step. Matching **entire snapshots** is stronger than comparing only population counts.

## Important limitations and engineering decisions

This is a small, deterministic **demonstration**, not the entire 10,000-agent group game. It deliberately replaces spatial-grid/multiprocessing searches with linear scans to keep the storage architecture easy to inspect. It does not require Tkinter or a running database. A deterministic random seed derived from the tick gives both independent simulations the same random movement. The entire state is loaded and saved on each tick, which is simple but inefficient for very large populations. The JSON backend initializes from the supplied initial state each time it is constructed; it does not resume a previous saved run automatically. Concurrent writes and malformed-file recovery are outside this midterm's scope.

## Questions to defend in class

**Why not access a JSON file directly inside the simulation?** That would mix game rules with persistence. Switching to RAM or a DBMS would force changes to the simulation.

**How does the design relate to our actual Zombie Game?** It retains the agent inheritance structure, the three concrete agent types, the arena, movement, combat, and conversion concepts from `Zombie_Game.py`; it simplifies the rendering and parallel search infrastructure.

**Where is state stored?** `MemoryStorage` keeps a snapshot in a Python dictionary. `JSONFileStorage` keeps the same snapshot on disk.

**How can you prove the simulation is independent of storage?** The exact same `SimulationPlayground` class runs against both backends, with assertions checking identical complete states.

**Is the group's PostgreSQL history logging the same thing?** No. The original DB logging records run metadata and population history; this midterm persists the complete *live* state for the next simulation tick.

**What would change to add a database backend?** Only a new `StateStorage` implementation and the setup code that constructs it; the simulation rules stay unchanged.

## Conclusion

This design uses the existing Zombie Game's OOP concepts to demonstrate a concrete separation between simulation and state storage. Two interchangeable backends and a side-by-side equivalence test make that separation visible and testable.
