---
name: charmmgui-quick-bilayer-api
description: Build lipid bilayer systems (membrane-only, or a protein from a CHARMM-GUI PDB Reader job) through the CHARMM-GUI REST API's Quick Bilayer module, then poll and download the GROMACS/NAMD/AMBER/OpenMM inputs. Use it whenever a task mentions the CHARMM-GUI API, Quick Bilayer, building or rebuilding membrane systems without the web interface, scripting many bilayer builds (lipid-composition scans, several boxes from one protein job), or checking the status of / downloading a CHARMM-GUI job by job ID, even if the user only says "build a POPE/POPG membrane" or "get the CHARMM-GUI files for job 123…".
---

# CHARMM-GUI Quick Bilayer API

The CHARMM-GUI REST API (https://www.charmm-gui.org/?doc=api) has four calls: login, Quick
Bilayer submission, job status and download. `scripts/cgui_qb.py` (Python 3 standard library
only) wraps all four and adds the checks the server does not make. Parameters and replies are
in `references/api.md`; the test jobs behind every statement here are in
`references/test-record.md`.

## Before submitting

1. **Credentials.** The user supplies the CHARMM-GUI email and password. Pass them as
   `CGUI_EMAIL`/`CGUI_PASSWORD` in the environment of the command only; never write them into
   a file in a repository, a report or a shared document. The helper caches the 12 h token in
   `~/.charmmgui_token` (mode 600).
2. **Protein or not.** There is no PDB Reader endpoint. A protein system needs the job ID of a
   PDB Reader (or full Membrane Builder) job made in the web interface; always add `--clone`
   so the build runs in a copy and the source job stays reusable. A membrane-only system needs
   no job ID.
3. **Orientation.** Use `--ppm` unless the input is already placed in the membrane frame.
   With it, the API build of an AF3 trimer matched the web PPM build to 0.2 Å in depth and
   1° in tilt (`ppm.out` reports ΔG transfer, hydrophobic thickness and tilt). Without it
   the protein keeps its PDB Reader coordinates, with the bilayer at about z = 0 of that frame,
   normal along z; the same trimer came out 9 Å too high and tilted 34°, and any web Orient
   step is not reused. Check the placement in the result either way.
4. **Protocol clash.** API builds always use hydrogen mass repartitioning, a 4 fs step and
   303.15 K in every engine's inputs; `hmr=false` and `temp=` are silently ignored. If the
   project's protocol differs (e.g. 2 fs without HMR, 310.15 K), say so before submitting and
   plan how the inputs will be adapted, or use a web build instead.
5. **Box size.** `--margin` (Å) is required. With a protein it is the protein-to-edge distance
   in x/y; membrane-only with `--upper/--lower` it is half the box length (20 → 40 Å box);
   presets size the box from their lipid areas (PMm, 20 → 38.9 Å).

## Run

```bash
H=<skill dir>/scripts/cgui_qb.py
# membrane-only, custom composition
python3 $H submit --membrane-only --upper POPE:POPG=3:1 --lower POPE:POPG=3:1 \
    --margin 40 --ion-type KCl --ffconverter --wait --out memb.tgz
# protein from an existing PDB Reader job, in a clone, oriented by PPM
python3 $H submit --jobid 1234567890 --clone --upper POPE:POPG=3:1 --lower POPE:POPG=3:1 \
    --margin 22 --ion-type KCl --ppm --ffconverter --wait --out prot_memb.tgz
# preset membrane (PMm, PMf, ERm, MOM, G-IM, ...; full list in references/api.md)
python3 $H submit --membrane-only --membtype PMm --margin 30 --ffconverter --wait --out pmm.tgz
python3 $H status 1234567890 [--wait]
python3 $H download 1234567890 out.tgz
```

`--ffconverter` is needed for any engine other than CHARMM. Builds take 3–4 min for a ~40 Å
membrane and 15–20 min for 80–100 Å systems; with `--wait` run the command in the
background (or under `nohup`) rather than holding a foreground shell. Archives are 30–110 MB;
unpack each into a new empty directory.

## Check the result before using it

- `input.config.dat`: box `dimensions`, `hmr`, engines written.
- `step3_size.str`: `A`, `C`, lipids per leaflet (`NLIPTOP`/`NLIPBOT`); ratios are rounded per
  leaflet (3:1 gave 20:7 in a 40 Å box), and with a protein the leaflets differ in count.
- `gromacs/topol.top` `[ molecules ]`: lipid, ion (`POT`/`SOD`/`CLA`) and water counts.
- `gromacs/step7_production.mdp` (`dt`, `ref_t`) and the other engines' inputs against the
  project protocol.
- With a protein: its depth and orientation in the bilayer (e.g. CA centre and terminal z
  relative to the mean phosphorus plane in `gromacs/step5_input.pdb`).

## Failure modes the helper handles (and raw curl does not)

- The server validates nothing: a request without `margin` or lipids is "submitted". Without
  lipids the job ends in `error occurred from quick_bilayer`; without `margin` it reports
  `done` after step 4 with no archive. A job is complete only when `status` is `done` and
  `lastInpStep` is at least 6 (6 or 7 seen).
- `check_status` replies contain raw control characters in `lastOutLine`: `jq` and strict
  JSON parsers fail; parse with `json.loads(text, strict=False)`.
- Web-interface jobs and unknown job IDs both report `status: null`; `lastOutTime` is US
  Eastern time.
- `download` on a job without an archive answers "Start compressing now, please download
  after 1-2 minutes" (also for unknown IDs); the helper retries.
- Transient HTTP 408 on submit (request never read: one retry is safe) and dropped
  connections while polling; the helper retries both. A connection dropped *during* a
  submission is not retried: the job may already exist and the API cannot list jobs, so
  check the web interface (or accept a possible duplicate for cheap builds) before resubmitting.
- The official toolkit's job list (`check_status` without a job ID) returns a PHP notice,
  not a list: keep the returned job IDs yourself.

The official Bash/Python toolkit is https://github.com/junepark6/cgui_api.
