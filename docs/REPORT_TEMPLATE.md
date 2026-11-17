# Technical report: outline

This is an outline, not the finished report. Text in *italics* tells you what to write.
The numbers in the tables come from this program; run the commands again after you change the code.

---

## 1. Title page

*Project title: Mini CPU Task Manager. Course, professor, group number, the eight names and student IDs, date.*

## 2. Introduction

*What is the project and why is it useful? Three or four sentences.* Example:

> Mini CPU Task Manager is an educational simulator of CPU scheduling. The user creates processes with an
> arrival time, a CPU burst and a priority, chooses a scheduling policy, and watches each process move
> between the states NEW, READY, RUNNING, WAITING and TERMINATED. The program does not only list the
> processes: it shows every decision of the scheduler, every context switch and the final scheduling metrics.

## 3. Background: the OS concepts

*One short paragraph for each concept, in your own words. Model sentences:*

- **Process**: A process is a program in execution.
- **Process states**: During its life a process moves between five states: new, ready, running, waiting and terminated. Our program adds a sixth, suspended, for a process the user has paused.
- **Process control block (PCB)**: The PCB is the data structure in which the operating system stores all
  information about one process, for example its state, program counter, priority and accounting information.
- **CPU burst**: A CPU burst is a period in which the process uses the CPU without waiting for I/O.
- **Arrival time**: The arrival time is the moment when the process enters the ready queue.
- **Priority**: A priority is a number that tells the scheduler how important a process is. In our program a
  lower number means a higher priority.
- **Context switch**: In a context switch the operating system saves the state of the running process in its PCB
  and loads the saved state of the next process. It is pure overhead, because no user process runs during the switch.
- **Scheduling metrics**: Turnaround time is the time from arrival to completion. Waiting time is the time spent
  in the ready queue. Response time is the time from arrival to the first time on the CPU.
  Throughput is the number of processes completed per time unit. CPU utilisation is the percentage of time
  the CPU is busy.

## 4. Design

*Explain the three layers and why they are separate. You can copy the project structure from the README.*

- `core/`: the simulator (PCB, clock, metrics). It has no interface code.
- `policies/`: one module per policy. Every policy has the same function `choose_next(ready, running, sim)`.
- `gui/`: the window. It only calls `Simulator.step()` and draws the result.

*Add the table "five phases of one tick" from the README and the process state diagram with our transitions.*

*Write down the rules we chose (README, "The rules we chose"), because other textbooks may use other conventions.*

## 5. Implementation

*One subsection per member (see TEAM_ROLES.md). For each part: what it does, the most important function,
one short piece of code with an explanation, and the member's own improvement.*

## 6. User interface

*Screenshots with one or two sentences each: the Simulation tab, a context switch with I/O, aging,
the Results tab, the Compare tab. Take your own screenshots on your computer; examples are in `docs/screenshots/`.*

## 7. Testing

*Explain the two kinds of tests and show the output of `python3 -m unittest -v`.*

Hand-calculated answers for the sample "Classic mix"
(P1: arrival 0, burst 7; P2: 2, 4; P3: 4, 1; P4: 5, 4):

| Policy | Gantt chart | Avg turnaround | Avg waiting | Avg response |
|---|---|---|---|---|
| FCFS | P1 0-7, P2 7-11, P3 11-12, P4 12-16 | 8.75 | 4.75 | 4.75 |
| SJF | P1 0-7, P3 7-8, P2 8-12, P4 12-16 | 8.00 | 4.00 | 4.00 |
| SRTF | P1 0-2, P2 2-4, P3 4-5, P2 5-7, P4 7-11, P1 11-16 | 7.00 | 3.00 | 0.50 |
| Round Robin, quantum 3 | P1, P2, P1, P3, P4, P2, P1, P4 | 11.00 | 7.00 | 2.75 |

*Draw these Gantt charts by hand in the report and show that the program gives the same numbers.*

## 8. Experiments and results

### 8.1 All policies on the same workload

`python3 cli.py --sample "Classic mix" --compare` (quantum 2):

| Policy | Avg turnaround | Avg waiting | Avg response | Context switches |
|---|---|---|---|---|
| FCFS | 8.75 | 4.75 | 4.75 | 3 |
| SJF | 8.00 | 4.00 | 4.00 | 3 |
| SRTF | 7.00 | 3.00 | 0.50 | 5 |
| Priority | 9.50 | 5.50 | 5.50 | 3 |
| Priority (preemptive) | 9.00 | 5.00 | 3.00 | 4 |
| Round Robin | 9.00 | 5.00 | 1.50 | 8 |

*What do you see? For example: SRTF has the lowest waiting time; Round Robin has a low response time
but the most context switches.*

### 8.2 Convoy effect

`python3 cli.py --sample "Convoy effect" --compare`: one long process (burst 12) and three short ones, all arriving at time 0.

| Policy | Avg turnaround | Avg waiting |
|---|---|---|
| FCFS | 14.75 | 10.50 |
| SJF | 6.50 | 2.25 |
| Round Robin (quantum 2) | 8.50 | 4.25 |

### 8.3 The time quantum of Round Robin

Classic mix, `python3 cli.py --policy "Round Robin" --quantum N`:

| Quantum | Avg turnaround | Avg waiting | Avg response | Context switches |
|---|---|---|---|---|
| 1 | 9.50 | 5.50 | 0.75 | 14 |
| 2 | 9.00 | 5.00 | 1.50 | 8 |
| 3 | 11.00 | 7.00 | 2.75 | 7 |
| 4 | 8.50 | 4.50 | 3.25 | 4 |
| 8 | 8.75 | 4.75 | 4.75 | 3 |

*Explain: a small quantum gives a good response time but many context switches. With quantum 8 the result is
the same as FCFS, because no process is ever interrupted.*

### 8.4 The cost of a context switch

Classic mix, Round Robin, quantum 2, `--cs N`:

| Switch cost | Total time | Avg waiting | CPU utilisation |
|---|---|---|---|
| 0 | 16 | 5.00 | 100% |
| 1 | 24 | 11.25 | 67% |
| 2 | 32 | 17.00 | 50% |

### 8.5 Starvation and aging

Sample "Starvation and aging", policy Priority. P1 has the worst priority (5).

| Aging | P1 starts at | P1 waiting time | Avg waiting (all processes) |
|---|---|---|---|
| off | 17 | 17 | 3.14 |
| on | 12 | 12 | 3.86 |

*Explain the trade-off: aging helps the starving process, but the others wait a little longer.*

## 9. Discussion

*Which policy is good for which goal (batch system, interactive system, real-time)? What surprised you?
What did you learn about the operating system from building this?*

## 10. Limitations and future work

*One CPU; one I/O operation per process; no memory management; burst times are known in advance,
which a real OS cannot know. Ideas: multi-core, multilevel feedback queue, memory, synchronization.*

## 11. Contributions

| Member | Files | Own improvement | Report section |
|---|---|---|---|
| *name* | | | |

## 12. Use of AI tools

*Say honestly which tools the group used and for what, and how you checked the result (reading, tests, hand calculations).
Follow the rule in the syllabus.*

## 13. References

*Silberschatz, Galvin, Gagne: Operating System Concepts, chapter 3 (Processes) and chapter 5 (CPU Scheduling).
The lecture slides of weeks 3 to 5.*
