# Decision Constraint Eliminator

[![CI](https://github.com/loganpendragonmultiverse/decision-constraint-eliminator/actions/workflows/ci.yml/badge.svg)](https://github.com/loganpendragonmultiverse/decision-constraint-eliminator/actions/workflows/ci.yml)

Decision Constraint Eliminator removes options that violate explicit hard requirements before preferences are compared. Every eliminated option retains the exact failed constraints, while surviving options remain unranked.

## Three-minute start

```bash
python -m pip install .
constraint-eliminator examples/decision.json
constraint-eliminator examples/decision.json --format json
```

Version 1 supports equality, inequality, membership, exclusion, numeric minimum and maximum, containment, and field-presence constraints. Inputs are validated and reports are deterministic.

The tool does not decide which requirements should be hard, score preferences, recommend a winner, or compensate for incomplete attributes. A surviving option only satisfies the supplied constraints. Requires Python 3.10 or newer.

Part of the [Logan Pendragon Forge open-source collection](https://www.loganpendragonforge.com/open-source/). Licensed under the [MIT License](LICENSE).
