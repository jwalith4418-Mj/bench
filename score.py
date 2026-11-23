#!/usr/bin/env python3
"""score.py questions.jsonl answers.jsonl [--offline]
No model grades anything. Each question gets one outcome:
  OK              the check passes
  WRONG           an answer was given and the check fails (an empty answer counts as WRONG)
  GAP             the answer row says "abstain": true
  ORIGIN_CHANGED  cited_span only: the official page no longer has the bytes we froze; not counted either way
answers.jsonl rows: {"id": "...", "answer": "...", "abstain": false}
py_test answers run as local Python code with a 10 s limit. Run untrusted answers in a container or VM."""
import collections, hashlib, json, os, re, subprocess, sys, tempfile, unicodedata, urllib.request, urllib.error

def norm(s): return " ".join(unicodedata.normalize("NFC", s).split())
def exact(a, c):
    e = c["expected"]
    f = lambda s: norm(str(s)).casefold().removesuffix(".")
    return f(a) == f(e)
FENCE = re.compile(r"```(?:python|py)?[ \t]*\n(.*?)```", re.S)
def py_test(a, c):
    m = FENCE.search(a); code = m.group(1) if m else a
    nonce = hashlib.sha256(os.urandom(16)).hexdigest()
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "t.py")
        open(p, "w").write(code + "\n" + c["test"] + f"\nprint({nonce!r})\n")
        try: r = subprocess.run([sys.executable, "-I", p], cwd=d, capture_output=True, text=True, timeout=10)
        except subprocess.TimeoutExpired: return False
    return r.returncode == 0 and nonce in r.stdout
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
    if not any(s in a for s in c["allowed_sources"]): return False
    if not offline and "origin" in c and not origin_ok(c["origin"]): return "ORIGIN_CHANGED"
    return norm(c["span"]) in norm(a)
def score(q, row, offline):
    if row is None: return "MISSING"
    if row.get("abstain") is True: return "GAP"
    a = row.get("answer")
    if not isinstance(a, str) or not a.strip(): return "WRONG"
    c = q["check"]; t = c["type"]
    r = exact(a, c) if t == "exact" else py_test(a, c) if t == "py_test" else cited_span(a, c, offline)
    return r if r == "ORIGIN_CHANGED" else ("OK" if r else "WRONG")

def main():
    args = [x for x in sys.argv[1:] if not x.startswith("--")]; offline = "--offline" in sys.argv
    if len(args) != 2: sys.exit(__doc__)
    qs = [json.loads(l) for l in open(args[0]) if l.strip()]
    ans = {r["id"]: r for r in (json.loads(l) for l in open(args[1]) if l.strip())}
    per = collections.defaultdict(collections.Counter)
    for q in qs:
        o = score(q, ans.get(q["id"]), offline); per[q["domain"]][o] += 1
        print(q["id"], o)
    print()
    for d, c in sorted(per.items()):
        n = sum(c.values()); print(f"{d:16} OK {c['OK']}/{n}  WRONG {c['WRONG']}  GAP {c['GAP']}  ORIGIN_CHANGED {c['ORIGIN_CHANGED']}  MISSING {c['MISSING']}")
if __name__ == "__main__": main()
