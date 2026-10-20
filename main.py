"""Run the Kaeru tool-usage benchmark."""

import argparse
from datetime import datetime
import logging
from pathlib import Path

from runner.build import prepare_runtime
from runner.fixtures import select_cases
from runner.isolation import find_native_binary
from runner.launch import launch
from runner.policy import MEMORY_POLICY


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Kaeru source checkout under test")
    parser.add_argument("--output", type=Path, default=Path("results") / datetime.now().strftime("%Y%m%d-%H%M%S-%f"),
                        help="results directory (default: results/<timestamp>)")
    parser.add_argument("--dataset", type=Path, default=Path(__file__).parent / "tool-usage/cases")
    parser.add_argument("--case", action="append", dest="cases", help="case to run; repeat to select several")
    parser.add_argument("--model", default="gpt-6.1-sol")
    parser.add_argument("--effort", default="low", choices=["minimal", "low", "medium", "high", "xhigh"])
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=900, help="seconds per agent turn")
    parser.add_argument("--prepare-only", action="store_true", help="check fixtures without model calls")
    parser.add_argument("--memory-policy", choices=["required", "none"], default="required")
    parser.add_argument("--memory-guide", type=Path,
                        help="supply a reusable tool guide to every turn; recorded as a separate condition")
    parser.add_argument("--isolation", choices=["bubblewrap", "host"], default="bubblewrap")
    parser.add_argument("--agent", default="codex", help="Codex CLI executable")
    parser.add_argument("--native-binary", type=Path, help="override native Codex executable detection")
    parser.add_argument("--binary", type=Path, help="use an existing MCP binary instead of building it")
    parser.add_argument("--cloud-binary", type=Path, help="use an existing cloud binary")
    parser.add_argument("--helper", type=Path, help="use an existing fixture helper")
    config = parser.parse_args(argv)
    if config.repetitions < 1 or config.timeout <= 0:
        parser.error("repetitions and timeout must be positive")
    for key in ("source", "output", "dataset", "binary", "cloud_binary", "helper", "native_binary", "memory_guide"):
        value = getattr(config, key)
        if value is not None:
            setattr(config, key, value.resolve())
    if config.output.exists():
        parser.error("output directory already exists; choose a new run directory")
    if not (config.source / "kaeru-core/Cargo.toml").is_file():
        parser.error("source must be a Kaeru checkout containing kaeru-core")
    if not config.dataset.is_dir():
        parser.error("dataset directory does not exist")
    for key in ("binary", "cloud_binary", "helper", "native_binary"):
        value = getattr(config, key)
        if value is not None and not value.is_file():
            parser.error(f"{key} does not exist")
    config.policy = MEMORY_POLICY if config.memory_policy == "required" else None
    if config.memory_guide is not None:
        if not config.policy:
            parser.error("memory-guide requires memory-policy required")
        try:
            guide = config.memory_guide.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            parser.error(f"cannot read memory-guide: {error}")
        if not guide.strip():
            parser.error("memory-guide must not be empty")
        config.policy += "\n\nKaeru operating guide; use live tool schemas for signatures.\n\n" + guide
    return config


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    config = parse_args(argv)
    cases = select_cases(config.dataset, config.cases)
    if not config.prepare_only and config.isolation == "bubblewrap" and not config.native_binary:
        config.native_binary = find_native_binary(config.agent)
    prepare_runtime(config, cases)
    result = launch(config)
    eligible = {"PREPARED"} if config.prepare_only else {"EXECUTED"}
    return 0 if set(result["status_counts"]).issubset(eligible) else 1


if __name__ == "__main__":
    raise SystemExit(main())
