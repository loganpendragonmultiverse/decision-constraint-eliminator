from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import counterfactual, eliminate, load_decision, render_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Eliminate options that violate explicit hard constraints."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--omit-constraint",
        action="append",
        metavar="ID",
        help="compare hypothetical eligibility without this constraint; repeat for multiple ids",
    )
    args = parser.parse_args(argv)
    try:
        data = load_decision(args.input)
        report = (
            counterfactual(data, args.omit_constraint)
            if args.omit_constraint is not None
            else eliminate(data)
        )
        rendered = (
            json.dumps(report, indent=2, ensure_ascii=False) + "\n"
            if args.format == "json"
            else render_markdown(report)
        )
        if args.output:
            if args.output.exists():
                raise ValueError(f"output already exists: {args.output}")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
