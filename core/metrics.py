"""Scheduling metrics, calculated from the PCBs after (or during) a simulation.

    turnaround time = finish - arrival
    waiting time    = time spent in the READY queue
    response time   = first time on the CPU - arrival
    throughput      = finished processes / total time
    CPU utilisation = time the CPU ran processes / total time
"""

from core.engine import IDLE, SWITCH
from core.pcb import TERMINATED


def process_rows(sim):
    """One dictionary per process, in the order of the workload."""
    rows = []
    for p in sim.processes:
        rows.append({
            "pid": p.pid,
            "arrival": p.arrival,
            "burst": p.burst,
            "io_time": p.io_time,
            "start": p.start,
            "finish": p.finish,
            "killed": p.killed,
            # A killed process never completed, so it has no turnaround or waiting time to report.
            "turnaround": None if p.killed else p.turnaround,
            "waiting": p.waited if p.finish is not None and not p.killed else None,
            "response": p.response,
        })
    return rows


def _average(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def summary(sim):
    """Numbers that describe the whole run.

    Averages are over the processes that completed their work; killed processes are left out.
    """
    done = [p for p in sim.processes if p.state == TERMINATED and not p.killed]
    total_time = sim.time
    busy = sum(1 for label in sim.gantt if label not in (IDLE, SWITCH))
    return {
        "finished": len(done),
        "killed": sum(1 for p in sim.processes if p.killed),
        "processes": len(sim.processes),
        "total_time": total_time,
        "avg_turnaround": _average([p.turnaround for p in done]),
        "avg_waiting": _average([p.waited for p in done]),
        "avg_response": _average([p.response for p in done]),
        "throughput": len(done) / total_time if total_time else 0.0,
        "cpu_utilisation": 100.0 * busy / total_time if total_time else 0.0,
        "context_switches": sim.context_switches,
        "switch_time": sim.gantt.count(SWITCH),
        "idle_time": sim.gantt.count(IDLE),
    }
