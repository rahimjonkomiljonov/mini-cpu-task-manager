"""Text version of the simulator (no window needed).

    python cli.py                                    classic sample with FCFS
    python cli.py --policy "Round Robin" --quantum 2
    python cli.py --sample "I/O-bound and CPU-bound" --policy SJF
    python cli.py --compare                          all policies on the same workload
    python cli.py --list                             show the policy and sample names

Useful for testing a policy quickly and for copying results into the report.
"""

import argparse

from core import metrics, samples
from core.engine import Simulator
from core.pcb import NEW, WAITING
from policies import POLICIES


def show(value):
    return "-" if value is None else f"{value:.2f}"


def print_events(events):
    for time, _kind, text in events:
        print(f"        > t={time}: {text}")


def run_one(workload, policy, quantum, cs_cost, aging, quiet=False):
    sim = Simulator(workload, policy, quantum, cs_cost, aging)
    while not sim.finished:
        tick = sim.time
        events = sim.step()
        if quiet:
            continue
        print_events([e for e in events if e[0] == tick])        # start of the tick: arrivals, dispatches
        ready = " ".join(p.pid for p in sim.ready) or "-"
        waiting = " ".join(p.pid for p in sim.processes if p.state == WAITING) or "-"
        new = " ".join(p.pid for p in sim.processes if p.state == NEW) or "-"
        print(f"t={tick:>3} | CPU: {sim.gantt[-1]:<5}| ready: {ready:<14}| waiting: {waiting:<8}| new: {new}")
        print_events([e for e in events if e[0] > tick])         # end of the tick: finished, I/O request, aging
    return sim


def print_results(sim):
    print("\nGantt chart:")
    print("  " + " ".join(f"[{start}] {label}" for label, start, _end in sim.gantt_blocks()) + f" [{sim.time}]")
    print("\nPID   Arrival  Burst  Finish  Turnaround  Waiting  Response")
    for row in metrics.process_rows(sim):
        print(f"{row['pid']:<5} {row['arrival']:>7} {row['burst']:>6} {row['finish']:>7} "
              f"{row['turnaround']:>11} {row['waiting']:>8} {row['response']:>9}")
    m = metrics.summary(sim)
    print(f"\nAverage turnaround {show(m['avg_turnaround'])} | waiting {show(m['avg_waiting'])} | "
          f"response {show(m['avg_response'])}")
    print(f"Context switches {m['context_switches']} | CPU utilisation {m['cpu_utilisation']:.0f}% | "
          f"throughput {m['throughput']:.3f} processes per tick | total time {m['total_time']}")


def compare(workload, quantum, cs_cost, aging):
    print(f"{'Policy':<24}{'Turnaround':>11}{'Waiting':>9}{'Response':>10}{'Switches':>10}{'Time':>6}")
    for name, policy in POLICIES.items():
        sim = run_one(workload, policy, quantum, cs_cost, aging, quiet=True)
        m = metrics.summary(sim)
        print(f"{name:<24}{show(m['avg_turnaround']):>11}{show(m['avg_waiting']):>9}"
              f"{show(m['avg_response']):>10}{m['context_switches']:>10}{m['total_time']:>6}")


def main():
    parser = argparse.ArgumentParser(description="Mini CPU Task Manager - text mode")
    parser.add_argument("--policy", default="FCFS", help="policy name (see --list)")
    parser.add_argument("--sample", default=samples.DEFAULT_SAMPLE, help="sample workload name (see --list)")
    parser.add_argument("--quantum", type=int, default=2, help="time quantum for Round Robin")
    parser.add_argument("--cs", type=int, default=0, help="cost of one context switch, in ticks")
    parser.add_argument("--aging", action="store_true", help="turn on aging (priority policies)")
    parser.add_argument("--compare", action="store_true", help="compare all policies on the sample")
    parser.add_argument("--list", action="store_true", help="list policies and samples")
    args = parser.parse_args()

    if args.list:
        print("Policies:", ", ".join(f'"{name}"' for name in POLICIES))
        print("Samples: ", ", ".join(f'"{name}"' for name in samples.SAMPLES))
        return
    if args.policy not in POLICIES or args.sample not in samples.SAMPLES:
        parser.error("unknown policy or sample name - run with --list to see the names")

    workload = samples.load(args.sample)
    if args.compare:
        compare(workload, args.quantum, args.cs, args.aging)
    else:
        print(f"Policy: {args.policy} | sample: {args.sample} | quantum {args.quantum} | "
              f"context-switch cost {args.cs} | aging {'on' if args.aging else 'off'}\n")
        print_results(run_one(workload, POLICIES[args.policy], args.quantum, args.cs, args.aging))


if __name__ == "__main__":
    main()
