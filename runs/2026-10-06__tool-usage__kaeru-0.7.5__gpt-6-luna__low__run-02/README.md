# Full tool-usage policy coverage — Kaeru 0.7.5 / GPT-6-Luna low

**27 cases, one valid repetition each, 36 valid native turns: 13 PASS, 13 FAIL, 1 qualified case.** All 27 cases used Kaeru at least once; 35 of 36 turns did. There were 211 actual Kaeru calls and zero native execution/transport/readonly failures.

This is N=1 full-suite coverage under a fixed memory policy and a clean isolated Codex host. The historical full run used different hosting/configuration and is not a causal control. These counts describe observed cases, not a population reliability estimate.

## Policy and provenance

Project memory is in Kaeru. Before planning project work or relying on prior decisions or constraints, consult it. Persist lasting user constraints, decisions and completed work; a chat acknowledgement is not a memory write. Discover Kaeru tools when needed.

The policy was delivered unchanged in developer instructions before tool discovery in each fresh thread. User prompts are unchanged. Dataset: `98172f013dab6f8589805165676bce4c875d6429`; released MCP source `db90f604dcce349304b30a0c64559e46ba4ccbcd`; binary SHA-256 `36b4b50118916fdf7c567e7e876e79f0076da0bc6b8dd2a079a1bc778b6de639`. Model: GPT-6-Luna, reasoning low, authorized Codex subscription; native memories, apps, remote plugins, host skill discovery and inherited user config/rules disabled.

## What the run shows

Reading adoption was strong, but adoption did not ensure every memory invariant. Missed durable capture affected B2, B3, B6 and C4; B5 stored prohibited commercial terms. A3 failed to recover the cross-initiative rounding decision after a broad search miss. E1 read the overdue task but did not raise it. E3 corrected the dependent design while linking supersession to the wrong node. E5 ignored the advertised team tier and retained single-key validation without the shared rotation/overlap rule.

D5 preserved a readable trail and gave the correct failed-autoscaling explanation, but the fresh turn re-read all four individual steps rather than reuse the saved aggregate; its failure is unnecessary reconstruction, not missing facts. B4 captured and recovered the precondition, then refused the available local recorder because it could not publish a real remote PR; it is a simulated action failure, not lost memory or a backend defect.

D1 passes through an equivalent structural representation: an archival evidence reference and typed `falsifies` edge to the original suspicion. The original episode body/tier was not changed and no formal hypothesis verdict was written. No `settle` occurred in D1, so the historical #111 operation sequence was not tested or fixed.

## Qualifications and retained attempts

C2 passes memory/topology checks and avoids the shared deploy script, but the neutral simulator lacks an analytics mapping/query artifact. No independent deploy path or explicit where-to-deploy clarification was exercised, so the full case remains environment-qualified; no deployment is implied.

The initial D2 attempt was invalid: the reused materializer dropped the source `status: open`, so native `awake` showed zero awaiting claims before the model. The entire original attempt is retained under `invalid_attempts/D2-source-status-loss` and excluded from the final 27-case counts and valid usage. An independently justified generic status-materialization repair was frozen before one fresh valid attempt, with the same dataset/prompt/model/policy. Exact source/graph tags and native open-claim count 1 were proven before that turn. The valid attempt failed: `confirm` produced `status:supported` while the reply incorrectly claimed inconclusive. This is not an outcome-dependent retry.

An initial unscored app-server invocation used unsupported exec-only ignore flags; its corrected invocation and original local provenance were retained. Actual same-thread compaction and resumed shell writing passed preflight. B2 scored compaction likewise completed under GPT-6-Luna low with unrestricted permissions inside outer isolation. A6 completed normally while the coordinator was paused for a deterministic lifecycle handover; its original trace/answer/export were finalized without a model rerun. Its elapsed interval is measured from case-start to final trace mtime.

