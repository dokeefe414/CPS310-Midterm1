"""Automated checks for the original-Zombie-Game-inspired midterm design."""
import json
import tempfile
import unittest
from pathlib import Path
from midterm1 import (
    ArmedHuman, Human, Zombie, MemoryStorage, JSONFileStorage,
    SimulationPlayground, initial_state, run_demo,
)


class MidtermTests(unittest.TestCase):
    def test_both_backends_remain_identical(self):
        with tempfile.TemporaryDirectory() as folder:
            memory = MemoryStorage(initial_state())
            disk = JSONFileStorage(Path(folder) / "state.json", initial_state())
            m, d = SimulationPlayground(memory), SimulationPlayground(disk)
            for tick in range(1, 21):
                self.assertEqual(m.step(), d.step())
                self.assertEqual(memory.load(), disk.load())
                self.assertEqual(memory.load()["runtime"]["tick"], tick)

    def test_memory_isolation(self):
        store = MemoryStorage(initial_state())
        copy = store.load()
        copy["agents"][0]["health"] = -100
        self.assertEqual(store.load()["agents"][0]["health"], 100.0)

    def test_file_contains_complete_state(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.json"
            store = JSONFileStorage(path, initial_state())
            SimulationPlayground(store).step()
            state = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(state["runtime"]["tick"], 1)
            self.assertIn("environment", state)
            self.assertIn("agents", state)

    def test_agent_types_and_first_tick(self):
        state = initial_state()
        self.assertEqual({a["type"] for a in state["agents"]}, {"Human", "ArmedHuman", "Zombie"})
        store = MemoryStorage(state)
        SimulationPlayground(store).step()
        self.assertEqual(store.load()["runtime"]["tick"], 1)

    def test_armed_human_shoots_and_sets_cooldown(self):
        state = initial_state()
        # Isolate an armed human and a nearby zombie.
        state["agents"] = [
            {"id": "a1", "type": "ArmedHuman", "x": 10.0, "y": 10.0,
             "speed": 2.1, "health": 100.0, "cooldown": 0},
            {"id": "z1", "type": "Zombie", "x": 20.0, "y": 10.0,
             "speed": 2.1, "health": 120.0},
        ]
        result = SimulationPlayground(MemoryStorage(state)).step()
        armed = next(a for a in result["agents"] if a["type"] == "ArmedHuman")
        zombie = next(a for a in result["agents"] if a["type"] == "Zombie")
        self.assertEqual(armed["cooldown"], 6)
        self.assertLess(zombie["health"], 120.0)

    def test_zombie_bite_and_conversion(self):
        state = initial_state()
        state["agents"] = [
            {"id": "h1", "type": "Human", "x": 10.0, "y": 10.0,
             "speed": 0.0, "health": 40.0},
            {"id": "z1", "type": "Zombie", "x": 11.0, "y": 10.0,
             "speed": 2.1, "health": 120.0},
        ]
        result = SimulationPlayground(MemoryStorage(state)).step()
        self.assertEqual(len(result["agents"]), 2)
        self.assertTrue(all(a["type"] == "Zombie" for a in result["agents"]))
        self.assertEqual(result["runtime"]["next_id"], 4)

    def test_state_isolation_between_simulations(self):
        original = initial_state()
        first = MemoryStorage(original)
        second = MemoryStorage(original)
        SimulationPlayground(first).step()
        self.assertEqual(second.load()["runtime"]["tick"], 0)
        self.assertEqual(first.load()["runtime"]["tick"], 1)

    def test_demo(self):
        with tempfile.TemporaryDirectory() as folder:
            run_demo(Path(folder) / "state.json", steps=3)


if __name__ == "__main__":
    unittest.main()
