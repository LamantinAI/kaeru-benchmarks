# tool-usage — does the agent reach for memory, and get the current answer?

A regression instrument for the curator API. Sibling to `../agent-memory/`:
that suite asks whether memory can produce the right answer; this one asks
whether a working agent uses memory at all, and whether what comes back is the
version in force.

- **[DESIGN.md](DESIGN.md)** — method, why expectations are states rather than
  verb sequences, scoring, and how this differs from the golden dataset (#80).
- **[RUNNER_CONTRACT.md](RUNNER_CONTRACT.md)** — environment, fixture fidelity,
  blinding, real compaction and disposable team-cloud requirements.
- **[CATALOG.md](CATALOG.md)** — 27 situations, grouped by failure mechanism,
  each with the field evidence behind it.
- **[cases/](cases/)** — worked cases: a fixture, a prompt, and expectations.

## Status

**All 27 catalogued situations are built.** The [R2 runner](../README.md#running)
prepares isolated fixtures and records native agent turns. Correctness is
assessed separately against the case expectations.

| group | cases | what the group isolates |
|---|---|---|
| **A · asked, got the wrong answer** | A1 A2 A3 A4 A5 A6 A7 | the costliest mechanism: memory was consulted and returned the wrong thing — stale versions, unreachable nodes, sibling initiatives, misremembered names, answers living in artifacts |
| **B · rule stated, never captured** | B1 B2 B3 B4 B5 B6 | the most frequent mechanism: a constraint spoken once, holding for weeks, that nothing writes down |
| **C · memory never consulted** | C1 C2 C3 C4 | zero-call failures: cold re-entry, assumed topology, reopened decisions, unrecorded plans |
| **D · capture dispatch** | D1 D2 D3 D4 D5 | the verb matched to epistemic status, so the next session can tell settled from open |
| **E · debts and lifecycle** | E1 E2 E3 E4 E5 | overdue work, unclosed tasks, unmarked contradictions, cold knowledge, the team tier |

**Modes.** 12 single-turn `silent`, 6 `explicit`, 9 multi-turn (a rule is stated
in one session and must survive into the next). Every case carries a `baseline`
recording what actually happened in the field, and every fixture pulls a noise
bank so the target does not sit on the surface.

**Regression guards.** Individual cases are pinned to known defects and fixes, so
a change that breaks one names itself: A2 revision 3 → #81 (scoped core capture
and fresh-session recovery),
D2 → the `inconclusive` verdict added in v0.7.0, D5 → #71 chain membership across
promotion, C1 and E1 → the awake read-back sections, A5 → structural vs prose
supersession (paired with variant A5b to measure what the edges buy).

**Validation update, 2026-10-05:** A1's original bank still ranked its target
first on kaeru 0.7.5. Four additional capture-bookkeeping notes now make the
48-node fixture rank the target fifth; the pre-run minimum remains fourth.
A2 revision 3 tests scoped core capture and recovery in a fresh session; the
former orphan-core fixture is preserved in `legacy/` for explicitly labelled
legacy diagnostics. A preliminary 2026-10-04 run exposed shell sandbox and
seed-escaping errors, so its results are not a validated baseline. Follow the
runner contract and revalidate every materialized fixture before a new run.

## Where the cases come from

Two audits of one vault's complete history — 13,110 session files, June to
September 2026. The first inventoried every `mcp__kaeru__*` call and every
error. The second classified all 136 unique interrupted responses by what the
user said after stopping the agent.

That classification is why the suite is shaped the way it is. The most
expensive failure was not "the agent never asked memory" — in the worst case it
had made **143** memory calls before the user intervened, and still acted on a
superseded method. Any metric built on call counts would have scored that
session as exemplary. So the cases measure what was left in memory and whether
the answer used was current, never which verbs were called.

Silent work requests remain central: twelve single-turn cases and later
turns in multi-session cases do not mention memory. A2 now explicitly requests
core capture in its first turn and tests unprompted recovery in its second.
