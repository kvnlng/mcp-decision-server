# Building a scenario, step by step

From nothing to a served scenario of your own, starting from the one `decision-new-scenario` writes.
[scenario.md](scenario.md) is the reference for every setting named here.

## 1. Start a folder

```bash
uv run decision-new-scenario my_scenario
```

This writes a small working scenario for a shop's customer messages: `scenario.toml` with three routes, a question, a
rule, an informing tool and an acting tool; `my_scenario_tools.py` with the two tools; `scenario.cases.jsonl`, a few
labelled cases. The `[clm]` block suits the machine: MLX on a Mac with Apple Silicon, torch elsewhere. See it decide
with the `decision-evaluate` command of step 7, then edit each part into your own.

## 2. Write the policy as routes

A [route](scenario.md#routes) is one thing the server can decide to do. Describe it as you would brief a person: what is
true of the request when this route is right. Keep one route for everything else, as the starter's `Other` is: CLM
always picks a route.

If your organisation has a written policy, make each answer's section its route's description, word for word, and add a
test that compares them, so the two cannot drift apart.

## 3. Give the decision what it needs to know: informing tools

An [informing tool](scenario.md#informing-tools) states plain sentences: "the order is 3 days late", not two dates for
CLM to compare.

- [`[routing] inform`](scenario.md#facts-the-route-considers): the starter's `order_status` says whether the order was
  delivered or how late it is, before the route is decided.
- A route's [`options`](scenario.md#options-fetched-at-decision-time): a tool that offers a few choices, such as the
  replacement items in stock, and CLM picks one.
- `[tools.inform.<tool>] questions`: facts that would sway a question's answer unfairly are kept from it. The starter's
  order facts go to the route, not to the question of how urgent the customer is.

Tools find their records from the request's `context`, which CLM never reads: the starter's tools expect
`{"order": "<order id>"}`.

## 4. Act on it: acting tools

An [acting tool](scenario.md#acting-tools) runs as soon as the decision is made. Put every safeguard in the tool: the
starter's `open_case` refuses, naming the reason, when the context has no order number, and the reply says so.

**Build each tool with a mock backend first.** The starter's tools read `[tools.settings] backend`: `"mock"` works now,
`"live"` is where you call your real systems. Point `"live"` at a test system before a real one.

## 5. Questions and rules

[Questions](scenario.md#questions-for-clm) are what the decision needs besides the route: how urgent, whether someone
vulnerable is involved. [Rules](scenario.md#rules) turn answers into instructions for the reply: the starter's
`urgent >= 0.5` tells the reply to answer today.

## 6. Examples to train on, and cases to check on

Training needs labelled examples of each route, ideally with the right answer to each question and the right option.
Checking needs **cases whose wording training never saw**, or the check measures memory.

- Without data, `decision-synthesize` has a language model write examples for each route.
- With real messages, label some for training and keep others, in different words, for checking only.
- Write the check cases in `scenario.cases.jsonl`, at least two per route, in the words real senders use.
- Label rare answers too: training balances them, and every report is per class, so "always no" cannot pass as
  success.

## 7. Train and check

```bash
uv run decision-evaluate my_scenario/scenario.toml --cases my_scenario/scenario.cases.jsonl   # before
uv run decision-train my_scenario/scenario.toml
uv run decision-evaluate my_scenario/scenario.toml --cases my_scenario/scenario.cases.jsonl   # after
```

`decision-evaluate --cases` decides every case through the server's own steps, with your tools but no acting tool. It
reports each route, option and answer per class, accuracy by confidence, and the lowest `confidence_threshold` at which
the routes kept are 90% right. It lists each case that got the wrong route, with its line in the file, the route it got
and its text. A score's answer counts as its likeliest level, as in training. Compare the two runs: on the examples,
trained heads lifted the routes a long way ([findings](findings.md#training)). People's corrections of real decisions
are training data too ([fine-tuning.md](fine-tuning.md)); `decision-evaluate` without `--cases` replays them.

## 8. Serve it and measure

```bash
uv run decision-server my_scenario/scenario.toml --trace runs/my.trace.jsonl
```

`--trace` records where each call's time went; `decision-trace-report` sums it up ([serving.md](serving.md)). To measure
a busy day, send a batch of real or generated messages through `decide_many`, as a coordinator would, and read the
report.

A complete scenario with options, several questions, rules and a replay of a whole day:
[examples/crowdstrike](../examples/crowdstrike/README.md).
