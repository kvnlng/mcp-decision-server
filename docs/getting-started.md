# Getting started

This quick start takes about an hour, plus downloads. It has three parts:

1. **Weigh options**, sections 1 to 7: install the project, look inside a decision server, serve it with its portal,
   make an environment of your own and connect an agent to it. It starts with the **tariff** example, which needs
   no training, database or GPU.
2. **Route messages**, section 8: train CLM to route the team's messages about your offsite.
3. **Work together**, sections 9 and 10: use both servers in one chat, then join them with a tool.

The [reference](#reference) at the end explains what you ran.

**Before you start**, install:

- [git](https://git-scm.com), Python 3.12 to 3.14 and [uv](https://docs.astral.sh/uv/)
- [Node](https://nodejs.org), for the MCP Inspector (`npx` downloads it)
- [Ollama](https://ollama.com), for sections 4, 6, 8, 9 and 10
- For sections 8 to 10 only: an Apple Silicon Mac, or Linux with an NVIDIA GPU, and about 8 GB of disk for CLM

# Part 1: Weigh options

## 1. Install

```bash
git clone https://github.com/kvnlng/clm-decision-agent
cd clm-decision-agent
uv sync
```

**Check:** `uv run clm-server --help` prints the flags. A checkout gets every extra, so every command works. CLM
itself downloads only when something first needs it, which nothing before section 8 does.

## 2. Look inside the server

You start a decision server for the **tariff** example: a made-up manufacturer weighing whether to buy more of
Product Line X's components from Region B after a tariff rise. Its products, suppliers and rules are invented, so
you need not follow them; the point is to see what a decision server offers an agent and what comes back. You make
one of your own in [section 5](#5-make-your-own).

The [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) is a browser page that starts your server
and calls one tool at a time, with no model and no agent. Use it after every change, before an agent. These steps
are for 2.13.0; the page changes between versions.

```bash
npx -y @modelcontextprotocol/inspector@2.13.0 uv run clm-server examples/tariff/environment.toml
```

1. **Open the page.** The command opens `http://127.0.0.1:6274/?MCP_INSPECTOR_API_TOKEN=...`. The token lets only
   you use it. A **Read-only session** notice says the Inspector's list of servers can't be edited or saved, since
   the command named the server; that is expected, and the server itself is not read-only.
2. **Connect.** The server card shows a slider marked **Disconnected**. Click it: the Inspector starts your server
   and the slider turns to **Connected**. On **Failed**, the **Console** has the one-line reason.
3. **Open Tools.** You should see 18 tools. If the list is empty and the **Protocol** panel shows `tools/list`
   as **Pending**, click that message's **Replay** button (the same for `prompts/list` and
   `resources/templates/list`).
4. **Run `query_components_of`** with `PX` in its **product** field (only `PX`, nothing else). You should see
   three rows, Housing (C1), Controller board (C2) and Drive motor (C3), and the steps behind them. This JSON is
   what an agent gets.
5. **Run `scenario_sourcing`** the same way. This is the decision: should Product Line X's sourcing move to Region
   B? The result is long; look at each branch's `levers`, `status` and `figures`, then `best` at the end:

   | `region_b_share` | `status` | `q3_margin` | |
   |---|---|---|---|
   | 0 | `kept` | 662,500 | |
   | 0.5 | `kept` | 704,900 | `best` |
   | 1.0 | `rejected` | 747,300 | `rejected_by` `supply_concentration`: all of supply would depend on Kestrel Polymers, over the 60% limit |

   The highest margin loses to a rule, and each branch's `steps` show every query, rule and calculation behind it.
6. **Open Prompts.** You should see one, `answer_question`. Select it, type "Should we shift Product Line X's
   sourcing to Region B?" in its **question** field and click **Get Prompt**. You should see one user message: the
   reference agent's instructions (start with `describe`, never calculate a figure, run the scenario tool to compare
   alternatives, cite what you relied on), then the environment's name and description, then your question. A
   client that offers prompts, such as a slash command, sends this message to its model.
7. **Open Resources.** You should see one, `describe`: every query, decision, calculation, judge and scenario,
   with its description and parameters. Tariff has no templates; an environment with rule metadata or documents has
   templates that read one rule or document by name.

After an edit to the environment's files, click the slider off and on again to restart the server from them. The
**Protocol** panel times every message.

## 3. Serve it to agents, with the portal

Stop the Inspector (Ctrl-C). Make two keys, one for agents and one for you, then start the server:

```bash
export DECISION_SERVER_KEY=$(openssl rand -hex 32)    # agents send this
export CLM_PORTAL_KEY=$(openssl rand -hex 32)         # you sign in to the portal with this
echo "$CLM_PORTAL_KEY"
uv run clm-server examples/tariff/environment.toml --http --portal 8400
```

1. **Agents** connect to <http://127.0.0.1:8000/mcp> with `Authorization: Bearer $DECISION_SERVER_KEY`.
2. **Open the portal** at <http://127.0.0.1:8400>. Sign in with the portal key and your name.
3. **Open Server.** You should see 18 offered tools, each with a **Disable** button, and the checks: `tools` and
   `describe` pass, `clm` warns that it loads on first judgement, and the rest are `not configured`.

Leave the server running for section 4. The portal is described in [portal](portal.md).

## 4. Ask it a question

Ask puts your question to a model, which answers using only the server's tools, and shows every call it makes. The
server from section 3 keeps its terminal busy, so open a second terminal. Start the [Ollama](https://ollama.com) app
(or run `ollama serve`), then download the starter model once:

```bash
ollama pull granite4:micro          # about 2.1 GB
```

In the portal, open **Ask** and fill in the form:

| Field | Enter |
|---|---|
| **Question** | Should we shift Product Line X's sourcing to Region B, and what would it do to Q3 margin? |
| **Model** | OpenAI-style (Ollama by default) |
| **Model name** | leave empty |
| **Model URL** | leave empty |
| **Dry run** | leave unticked |
| **Dry run for only these tools** | leave empty |
| **Full results** | leave unticked |

Click **Ask**. After a few seconds you should see each tool call with its arguments and result, then the answer.
Read the calls, not only the answer: the model should call `scenario_sourcing` with `PX` and report the 0.5 branch as
best, with 100% rejected for supply concentration, as in section 2. A small model can pass the product's name instead
of its id `PX`, and every branch then fails; click **Ask** again.

Now ask a follow-up in **Question**: "Why was moving everything to Region B rejected?" The conversation continues, so
the model knows what "everything" means. You should see it name the `supply_concentration` rule and Kestrel
Polymers, the raw-material provider all of Region B's suppliers depend on, from the result it already has or by
calling a tool again. Every setting is described in [Ask](portal.md#ask).

When you are done, stop the server in the first terminal (Ctrl-C).

## 5. Make your own

Run `clm-new-environment`. It creates a folder,
`my_environment`, pre-loaded with a small working example: a made-up team choosing which of three venues to hold an
offsite at, within a budget. The second command opens it in the Inspector:

```bash
uv run clm-new-environment my_environment
npx -y @modelcontextprotocol/inspector@2.13.0 uv run clm-server my_environment/environment.toml
```

A blank environment would offer only `describe`, and you would have to write several parts that fit together
before you could test anything. The example gives you one of each part, already working, so every edit you make can
be checked at once, and each part shows the shape yours will take:

| File | What it adds |
|---|---|
| `environment.toml` | Every part, with a comment on each: the description an agent reads first, the queries, decisions, calculation and scenario |
| `graph/nodes.csv`, `graph/edges.csv` | The made-up data the queries read: the team, its cities, the venues and the train fares. Replace them with your own |
| `rules/capacity.dmn`, `rules/budget.dmn` | Two rules as DMN tables, each saying whether a branch is allowed and why |
| `my_environment_functions.py` | The Python behind the queries, the calculation and each branch of the scenario |

1. **Connect** with the **Disconnected** slider, as in section 2.
2. **Open Tools.** You should see 8, each made from one part of `environment.toml`: three queries that read the
   made-up data (who is in the team, each venue's terms, train fares), two decisions that are rules (does everyone
   fit, is it within budget), a calculation that adds up the costs, `scenario_offsite` that runs them for each venue,
   and `describe`, which every environment has.
3. **Run `scenario_offsite`** with `T1` in **team** and `2` in **days**. You should see:

   | `venue` | `status` | `total_cost` | |
   |---|---|---|---|
   | V1 | `kept` | 7,380 | |
   | V2 | `rejected` | 5,400 | `capacity`: the venue is too small for everyone |
   | V3 | `kept` | 6,960 | `best` |

4. **Change a rule.** Lower the budget from 9,000 to 7,000 pounds:
   - `my_environment/rules/budget.dmn`, line 11 (the rule `budget_refused`): change `&gt; 9000` to `&gt; 7000`, and
     "9,000" to "7,000" in the reason "Over the offsite budget of 9,000 pounds".
   - `my_environment/environment.toml`, line 39 (the description of `decisions.budget`, which agents read): change
     "9,000 pounds" to "7,000 pounds".
5. **Restart** by clicking the slider off and on again, and run `scenario_offsite` again. V1 is now `rejected` by
   `budget` ("Over the offsite budget of 7,000 pounds"); V3 is still `best`. A mistake in a file stops start-up with
   one line naming it, shown in the **Console**.

`my_environment/environment.toml` lists every part, with a comment on each. The [environment](environment.md) guide
explains them, and how to replace the made-up data with your own; the graph can live in
[Neo4j](environment.md#on-neo4j).

## 6. Connect an agent

So far you have called tools by hand in the Inspector, and through Ask, which is built into the portal. A real
deployment has four parts:

| Part | Here | What it does |
|---|---|---|
| The person | You | Types questions in a chat |
| The harness | `ollmcp`, a command-line chat app | Connects to two servers: the model, and your decision server. Passes your question and the tool descriptions to the model, runs the tool calls the model asks for, and returns the results until the model answers |
| The model | `qwen3:14b`, served by Ollama | Reads the tool descriptions and decides which tools to call |
| Your decision server | `clm-server` | Waits for harnesses to connect, runs the tools they call, and returns the results |

You never talk to the decision server directly, and neither does Ollama: the harness connects the two. Ask, Claude
Desktop and Claude Code are harnesses too. Here you use a separate one, `ollmcp`
([mcp-client-for-ollama](https://github.com/jonigl/mcp-client-for-ollama)), to see that any MCP client can use your
server.

### Start your decision server

1. **Start it**, in the first terminal. Stop the Inspector (Ctrl-C). Show the agents' key from section 3 and copy it,
   then start the server:

   ```bash
   echo "$DECISION_SERVER_KEY"
   uv run clm-server my_environment/environment.toml --http
   ```

   You should see `Serving MCP at http://127.0.0.1:8000/mcp`. The server now waits for harnesses; leave it running.

### Set up the harness

2. **Give the second terminal the key.** Paste the key you copied:

   ```bash
   export DECISION_SERVER_KEY=<the key you copied>
   ```

3. **Download a larger model** (about 9.3 GB). `granite4:micro` often reaches for figures no tool returned on this
   environment; `qwen3:14b` answers from the tools:

   ```bash
   ollama pull qwen3:14b
   ```

4. **Tell the harness where your server is**, once. This saves the address and the key in `ollmcp`'s settings, for
   this folder only, so run it and the next step from the repository:

   ```bash
   uvx --from mcp-client-for-ollama==0.35.1 ollmcp mcp add --transport http \
       --header "Authorization: Bearer $DECISION_SERVER_KEY" offsite http://127.0.0.1:8000/mcp
   ```

### Chat with your server

5. **Start the harness** with the model:

   ```bash
   uvx --from mcp-client-for-ollama==0.35.1 ollmcp -m qwen3:14b
   ```

   You should see `Successfully connected to offsite with 8 tool(s) and 1 prompt(s) and 1 resource(s)`, then your
   tools, each named `offsite.` and the tool, and a prompt ending in `❯`.
6. **Ask with your server's prompt.** This is the prompt you met in section 2: your server's instructions for the
   model, then your question.
   1. At the `❯` prompt, type `/offsite:answer_question` and press Enter.
   2. When `question❯` appears, type this question and press Enter:

      ```text
      Where should the Platform team (T1) hold a two-day offsite, and why not the other venues?
      ```

   3. When asked `What would you like to do? (y)`, type `y` and press Enter to send it to the model.
   4. The model's thinking scrolls past, then it asks to run `offsite.scenario_offsite` with `team` T1 and `days` 2,
      sometimes after `offsite.describe`. At each `What would you like to do? (y)`, type `y` and press Enter to
      approve the call: the harness asks you before every call.

   The result follows, then the answer: Leith Studio (V3) at 6,960 pounds; Thames Loft (V1) rejected by `budget` at
   7,380 pounds; Northern Works (V2) rejected by `capacity`, with 2 seats short. Each reason names the rule behind it.
7. **Ask a follow-up.** At the `❯` prompt, type "Why was Thames Loft rejected?" and press Enter. The conversation
   continues, so the model answers from the result it already has, without a new tool call: 7,380 pounds is over the
   budget of 7,000.
8. **Try it without the prompt.** Type `/new` to start again, then type the question on its own. Without your
   instructions the model tends to fetch the facts one query at a time and work the costs out itself, asking you to
   approve each call, and may reach the harness's limit of 7 rounds before it answers. Your server's prompt is what
   tells it to run the scenario.
9. **Leave** with `/q`. The decision server in the first terminal is still running, ready for the next harness.

When you are done, stop the server in the first terminal (Ctrl-C). `ollmcp` keeps the address and key you saved for
the sections that follow.

## 7. Grow your environment

Now change your environment the way you would for real: add a rule, then add an option for it to choose. You edit
the files under `my_environment` in the second terminal, then check each change in the Inspector, in the first, as in
section 5. At the end you ask your agent. The commands use `vi`; any editor works. Line numbers are for the files as
`clm-new-environment` wrote them.

### Add a rule

The team's travel must not cost more than 1,500 pounds.

1. **Write the rule.** Create a new file:

   ```bash
   vi my_environment/rules/travel.dmn
   ```

   Add the following, then save. It is `budget.dmn` with the names, the limit and the reasons changed:

   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <definitions xmlns="https://www.omg.org/spec/DMN/20191111/MODEL/" id="travel_definitions" name="travel"
                namespace="https://example.org/offsite">
     <decision id="travel" name="travel">
       <decisionTable id="travel_table" hitPolicy="FIRST">
         <input id="travel_in1" label="travel_cost"><inputExpression typeRef="number"><text>travel_cost</text></inputExpression></input>
         <output id="travel_out1" name="allowed" typeRef="boolean"/>
         <output id="travel_out2" name="reason" typeRef="string"/>
         <rule id="travel_refused"><inputEntry><text>&gt; 1500</text></inputEntry><outputEntry><text>false</text></outputEntry><outputEntry><text>"Travel would cost more than 1,500 pounds"</text></outputEntry></rule>
         <rule id="travel_allowed"><inputEntry><text>-</text></inputEntry><outputEntry><text>true</text></outputEntry><outputEntry><text>"Travel is within 1,500 pounds"</text></outputEntry></rule>
       </decisionTable>
     </decision>
   </definitions>
   ```

2. **Make it a limit.** Open the environment's file:

   ```bash
   vi my_environment/environment.toml
   ```

   - After line 40, `dmn = "rules/budget.dmn"`, add a blank line and:

     ```toml
     [decisions.travel]
     description = "Whether the team's total travel cost in pounds is within 1,500 pounds."
     dmn = "rules/travel.dmn"
     ```

   - In the `limits` line (line 57 as written, 61 now), add `"travel"`: `limits = ["capacity", "budget", "travel"]`.

   Save the file.
3. **Check it in the Inspector.** In the first terminal, start the Inspector on your environment:

   ```bash
   npx -y @modelcontextprotocol/inspector@2.13.0 uv run clm-server my_environment/environment.toml
   ```

   1. Connect with the **Disconnected** slider.
   2. Open **Tools**. You should see `decision_travel`, a ninth tool, made from your rule.
   3. Run `scenario_offsite` with `T1` in **team** and `2` in **days**. In the result, look at each of the three
      branches, one per venue in `levers`. Each has:

      ```text
      "status": "failed",
      "rejected_by": [],
      "error": "limit travel was not checked"
      ```

      Near the end, `"ranking": []` and `"best": null`: no venue was ranked. Each branch still has its `figures`, but
      a limit must be checked in every branch, and a branch that skips one is never ranked. You added the rule to the
      file but not to the branch; step 4 does that.

   Leave the Inspector open for the next checks.
4. **Apply it in the branch.** In the second terminal, open the environment's functions:

   ```bash
   vi my_environment/my_environment_functions.py
   ```

   After line 69, `steps.decide("budget", ...)`, add this line with the same indent, then save:

   ```python
       steps.decide("travel", travel_cost=figures["travel_cost"])
   ```

5. **Check it again.** In the Inspector, click the slider off and on to restart the server from your files,
   and run `scenario_offsite` again. Now every venue is `rejected`: V1 by `budget`, V2 by `capacity`, and
   V3 by `travel`, at 1,920 pounds. There is no `best`. The rules leave nothing to choose.

### Add a venue

6. **Add the data.** Canal Rooms, in Manchester, seats 30. In the second terminal, open the venues and places:

   ```bash
   vi my_environment/graph/nodes.csv
   ```

   Add this line at the end, then save:

   ```text
   V4,venue,Canal Rooms,,30,1600,38
   ```

   Then open the connections between them:

   ```bash
   vi my_environment/graph/edges.csv
   ```

   Add this line at the end, then save:

   ```text
   V4,located_in,MAN,
   ```

7. **Offer it.** Open the environment's file again:

   ```bash
   vi my_environment/environment.toml
   ```

   Change the `levers` line (line 53 as written, 57 now) to `levers = { venue = ["V1", "V2", "V3", "V4"] }`, and on
   line 8 change "the three venues" to "the four venues", then save. The levers are the only values an agent may
   choose, so a venue that is not listed is never compared.
8. **Check it again**, as in step 5. V4 is `kept` and `best`: 5,708 pounds in all, 1,140 of it travel.

### Ask your agent

9. **Serve the new version.** Stop the Inspector (Ctrl-C) and start the server as in section 6:

   ```bash
   uv run clm-server my_environment/environment.toml --http
   ```

10. **Ask again**, in the second terminal: start `ollmcp` as in section 6, step 5, and ask with
    `/offsite:answer_question` as in step 6. It uses the address and key you saved, and now shows 9 tools. The answer
    should be Canal Rooms (V4) at 5,708 pounds, with each of the other three rejected by a different rule.

When you are done, type `/q` in `ollmcp` and stop the server (Ctrl-C).

# Part 2: Route messages

## 8. Route messages with CLM

Everything so far *weighed options*: the server worked out figures, and rules rejected venues and ranked the rest.
The other style of decision *routes a message*: CLM, a contextual language model, reads a message and picks one of
the routes you describe. Here you make one for messages the team sends about the offsite. It is a separate server, a
*scenario*, and it is deliberately simple; the point is to see how you describe routes and train CLM on them.

1. **Make the scenario.** In the second terminal:

   ```bash
   uv run clm-new-scenario offsite_desk
   ```

   It writes a folder, `offsite_desk`, with a template for a shop's help desk:

   | File | What it is |
   |---|---|
   | `scenario.toml` | The scenario: which CLM to use, the routes, the questions and rules |
   | `offsite_desk_tools.py` | The template's tools, which look up an order and open a case; not used here |
   | `scenario.cases.jsonl` | Test messages, each with its right route |

2. **Describe the routes.** Open the scenario's file:

   ```bash
   vi offsite_desk/scenario.toml
   ```

   Keep lines 1 to 14: the `[clm]` block says which CLM to use. On Linux, put `#` before lines 8 and 9 and remove
   it from lines 11 and 12. Delete everything from line 15, `# Only synthesize.py uses a language model...`, to the
   end (in `vi`, type `:15,$d` and Enter), then add the following and save:

   ```toml
   # Only clm-synthesize uses a language model, to write example messages for training
   [generator]
   backend = "ollama"
   model = "qwen3:14b"
   max_tokens = 500

   [synthesize]
   messages = "messages that team members might send to the organiser of a two-day team offsite"

   [routing]
   instructions = "What does the team member need?"
   confidence_threshold = 0.6

   [routes.Attendance]
   description = "The team member cannot come, will arrive late or must leave early."
   examples = ["I can't make the second day, sorry"]

   [routes.Dietary]
   description = "The team member has a food requirement or allergy the caterers need to know about."
   examples = ["I'm vegetarian, can you let the caterers know?"]

   [routes.Travel]
   description = "The team member is asking how to get to the venue, or about travel and parking."
   examples = ["Is there parking at the venue?"]

   # CLM always picks one of the routes, so a scenario needs one for requests it does not cover.
   [routes.Other]
   description = "Anything else, or a message too vague to tell what the team member needs."
   examples = ["Quick question about the offsite"]
   ```

   | Block | What it does |
   |---|---|
   | `[generator]` | The language model that writes training messages: your Ollama model from section 6 |
   | `[synthesize]` | What kind of messages it writes |
   | `[routing]` | The question CLM answers, and the confidence below which a route is marked uncertain |
   | `[routes.…]` | One per route: CLM reads its description and examples |

3. **Write the test messages.** Open the cases file:

   ```bash
   vi offsite_desk/scenario.cases.jsonl
   ```

   Delete its six lines (in `vi`, `:%d` and Enter), add these eight, then save. Each is a message and its right route:

   ```text
   {"text": "My train gets in at 11, so I'll miss the morning session on day one.", "route": "Attendance"}
   {"text": "Family emergency, I won't be there at all. Really sorry.", "route": "Attendance"}
   {"text": "Just a reminder that I don't eat pork.", "route": "Dietary"}
   {"text": "I'm coeliac, so lunch needs to be gluten free for me.", "route": "Dietary"}
   {"text": "Which station is closest to the venue?", "route": "Travel"}
   {"text": "Can I leave my car there overnight?", "route": "Travel"}
   {"text": "Will the slides be shared afterwards?", "route": "Other"}
   {"text": "hi, got a minute?", "route": "Other"}
   ```

4. **Measure CLM as released.** The first run downloads CLM, about 8 GB:

   ```bash
   uv run clm-evaluate offsite_desk/scenario.toml --cases offsite_desk/scenario.cases.jsonl
   ```

   You should see:

   ```text
   CLM is using its released heads (scenario.heads has no trained heads yet; ...)
   Route: 4 of 8 (50%): Attendance 0 of 2, Dietary 2 of 2, Travel 2 of 2, Other 0 of 2
   ```

   As released, CLM has only your descriptions to go on. It gets food and travel right, but not lateness, absence or
   a vague message.

5. **Write training messages.** With Ollama running, as in section 6:

   ```bash
   uv run clm-synthesize offsite_desk/scenario.toml
   ```

   It takes about two minutes and writes 64 messages for each route to `offsite_desk/scenario.examples.jsonl`. Read a
   few with `head offsite_desk/scenario.examples.jsonl`: these are what CLM learns from.

6. **Train CLM:**

   ```bash
   uv run clm-train offsite_desk/scenario.toml
   ```

   It takes under a minute. It holds back some of the messages, scores CLM on them before and after training, and
   saves the trained *heads*, the small part of CLM that training changes, in `offsite_desk/scenario.heads`. You
   should see `released` about 50% and `trained` above 90%; the figures differ a little from run to run, since the
   messages differ.

7. **Measure again**, with the command from step 4. Now it says `CLM is using its trained heads`, and the routes
   should be 8 of 8, or very nearly.

8. **Try it in the Inspector.** In the first terminal:

   ```bash
   npx -y @modelcontextprotocol/inspector@2.13.0 uv run clm-server offsite_desk/scenario.toml
   ```

   1. Connect with the **Disconnected** slider.
   2. Open **Tools**. A scenario's main tool is `decide`.
   3. Run `decide` with `My train gets in at 11, so I'll miss the morning session on day one.` in **text**. You
      should see `"route": "Attendance"`, its `confidence`, about 0.9, and the `probabilities` of all four routes.
   4. Try messages of your own.

   When you are done, stop the Inspector (Ctrl-C).

# Part 3: Work together

## 9. Use both servers in one chat

You now have two decision servers: the offsite environment, which weighs venues, and the offsite desk, which routes
the team's messages. A harness can connect to both at once. Here a message goes to the desk, and its route decides
whether the model then asks the offsite environment.

You need three terminals: one for each server, and one for `ollmcp`. All three use the agents' key from section 3,
which only the first terminal has.

1. **Serve the offsite environment**, in the first terminal. Show the key and copy it first:

   ```bash
   echo "$DECISION_SERVER_KEY"
   uv run clm-server my_environment/environment.toml --http
   ```

   You should see `Serving MCP at http://127.0.0.1:8000/mcp`.
2. **Serve the desk**, in the second terminal, on the next port. Give it the key first:

   ```bash
   export DECISION_SERVER_KEY=<the key you copied>
   uv run clm-server offsite_desk/scenario.toml --http --port 8001
   ```

   Loading CLM takes a little while. Wait for `CLM is using its trained heads from scenario.heads` and
   `Serving MCP at http://127.0.0.1:8001/mcp`. If it stops at once with "set DECISION_SERVER_KEY to the key
   callers must send", the key is not set in this terminal.
3. **Open a third terminal**, go to the repository, and give it the same key. A new terminal starts in your home
   folder, and `ollmcp` saves servers for the folder it runs in, so the `cd` matters:

   ```bash
   cd clm-decision-agent        # or wherever you cloned it
   export DECISION_SERVER_KEY=<the key you copied>
   ```

4. **Tell the harness where the desk is.** `offsite` is saved for the repository from section 6; this adds `desk`
   beside it:

   ```bash
   uvx --from mcp-client-for-ollama==0.35.1 ollmcp mcp add --transport http \
       --header "Authorization: Bearer $DECISION_SERVER_KEY" desk http://127.0.0.1:8001/mcp
   ```

5. **Start the harness:**

   ```bash
   uvx --from mcp-client-for-ollama==0.35.1 ollmcp -m qwen3:14b
   ```

   You should see two lines, `Successfully connected to offsite with 9 tool(s)...` and
   `Successfully connected to desk with 4 tool(s)`: 13 tools in one chat.
6. **Ask a question that needs both.** At the `❯` prompt, type this and press Enter:

   ```text
   A team member wrote: 'How do I get to the venue?' Route the message with the desk. If its route is Travel, find which venue the offsite chooses for team T1 for two days, and tell them the venue and the city it is in.
   ```

   Approve each call with `y` and Enter, as in section 6. The model calls `desk.decide`, which returns
   `"route": "Travel"`, then `offsite.scenario_offsite` with `team` T1 and `days` 2. The answer: Canal Rooms, in
   Manchester.
7. **Ask without the instructions.** Type `/new` to start again, then type this and press Enter:

   ```text
   A team member wrote: 'How do I get to the venue?' Route the message with the desk, and reply to them.
   ```

   The model calls `desk.decide` and gets `Travel` again, but stops there: the reply suggests a map, and names no
   venue.
8. **Leave** with `/q`, and leave both servers running.

The two servers never spoke to each other. The harness passed the desk's route to the model, and the model called
the offsite environment only when your question told it to. Each link between servers is the model's choice, and it
can skip one.

## 10. Join them with a tool

To make the link happen every time, the desk can ask the offsite environment itself. A scenario's *informing tool*
runs once CLM has picked a route, and adds facts to the decision. Here you add one to the Travel route that calls the
offsite server, as a harness would. It is the guide's only Python, and it is supplied.

1. **Stop the desk**, in the second terminal (Ctrl-C).
2. **Write the tool.** Open the desk's tools file:

   ```bash
   vi offsite_desk/offsite_desk_tools.py
   ```

   Delete the template's code (in `vi`, `:%d` and Enter). Type `:set paste` and Enter, so `vi` keeps the pasted
   indents as they are, then add the following and save:

   ```python
   """Tools for the offsite desk. offsite_venue asks your offsite environment's server which venue it chose, so a
   travel message is decided with the venue and its city."""
   import asyncio
   from concurrent.futures import ThreadPoolExecutor

   from mcp import Client

   from clm_decision.connection import connect

   SETTINGS: dict = {}


   def configure(settings: dict, scenario_dir) -> None:
       """Take [tools.settings] from scenario.toml: the offsite server's address, and the team and days."""
       SETTINGS.clear()
       SETTINGS.update(settings)


   async def ask_offsite() -> list[str]:
       """Call two of the offsite server's tools, as a harness would."""
       # connect() sends the key in DECISION_SERVER_KEY
       async with Client(connect(SETTINGS["offsite_url"])) as offsite:
           chosen = await offsite.call_tool("scenario_offsite", {"team": SETTINGS["team"], "days": SETTINGS["days"]})
           best = chosen.structured_content["best"]
           if best is None:
               return ["The offsite has no venue yet: every venue was rejected."]
           found = await offsite.call_tool("query_venue_facts", {"venue": best["venue"]})
           venue = found.structured_content["rows"][0]
           return [f"The offsite is at {venue['name']} in {venue['city_name']}."]


   def offsite_venue(request: dict) -> dict:
       """An informing tool: the venue the offsite environment chose, as a fact for the decision."""
       # The desk's own server is already running, so the call to the offsite server runs in a thread of its own
       try:
           with ThreadPoolExecutor(1) as pool:
               facts = pool.submit(asyncio.run, ask_offsite()).result()
       except Exception as error:
           raise RuntimeError(f"the offsite server at {SETTINGS['offsite_url']} did not answer, "
                              "or refused the key") from error
       return {"facts": facts}


   TOOLS = [offsite_venue]
   ```

   `configure` takes the settings you add in step 3. `ask_offsite` calls two of the offsite server's tools,
   `scenario_offsite` and then `query_venue_facts` for the best venue, sending the key in `DECISION_SERVER_KEY`.
   `offsite_venue` is the informing tool: it returns that venue as a fact. `TOOLS` lists the tools the scenario may
   use.
3. **Give it to the desk.** Open the scenario's file:

   ```bash
   vi offsite_desk/scenario.toml
   ```

   Make the lower change first, so the line numbers hold:
   - After line 38, `examples = ["Is there parking at the venue?"]`, add `inform = ["offsite_venue"]`. The tool now
     runs only when the route is Travel.
   - After line 26, `confidence_threshold = 0.6`, add a blank line and:

     ```toml
     [tools]
     module = "offsite_desk_tools"

     [tools.settings]
     offsite_url = "http://127.0.0.1:8000/mcp"
     team = "T1"
     days = 2

     # The venue is a fact for whoever asked, not for any question
     [tools.inform.offsite_venue]
     questions = []
     ```

   Save the file.
4. **Serve the desk again**, with the command from section 9, step 2, and wait for `Serving MCP`.
5. **Ask the short question again.** In the third terminal, start `ollmcp` as in section 9, step 5, and ask the
   question from step 7. Approve the one call, `desk.decide`. Its result now includes the venue:

   ```text
   "informed": [
     {
       "tool": "offsite_venue",
       "status": "done",
       "facts": [
         "The offsite is at Canal Rooms in Manchester."
       ]
     }
   ]
   ```

   and the reply names Canal Rooms, in Manchester. The model made one call; the desk made the other.
6. **See what it costs.** The desk now depends on the offsite server. Stop the server in the first terminal (Ctrl-C)
   and ask again: `offsite_venue` is `failed`, with the error "the offsite server at http://127.0.0.1:8000/mcp did
   not answer, or refused the key", and the route is still Travel.

When you are done, type `/q` in `ollmcp` and stop the desk (Ctrl-C). To remove the saved addresses and key from
`ollmcp`'s settings, run these from the repository:

```bash
uvx --from mcp-client-for-ollama==0.35.1 ollmcp mcp remove offsite
uvx --from mcp-client-for-ollama==0.35.1 ollmcp mcp remove desk
```

If one says "No server named 'desk' found in any scope", it was saved from another folder, most likely your home
folder: run the same command from there.

## Where next

### Route messages: the service desk

A fuller scenario than section 8's: its tools look up which team handles a request, and it opens a ticket in a
stand-in issue tracker. Train it first, as in section 8:

```bash
uv run clm-train examples/service_desk/scenario.toml
uv run python examples/service_desk/mock_tracker.py              # terminal 1: a stand-in issue tracker
npx -y @modelcontextprotocol/inspector@2.13.0 \
    uv run clm-server examples/service_desk/scenario.toml --review    # terminal 2: the MCP Inspector
```

Call `decide` with `text` "I need access to the oncology registry for an audit, needed this week". You should see
the route (Data_Access) and its probabilities, each question's answer, the informing tools' facts, the rules, and the
ticket really opened in the mock tracker. `--review` adds `correct`, which saves the right route, and `agreement`,
which reports how often CLM agrees with your corrections. With `--read-only` instead (not both, since `correct`
writes the record), acting tools are reported `skipped` with the reason "read-only server", so the tracker is not
needed.

To take your own scenario further, with questions, rules and tools that inform and act: the
[walkthrough](walkthrough.md); [fine-tuning](fine-tuning.md) trains CLM on corrections.

### Decide from documents: the handbook

An environment with documents needs PostgreSQL ([handbook](../examples/handbook/README.md)). The Inspector passes on
none of your shell's variables, so start the server through a shell that reads your password file; the password
never reaches the command or the page. You should see 22 tools, 1 resource (`describe`), 3 templates and 1 prompt:

```bash
npx -y @modelcontextprotocol/inspector@2.13.0 sh -c \
    'set -a; . ./.postgres-local.env; exec uv run clm-server examples/handbook/environment.toml'
```

### Call a tool from a script

`--cli` with a method makes one call and prints the result as JSON. `--method tools/list`, `resources/list` and
`prompts/list` list the tools, resources and prompts. A server already on HTTP is reached by address and key:
[serving](serving.md#inspecting-a-server).

```bash
npx -y @modelcontextprotocol/inspector@2.13.0 --cli uv run clm-server examples/tariff/environment.toml \
    --method tools/call --tool-name scenario_sourcing --tool-arg product=PX
```

### Connect real agents

```bash
uv run clm-server my_scenario/scenario.toml --http                   # a shared key, DECISION_SERVER_KEY
uv run clm-server examples/tariff/environment.toml --http --auth oauth \
    --issuer https://login.example.org/realms/corp --audience decisions   # tokens from your identity provider
```

| | |
|---|---|
| HTTP, shared key or OAuth from any OIDC issuer | [serving](serving.md) |
| An MCP registry, so agents find a deployment | `clm-registry`, [registry](registry.md) |
| Tracing | `--trace FILE` records each call's time and caller; `clm-trace-report` summarises it |
| `clm-agent` | Takes a server's URL as well as a file; the key in `DECISION_SERVER_KEY` goes only over https or to this computer |
| Databricks | Not tried yet; [what it needs](serving.md#databricks) |

**A scenario's server acts without asking:** an acting tool runs at once unless the route is uncertain, and calling
`decide` twice acts twice, so point acting tools at real systems with care. An environment's tools only read. Read
[data handling](data-handling.md) before any real text goes in.

All the examples: [examples/README.md](../examples/README.md).

## Reference

### Environment

**An environment is what you define:**

- queries over your data
- actions such as opening a ticket
- rules: DMN tables, calculations and limits

Decisions over an environment come in two styles:

| | **Routing** | **Weighing options** |
|---|---|---|
| Decides | A message's route, many at once | A question with alternatives: "move Product Line X to Region B?" |
| How | CLM picks the route from the message and your informing tools' facts; your acting tools carry it out | Queries supply figures, calculations work out each alternative, rules reject those over a limit and an objective ranks the rest |
| CLM | Ranks the options | Only in a **judge**: a yes/no question of text no rule can read |
| The agent | Talks to the person, acts on the decision | Chooses what to run and reports it; never calculates; every figure is checked |
| File | `scenario.toml` | `environment.toml` |
| Examples | [service desk](../examples/service_desk/README.md), [CrowdStrike day](../examples/crowdstrike/README.md) | [tariff](../examples/tariff/README.md), [new site](../examples/new_site/README.md), [non-competes](../examples/noncompete/README.md), [handbook](../examples/handbook/README.md) |
| Guide | [scenario](scenario.md), [walkthrough](walkthrough.md) | [environment](environment.md) |

`clm-server` serves one file at a time, so the two styles cannot yet share tools. A CLM does not generate text: it
says which listed option fits a situation, with a probability (Kwok et al. 2026,
[Contrastive-LM/CLM](https://github.com/Contrastive-LM/CLM)). This project runs the authors' model with PyTorch, or
community MLX builds on a Mac.

### Installing

CLM needs one of:

| Hardware | Backend | First run downloads | |
|---|---|---|---|
| Mac, Apple Silicon, 16 GB or more | MLX | about 8 GB | |
| Linux, NVIDIA GPU of 24 GB or more | PyTorch | about 16 GB | Set the torch backend in the scenario's `[clm]` table; install a C compiler and Python's headers (`sudo apt install build-essential python3.12-dev` on Ubuntu). A CPU works, slowly: [serving](serving.md#on-linux) |

In a checkout, run `uv sync`, then `uv run <command>`. Installed as a package, the core (about 50 MB) serves
environments without judges; `uvx` runs it uninstalled, so an MCP client or the Inspector can start a server:

```bash
pip install "clm-decision-agent @ git+https://github.com/kvnlng/clm-decision-agent"               # the core
pip install "clm-decision-agent[clm,neo4j,agent] @ git+https://github.com/kvnlng/clm-decision-agent"
uv tool install "clm-decision-agent[clm] @ git+https://github.com/kvnlng/clm-decision-agent"       # commands only
uvx --from "git+https://github.com/kvnlng/clm-decision-agent" clm-server my_environment/environment.toml
uvx --from "clm-decision-agent[documents] @ git+https://github.com/kvnlng/clm-decision-agent" clm-server ...  # an extra
```

| Extra | Adds |
|---|---|
| `clm` | CLM: scenarios, judges, training and the example writer |
| `neo4j` | The Neo4j driver, for a graph in Neo4j |
| `documents` | The PostgreSQL driver and pgvector, for collections of documents |
| `agent` | The Anthropic SDK, for `clm-agent` with Claude; Ollama needs nothing more |

The commands are `clm-server`, `clm-agent`, `clm-new-scenario`, `clm-new-environment`, `clm-synthesize`,
`clm-train`, `clm-evaluate`, `clm-record`, `clm-load-graph`, `clm-load-documents`, `clm-registry`,
`clm-trace-report` and `clm-derive`. Each has `--help`, and one that needs a missing extra says which. The Python
package is `clm_decision`.

### Index of guides

| Guide | What it covers |
|---|---|
| [environment](environment.md) | An environment for weighing options; its keys, limits and figures in the [reference](environment-reference.md) |
| [scenario](scenario.md) | A scenario for routing; its keys and exact rules in the [reference](scenario-reference.md) |
| [walkthrough](walkthrough.md) | A scenario, step by step |
| [fine-tuning](fine-tuning.md) | Training CLM on your routes |
| [models](models.md) | CLM and language models, and where they run |
| [serving](serving.md) | Serving decisions to agents; the flags, OAuth setups and measurements in the [reference](serving-reference.md) |
| [registry](registry.md) | Listing a deployment in an MCP registry |
| [data handling](data-handling.md) | Where text goes; read before using real text |
| [findings](findings.md) | What the benchmark traces showed |
| [portal](portal.md) | An admin page `clm-server` serves, and a chat with a running server |
