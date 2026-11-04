#!/usr/bin/env python3
"""Make a protocol-matched copy of a CHARMM-GUI gromacs/ folder (stdlib only).

API builds always come with hydrogen mass repartitioning (HMR), a 4 fs production step and
303.15 K. This writes a new folder with any of:
  --temp K     every ref_t / ref-t value and gen_temp / gen-temp set to K
  --no-hmr     standard masses: each atom gets its atom-type mass from toppar/forcefield.itp
               (HMR only moves mass between atoms, so each molecule's total must not change;
               the script stops if one does)
  --dt PS      any .mdp whose dt is larger is set to PS, and its step counts and output
               intervals are scaled so that simulated times stay the same
The source folder is never modified; DEST must not exist. Run grompp on the result with the
GROMACS version that will run it.

usage: adapt_gromacs.py SRC_GROMACS_DIR DEST_DIR [--temp 310.15] [--no-hmr] [--dt 0.002]
"""
import argparse, re, shutil, sys
from pathlib import Path

STEP_KEYS = ("nsteps", "nstxout-compressed", "nstxout_compressed", "nstxout", "nstvout", "nstfout",
             "nstenergy", "nstlog")


def mdp_value(text, key):
    m = re.search(rf"^\s*{key}\s*=\s*([^;\n]*)", text, re.M | re.I)
    return m.group(1).strip() if m else None


def mdp_set(text, key, value):
    return re.sub(rf"^(\s*{key}\s*=\s*)([^;\n]*?)(\s*(;.*)?)$", lambda m: m.group(1) + value + m.group(3),
                  text, flags=re.M | re.I)


def adapt_mdp(path, temp, dt, log):
    text = path.read_text()
    if temp is not None:
        for key in ("ref_t", "ref-t"):
            old = mdp_value(text, key)
            if old:
                text = mdp_set(text, key, " ".join(f"{temp:g}" for _ in old.split()))
                log.append(f"{path.name}: {key} {old} -> {temp:g}")
        for key in ("gen_temp", "gen-temp"):
            old = mdp_value(text, key)
            if old:
                text = mdp_set(text, key, f"{temp:g}")
                log.append(f"{path.name}: {key} {old} -> {temp:g}")
    old_dt = mdp_value(text, "dt")
    if dt is not None and old_dt and float(old_dt) > dt + 1e-12:
        factor = float(old_dt) / dt
        if abs(factor - round(factor)) > 1e-6:
            sys.exit(f"{path.name}: dt {old_dt} -> {dt} is not an integer ratio; choose another dt")
        factor = round(factor)
        text = mdp_set(text, "dt", f"{dt:g}")
        log.append(f"{path.name}: dt {old_dt} -> {dt:g}")
        for key in STEP_KEYS:
            old = mdp_value(text, key)
            if old and old.lstrip("-").isdigit() and int(old) > 0:
                text = mdp_set(text, key, str(int(old) * factor))
                log.append(f"{path.name}: {key} {old} -> {int(old) * factor} (same simulated time)")
    path.write_text(text)


def atomtype_masses(ff):
    masses, sec = {}, None
    for line in ff.read_text().splitlines():
        s = line.split(";")[0].strip()
        if s.startswith("["):
            sec = s.strip("[] ").lower()
        elif sec == "atomtypes" and s:
            f = s.split()
            # name [bonded type] [at.num] mass charge ptype sigma eps: mass is the field before charge
            # and ptype ("A"); find it from the ptype position
            i = next(k for k, x in enumerate(f) if x in ("A", "D", "S", "V"))
            masses[f[0]] = (float(f[i - 2]), f[i - 3] if i >= 4 else f[0])
    return masses


