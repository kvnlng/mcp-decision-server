# What we measured

These are the measurements we made on the examples; the guides link here rather than quote them. The CrowdStrike example
is also the benchmark: runs were traced (`decision-server --trace`) before and after each change; its own numbers are in
the [example's README](../examples/crowdstrike/README.md).

## Where the time goes

| Measurement | Result |
|---|---|
| CLM reading the texts, share of a `decide_many` call | 96–98% on the A100 and H100; all but 3 ms a call on the Mac |
| The tools (searching for journeys, holding seats) | 1–3% |
| H100 GPU busy, sampled every 5 seconds, day's average | 82%; the server used one CPU core, mostly waiting for the GPU |
| A second copy of the model on the same GPU | +4%: one copy already fills it |

The GPU is the limit, not the CPU; faster decisions come from encoding less, or better.

## What each change bought

The figures are decisions a second, `decide_many`'s own rate from the traces (the replay's scoreboard in the
example's README counts slightly more):

| Change | Before | After | Measured on |
|---|---|---|---|
| The tools share one HTTP client instead of making one per call (about 17 ms each on a cloud VM) | 23 | 55 | service desk, A100, 100 messages a call |
| Each message encoded once for all its questions (a shared start) | 55 | 72 | the same |
| Texts packed end to end in rows, no padding (42% of the tokens had been padding) | 10.9 | 12.5 | CrowdStrike, A100: before, the day's first 40,918 bookings; after, its first 3,000, rows of 4,096 tokens. Not the same work |
| Every request's options ranked in the questions' pass, not about 70 small passes a call | 12.5 | 17.4 | CrowdStrike, A100, first 3,000 bookings, rows of 4,096 |
| Rows of 2,048 tokens instead of 4,096 | 17.4 | 18.6 | the same |
| The H100 instead of the A100 | 18.6 | 45.8 | the same, rows of 2,048 |

The H100 decided the whole day at 50.1 a second.

- Packing alone bought little: with padding gone, ranking each request's options in its own small pass cost more than
  everything else.
- Rows of 1,024 or 2,048 tokens were fastest on both GPUs; on the A100, 4,096 was 6–7% slower and 8,192 25% slower,
  because attention covers the whole row.
- Before packing, a shared start took a second pass, slowing a single small decision, so it was used only with 1,024
  tokens or more to encode. In a packed row the start and the questions go in one pass, shared whenever texts in a row
  start alike.
- The day's busiest minute needs 10.7 decisions a second. The Mac (3.6) falls behind at the peaks by up to 4.5 minutes;
  one A100 keeps up; an H100 decides 4.8 times what the peak needs.

## What broke

| What | Where | Fix |
|---|---|---|
| The vector cache reached its 50,000 entries and evicted a text the same call was about to use; the run stopped with a `KeyError` | A100, first whole-day run, 28 minutes in, at 09:12 of the simulated day | The cache evicts only after the call has what it needs |
| Packed rows were right only with SDPA attention, which honours the mask keeping packed texts apart; eager attention would have added the mask to its scores, and every text would have read its neighbours | A review caught it before any wrong number was published | The encoder loads with SDPA and refuses anything else |
| Python 3.15 was picked; torch has no wheels for it yet | A fresh install | Python is capped below 3.15 |
| Packed and alone differ a little: encoded in a batch, a text's numbers come out very slightly different, and a decision on the edge between two routes can flip | Service desk, 318 messages: 2 flipped on the Mac, 1 on the A100, all near ties well below the confidence threshold ([serving.md](serving.md)). CrowdStrike: rows of different sizes gave 2,393 to 2,404 right of 3,000; which decisions changed was not traced. Heads trained again on the H100 gave 2,379 against the A100's 2,399; whether training or the GPU's rounding made the difference was not measured | None |

## What the measurements say about the decisions

| Finding | Figures |
|---|---|
| Train CLM first | Service desk, 55 held-back generated examples: 51% of routes right as released, 98% trained |
| A GPU makes CLM fast | The day replayed: 3.6 decisions a second on the Mac, 19.2 on an A100 80 GB, 51.1 on an H100 80 GB SXM (torch, bf16) |
| CLM's probabilities are relative | Tune thresholds on labelled cases. An untrained judge leaned one way: on the tariff example's supplier news, harmless items scored 0.47 to 0.79 and risks 0.84 to 0.98 (`examples/tariff/judge_news.py`) |
| Many bookings go to a person | Threshold 0.6: 5% of the day's bookings got a wrong route not marked uncertain; 46% were marked uncertain, most answered rightly. `decision-evaluate --cases` puts the lowest threshold keeping the routes 90% right at 0.63: better-trained heads are the fix, not a lower threshold |
| Claude was more accurate, and on the Mac faster | 600 unseen cases (CLM as released got 17%): Sonnet 5.5 82% of routes right, Haiku 5.5 79%, CLM 75%; Sonnet took 267 ms a decision, CLM 300 ms. CLM costs nothing per decision, keeps the messages on the machine and marks most of its wrong answers uncertain |
| `check_call` is weak as a yes or no | On an M5 Max with trained heads, approving at 0.5, over the 200 check cases whose answer is Rebook or Refund, with a rebooking and a refund proposed for the same passenger: it approved the right one and refused the wrong one for 114 of 200; compared with each other, 169 were told apart. `decide` was right for 162 and marks most of its mistakes uncertain |

From the local-document examples ([examples/noncompete](../examples/noncompete/README.md),
[examples/handbook](../examples/handbook/README.md)):

| Finding | Figures |
|---|---|
| Local documents made answers better sourced, not different | Non-compete: the rules carry the statutes, so with or without the document tools Claude and gemma4 gave every state's verdict rightly. On the Texas question Claude reached the same verdict either way, citing 13 opinions the tools returned against 9 |
| A large tool result can silently lose a local model its question | `scenario_narrow_to_enforce` returned about 1 MB; Ollama cuts the conversation to its context window, and gemma4 answered "please provide the question". At about 0.7 MB it answered, in over 7 minutes. Neither the scenario nor the agent warns yet |
| The CLM's two document judgements do not separate their labels | "Broader than needed" ordered 6 of 28 labelled pairs rightly, worse than chance; "departs" 28 of 40. No rule reads either |
| With a company's own documents, the missing answer is the gap, not a wrong one | Made-up handbook, no tools: Claude and gemma4 said they could not know (Claude gave 1 of 17 figures, the public IRS limit; gemma4 none). With supplied rules, 16 of 17 right and none of the 17 stated wrongly; the handbook added the one question no rule covers, and the policy text. One run each |
| Small results suit a local model | Handbook questions: gemma4 about as fast as Claude (13 to 17 s) and as accurate with the rules only (16 of 17 each); with the handbook 14 of 17 against Claude's 17 |
| Rules Claude derived from the handbook matched the hand-written ones | Claude's five tables and six plan figures, all 11, matched the hand-written ones over a grid of every bound; all 11 passed the first check (3 on the second try). Answering from them, Claude gave 17 of 17 key figures, as with the hand-written rules; gemma4 14 of 17, none wrong. A stricter check (a range's upper bound, whole words in quotes, figures in a rule's reason; dates, bare years and section references exempt) still passes all 11 |
| Fully local derivation let wrong figures through the check | gemma4 derived 9 of 11 that pass the stricter check (10 of 11 the first), but two are wrong: it read "100% of the first 3% ... 50% of the next 3%" as tiers of 100% and 50% of pay. Every figure is in the quote, so the check cannot tell a rate from a width: it catches figures not in the document, not figures in the wrong place, which is the person's part. The scripted approval passed them; gemma4 answering from its own layer stated two wrong figures as fact (a $3,680 match where the key says $3,220). gemma4 also needed thinking off: with thinking on, under a JSON schema, it ran past 100,000 tokens without answering |
| A second reading caught the misplaced figures when Claude read, only partly when a local model did | `decision-derive check` can have a second model derive each entry again without the first answer; a disagreement fails the check. On gemma4's layer, Claude caught both wrong tiers and flagged none of the 9 right entries; granite4:micro caught both but flagged 5 right entries (it read the rates as 3); qwen3:14b caught one and agreed with the other, making gemma4's own mistake, so a wrong figure passed both checks. gemma4 reading Claude's all-right layer raised 3 false alarms of 11. Agreement is not proof; every entry still needs a person. One run each ([a second reading](../examples/handbook/README.md#a-second-reading)) |
| The handbook alone, with the calculations, was nearly enough for Claude and not for gemma4 | No rules: Claude gave 16 of 17 and recognised the superseded 2024 edition as replaced; gemma4 10 of 17 and one wrong figure, passing the match's rates to the calculation wrongly |

## Training

On an earlier, five-route version of the service desk example, CLM as released got 8 of 20 hand-written messages right,
and the trained result on those 20 was 16 or 17 depending on the run. On the current version's 55 held-back generated
examples, with the route, urgency and identifiable trained together (each count is the number right of all examples with
that answer):

| | Released | Trained |
|---|---|---|
| Route | 49% (balanced) | 96% (53 of 55) |
| Urgency: no deadline | 9 of 49 | 47 of 49 |
| Urgency: within weeks | 0 of 1 | 0 of 1 |
| Urgency: within days | 5 of 5 | 4 of 5 |
| Identifiable: no | 17 of 42 | 40 of 42 |
| Identifiable: yes | 13 of 13 | 13 of 13 |
| Hand-written test messages (17) through the server, route | | 15 |

- The same 55 held-back examples appear three times on this page, from different runs: the route alone (51% as released,
  98% trained, in the table above), the route with the questions (this table, balanced) and the torch backend (55%
  released, under backends checked).
- Trained heads fit the exact wording: in an early test, rewording a route's options after training dropped accuracy
  below the untrained model.
- Training the questions did not cost the route: trained on the route alone it was 54 of 55 and 15 of 17.
- "Within weeks" has two examples in all, one held back, so it cannot be learned. Label more of a rare answer before
  trusting it.

Two earlier measurements on a similar problem (issue reports, 450 generated examples) showed that most of the gain
arrived by 100 to 200 examples, and that a plain classifier on the encoder's vectors did about as well as trained heads;
the heads were chosen so that CLM does every job through one model. `decision-train` prints the classifier's accuracy
beside its own.

## Backends checked

On the service desk example, unless a row says otherwise:

| Check | Result |
|---|---|
| Torch on a Mac's GPU against the MLX 8-bit build, released heads, 81 requests | Same route for 79; largest difference in a route's probability 0.06 |
| Training with torch on a Mac | 55% → 98% on held-back examples; 15 of 17 hand-written messages |
| Torch on Linux (arm64), in Docker, on the CPU: the slow test through the server, released heads | Passes: 11 of 17 hand-written messages, in about 5 minutes on 2 CPUs. The Mac's GPU got 12; the difference is a near tie |
| An Intel Linux image (amd64) | Installs, with PyTorch's CUDA 13.0 build. CLM was not run in it |
| Torch on an NVIDIA A100 80GB (Azure NC24ads_A100_v4, Ubuntu, driver 580): the slow test through the server, released heads | Passes: 12 of 17, as on the Mac's GPU. About 40 ms a decision; the model loads in 7 seconds once downloaded. The fast tests pass (241, with 2 MLX-only ones skipped) |
| Torch in Docker on the A100 (an image since removed), with the GPU: the same slow test | Passes: 12 of 17 |
| Memory on the A100 | CLM used at most 14.4 GB of GPU memory while deciding and 15.2 GB while training |
| Training on the A100 | 55% → 98% on held-back examples, kept after the same pass as on the Mac; 15 of 17 hand-written messages; 20 seconds, loading the model included |
| Torch on an NVIDIA H100 80GB SXM (DigitalOcean, Ubuntu 22.04, driver 580, Python 3.13): the CrowdStrike example, trained and replayed for the whole day | Training 2 min 40 s with the download; 76% on held-back examples as on the A100; 99,806 decisions at 51.1 a second |

## Serving speed

The table gives decisions a second, with encoding's share of the time in brackets, on the service desk example's 318
messages. Each run was in a fresh server, measured before packing ([how a batch is
packed](serving-reference.md#one-at-a-time-or-many-at-once)) and not measured again:

| Calls | M5 Max, 64 GB, MLX | A100 80 GB, torch |
|---|---|---|
| `decide`, one message at a time | 14.7 (95%) | 19.8 (94%) |
| `decide_many`, 100 messages a call | 22.4 (93%) | 71.6 (87%) |

| Measured | Result |
|---|---|
| Row size, A100 | 1,024 and 2,048 tokens equally fast; 4,096 7% slower; 8,192 25% slower: the mask makes attention cover the whole row |
| Tools' share, A100 | The service desk's tools at first made a new HTTP client per call, about 17 ms each, which held `decide_many` to 23 a second until they shared one ([scenario reference](scenario-reference.md#tools)). Their share grows as CLM gets faster |
| Packing's effect on routes | A text's numbers differ very slightly when it is encoded with others, so a near tie can flip. 2 of the 318 did on the Mac and 1 on the A100, all about 0.50 against 0.49, well below the confidence threshold; no acting tool ran |
| Holding the lock | A `decide_many` call holds CLM for its batch, so other calls wait: 1,000 requests take about 20 seconds on the A100 |
| H100 80 GB (SXM) | The CrowdStrike example decided 2.5 times as fast as on the A100, 46.6 against 18.8 a second on the same 3,000 bookings, and the whole day of 99,806 in 32.5 minutes ([its README](../examples/crowdstrike/measurements.md#the-whole-day-on-a-data-centre-gpu)) |

## Ask's starter model

The portal's starter model for Ask, `granite4:micro`, beat `qwen3:4b` and `llama3.2:3b`: fastest, and the only one to
call `decide`. The tariff and service desk examples' servers, three questions, once each:

| Question | `granite4:micro`, local, free | `claude-opus-5-5`, paid |
|---|---|---|
| Who supplies Product Line X's components? | Right | Right |
| Should sourcing move to Region B? | Passed the product's name, not its id `PX`; every branch failed | Right: 50%, and why 100% was rejected |
| Service desk: who handles a registry request? | Right route and ticket, but rewrote the ticket's address | Right, and did not claim more than the result showed |

- **A weak answer may be the model, not your server:** every miss was the small model's; Claude got all three on the
  same tools. Try a larger model before changing tools.
- **A small model shows unclear descriptions:** two passed a component's name, not its id; "give the id, such as C1" in
  the tariff descriptions fixed `granite4:micro`. Test with both sizes.
- **Speed is similar:** 4 to 7 seconds a question for `granite4:micro` on a Mac, about 10 for Claude.
