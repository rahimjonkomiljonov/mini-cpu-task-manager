"""Tests for the task-manager part: managing a live process, and the saved CPU context.

Run all tests from the project folder:   python -m unittest -v
"""

import random
import unittest

from core import metrics, samples
from core.engine import IDLE, SWITCH, Simulator
from core.pcb import PCB, NEW, READY, RUNNING, WAITING, SUSPENDED, TERMINATED
from policies import ALL, POLICIES

CLASSIC = "Classic mix"                     # P1(0,7) P2(2,4) P3(4,1) P4(5,4)


def start(policy_name, workload, ticks=0, **settings):
    """A simulator that has already run for some ticks."""
    sim = Simulator(workload, POLICIES[policy_name], **settings)
    for _ in range(ticks):
        sim.step()
    return sim


class ContextSwitch(unittest.TestCase):
    """The CPU registers must be saved in the PCB and restored from it."""

    def test_a_process_does_not_notice_that_it_was_interrupted(self):
        # ACC adds 1 + 2 + ... + burst. That sum is only correct if every context switch
        # saved the registers of the old process and restored the registers of the new one.
        for policy in ALL:
            sim = Simulator(samples.load(CLASSIC), policy, quantum=1, cs_cost=1).run_all()
            for p in sim.processes:
                self.assertEqual(p.context, {"PC": p.burst, "ACC": p.burst * (p.burst + 1) // 2},
                                 f"{policy.NAME}, {p.pid}")

    def test_the_context_is_saved_at_preemption_and_loaded_at_dispatch(self):
        sim = start("Round Robin", samples.load(CLASSIC), ticks=3, quantum=2)   # P1 ran 0-2, P2 runs now
        p1, p2 = sim.processes[0], sim.processes[1]
        self.assertEqual((p1.state, p1.context), (READY, {"PC": 2, "ACC": 3}))  # saved: 1 + 2 = 3
        self.assertEqual((p2.state, sim.cpu), (RUNNING, {"PC": 1, "ACC": 1}))   # the CPU holds P2's values
        self.assertEqual(sim.last_saved, ("P1", {"PC": 2, "ACC": 3}))

    def test_the_policy_is_asked_again_when_a_paid_switch_is_over(self):
        # A runs. B (priority 2) arrives at 1: a switch to B starts and takes 2 ticks.
        # C (priority 1) arrives at 2, during the switch, so C must get the CPU, not B.
        workload = [PCB("A", 0, 5, 3), PCB("B", 1, 3, 2), PCB("C", 2, 2, 1)]
        sim = Simulator(workload, POLICIES["Priority (preemptive)"], cs_cost=2).run_all()
        self.assertEqual(sim.gantt_blocks()[:3], [("A", 0, 1), (SWITCH, 1, 3), ("C", 3, 5)])


class ManagingALiveProcess(unittest.TestCase):

    def test_kill_the_running_process(self):
        sim = start("FCFS", samples.load(CLASSIC), ticks=3)                     # P1 is running
        sim.kill("P1")
        p1 = sim.processes[0]
        self.assertEqual((p1.state, p1.killed, p1.finish, p1.remaining), (TERMINATED, True, 3, 4))
        self.assertIsNone(sim.running)
        sim.run_all()
        self.assertEqual(sim.gantt_blocks(), [("P1", 0, 3), ("P2", 3, 7), ("P3", 7, 8), ("P4", 8, 12)])
        m = metrics.summary(sim)
        self.assertEqual((m["finished"], m["killed"]), (3, 1))                  # P1 is not in the averages
        self.assertAlmostEqual(m["avg_turnaround"], (5 + 4 + 7) / 3)

    def test_kill_a_process_that_has_not_arrived(self):
        sim = start("FCFS", samples.load(CLASSIC), ticks=1)
        sim.kill("P4")
        sim.run_all()
        self.assertNotIn("P4", sim.gantt)

    def test_suspend_and_resume(self):
        sim = start("FCFS", samples.load(CLASSIC), ticks=3)                     # P1 is running, pc = 3
        sim.suspend("P1")
        p1 = sim.processes[0]
        self.assertEqual((p1.state, p1.context["PC"]), (SUSPENDED, 3))          # its context is saved
        for _ in range(4):
            sim.step()                                                          # P2 uses the CPU meanwhile
        self.assertEqual(sim.gantt[3:7], ["P2"] * 4)
        self.assertEqual((p1.remaining, p1.suspended_time), (4, 4))             # P1 did nothing
        sim.resume("P1")
        self.assertEqual((p1.state, sim.ready[-1]), (READY, p1))                # back at the tail of the queue
        sim.run_all()
        self.assertEqual(p1.context["PC"], 7)                                   # it continued where it stopped
        self.assertEqual(p1.turnaround, p1.burst + p1.waited + p1.suspended_time)

    def test_suspend_during_io_pauses_the_io(self):
        sim = start("FCFS", [PCB("P1", 0, 4, io_at=1, io_time=3)], ticks=2)     # 1 of 3 I/O ticks done
        p1 = sim.processes[0]
        self.assertEqual((p1.state, p1.io_left), (WAITING, 2))
        sim.suspend("P1")
        sim.step()
        sim.step()
        self.assertEqual(p1.io_left, 2)
        sim.resume("P1")
        self.assertEqual(p1.state, WAITING)                                     # back to its unfinished I/O
        sim.run_all()
        self.assertEqual(p1.turnaround, p1.burst + p1.io_waited + p1.waited + p1.suspended_time)

    def test_only_suspended_processes_left(self):
        sim = start("FCFS", [PCB("P1", 0, 4)], ticks=1)
        sim.suspend("P1")
        self.assertTrue(sim.stalled)
        self.assertFalse(sim.finished)
        sim.step()
        self.assertEqual(sim.gantt[-1], IDLE)
        with self.assertRaises(RuntimeError):                                   # it would never end
            sim.run_all()
        sim.resume("P1")
        self.assertTrue(sim.run_all().finished)

    def test_a_new_priority_preempts_immediately(self):
        sim = start("Priority (preemptive)", samples.load(CLASSIC), ticks=3)    # P2 (priority 1) is running
        self.assertEqual(sim.running.pid, "P2")
        sim.set_priority("P1", 0)                                               # P1 becomes the most important
        sim.step()
        self.assertEqual(sim.running.pid, "P1")

    def test_create_a_process_while_the_simulation_runs(self):
        sim = start("FCFS", samples.load(CLASSIC), ticks=5)
        sim.create(PCB("P9", 0, 2))                                             # arrival 0 is in the past
        p9 = sim.find("P9")
        self.assertEqual((p9.state, p9.arrival), (NEW, 5))
        sim.run_all()
        self.assertEqual(sim.gantt_blocks()[-1], ("P9", 16, 18))
        with self.assertRaises(ValueError):
            sim.create(PCB("P1", 0, 2))                                         # the name is taken

    def test_create_after_everything_has_finished(self):
        sim = start("FCFS", [PCB("P1", 0, 2)]).run_all()
        sim.create(PCB("P2", 0, 1))
        self.assertFalse(sim.finished)
        self.assertEqual(sim.run_all().gantt, ["P1", "P1", "P2"])

    def test_kill_or_suspend_the_target_of_a_context_switch(self):
        for operation in ("kill", "suspend"):
            # At t=7 P1 finishes and a 2-tick switch to P2 starts. We remove P2 during the switch.
            sim = start("FCFS", samples.load(CLASSIC), ticks=8, cs_cost=2)
            self.assertEqual((sim.gantt[-1], sim.switch_target.pid), (SWITCH, "P2"))
            getattr(sim, operation)("P2")
            self.assertIsNone(sim.switch_target)
            sim.step()                                                          # the second tick of the switch
            sim.step()
            self.assertEqual(sim.gantt[8:], [SWITCH, "P3"])                     # the next in line got the CPU
            # ... and when nobody at all is ready, the CPU simply stays idle.
            sim = start("FCFS", [PCB("P1", 0, 2), PCB("P2", 0, 2)], ticks=3, cs_cost=2)
            getattr(sim, operation)("P2")
            sim.step()
            sim.step()
            self.assertIsNone(sim.running)

    def test_requests_that_make_no_sense_are_refused(self):
        sim = start("FCFS", samples.load(CLASSIC), ticks=8)                     # P1 has finished, P4 is READY
        for bad in (lambda: sim.kill("P1"), lambda: sim.kill("nobody"), lambda: sim.resume("P4"),
                    lambda: sim.set_priority("P4", -1)):
            with self.assertRaises(ValueError):
                bad()
        sim.suspend("P4")
        with self.assertRaises(ValueError):
            sim.suspend("P4")                                                   # it is already suspended
        early = start("FCFS", samples.load(CLASSIC), ticks=1)
        with self.assertRaises(ValueError):
            early.suspend("P4")                                                 # it has not arrived yet

    def test_io_input_mistakes_are_refused(self):
        for bad in [("P1", 0, 3, 1, 0, 5),       # I/O after 0 CPU units is not possible
                    ("P1", 0, 3, 1, None, 5)]:   # a duration without a start
            with self.assertRaises(ValueError):
                PCB(*bad)
        self.assertIsNone(PCB("P1", 0, 3, 1, "", 0).io_at)                      # empty fields = no I/O


class ShortestJobWithIO(unittest.TestCase):

    def test_sjf_compares_the_next_cpu_burst(self):
        # P1 needs 6 units in total, but asks for I/O after 1: its next CPU burst is 1.
        # P2 needs 3 units. SJF must choose P1 first, because 1 < 3.
        sim = Simulator([PCB("P1", 0, 6, io_at=1, io_time=2), PCB("P2", 0, 3)], POLICIES["SJF"]).run_all()
        self.assertEqual(sim.gantt_blocks(), [("P1", 0, 1), ("P2", 1, 4), ("P1", 4, 9)])


class RulesThatAlwaysHoldWhileTheUserInterferes(unittest.TestCase):
    """Random workloads with random kill / suspend / resume / priority / create between the ticks."""

    def test_invariants(self):
        rng = random.Random(7)
        for round_number in range(300):
            workload = []
            for i in range(rng.randint(1, 7)):
                burst = rng.randint(1, 9)
                io_at = rng.randint(1, burst - 1) if burst > 1 and rng.random() < 0.3 else None
                workload.append(PCB(f"P{i + 1}", rng.randint(0, 10), burst, rng.randint(0, 5),
                                    io_at, rng.randint(1, 4) if io_at else 0))
            policy = ALL[round_number % len(ALL)]
            sim = Simulator(workload, policy, quantum=rng.randint(1, 4), cs_cost=rng.randint(0, 2),
                            aging=rng.random() < 0.5)
            created = 0
            while not sim.finished:
                self.assertLess(sim.time, 2000, "the simulation does not end")
                alive = [p for p in sim.processes if p.state != TERMINATED]
                p = rng.choice(alive)
                action = rng.random()
                if sim.stalled or (p.state == SUSPENDED and action < 0.5):
                    sim.resume(rng.choice([q for q in alive if q.state == SUSPENDED]).pid)
                elif action < 0.04:
                    sim.kill(p.pid)
                elif action < 0.10 and p.state not in (NEW, SUSPENDED):
                    sim.suspend(p.pid)
                elif action < 0.15:
                    sim.set_priority(p.pid, rng.randint(0, 5))
                elif action < 0.18 and created < 3:
                    created += 1
                    sim.create(PCB(f"N{created}", rng.randint(0, sim.time + 3), rng.randint(1, 5)))
                sim.step()

                # the ready queue holds exactly the READY processes, and at most one process is RUNNING
                self.assertEqual({q.pid for q in sim.ready}, {q.pid for q in sim.processes if q.state == READY})
                self.assertEqual([q for q in sim.processes if q.state == RUNNING],
                                 [sim.running] if sim.running else [])

            self.assertEqual(len(sim.gantt), sim.time)
            for p in sim.processes:
                self.assertEqual(sim.gantt.count(p.pid), p.pc)                  # the Gantt chart and the PCB agree
                self.assertEqual(p.context, {"PC": p.pc, "ACC": p.pc * (p.pc + 1) // 2})
                self.assertNotIn(p.pid, sim.gantt[:p.arrival])
                if p.killed:
                    self.assertGreater(p.remaining, 0)
                else:
                    self.assertEqual(p.remaining, 0)
                    # every tick of its life a process is running, doing I/O, waiting, or suspended
                    self.assertEqual(p.turnaround, p.burst + p.io_waited + p.waited + p.suspended_time)


if __name__ == "__main__":
    unittest.main()
