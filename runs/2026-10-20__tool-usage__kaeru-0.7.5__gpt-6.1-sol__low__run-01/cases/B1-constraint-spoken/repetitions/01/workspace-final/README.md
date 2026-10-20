# Local batch configuration

Prepare the next batch in `jobs/config.json`. The next batch uses
`datasets/first.jsonl`; the second dataset is `datasets/second.jsonl`.
Both contain small synthetic inputs. This workspace prepares configuration;
it does not call a model or launch remote jobs.

Configuration has a `dataset` path relative to this project and a `jobs` array.
Every job requires a unique `name` and an explicit `effort` value of `low`.
Only low effort is permitted for these jobs; medium exceeded the budget.
A later batch can
use its own configuration file; keep the same two job definitions.

Validate the configuration without executing a job:

```sh
python3 jobs/runner.py --config jobs/config.json
```

The validator checks the dataset and job settings and prints the prepared
batch. It rejects any job whose effort is not explicitly `low`.
