# charmmgui-quick-bilayer-api

An agent skill (Claude Code / `~/.agents/skills` layout) for building lipid bilayer systems
through the CHARMM-GUI REST API's Quick Bilayer module, plus a standalone command-line helper.

- `SKILL.md`: when to use it, the workflow, and the pitfalls found in testing
- `scripts/cgui_qb.py`: login, submit (with client-side checks), poll, download; Python 3
  standard library only
- `references/api.md`: endpoints and parameters as observed
- `references/test-record.md`: the test jobs behind the documented behaviour

## Install

```bash
git clone <this repo> ~/.agents/skills/charmmgui-quick-bilayer-api
ln -s ../../.agents/skills/charmmgui-quick-bilayer-api ~/.claude/skills/charmmgui-quick-bilayer-api
```

## Helper quick start

```bash
export CGUI_EMAIL=you@example.org CGUI_PASSWORD='...'
python3 scripts/cgui_qb.py submit --membrane-only --upper POPE:POPG=3:1 --lower POPE:POPG=3:1 \
    --margin 40 --ion-type KCl --ffconverter --wait --out memb.tgz
```

The token is cached in `~/.charmmgui_token` (mode 600). Keep credentials out of this
repository. CHARMM-GUI's own toolkit is at https://github.com/junepark6/cgui_api.
