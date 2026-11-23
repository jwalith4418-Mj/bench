#!/usr/bin/env node
// node run.mjs [questions.jsonl] [answers.jsonl]: asks every question through the Pauhu CLI and writes answers.jsonl.
// Works on Windows, macOS and Linux. Needs Node 20+, `npm i -g github:pauhu/cli` and your own developer key.
// Then: python3 score.py questions.jsonl answers.jsonl
import { readFileSync, writeFileSync, appendFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';

const [q = 'questions.jsonl', out = 'answers.jsonl'] = process.argv.slice(2);
// Run the npm package's own script with this node, so another `pauhu` earlier on PATH
// (for example an old pip package) is never picked up, and no shell quoting is involved.
function cliScript() {
  if (process.env.PAUHU_CLI_JS) return process.env.PAUHU_CLI_JS;
  const npm = process.platform === 'win32' ? 'npm.cmd' : 'npm';
  const r = spawnSync(npm, ['root', '-g'], { encoding: 'utf8', shell: process.platform === 'win32' });
  const p = join((r.stdout || '').trim(), 'pauhu', 'pauhu.mjs');
  if (r.status !== 0 || !existsSync(p)) { console.error('pauhu CLI not found: npm i -g github:pauhu/cli'); process.exit(2); }
  return p;
}
const script = cliScript();
writeFileSync(out, '');
let fails = 0;
for (const line of readFileSync(q, 'utf8').split('\n')) {
  if (!line.trim()) continue;
  const { id, question } = JSON.parse(line);
  const r = spawnSync(process.execPath, [script, 'ask', question], { encoding: 'utf8', maxBuffer: 16 << 20 });
  const error = r.status !== 0 || !!r.error;
  const row = { id, answer: error ? '' : (r.stdout || '').trimEnd(), abstain: false, error };
  if (error) {
    fails++;
    row.reason = (r.error?.message || r.stderr || '').split('\n').find(Boolean) || `exit ${r.status}`;
    console.error(`${id} error: ${row.reason}`);
  } else console.error(`${id} done`);
  appendFileSync(out, JSON.stringify(row) + '\n');
}
if (fails) { console.error(`${fails} question(s) got no answer (marked error); the run is incomplete`); process.exit(1); }
