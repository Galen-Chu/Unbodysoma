"""Command line: run and validate scenario files.

python -m unbodysoma run scenarios/fear_response.toml --out runs/fear
python -m unbodysoma validate scenarios/*.toml
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from .config import ScenarioError, load_scenario, replay


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m unbodysoma", description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="run a scenario file")
    run.add_argument("scenario", type=Path)
    run.add_argument("--out", type=Path, help="write a run record to this directory")
    run.add_argument("--seed", type=int, help="override the scenario's seed")
    run.add_argument("--hours", type=float, help="override the scenario's duration")
    run.add_argument("--rerun", action="store_true", help="stream to a Rerun viewer (needs unbodysoma[viz])")
    run.add_argument("--rerun-save", type=Path, help="write a Rerun recording (.rrd) to this file")

    validate = commands.add_parser("validate", help="check scenario files without running them")
    validate.add_argument("scenarios", type=Path, nargs="+")

    again = commands.add_parser("replay", help="re-run a recorded scenario and check it reproduces exactly")
    again.add_argument("run", type=Path, help="a run record directory written by `run --out`")

    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            for path in args.scenarios:
                scenario = load_scenario(path)
                print(f"ok  {path}  ({scenario.preset}, {scenario.duration_s / 3600:.2f} h)")
            return 0

        if args.command == "replay":
            outcome = replay(args.run)
            for warning in outcome.warnings:
                print(f"warning: {warning}")
            print(f"{'identical' if outcome.identical else 'DIFFERENT'}: {outcome.detail}")
            return 0 if outcome.identical else 1

        scenario = load_scenario(args.scenario)
        if args.seed is not None:
            scenario = replace(scenario, seed=args.seed)
        if args.hours is not None:
            scenario = replace(scenario, duration_s=args.hours * 3600.0)
        try:
            result = scenario.run(out=args.out, rerun_spawn=args.rerun, rerun_save=args.rerun_save)
        except ImportError as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
    except ScenarioError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(result.summary())
    if args.out:
        print(f"run record  {args.out}")
    return 1 if result.stopped else 0


if __name__ == "__main__":
    sys.exit(main())
