# Building a decision server with a person

This file is for a coding agent helping a person build their own decision server in a clone of this repository. The
person describes a decision; you build it with them, one small part at a time, and prove each part works before the
next. The docs hold the detail: read the page named in each section when you need it.

## Where you work

- **Build only in the person's own folders.** Each is made at the root of the clone by `uv run decision-new-environment
  FOLDER` or `uv run decision-new-scenario FOLDER`, and holds everything of theirs: the TOML file, data, rules and
  Python.
- **Leave the framework alone.** `src/`, `tests/`, `examples/`, `docs/`, `pyproject.toml` and `uv.lock` are the
  framework. Read them for reference; never edit them to make the person's server work.
- **Before you change anything in the framework, ask the person whether they develop it**: whether they own or
  maintain this repository, or are contributing a change to it. If they do, the framework is theirs to change: run
  `uv run pytest` before and after, and keep each change small. If they do not, or are not sure, leave the framework
  unchanged. Tell them what you found, with the command and the error, and carry on in their own folders.
- **If you think the framework has a bug,** stop and ask that question before you change anything.
- **Never commit or push** unless the person asks. Never write a key or password into a file that git tracks; use an
  environment variable, as the docs do.
- Run commands from the root of the clone, with `uv run`. Run natively; no Docker.

## First, which kind of decision

Ask what the person wants decided, then choose with them:

| The person wants to | Build | Read |
|---|---|---|
| Pick the best of several options, by rules and figures ("which venue", "which supplier") | An **environment** | [docs/environment.md](docs/environment.md) |
| Sort incoming messages into a fixed set of kinds ("what does this customer need") | A **scenario**, routed by CLM | [docs/scenario.md](docs/scenario.md) |

Both can work together: a scenario's informing tool can call an environment's server, as in
[getting started, section 10](docs/getting-started.md#10-join-them-with-a-tool).

**Ask, do not invent, the person's domain:** the options, the rules and their thresholds, the routes, and the data.
Made-up data is fine for a first build, but say it is made up. If the person cannot answer, choose, and list every
choice in your report so they can change it.

## Building an environment

Start from the template and cut it down. The smallest environment that loads has `[environment]` with `name`,
`description` and `functions` (a Python module beside the file), and `[graph]` with `nodes` and `edges` CSV files;
an `edges.csv` with only its header line loads. Each part then becomes one tool:

| Part | In `environment.toml` | Becomes the tool |
|---|---|---|
| A named query over the graph | `[queries.NAME]` with `params` and `function` | `query_NAME` |
| A rule | `[decisions.NAME]` with `dmn = "rules/NAME.dmn"`, or a function | `decision_NAME` |
| Arithmetic | `[calculations.NAME]` with `params` and `function` | `calculation_NAME` |
| Options to weigh | `[scenarios.NAME]` with `params`, `levers`, `branch`, `objective`, `limits` | `scenario_NAME` |

Every environment also has `describe`. Delete the template's parts the person does not need, such as its budget
rule. Build in this order, checking each part before the next: a query, a rule, a calculation, then the scenario that
joins them.

How the parts link up, which is where a first build goes wrong:

- **A query fails when what it was asked about does not exist.** Raise `LookupError`; an empty list looks like an
  answer (an unknown team had nobody in it, so every venue fitted). The graph operations a query can use are in
  [the reference](docs/environment-reference.md#the-graph); the template's `_known` helper shows the check.
- **A limit is a decision whose outputs include `allowed` (boolean) and `reason` (text).** Every limit listed in a
  scenario must be checked in every branch, with `steps.decide(...)`, or the branch fails with "limit NAME was not
  checked".
- **A DMN table's input names become the decision's arguments**, lower-case identifiers. The supported DMN is listed
  in [the reference](docs/environment-reference.md#decisions); no row matching is an error, never a silent "allowed",
  unless the table gives every output a default.
- **A calculation's `params` take the rows the queries returned**, as `list`, and it returns a dict of figures.
- **A calculation raises `ValueError` for inputs that make no sense**, such as a meeting of 0 hours. Otherwise every
  option costs nothing and the cheapest wins; with the error, every branch fails and says why.
- **The scenario's `objective` is a key of the figures the branch returns**, a finite number.
- **The branch function moves rows between steps and does no arithmetic.** It calls `steps.query`, `steps.calculate`
  and `steps.decide`, and returns the figures.
- **What the question fixes is a parameter; only real alternatives are levers.** The levers are the only values an
  agent may choose.
- **Descriptions are what the calling agent reads.** Say what the rows hold and in which units, and which ids to ask
  about.

Copy the shapes from the template and from [examples/tariff](examples/tariff/README.md). The full key reference:
[docs/environment-reference.md](docs/environment-reference.md).

### Check each step

A mistake in the file stops loading with one line naming the setting. List the tools and call one, without a
browser. Here the folder is `meeting_rooms` and its scenario `meeting_room`, with the parameters `people` and `hours`:

```bash
npx -y @modelcontextprotocol/inspector@2.13.0 --cli uv run decision-server meeting_rooms/environment.toml --method tools/list
npx -y @modelcontextprotocol/inspector@2.13.0 --cli uv run decision-server meeting_rooms/environment.toml \
    --method tools/call --tool-name scenario_meeting_room --tool-arg people=6 --tool-arg hours=2
