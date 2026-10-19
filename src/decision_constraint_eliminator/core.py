from __future__ import annotations

import html
import json
import math
import re
from pathlib import Path
from typing import Any

OPERATORS = {"eq", "ne", "in", "not_in", "min", "max", "contains", "exists"}


def load_decision(path: Path) -> dict[str, Any]:
    return _validate_decision(json.loads(path.read_text(encoding="utf-8")))


def _validate_decision(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("decision must be a version 1 object")
    options, constraints = data.get("options"), data.get("constraints")
    if data.get("missing_policy", "fail") not in ("fail", "ignore", "unknown"):
        raise ValueError("missing_policy must be fail, ignore, or unknown")
    if not isinstance(options, list) or not options:
        raise TypeError("options must be a non-empty list")
    if not isinstance(constraints, list):
        raise TypeError("constraints must be a list")
    seen: set[str] = set()
    for option in options:
        if (
            not isinstance(option, dict)
            or not isinstance(option.get("id"), str)
            or not isinstance(option.get("label"), str)
            or not isinstance(option.get("attributes"), dict)
        ):
            raise TypeError("each option requires string id, label, and object attributes")
        if option["id"] in seen:
            raise ValueError(f"duplicate option id: {option['id']}")
        seen.add(option["id"])
    constraint_ids: set[str] = set()
    for constraint in constraints:
        if (
            not isinstance(constraint, dict)
            or not isinstance(constraint.get("id"), str)
            or not isinstance(constraint.get("field"), str)
            or not isinstance(constraint.get("operator"), str)
            or constraint["operator"] not in OPERATORS
        ):
            raise ValueError("each constraint requires id, field, and a supported operator")
        if not constraint["id"] or constraint["id"] in constraint_ids:
            raise ValueError("constraint ids must be non-empty and unique")
        constraint_ids.add(constraint["id"])
        if constraint["operator"] != "exists" and "value" not in constraint:
            raise ValueError(f"constraint {constraint['id']} requires a value")
        operator, value = constraint["operator"], constraint.get("value")
        if operator in {"in", "not_in"} and not isinstance(value, list):
            raise TypeError(f"constraint {constraint['id']} {operator} value must be a list")
        if operator in {"min", "max"} and not _finite_number(value):
            raise TypeError(f"constraint {constraint['id']} requires finite numeric values")
        if operator == "exists" and "value" in constraint and not isinstance(value, bool):
            raise TypeError(f"constraint {constraint['id']} exists value must be a boolean")
    return data


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and (not isinstance(value, float) or math.isfinite(value))
    )


def _passes(attributes: dict[str, Any], constraint: dict[str, Any]) -> bool:
    field, operator = constraint["field"], constraint["operator"]
    present = field in attributes
    actual = attributes.get(field)
    expected = constraint.get("value")
    if operator == "exists":
        return present == bool(expected)
    if not present:
        return False
    if operator == "eq":
        return actual == expected
    if operator == "ne":
        return actual != expected
    if operator == "in":
        if not isinstance(expected, list):
            raise TypeError(f"constraint {constraint['id']} in value must be a list")
        return actual in expected
    if operator == "not_in":
        if not isinstance(expected, list):
            raise TypeError(f"constraint {constraint['id']} not_in value must be a list")
        return actual not in expected
    if operator in {"min", "max"}:
        if not _finite_number(actual) or not _finite_number(expected):
            raise TypeError(f"constraint {constraint['id']} requires finite numeric values")
        return actual >= expected if operator == "min" else actual <= expected
    if operator == "contains":
        if not isinstance(actual, (str, list)):
            raise TypeError(
                f"constraint {constraint['id']} contains requires a string or list attribute"
            )
        return expected in actual
    raise ValueError(f"unsupported operator: {operator}")


