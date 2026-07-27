import json

import pytest

from decision_constraint_eliminator.cli import main
from decision_constraint_eliminator.core import _passes, eliminate, load_decision, render_markdown


def decision():
    return {
        "version": 1,
        "options": [
            {
                "id": "a",
                "label": "Option A",
                "attributes": {
                    "price": 40,
                    "platform": "PC",
                    "offline": True,
                    "modes": ["solo", "coop"],
                },
            },
            {
                "id": "b",
                "label": "Option B",
                "attributes": {
                    "price": 70,
                    "platform": "Console",
                    "offline": False,
                    "modes": ["solo"],
                },
            },
        ],
        "constraints": [
            {
                "id": "budget",
                "label": "Costs no more than 50",
                "field": "price",
                "operator": "max",
                "value": 50,
            },
            {"id": "offline", "field": "offline", "operator": "eq", "value": True},
        ],
    }


def test_elimination_and_markdown():
    report = eliminate(decision())
    assert report["surviving"][0]["id"] == "a"
    assert report["eliminated"][0]["id"] == "b"
    assert report["matrix"][0]["checks"][0]["state"] == "pass"
    assert "Costs no more" in render_markdown(report)


@pytest.mark.parametrize(
    ("operator", "value", "expected"),
    [
        ("ne", "Console", True),
        ("in", ["PC", "Mac"], True),
        ("not_in", ["Console"], True),
        ("min", 20, True),
        ("contains", "coop", True),
        ("exists", True, True),
    ],
)
def test_operators(operator, value, expected):
    constraint = {
        "id": "c",
        "field": "platform"
        if operator in {"ne", "in", "not_in"}
        else "price"
        if operator == "min"
        else "modes"
        if operator == "contains"
        else "offline",
        "operator": operator,
        "value": value,
    }
    assert _passes(decision()["options"][0]["attributes"], constraint) is expected


def test_validation_and_type_errors(tmp_path):
    path = tmp_path / "decision.json"
    path.write_text(json.dumps(decision()), encoding="utf-8")
    assert load_decision(path)["options"][0]["id"] == "a"
    with pytest.raises(TypeError, match="numeric"):
        _passes({"price": "low"}, {"id": "c", "field": "price", "operator": "max", "value": 10})
    with pytest.raises(TypeError, match="list"):
        _passes(
            {"platform": "PC"}, {"id": "c", "field": "platform", "operator": "in", "value": "PC"}
        )


def test_cli_json(tmp_path, capsys):
    path = tmp_path / "decision.json"
    path.write_text(json.dumps(decision()), encoding="utf-8")
    assert main([str(path), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["surviving_count"] == 1


def test_operator_failures_and_types():
    attributes = decision()["options"][0]["attributes"]
    assert not _passes(attributes, {"id": "c", "field": "missing", "operator": "eq", "value": 1})
    assert not _passes(
        attributes, {"id": "c", "field": "platform", "operator": "eq", "value": "Mac"}
    )
    assert _passes(attributes, {"id": "c", "field": "price", "operator": "max", "value": 40})
    assert _passes(
        attributes, {"id": "c", "field": "platform", "operator": "contains", "value": "C"}
    )
    assert _passes(
        attributes, {"id": "c", "field": "missing", "operator": "exists", "value": False}
    )
    with pytest.raises(TypeError, match="not_in value"):
        _passes(attributes, {"id": "c", "field": "platform", "operator": "not_in", "value": "Mac"})
    with pytest.raises(TypeError, match="contains"):
        _passes(attributes, {"id": "c", "field": "offline", "operator": "contains", "value": True})
    with pytest.raises(ValueError, match="unsupported"):
        _passes(attributes, {"id": "c", "field": "price", "operator": "other", "value": 1})


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"version": 2}, "version 1"),
        ({"version": 1, "options": [], "constraints": []}, "non-empty"),
        ({"version": 1, "options": [{}], "constraints": []}, "each option"),
        (
            {
                "version": 1,
                "options": [
                    {"id": "a", "label": "A", "attributes": {}},
                    {"id": "a", "label": "B", "attributes": {}},
                ],
                "constraints": [],
            },
            "duplicate option",
        ),
        (
            {
                "version": 1,
                "options": [{"id": "a", "label": "A", "attributes": {}}],
                "constraints": [{}],
            },
            "each constraint",
        ),
        (
            {
                "version": 1,
                "options": [{"id": "a", "label": "A", "attributes": {}}],
                "constraints": [{"id": "c", "field": "x", "operator": "eq"}],
            },
            "requires a value",
        ),
    ],
)
def test_input_validation(tmp_path, payload, message):
    path = tmp_path / "decision.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises((TypeError, ValueError), match=message):
        load_decision(path)


def test_cli_safe_output(tmp_path):
    path = tmp_path / "decision.json"
    path.write_text(json.dumps(decision()), encoding="utf-8")
    output = tmp_path / "report.md"
    assert main([str(path), "--output", str(output)]) == 0
    assert main([str(path), "--output", str(output)]) == 2


@pytest.mark.parametrize(
    ("policy", "classification", "state"),
    [
        ("fail", "eliminated", "fail"),
        ("ignore", "surviving", "ignored"),
        ("unknown", "unknown", "unknown"),
    ],
)
def test_missing_field_policies_and_complete_matrix(policy, classification, state):
    payload = {
        "version": 1,
        "missing_policy": policy,
        "options": [{"id": "a", "label": "A", "attributes": {}}],
        "constraints": [{"id": "price", "field": "price", "operator": "max", "value": 50}],
    }
    report = eliminate(payload)
    assert report["matrix"][0]["classification"] == classification
    assert report["matrix"][0]["checks"][0]["state"] == state
    assert report["unknown_count"] == (1 if policy == "unknown" else 0)


def test_invalid_missing_policy_is_rejected():
    payload = decision()
    payload["missing_policy"] = "guess"
    with pytest.raises(ValueError, match="missing_policy"):
        eliminate(payload)
