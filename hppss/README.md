# HPPSS SC26 demo

OpenFOAM `pitzDaily` optimization with radex and RHAPSODY on Perlmutter,
part 2 through an ORBIT service (2026-11-15).

| File | Content |
|---|---|
| `2026-11-15-hppss-sc26.md` | Demo plan and work items W1-W10 |
| `2026-11-15-hppss-sc26-perlmutter-runbook.md` | Build, run scripts and timings on Perlmutter |
| `hppss-sc26-howto.md` | HOWTO: run the demo from the shared deployment |
| `orbit/` | Part 2 through ORBIT: `run_orbit.py`, `driver-orbit.py`, `orbit_harness.py` |
| `videos/` | Recorded parts 1 and 2, contact sheets, loss plots, presenter notes |

## Origin

- The documents and `orbit/` moved here on 2026-11-06 from
  `radical-collaboration/amsc`, branch `feature/hppss-demo`, commit
  `2fcf32b` (`demos/`). Their earlier history is there.
- `driver-orbit.py` runs the optimization of `driver-staged.py` from
  [CrayLabs/rhapsody-plugins-openfoam](https://github.com/CrayLabs/rhapsody-plugins-openfoam)
  through ORBIT. Upstream files from that repo are not copied here; only
  our own scripts and edits are.
