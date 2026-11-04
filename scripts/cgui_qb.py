#!/usr/bin/env python3
"""CHARMM-GUI Quick Bilayer via the REST API: login, submit, poll, download (stdlib only).

The server accepts incomplete requests and fails later, so this script checks them first.
The token is kept in ~/.charmmgui_token (mode 600; override with CGUI_TOKEN_FILE).

  export CGUI_EMAIL=you@example.org CGUI_PASSWORD='...'   # used only when the saved token is missing or expired
  cgui_qb.py submit --membrane-only --upper POPE:POPG=3:1 --lower POPE:POPG=3:1 --margin 20 \
                    --ion-type KCl --ffconverter --wait --out mem.tgz
  cgui_qb.py submit --jobid 1234567890 --clone --upper POPE:POPG=3:1 --lower POPE:POPG=3:1 --margin 22 \
                    --ion-type KCl --ppm --ffconverter --wait --out prot.tgz
  cgui_qb.py status 1234567890
  cgui_qb.py download 1234567890 out.tgz
"""
import argparse, base64, json, os, sys, time, urllib.parse, urllib.request

API = "https://charmm-gui.org/api"
TOKEN_FILE = os.path.expanduser(os.environ.get("CGUI_TOKEN_FILE", "~/.charmmgui_token"))
PRESETS = "PMm PMf PMp ERm ERf GOLm GOLf ENDm LYSm VAC MOM MIM THYp THYb aPM G-OM G-IM G+PM".split()


def call(path, token=None, query=None, form=None, json_body=None, raw=False, retry=True):
    url = f"{API}/{path}" + ("?" + urllib.parse.urlencode(query) if query else "")
    headers, data = {}, None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if json_body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(json_body).encode()
    elif form is not None:
        data = urllib.parse.urlencode(form).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        r = urllib.request.urlopen(req, timeout=120)
        body = r.read()
    except urllib.error.HTTPError as e:
        if e.code == 408 and retry:  # Apache timed out reading the request: nothing was submitted
            time.sleep(10)
            return call(path, token, query, form, json_body, raw, retry=False)
        sys.exit(f"HTTP {e.code} from {path}: {e.read().decode(errors='replace')[:300]}")
    except OSError as e:  # dropped connection, proxy or TLS hiccup
        if path == "quick_bilayer":  # the job may exist already: never resubmit blindly
            sys.exit(f"connection lost during submission ({e!r}); a job may or may not have been "
                     "created, and the API cannot list jobs: check the web interface before resubmitting")
        if not retry:
            raise
        time.sleep(10)
        return call(path, token, query, form, json_body, raw, retry=False)
    if raw:
        return r.headers.get("Content-Type", ""), body
    try:
        # check_status embeds raw control characters (log lines), so parse leniently
        return json.loads(body.decode(errors="replace"), strict=False)
    except ValueError:
        sys.exit(f"non-JSON reply from {path}: {body[:300]!r}")


def token_expiry(tok):
    p = tok.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))["exp"]


def get_token():
    if os.path.exists(TOKEN_FILE):
        tok = open(TOKEN_FILE).read().strip()
        if tok.count(".") == 2 and token_expiry(tok) > time.time() + 300:
            return tok
    email, pw = os.environ.get("CGUI_EMAIL"), os.environ.get("CGUI_PASSWORD")
    if not (email and pw):
        sys.exit(f"no valid token in {TOKEN_FILE}; set CGUI_EMAIL and CGUI_PASSWORD")
    d = call("login", json_body={"email": email, "password": pw})
    if not d.get("token"):
        sys.exit(f"login failed: {d}")
    fd = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.write(fd, d["token"].encode())
    os.close(fd)
    return d["token"]


def status(tok, jobid):
    d = call("check_status", tok, {"jobid": jobid})
    if "error" in d:
        sys.exit(f"{d['error']}: {d.get('detail')}")
    return d


def wait(tok, jobid, every=30):
    while True:
        try:
            d = status(tok, jobid)
        except OSError as e:  # dropped connection or proxy hiccup: try again next round
            print(f"{time.strftime('%H:%M:%S')} {jobid} poll failed ({e}); retrying", flush=True)
            time.sleep(every)
            continue
        s = d.get("status") or ""
        print(f"{time.strftime('%H:%M:%S')} {jobid} {s or 'null'} {d.get('lastOutFile')}", flush=True)
        if s == "done" and int(d.get("lastInpStep") or 0) < 6:  # e.g. no margin: stops at step 4, still "done"
            sys.exit(f"job {jobid} ended without an archive (last step {d.get('lastInpStep')}, "
                     f"{d.get('lastOutFile')})")
        if s == "done" or s.startswith("error"):
            return d
        if not s and d.get("hasTarFile"):  # jobs built in the web interface report status null
            return d
        if not s and d.get("lastOutFile") is None:
            sys.exit(f"job {jobid} unknown to the server (or not yet started)")
        time.sleep(every)


