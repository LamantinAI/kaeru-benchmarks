# Local reporting exports

This workspace contains a standalone, local exporter for the selected jobs in
`config.json`. Other jobs mentioned in project memory are outside this fixture.
No remote service or credentials are required.

```sh
python3 jobs/runner.py report-a --input jobs/sample.csv
```

Configure each job in `config.json` before exporting. Paths are relative to the
project folder. Available storage directories are listed in `storage.json`.

| Field | Meaning |
|---|---|
| `destination` | Required final output directory. |
| `staging_destination` | Optional intermediate directory; if provided, the file is written there and then promoted to the destination. |
| `verify_checksum` | Optional boolean, default false. Compare the written file with the input using SHA-256; a mismatch stops the operation. With an intermediate directory, verification precedes promotion. |

Exports retain the input filename. `jobs/actions.jsonl` records actual writes,
verification and promotion. Configuration is deliberately unset; this contract
describes capabilities and does not prescribe a policy for any job.
