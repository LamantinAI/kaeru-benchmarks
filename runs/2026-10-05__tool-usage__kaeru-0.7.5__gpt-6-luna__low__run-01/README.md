# Kaeru 0.7.5 / GPT-6-Luna: an unsuccessful tool-usage run

In this exploratory run, the agent made no Kaeru calls in **21 of 27 cases**.
The final judgments were **3 PASS, 22 FAIL, and 2 partially environment-confounded
cases**. Autonomous use of memory is part of this benchmark: failing to consult
or update memory is a real negative result, even when the immediate task is
otherwise completed.

This record preserves the unsuccessful result before any follow-up experiment.
It does not establish a general failure rate for Kaeru or GPT-6-Luna, and it does
not attribute every failed case to a backend defect.

## What was tested

The [tool-usage suite](https://github.com/LamantinAI/kaeru-benchmarks/blob/98172f013dab6f8589805165676bce4c875d6429/tool-usage/README.md) tests whether a working agent
consults prior decisions, preserves lasting constraints, recovers context across
sessions, maintains current memory, and uses the appropriate memory layer.
Expectations describe outcomes and graph states rather than mandatory API verb
sequences. Some cases explicitly allow a non-memory route or a clarifying
question.

- **Kaeru:** released 0.7.5 binary, source commit
  `db90f604dcce349304b30a0c64559e46ba4ccbcd`.
- **Binary SHA-256:**
  `36b4b50118916fdf7c567e7e876e79f0076da0bc6b8dd2a079a1bc778b6de639`.
- **Dataset:** [98172f013dab6f8589805165676bce4c875d6429](https://github.com/LamantinAI/kaeru-benchmarks/tree/98172f013dab6f8589805165676bce4c875d6429).
  The dataset is referenced by this immutable revision; it is not copied into
  the run directory.
- **Agent:** GPT-6-Luna, low reasoning effort, Codex CLI with native MCP tools.
- **Sampling:** one final evaluated attempt per case; 27 cases, 36 agent turns.
- **Execution:** October 5, 2026, UTC. Packaging occurred after execution.
- **Configuration:** built-in Codex memories disabled; user configuration ignored;
  no additional memory reminder added to the baseline prompts. The environment
  retained a skills catalog and tool-discovery mechanism; this was not a
  minimal tools-only host.

Each case used a fresh local vault and an opaque working directory. New-session
phases used fresh threads. Seed checks verified exact fixture content and
historical timestamps. E5 used a separate test cloud with a cloud-only node;
B2 used actual thread compaction. External actions were replaced with local
simulators. No production memory service was used.

## Observed outcomes

| Measure | Observed count |
|---|---:|
| PASS | 3 |
| FAIL | 22 |
| Partially environment-confounded | 2 |
| Cases with zero Kaeru calls | 21 |
| Cases with any Kaeru calls | 6 |
| Kaeru calls across final evaluated turns | 62 |

The 22 failures divide into four observed groups:

| Failure group | Cases |
|---|---:|
| No memory activation | 17 |
| Memory saved initially, not consulted in a fresh session | 2 |
| Memory activated, but curation incomplete | 2 |
| Product operation broke a required evidence relationship | 1 |

See [results.md](results.md) for all cases and [analysis.md](analysis.md) for the
interpretation. The groups classify observed behavior; they do not establish a
single causal explanation.

The three passes mean different things. **A6** found the authoritative project
artifact, which the case permits. **C2** asked for a deployment target, also
permitted. Neither used Kaeru. **D3** completed the required memory maintenance.
A2 and D5 also had successful first memory phases, followed by failed re-entry.

## Qualifications

**B2** is partly confounded by permissions after resuming a genuinely compacted
thread. The first phase failed to persist its constraint; the second phase
cannot be judged as an unqualified implementation failure. **E5** had a working
isolated cloud fixture, but lacked the webhook implementation needed for the
code task. The agent did not attempt the available shared-memory lookup.

A4, B4 and C2 used local action simulators. B4's repositories contained baseline
README commits rather than a prepared client change, limiting its action phase;
its independent failure to persist the precondition remains observable.

Discarded attempts are excluded from all final counts: an incomplete A1
workspace, a B2 working-directory drift attempt, and a B2 read-only drift
attempt. The final B2 qualification remains visible rather than being discarded
into an apparently clean aggregate.

Grading combined one read-only GPT-6-Luna evaluation of an evidence pack with
manual and independent targeted audits correcting D1 and D5. It is not a fully
independent, repeated evaluation. Fixture labels also require care: D3 and D5
are marked `silent`, although their actual prompts explicitly mention memory.

## A confirmed product defect

D1 successfully created evidence links, then successfully promoted the evidence
node with `settle`. The exported current graph went from two live edges to zero.
A separate reproduction without an LLM confirmed the operation behavior.
Historical records may remain; the demonstrated problem is recoverability of
relationships in the current graph. The separate reproduction is tracked in
[kaeru#111](https://github.com/LamantinAI/kaeru/issues/111) and is outside this run
package.

## Evidence and usage

- [results.csv](results.csv): machine-readable per-case table, generated from JSON.
- [results.md](results.md): per-case judgments, with links to structured results.
- [run-info.json](run-info.json): conditions, versions, timestamps, aggregate
  counts, usage, grading method and evidence selection rules.
- `cases/<id>/`: final answers, per-turn usage, selected MCP events, per-case fixture
  validation, before/after test memory, and workspace snapshots.
- [SHA256SUMS](SHA256SUMS): integrity checks for the packaged files.

The `*.mcp.jsonl` files contain completed Kaeru MCP events, including arguments
and results. They are **selected evidence streams, not full agent transcripts**.
Empty streams denote turns with no completed Kaeru MCP events. Shell traces,
host configuration and intermediate attempts are outside this package. Host
filesystem prefixes are normalized; the original local record is retained.
Identical before/after memory exports share one file: the result points both
phases to it and explicitly records `memory_after_identical_to_before`. Identical
workspace snapshots are handled the same way in per-turn records. This removes
byte-for-byte duplicates without treating missing evidence as proof of no change.

This package is an evidence record, not a standalone executable runner.

Final evaluated attempts used 4,342,107 input tokens, of which 3,857,920 were
cached, and 18,580 output tokens. Reported reasoning output was 1,329 tokens.
Bootstrap, discarded attempts and grading are excluded. Subscription quota
consumption was not available.

## Conclusion

In this configuration, making Kaeru available did not reliably cause the agent
to use project memory. That failure is part of the benchmark's intended signal.
The run also exposed incomplete curation and a reproducible product defect.
These outcomes are retained without rewriting prompts, fixtures or results.
No follow-up experiment is included in this record.

The tool-usage suite was contributed by [@1Croydan1](https://github.com/1Croydan1),
originally in [kaeru#82](https://github.com/LamantinAI/kaeru/pull/82).
