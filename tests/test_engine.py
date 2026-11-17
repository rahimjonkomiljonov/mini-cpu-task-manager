"""Tests for the simulation core.

The expected numbers come from Gantt charts worked out by hand with the textbook rules
(draw them on paper yourself: it is good exam practice), so these tests show that
the simulator follows those rules.

Run all tests from the project folder:   python -m unittest -v
"""

import random
import unittest

from core import metrics, samples
from core.engine import IDLE, SWITCH, Simulator
from core.pcb import PCB, TERMINATED
from policies import ALL, POLICIES

CLASSIC = "Classic mix"                     # P1(0,7) P2(2,4) P3(4,1) P4(5,4)
CAPSTONE = "SJF capstone (idle gap)"
STARVATION = "Starvation and aging"


def run(policy_name, workload, **settings):
    return Simulator(workload, POLICIES[policy_name], **settings).run_all()


class KnownAnswers(unittest.TestCase):
    """Compare the simulator with Gantt charts worked out by hand."""

    def check(self, sim, blocks, turnaround, waiting, response):
        m = metrics.summary(sim)
        self.assertEqual(sim.gantt_blocks(), blocks)
        self.assertAlmostEqual(m["avg_turnaround"], turnaround)
        self.assertAlmostEqual(m["avg_waiting"], waiting)
        self.assertAlmostEqual(m["avg_response"], response)

    def test_fcfs(self):
        sim = run("FCFS", samples.load(CLASSIC))
        self.check(sim, [("P1", 0, 7), ("P2", 7, 11), ("P3", 11, 12), ("P4", 12, 16)], 8.75, 4.75, 4.75)
        self.assertEqual(sim.context_switches, 3)

    def test_sjf(self):
        sim = run("SJF", samples.load(CLASSIC))
        self.check(sim, [("P1", 0, 7), ("P3", 7, 8), ("P2", 8, 12), ("P4", 12, 16)], 8.0, 4.0, 4.0)

    def test_srtf(self):
        sim = run("SRTF", samples.load(CLASSIC))
        self.check(sim, [("P1", 0, 2), ("P2", 2, 4), ("P3", 4, 5), ("P2", 5, 7), ("P4", 7, 11), ("P1", 11, 16)],
                   7.0, 3.0, 0.5)

    def test_round_robin_quantum_3(self):
        sim = run("Round Robin", samples.load(CLASSIC), quantum=3)
        self.check(sim, [("P1", 0, 3), ("P2", 3, 6), ("P1", 6, 9), ("P3", 9, 10), ("P4", 10, 13),
                         ("P2", 13, 14), ("P1", 14, 15), ("P4", 15, 16)], 11.0, 7.0, 2.75)
        self.assertEqual(sim.context_switches, 7)

    def test_priority_non_preemptive(self):
        sim = run("Priority", samples.load(CLASSIC))      # priorities: P1=3 P2=1 P3=4 P4=2
        self.assertEqual(sim.gantt_blocks(), [("P1", 0, 7), ("P2", 7, 11), ("P4", 11, 15), ("P3", 15, 16)])

    def test_priority_preemptive(self):
        sim = run("Priority (preemptive)", samples.load(CLASSIC))
        self.assertEqual(sim.gantt_blocks(),
                         [("P1", 0, 2), ("P2", 2, 6), ("P4", 6, 10), ("P1", 10, 15), ("P3", 15, 16)])

    def test_sjf_capstone_with_idle_gap_and_tie(self):
        sim = run("SJF", samples.load(CAPSTONE))
        self.check(sim, [("P1", 0, 7), ("P3", 7, 8), ("P6", 8, 10), ("P2", 10, 14), ("P4", 14, 18),
                         ("P7", 18, 23), ("P5", 23, 29), (IDLE, 29, 30), ("P8", 30, 33)], 9.75, 5.75, 5.75)
        self.assertEqual(sim.context_switches, 6)          # starting after an idle CPU is not a switch


