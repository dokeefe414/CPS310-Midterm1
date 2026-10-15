"""CPS 310 Midterm #1 — Daniel O'Keefe.

Individual storage-decoupling adaptation of dokeefe414/CPS310-Zombie-Game.
Original concepts: Agent/Human/ArmedHuman/Zombie, SimulationPlayground,
spatial arena, fleeing, chasing, shooting, biting, infection, and ticks.
Two identical independent simulations run in lockstep with different storage.
"""
from abc import ABC, abstractmethod
from copy import deepcopy
from pathlib import Path
import json
import math
import os
import random
import tempfile


class StateStorage(ABC):
    """Persistence contract; simulation never depends on a concrete backend."""
    @abstractmethod
    def load(self) -> dict:
        pass

    @abstractmethod
    def save(self, state: dict) -> None:
        pass


class MemoryStorage(StateStorage):
    """Independent state snapshots stored in RAM."""
    def __init__(self, initial_state: dict):
        self._state = deepcopy(initial_state)

    def load(self) -> dict:
        return deepcopy(self._state)

    def save(self, state: dict) -> None:
        self._state = deepcopy(state)


class JSONFileStorage(StateStorage):
    """Independent state snapshots stored in a JSON file."""
    def __init__(self, path: Path, initial_state: dict):
        self.path = Path(path)
        self.save(initial_state)

    def load(self) -> dict:
        with self.path.open(encoding="utf-8") as f:
            return json.load(f)

    def save(self, state: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=self.path.parent,
            prefix=".state-", suffix=".tmp", delete=False
        ) as f:
            temp_path = Path(f.name)
            try:
                json.dump(state, f, indent=2)
                f.write("\n")
            except BaseException:
                temp_path.unlink(missing_ok=True)
                raise
        os.replace(temp_path, self.path)


class Agent(ABC):
    """Common movement and damage behavior adapted from Zombie_Game.py."""
    def __init__(self, record: dict):
        self.record = record

    @property
    def x(self):
        return self.record["x"]

    @property
    def y(self):
        return self.record["y"]

    def distance_to(self, other: "Agent") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def move(self, tx: float, ty: float, width: float, height: float, away=False):
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist:
            direction = -1 if away else 1
            self.record["x"] = min(width, max(0, self.x + direction * dx / dist * self.record["speed"]))
            self.record["y"] = min(height, max(0, self.y + direction * dy / dist * self.record["speed"]))

    def take_damage(self, damage: float):
        self.record["health"] = max(0.0, self.record["health"] - damage)

    @abstractmethod
    def update(self, playground: "SimulationPlayground"):
        pass


class Human(Agent):
    """Flee from zombies within the original project's perception radius."""
    def update(self, playground: "SimulationPlayground"):
        nearest = playground.nearest(self, playground.zombies, 25.0)
        if nearest:
            self.move(nearest.x, nearest.y, playground.width, playground.height, away=True)
        else:
            # Original game wanders when no zombie is nearby.
            self.record["x"] = min(playground.width, max(0, self.x + playground.rng.uniform(-0.4, 0.4) * self.record["speed"]))
            self.record["y"] = min(playground.height, max(0, self.y + playground.rng.uniform(-0.4, 0.4) * self.record["speed"]))


class ArmedHuman(Human):
    """Flee and fire at nearby zombies, with cooldown."""
    def update(self, playground: "SimulationPlayground"):
        self.record["cooldown"] = max(0, self.record["cooldown"] - 1)
        target = playground.nearest(self, playground.zombies, 35.0)
        if target and self.record["cooldown"] == 0:
            target.take_damage(45.0)
            self.record["cooldown"] = 6
        super().update(playground)


