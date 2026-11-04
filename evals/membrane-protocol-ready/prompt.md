---
tags: [skill-creator]
max_turns: 80
timeout_seconds: 5400
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash, WebFetch]
---

Build a POPE:POPG 3:1 membrane-only box, about 60 Å across, 150 mM KCl, through the CHARMM-GUI API. Our MD protocol is a 2 fs step without hydrogen mass repartitioning at 310.15 K, run with GROMACS 2023.2. Give me a GROMACS folder that follows that protocol and is ready to minimise, and show that it passes grompp and that energy minimisation converges. GROMACS 2023.2 is on our workstation: `ssh workstation-tb`, binary /mnt/sda/software/gromacs-2023.2-install/bin/gmx; its GPU is busy with another job, so run on CPU only (`-nb cpu -ntmpi 1 -ntomp 4`) in /mnt/sda/charmmgui-api-test/<your own new folder>.
