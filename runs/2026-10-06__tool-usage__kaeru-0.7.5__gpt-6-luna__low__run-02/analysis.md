# Fix triage against RFC #79

The full policy run produced 13 PASS, 13 FAIL and one environment-qualified
case. Every case called Kaeru; 35 of 36 valid turns did so. Adoption, retention,
retrieval, curation and task execution are distinct outcomes. The 13 failures
are not 13 newly established backend defects.

This analysis maps the actual traces to the current
[RFC #79](https://github.com/LamantinAI/kaeru/issues/79), retrieved on October 6,
2026. Proposed remedies have not been tested. The per-case mapping and acceptance
checks are in [case-triage.csv](case-triage.csv); original results are unchanged.

## Fix independently of the RFC

### Preservation during promotion — #111

[Issue #111](https://github.com/LamantinAI/kaeru/issues/111) is independently
reproduced in the earlier run: successful promotion disconnected evidence
relationships from the live graph. The current `consolidate` implementation
copies outgoing `derived_from` relationships, then retracts the predecessor;
other evidential and incoming relationships do not get equivalent preservation.
Even its copied provenance edges are rebuilt with weight 1.0 and null properties.

Fix the operation's preservation contract before building more automation on
it. Regression coverage should inspect incoming/outgoing relationship types,
weights/properties, memberships, saved trails and historical recoverability,
rather than merely counting one surviving provenance edge.

D1 passes in this run through a different allowed representation: an archival
finding structurally falsifies the original suspicion. It never calls `settle`.
This pass does not demonstrate that #111 has been fixed. The successful D3/D5
provenance paths also do not cover every relationship type.

Source: `kaeru-core/src/mutate/consolidate.rs`, especially its edge-copy and
predecessor-retraction steps.

### Atomic replacement — #103

[Issue #103](https://github.com/LamantinAI/kaeru/issues/103) covers another property:
`supersedes` and consolidation perform several separate writes. Retraction-last
makes interruption survivable, but does not make replacement atomic. Current
source explicitly documents that limitation.

Fix and verify transactional behavior independently of tool renaming. Keep this
separate from #111: preserving the wrong set of relationships atomically would
still be wrong. No crash or partial replacement was observed in this benchmark,
so #103 is a known robustness gap, not an explanation of these 13 failures.

RFC's proposed automatic reactivation of edited archival knowledge makes this
foundation more important; it does not supply the transactional guarantee.

### Server identity — PR #108

[PR #108](https://github.com/LamantinAI/kaeru/pull/108) is still open. The server's
initialization metadata should identify Kaeru rather than the rmcp dependency.
This is a small independent correction to diagnosis and integration. There is
no evidence here that it caused the observed search/capture/curation failures.
Versioned binary hashes and `config()` were used to establish the tested release.

### Benchmark infrastructure

Keep these as runner work, with their own checks and provenance:

- Validate source YAML → normalized manifest → graph, including status/kind,
  dates, policy, edges and artifacts. The missing D2 status was a runner defect,
  not a Kaeru defect. Retain the invalid attempt and the corrected valid one.
- Normalize usage from unique response records grouped by actor turn. B2 CLI
  resume counters are cumulative; compaction belongs in a separate accounting
  category. Preserve raw counters alongside derived values.
- Observe Git actions independently of wrapper position: `git -C REPO pull`
  bypassed a logger that recognized only a leading `pull` argument.
- Make lifecycle configuration deterministic before startup, and probe the
  running adapter registry. A polling watcher is not a correctness guarantee.
- Declare simulator semantics clearly and consistently in future experiments.
  B4 refused the local PR recorder despite recovering the memory rule. C2 lacked
  a deployable query and identifiable independent route. Supply task capabilities
  without leaking the hidden memory/precondition answer.

These repairs should not be sold as improvements to Kaeru's memory quality.
Completed outcomes remain recorded; a changed environment defines a later test.

## Work directly supported by the RFC

### D2: one verdict operation with an explicit enum

RFC's merge of `confirm`/`refute`/`inconclusive` into `verdict` directly addresses
this selection failure. In the valid D2 attempt, the agent called `confirm`,
which correctly set `status:supported`, then told the user it had marked the
claim inconclusive. `inconclusive` already exists and is correctly described;
this is not a missing backend capability.

Use a required verdict value and echo the resulting transition explicitly.
The existing output says `confirmed`, rather than printing the machine status.
An additive status/transition echo can be improved before the rename; the unified
operation belongs with the RFC. Neither change guarantees the model chooses the
right value. Acceptance requires agreement between requested meaning, graph
status and final answer, with the check/evidence still recoverable.

Sources: `kaeru-mcp/src/server.rs` hypothesis cycle and
`kaeru-mcp/src/tools/hypothesis.rs::verdict`.

### D5: deliver the saved reasoning, not just a read hint

The first phase saved a valid trail and summary. The fresh phase gave a correct
answer but opened all four steps individually. That violates the explicit
trail-reuse expectation; it is not factual forgetting or a lost trail.

RFC Level 2 can address this by delivering the existing causal summary through
ordinary reads. A trail name or another instruction to call `why` is insufficient:
those hints were already delivered. The useful summary includes the failed
scaling attempt and why it favored repartitioning. Measure whether the answer
uses that aggregate without reconstructing every step, not whether a particular
verb gets called.

### E1: put relevant blocking debts first

RFC's debt-first budget/ranking is a plausible improvement. The actual awake
output already contained an explicit overdue warning, and search exposed the
sign-off task. The model nevertheless completed the requested retention draft
without surfacing the overdue blocker.

Show the task's significance for current work, ahead of repeated noise listings,
under a fixed budget. Delivery was established already; emission counts alone
would produce a false success here. Acceptance measures the user-facing warning
and its relevant consequence while preserving task completion.

## Partial coverage and explicit RFC extensions

### A3: sibling-initiative retrieval is not solved by fewer read verbs

The rounding decision lived in `billing-legacy`; the model searched only
`billing-service` with an overly restrictive multi-term query. The fixture has
no structured link to that decision. The backend returned the scoped results
requested; no search implementation defect was established.

RFC's read consolidation can improve ergonomics, but does not specify an alias/
sibling-scope strategy. Define permission-bounded query recovery and cross-scope
lookup, or explicit project/initiative relationships. Avoid assuming that global
unscoped search is always an acceptable fallback. Acceptance recovers the
existing per-line rounding rule and yields 5.86 for the sample.

### E3: safer identity-aware correction

`revise` and dedicated `supersede` already exist. Instead, the model captured a
second fact and attached a generic `supersedes` edge to the dependent design,
not the old fact. Updating the design correctly did not mark the old one-hour
fact as obsolete.

RFC keeps those appropriate operations and proposes automatic archival
reactivation. That does not identify the right predecessor. Add explicit
replacement intent, useful named-capture collision feedback and observable
resulting state. Inspect dependents before changing the old fact. Avoid claiming
that a generic link and a replacement transaction are the same operation.

Acceptance: old fact visibly corrected/superseded, dependent design updated,
and history/provenance recoverable. This is mutation ergonomics/validation,
not evidence that the existing backend ignored its supplied arguments.

### D4: source fidelity plus complete curation

The model used the correct archival reference family, but paraphrased the final
conventions and left both discussion rounds looking unresolved. Keeping `cite`
and making closure cues visible may help; neither adds a faithful source
pass-through or performs the whole curation step.

Where canonical source text is supplied, support capturing that actual source
rather than rebuilding it through generation, with identity/hash checks. Resolve
all superseded discussions while preserving their provenance. The server cannot
recover an original user message it was never given. This needs an explicit
source/curation workflow, beyond a smaller tool list.

### E5: team context must be fetched or declared incomplete

The cloud was working and fresh. The model received the team-tier warning but
read only the local retry note, then implemented single-key hardening without
quarterly rotation or a two-week overlap.

The current RFC keeps `cloud_recall` on the assumption that the team-tier line
creates its moment. This run supplies a counterexample. Define bounded opt-in
team enrichment in the MCP/host read layer, or an explicit coverage state that
requires handling before a confident action. Preserve initiative permissions,
source identity, budget and failure/timeout behavior; core stays network-free.
Do not present changing the number of advertised tools as a fix for unread
team knowledge.

## The capture gap needs its own integration track

B2, B3, B5, B6 and C4 each failed to retain a newly supplied constraint,
restriction, closure or plan at the required moment. B5 additionally stored
prohibited commercial terms. These are semantic content/lifecycle failures.
They are not eligible for graph-derived metadata hygiene.

The RFC assumes a save intention exists when a capture verb is needed. These
cases show that the intention may be missing. For B6's first turn there was no
MCP call at all: the server had no observation of the user's closure. Enriching
a later read cannot recreate content that never reached it.

Add an explicit host/agent capture checkpoint at meaningful boundaries:
constraints, accepted plans, closed questions, completion, and before context
loss. Scope working boundaries to their task/project and record their lifecycle.
Capture restrictions must bind before the first write; forbidden content should
not be persisted and then removed, because historical storage can retain it.
The driver must respect the RFC's semantic-authority boundary and user choices.

`reflect` can be one carrier for maintenance, but inspecting only the existing
graph cannot detect every omitted conversation update. The host must supply the
relevant update. [Issue #100](https://github.com/LamantinAI/kaeru/issues/100) is a
read relevance/doubt hook; it does not already implement this write-side track.

## Update the RFC's evidence and migration checks

The small controlled policy study yielded 0/9 successes in baseline and 7/9 with
an early developer policy. It does not prove prompts solve everything, but it
limits the RFC's broad assertion that better explanation is exhausted. Early
host policy and a post-call opportunity hint are different interventions.
In the full run, adoption succeeded broadly while semantic state often failed.

The RFC inventory is 69 tools as of 0.7.1; the tested surface is 71. Refresh the
inventory before committing to a count. Compatibility aliases must not silently
repopulate the default advertised agent tier, or the promised smaller name list
will not exist during migration. Keep call compatibility and listing policy
separate and test actual `tools/list` output.

Measure delivery and actual use, state correctness, capture/recovery, and cost.
A delivered overdue warning was ignored in E1; a delivered cloud warning was
ignored in E5. Neither emission alone demonstrates success. The current valid
actor input was 10,071,629 tokens, including 9,076,224 cached; compaction is separate.
Token counters do not establish subscription quota cost.

## Suggested order

1. Land/test independent integrity and identity corrections (#111, #103, #108),
   and consolidate the validated runner repairs. These are prerequisites and
   measurement work, not a promised cure for the 13 failures.
2. Implement RFC's explicit verdict operation and actual trail/debt enrichment;
   retain compatibility without expanding the default advertised tier.
3. Add sibling/team coverage and identity/source-aware curation specifications.
4. Treat capture checkpoints and pre-write restrictions as a separate integration
   deliverable, rather than assuming read-side consolidation will solve them.
5. Re-run unchanged cases with recorded conditions. Use D2/D5/E1 to evaluate the
   direct RFC mechanisms, A3/E5 for its extensions, and B2/B3/B5/B6/C4 for the
   capture track. Full-suite results follow targeted mechanism checks.

No product changes, issue creation, commits or model runs were performed for
this analysis. Evidence and grades from the completed run are preserved.

## Prospective evaluation after RFC implementation

The [effect plan](rfc-effect-plan.csv) freezes hypotheses at publication. It is
not a measured RFC result. Mechanism IDs V1/R1/R2/X1/X2/W1/W2/I1/I2/I3/S1/G1/Q1
connect the proposal, baseline case evidence and the observable check in the next
run. Keep this table unchanged; append a later assessment linking its run ID,
implementation commit, which mechanisms actually shipped, and per-case outcomes.
A hypothesis can be supported, rejected or remain untested.

For each mechanism, distinguish availability, delivery, actual use and resulting
state. In particular, emitting a debt/cloud line is not success if the answer or
implementation ignores it. A renamed verdict tool is not success if the graph
still holds the wrong status. Trail enrichment must preserve the failed attempt,
not merely reduce call count.

A comparable follow-up holds the dataset revision, prompts, policy, model ID,
reasoning effort, host/tool-discovery settings, grading criteria and validated
fixture semantics fixed. Record exact product/CLI/harness versions and the RFC
implementation commit. Relative dates and fresh generated IDs should preserve
fixture meaning rather than be compared as identical bytes. Use matched
repetitions on affected cases before drawing reliability conclusions; this full
baseline has one valid attempt per case.

Independent bug fixes and harness repairs are separate interventions. If they
ship together with RFC changes, test an intermediate bug-fix-only build or
report a bundled effect rather than assigning every changed score to the RFC.
B4/C2 results from changed simulator environments are not direct before/after
RFC evidence without a matched baseline. Changes to criteria require a new
benchmark revision and an explicit comparability qualification.

The earlier focused policy comparison is supplementary evidence, not the full
run's control: [matched pairs](policy-comparison.csv) record baseline 0/9 versus
policy 7/9 on C1/A2/E2, three repetitions each under the same clean host. That
comparison varied an early developer policy, not an RFC implementation. The
supplement contains paired judgments rather than complete transcripts; the
full local evidence is retained. Its narrow scope does not establish a
population reliability estimate or attribute the historical full-suite delta.
