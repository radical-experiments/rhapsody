# HPPSS SC26 demo

OpenFOAM `pitzDaily` optimization with radex and RHAPSODY on Perlmutter,
part 2 through an ORBIT service (2026-11-15).

| File | Content |
|---|---|
| `2026-11-15-hppss-sc26.md` | Demo plan and work items W1-W10 |
| `2026-11-15-hppss-sc26-perlmutter-runbook.md` | Build, run scripts and timings on Perlmutter |
| `hppss-sc26-howto.md` | HOWTO: run the demo from the shared deployment |
| `orbit/` | Part 2 through ORBIT: `run_orbit.py`, `driver-orbit.py`, `orbit_harness.py` |
| `part1/` | Part 1 under Dragon: `driver-video.py` (demo size, 4 x 4), `driver-asyncmatched.py`, `part1.sh` (batch script), `run-w1.sh` (W1 timing runs) |
| `deploy/` | Environment files: `env.sh` (the shared deployment), `my-env.sh` (personal TLS pair, token and psij dir, HOWTO section 2.2), `env-w1.sh` (the W1 build that `run-w1.sh` sources) |
| `videos/` | Recorded parts 1 and 2, contact sheets, loss plots, presenter notes |

## Origin

- The documents and `orbit/` moved here on 2026-11-06 from
  `radical-collaboration/amsc`, branch `feature/hppss-demo`, commit
  `2fcf32b` (`demos/`). Their earlier history is there.
- `driver-orbit.py` runs the optimization of `driver-staged.py` from
  [CrayLabs/rhapsody-plugins-openfoam](https://github.com/CrayLabs/rhapsody-plugins-openfoam)
  through ORBIT. Upstream files from that repo are not copied here; only
  our own scripts and edits are.
- `part1/` and `deploy/` were copied here on 2026-11-06 from Perlmutter,
  unchanged:

  | File | From |
  |---|---|
  | `part1/driver-video.py`, `part1/driver-asyncmatched.py` | `/pscratch/sd/m/merzky/hppss-d015/runs/pitzDaily-optimize/` |
  | `part1/run-w1.sh` | `$PSCRATCH/hppss/runs/run-w1.sh` |
  | `part1/part1.sh` | `/pscratch/sd/m/merzky/hppss-rehearsal/part1.sh`, the HOWTO's `part1.sh` |
  | `deploy/env.sh` | `/pscratch/sd/m/merzky/hppss-demo/env.sh` |
  | `deploy/my-env.sh` | `/pscratch/sd/m/merzky/hppss-rehearsal-2026-11-05/my-env.sh`, the HOWTO's `my-env.sh` for that rehearsal (`HPPSS_WORK` is its directory) |
  | `deploy/env-w1.sh` | `$PSCRATCH/hppss/env.sh` |

  The two drivers load `driver-staged.py` and `driver-async.py` from their
  own directory, so they run from a copy of the upstream
  `pitzDaily-optimize` example.
- Upstream files the drivers and scripts need are not copied. In the
  deployment they are identical to the upstream sources:

  | File | Repo, commit, path |
  |---|---|
  | `driver-staged.py`, `driver-async.py`, `pitzdaily_case.py`, `Allrun`, `Allclean` | `CrayLabs/rhapsody-plugins-openfoam` `306d3f4`, `examples/pitzDaily-optimize/` |
  | `radical-orbit-endpoint-wrapper.sh` | `radical-cybertools/radical.orbit` `a843434` (devel), `bin/` |
