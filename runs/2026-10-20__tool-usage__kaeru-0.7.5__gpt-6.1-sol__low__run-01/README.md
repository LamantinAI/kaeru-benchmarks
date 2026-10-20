# R2 API validation with the operating guide

**The R2 API passed integration and agent tool-use validation on this suite.**
All 81 attempts executed successfully; 80 met every scenario requirement.
The remaining failure was an omitted agent action, not a demonstrated API
failure. Its original FAIL is retained in the evidence and totals.

This conclusion covers the evaluated scenarios with the guide explicitly
delivered. It does not assert exhaustive coverage of every API operation or
perfect model compliance on arbitrary input.

## Conditions and results

27 scenarios, three repetitions each, `gpt-6.1-sol` with low reasoning. The
three repetitions ran concurrently and completed in 28 minutes 52 seconds.
Code, binaries, fixtures, policy and guide were fixed for the entire series.
There were no additional reruns or discarded attempts.

| Group | Mechanism | Successful attempts |
|---|---|---:|
| A | Discovery, currency, project boundaries, sources and duplicates | 21/21 |
| B | Constraints across fresh sessions and compaction | 18/18 |
| C | Re-entry, decisions and plans | 12/12 |
| D | Verdicts, completion, references and saved explanations | 14/15 |
| E | Debts, tasks, contradictions, archival and team knowledge | 15/15 |
| Total | | 80/81 (98.8%) |

All 27 scenarios passed at least once; 26 passed all three repetitions.
The [case results](results.md) aggregate repetitions: 26 PASS and one PARTIAL
case. [Attempt results](attempts.csv) preserve 80 PASS and one FAIL.
Execution completion is separate from correctness: 81 EXECUTED, no timeouts
or launch failures, 108 actor turns and 105 distinct native threads. Three
real native compactions completed. Actual model, effort and policy delivery
were audited against the saved native sessions.

### Remaining agent failure

[D3, repetition 2](cases/D3-arc-closed/repetitions/02/result.json) corrected
stale pending-work wording and preserved completion facts and provenance.
It did not promote the conclusion to archival: no archival record exists in
the final state and no lifecycle promotion was attempted. The other two D3
repetitions performed the promotion successfully. This is retained as a
behavioral reliability limitation rather than relabeled as a pass.

The financial write-exclusion scenario passed 3/3: stored records contain
only the exclusion itself and permitted technical/progress information.
Offer amounts, improved terms and commitment durations were not persisted.
Compliance remains model-driven; no mechanical content-policy gate is claimed.

## Interpretation and evidence

The primary assistant reviewed original case expectations, actual tool
responses, user-facing messages, before/after records and resulting files.
Assessment was unblinded; no independent judge model or human adjudication
is claimed. [Reviews](reviews.json) retain the reasons and qualifications.

- D5 saved a trail in every repetition. Repetitions 1 and 3 recovered a saved
  explanation through a handoff summary in context; repetition 2 also found
  the named trail through search. These observations do not isolate the
  causal benefit of the trail operation from other saved summaries.
- E3 repetition 2 flags the dependent design through a supported claim about
  it and a corrective plan targeting it, rather than a formal review flag.
- A1 verifies recovery and observance of the background/window-ID capture
  rule. The isolated workspace has no desktop connection; no actual frame
  capture is claimed.
- This guided condition differs from minimal-policy runs. Changed fixtures,
  models, schemas or instructions prevent treating historical totals as a
  matched causal comparison.

## Cost

| Metric | Total |
|---|---:|
| Input tokens, including cache | 23,526,986 |
| Cached input tokens | 20,284,032 |
| Uncached input tokens | 3,242,954 |
| Output tokens, including reasoning | 108,604 |
| Reasoning output tokens | 2,185 |
| Kaeru calls | 891 |
| Rejected calls, recovered by the agent | 37 (4.2%) |

Usage takes the last cumulative counters per distinct thread, avoiding
double-counting resumed turns. Cache and reasoning are subsets, not additional
tokens. Extra compaction usage was not separately reported; assessment cost
is excluded. Rejections comprise 27 invalid arguments, nine revision conflicts
and one stale cursor, all retained in the completed tool events.

## Reproduction and artifacts

Exact source, dataset, runner and binary hashes are in [run-info.json](run-info.json).
The [guide](memory-guide.md) and [full policy](memory-policy.txt) are exact copies.
Original execution commit hashes are retained as provenance. The local work
was squashed for publication; `source.patch.gz` and `runner.patch.gz` reconstruct the
exact tested trees from their published base commits. Decompress and apply each patch in its
respective checkout; base commits and expected target tree hashes are recorded
in `run-info.json`. After reconstructing the revisions and preparing an
authenticated Codex CLI:

```sh
python3 main.py --source /path/to/kaeru \
  --memory-guide runs/2026-10-20__tool-usage__kaeru-0.7.5__gpt-6.1-sol__low__run-01/memory-guide.md \
  --model gpt-6.1-sol --effort low --repetitions 3 \
  --output /path/to/new-results
```

The original execution used three processes with one repetition each and
separate outputs. For exact runtime matching, supply the MCP, cloud, helper
and native binaries identified by their recorded hashes.

`cases/<id>/repetitions/<NN>/` contains normalized memory snapshots, completed
Kaeru events, all user-facing messages, execution counters and resulting text
files. Native session metadata, shell/environment transcripts, runtime/auth
configuration and embedded databases are excluded. The complete original raw
archive remains local; `native-audit.json` identifies the inspected raw session
files, which are not distributed in this record. `SHA256SUMS` covers the
packaged bytes after path normalization.

`results.csv` is generated from per-case JSON with the existing exporter:

```sh
python3 runs/export_results.py runs/2026-10-20__tool-usage__kaeru-0.7.5__gpt-6.1-sol__low__run-01
```
