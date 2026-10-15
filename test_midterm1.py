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

    def test_agent_types_and_combat(self):
        state = initial_state()
        self.assertEqual({a["type"] for a in state["agents"]}, {"Human", "ArmedHuman", "Zombie"})
        store = MemoryStorage(state)
        SimulationPlayground(store).step()
        self.assertEqual(store.load()["runtime"]["tick"], 1)

    def test_demo(self):
        with tempfile.TemporaryDirectory() as folder:
            run_demo(Path(folder) / "state.json", steps=3)


if __name__ == "__main__":
    unittest.main()
