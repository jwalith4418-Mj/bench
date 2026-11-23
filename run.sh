#!/usr/bin/env bash
# run.sh [questions.jsonl] [answers.jsonl]: asks every question through the Pauhu CLI and writes answers.jsonl.
# Needs: Node 20+, `npm i -g github:pauhu/cli`, and your own developer key (`pauhu key set`, or PAUHU_KEY in CI).
# Then: python3 score.py questions.jsonl answers.jsonl
set -euo pipefail
Q=${1:-questions.jsonl}; OUT=${2:-answers.jsonl}
command -v pauhu >/dev/null || { echo "pauhu CLI not found: npm i -g github:pauhu/cli" >&2; exit 2; }
: > "$OUT"; fails=0
while IFS= read -r line; do
  [ -n "$line" ] || continue
  id=$(printf '%s' "$line" | python3 -c 'import json,sys;print(json.load(sys.stdin)["id"])')
  q=$(printf '%s' "$line" | python3 -c 'import json,sys;print(json.load(sys.stdin)["question"])')
  err=false; a=$(pauhu ask "$q" 2>/dev/null) || { a=""; err=true; fails=$((fails+1)); }
  python3 -c 'import json,sys;print(json.dumps({"id":sys.argv[1],"answer":sys.argv[2],"abstain":False,"error":sys.argv[3]=="true"},ensure_ascii=False))' "$id" "$a" "$err" >> "$OUT"
  echo "$id done" >&2
done < "$Q"
if [ "$fails" -gt 0 ]; then echo "$fails question(s) got no answer (marked error); the run is incomplete" >&2; exit 1; fi
