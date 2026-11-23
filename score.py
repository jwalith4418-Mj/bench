#!/usr/bin/env python3
"""score.py questions.jsonl answers.jsonl [--offline]
No model grades anything. Each question gets one outcome:
  OK              the check passes; cited_span needs an allowed source id and the exact passage in quotation marks
  WRONG           an answer was given and the check fails (an empty answer counts as WRONG)
  GAP             the answer row says "abstain": true
  ERROR           the runner could not get an answer (row says "error": true); a run with errors is incomplete
  ORIGIN_CHANGED  cited_span only: the official page was fetched and no longer has the bytes we froze; not counted either way
  ORIGIN_UNREACHABLE  cited_span only: the official page could not be fetched (network or HTTP error); rerun later or use --offline
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
# The harness reads the success token from stdin before any answer code runs and prints it only after every test
# line has run. The token is never in a file or argv, but it sits in the harness's memory: code written to cheat can
# read it (see README, Limits).
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
    if _cache[u] is None: return "ORIGIN_UNREACHABLE"
    return _cache[u] == o["sha256"]
def cited_span(a, c, offline):
    # Needs one allowed source id and the exact passage inside quotation marks.
    if not any(s in a for s in c["allowed_sources"]): return False
    sp = norm(c["span"]); na = norm(a)
    if not any(f"{o}{sp}{e}" in na for o, e in (('"', '"'), ("\u201c", "\u201d"), ("\u00ab", "\u00bb"))): return False
    if not offline and "origin" in c:
        o = origin_ok(c["origin"])
        if o == "ORIGIN_UNREACHABLE": return o
        if not o: return "ORIGIN_CHANGED"
    return norm(c["span"]) in norm(a)
def score(q, row, offline):
    if row is None: return "MISSING"
    if row.get("error") is True: return "ERROR"
    if row.get("abstain") is True: return "GAP"
    a = row.get("answer")
    if not isinstance(a, str) or not a.strip(): return "WRONG"
    c = q["check"]; t = c["type"]
    r = exact(a, c) if t == "exact" else py_test(a, c) if t == "py_test" else cited_span(a, c, offline)
    return r if isinstance(r, str) else ("OK" if r else "WRONG")

def main():
    flags = [x for x in sys.argv[1:] if x.startswith("--")]; args = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(args) != 2 or set(flags) - {"--offline"}: sys.exit(__doc__)
    offline = "--offline" in flags
    qs = [json.loads(l) for l in open(args[0]) if l.strip()]
    ids = [q["id"] for q in qs]
    if len(ids) != len(set(ids)): sys.exit("duplicate question id")
    NEED = {"exact": {"expected"}, "py_test": {"test"}, "cited_span": {"allowed_sources", "span"}}
    for q in qs:
        c = q.get("check")
        if not isinstance(c, dict) or c.get("type") not in NEED: sys.exit(f"unknown check type: {q['id']}")
        if NEED[c["type"]] - c.keys(): sys.exit(f"check missing {sorted(NEED[c['type']] - c.keys())}: {q['id']}")
        if "origin" in c and not ({"url", "sha256"} <= c["origin"].keys()): sys.exit(f"origin needs url and sha256: {q['id']}")
    ans = {}
    for l in open(args[1]):
        if not l.strip(): continue
        r = json.loads(l)
        if r.get("id") not in set(ids): sys.exit(f"answer id not in questions: {r.get('id')}")
        if r["id"] in ans: sys.exit(f"duplicate answer id {r['id']}")
        ans[r["id"]] = r
    per = collections.defaultdict(collections.Counter)
    for q in qs:
        o = score(q, ans.get(q["id"]), offline); per[q["domain"]][o] += 1
        print(q["id"], o)
    print()
    for d, c in sorted(per.items()):
        n = sum(c.values()); print(f"{d:16} OK {c['OK']}/{n}  WRONG {c['WRONG']}  GAP {c['GAP']}  ERROR {c['ERROR']}  ORIGIN_CHANGED {c['ORIGIN_CHANGED']}  ORIGIN_UNREACHABLE {c['ORIGIN_UNREACHABLE']}  MISSING {c['MISSING']}")
if __name__ == "__main__": main()
