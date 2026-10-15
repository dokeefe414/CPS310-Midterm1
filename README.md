# CPS 310 — Midterm #1: Storage-Independent Zombie Simulation

**Student:** Daniel O'Keefe  
**Course:** CPS 310 — Fall 2026  
**Instructor:** Dr. Fanchao Meng

## Assignment and objective

The assignment asks for a concrete object-oriented design that separates a Zombie Game Simulation's rules from the way the live state of its agents, environment, and runtime is stored. At least two storage implementations must demonstrate that the simulation code does not change when storage changes.

This submission implements an **abstract storage interface**, an **in-memory dictionary backend**, and a **JSON-file backend**. Two independent simulations run side by side with identical starting conditions. Each uses the same `ZombieSimulation` class and executes the same `step()` method. The program checks their complete states for equality after every tick.

## Repository contents

| File | Purpose |
| --- | --- |
| `midterm1.py` | All OOP classes, game rules, and the executable demonstration |
| `test_midterm1.py` | Automated verification of both backends and state isolation |
| `game_state.json` | Example output snapshot produced by the file backend |
| `README.md` | Design, justification, instructions, and explanation |

## Running the project

Requirements: **Python 3.10+**; only Python standard-library modules are used. No installation or database server is needed.

From the repository directory:

```bash
python midterm1.py
python -m unittest -v
```

On some computers the command may be `python3` or `py`.

The first command runs two independent simulations in lockstep and prints a table of each tick's zombie position, human health, and a YES indicator when the complete state snapshots match. It also writes `game_state.json`. The second command runs three automated tests.

## Object-oriented architecture

```text
                     ZombieSimulation
                       (game rules)
                             |
                  calls load() and save()
                             |
                      StateStorage
                    (abstract interface)
                       /           \
                      /             \
              MemoryStorage     JSONFileStorage
              (RAM dictionary)   (JSON on disk)
```

**StateStorage (abstraction).** This abstract base class defines two operations: `load() -> dict` and `save(state: dict) -> None`. Any storage solution implementing the contract can be passed to `ZombieSimulation`.

**MemoryStorage (implementation 1).** Keeps the current snapshot in a private Python dictionary in RAM. It deep-copies data when saving and loading so outside code cannot accidentally mutate the stored snapshot. This backend is fast and simple, but state is lost when the process ends.

**JSONFileStorage (implementation 2).** Serializes a complete snapshot into a human-readable JSON file. `load()` deserializes that file into the same dictionary structure that `MemoryStorage` returns. A temporary file and atomic replacement are used during saving to reduce the chance of exposing a partially written snapshot. The file remains on disk after the program exits.

**ZombieSimulation (simulation layer).** The constructor receives a `StateStorage` object. Each `step()` loads the current state, increments the runtime tick, moves the zombie one cell toward the human, applies 25 damage when they meet, then saves the updated state. This class never opens files, serializes JSON, or accesses a storage backend's internal fields.

**Dependency injection.** The chosen backend is passed into `ZombieSimulation(storage)` when a simulation object is constructed. The simulation does not create or select the storage implementation itself.

## Complete state model

A single snapshot contains all three categories required by the prompt:

```json
{
  "agents": {
    "zombie": {"id": "z1", "x": 0},
    "human": {"id": "h1", "x": 5, "health": 100}
  },
  "environment": {"width": 10, "terrain": "street"},
  "runtime": {"tick": 0}
}
```

- **Agents:** zombie position and identity; human position, identity, and health.
- **Environment:** map width and terrain type.
- **Runtime:** current simulation tick.

The same snapshot structure is used by both storage solutions. Neither storage class needs to know the movement or attack rules.

## Why this decouples storage from simulation

The central dependency is `ZombieSimulation -> StateStorage`, **not** `ZombieSimulation -> MemoryStorage` or `ZombieSimulation -> JSONFileStorage`.

