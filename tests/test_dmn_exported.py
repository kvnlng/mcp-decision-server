"""Tests for dmn.py on DMN files exported by other tools (tests/dmn/exported/README.md says where each is from).

Each file is refused at load, naming why, or loads and answers: the TCK's models give the TCK's expected results, and
the others give what their rows say. None loads and then answers wrongly.
"""
# Test names say what they check.
# pylint: disable=missing-function-docstring
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree

import pytest

from mcp_decision_server.dmn import DmnError, evaluate, load_table
from mcp_decision_server.environment import ScenarioError, load_environment

EXPORTED = Path(__file__).parent / "dmn" / "exported"
_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"


def _local(element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _value(element):
    """A TCK <value>, as the JSON an agent would send: decimals as numbers, booleans, strings."""
    kind, text = element.get(_TYPE, ""), element.text or ""
    if kind.endswith("decimal"):
        number = Decimal(text)
        return int(number) if number == number.to_integral_value() else float(number)
    if kind.endswith("boolean"):
        return text == "true"
    return text


def _expected(node):
    """A TCK <expected>: a value, a context of components, or a list of either."""
    for child in node:
        if _local(child) == "value":
            return _value(child)
        if _local(child) == "list":
            return [_expected(item) for item in child]
    return {component.get("name"): _expected(component) for component in node if _local(component) == "component"}


def _first(element, name: str):
    return [child for child in element if _local(child) == name][0]


def _tck_cases(model: str) -> list[tuple]:
    """Each TCK test case: its id, inputs, decision name and expected result."""
    root = ElementTree.parse(EXPORTED / "tck" / f"{model}-test-01.xml").getroot()
    cases = []
    for case in (child for child in root if _local(child) == "testCase"):
        inputs = {node.get("name"): _value(_first(node, "value")) for node in case if _local(node) == "inputNode"}
        result = _first(case, "resultNode")
        cases.append((case.get("id"), inputs, result.get("name"), _expected(_first(result, "expected"))))
    return cases


@pytest.mark.parametrize("model", ["0004-simpletable-U", "0010-multi-output-U", "0108-first-hitpolicy",
                                   "0119-multi-collect-hitpolicy"])
def test_a_tck_table_gives_the_tck_answers(model):
    table = load_table(EXPORTED / "tck" / f"{model}.dmn")
    cases = _tck_cases(model)
    assert cases
    for case, inputs, decision, expected in cases:
        assert table.name == decision
        outputs = evaluate(table, inputs)["outputs"]
        # A single output is the decision's own value; several make a context with one entry per output
        if len(table.outputs) == 1 and not isinstance(expected, (dict, list)):
            outputs = outputs[table.outputs[0]]
        assert outputs == expected, f"{model} case {case}"


def test_a_tck_single_output_without_a_name_takes_the_decision_name():
    table = load_table(EXPORTED / "tck" / "0004-simpletable-U.dmn")
    assert table.outputs == ["Approval Status"]


def test_a_camunda_table_loads_and_answers():
    table = load_table(EXPORTED / "camunda" / "Example.dmn")
    assert (table.name, table.inputs, table.outputs) == ("Check Order", ["status", "sum"], ["result", "reason"])
    assert evaluate(table, {"status": "silver", "sum": 2000})["outputs"]["result"] == "notok"
    assert evaluate(table, {"status": "gold", "sum": 5})["outputs"]["result"] == "ok"


def test_a_kogito_table_with_an_unnamed_output_loads_and_answers():
    table = load_table(EXPORTED / "kogito" / "habitability.dmn")
    assert table.outputs == ["habitability"]
    assert evaluate(table, {"oxygene": 50, "temperature": 20})["outputs"] == {"habitability": "somehow doable"}


@pytest.mark.parametrize("file, problem", [
    ("camunda/dinnerDecisions.dmn", r"2 decisions \(Beverages, Dish\)"),
    ("kogito/traffic_violation.dmn", r"2 decisions \(Fine, Should the driver be suspended\?\)"),
    ("kogito/LoanEligibility.dmn", r"4 decisions \(Eligibility, Judgement, Is Enough\?, Decide\)"),
    ("camunda/ExpressionLanguageTest.JUEL.dmn", r"expression language JUEL"),
    ("camunda/ExpressionLanguageTest.groovy.decisionTable.dmn", r"expression language groovy"),
    ("tck/0003-input-data-string-allowed-values.dmn",
     r"decision Employment Status Statement is a literalExpression, not a decision table"),
    ("kogito/dtevent.dmn", r"decision my decision is a context, not a decision table"),
    ("tck/0005-simpletable-A.dmn", r"hit policy ANY is not supported"),
    ("tck/0114-min-collect-hitpolicy.dmn", r"COLLECT aggregation MIN is not supported"),
    ("kogito/loan-application-age-limit.dmn", r'unsupported expression "\? = Applicant.id"'),
])
def test_an_exported_file_the_reader_cannot_serve_is_refused_naming_why(file, problem):
    with pytest.raises(DmnError, match=rf"^{Path(file).name}.*{problem}"):
        load_table(EXPORTED / file)


@pytest.mark.parametrize("file, served", [
    ("camunda/Example.dmn", {"status": "string", "sum": "number"}),
    ("kogito/habitability.dmn", {"oxygene": "number", "temperature": "number"}),
    ("tck/0004-simpletable-U.dmn", "input 'Age' cannot be a parameter"),
    ("tck/0010-multi-output-U.dmn", "input 'Age' cannot be a parameter"),
    ("tck/0108-first-hitpolicy.dmn", "input 'Age' cannot be a parameter"),
    ("tck/0119-multi-collect-hitpolicy.dmn", "input 'Age' cannot be a parameter"),
])
def test_an_exported_table_is_served_unedited_only_when_its_inputs_are_lower_case_names(write_environment, file,
                                                                                      served):
    path = write_environment()
    path.write_text(path.read_text(encoding="utf-8") + '\n[decisions.exported]\ndescription = "An exported table"\n'
                    'dmn = "rules/exported.dmn"\n', encoding="utf-8")
    (path.parent / "rules" / "exported.dmn").write_bytes((EXPORTED / file).read_bytes())
    if isinstance(served, str):
        with pytest.raises(ScenarioError, match=served):
            load_environment(path)
    else:
        assert load_environment(path).decisions["exported"].params == served