def precise_masses(itps, masses):
    """[ atomtypes ] rounds some masses (O 15.999); take each element's 4-decimal mass from atoms
    that HMR left alone (mass within 0.01 of the type mass)."""
    best = {}
    for itp in itps:
        sec = None
        for line in itp.read_text().splitlines():
            s = line.split(";")[0].strip()
            if s.startswith("["):
                sec = s.strip("[] ").lower()
            elif sec == "atoms" and s and len(s.split()) >= 8:
                f = s.split()
                if f[1] in masses and abs(float(f[7]) - masses[f[1]][0]) < 0.01:
                    best.setdefault(masses[f[1]][1], float(f[7]))
    return best


def unhmr_itp(path, masses, precise, log):
    out, sec, mol, totals = [], None, None, {}
    for line in path.read_text().splitlines():
        s = line.split(";")[0].strip()
        if s.startswith("["):
            sec = s.strip("[] ").lower()
        elif sec == "moleculetype" and s:
            mol = s.split()[0]
            totals[mol] = [0.0, 0.0, 0, 0]
        elif sec == "atoms" and s:
            spans = [m.span() for m in re.finditer(r"\S+", line.split(";")[0])]
            f = s.split()
            if len(f) >= 8:
                if f[1] not in masses:
                    sys.exit(f"{path.name}: atom type {f[1]} not in forcefield.itp [ atomtypes ]")
                old, (new, elem) = float(f[7]), masses[f[1]]
                if abs(old - new) < 0.01:  # not repartitioned: keep the exact value
                    new = old
                elif elem in precise and abs(precise[elem] - new) < 0.01:
                    new = precise[elem]
                t = totals[mol]
                t[0] += old
                t[1] += new
                t[3] += 1
                if abs(old - new) > 1e-4:
                    a, b = spans[7]
                    line = line[:a] + f"{new:.4f}".rjust(b - a) + line[b:]
                    t[2] += 1
        out.append(line)
    path.write_text("\n".join(out) + "\n")
    for mol, (old, new, n, _) in totals.items():
        if abs(old - new) > 0.01:  # HMR only moves mass within a molecule
            sys.exit(f"{path.name} {mol}: total mass {old:.3f} -> {new:.3f}; this is not plain HMR, stopping")
        if n:
            log.append(f"{path.name} {mol}: {n} atom masses reset, total mass {old:.3f} -> {new:.3f}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("src")
    p.add_argument("dest")
    p.add_argument("--temp", type=float)
    p.add_argument("--no-hmr", action="store_true")
    p.add_argument("--dt", type=float)
    a = p.parse_args()
    src, dest = Path(a.src), Path(a.dest)
    if not (src / "topol.top").exists():
        sys.exit(f"{src} has no topol.top: give the gromacs/ folder of a CHARMM-GUI build")
    if dest.exists():
        sys.exit(f"{dest} exists; give a new folder")
    if a.temp is None and not a.no_hmr and a.dt is None:
        sys.exit("nothing to change: give --temp, --no-hmr and/or --dt")
    shutil.copytree(src, dest)
    log = []
    try:
        if a.no_hmr:
            masses = atomtype_masses(dest / "toppar" / "forcefield.itp")
            itps = [i for i in sorted((dest / "toppar").glob("*.itp")) if i.name != "forcefield.itp"]
            precise = precise_masses(itps, masses)
            for itp in itps:
                unhmr_itp(itp, masses, precise, log)
        for mdp in sorted(dest.glob("*.mdp")):
            adapt_mdp(mdp, a.temp, a.dt, log)
    except BaseException:
        shutil.rmtree(dest)  # leave no half-adapted copy behind
        raise
    if a.no_hmr and a.dt is None:
        for mdp in sorted(dest.glob("*.mdp")):
            d = mdp_value(mdp.read_text(), "dt")
            if d and float(d) > 0.002:
                log.append(f"WARNING {mdp.name}: dt {d} with standard masses; add --dt 0.002")
    (dest / "ADAPTED.txt").write_text(f"adapted from {src.resolve()}\n" + "\n".join(log) + "\n")
    print("\n".join(log))
    print(f"wrote {dest}; run grompp on it before use")


if __name__ == "__main__":
    main()
