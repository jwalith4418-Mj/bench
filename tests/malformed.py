"""Run: python3 tests/malformed.py  (from the repo root). Each malformed input must be refused with exit 1 and no traceback."""
import shutil, subprocess, sys, tempfile
CASES = [
 ('{"id":"a","domain":"x","question":"q","check":{"type":"py_test","test":5}}', '{"id":"a","answer":"x"}'),
 ('{"id":"a","domain":"x","question":"q","check":{"type":"cited_span","allowed_sources":"C","span":"s"}}', '{"id":"a","answer":"x"}'),
 ('{"id":"a","domain":"x","question":"q","check":{"type":"cited_span","allowed_sources":["C"],"span":"s","origin":null}}', '{"id":"a","answer":"x"}'),
 ('{"id":"a","domain":"x","question":"q","check":{"type":"exact","expected":"1"}}', '[1,2]'),
 ('{"id":"a","domain":"x","question":"q","check":{"type":"exact","expected":"1"}}', '{"id":"a","answer":7}'),
 ('{"id":"a","domain":"x","question":"q","check":{"type":"exact","expected":"1"}}', '{"id":"zzz","answer":"1"}'),
 ('{"id":"a","domain":"x","question":"q","check":{"type":"nope"}}', '{"id":"a","answer":"1"}'),
 ('{"id":"a",', '{"id":"a","answer":"1"}'),
 ('{"id":"a","domain":"x","question":"q","check":{"type":"exact","expected":"1"}}', '{oops'),
]
d = tempfile.mkdtemp(); fails = 0
for i, (q, a) in enumerate(CASES):
    open(f"{d}/q", "w").write(q + "\n"); open(f"{d}/a", "w").write(a + "\n")
    r = subprocess.run([sys.executable, "score.py", f"{d}/q", f"{d}/a", "--offline"], capture_output=True, text=True)
    ok = r.returncode == 1 and "Traceback" not in r.stderr
    print("ok  " if ok else "FAIL", i, (r.stderr or r.stdout).strip()[:80]); fails += not ok
shutil.rmtree(d)
sys.exit(1 if fails else 0)
