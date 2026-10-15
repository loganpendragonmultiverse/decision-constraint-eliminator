import copy
import json

import pytest
from test_core_cli import decision

from decision_constraint_eliminator.cli import main
from decision_constraint_eliminator.core import (
    counterfactual,
    eliminate,
    load_decision,
    render_markdown,
)


def test_original_matrix_retained_and_only_affected_eligibility_changes():
    data = decision()
    data["options"].append({"id": "c", "label": "C", "attributes": {"price": 70, "offline": True}})
    before = copy.deepcopy(data)
    original = eliminate(data)
    report = counterfactual(data, ["budget"])
    assert {k: v for k, v in report.items() if k != "counterfactual"} == original
    scenario = report["counterfactual"]
    assert scenario["hypothetical"] is True
    assert scenario["eligibility_changes"] == [
        {"id": "c", "original": "eliminated", "hypothetical": "surviving"}
    ]
    assert [x["id"] for x in scenario["relaxed"]["surviving"]] == ["a", "c"]
    assert scenario["relaxed"]["eliminated"][0]["id"] == "b"
    assert data == before
    assert "Hypothetical survivors" in render_markdown(report)
    assert "counterfactual" not in eliminate(data)


@pytest.mark.parametrize("omitted", [["bad"], ["budget", "budget"], [], [None]])
def test_invalid_omissions_reject(omitted):
    with pytest.raises(ValueError, match="known, unique"):
        counterfactual(decision(), omitted)


@pytest.mark.parametrize(
    "policy, expected", [("fail", "eliminated"), ("ignore", "surviving"), ("unknown", "unknown")]
)
def test_missing_policies_remain_distinct(policy, expected):
    data = decision()
    data["missing_policy"] = policy
    data["options"] = [{"id": "x", "label": "X", "attributes": {}}]
    report = counterfactual(data, ["budget"])
    assert report["matrix"][0]["classification"] == expected
    assert report["counterfactual"]["relaxed"]["matrix"][0]["classification"] == expected
    assert len(report["matrix"][0]["checks"]) == 2
    assert len(report["counterfactual"]["relaxed"]["matrix"][0]["checks"]) == 1
    all_removed = counterfactual(data, ["budget", "offline"])
    assert all_removed["counterfactual"]["relaxed"]["surviving_count"] == 1


def test_duplicate_constraint_ids_reject_in_loader_and_api(tmp_path):
    data = decision()
    data["constraints"][1]["id"] = "budget"
    source = tmp_path / "decision.json"
    source.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="unique"):
        load_decision(source)
    with pytest.raises(ValueError, match="unique"):
        counterfactual(data, ["budget"])


def test_cli_default_and_hypothetical_roundtrip(tmp_path, capsys):
    source = tmp_path / "decision.json"
    source.write_text(json.dumps(decision()))
    before = source.read_bytes()
    assert main([str(source), "--format", "json"]) == 0
    assert "counterfactual" not in json.loads(capsys.readouterr().out)
    assert main([str(source), "--format", "json", "--omit-constraint", "budget"]) == 0
    assert json.loads(capsys.readouterr().out)["counterfactual"]["omitted_constraints"] == [
        "budget"
    ]
    assert main([str(source), "--omit-constraint", "unknown"]) == 2
    assert source.read_bytes() == before
