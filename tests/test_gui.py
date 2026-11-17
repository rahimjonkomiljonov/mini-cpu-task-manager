"""A smoke test of the window: the main button paths run without an error.

The window opens for a moment while these tests run.
They are skipped automatically when there is no display (for example over SSH)
or when tkinter is not installed.
"""

import unittest

try:
    import tkinter as tk
    from gui.app import App
except ImportError:              # tkinter is not installed
    tk = App = None

from core import samples
from core.pcb import PCB
from policies import POLICIES


class WindowTest(unittest.TestCase):
    def setUp(self):
        if App is None:
            self.skipTest("tkinter is not installed")
        try:
            self.app = App()
        except tk.TclError:
            self.skipTest("no display")
        self.app.update()                                # draw the window once

    def tearDown(self):
        self.app.destroy()

    def choose(self, policy, quantum=2, cs_cost=0, aging=False):
        controls = self.app.controls
        controls.policy.set(policy)
        controls.quantum.set(str(quantum))
        controls.cs_cost.set(str(cs_cost))
        controls.aging.set(aging)
        self.app.reset()

    def run_to_the_end(self):
        for _ in range(500):
            if self.app.sim.finished:
                break
            self.app.step()
        self.app.update()
        self.assertTrue(self.app.sim.finished)

    def test_every_policy_finishes_every_sample(self):
        for sample in samples.SAMPLES:
            self.app.load_sample(sample)
            for policy in POLICIES:
                self.choose(policy, cs_cost=1, aging=True)
                self.run_to_the_end()

    def test_the_window_shows_what_the_simulator_says(self):
        self.app.load_sample(samples.DEFAULT_SAMPLE)
        self.choose("Round Robin", quantum=2)
        for _ in range(7):
            self.app.step()
        table = self.app.table.tree
        for p in self.app.sim.processes:                 # every PCB row shows the real state
            self.assertEqual(table.set(p.pid, "state"), p.state)
        self.assertEqual(self.app.controls.clock.cget("text"), "7")

    def test_add_remove_and_clear(self):
        self.app.clear_all()
        self.assertTrue(self.app.sim.finished)           # nothing to simulate
        self.app.add_process(PCB("P1", 0, 3))
        self.app.add_process(PCB("P2", 1, 2, 1, 1, 2))   # this one does I/O
        self.assertEqual(len(self.app.sim.processes), 2)
        self.run_to_the_end()
        self.app.table.tree.selection_set("P1")
        self.app.remove_selected()
        self.assertEqual([p.pid for p in self.app.workload], ["P2"])

    def test_random_workloads_and_the_compare_tab(self):
        for _ in range(5):
            self.app.random_workload()
            self.app.compare.run()
            self.app.update()
            self.assertEqual(len(self.app.compare.tree.get_children()), len(POLICIES))

    def test_the_task_manager_buttons(self):
        app, table = self.app, self.app.table.tree
        app.load_sample(samples.DEFAULT_SAMPLE)
        self.choose("Priority (preemptive)", cs_cost=1)
        for _ in range(3):
            app.step()

        table.selection_set("P1")
        app.suspend_selected()
        self.assertEqual(table.set("P1", "state"), "SUSPENDED")
        app.change_priority(0)
        app.resume_selected()
        self.assertEqual(table.set("P1", "state"), "READY")
        self.assertEqual(table.set("P1", "priority"), "0")

        table.selection_set("P2")
        app.kill_selected()
        self.assertEqual(table.set("P2", "finish"), "3 killed")

        app.add_process(PCB("P9", 0, 2))                 # created live: the clock does not go back to 0
        self.assertEqual(app.sim.time, 3)
        self.assertEqual(table.set("P9", "state"), "NEW")
        self.assertIn("P9", app.colors)
        self.run_to_the_end()

        app.reset()                                      # Reset replays the workload, with P2 alive again
        self.assertEqual([p.pid for p in app.sim.processes], ["P1", "P2", "P3", "P4", "P9"])
        self.assertFalse(any(p.killed for p in app.sim.processes))

    def test_the_clock_stops_when_only_suspended_processes_are_left(self):
        self.app.clear_all()
        self.app.add_process(PCB("P1", 0, 5))
        self.app.step()
        self.app.table.tree.selection_set("P1")
        self.app.suspend_selected()
        self.app.start_pause()                           # the clock starts, sees that nothing can run, and stops
        self.assertFalse(self.app.running)
        self.assertIn("suspended", self.app.status.cget("text"))


if __name__ == "__main__":
    unittest.main()
