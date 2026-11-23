#!/usr/bin/env python3
"""score.py questions.jsonl answers.jsonl [--offline]
No model grades anything. Each question gets one outcome:
  OK              the check passes; cited_span needs an allowed source id and the exact passage in quotation marks
  WRONG           an answer was given and the check fails (an empty answer counts as WRONG)
  GAP             the answer row says "abstain": true
  ERROR           the runner could not get an answer (row says "error": true); a run with errors is incomplete
  ORIGIN_CHANGED  cited_span only: the official page no longer has the bytes we froze; not counted either way
answers.jsonl rows: {"id": "...", "answer": "...", "abstain": false}
py_test answers run in a separate process with memory, CPU, file-size and process limits, an empty
environment, and no network where the host allows it. That is not a full sandbox: run untrusted answers in a container or VM."""
import collections, hashlib, json, os, re, subprocess, sys, tempfile, unicodedata, urllib.request, urllib.error

def norm(s): return " ".join(unicodedata.normalize("NFC", s).split())
def exact(a, c):
    e = c["expected"]
    f = lambda s: norm(str(s)).casefold().removesuffix(".")
    return f(a) == f(e)
FENCE = re.compile(r"```(?:python|py)?[ \t]*\n(.*?)```", re.S)
# The harness reads the success token from stdin before any answer code runs, keeps only its hash in a closure,
# and prints the token only after every test line has run. The answer never sees the token in a file or argv.
HARNESS = r"""
import sys, hashlib
def _run(_tok=sys.stdin.readline().strip()):
    sys.stdin.close()
    _ans = open(sys.argv[1]).read(); _tst = open(sys.argv[2]).read()
    _g = {"__name__": "answer"}
    exec(compile(_ans, "answer.py", "exec"), _g)
    exec(compile(_tst, "test.py", "exec"), _g)
    return _tok
_t = _run()
sys.stdout.write("PASS " + _t + "\n")
"""
def _limits():
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1 << 20, 1 << 20))
    resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
def _netless():
    # Use an empty network namespace when the host allows it (Linux, unprivileged user namespaces).
    import shutil
    u = shutil.which("unshare")
    if u and subprocess.run([u, "-rn", "true"], capture_output=True).returncode == 0: return [u, "-rn"]
    return []
NET = None
def py_test(a, c):
    global NET
    if NET is None:
        NET = _netless()
        if not NET: print("warning: no network isolation available; run in a container", file=sys.stderr)
    m = FENCE.search(a); code = m.group(1) if m else a
    tok = hashlib.sha256(os.urandom(32)).hexdigest()
    with tempfile.TemporaryDirectory() as d:
        for n, t in (("h.py", HARNESS), ("answer.py", code), ("test.py", c["test"])):
            open(os.path.join(d, n), "w").write(t)
        try:
            r = subprocess.run(NET + [sys.executable, "-I", "h.py", "answer.py", "test.py"], cwd=d, input=tok + "\n",
                               capture_output=True, text=True, timeout=15, preexec_fn=_limits, env={})
        except subprocess.TimeoutExpired: return False
    return r.returncode == 0 and r.stdout.endswith("PASS " + tok + "\n")
_cache = {}
def origin_ok(o):
    u = o["url"]
    if u not in _cache:
        try:
            req = urllib.request.Request(u, headers={**o.get("headers", {}), "User-Agent": "pauhu-bench-scorer"})
            _cache[u] = hashlib.sha256(urllib.request.urlopen(req, timeout=60).read()).hexdigest()
        except Exception: _cache[u] = None
    return _cache[u] == o["sha256"]
def cited_span(a, c, offline):
    # Needs one allowed source id and the exact passage inside quotation marks.
    if not any(s in a for s in c["allowed_sources"]): return False
    sp = norm(c["span"]); na = norm(a)
    if not any(f"{o}{sp}{e}" in na for o, e in (('"', '"'), ("\u201c", "\u201d"), ("\u00ab", "\u00bb"))): return False
    if not offline and "origin" in c and not origin_ok(c["origin"]): return "ORIGIN_CHANGED"
    return norm(c["span"]) in norm(a)
def score(q, row, offline):
    if row is None: return "MISSING"
    if row.get("error") is True: return "ERROR"
    if row.get("abstain") is True: return "GAP"
    a = row.get("answer")
    if not isinstance(a, str) or not a.strip(): return "WRONG"
    c = q["check"]; t = c["type"]
    r = exact(a, c) if t == "exact" else py_test(a, c) if t == "py_test" else cited_span(a, c, offline)
    return r if r == "ORIGIN_CHANGED" else ("OK" if r else "WRONG")

def main():
    flags = [x for x in sys.argv[1:] if x.startswith("--")]; args = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(args) != 2 or set(flags) - {"--offline"}: sys.exit(__doc__)
    offline = "--offline" in flags
    qs = [json.loads(l) for l in open(args[0]) if l.strip()]
    ids = [q["id"] for q in qs]
    if len(ids) != len(set(ids)): sys.exit("duplicate question id")
    bad = [q["id"] for q in qs if q["check"]["type"] not in ("exact", "py_test", "cited_span")]
    if bad: sys.exit(f"unknown check type: {bad[0]}")
    ans = {}
    for l in open(args[1]):
        if not l.strip(): continue
        r = json.loads(l)
        if r["id"] in ans: sys.exit(f"duplicate answer id {r['id']}")
        ans[r["id"]] = r
    per = collections.defaultdict(collections.Counter)
    for q in qs:
        o = score(q, ans.get(q["id"]), offline); per[q["domain"]][o] += 1
        print(q["id"], o)
    print()
    for d, c in sorted(per.items()):
        n = sum(c.values()); print(f"{d:16} OK {c['OK']}/{n}  WRONG {c['WRONG']}  GAP {c['GAP']}  ERROR {c['ERROR']}  ORIGIN_CHANGED {c['ORIGIN_CHANGED']}  MISSING {c['MISSING']}")
if __name__ == "__main__": main()
