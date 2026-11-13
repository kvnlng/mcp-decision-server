"""Tests for dmn.py: DMN decision tables, the subset the framework uses."""
# Test names say what they check.
# pylint: disable=missing-function-docstring
from pathlib import Path

import pytest
from conftest import limit_dmn

from mcp_decision_server.dmn import DmnError, evaluate, load_table

TABLES = Path(__file__).parent / "dmn"


def test_first_hit():
    table = load_table(TABLES / "quality.dmn")
    assert table.name == "quality_threshold" and table.inputs == ["defect_rate"] and table.types == ["number"]
    assert table.outputs == ["allowed", "reason"] and table.hit_policy == "FIRST"
    assert evaluate(table, {"defect_rate": 0.03}) == {
        "outputs": {"allowed": False, "reason": "The defect rate is above 2%"}, "fired": ["r1"]}
    assert evaluate(table, {"defect_rate": 0.01}) == {"outputs": {"allowed": True, "reason": "Within the limit"},
                                                     "fired": ["r2"]}


@pytest.mark.parametrize("inputs, fired", [
    ({"size": 4.9, "grade": "B", "count": 3}, "small"),
    ({"size": 5, "grade": "A", "count": 4}, "large"),
    ({"size": 1, "grade": "C", "count": 3}, "graded"),
    ({"size": 100, "grade": "A", "count": 3}, "three"),
])
def test_ranges_lists_and_not(inputs, fired):
    assert evaluate(load_table(TABLES / "forms.dmn"), inputs)["fired"] == [fired]


def test_collect_returns_every_match():
    result = evaluate(load_table(TABLES / "collect.dmn"), {"days": 6})
    assert result == {"outputs": [{"flag": "late"}, {"flag": "very late"}], "fired": ["late", "very_late"]}
    assert evaluate(load_table(TABLES / "collect.dmn"), {"days": 0}) == {"outputs": [], "fired": []}


def test_unique_with_two_matches_is_an_error():
    with pytest.raises(DmnError, match=r"quality_threshold.*r1.*r2"):
        evaluate(load_table(TABLES / "overlap.dmn"), {"defect_rate": 0.03})


def test_no_matching_rule_is_an_error():
    with pytest.raises(DmnError, match=r"quality_threshold: no rule matches .*defect_rate.*0\.01"):
        evaluate(load_table(TABLES / "gap.dmn"), {"defect_rate": 0.01})


def test_a_missing_input_is_named():
    with pytest.raises(DmnError, match="defect_rate"):
        evaluate(load_table(TABLES / "quality.dmn"), {})


def test_an_unsupported_expression_is_refused_at_load():
    with pytest.raises(DmnError, match=r'unsupported.dmn rule r1: unsupported expression "date\("2026-01-01"\)"'):
        load_table(TABLES / "unsupported.dmn")


@pytest.mark.parametrize("table, problem", [
    (limit_dmn("not()"), r'rule fine: unsupported expression "not\(\)"'),
    (limit_dmn("not(-)"), r'rule fine: unsupported expression "not\(-\)"'),
    (limit_dmn("[5..1]"), r'rule fine: unsupported expression "\[5\.\.1\]"'),
    (limit_dmn().replace("<text>true</text>", "<text></text>"), r"rule fine: empty entry"),
], ids=["not", "not_dash", "backwards_range", "empty_output"])
def test_a_bad_entry_is_refused_at_load(tmp_path, table, problem):
    (tmp_path / "bad.dmn").write_text(table, encoding="utf-8")
    with pytest.raises(DmnError, match="bad.dmn " + problem):
        load_table(tmp_path / "bad.dmn")


def test_a_number_test_on_text_is_an_error():
    with pytest.raises(DmnError, match="quality_threshold: defect_rate must be a number, not '0.9'"):
        evaluate(load_table(TABLES / "quality.dmn"), {"defect_rate": "0.9"})


def test_a_number_test_on_text_names_its_own_input_when_another_holds_the_same_text():
    with pytest.raises(DmnError, match="count must be a number, not 'B'"):
        evaluate(load_table(TABLES / "forms.dmn"), {"size": 50, "grade": "B", "count": "B"})


def test_a_collect_aggregation_is_refused_at_load(tmp_path):
    table = (TABLES / "collect.dmn").read_text(encoding="utf-8").replace(
        'hitPolicy="COLLECT"', 'hitPolicy="COLLECT" aggregation="SUM"')
    (tmp_path / "sum.dmn").write_text(table, encoding="utf-8")
    with pytest.raises(DmnError, match="^sum.dmn: COLLECT aggregation SUM is not supported"):
        load_table(tmp_path / "sum.dmn")


def _write(tmp_path, text: str) -> Path:
    (tmp_path / "bad.dmn").write_text(text, encoding="utf-8")
    return tmp_path / "bad.dmn"


@pytest.mark.parametrize("language", ["feel", "FEEL", "https://www.omg.org/spec/DMN/20230324/FEEL/",
                                      "http://www.omg.org/spec/DMN/20180521/FEEL/",
                                      "http://www.omg.org/spec/FEEL/20140401"])
def test_feel_in_any_spelling_is_accepted(tmp_path, language):
    table = limit_dmn().replace('namespace="t"', f'namespace="t" expressionLanguage="{language}"')
    assert load_table(_write(tmp_path, table)).name == "share_limit"


