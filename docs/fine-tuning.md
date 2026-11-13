# Training CLM for your scenario

As released, CLM is general and often wrong on a specific set of routes. Training fits it to your routes in about a
minute. What training did on the examples: [findings](findings.md#training).

## What is trained

Only CLM's two small heads (about 75 MB together) are trained; the encoder is untouched. Each example is encoded
once, and training adjusts how the vectors are projected so each message lands nearest the right answer.

The route is always trained, in the same heads as every question your examples label and, where examples say which
option was right, the choice among a route's options. Unlabelled questions and the tool check stay as released;
`decision-train` reports how far their answers moved.

Rare answers count as much as common ones: with one example in ten urgent, each urgent one weighs nine times as much,
and results are reported per answer ("4 of 5"), or "never urgent" would score 90%.

## Steps

**1. Get labelled examples**, from either source or both:

- `uv run decision-synthesize <scenario>` has the language model write messages for each route, in eight styles, into
  `<scenario>.examples.jsonl`. `[synthesize] messages` says who is writing and to what, such as "messages that customers
  might send to an online shop's help desk". Read some of the results; edit the file freely, or add lines:
  `{"text": "<a message>", "route": "<a route's name>"}`
- Correct decisions in review mode: start the server with `--review` in the MCP Inspector
  (`npx -y @modelcontextprotocol/inspector@2.13.0 uv run decision-server <scenario> --review`), call `decide` with a
  message, then `correct` with the same text and the right route. Every corrected route is a real example. A corrected
  answer or option the scenario can no longer take is left out on its own, and `decision-train` says how many.

A line can also label each question's right answer and, on a route with options, the right option. Only what a line
labels is trained from it:

```json
{"text": "The kettle arrived broken and I need the money back today", "route": "Refund",
 "answers": {"urgent": true, "upset": 1}}
{"text": "The lamp came with a cracked shade, can you send another?", "route": "Replace",
 "facts": ["Order A102, a desk lamp, was delivered 2 days ago."],
 "options": [{"id": "L-20", "text": "The same lamp, in stock, delivered tomorrow"},
             {"id": "L-21", "text": "The same lamp in black, delivered in 5 days"}],
 "option": "L-20"}
```

A yes/no answer is `true` or `false`, a score the level's number counting from 0, a choice the option's key.

| `facts` | Value | Who hears it |
|---|---|---|
| As a list | what CLM read with the request, as your tools would find them | every question |
| By tool, as corrections save them: `{"situation": ["..."], "lookup": ["..."]}` | the same | each question hears only what its `[tools.inform]` settings give it; the facts of `[routing] inform` tools join the text the route trains on, as when deciding |

A line naming a question the scenario lacks, or an answer it cannot take, stops `decision-train` with the line's number.
Lines of a route the scenario no longer has are left out, and `decision-train` says how many for each route.

**2. Say where to save the result**, in the scenario:

```toml
[clm]
heads = "scenario.heads"
```

**3. Train.**

```bash
uv run decision-train <scenario>
```

It prints accuracy before and after on held-back examples, and how far your other questions' answers moved. If the
held-back examples did not improve, nothing is saved.

**4. Start the server.** It says at start-up whether it is using the trained heads.

Then loop: generate, train, try and correct messages in the Inspector, evaluate, adjust, train again.

## Reading the numbers

| Caution | Detail |
|---|---|
| Generated examples flatter the result: the held-back ones come from the same model and styles as the training ones | Believe a test on real or hand-written messages; keep such a set aside and never train on it |
| Small tests move | On a test of 20 messages, one or two right more or less can be the run, not the change ([findings](findings.md#training)) |
| Look at confidence as well as accuracy | A wrong route below the confidence threshold is marked uncertain and runs no action; a confident wrong one acts. Run `decision-evaluate` on your corrections to choose the threshold |

## Limits and when to train again

- Train again when a route's description or name or the routing question changes, when a trained question's wording
  changes (untrained questions can change freely), when a route's options instructions change and its ranking was
  trained, when you change the CLM build, and when you have corrected more real messages. Trained heads fit the exact
  wording, so reworded options can score below the untrained model ([findings](findings.md#training)). The server
  detects a change, says so, and uses the released heads until you retrain.
- Training runs with either backend, on the machine you serve from. Heads trained with one backend are not used by the
  other ([models.md](models.md#heads-belong-to-one-backend)).
- One example in five of the generated set is held back, chosen by a hash of its text, so the same examples are held
  back on every run. Reviewed routes are always trained on.
- After training, the "near-identical message" matching that reuses corrections works on different vectors. A spot
  check looked fine at the default `match_threshold`; it has not been measured properly.
- Trained heads are made from your examples and corrections. Treat the folder with the same care as that text
  ([data-handling.md](data-handling.md)).
