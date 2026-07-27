from __future__ import annotations

import json
from pathlib import Path
from typing import Any

OPERATORS = {"eq", "ne", "in", "not_in", "min", "max", "contains", "exists"}


def load_decision(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("decision must be a version 1 object")
    options, constraints = data.get("options"), data.get("constraints")
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
    for constraint in constraints:
        if (
            not isinstance(constraint, dict)
            or not isinstance(constraint.get("id"), str)
            or not isinstance(constraint.get("field"), str)
            or constraint.get("operator") not in OPERATORS
        ):
            raise ValueError("each constraint requires id, field, and a supported operator")
        if constraint["operator"] != "exists" and "value" not in constraint:
            raise ValueError(f"constraint {constraint['id']} requires a value")
    return data


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
        if (
            not isinstance(actual, (int, float))
            or isinstance(actual, bool)
            or not isinstance(expected, (int, float))
            or isinstance(expected, bool)
        ):
            raise TypeError(f"constraint {constraint['id']} requires numeric values")
        return actual >= expected if operator == "min" else actual <= expected
    if operator == "contains":
        if not isinstance(actual, (str, list)):
            raise TypeError(
                f"constraint {constraint['id']} contains requires a string or list attribute"
            )
        return expected in actual
    raise ValueError(f"unsupported operator: {operator}")


def eliminate(data: dict[str, Any]) -> dict[str, Any]:
    surviving, eliminated = [], []
    for option in data["options"]:
        failures = []
        for constraint in data["constraints"]:
            if not _passes(option["attributes"], constraint):
                failures.append(
                    {
                        "constraint": constraint["id"],
                        "label": constraint.get("label", constraint["id"]),
                        "field": constraint["field"],
                    }
                )
        if failures:
            eliminated.append({"id": option["id"], "label": option["label"], "failures": failures})
        else:
            surviving.append(option)
    return {
        "version": 1,
        "surviving_count": len(surviving),
        "eliminated_count": len(eliminated),
        "surviving": surviving,
        "eliminated": eliminated,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Decision Constraint Report",
        "",
        f"**{report['surviving_count']} surviving · {report['eliminated_count']} eliminated**",
        "",
        "## Surviving",
        "",
    ]
    lines.extend(f"- **{item['label']}** (`{item['id']}`)" for item in report["surviving"])
    if report["eliminated"]:
        lines.extend(["", "## Eliminated", ""])
        for item in report["eliminated"]:
            lines.append(f"- **{item['label']}** (`{item['id']}`)")
            lines.extend(f"  - {failure['label']}" for failure in item["failures"])
    return "\n".join(lines).rstrip() + "\n"
