"""Run: python3 tests/adversarial.py  (from the repo root). Each case must give the expected outcome."""
import json, os, subprocess, sys, tempfile
Q = [{"id": "c1", "domain": "code", "question": "x", "check": {"type": "py_test", "test": "assert solve(2)==4\nassert False"}},
     {"id": "s1", "domain": "research", "question": "x", "check": {"type": "cited_span", "allowed_sources": ["52019DC0640"], "span": "The sky is blue."}}]
CASES = [
 ("c1", "def solve(x):\n\treturn x*2", "WRONG"),                                     # assert False must fail
 ("c1", "import sys,re\nprint(open(sys.argv[0]).read())\nraise SystemExit(0)", "WRONG"),  # exit before tests
 ("c1", "import os\nos._exit(0)", "WRONG"),                                          # hard exit before tests
 ("s1", "The sky is blue. 52019DC0640", "WRONG"),                                    # passage not quoted
 ("s1", "52019DC0640 says \"The sky is blue.\"", "OK"),
 ("s1", "\"The sky is blue.\"", "WRONG"),                                            # no source id
]
def main():
    d = tempfile.mkdtemp(); qf = os.path.join(d, "q.jsonl"); fails = 0
    open(qf, "w").write("".join(json.dumps(q) + "\n" for q in Q))
    for i, (qid, ans, want) in enumerate(CASES):
        af = os.path.join(d, f"a{i}.jsonl"); qq = os.path.join(d, f"q{i}.jsonl")
        open(qq, "w").write(json.dumps(next(q for q in Q if q["id"] == qid)) + "\n")
        open(af, "w").write(json.dumps({"id": qid, "answer": ans}) + "\n")
        out = subprocess.run([sys.executable, "score.py", qq, af, "--offline"], capture_output=True, text=True).stdout
        got = out.split("\n")[0].split()[-1]
        print("ok  " if got == want else "FAIL", i, want, got); fails += got != want
    sys.exit(1 if fails else 0)
main()
