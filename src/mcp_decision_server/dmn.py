"""DMN decision tables: the subset the framework uses, evaluated with no model and no dependency.

A table is read from a DMN XML file (any DMN namespace version) holding one decision, a decision table in FEEL that
requires no other decision. Each input's expression text is the name of the variable it reads; each output's name is
the key of the result, and a table's only output may go unnamed, taking the decision's name. Supported:

    hit policies    UNIQUE (the default), FIRST, COLLECT (with no aggregation: every matching rule's outputs)
    input entries   -   a literal (1.5, "Region B", true)   < <= > >= = != with a number
                    ranges [a..b] (a..b) [a..b) (a..b]   comma-separated lists of these   not(...)
    output entries  number, string and boolean literals
    defaults        a defaultOutputEntry on every output, given when no rule matches (UNIQUE, FIRST); read as a last
                    row of - entries with the id "default", so it is shown and checked as the other rows are

Anything else is refused when the table is loaded, naming the file (and the rule, where the problem is in one), so a
table never half-works: a file with several decisions (they are not chained), a decision needing another, logic other
than one decision table, an expressionLanguage other than FEEL, two outputs with one name, an empty output entry, not()
and not(-), a range whose low end is above its high end, and a default on only some outputs or under COLLECT.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree

HIT_POLICIES = ("UNIQUE", "FIRST", "COLLECT")
_NUMBER = r"-?\d+(?:\.\d+)?"
_COMPARE = re.compile(rf"(<=|>=|!=|<|>|=)\s*({_NUMBER})")
_RANGE = re.compile(rf"([\[(])\s*({_NUMBER})\s*\.\.\s*({_NUMBER})\s*([\])])")
_STRING = re.compile(r'"([^"]*)"')


class DmnError(ValueError):
    """A table that cannot be read, or an evaluation that has no answer."""


class _NotANumber(TypeError):
    """A number test was given something else; evaluate() names the input."""


@dataclass(frozen=True)
class Rule:
    """One row: a test per input and a value per output."""
    id: str
    tests: tuple[Callable[[Any], bool], ...]
    values: tuple[Any, ...]
    entries: tuple[str, ...] = ()       # each input entry as written, for showing the row to a person
    default: bool = False               # the table's default outputs: fires only when no other rule matches


@dataclass(frozen=True)
class Table:
    """A decision table, ready to evaluate."""
    name: str
    inputs: list[str]
    types: list[str]        # each input's typeRef: number, string or boolean, or "" when the table gives none
    outputs: list[str]
    hit_policy: str
    rules: list[Rule]       # with the default outputs, if any, last, as a row of - entries with the id "default"


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _number(value):
    """The value, if it is a number; a comparison with text must not quietly come out false."""
    if not _is_number(value):
        raise _NotANumber(value)
    return value


def _literal(text: str):
    """A number, string or boolean literal; raises ValueError for anything else."""
    text = text.strip()
    if re.fullmatch(_NUMBER, text):
        return float(text) if "." in text else int(text)
    if text in ("true", "false"):
        return text == "true"
    match = _STRING.fullmatch(text)
    if match:
        return match.group(1)
    raise ValueError(text)


def _split(text: str) -> list[str]:
    """Split at the commas that are not inside quotes, brackets or parentheses."""
    parts, depth, quoted, start = [], 0, False, 0
    for index, char in enumerate(text):
        if char == '"':
            quoted = not quoted
        elif not quoted and char in "[(":
            depth += 1
        elif not quoted and char in "])":
            depth -= 1
        elif not quoted and depth == 0 and char == ",":
            parts.append(text[start:index])
            start = index + 1
    return [part.strip() for part in parts + [text[start:]]]


def _compare(op: str, bound: float) -> Callable[[Any], bool]:
    checks = {"<": lambda v: v < bound, "<=": lambda v: v <= bound, ">": lambda v: v > bound,
              ">=": lambda v: v >= bound, "=": lambda v: v == bound, "!=": lambda v: v != bound}
    check = checks[op]
    return lambda value: check(_number(value))


def _one(text: str) -> Callable[[Any], bool]:
    """One test of a list; raises ValueError for an unsupported one."""
    match = _COMPARE.fullmatch(text)
    if match:
        return _compare(match.group(1), float(match.group(2)))
    match = _RANGE.fullmatch(text)
    if match:
        low, high = float(match.group(2)), float(match.group(3))
        if low > high:
            raise ValueError(text)
        low_open, high_open = match.group(1) == "(", match.group(4) == ")"
        def within(value) -> bool:
            value = _number(value)
            return (value > low if low_open else value >= low) and (value < high if high_open else value <= high)
        return within
    expected = _literal(text)
    if _is_number(expected):
        return lambda value: _number(value) == expected
    return lambda value: type(value) is type(expected) and value == expected


def _test(text: str) -> Callable[[Any], bool]:
    """An input entry as a function of the input's value; raises ValueError for an unsupported one."""
    text = text.strip()
    if text in ("", "-"):
        return lambda _: True
    match = re.fullmatch(r"not\s*\((.*)\)", text)
    if match:
        # not() and not(-) would match nothing, which is never what a rule means
        if match.group(1).strip() in ("", "-"):
            raise ValueError(text)
        inner = _test(match.group(1))
        return lambda value: not inner(value)
    tests = [_one(part) for part in _split(text)]
    return lambda value: any(test(value) for test in tests)


