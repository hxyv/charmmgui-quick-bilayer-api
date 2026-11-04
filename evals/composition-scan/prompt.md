---
tags: [skill-creator]
max_turns: 80
timeout_seconds: 5400
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash, WebFetch]
---

From our trimer's PDB Reader job 9377181149, build three membrane systems through the CHARMM-GUI API for a lipid-composition comparison: POPE:POPG 3:1, pure POPC, and POPC:cholesterol 7:3, the same in both leaflets, 0.15 M KCl, GROMACS files, and the same lateral padding around the protein in all three. The PDB Reader job has to stay reusable. Give me a table comparing the three builds: box, lipids per leaflet, ions, and how the protein sits in each membrane.
