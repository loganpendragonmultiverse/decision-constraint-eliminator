import copy
import json

import pytest

from decision_constraint_eliminator.cli import main
from decision_constraint_eliminator.core import (
    counterfactual,
    eliminate,
    load_decision,
    render_markdown,
)


def decision(constraint, policy="ignore"):
    return {
        "version": 1,
        "missing_policy": policy,
        "options": [{"id": "a", "label": "A", "attributes": {}}],
        "constraints": [constraint],
    }


@pytest.mark.parametrize(
    "operator,value",
    [
        ("in", "PC"),
        ("not_in", {}),
        ("min", True),
        ("max", "50"),
        ("max", float("inf")),
        ("min", float("nan")),
        ("exists", "false"),
    ],
)
@pytest.mark.parametrize("policy", ["fail", "ignore", "unknown"])
def test_requirement_types_are_checked_before_missing_policies(operator, value, policy):
    data = decision({"id": "c", "field": "missing", "operator": operator, "value": value}, policy)
    original = copy.deepcopy(data)
    with pytest.raises((TypeError, ValueError)):
        eliminate(data)
    with pytest.raises((TypeError, ValueError)):
        counterfactual(data, ["c"])
    assert data["options"] == original["options"]


def test_invalid_requirement_cli_fails_before_writing(tmp_path, capsys):
    data = decision({"id": "c", "field": "missing", "operator": "in", "value": "PC"})
    source = tmp_path / "decision.json"
    source.write_text(json.dumps(data))
    before = source.read_bytes()
    output = tmp_path / "report.json"
    assert main([str(source), "--omit-constraint", "c", "--output", str(output)]) == 2
    assert not output.exists() and source.read_bytes() == before
    assert "Traceback" not in capsys.readouterr().err


def test_nonfinite_numeric_attributes_and_bool_values_rejected():
    data = decision({"id": "c", "field": "x", "operator": "max", "value": 5})
    for value in (float("nan"), float("inf"), True):
        data["options"][0]["attributes"]["x"] = value
        with pytest.raises(TypeError, match="finite numeric"):
            eliminate(data)


def test_large_integers_remain_valid_numbers():
    data = decision({"id": "c", "field": "x", "operator": "max", "value": 10**1000})
    data["options"][0]["attributes"]["x"] = 10**999
    assert eliminate(data)["surviving_count"] == 1


def test_optional_exists_false_default_retained():
    data = decision({"id": "c", "field": "missing", "operator": "exists"})
    assert eliminate(data)["surviving_count"] == 1
    data["constraints"][0]["value"] = True
    assert eliminate(data)["eliminated_count"] == 1


def test_literals_do_not_create_markup_or_extra_report_lines():
    data = decision(
        {
            "id": "c`<tag>\n# fake",
            "field": "x",
            "operator": "eq",
            "value": 1,
            "label": "<b>fail</b>\n# heading",
        }
    )
    data["options"][0].update(id="a`\n# heading", label="<span hidden>Option</span>\n# fake")
    before = copy.deepcopy(data)
    report = counterfactual(data, [data["constraints"][0]["id"]])
    markdown = render_markdown(report)
    assert "<span" not in markdown and "<b>" not in markdown and "<tag>" not in markdown
    assert "&lt;span hidden&gt;" in markdown and "&#10;" in markdown and "&#96;" in markdown
    assert "\n# fake" not in markdown and "Hypothetical" in markdown
    assert data == before and report["matrix"][0]["label"] == data["options"][0]["label"]


@pytest.mark.parametrize("operator", [[], {}, None])
def test_invalid_operator_shapes_raise_useful_validation(operator):
    with pytest.raises(ValueError, match="supported operator"):
        eliminate(decision({"id": "c", "field": "x", "operator": operator}))


def test_loader_rejects_invalid_requirements_even_when_missing(tmp_path):
    source = tmp_path / "decision.json"
    source.write_text(
        json.dumps(decision({"id": "c", "field": "x", "operator": "not_in", "value": "PC"}))
    )
    with pytest.raises(TypeError, match="must be a list"):
        load_decision(source)