class Zombie(Agent):
    """Starve, chase humans, bite, and trigger conversion on death."""
    def update(self, playground: "SimulationPlayground"):
        self.take_damage(0.05)
        if self.record["health"] <= 0:
            return
        target = playground.nearest(self, playground.humans, 120.0)
        if target:
            distance_before_move = self.distance_to(target)
            self.move(target.x, target.y, playground.width, playground.height)
            if distance_before_move <= 3.2 and target.record["health"] > 0:
                target.take_damage(40.0)
                self.record["health"] = min(120.0, self.record["health"] + 18.0)
                if target.record["health"] <= 0:
                    playground.new_zombies.append({
                        "id": playground.next_id(), "type": "Zombie",
                        "x": target.x, "y": target.y,
                        "speed": 2.1, "health": 120.0
                    })
        else:
            self.record["x"] = min(playground.width, max(0, self.x + playground.rng.uniform(-1, 1) * self.record["speed"]))
            self.record["y"] = min(playground.height, max(0, self.y + playground.rng.uniform(-1, 1) * self.record["speed"]))


class SimulationPlayground:
    """One tick of game rules; knows only the StateStorage interface.

    Agents are reconstructed from stored dictionaries every tick. The complete
    state includes agents, environment, runtime, and RNG state (seed+tick).
    This version uses deterministic per-tick random seeds for reproducibility.
    """
    def __init__(self, storage: StateStorage):
        self.storage = storage

    def next_id(self) -> str:
        value = self.state["runtime"]["next_id"]
        self.state["runtime"]["next_id"] += 1
        return f"z{value}"

    @staticmethod
    def nearest(agent: Agent, candidates: list[Agent], radius: float):
        eligible = [other for other in candidates if other.record["health"] > 0 and agent.distance_to(other) < radius]
        return min(eligible, key=agent.distance_to) if eligible else None

    def step(self) -> dict:
        self.state = self.storage.load()
        environment = self.state["environment"]
        self.width, self.height = environment["width"], environment["height"]
        runtime = self.state["runtime"]
        self.rng = random.Random(runtime["seed"] + runtime["tick"])
        self.humans, self.zombies = [], []
        for record in self.state["agents"]:
            if record["health"] <= 0:
                continue
            if record["type"] == "Human":
                self.humans.append(Human(record))
            elif record["type"] == "ArmedHuman":
                self.humans.append(ArmedHuman(record))
            elif record["type"] == "Zombie":
                self.zombies.append(Zombie(record))
            else:
                raise ValueError(f"Unknown agent type: {record['type']}")

        self.new_zombies = []
        for human in self.humans:
            human.update(self)
        for zombie in self.zombies:
            zombie.update(self)
        self.state["agents"] = [
            a.record for a in (*self.humans, *self.zombies)
            if a.record["health"] > 0
        ] + self.new_zombies
        runtime["tick"] += 1
        self.storage.save(self.state)
        return deepcopy(self.state)


def initial_state() -> dict:
    """Small, repeatable arena based on the group's three agent types."""
    return {
        "agents": [
            {"id": "h1", "type": "Human", "x": 15.0, "y": 15.0, "speed": 2.4, "health": 100.0},
            {"id": "a1", "type": "ArmedHuman", "x": 40.0, "y": 40.0, "speed": 2.1, "health": 100.0, "cooldown": 0},
            {"id": "z1", "type": "Zombie", "x": 18.0, "y": 15.0, "speed": 2.1, "health": 120.0},
            {"id": "z2", "type": "Zombie", "x": 42.0, "y": 40.0, "speed": 2.1, "health": 120.0}
        ],
        "environment": {"width": 1200.0, "height": 1200.0, "terrain": "square playground"},
        "runtime": {"tick": 0, "seed": 310, "next_id": 3}
    }


def run_demo(path: Path = Path("game_state.json"), steps: int = 10):
    memory = MemoryStorage(initial_state())
    file_storage = JSONFileStorage(path, initial_state())
    first, second = SimulationPlayground(memory), SimulationPlayground(file_storage)
    print("CPS 310 Midterm #1 — Daniel O'Keefe")
    print("tick | humans | zombies | memory == JSON")
    for _ in range(steps):
        a, b = first.step(), second.step()
        assert a == b == memory.load() == file_storage.load()
        humans = sum(agent["type"] != "Zombie" for agent in a["agents"])
        zombies = sum(agent["type"] == "Zombie" for agent in a["agents"])
        print(f"{a['runtime']['tick']:>4} | {humans:>6} | {zombies:>7} | YES")
    print("PASS: complete stored states match after every tick")


if __name__ == "__main__":
    run_demo()