def eliminate(data: dict[str, Any]) -> dict[str, Any]:
    data = _validate_decision(data)
    policy = data.get("missing_policy", "fail")
    surviving, eliminated, unknown, matrix = [], [], [], []
    for option in data["options"]:
        failures, unresolved, checks = [], [], []
        for constraint in data["constraints"]:
            missing = (
                constraint["field"] not in option["attributes"]
                and constraint["operator"] != "exists"
            )
            state = (
                "ignored"
                if missing and policy == "ignore"
                else "unknown"
                if missing and policy == "unknown"
                else "pass"
                if _passes(option["attributes"], constraint)
                else "fail"
            )
            evidence = {
                "constraint": constraint["id"],
                "label": constraint.get("label", constraint["id"]),
                "field": constraint["field"],
                "state": state,
            }
            checks.append(evidence)
            if state == "fail":
                failures.append(evidence)
            elif state == "unknown":
                unresolved.append(evidence)
        classification = "eliminated" if failures else "unknown" if unresolved else "surviving"
        matrix.append(
            {
                "id": option["id"],
                "label": option["label"],
                "classification": classification,
                "checks": checks,
            }
        )
        if failures:
            eliminated.append({"id": option["id"], "label": option["label"], "failures": failures})
        elif unresolved:
            unknown.append({"id": option["id"], "label": option["label"], "unknown": unresolved})
        else:
            surviving.append(option)
    return {
        "version": 1,
        "surviving_count": len(surviving),
        "eliminated_count": len(eliminated),
        "unknown_count": len(unknown),
        "missing_policy": policy,
        "surviving": surviving,
        "eliminated": eliminated,
        "unknown": unknown,
        "matrix": matrix,
    }


def counterfactual(data: dict[str, Any], omitted: list[str]) -> dict[str, Any]:
    """Retain the full result and compare explicit hypothetical omissions."""
    data = _validate_decision(data)
    ids = [constraint["id"] for constraint in data["constraints"]]
    if (
        not isinstance(omitted, list)
        or not omitted
        or any(not isinstance(value, str) or value not in ids for value in omitted)
        or len(set(omitted)) != len(omitted)
    ):
        raise ValueError("omitted constraints must be known, unique ids in a non-empty list")
    original = eliminate(data)
    relaxed = eliminate(
        {**data, "constraints": [c for c in data["constraints"] if c["id"] not in omitted]}
    )
    original["counterfactual"] = {
        "hypothetical": True,
        "omitted_constraints": omitted.copy(),
        "relaxed": relaxed,
        "eligibility_changes": [
            {
                "id": before["id"],
                "original": before["classification"],
                "hypothetical": after["classification"],
            }
            for before, after in zip(original["matrix"], relaxed["matrix"])
            if before["classification"] != after["classification"]
        ],
    }
    return original


def _literal(value: Any) -> str:
    text = html.escape(str(value), quote=False)
    text = re.sub(r"([\\*_{}\[\]()#+!|~\-])", r"\\\1", text)
    return text.replace("\r", "&#13;").replace("\n", "&#10;").replace("`", "&#96;")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Decision Constraint Report",
        "",
        f"**{report['surviving_count']} surviving · {report['eliminated_count']} eliminated · {report['unknown_count']} unknown**",
        "",
        "## Surviving",
        "",
    ]
    lines.extend(
        f"- **{_literal(item['label'])}** ({_literal(item['id'])})" for item in report["surviving"]
    )
    if report["eliminated"]:
        lines.extend(["", "## Eliminated", ""])
        for item in report["eliminated"]:
            lines.append(f"- **{_literal(item['label'])}** ({_literal(item['id'])})")
            lines.extend(f"  - {_literal(failure['label'])}" for failure in item["failures"])
    if report["unknown"]:
        lines.extend(["", "## Unknown", ""])
        for item in report["unknown"]:
            lines.append(f"- **{_literal(item['label'])}** ({_literal(item['id'])})")
            lines.extend(
                f"  - {_literal(check['label'])} (missing field)" for check in item["unknown"]
            )
    lines.extend(["", "## Complete Matrix", ""])
    for item in report["matrix"]:
        states = ", ".join(
            f"{_literal(check['constraint'])}={check['state']}" for check in item["checks"]
        )
        lines.append(
            f"- **{_literal(item['label'])}**: {item['classification']} — {states or 'no constraints'}"
        )
    if "counterfactual" in report:
        scenario = report["counterfactual"]
        lines.extend(
            [
                "",
                "## Hypothetical constraint omission",
                "",
                "Omitted: "
                + ", ".join(_literal(value) for value in scenario["omitted_constraints"]),
                "",
                "All eligibility below is hypothetical; options remain unranked.",
                "",
            ]
        )
        relaxed_text = render_markdown(scenario["relaxed"])
        lines.append(
            relaxed_text.replace("# Decision Constraint Report", "### Hypothetical result")
            .replace("## Surviving", "### Hypothetical survivors")
            .replace("## Eliminated", "### Hypothetically eliminated")
            .replace("## Unknown", "### Hypothetically unknown")
            .replace("## Complete Matrix", "### Hypothetical matrix")
        )
    return "\n".join(lines).rstrip() + "\n"
