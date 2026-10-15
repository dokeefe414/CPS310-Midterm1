"""Tests for the two interchangeable storage backends."""
import json
import tempfile
import unittest
from pathlib import Path
from midterm1 import MemoryStorage, JSONFileStorage, ZombieSimulation, initial_state


class StorageTests(unittest.TestCase):
    def test_memory_copy_isolation(self):
        storage = MemoryStorage(initial_state())
        snapshot = storage.load()
        snapshot["agents"]["zombie"]["x"] = 99
        self.assertEqual(storage.load()["agents"]["zombie"]["x"], 0)

    def test_backends_have_identical_simulation_behavior(self):
        with tempfile.TemporaryDirectory() as folder:
            memory = MemoryStorage(initial_state())
            disk = JSONFileStorage(Path(folder) / "state.json", initial_state())
            first = ZombieSimulation(memory)
            second = ZombieSimulation(disk)
            for _ in range(10):
                self.assertEqual(first.step(), second.step())
                self.assertEqual(memory.load(), disk.load())
            self.assertEqual(memory.load()["runtime"]["tick"], 10)
            self.assertEqual(memory.load()["agents"]["human"]["health"], 0)

    def test_file_persists_for_new_reader(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.json"
            disk = JSONFileStorage(path, initial_state())
            ZombieSimulation(disk).step()
            self.assertEqual(disk.load()["runtime"]["tick"], 1)
            self.assertEqual(json.loads(path.read_text())["runtime"]["tick"], 1)


if __name__ == "__main__":
    unittest.main()
