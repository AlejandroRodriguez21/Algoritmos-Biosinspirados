"""Prueba de integración con ventana oculta; requiere Tcl/Tk."""

import time
import tkinter as tk
import unittest

from main import Application


class InterfaceTests(unittest.TestCase):
    def test_start_pause_finish_replay_reset(self):
        root = tk.Tk()
        root.withdraw()
        app = Application(root)
        try:
            root.update()
            app.start()
            app.pause()
            self.assertTrue(app.paused)
            self.assertFalse(app.gate.is_set())
            app.pause()
            deadline = time.monotonic() + 15
            while app.running and time.monotonic() < deadline:
                root.update()
                time.sleep(0.02)
            self.assertFalse(app.running, "La evolución no terminó dentro del plazo")
            self.assertTrue(app.best.solved)
            self.assertIn("Óptimo comprobado", app.status.cget("text"))
            app.replay()
            root.update()
            self.assertIsNotNone(app.animation_index)
            previous_maze = app.maze
            app.new_maze()
            self.assertNotEqual(app.maze, previous_maze)
            self.assertIsNone(app.best)
            self.assertIsNone(app.animation_id)
            app.start()
            app.reset()
            root.update()
            self.assertFalse(app.running)
            self.assertIsNone(app.best)
        finally:
            app.close()


if __name__ == "__main__":
    unittest.main()