```

- **Arguments:** numbers arrive as numbers; a `list` argument is passed as JSON text, `--tool-arg 'rows=[{...}]'`.
- **The output** is a JSON object followed by a "Schema portability" line, so parse from the first `{` to its end.
- **Reading a scenario's result:** each branch has a `status`: `kept`, `rejected` (with `rejected_by`: the decision,
  reason and inputs) or `failed` (with `error`). Every branch keeps its `figures`. `ranking` lists the kept branches'
  lever values, best first, and `best` is the first; when every branch is rejected, `ranking` is `[]` and `best` is
  `null`, which means no option meets the rules.

Show the person what changed. They can open the same server in the browser with the command minus `--cli` and the
`--method` arguments.

## Building a scenario

`uv run decision-new-scenario FOLDER` writes `scenario.toml`, a tools module and a cases file, for a made-up shop. For a
scenario that only routes, keep the `[clm]` block and replace everything after it with your own `[generator]`,
`[synthesize]`, `[routing]` and routes, as in
[getting started, section 8, step 2](docs/getting-started.md#8-route-messages-with-clm); the tools module is then
unused. Add questions, rules, informing and acting tools only if the person needs them
([docs/scenario.md](docs/scenario.md)).

**What it needs:** an Apple Silicon Mac (keep `backend = "mlx"`) or Linux with an NVIDIA GPU (the template's
`backend = "torch"` lines), and about 8 GB for the CLM model, which downloads on first use. Training examples are
written by the `[generator]` model. With Ollama running and the model pulled:

```toml
[generator]
backend = "ollama"
model = "qwen3:14b"
max_tokens = 500

[synthesize]
messages = "messages that people in an office might send to the office manager"
```

If the machine has neither a GPU nor a generator model, say so before building.

**Write the routes well, since they do most of the work.** Each `[routes.NAME]` has a `description` and `examples`.
**One route must be for everything else**: CLM always picks a route. `[synthesize] messages` says who sends the
messages and about what; make it as wide as the messages the server will really get, or the catch-all route is
trained only on near-misses and real off-topic messages land on other routes.

The loop:

1. **Write the routes** with the person.
2. **Write test cases** with the person in `scenario.cases.jsonl`, one per line: `{"text": "...", "route": "NAME"}`,
   at least two per route, in the words real senders use. `context` and `answers` are needed only when the scenario
   has tools or questions.
3. **Measure the start:** `uv run decision-evaluate FOLDER/scenario.toml --cases FOLDER/scenario.cases.jsonl`. It prints
   the score per route, how many wrong routes were marked uncertain, each case that got the wrong route (its line,
   the route it got and its text), and a suggested `confidence_threshold`.
4. **Write training examples:** `uv run decision-synthesize FOLDER/scenario.toml`, 64 per route. Read some from each
   route. If the generator filed messages under the wrong route, reword the descriptions, move
   `scenario.examples.jsonl` aside (it refuses to overwrite it) and synthesize again.
5. **Train:** `uv run decision-train FOLDER/scenario.toml` writes `scenario.heads`, and prints the released and trained
   scores on examples it held back from training.
6. **Measure again** with the same `decision-evaluate` command, and report both scores plainly.

To see a whole decision for one message, call `decide` through the Inspector:
`--method tools/call --tool-name decide --tool-arg text="..."` on `FOLDER/scenario.toml`. If a route still scores
badly, rewrite its description and examples, or widen `[synthesize] messages`, before training more. Changing a
route's name or description, or the routing question, means synthesizing and training again.

## Reporting to the person

- Say what you built, the command you checked it with and what came back. A claim without a run behind it is a guess.
- Report results even-handedly, including what does not work yet.
- When you made something up or chose for the person, say so, so they can change it.
