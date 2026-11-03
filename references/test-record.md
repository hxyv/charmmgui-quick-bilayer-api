# Test record (3 November 2026)

All jobs on one user account; times are wall-clock from submission to `done`.

| Job ID | Request | Result |
|---|---|---|
| 9371726959 | membrane-only, POPE:POPG=3:1 both leaflets, margin 20, KCl, FF-Converter | done in 3 min; 40.1 × 40.1 × 85 Å; 40 POPE, 14 POPG, 18 POT, 4 CLA, 2118 TIP3 |
| 9371803460 | as above, margin 40, plus `hmr=false`, `temp=310.15` | ~20 min; 80.2 × 80.2 × 85 Å; 162 POPE, 54 POPG, 75 POT, 21 CLA; HMR on, dt 0.004, 303.15 K regardless |
| 9371803679 | protein trimer (195 residues), `clone_job` of web Membrane Builder job 9368970333, margin 22, KCl, no PPM | ~20 min; 100.6 × 100.6 × 99.3 Å; 234 POPE, 78 POPG (151/161 per leaflet); protein kept at its PDB Reader z, ~9 Å higher in the bilayer than in the web build (whose Orient step had translated it −8.5 Å); source job unchanged |
| 9371806425 | membrane-only, no `margin` | `done` after step 4, `hasTarFile: false` |
| 9371806626 | membrane-only, no lipids | `error occurred from quick_bilayer`: "NO lipids INPUT for upper and lower leaflets!" |
| 9371967658 | membrane-only, `membtype=PMm`, margin 20, KCl, via `cgui_qb.py` | ~3.5 min; 38.9 × 38.9 × 107.3 Å; asymmetric, 29/26 lipids per leaflet, 10 species |

Other observations: one submission returned HTTP 408 and succeeded on repeat; one status
poll failed with an SSL EOF; `download` of an unknown job ID answered "Start compressing
now, please download after 1-2 minutes"; `check_status?check_rq=true` (job list) returned
the PHP notice "NO JOBID!!".

4 November 2026: one membrane-only submission through the installed skill lost its
connection (`RemoteDisconnected`, no reply); the repeat (job 9372693741) went through.