1. **Abstraction:** `StateStorage` exposes the operations needed by the simulation while hiding implementation details.
2. **Polymorphism:** both concrete storage classes can be used through the same interface.
3. **Dependency inversion:** high-level simulation logic depends on the storage abstraction rather than a concrete storage mechanism.
4. **Single responsibility:** game rules belong to the simulation class; persistence and retrieval belong to the storage classes.
5. **Open for extension:** a future `SQLiteStorage` could implement `load()` and `save()` without changing `ZombieSimulation.step()`.

Changing storage means constructing `ZombieSimulation(MemoryStorage(...))` or `ZombieSimulation(JSONFileStorage(...))`. No changes are required in the simulation class. This is the exact separation requested by the assignment.

## Side-by-side demonstration

`run_demo()` constructs **two separate storage objects** and **two separate simulation objects**, both initialized with the same state. They are advanced one after the other in each loop iteration. This is *lockstep comparison*, not true parallel threads, and not one simulation writing to both storage backends.

At each tick, the program checks:
- The returned snapshots from both simulations are identical.
- The returned snapshot matches what each backend actually stores.

Expected state progression for eight ticks:

| Tick | Zombie x | Human health |
| ---: | ---: | ---: |
| 1 | 1 | 100 |
| 2 | 2 | 100 |
| 3 | 3 | 100 |
| 4 | 4 | 100 |
| 5 | 5 | 75 |
| 6 | 5 | 50 |
| 7 | 5 | 25 |
| 8 | 5 | 0 |

The full state equality assertion covers the environment and runtime too, not just the displayed fields.

## Tests and how to interpret them

Run `python -m unittest -v`.

1. **Memory copy isolation:** changing a loaded dictionary without saving does not mutate the backend's stored state.
2. **Backend equivalence:** ten steps through two independent simulations produce identical full snapshots and end at tick 10 with human health 0.
3. **File persistence:** the file backend's saved state can be read back from the JSON document after a simulation step.

All tests should report `ok`. A passing test does not prove that all possible storage systems are correct, but it provides concrete evidence that these two implementations obey the shared contract for the demonstrated operations.

## Design tradeoffs and limitations

- This is a deliberately small, deterministic one-dimensional zombie simulation designed to isolate the storage architecture rather than recreate the entire group game.
- The whole state is loaded and saved every tick. For a large world, smaller incremental operations might be more efficient.
- JSON is human-readable and persistent, but file I/O is slower than memory access.
- `JSONFileStorage` initializes its file from the provided starting state when constructed; it does **not** automatically resume an existing run. The existing JSON file can still be inspected or loaded before a new initialization.
- No concurrency control, schema migration, distributed transactions, or recovery from invalid JSON is implemented.
- This example does not require a DBMS; a database backend could be added later using the same interface.

## Questions to prepare for when defending the design

**Q: Why not have ZombieSimulation write directly to a JSON file?**  
A: Then the simulation would depend on JSON and file operations. Switching to a dictionary or database would require modifying game logic.

**Q: How do you switch storage?**  
A: Pass a different implementation of `StateStorage` into the constructor. The `step()` method stays unchanged.

**Q: Why use an abstract base class?**  
A: It makes the required `load` and `save` operations explicit and ensures concrete subclasses implement them.

**Q: What does running both simultaneously mean here?**  
A: Two independent simulations are advanced in lockstep and their full states are compared after every tick. They are not separate operating-system threads.

**Q: Where are the live states?**  
A: They are complete snapshots containing agents, environment, and runtime. MemoryStorage keeps one in RAM; JSONFileStorage stores one on disk.

**Q: How would you add a database?**  
A: Implement a third `StateStorage` subclass with the same `load` and `save` signatures and pass it to `ZombieSimulation`.

## Conclusion

The implementation demonstrates that the **simulation rules remain unchanged** when switching between in-memory and file-based state storage. The interface, constructor injection, and backend-equivalence tests provide a concrete OOP solution to the midterm's decoupling requirement.