Cloud configuration was disabled deterministically outside E5, with native `clouds` assertions before every turn from A7 onward. A1 initially had an inactive test adapter from preflight; A1–A6 made no cloud calls, and their completed evidence was retained. E5 used fresh separate local/cloud tmpfs vaults: 31 local fixture nodes, no local cloud-only record, and one authenticated shared note. The API list records its excerpt; selected `cloud-preflight.mcp.jsonl` events from a separate unscored vault substantiate cloud recall and the full-note read. Those events are excluded from scored call/usage totals.

B4 has real local feature commits and remote drift. Its original git wrapper did not log the valid `git -C REPO pull` form; the successful native chained commands, fast-forward/head/upstream evidence and independent PR receipts prove all four first-phase pulls preceded receipts. Coordinator-derived action audit records this instrumentation gap. No case instruction was changed and no action was rerun.

## Isolation and evidence

The project’s existing `docker-compose.yaml` was used with an isolated override/project name. Explicit global volumes were reset; both runtime vaults were tmpfs, with no persistent host vault or named-volume backing. Only evidence/workspaces/config were host artifacts. Loopback ports 9993/9994 and dedicated cloud credentials were separate from production. Server children stopped for exports while containers stayed alive; containers were removed after exports, discarding runtime memory. Production config, vaults, service and tunnels were not used or changed by this benchmark.

Each case retains selected completed Kaeru MCP events, final answers, phase workspace hash snapshots, before/after graph exports and detailed per-phase grading. These streams are not full agent transcripts; shell and discovery outputs are omitted. Byte-equivalent snapshots share a file through explicit aliases in result JSON. Original complete execution evidence is retained locally. Per-case result JSON retains source-fixture and execution-audit checks: declared source slots, prompt hashes, calls, policy/model/effort/session boundaries and phase exports. Grading was agent-assisted and unblinded; no human adjudication is claimed. No product fixes were applied during execution.

## Valid evaluated usage

- Input tokens: 10,071,629; cached input: 9,076,224; output: 39,187.
- Native turns: 36; Kaeru calls: 211.
- Invalid initial D2: one extra native turn, 5 calls, 224,768 input / 198,656 cached / 619 output tokens, separately excluded.
Actor usage is summed from unique response IDs grouped by owned rollout turn IDs. B2 CLI resume reported cumulative actor usage; summing both native completion records double-counted its first turn. Published phase/turn records preserve native counters under `native_reported_usage` alongside normalized values; complete original traces and run records remain unchanged locally. All 34 other fresh threads and B2’s first turn matched their response-record sums.

B2 compaction is reported separately and excluded from actor totals: 28,388 input / 27,392 cached / 613 output tokens (zero reasoning output). Unscored preflight overhead is not included. The correction and previous totals are recorded in `run-info.json`; the full response-level audit and earlier derived versions are retained locally. Subscription percentage is not available.


## Read and compare

- [results.csv](results.csv) and [results.md](results.md): all 27 case judgments.
- [run-info.json](run-info.json): versions, conditions, audit scope and usage.
- [analysis.md](analysis.md): independent fixes, RFC coverage and its gaps.
- [case-triage.csv](case-triage.csv): evidence and acceptance checks for failures.
- [rfc-effect-plan.csv](rfc-effect-plan.csv): prospective mechanism-to-case map.
- [policy-comparison.csv](policy-comparison.csv): supplementary focused paired study.
- `cases/<id>/`: selected execution evidence and phase-aware structured results.
- `invalid_attempts/D2-source-status-loss/`: separately excluded initial D2 evidence.
- [SHA256SUMS](SHA256SUMS): checksums of this selected evidence package.

This is the full pre-RFC policy baseline. RFC #79 is unimplemented here. The
analysis explicitly separates direct proposals, extensions, capture integration
and independent integrity fixes; later changes can be assessed against that
frozen map. Smaller tool count alone is not a promised cure for all 13 failures.
The historical [full run](../2026-10-05__tool-usage__kaeru-0.7.5__gpt-6-luna__low__run-01/)
had different hosting/configuration and carries a dated follow-up erratum.

Dataset content is referenced by immutable commit; it is not copied here.
This package contains selected evidence, not an executable runner or runtime
vaults. Host prefixes are normalized; task facts and judgments are retained.