def _local(element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _children(element, name: str) -> list:
    return [child for child in element if _local(child) == name]


def _text(element) -> str:
    texts = _children(element, "text")
    return (texts[0].text or "") if texts else ""


def _rules(path: Path, table, inputs: int, outputs: int) -> list[Rule]:
    rules = []
    for index, row in enumerate(_children(table, "rule")):
        rule_id = row.get("id") or f"rule {index + 1}"
        entries, values = _children(row, "inputEntry"), _children(row, "outputEntry")
        if len(entries) != inputs or len(values) != outputs:
            raise DmnError(f"{path.name} rule {rule_id}: needs {inputs} input and {outputs} output entries")
        # An empty input entry is "-", as in DMN; an empty output entry has no value to give
        if any(not _text(value).strip() for value in values):
            raise DmnError(f"{path.name} rule {rule_id}: empty entry; every output needs a value")
        try:
            tests = tuple(_test(_text(entry)) for entry in entries)
            results = tuple(_literal(_text(value)) for value in values)
        except ValueError as error:
            raise DmnError(f'{path.name} rule {rule_id}: unsupported expression "{error}"') from error
        rules.append(Rule(rule_id, tests, results, tuple(_text(entry).strip() or "-" for entry in entries)))
    return rules


def _feel(language: str) -> bool:
    """Whether an expressionLanguage names FEEL: "feel" in any case, or a URI whose last part is FEEL."""
    return bool(re.fullmatch(r"(?i)(.*/)?feel(/\d+)?/?", language.strip()))


def _decision(path: Path, root) -> tuple[Any, str]:
    """The file's one decision, which must be a decision table in FEEL needing no other decision, and its name."""
    decisions = [element for element in root.iter() if _local(element) == "decision"]
    named = [element.get("name") or element.get("id") or "?" for element in decisions]
    if not decisions:
        raise DmnError(f"{path.name}: no decision")
    if len(decisions) > 1:
        raise DmnError(f"{path.name}: {len(decisions)} decisions ({', '.join(named)}); a file holds one decision "
                       "table, as decisions are not chained, so put each table in its own file")
    decision, name = decisions[0], named[0]
    required = [element.get("href", "?") for element in decision.iter() if _local(element) == "requiredDecision"]
    if required:
        raise DmnError(f"{path.name}: decision {name} requires decision {', '.join(required)}, and decisions are "
                       "not chained")
    logic = [_local(child) for child in decision if _local(child) not in (
        "description", "extensionElements", "question", "allowedAnswers", "variable", "informationRequirement",
        "knowledgeRequirement", "authorityRequirement", "supportedObjective", "impactedPerformanceIndicator",
        "decisionMaker", "decisionOwner", "usingProcess", "usingTask")]
    if logic.count("decisionTable") > 1:
        raise DmnError(f"{path.name}: decision {name} has {logic.count('decisionTable')} decision tables")
    if logic != ["decisionTable"]:
        other = [kind for kind in logic if kind != "decisionTable"]
        raise DmnError(f"{path.name}: decision {name} is a {other[0] if other else 'decision with no logic'}, "
                       "not a decision table")
    for element in [root, *decision.iter()]:
        language = element.get("expressionLanguage")
        if language is not None and not _feel(language):
            raise DmnError(f"{path.name}: {_local(element)} uses expression language {language}; only FEEL is read")
    return decision, name


def _defaults(path: Path, columns: list, outputs: list[str], hit_policy: str) -> tuple[Any, ...] | None:
    """Every output's default entry, or None when no output has one; read as the table's last row."""
    entries = [(_children(column, "defaultOutputEntry") or [None])[0] for column in columns]
    # An empty default entry gives no value, as if it were absent
    entries = [entry if entry is not None and _text(entry).strip() else None for entry in entries]
    if all(entry is None for entry in entries):
        return None
    if hit_policy == "COLLECT":
        raise DmnError(f"{path.name}: default output entries are not supported under COLLECT")
    for entry, output in zip(entries, outputs):
        if entry is None:
            raise DmnError(f"{path.name}: output {output} has no default output entry; give every output one, "
                           "or none")
    try:
        return tuple(_literal(_text(entry)) for entry in entries)
    except ValueError as error:
        raise DmnError(f'{path.name}: default output entry: unsupported expression "{error}"') from error


def _outputs(path: Path, table, decision: str) -> list[str]:
    """Each output's name; as in DMN, a table's only output may go unnamed, its value being the decision's own."""
    outputs = [item.get("name") or "" for item in _children(table, "output")]
    if outputs == [""]:
        outputs = [decision]
    if not outputs or not all(outputs):
        raise DmnError(f"{path.name}: every output needs a name")
    if repeated := sorted({output for output in outputs if outputs.count(output) > 1}):
        raise DmnError(f"{path.name}: two outputs are named {', '.join(repeated)}")
    return outputs


def load_table(path: Path) -> Table:
    """The file's one decision table; raises DmnError naming the file (and rule) of any problem."""
    path = Path(path)
    try:
        root = ElementTree.parse(path).getroot()
    except (OSError, ElementTree.ParseError) as error:
        raise DmnError(f"{path.name}: cannot read: {error}") from error
    decision, name = _decision(path, root)
    table = _children(decision, "decisionTable")[0]
    if name == "?":
        name = path.stem
    hit_policy = table.get("hitPolicy", "UNIQUE")
    if hit_policy not in HIT_POLICIES:
        raise DmnError(f"{path.name}: hit policy {hit_policy} is not supported ({', '.join(HIT_POLICIES)})")
    if aggregation := table.get("aggregation"):
        raise DmnError(f"{path.name}: COLLECT aggregation {aggregation} is not supported; remove it to get every "
                       "matching rule's outputs")
    expressions = [(_children(item, "inputExpression") or [None])[0] for item in _children(table, "input")]
    inputs = [_text(expression).strip() if expression is not None else "" for expression in expressions]
    types = [expression.get("typeRef", "") if expression is not None else "" for expression in expressions]
    if not inputs or not all(inputs):
        raise DmnError(f"{path.name}: every input needs an inputExpression naming its variable")
    outputs = _outputs(path, table, name)
    defaults = _defaults(path, _children(table, "output"), outputs, hit_policy)
    rules = _rules(path, table, len(inputs), len(outputs))
    if defaults is not None:
        if any(rule.id == "default" for rule in rules):
            raise DmnError(f"{path.name}: rule id default is kept for the default outputs; rename the rule")
        rules.append(Rule("default", tuple(_test("-") for _ in inputs), defaults, ("-",) * len(inputs), True))
    return Table(name, inputs, types, outputs, hit_policy, rules)


def _matches(table: Table, rule: Rule, values: list) -> bool:
    """Whether every test of the rule passes, stopping at the first that fails; a number test given something else
    names its own input."""
    for name, test, value in zip(table.inputs, rule.tests, values):
        try:
            if not test(value):
                return False
        except _NotANumber as error:
            raise DmnError(f"{table.name}: {name} must be a number, not {value!r}") from error
    return True


def evaluate(table: Table, inputs: dict) -> dict:
    """-> {"outputs": ..., "fired": [rule ids]}; for COLLECT, outputs is a list of dicts, one per rule fired.
    Raises DmnError for a missing input, for no matching rule and no defaults (UNIQUE, FIRST) or for two (UNIQUE)."""
    missing = [name for name in table.inputs if name not in inputs]
    if missing:
        raise DmnError(f"{table.name}: missing input {', '.join(missing)}")
    values = [inputs[name] for name in table.inputs]
    fired = [rule for rule in table.rules if not rule.default and _matches(table, rule, values)]
    if table.hit_policy == "COLLECT":
        return {"outputs": [dict(zip(table.outputs, rule.values)) for rule in fired],
                "fired": [rule.id for rule in fired]}
    if not fired and table.rules and table.rules[-1].default:
        # A rule's tests stop at its first failure; before the default answers, text in a number column is an error
        for rule in table.rules:
            for name, test, value in zip(table.inputs, rule.tests, values):
                try:
                    test(value)
                except _NotANumber as error:
                    raise DmnError(f"{table.name}: {name} must be a number, not {value!r}") from error
        fired = [table.rules[-1]]
    if not fired:
        shown = ", ".join(f"{name}={inputs[name]!r}" for name in table.inputs)
        raise DmnError(f"{table.name}: no rule matches {shown}")
    if table.hit_policy == "UNIQUE" and len(fired) > 1:
        raise DmnError(f"{table.name}: rules {', '.join(rule.id for rule in fired)} all match, and the hit policy "
                       "is UNIQUE")
    return {"outputs": dict(zip(table.outputs, fired[0].values)), "fired": [fired[0].id]}
