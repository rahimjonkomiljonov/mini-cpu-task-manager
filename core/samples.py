"""Ready-made workloads that show typical scheduling situations."""

from core.pcb import PCB

# Each process: (pid, arrival, burst, priority, io_at, io_time). The last two are optional.
SAMPLES = {
    "Classic mix": [
        ("P1", 0, 7, 3), ("P2", 2, 4, 1), ("P3", 4, 1, 4), ("P4", 5, 4, 2),
    ],
    "Convoy effect": [
        ("P1", 0, 12, 2), ("P2", 0, 2, 1), ("P3", 0, 2, 3), ("P4", 0, 1, 2),
    ],
    "Starvation and aging": [
        ("P1", 0, 5, 5), ("P2", 0, 3, 1), ("P3", 2, 3, 1), ("P4", 5, 3, 2),
        ("P5", 8, 3, 1), ("P6", 11, 3, 2), ("P7", 14, 2, 1),
    ],
    "I/O-bound and CPU-bound": [
        ("P1", 0, 10, 2), ("P2", 0, 4, 1, 1, 3), ("P3", 1, 5, 3, 2, 4),
    ],
    "SJF capstone (idle gap)": [
        ("P1", 0, 7, 3), ("P2", 2, 4, 2), ("P3", 4, 1, 1), ("P4", 5, 4, 4),
        ("P5", 6, 6, 3), ("P6", 8, 2, 2), ("P7", 9, 5, 5), ("P8", 30, 3, 1),
    ],
}

# What to try with each sample (shown in the status bar after loading it).
HINTS = {
    "Classic mix": "A normal mixed workload: run every policy and compare the results.",
    "Convoy effect": "Run FCFS, then SJF: under FCFS three short processes wait behind the long P1.",
    "Starvation and aging": "Run Priority: P1 (priority 5) waits until all the others finish. Then turn on Aging.",
    "I/O-bound and CPU-bound": "P2 and P3 do I/O and move to WAITING. Try Round Robin with switch cost 1.",
    "SJF capstone (idle gap)": "The workload of our SJF assignment: P8 arrives late, so the CPU is idle for a while.",
}

DEFAULT_SAMPLE = "Classic mix"


def load(name):
    """Return the sample workload as a list of fresh PCBs."""
    return [PCB(*spec) for spec in SAMPLES[name]]
