# Pauhu bench

A public question set for checking answers that cite their sources. No model grades the answers: every check is a fixed rule you can read in `score.py`. A pass means the answer met that rule; it is not a judgement of the whole answer.

## Domains (25 questions each)

| Domain | Check |
| --- | --- |
| code | The answer's Python runs against fixed tests |
| eu_law_sources | The answer names the EU act and quotes the exact passage in quotation marks |
| data_lookup | Exact match against the official EU publications data |
| research | The answer names the Commission communication and quotes the exact passage in quotation marks |

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
- `ERROR`: the runner got no answer (`"error": true`). A run with errors is incomplete; `run.sh` exits 1.
- `ORIGIN_CHANGED`: the official page no longer matches the copy the passage was taken from. This counts as neither OK nor WRONG.
- `ORIGIN_UNREACHABLE`: the official page could not be fetched (network or HTTP error). Rerun later, or use `--offline`.

`--offline` skips re-fetching the official pages.

## Limits

- The answer key is public: `questions.jsonl` holds every expected passage and test. Only the `question` text should reach the system under test, which is what `run.sh` sends.
- Code answers run in a separate process with memory, CPU, file-size and process limits, an empty environment, and no network where the host allows it. That is not a full sandbox. Run untrusted answers in a container or VM.
- Code runs in the same Python process as its tests, so an answer written to cheat the scorer can fake a pass. Publish your `answers.jsonl` with any score so others can rerun and read it.

`tests/adversarial.py` checks the known tricks the scorer does catch.

## Licence

The code and question set are under Apache-2.0 (see `LICENSE`). Quoted passages come from EUR-Lex documents of the European Union, reused under Commission Decision 2011/833/EU; the source of each passage is the CELEX number and URL in its question. The EU does not endorse this benchmark.
