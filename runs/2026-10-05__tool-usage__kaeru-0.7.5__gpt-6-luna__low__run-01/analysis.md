# Failure analysis

## What the run establishes

The benchmark includes autonomous memory adoption. An agent that never consults
memory can fail even if its immediate answer looks reasonable. Conversely,
calling memory is not sufficient to pass: the resulting answer, durable state,
and current relationships must satisfy the case.

There were 21 zero-call cases overall. Among the 22 failures, 17 never activated
Kaeru and two saved useful memory in the first session but did not consult it
in the next. Thus **19 of 22 failures involved activation or re-entry**. This is
a behavioral classification, not evidence that retrieval returned bad facts.

Zero-call cases also include two permitted passes, A6 and C2, and the two partly
confounded cases, B2 and E5. It would be incorrect to describe all 22 failures
as forgetting Kaeru or all zero-call cases as failures.

## Activation and discovery

All six cases that used Kaeru began with an explicit request to save, write,
update or tidy memory: A2, A7, D1, D3, D4 and D5. No other case used Kaeru.
This association suggests that explicit memory requests were a strong activation
cue in the tested setup. With one attempt per case and different prompts, it
is not a controlled estimate of their causal effect.

Detailed tool descriptions are exposed through the host's discovery mechanism.
One plausible explanation is that an agent must already choose to discover
memory tools before receiving their detailed guidance. The retained MCP-only
streams do not capture initial model requests or discovery, so that explanation
is a hypothesis rather than a conclusion established by the packaged traces.

Other possible contributors include model behavior at low reasoning effort,
missing standing project policy, host integration, skills configuration and the
cost of choosing among tools. This run does not isolate these factors. It does
not prove that reducing the tool count or adding a reminder will fix adoption.

The result remains valid for the tested configuration: unprompted memory use was
unreliable. Configuration limitations restrict generalization; they do not erase
the observed failure.

## Re-entry after a successful write

**A2** correctly saved the scoped TSV/date-first convention. A fresh session
made no memory calls, requested records instead of recovering the available
facts, and produced no TSV report. The initial write succeeded; continuity did
not.

**D5** preserved a useful handoff summary and repaired relationships in the
first phase. The absence of a particular `chain` call is not a failure when an
alternative representation satisfies the required state. The fresh second
session did not retrieve the summary and omitted the actual failed autoscaling
attempt. The overall failure is re-entry, not inability to save a reasoning
trail.

## Errors after activation

**A7** created a duplicate with `jot` without first searching for the existing
root-cause record. Memory was available and used, but the strategy did not
satisfy deduplication.

**D4** saved an archival reference but paraphrased a document that required exact
preservation and left a second discussion open. This was incomplete curation.

These cases show why improving activation alone may not be sufficient. The
benchmark also measures how the agent maintains memory after choosing it.

## D1: operation semantics

In **D1**, the agent successfully created a falsifying relationship and a
refuted claim linked to its evidence. A successful `settle` then replaced the
evidence node without preserving the required live relationships. The final
memory export contained no edges.

The independent operation reproduction has two live edges before promotion
and zero after, with all calls successful. This isolates a product behavior
from a model failure to create the links. It does not demonstrate deletion of
all historical substrate records. The defect concerns current-graph recovery
and is tracked in [kaeru#111](https://github.com/LamantinAI/kaeru/issues/111).

## Limits of the aggregate

Some failed cases contained successful ordinary actions: A1 used background
capture correctly and B1 honored low reasoning effort for its first job.
Their memory requirements still failed. Per-phase results therefore matter
more than a single total when diagnosing the system.

B2 and E5 remain partly environment-confounded. B4's limited action fixture is
also disclosed. These qualifications prevent interpreting 22 FAIL as a clean
release-wide defect rate, while leaving independent memory failures visible.

Dataset mode labels are not a reliable basis for an explicit-versus-silent
comparison: D3 and D5 mention memory in their prompts despite being labeled
`silent`. The exact fixtures are accessible at the pinned dataset revision; neither
prompts nor labels were changed retrospectively in this record.

This was an exploratory N=1 run with partly machine-assisted grading. It
supports a concrete negative observation about this configuration, a useful
failure taxonomy and one independently reproduced product defect. It does
not support model comparisons, statistical reliability estimates or a proven
single explanation. Any later experiment should be recorded separately.