@pytest.mark.parametrize("where", ["definitions", "inputEntry", "outputEntry", "inputExpression"])
def test_another_expression_language_is_refused_wherever_it_is_named(tmp_path, where):
    table = limit_dmn()
    if where == "definitions":
        table = table.replace('namespace="t"', 'namespace="t" expressionLanguage="javascript"')
    else:
        table = table.replace(f"<{where}", f'<{where} expressionLanguage="javascript"', 1)
    with pytest.raises(DmnError, match=r"^bad.dmn: .*expression language javascript; only FEEL"):
        load_table(_write(tmp_path, table))


def test_a_decision_that_requires_another_decision_is_refused(tmp_path):
    table = limit_dmn().replace(
        '<decisionTable', '<informationRequirement><requiredDecision href="other.dmn#region"/>'
        '</informationRequirement><decisionTable')
    with pytest.raises(DmnError, match=r"^bad.dmn: decision share_limit requires decision other.dmn#region"):
        load_table(_write(tmp_path, table))


def _defaults(table: str, allowed: str | None = "true", reason: str | None = '"No rule matched"') -> str:
    for name, value in (("allowed", allowed), ("reason", reason)):
        if value is not None:
            kind = "boolean" if name == "allowed" else "string"
            table = table.replace(f'<output id="o{1 if name == "allowed" else 2}" name="{name}" typeRef="{kind}"/>',
                                  f'<output id="o{1 if name == "allowed" else 2}" name="{name}" typeRef="{kind}">'
                                  f"<defaultOutputEntry><text>{value}</text></defaultOutputEntry></output>")
    return table


def test_default_output_entries_answer_when_no_rule_matches(tmp_path):
    table = load_table(_write(tmp_path, _defaults(limit_dmn())))
    assert evaluate(table, {"share": 0.7}) == {"outputs": {"allowed": True, "reason": "No rule matched"},
                                               "fired": ["default"]}
    assert table.rules[-1].entries == ("-",) and table.rules[-1].values == (True, "No rule matched")
    assert evaluate(table, {"share": 0.95})["fired"] == ["too_much"]


def test_a_default_on_only_some_outputs_is_refused(tmp_path):
    with pytest.raises(DmnError, match=r"^bad.dmn: output reason has no default output entry; give every output "
                                       "one, or none"):
        load_table(_write(tmp_path, _defaults(limit_dmn(), reason=None)))


def test_a_default_under_collect_is_refused(tmp_path):
    table = _defaults(limit_dmn()).replace('<decisionTable id="t">', '<decisionTable id="t" hitPolicy="COLLECT">')
    with pytest.raises(DmnError, match=r"^bad.dmn: default output entries are not supported under COLLECT"):
        load_table(_write(tmp_path, table))


def test_several_unnamed_outputs_are_refused(tmp_path):
    table = limit_dmn().replace(' name="allowed"', "").replace(' name="reason"', "")
    with pytest.raises(DmnError, match=r"^bad.dmn: every output needs a name"):
        load_table(_write(tmp_path, table))


def test_text_in_a_number_column_is_an_error_even_when_the_default_would_answer(tmp_path):
    table = _defaults(limit_dmn()).replace(
        '<input id="i">', '<input id="r"><inputExpression typeRef="string"><text>region</text></inputExpression>'
        '</input><input id="i">').replace("<rule id=\"too_much\">", '<rule id="too_much"><inputEntry><text>"B"</text>'
        "</inputEntry>").replace('<rule id="fine">', '<rule id="fine"><inputEntry><text>"B"</text></inputEntry>')
    loaded = load_table(_write(tmp_path, table))
    assert evaluate(loaded, {"region": "A", "share": 0.5})["fired"] == ["default"]
    with pytest.raises(DmnError, match="share_limit: share must be a number, not 'abc'"):
        evaluate(loaded, {"region": "A", "share": "abc"})


def test_defaults_answer_under_first(tmp_path):
    table = _defaults(limit_dmn()).replace('<decisionTable id="t">', '<decisionTable id="t" hitPolicy="FIRST">')
    assert evaluate(load_table(_write(tmp_path, table)), {"share": 0.7})["fired"] == ["default"]


def test_empty_default_entries_are_no_defaults(tmp_path):
    table = load_table(_write(tmp_path, _defaults(limit_dmn(), allowed="", reason="")))
    assert not any(rule.default for rule in table.rules)


def test_a_rule_named_default_is_refused_when_the_table_has_defaults(tmp_path):
    table = _defaults(limit_dmn()).replace('<rule id="fine">', '<rule id="default">')
    with pytest.raises(DmnError, match="^bad.dmn: rule id default is kept for the default outputs"):
        load_table(_write(tmp_path, table))


def test_two_outputs_with_one_name_are_refused(tmp_path):
    table = limit_dmn().replace('name="reason"', 'name="allowed"')
    with pytest.raises(DmnError, match="^bad.dmn: two outputs are named allowed"):
        load_table(_write(tmp_path, table))


def test_a_decision_with_two_tables_is_named_as_such(tmp_path):
    table = limit_dmn().replace("</decisionTable>", "</decisionTable><decisionTable id=\"t2\"/>")
    with pytest.raises(DmnError, match="^bad.dmn: decision share_limit has 2 decision tables"):
        load_table(_write(tmp_path, table))
