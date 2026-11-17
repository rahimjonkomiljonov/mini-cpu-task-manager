# Team roles (8 members)

The syllabus allows AI-assisted coding, but every student must **understand, test and explain**
the code they submit. So every member owns one part of the project:

1. **Read** every line of your files and run the program until you can predict what it will do.
2. **Explain**: be ready to answer the questions listed for your role without notes.
3. **Improve**: add one improvement of your own (ideas below) so that the project contains your work.
4. **Write** your section of the report.

Everybody should also read `core/pcb.py` and the top of `core/engine.py` (about 100 lines):
all other parts depend on them.

## Overview

| # | Role | Files you own | Report section |
|---|---|---|---|
| 1 | Team lead, PCB and the clock | `main.py`, `build_app.py`, `core/pcb.py`, `core/engine.py` (`step`, `_admit_arrivals`, `_dispatch`, `_run_one_tick`) | Introduction, design, process and PCB |
| 2 | FCFS, SJF, SRTF | `policies/__init__.py`, `policies/fcfs.py`, `policies/sjf.py`, `policies/srtf.py` | The three policies, convoy effect |
| 3 | Priority and aging | `policies/priority.py`, `policies/priority_preemptive.py`, `Simulator._age` in `core/engine.py` | Priority scheduling, starvation, aging |
| 4 | Round Robin and context switch | `policies/rr.py`, `Simulator._schedule` and `_save_context` in `core/engine.py`, the CPU registers | Round Robin, quantum, context switch |
| 5 | I/O and metrics | `Simulator._leave_cpu` and `_finish_io` in `core/engine.py`, `core/metrics.py`, `core/samples.py`, `cli.py` | Process states with I/O, scheduling metrics |
| 6 | Window: workload, PCB table, task manager | `gui/app.py`, `gui/process_form.py`, `gui/pcb_table.py`, the part "managing a live process" of `core/engine.py` (`create`, `kill`, `suspend`, `resume`, `set_priority`) | User guide: input, PCB table, event log, managing processes |
| 7 | Window: state board, Gantt chart, controls | `gui/state_board.py`, `gui/gantt.py`, `gui/controls.py`, `gui/theme.py` | Interface design, screenshots |
| 8 | Results, comparison, tests | `gui/results.py`, `gui/compare.py`, `tests/` (also `tests/test_manage.py`) | Testing, experiments, final editing of the report |

## Role 1: team lead, PCB and the clock

**Understand**: the fields of the PCB and why they are split into "workload", "changing part" and "accounting";
the five phases of `Simulator.step()`; why the simulator works on *copies* of the PCBs (`clone`).

**Be ready to answer**
- What information does a real PCB hold that our PCB does not? (CPU registers, memory-management information,
  open files, ...)
- What happens, in order, inside one call of `step()`?
- How is the program turned into an application (`build_app.py`)? Why must the Mac version be built on a Mac?
- Why does the engine not contain any scheduling policy?

**Your own improvement (choose one)**
- Save the workload to a JSON file and load it again.
- Add a "Run to the end" button that uses `Simulator.run_all()`.
- Add a memory size to the PCB and admit a process (NEW -> READY) only when enough memory is free
  (this is the job of the long-term scheduler).

**Team lead tasks**: create the repository, review the merges, plan the demo, check that everybody can explain their part.

## Role 2: FCFS, SJF, SRTF

**Understand**: the policy "contract" in `policies/__init__.py`; what `choose_next` receives and returns;
why a non-preemptive policy starts with `if running is not None: return running`.

**Be ready to answer**
- Why does SJF give the lowest average waiting time of all non-preemptive policies?
- What is the difference between SJF and SRTF? Show a moment in the demo where SRTF preempts.
- What is the convoy effect? (Use the sample "Convoy effect": FCFS 10.50, SJF 2.25 average waiting time.)
- A real OS does not know the length of the next CPU burst. How can it be predicted? (exponential averaging)

**Your own improvement (choose one)**
- Add **HRRN** (Highest Response Ratio Next): choose the process with the largest
  `(waiting time + burst) / burst`. The README shows how to add a policy file.
- Draw the Gantt charts of the Classic mix by hand for your three policies and add them to the report.

## Role 3: Priority and aging

**Understand**: `eff_priority` (the effective priority) versus `priority` (the base priority);
when `_age` is called and what `AGING_INTERVAL` means.

**Be ready to answer**
- In our program, does a lower number mean a higher or a lower priority?
- What is starvation? Show it with the sample "Starvation and aging".
- How does aging solve starvation? What changes in the PCB table when aging is on?
- Aging makes P1 wait 12 ticks instead of 17, but the *average* waiting time becomes a little higher. Why?

**Your own improvement (choose one)**
- Add a spinbox to the control bar so the user can change the aging interval.
- Give the process its base priority back after it has used the CPU.
- Add a policy "Priority with Round Robin": processes with the same priority take turns.

