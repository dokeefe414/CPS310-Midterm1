"""CPS 310 Midterm #1 — Daniel O'Keefe.

Demonstrates storage-independent zombie simulation using two interchangeable
storage backends, run side by side with identical initial conditions.
"""
from abc import ABC, abstractmethod
from copy import deepcopy
from pathlib import Path
import json
import tempfile


class StateStorage(ABC):
    """Abstract interface shared by every state storage implementation."""

    @abstractmethod
    def load(self) -> dict:
        """Load and return a separate copy of the complete game state."""
        pass

    @abstractmethod
    def save(self, state: dict) -> None:
        """Save a complete snapshot of the game state."""
        pass


class MemoryStorage(StateStorage):
    """Store snapshots in a Python dictionary in RAM."""

    def __init__(self, initial_state: dict):
        self._state = deepcopy(initial_state)

    def load(self) -> dict:
        return deepcopy(self._state)

    def save(self, state: dict) -> None:
        self._state = deepcopy(state)


class JSONFileStorage(StateStorage):
    """Store snapshots as a JSON document on disk."""

    def __init__(self, path: Path, initial_state: dict):
        self.path = Path(path)
        self.save(initial_state)

    def load(self) -> dict:
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def save(self, state: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Replace the file atomically to avoid partially written snapshots.
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=self.path.parent,
            prefix=".state-", suffix=".tmp", delete=False
        ) as handle:
            temporary_path = Path(handle.name)
            try:
                json.dump(state, handle, indent=2)
                handle.write("\n")
            except BaseException:
                temporary_path.unlink(missing_ok=True)
                raise
        temporary_path.replace(self.path)


class ZombieSimulation:
    """Simulation rules depend only on StateStorage, not a storage backend."""

    def __init__(self, storage: StateStorage):
        self.storage = storage

    def step(self) -> dict:
        state = self.storage.load()
        state["runtime"]["tick"] += 1

        width = state["environment"]["width"]
        zombie = state["agents"]["zombie"]
        human = state["agents"]["human"]

        if human["health"] > 0:
            # Move one cell toward the human each tick.
            if zombie["x"] < human["x"]:
                zombie["x"] = min(zombie["x"] + 1, width - 1)
            elif zombie["x"] > human["x"]:
                zombie["x"] = max(zombie["x"] - 1, 0)

            # Attack when both agents occupy the same position.
            if zombie["x"] == human["x"]:
                human["health"] = max(0, human["health"] - 25)

        self.storage.save(state)
        return state


def initial_state() -> dict:
    """Create a fresh state with agents, environment, and runtime."""
    return {
        "agents": {
            "zombie": {"id": "z1", "x": 0},
            "human": {"id": "h1", "x": 5, "health": 100},
        },
        "environment": {"width": 10, "terrain": "street"},
        "runtime": {"tick": 0},
    }


def run_demo(path: Path = Path("game_state.json"), steps: int = 8) -> None:
    """Advance two independent games in lockstep and verify equal results."""
    memory = MemoryStorage(initial_state())
    disk = JSONFileStorage(path, initial_state())

    memory_game = ZombieSimulation(memory)
    file_game = ZombieSimulation(disk)

    print("CPS 310 Midterm #1 | Daniel O'Keefe")
    print("tick | zombie x | human health | matching")
    for _ in range(steps):
        memory_state = memory_game.step()
        file_state = file_game.step()
        assert memory_state == file_state, "Storage backends disagree"
        assert memory_state == memory.load() == disk.load()
        print(
            f"{memory_state['runtime']['tick']:>4} | "
            f"{memory_state['agents']['zombie']['x']:>8} | "
            f"{memory_state['agents']['human']['health']:>12} | YES"
        )
    print(f"PASS: identical states for {steps} ticks; JSON saved to {path}")


if __name__ == "__main__":
    run_demo()
