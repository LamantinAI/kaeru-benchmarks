#!/usr/bin/env python3
"""Export per-case JSON results to a UTF-8 CSV table for a recorded run."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

METRICS = (
    'native_turns', 'kaeru_tool_calls', 'input_tokens', 'cached_input_tokens',
    'cache_write_input_tokens', 'output_tokens', 'reasoning_output_tokens',
)
FIELDS = (
    'run_id', 'case_id', 'status', 'failure_group', 'dataset_commit',
    'kaeru_version', 'model', 'reasoning_effort', 'repetition',
    *METRICS, 'phase_results', 'currency', 'grading_rationale', 'limitations',
    'result_file',
)


def export(run: Path) -> int:
    info = json.loads((run / 'run-info.json').read_text())
    paths = sorted(run.glob('cases/*/result.json'))
    if not paths:
        raise ValueError('No per-case result.json files found')
    rows = []
    for path in paths:
        result = json.loads(path.read_text())
        row = {key: result[key] for key in FIELDS if key in result}
        row.update({key: result['metrics'][key] for key in METRICS})
        row.update(run_id=info['run_id'],
                   failure_group=result.get('failure_group', ''),
                   result_file=path.relative_to(run).as_posix())
        rows.append(row)
    with (run / 'results.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    # Keep an existing evidence manifest valid after regenerating the table.
    manifest = run / 'SHA256SUMS'
    if manifest.exists():
        files = sorted(p for p in run.rglob('*') if p.is_file() and p != manifest)
        manifest.write_text(''.join(
            f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(run).as_posix()}\n'
            for p in files
        ))
    return len(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    args = parser.parse_args()
    print(f'Exported {export(args.run_directory)} cases to results.csv')
