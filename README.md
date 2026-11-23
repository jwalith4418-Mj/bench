# Pauhu bench

A public question set for checking answers that cite their sources. No model grades the answers: every check is a fixed rule you can read in `score.py`.

## Domains (25 questions each)

| Domain | Check |
| --- | --- |
| code | The answer's Python runs against fixed tests |
| eu_law_sources | The answer cites the named EU act and quotes the exact passage |
| data_lookup | Exact match against the official EU publications data |
| research | The answer cites the named Commission communication and quotes the exact passage |

## Run it

```sh
npm i -g github:pauhu/cli
pauhu key set            # your own developer key
./run.sh questions.jsonl answers.jsonl
python3 score.py questions.jsonl answers.jsonl
```

`score.py` works on any `answers.jsonl` with rows `{"id": "...", "answer": "...", "abstain": false}`, so you can score any system the same way.

## Outcomes

- `OK`: the check passes.
- `WRONG`: the check fails. An empty answer counts as wrong.
- `GAP`: the system said it does not know (`"abstain": true`).
- `ORIGIN_CHANGED`: the official page no longer matches the copy the passage was taken from. This counts as neither OK nor WRONG.

`--offline` skips re-fetching the official pages.

Code answers run as local Python with a 10-second limit. Run untrusted answers inside a container or VM.

## Licence

Apache-2.0. The quoted passages come from official EU publications, reused under the Commission's reuse policy (Decision 2011/833/EU).