def download(tok, jobid, out, tries=5):
    for _ in range(tries):
        ctype, body = call("download", tok, {"jobid": jobid}, raw=True)
        # a job without an archive is compressed on request: "Start compressing now, ..."
        if body.startswith(b"\x1f\x8b") or b"compressing" not in body:
            break
        print(f"{jobid}: server is compressing the job folder; retrying in 90 s", flush=True)
        time.sleep(90)
    if not body.startswith(b"\x1f\x8b"):
        sys.exit(f"no archive for {jobid}: {body[:300].decode(errors='replace')}")
    open(out, "wb").write(body)
    print(f"{out}: {len(body) / 1e6:.1f} MB")


def submit(tok, a):
    if not (a.membrane_only or a.jobid):
        sys.exit("give --jobid (a PDB Reader job) or --membrane-only")
    if a.clone and not a.jobid:
        sys.exit("--clone needs --jobid")
    if a.membtype and (a.upper or a.lower):
        sys.exit("give --membtype or --upper/--lower, not both")
    if not a.membtype and not (a.upper and a.lower):
        sys.exit("give --membtype, or both --upper and --lower")
    if a.membtype and a.membtype not in PRESETS:
        sys.exit(f"unknown --membtype; one of {' '.join(PRESETS)}")
    q = {"margin": a.margin, "wdist": a.wdist, "ion_conc": a.ion_conc, "ion_type": a.ion_type}
    q.update({"membrane_only": "true"} if a.membrane_only else {"jobid": a.jobid})
    for flag, key in [(a.clone, "clone_job"), (a.ffconverter, "run_ffconverter"), (a.ppm, "ppm"),
                      (a.proj_upper, "prot_projection_upper"), (a.proj_lower, "prot_projection_lower")]:
        if flag:
            q[key] = "true"
    form = {"membtype": a.membtype} if a.membtype else {"upper": a.upper, "lower": a.lower}
    d = call("quick_bilayer", tok, q, form)
    if not isinstance(d, dict) or not d.get("submitted"):
        sys.exit(f"not submitted: {d}")
    print(json.dumps(d, indent=1))
    return d["jobid"]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("submit")
    s.add_argument("--jobid")
    s.add_argument("--membrane-only", action="store_true")
    s.add_argument("--clone", action="store_true", help="work in a copy of the PDB Reader job")
    s.add_argument("--upper")
    s.add_argument("--lower")
    s.add_argument("--membtype")
    s.add_argument("--margin", type=float, required=True)
    s.add_argument("--wdist", type=float, default=22.5)
    s.add_argument("--ion-conc", type=float, default=0.15)
    s.add_argument("--ion-type", default="NaCl")
    s.add_argument("--ffconverter", action="store_true", help="also write GROMACS/AMBER/... inputs")
    s.add_argument("--ppm", action="store_true", help="orient the protein with PPM")
    s.add_argument("--proj-upper", action="store_true")
    s.add_argument("--proj-lower", action="store_true")
    s.add_argument("--wait", action="store_true")
    s.add_argument("--out", help="with --wait: download the archive here")
    st = sub.add_parser("status")
    st.add_argument("jobid")
    st.add_argument("--wait", action="store_true")
    dl = sub.add_parser("download")
    dl.add_argument("jobid")
    dl.add_argument("out", nargs="?")
    a = p.parse_args()

    tok = get_token()
    if a.cmd == "submit":
        jobid = submit(tok, a)
        if a.wait:
            d = wait(tok, jobid)
            if d["status"] == "done" and a.out:
                download(tok, jobid, a.out)
    elif a.cmd == "status":
        d = wait(tok, a.jobid) if a.wait else status(tok, a.jobid)
        log = d.pop("lastOutLine", None) or ""
        print(json.dumps(d, indent=1))
        print("\n".join(log.rstrip().splitlines()[-10:]))
    else:
        download(tok, a.jobid, a.out or f"charmm-gui-{a.jobid}.tgz")


if __name__ == "__main__":
    main()
