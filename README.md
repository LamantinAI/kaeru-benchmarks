# kaeru-benchmarks

Benchmarks for [kaeru](https://github.com/LamantinAI/kaeru) — a cognitive memory
layer for LLM agents. This repository contains datasets, recorded benchmark
results and an [R2 case runner](#running). The systems under test
and the previous executable runners live separately.

Kept separate from the main tree, and pulled into it as a submodule, so that
adding or revising a benchmark case does not touch the source history — and so
the datasets can be cited and reused on their own.

## Running

Requires Linux, Python 3.11+, Cargo, bubblewrap and an authenticated Codex CLI.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e .

python main.py --source /path/to/kaeru --model gpt-6.1-sol --case B2-constraint-after-compaction
```

`main.py` uses argparse. `--help` lists the options. It builds the required Kaeru
binaries and fixture helper using Cargo's target directory, and locates the
installed native Codex executable. Existing binaries can be supplied explicitly.

The default model is `gpt-6.1-sol` with low reasoning effort.

- `--prepare-only`: verify data and services without model calls.
- `--case ID`: select a case; repeat for several, or omit for the whole suite.
- `--output PATH`: results directory; defaults to `results/<timestamp>`.
- `--repetitions N`, `--effort low`, `--timeout 900`: run parameters.
- `--memory-guide PATH`: supply the product's reusable tool guide to every
  turn, including resumed and compacted sessions. The complete text and guide
  hash are saved. This is a distinct condition from the minimal memory policy.

The default memory policy tells the model to consult Kaeru and persist lasting
project information within the user's write boundaries. Those exclusions take
precedence over the generic capture instruction. Its text, source versions, native traces, usage, memory and
workspace snapshots are saved with results. Fixtures and expected answers are
hidden from the model in a disposable filesystem namespace. Network is shared
for model authentication and the local test services.

To evaluate an agent given Kaeru's operating guide:

```sh
python main.py --source /path/to/kaeru --memory-guide /path/to/kaeru/skills/kaeru-skill/SKILL.md
```

Host skills and rules remain disabled to prevent unrelated personal memory from
leaking into cases. MCP initialization instructions are recorded but are not
assumed to reach the model: the guide above is supplied explicitly. Guides must
describe the product, without case identifiers, hidden facts or expected answers.

Cases and their initial project files live in `tool-usage/cases/`; runtime code
in `runner/` reads those declarations. There are no per-case solver paths.
Execution completion is recorded separately from correctness; expectations are
defined by each case's `expect` and `fail_if`.

Run tests:

```sh
python -m unittest discover -s tests -v
```

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

Datasets and [recorded runs](runs/README.md). The first record documents an
unsuccessful Kaeru 0.7.5 / GPT-6-Luna tool-usage experiment. A second full
record adds an early memory policy, phase-aware results and prospective
[RFC analysis](runs/2026-10-06__tool-usage__kaeru-0.7.5__gpt-6-luna__low__run-02/analysis.md). Executable runners
for previous experiments are not included here. The [R2 runner](#running)
prepares isolated fixtures and records native agent turns; correctness grading
is separate. The [guided R2 validation](runs/2026-10-20__tool-usage__kaeru-0.7.5__gpt-6.1-sol__low__run-01/)
completed all 81 attempts with 80 PASS and one omitted archival promotion;
the API passed integration and tool-use validation for the evaluated scope.
`tool-usage/DESIGN.md` specifies what a runner must compute
(outcome, currency, cost) and why per-case isolation is mandatory.
See [`tool-usage/RUNNER_CONTRACT.md`](tool-usage/RUNNER_CONTRACT.md) for current
fixture validation, safe action workspaces and cloud/compaction requirements.

Contributions of cases drawn from real multi-session agent runs are especially
welcome — those are the ones that find bugs.
