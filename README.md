# Decision Constraint Eliminator

> ⭐ **Gold Star Project — v1.2.1**
> I consider this project complete. Fixes, maintenance and good new ideas are still welcome.
> [About Gold Stars](https://www.loganpendragonforge.com/open-source/?gold=1)
>
> Filter supplied decision options against explicit hard constraints and review unranked outcomes with complete evidence.

[![CI](https://github.com/loganpendragonmultiverse/decision-constraint-eliminator/actions/workflows/ci.yml/badge.svg)](https://github.com/loganpendragonmultiverse/decision-constraint-eliminator/actions/workflows/ci.yml)

Decision Constraint Eliminator removes options that violate explicit hard requirements before preferences are compared. Every eliminated option retains the exact failed constraints, while surviving options remain unranked.

## Three-minute start

```bash
python -m pip install .
constraint-eliminator examples/decision.json
constraint-eliminator examples/decision.json --format json
```

Version 1.1 supports equality, inequality, membership, exclusion, numeric minimum and maximum, containment, and field-presence constraints. It emits a complete option-versus-constraint matrix. Set `missing_policy` to `fail` (default), `ignore`, or `unknown`; the last keeps incomplete options visibly separate instead of eliminating them. Inputs are validated and reports are deterministic.

The tool does not decide which requirements should be hard, score preferences, recommend a winner, or infer missing attributes. A surviving option only satisfies the supplied constraints under the selected missing-field policy. Requires Python 3.10 or newer.

Part of the [Logan Pendragon Forge open-source collection](https://www.loganpendragonforge.com/open-source/). Licensed under the [MIT License](LICENSE).

## Hypothetical omissions

`constraint-eliminator examples/decision.json --omit-constraint budget --format json`
compares the original decision with a scenario that omits the named constraint.
Repeat `--omit-constraint ID` for multiple constraints. Unknown or repeated IDs reject;
constraint IDs must be non-empty and unique. The original full matrix and eligibility
remain at the top level. The `counterfactual` object contains the omitted IDs, the
hypothetical relaxed report and eligibility changes. Markdown explicitly labels the
relaxed survivors hypothetical. No options are ranked or recommended and the input
is unchanged. Missing-field fail/ignore/unknown policies apply independently to both
matrices. Ordinary calls retain their existing report structure.

## 1.2.1 input, output and installation

Configured requirements are validated before missing-field policy or hypothetical omission evaluation: `in`/`not_in` require list values, `min`/`max` require finite numbers (booleans are not numbers), and an explicit `exists` value must be boolean. An omitted `exists` value retains its existing false default. Numeric attributes checked by minimum/maximum must also be finite numbers. Missing fields still follow `fail`, `ignore` or `unknown` only after the requirement is valid. Markdown displays authored labels and IDs literally; JSON retains exact strings.

Reports require a new path. Existing files, directories and symlinks, including dangling symlinks and aliases to the input, are refused. Exclusive creation also refuses a file that appears immediately before writing. Invalid input and ordinary file, encoding or terminal-output failures return status 2. A failed write can leave a partial new report; inspect it and retry at a new path. No power-loss or concurrent-writer transaction is promised. Inputs and existing destinations are never rewritten.

Download the wheel or source archive from the GitHub release and install its actual filename with `python -m pip install /path/to/downloaded-file`. Run the command with `--help` to check installation. Both package formats include README, DEVELOPMENT, TESTING, CHANGELOG, license and the supplied JSON example; wheel installs place these under `share/doc/decision-constraint-eliminator` in the environment. This remains a local tool without telemetry or network calls.