## Role 4: Round Robin and context switch

**Understand**: `slice_used` and `quantum`; how `_schedule` preempts a process, counts a context switch
and, when the switch cost is not 0, lets the CPU do the switch for some ticks.

**Be ready to answer**
- What does the OS save and load during a context switch? Where do our event messages show this?
- Our CPU has two registers, PC and ACC. Where are they saved and restored? What would go wrong without
  `_save_context`? (Remove the line, run the tests, and see which test fails and why.)
- A context switch costs 2 ticks and a better process arrives during it. Who gets the CPU, and why?
- What happens with a very small quantum? With a very large quantum? (Try 1 and 8 on the Classic mix.)
- How does our program count context switches? Which dispatches are not counted?
- Why is a context switch "pure overhead"? (With switch cost 1, CPU utilisation falls from 100% to 67%.)

**Your own improvement (choose one)**
- Show the used part of the quantum on the RUNNING card, for example "slice 1/2".
- Add an "overhead" value to the Results tab: ticks lost to switching divided by total time.
- Add a quantum experiment to the report: quantum 1, 2, 3, 4, 8 on the same workload.

## Role 5: I/O and metrics

**Understand**: when a process moves RUNNING -> WAITING and WAITING -> READY; every formula in `core/metrics.py`;
how to use `cli.py`.

**Be ready to answer**
- Define turnaround time, waiting time and response time. Which one matters most for an interactive user?
- For a process with I/O, why is waiting time not equal to turnaround time minus burst time?
- What are throughput and CPU utilisation? Why is the CPU sometimes idle in the I/O sample?
- What is the difference between an I/O-bound and a CPU-bound process?

**Your own improvement (choose one)**
- Allow more than one I/O operation per process.
- Add a new metric, for example the longest waiting time or the standard deviation of the waiting times (fairness).
- Add a new sample workload that shows something interesting, with a hint in `HINTS`.

## Role 6: window: workload and PCB table

**Understand**: how `App` connects the panels to the simulator (`reset`, `step`, `_tick`, `refresh`);
how the form checks the input (`PCB._check` raises `ValueError`); how the table rows get their colours.

**Be ready to answer**
- What happens between a click on **Step** and the new picture on the screen?
- How does the clock run without freezing the window? (`after`, not `time.sleep`)
- What happens when the user types a wrong value, for example burst 0 or a PID that already exists?
- What exactly happens to a RUNNING process when the user presses Suspend? And Kill?
- Where does a resumed process go, and why not straight back to the CPU?
- Why are killed processes left out of the average waiting time?
- What does the program do when only suspended processes are left?

**Your own improvement (choose one)**
- Edit a process by double-clicking its row in the PCB table.
- Add a "Save event log" button that writes the log to a text file.
- Show the selected process in a small "PCB details" box.

## Role 7: window: state board, Gantt chart, controls

**Understand**: how the cards are placed (`_layout`) and animated (`_animate`); how the Gantt chart is drawn
from `Simulator.gantt_blocks()`; how the control bar enables only the settings a policy uses.

**Be ready to answer**
- How does a card move smoothly from one column to another?
- Why is the READY column in queue order, and why is this useful for Round Robin?
- What does the RUNNING column show when no process is running? (six different cases)

**Your own improvement (choose one)**
- Add a colour legend or a dark theme.
- Add zoom to the Gantt chart (change the width of one tick).
- Draw a small arrow or highlight on the card that has just changed state.

## Role 8: results, comparison, tests

**Understand**: how the Compare tab runs all policies (`Simulator(...).run_all()`); how the bar charts are drawn;
what every test checks.

**Be ready to answer**
- How do you know that the simulator is correct? (hand-made Gantt charts and rules that always hold)
- Which policy is the best? Why is the honest answer "it depends on the goal"?
- What does the test with 300 random workloads prove that the hand-made examples cannot?

**Your own improvement (choose one)**
- Export the comparison table to a CSV file.
- Ask every member for one hand-calculated example and add it as a test.
- Add a line to the Compare tab that explains the result in words.

## Working together

- One repository, one branch per member, small commits with clear messages.
- Before you push: `python3 -m unittest -v` must pass.
- Do not change another member's file without telling them.
- Suggested order: week 1 read and run; week 2 improvements; week 3 report, screenshots and demo practice.
- Check the deadline and the exact requirements with the professor.

## If the project must also show later topics

Some ideas that fit this program:

- **Threads**: run the simulation in a worker thread and show that the window stays responsive.
- **Synchronization**: add a shared resource with a lock; a process that cannot get the lock moves to WAITING.
- **Deadlock**: add two resources, let two processes take them in a different order, and detect the cycle.
- **Memory**: give every process a memory size and admit it only when memory is free.
