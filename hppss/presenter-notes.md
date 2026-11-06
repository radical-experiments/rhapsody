# HPPSS SC26 demo video: presenter notes (first iteration, 2026-11-05)

Two silent videos, recorded on Perlmutter on 2026-11-05 and rendered
offline. You narrate live. The timestamps are video time (m:ss). Each
terminal pane shows the real wall-clock time of the recording in its top
right corner. Wherever time was cut, an orange badge says so, for example
">> 29 s cut (...)".

- `hppss-part1.mp4`: 2:55
- `hppss-part2.mp4`: 3:22

Both are 1920x1080 H.264, 25 fps. Contact sheets: `hppss-part1-contact.png`
and `hppss-part2-contact.png`, one frame every 8 s.

**Numbers to have at hand**

- **Batches:** 4 OpenFOAM `pitzDaily` cases per batch, 4 batches, so 16
  solver runs per optimization.
- **Time per case:** a converging case takes about 7 to 13 s, typically
  about 9 s. The right pane shows each case's time.
- **Unconverged case:** in batch 1, one case per run (`pD-0003`, `A-0003`,
  `B-0003`) does not converge. It runs to the 2000-iteration cap, which
  takes 40 to 55 s, so batch 1 is the long one (45 s in part 1, about 65 s
  in part 2). The later batches take about 10 s in part 1 and 16 to 20 s in
  part 2. Both videos cut the middle of that wait.
- **Endpoint start:** about 35 s from submission to registration, including
  about 12 s in the queue (cut). From job start to registration it took
  about 23 s.
- **Results:**
  - Part 1 and part 2 client A (target −1.9): best avgInlets −1.8892,
    loss 1.17e-4. The best loss per batch was 0.213, 0.0196, 0.0196,
    1.17e-4.
  - Part 2 client B (target −2.0): best avgInlets −2.0024, loss 5.9e-6. The
    best loss per batch was 0.131, 0.0016, 0.0016, 5.9e-6.
  - These are bit-identical to the rehearsal of 2026-11-01. The optimizer
    is seeded, so the runs are deterministic.
- **Isolation:** each client probes its own radex store for the other
  client's first case. Both answers are "no -> isolated".

---

## Part 1: OpenFOAM on RHAPSODY and Dragon, radex between C++ and Python

| Time | Scene | On screen |
|---|---|---|
| 0:00–0:05 | Title | "Part 1" card |
| 0:05–0:42 | 1 Plugin interface | Code views: the Python case definition, then `controlDict` and the driver loop |
| 0:42–1:02 | 2 Start the job | Left: `cat part1.sh`, `sbatch`, `squeue`. Right: the Slurm job goes PENDING, then RUNNING |
| 1:02–2:43 | 3 Batches, radex, optimizer | Left: the driver on the compute node. Right: the solvers, their iterations, the radex writes |
| 2:43–2:53 | 3 Loss plot | Best loss per batch, log scale; the grey dots are the 4 case losses per batch |
| 2:53–2:55 | End card | |

**0:08–0:26: code, `pitzdaily_case.py`.**

- **On screen:** the left panel is the case class, the right panel shows
  how the case is tagged and its results are read back.
- **Say:**
  - A case is a plain Python class from the RHAPSODY OpenFOAM plugin. It
    copies the `pitzDaily` template into its own run directory and has one
    stage, `simpleFoam`.
  - The radex store descriptor is passed to the solver. That is all the
    solver needs to reach the store.
  - The case writes its own identifier into the `radexWrite` entry of
    `controlDict` (lines 128–129).
  - After the solve, `gather_results` reads two scalars back from radex
    with typed handles: the final step and the avgInlets value. The loss is
    (avgInlets − target)². No files are parsed.

**0:26–0:42: code, `controlDict` and the driver loop.**

- **On screen:** the left panel is the `controlDict` of the case.
- **Say:**
  - `radexWrite` is a C++ OpenFOAM function object, loaded from
    `libradexWrite.so`.
  - It runs at the end of the solve (`onEnd`) and exports the scalar
    computed by the `avgInlets` function object, under the case's
    identifier.
  - The right panel is the whole optimization loop: the optimizer asks for
    4 parameter sets, RHAPSODY submits 4 solver tasks and waits, the driver
    gathers the results from radex and tells the optimizer.

**0:45–1:02: submit.**

- **On screen:** the batch script, one CPU node on the debug QOS. The real
  driver is `dragon driver-video-verbose.py`; `$RECORD` is only the
  terminal recorder for this video.
- **Say:** the job is submitted and goes from PENDING to RUNNING. The queue
  wait (about 9 s) is cut.

**1:05–2:43: the run.**

- **Left, the driver on `nid006648`:** Dragon and the RHAPSODY backend come
  up in about 3 s, and the radex store (a Dragon DDict) in about 5 s. Then
  each batch:
  - `optimizer.ask(4)` proposes 4 parameter sets for the k-epsilon model;
  - RHAPSODY submits the 4 `simpleFoam` tasks;
  - when they are done, Python reads each case's `final_step` and
    `avgInlets` from radex and computes its loss;
  - `optimizer.tell` updates the optimizer;
  - one `Iteration N:` line reports the best case so far. These lines are
    the unchanged output of the example driver.
