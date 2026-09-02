# kaeru-benchmarks

Benchmarks for [kaeru](https://github.com/LamantinAI/kaeru) — a cognitive memory
layer for LLM agents. This repository is the datasets; the systems under test
and any runners live in kaeru itself.

Kept separate from the main tree, and pulled into it as a submodule, so that
adding or revising a benchmark case does not touch the source history — and so
the datasets can be cited and reused on their own.

## Suites

Two axes, deliberately distinct:

- **[`tool-usage/`](tool-usage/)** — *does a working agent reach for its memory
  at all, and is what comes back the version in force?* Twenty-seven cases built
  from an audit of real interrupted sessions, classified by what the user said
  after stopping the agent. Expectations are **states, not verb sequences**:
  a case grades the final answer and whether the instrument was used, never
  whether a particular verb was called. See [`tool-usage/DESIGN.md`](tool-usage/DESIGN.md)
  for the rules each case must satisfy.

- **`agent-memory/`** *(planned)* — the other axis: can memory produce the right
  answer when the facts are messy — supersession, temporal reads, contradiction,
  absence, naming?

## Why these cases

The design principle is that a case must be **unpassable without its mechanism**:
if an agent can reach the right answer without using memory the way the case is
meant to test, the case measures the model's good day, not the instrument. Each
case carries a named trap and a noise bank large enough to bury the answer, and
several are pinned to specific kaeru defects so a regression names itself.

## Credit

The `tool-usage/` suite was contributed by [@1Croydan1](https://github.com/1Croydan1),
originally as [kaeru#82](https://github.com/LamantinAI/kaeru/pull/82), and moved
here so the benchmarks can live and grow on their own.

## Status

Datasets only — no runner yet. `tool-usage/DESIGN.md` specifies what a runner
must compute (outcome, currency, cost) and why per-case isolation is mandatory.
Contributions of cases drawn from real multi-session agent runs are especially
welcome — those are the ones that find bugs.
