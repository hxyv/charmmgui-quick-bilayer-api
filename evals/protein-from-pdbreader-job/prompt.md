---
tags: [skill-creator]
max_turns: 80
timeout_seconds: 5400
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash, WebFetch]
---

I uploaded our AF3-predicted antimicrobial peptide trimer to CHARMM-GUI PDB Reader, job ID 9377181149. Please use the CHARMM-GUI API to put it into a POPE/POPG 3:1 bilayer with 0.15 M KCl and get GROMACS inputs. Keep the PDB Reader job reusable, we'll build other compositions from it later. Our lab protocol is 2 fs without hydrogen mass repartitioning at 310.15 K. Check that the protein sits sensibly in the membrane and tell me what I need to change before equilibration.