- **Right, the node's view:**
  - all 4 solvers of a batch run at the same time;
  - the SIMPLE iteration counter climbs;
  - each solver connects to radex ("connected"), and at the end writes 2
    keys (`<case>_avgInlets_<step>_0` and `<case>_final_step`);
  - the last column is the solver's own run time.
- **About 1:55 (batch 1):**
  - `pD-0003` does not converge and runs to the 2000-iteration cap ("no
    conv."). Its result is still written, but the optimizer ignores it.
  - The batch waits about 45 s for it, and the middle is cut (18 s).
  - The other batches finish in about 10 s each.
- **Points to make:**
  - The best loss falls from 0.213 to 0.0196 and then to 1.2e-4.
  - The final best avgInlets is −1.8892, against a target of −1.9.
  - The C++ solver writes into radex and the Python optimizer reads from
    it, with no file I/O and no glue in between.

**2:43–2:53: the plot.** It is the same as the "best loss so far" lines,
on a log scale. Each batch has 4 grey dots, its case losses. The two
unconverged cases with large losses show at the top.

---

## Part 2: the same workflow as an ORBIT service

Layout:

- **Top left:** the "laptop" terminal running `run_orbit.py`. It hosts the
  ORBIT broker (embedded, on the login node) and controls the endpoint.
- **Bottom left:** what the two clients on the laptop report (client A in
  cyan, client B in magenta).
- **Right:** Perlmutter, showing the endpoint's Slurm job, the solver tasks
  of both clients, and the radex writes.

| Time | Scene | On screen |
|---|---|---|
| 0:00–0:05 | Title | "Part 2" card |
| 0:05–1:00 | 1 Start the endpoint through ORBIT | Typed `run_orbit.py` command, broker, psij submit, job PENDING then RUNNING, "endpoint registered after 35.0s" |
| 1:00–2:45 | 2+3 Two optimizations, one endpoint | Both clients start; 8 solvers at a time (4 per client); progress lines per batch |
| 2:45–3:10 | 4 Progress, best parameters, isolation, teardown | Isolation probes, RESULT lines with the best parameters, cancel through ORBIT, job gone, `RUN RESULT PASS` |
| 3:10–3:20 | 4 Loss plot | Best loss per batch, clients A and B |
| 3:20–3:22 | End card | |

**0:08–1:00: start the endpoint.**

- **On screen:** the login node stands in for a laptop with no HPC login.
  In the final demo the broker moves to `three.radical`.
- **Say:**
  - The command starts two clients, with targets −1.9 and −2.0.
  - At about 0:28 the broker comes up.
  - At about 0:30, `submit_tunneled` of the psij plugin submits the
    endpoint job, a 1-node CPU job on the debug QOS. The client calls ORBIT
    and never runs `sbatch` itself.
  - On the right the job is PENDING (about 12 s of queue, cut), then
    RUNNING on `nid006085`. Inside the job, Dragon and the RHAPSODY plugin
    start.
  - At about 0:57 the endpoint has registered with the broker, 35 s after
    submission.

**1:04–2:45: two clients, side by side.**

- **Bottom left:**
  - Both clients start on the laptop.
  - Each client creates its own radex store inside the endpoint (`radex_A`
    and `radex_B`) and reports "endpoint ready".
  - The clients run the same driver as part 1, with two differences: the
    solver tasks run on the endpoint, and after each batch a Python
    function task on the endpoint reads the 4 results from radex and
    returns only (final_step, avgInlets) per case. The bulk data never
    leaves Perlmutter; only the losses come back.
- **Right:**
  - 8 solvers run at the same time, 4 from A and 4 from B.
  - Each writes into its own client's store.
  - The keys carry the client prefix (A-…, B-…).
- **About 1:50:**
  - Batch 1 is slow again because one unconverged case per client runs to
    2000 iterations (a 29 s cut).
  - In the HOWTO, the 64 s first batch is put down to "Dragon warm-up".
    The recording shows that the unconverged case causes it.
- **Later batches:** about 16 to 20 s each.
- **Say, about the result:** client A ends exactly where part 1 ended
  (avgInlets −1.8892). Client B, with a different target, ends at −2.0024.

**2:48–3:10: results and teardown.**

- **Bottom left:**
  - `isolation probe: B-0000 in own store? no -> isolated`, and the same
    for B. Neither client can see the other's keys.
  - The RESULT lines give the best parameters (epsilon, Cmu, C1, C2) and
    the final avgInlets and loss of each client. This is the "query best
    parameters remotely" step. The clients receive these values from the
    endpoint; run_orbit.py has no separate query command.
- **Top left and right:**
  - `run_orbit.py` cancels the endpoint job through ORBIT (psij
    `cancel_job`).
  - The job leaves the queue after about 40 s, of which 35 s is cut. Then
    the broker stops and the terminal prints `TIMINGS` and
    `RUN RESULT PASS`.

**3:10–3:20: the plot.** Two curves, one per client. Each client converges
to its own target on the same endpoint.
