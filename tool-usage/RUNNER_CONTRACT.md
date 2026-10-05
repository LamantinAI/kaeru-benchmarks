# Runner contract for the current suite

The dataset describes memory states and work requests. A runner supplies the
controlled environment needed to perform them. A failure to start the shell,
find a project workspace, or reach a required cloud is an infrastructure
failure, not an agent-memory outcome.

## Pin and validate before paying for model turns

Record the exact dataset commit, kaeru version/source commit, model, reasoning
setting, permissions and repetition count. A single repetition is exploratory;
report counts and traces, not a stochastic pass-rate estimate.

Before running any model:

- Prove that the actual `workspace-write` sandbox reads and writes files.
- Prove native MCP connectivity and the tested kaeru version.
- Build a fresh vault per case/repetition. Share only that case's vault between
  its turns; never reuse a mutated fixture for another case.
- Seed declared timestamps through the substrate. MCP captures stamp NOW and
  cannot faithfully materialize historical age or relative ordering.
- Read the materialized state back and compare exact bodies, types, tiers,
  layers, tags, initiative memberships, timestamps and edge endpoints. Cozo
  double-quoted raw literals are not JSON strings: blindly embedding JSON
  escapes can store literal backslash-n instead of a newline. Prefer bound
  parameters, or correctly escaped Cozo single-quoted literals.
- Check the complete declared noise count and every rank/age constraint. A1
  requires `capture*` to rank its target at least fourth, and at least five
  noise nodes to be newer than the target. Do not weaken a failed constraint.
- Preserve artifact paths and contents. Reject paths escaping the workspace.

A2 revision 3 starts without the convention; it must be captured during turn
one. The archived revision 2 is not part of the default suite.

## Blind model sessions

The model receives only its work prompt, native tool descriptions and neutral
project context. The initiative name may be supplied as project context;
conventions, expected answers and grading criteria may not.

Use opaque workspace identifiers. A working directory named
`A1-stale-method` or `D4-settled-doc` reveals what the case tests. Keep case
YAML, fixture manifests, expected results and grader traces outside the model's
workspace/context, and enforce read restrictions where the runtime supports
it. Record any remaining isolation limitation.

Do not add a runner reminder to consult memory for silent prompts. Product
instructions supplied by the tested MCP server remain part of the system
under test; preserve them and record their configuration.

For `session: fresh`, use a new model thread with no previous prompt, answer,
transcript or handoff summary. Preserve the case's memory and ordinary project
artifacts. For B2, keep the same thread and trigger **real compaction** between
turns, then save the completion event before issuing turn two. A mere resume,
new thread or shortened prompt is not compaction.

## Controlled action environments

Never use real deployment targets, user repositories, screen windows or
external PR services for these synthetic requests. Supply declared local
workspaces and interfaces with action logs, without leaking the hidden rule.

| Work request | Required environment |
|---|---|
| A1 guide capture | A synthetic window/capture interface if executing captures; the case also explicitly allows a stated method citing the stored rule. Do not capture the user's screen. |
| A2 weekly report | Writable workspace and exact `project-context.md` artifact. The output file is graded for format, naming and the stored run facts. |
| A3 invoice totals | Minimal local billing implementation/data if grading code; no prefilled rounding convention. The existing honest-uncertainty alternative remains allowed. |
| A4 rollback | Disposable route/stack state and a local inspect/repoint/stop interface. Its help lists capabilities, never the required order. Grade the action log and memory lookup. |
| A5 upload check | Minimal local client implementation and writable files; no prefilled size limit. |
| B1/B2 job exports | Local job/export configuration with staging/shared destination capabilities; no hidden rule in source comments or help. |
| B3/B5 investigation | Inspectable synthetic service files and data, so unchanged files are evidence rather than the absence of a service. Preserve before/after checksums. |
| B4 PR precondition | Disposable Git repositories and local bare remotes plus a local PR recorder. Verify remote refresh happened before PR creation. Do not invoke real GitHub publishing. |
| B6 notification change | Local notification configuration and inspection surface; do not prefill the newly stated decision. |
| C2 deployment | Local deployment recorder/target interface if executing a deploy; the case also allows asking where to deploy. No real SSH/production action. |
| E4 table styling | Inspectable local table/style files, without the frozen typography decision duplicated in source. |

If action stubs cannot exercise the required behavior, report
`UNSUPPORTED_WORKSPACE` or `ENVIRONMENT_CONFOUNDED`. Do not silently turn an
execution expectation into a plan-only pass.

## Team tier

E5 requires an independent disposable cloud vault, not the user's team cloud.
The initiative policy is `team`. Seed ordinary `nodes` locally and
`cloud_nodes` **only in the cloud**, with exactly the declared content.

Before the model starts, verify all of these:

1. The MCP is configured only for the test cloud.
2. The local graph contains the local note and noise, not the cloud-only node.
3. `awake`/`overview` advertises the shared tier.
4. Native `cloud_recall` reaches the cloud-only record.
5. A new repetition starts with fresh local and cloud states.

## Evidence and grading

Save model prompts/hashes, thread IDs, full native tool traces and command
results, memory before/after, ordinary workspace before/after, action logs,
cloud/compaction evidence, elapsed time and input/cached/output token counts.
Do not infer a percentage of subscription quota from token counters.

Grade memory/behavior states and `fail_if` independently of the chosen verb
sequence. A recorded rule without recovery, or a good answer without a durable
capture where required, is partial success, not a full pass. A transient tool
error followed by a correct recovery is not automatically a failure.

For multi-turn cases, preserve phase-level results. A completed capture phase
can fail independently, but an environment error in a later phase must still
be shown; do not describe the whole case as an entirely clean execution.
Separate invalid fixtures, expired revisions, unsupported capabilities and
runtime errors from eligible model/product outcomes.
