# CHARMM-GUI API reference (as tested, November 2026)

Base URL `https://charmm-gui.org/api` (`www.charmm-gui.org` also works). Every call except
login sends `Authorization: Bearer <token>`.

## Endpoints

| Endpoint | Input | Returns |
|---|---|---|
| `POST /login` | JSON `{"email", "password"}` | `{"token": "…"}`, a JWT valid 12 h (`exp` claim) |
| `POST /quick_bilayer` | query string and/or form fields (below) | `jobid`, `modules` (`membuilder ffconverter`), `submitted`, echoed `request` (adds `input_jobid` with `clone_job`), `use_redis`, `redis_key` |
| `GET /check_status?jobid=…` | job ID | `status`, `rank`, `rqinfo`, `pidfile`, `hasTarFile`, `lastOutFile`, `lastOutLine` (last 30 log lines, raw control characters), `lastOutTime` (US Eastern), `lastInpStep`; on failure also `error`, `detail` |
| `GET /download?jobid=…` | job ID | `charmm-gui.tgz` (`application/octet-stream`, folder `charmm-gui-<jobid>/`), or a text message |

Errors: no token → HTTP 401 `{"error":"No token provided"}`; malformed token →
`{"error":"Invalid token","detail":"Wrong number of segments"}`; expired token →
`{"error":"Invalid token","detail":"Expired token"}` (from the official toolkit). A
Quick Bilayer request with neither `jobid` nor `membrane_only` returns an HTML redirect form.

`status` values seen: `running quick_bilayer`, `running ffconverter`, `compressing`, `done`,
`error occurred from quick_bilayer`; `null` for web-interface jobs and unknown IDs.

## Quick Bilayer parameters

| Parameter | Default | Notes |
|---|---|---|
| `jobid` | – | PDB Reader (or Membrane Builder) job; required unless `membrane_only=true` |
| `membrane_only` | false | no protein |
| `clone_job` | false | build in a copy; the source job is not modified |
| `upper`, `lower` | – | e.g. `POPE:POPG=3:1`, `DOPC:POPC:CHL1=1:1:2` (CHARMM lipid names) |
| `membtype` | – | instead of upper/lower: PMm PMf PMp ERm ERf GOLm GOLf ENDm LYSm VAC MOM MIM THYp THYb aPM G-OM G-IM G+PM; URL-encode it |
| `margin` | required | Å; protein-to-edge in x/y, or half the box length for membrane-only custom compositions |
| `wdist` | 22.5 | Å of water on each side |
| `ion_conc`, `ion_type` | 0.15, NaCl | the docs write `Ion_conc`/`Ion_type`; lower case works (`KCl` gave POT/CLA) |
| `ppm` | false | orient the protein with PPM |
| `run_ffconverter` | false | write NAMD, GROMACS, AMBER, OpenMM, GENESIS, Desmond, LAMMPS, Tinker inputs |
| `prot_projection_upper`, `prot_projection_lower` | false | protein cross-section projection per leaflet |
| `topologyIn`, `heteroatoms` | true, false | documented, untested |

Not settable (ignored when sent): `hmr` (always on), temperature (`temp`, always 303.15 K).