class SpecialSituations(unittest.TestCase):

    def test_round_robin_alone_gets_a_fresh_quantum(self):
        # P1 is alone until t=3, so at t=2 it simply continues with a new time slice.
        sim = run("Round Robin", [PCB("P1", 0, 5), PCB("P2", 3, 2)], quantum=2)
        self.assertEqual(sim.gantt_blocks(), [("P1", 0, 4), ("P2", 4, 6), ("P1", 6, 7)])

    def test_io_moves_process_to_waiting(self):
        # P1 runs 2 units, then does I/O for 3 ticks. P2 uses the CPU meanwhile.
        sim = run("FCFS", [PCB("P1", 0, 4, io_at=2, io_time=3), PCB("P2", 0, 3)])
        self.assertEqual(sim.gantt_blocks(), [("P1", 0, 2), ("P2", 2, 5), ("P1", 5, 7)])
        p1, p2 = sim.processes
        self.assertEqual((p1.finish, p1.waited), (7, 0))
        self.assertEqual((p2.finish, p2.waited), (5, 2))

    def test_cpu_is_idle_while_the_only_process_does_io(self):
        sim = run("FCFS", [PCB("P1", 0, 4, io_at=1, io_time=2)])
        self.assertEqual(sim.gantt_blocks(), [("P1", 0, 1), (IDLE, 1, 3), ("P1", 3, 6)])

    def test_context_switch_cost(self):
        sim = run("FCFS", samples.load(CLASSIC), cs_cost=1)
        self.assertEqual(sim.gantt_blocks(), [("P1", 0, 7), (SWITCH, 7, 8), ("P2", 8, 12), (SWITCH, 12, 13),
                                              ("P3", 13, 14), (SWITCH, 14, 15), ("P4", 15, 19)])
        self.assertEqual(metrics.summary(sim)["switch_time"], 3)

    def test_small_quantum_means_more_context_switches(self):
        few = run("Round Robin", samples.load(CLASSIC), quantum=8).context_switches
        many = run("Round Robin", samples.load(CLASSIC), quantum=1).context_switches
        self.assertGreater(many, few)

    def test_aging_rescues_a_starving_process(self):
        without = run("Priority", samples.load(STARVATION), aging=False).processes[0]
        with_aging = run("Priority", samples.load(STARVATION), aging=True).processes[0]
        self.assertEqual(without.waited, 17)               # P1 (low priority) runs last
        self.assertLess(with_aging.waited, without.waited)

    def test_invalid_processes_are_refused(self):
        for bad in [("P1", -1, 3), ("P1", 0, 0), ("", 0, 3), ("P1", 0, 3, 1, 3, 2), ("P1", 0, 3, 1, 1, 0)]:
            with self.assertRaises(ValueError):
                PCB(*bad)


class RulesThatAlwaysHold(unittest.TestCase):
    """Random workloads: whatever the policy, some facts must always be true."""

    def random_workload(self, rng):
        workload = []
        for i in range(rng.randint(1, 8)):
            burst = rng.randint(1, 9)
            io_at = rng.randint(1, burst - 1) if burst > 1 and rng.random() < 0.3 else None
            workload.append(PCB(f"P{i + 1}", rng.randint(0, 12), burst, rng.randint(0, 5),
                                io_at, rng.randint(1, 4) if io_at else 0))
        return workload

    def test_invariants(self):
        rng = random.Random(2026)
        for _ in range(300):
            workload = self.random_workload(rng)
            for policy in ALL:
                sim = Simulator(workload, policy, quantum=rng.randint(1, 4),
                                cs_cost=rng.randint(0, 2), aging=rng.random() < 0.5).run_all()
                m = metrics.summary(sim)
                self.assertTrue(all(p.state == TERMINATED for p in sim.processes))
                self.assertEqual(len(sim.gantt), sim.time)
                # the CPU did exactly the work that was asked for
                busy = sum(1 for label in sim.gantt if label not in (IDLE, SWITCH))
                self.assertEqual(busy, sum(p.burst for p in workload))
                self.assertEqual(m["switch_time"], sim.context_switches * sim.cs_cost)
                for p in sim.processes:
                    # every tick of its life a process is running, doing I/O, or waiting
                    self.assertEqual(p.turnaround, p.burst + p.io_time + p.waited)
                    self.assertGreaterEqual(p.start, p.arrival)
                    self.assertNotIn(p.pid, sim.gantt[:p.arrival])     # never runs before it arrives
                if not policy.PREEMPTIVE:
                    self.assertFalse([e for e in sim.events if e[1] == "preempt"])

    def test_same_workload_can_be_reused(self):
        workload = samples.load(CLASSIC)
        first = run("SRTF", workload).gantt
        second = run("SRTF", workload).gantt
        self.assertEqual(first, second)
        self.assertTrue(all(p.state == "NEW" for p in workload))       # the originals are untouched


if __name__ == "__main__":
    unittest.main()
