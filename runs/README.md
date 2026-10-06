# Recorded runs

Completed experiments live in dated directories. Each record identifies the
system, model, dataset revision, conditions, outcomes, qualifications and evidence
scope. Later experiments use new directories rather than replacing earlier
results. Dataset commit references identify the fixtures actually evaluated; do not copy
the dataset into individual run directories.

## Directory naming

Use this format for every recorded run:

```text
YYYY-MM-DD__<suite>__kaeru-<version>__<model>__<effort>__run-NN
```

Example:

```text
2026-10-05__tool-usage__kaeru-0.7.5__gpt-6-luna__low__run-01
```

- Date: execution start date in UTC, not the packaging or publication date.
- Suite: its repository identifier, such as `tool-usage`.
- Version: the Kaeru version under test; exact source and binary hashes belong
  in `run-info.json`.
- Model: the exact model identifier used by the runner, in lowercase.
- Effort: the configured reasoning effort, in lowercase; use `default` when
  unspecified and `na` when the setting is not applicable.
- Sequence: a two-digit counter starting at `01` for each identical combination
  of the preceding fields. A distinct execution gets the next number; it never
  replaces a previous record. This counter is not the number of repetitions
  within an experiment.

Double underscores separate fields; hyphens are allowed inside a field.
Use lowercase ASCII letters, digits, dots and hyphens inside fields. If an exact
model identifier contains other characters, replace them with hyphens in the
folder name and retain the exact identifier in `run-info.json`.

Conditions, prompt policies, dataset hashes, repetitions and outcomes belong in
metadata and the report. Do not put `pass`, `fail`, `final`, `new` or `rerun` in
directory names. Once a record is published, keep its identifier stable.

## Tabular data

Each run includes `results.csv`: one row per case, in UTF-8 with a header,
comma separators and standard CSV quoting. Numeric metrics are numeric values;
blank `failure_group` means that the case is outside the FAIL classification.
Partial outcomes retain their full status and qualifications. Failure groups
are stored in the per-case result JSON.

Per-case `cases/<id>/result.json` files are the source of truth. The CSV is a
flattened export for filtering, plotting and comparing runs; `results.md` is a
readable view. Do not edit the CSV independently. Regenerate it from the
repository root with:

```sh
python3 runs/export_results.py runs/<run-id>
```

The exporter also refreshes the run's checksum manifest if one exists.
Input tokens include cached input tokens; reasoning output is a reported
component of output, not an additional cost to add to it.

## Index

| Run | Suite | Result |
|---|---|---|
| [2026-10-05: Kaeru 0.7.5 / GPT-6-Luna low](2026-10-05__tool-usage__kaeru-0.7.5__gpt-6-luna__low__run-01/) | tool-usage, 27 cases, N=1 | 3 PASS, 22 FAIL, 2 partly confounded; 21 cases without Kaeru calls |
