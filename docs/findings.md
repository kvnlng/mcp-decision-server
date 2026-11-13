# Measurements of the decision framework

## Abstract

We measured the framework on its examples:

- how fast and how accurately CLM routes messages, and what training does;
- which backends and GPUs it runs on;
- how an agent using Claude or a local model answers with and without a company's own documents and derived rules;
- whether DMN files exported by other tools load.

**Training.** Training CLM on generated examples lifted the service desk's routes from about half right to 96–98%
right on held-back examples.

**Speed.** On the CrowdStrike example's data-centre GPUs, encoding the texts took 96–98% of a call's time, so the GPU
sets the speed. Replaying its day of bookings, the Mac decided 3.6 a second, an A100 19.2 and an H100 51.1; only the
H100 decided the whole day of 99,806. On the CrowdStrike benchmark, ranking
every request's options in one pass and smaller rows took the A100 from 12.5 to 18.6 decisions a second; the H100
reached 45.8.

**Accuracy.** In one comparison on 600 unseen cases, Claude was more accurate than trained CLM, 82% against 75%, and,
at 8 calls at once against CLM on the Mac, faster. CLM costs nothing per decision, keeps the messages on the machine and
marks most of its wrong answers uncertain.

**Documents and derived rules.** With a made-up company's rules as tools, Claude and a local model each gave 16 of 17
figures right, in one run.
Rules Claude derived from a handbook matched the hand-written ones; rules a local model derived passed the mechanical
check with two wrong figures, which is why a person approves every derived rule.

**DMN.** Of 16 DMN files exported by other tools, chosen to cover their features, 6 load and 10 are refused, each
naming why; 2 of the 6 can be served without editing.

## Methodology

### Examples and data

| Example | Data | Used for |
|---|---|---|
| Service desk (scenario) | 318 messages; 55 generated examples held back from training; 17 hand-written test messages | Training, backends, serving speed, Ask's starter model |
| CrowdStrike (scenario) | A replayed day of 99,806 bookings (the Mac replayed Atlanta's 9,704, the A100 the first 27,511, the H100 all); the first 3,000; 600 unseen check cases, 200 of them with the answer Rebook or Refund | Serving speed, accuracy against Claude, `check_call` |
| Tariff (environment) | Made-up suppliers and supplier news | The untrained judge; Ask's starter model |
| Non-compete (environment and documents) | Statutes and court opinions in a local document store | Answers with and without document tools |
| Handbook (environment and documents) | A made-up employee handbook; 17 key figures; 11 rule and plan entries | Answers from rules, documents or both; derived rules and their checks |
| Exported DMN files | 16 files from the DMN TCK, Camunda and Kogito ([their sources](../tests/dmn/exported/README.md)) | Which real files the DMN reader loads |

The CrowdStrike flights, the non-compete statutes and its 4,807 court opinions (Caselaw Access Project) are real; the
messages, bookings, passengers, companies and handbook are made up or generated. The CrowdStrike example's own figures
are in [its README](../examples/crowdstrike/README.md).

### Hardware and software

| Machine | Backend |
|---|---|
| Apple M5 Max, 64 GB | MLX (8-bit build); torch on the Mac's GPU for comparison |
| NVIDIA A100 80 GB (Azure NC24ads_A100_v4, Ubuntu, driver 580) | torch |
| NVIDIA H100 80 GB SXM (DigitalOcean, Ubuntu 22.04, driver 580, Python 3.13) | torch, bf16 |
| Linux arm64 in Docker, 2 CPUs | torch on the CPU |
| An Intel (amd64) Linux image | Installed only; CLM was not run |

Claude Sonnet and Haiku ran with 8 calls at once.

The language models were:

- **Through Anthropic's API:** Claude Sonnet 5.5, Haiku 5.5 and Opus 5.5.
- **Locally through Ollama:** gemma4, granite4:micro, qwen3:14b, qwen3:4b and llama3.2:3b.

### Procedure

- **Speed.** Runs were traced with `decision-server --trace` before and after each change. Decisions a second are
  `decide_many`'s own rate from the traces; the replay's scoreboard in the CrowdStrike README counts slightly more. Each
  service desk speed run was in a fresh server, before packing, and was not measured again.
- **Accuracy.** `decision-train` scored routes and answers on examples held back from training; each count is the
  number right of all examples with that answer. Hand-written and unseen cases were decided through the server, and
  `decision-evaluate --cases` gave the CrowdStrike threshold.
- **Documents and rules.** Each question was asked with and without the document tools and the rules, and the stated
  figures were compared with the handbook's answer key. Derived rules were compared with the hand-written ones over a
  grid of every bound. These comparisons ran once each.
- **DMN files.** Each exported file was loaded with the reader, and through an environment for those that load. The
  TCK's models were evaluated against the TCK's expected results; the other two were spot-checked on a few inputs
  against what their rows say.

## Results

### Training

On an earlier, five-route version of the service desk example, CLM as released got 8 of 20 hand-written messages right,
and the trained result on those 20 was 16 or 17 depending on the run.

On the current version's 55 held-back generated examples, the route was trained alone first: 51% right as released,
98% trained. With the route, urgency and identifiable trained together:

| | Released | Trained |
|---|---|---|
| Route | 49% (balanced) | 96% (53 of 55) |
| Urgency: no deadline | 9 of 49 | 47 of 49 |
| Urgency: within weeks | 0 of 1 | 0 of 1 |
| Urgency: within days | 5 of 5 | 4 of 5 |
| Identifiable: no | 17 of 42 | 40 of 42 |
| Identifiable: yes | 13 of 13 | 13 of 13 |
| Hand-written test messages (17) through the server, route | | 15 |

- Training the questions did not cost the route: trained on the route alone it was 54 of 55 and 15 of 17.
- "Within weeks" has two examples in all, one held back.
- In an early test, rewording a route's options after training dropped accuracy below the untrained model.
- Two earlier measurements on a similar problem, issue reports with 450 generated examples, showed most of the gain by
  100 to 200 examples. They also showed that a plain classifier on the encoder's vectors did about as well as trained
  heads. The heads were chosen so that CLM does every job through one model; `decision-train` prints the classifier's
  accuracy beside its own.

### Backends checked

On the service desk example, unless a row says otherwise:

| Check | Result |
|---|---|
| Torch on a Mac's GPU against the MLX 8-bit build, released heads, 81 requests | Same route for 79; largest difference in a route's probability 0.06 |
| Training with torch on a Mac | 55% → 98% on held-back examples; 15 of 17 hand-written messages |
| Torch on Linux (arm64), in Docker, on the CPU: the slow test through the server, released heads | Passes: 11 of 17 hand-written messages, in about 5 minutes on 2 CPUs. The Mac's GPU got 12; the difference is a near tie |
| An Intel Linux image (amd64) | Installs, with PyTorch's CUDA 13.0 build. CLM was not run in it |
| Torch on the A100: the slow test through the server, released heads | Passes: 12 of 17, as on the Mac's GPU. About 40 ms a decision; the model loads in 7 seconds once downloaded. The fast tests pass (241, with 2 MLX-only ones skipped) |
| Torch in Docker on the A100 (an image since removed), with the GPU: the same slow test | Passes: 12 of 17 |
| Memory on the A100 | CLM used at most 14.4 GB of GPU memory while deciding and 15.2 GB while training |
| Training on the A100 | 55% → 98% on held-back examples, kept after the same pass as on the Mac; 15 of 17 hand-written messages; 20 seconds, loading the model included |
| Torch on the H100: the CrowdStrike example, trained and replayed for the whole day | Training 2 min 40 s with the download; 76% on held-back examples as on the A100; 99,806 decisions at 51.1 a second |

The released service desk scored 55% on the held-back examples under torch, against 51% in the route-only run above.

### Serving speed

**Where the time goes.**

| Measurement | Result |
|---|---|
| CLM reading the texts, share of a `decide_many` call | 96–98% on the A100 and H100; all but 3 ms a call on the Mac |
| The tools (searching for journeys, holding seats) | 1–3% |
| H100 GPU busy, sampled every 5 seconds, day's average | 82%; the server used one CPU core, mostly waiting for the GPU |
| A second copy of the model on the same GPU | +4%: one copy already fills it |

**The service desk, before packing.** Decisions a second, with encoding's share of the time in brackets, on its 318
messages ([how a batch is packed](serving-reference.md#one-at-a-time-or-many-at-once)):

| Calls | M5 Max, 64 GB, MLX | A100 80 GB, torch |
|---|---|---|
| `decide`, one message at a time | 14.7 (95%) | 19.8 (94%) |
| `decide_many`, 100 messages a call | 22.4 (93%) | 71.6 (87%) |

**What each change bought**, in decisions a second:

| Change | Before | After | Measured on |
|---|---|---|---|
| The tools share one HTTP client instead of making one per call (about 17 ms each on a cloud VM) | 23 | 55 | Service desk, A100, 100 messages a call |
| Each message encoded once for all its questions (a shared start) | 55 | 72 | The same |
| Texts packed end to end in rows, no padding (42% of the tokens had been padding) | 10.9 | 12.5 | CrowdStrike, A100: before, the day's first 40,918 bookings; after, its first 3,000, rows of 4,096 tokens. Not the same work |
| Every request's options ranked in the questions' pass, not about 70 small passes a call | 12.5 | 17.4 | CrowdStrike, A100, first 3,000 bookings, rows of 4,096 |
| Rows of 2,048 tokens instead of 4,096 | 17.4 | 18.6 | The same |
| The H100 instead of the A100 | 18.6 | 45.8 | The same, rows of 2,048 |

**Other measurements:**

- **Row size.** Rows of 1,024 or 2,048 tokens were fastest on both GPUs. On the A100, 4,096 was 6–7% slower and 8,192
  25% slower.
- **Shared starts.** Before packing, a shared start took a second pass, slowing a single small decision, so it was
  used only with 1,024 tokens or more to encode. In a packed row the start and the questions go in one pass, shared
  whenever texts in a row start alike.
- **The replay.** 3.6 decisions a second on the Mac (Atlanta's 9,704 bookings), 19.2 on the A100 (the first 27,511; the
  run was stopped to change machines) and 51.1 on the H100 (the whole day).
- **The whole day.** The H100 decided the day's 99,806 bookings in 32.5 minutes, at 50.1 to 51.1 a second (the traces
  and the replay's scoreboard count slightly differently)
  ([measurements](../examples/crowdstrike/measurements.md#the-whole-day-on-a-data-centre-gpu)). On the same 3,000
  bookings it was 2.5 times as fast as the A100: 46.6 a second against 18.8.
- **The peak.** The day's busiest minute needs 10.7 decisions a second. The Mac (3.6) falls behind at the peaks by up to
  4.5 minutes; one A100 keeps up; an H100 decides 4.8 times what the peak needs.
- **Holding the lock.** A `decide_many` call holds CLM for its batch, so other calls wait: 1,000 requests take about 20
  seconds on the A100.

### Decision quality

| Finding | Figures |
|---|---|
| Training lifts the routes | Service desk, 55 held-back generated examples: 51% of routes right as released, 98% trained |
| CLM's probabilities are relative | Thresholds are tuned on labelled cases. An untrained judge leaned one way: on the tariff example's supplier news, harmless items scored 0.47 to 0.79 and risks 0.84 to 0.98 (`examples/tariff/judge_news.py`) |
| Many bookings go to a person | CrowdStrike, threshold 0.6: 5% of the day's bookings got a wrong route not marked uncertain; 46% were marked uncertain, most answered rightly. `decision-evaluate --cases` puts the lowest threshold keeping the routes 90% right at 0.63: better-trained heads are the fix, not a lower threshold |
| Claude against CLM | 600 unseen cases (CLM as released got 17%): Sonnet 5.5 82% of routes right, Haiku 5.5 79%, trained CLM 75%. Sonnet took 267 ms a decision at 8 calls at once, CLM 300 ms on the Mac |
| `check_call` as a yes or no | On the M5 Max with trained heads, approving at 0.5, over the 200 check cases whose answer is Rebook or Refund, with a rebooking and a refund proposed for the same passenger: it approved the right one and refused the wrong one for 114 of 200; compared with each other, 169 were told apart. `decide` was right for 162 and marked most of its mistakes uncertain |
| Packed against alone | A text's numbers differ very slightly when it is encoded with others. Service desk, 318 messages: 2 routes flipped on the Mac and 1 on the A100, all near ties of about 0.50 against 0.49, below the confidence threshold, and no acting tool ran ([serving.md](serving.md)). CrowdStrike: rows of different sizes gave 2,393 to 2,404 right of 3,000; which decisions changed was not traced. Heads trained again on the H100 gave 2,379 against the A100's 2,399 |

### Local documents and derived rules

From [examples/noncompete](../examples/noncompete/README.md) and [examples/handbook](../examples/handbook/README.md):

| Finding | Figures |
|---|---|
| Documents made answers better sourced, not different | Non-compete: the rules carry the statutes, so with or without the document tools Claude and gemma4 gave every state's verdict rightly. On the Texas question Claude reached the same verdict either way, citing 13 opinions the tools returned against 9 |
| A large tool result lost a local model its question | `scenario_narrow_to_enforce` returned about 1 MB; Ollama cut the conversation to its context window, and gemma4 answered "please provide the question". At about 0.7 MB it answered, in over 7 minutes |
| CLM's two document judgements did not separate their labels | "Broader than needed" ordered 6 of 28 labelled pairs rightly; "departs" 28 of 40 |
| Without the company's documents, the answer is missing, not wrong | Made-up handbook, no tools: Claude and gemma4 said they could not know (Claude gave 1 of 17 figures, the public IRS limit; gemma4 none). With supplied rules, 16 of 17 right and none of the 17 stated wrongly; the handbook added the one question no rule covers, and the policy text |
| Small results suit a local model | Handbook questions: gemma4 about as fast as Claude (13 to 17 s) and as accurate with the rules only (16 of 17 each); with the handbook, 14 of 17 against Claude's 17 |
| The handbook alone, with the calculations, was nearly enough for Claude and not for gemma4 | No rules: Claude gave 16 of 17 and recognised the superseded 2024 edition as replaced; gemma4 10 of 17 and one wrong figure, passing the match's rates to the calculation wrongly |
| Rules Claude derived matched the hand-written ones | Claude's five tables and six plan figures, all 11, matched over a grid of every bound; all 11 passed the first check (3 on the second try). Answering from them, Claude gave 17 of 17 key figures, as with the hand-written rules; gemma4 14 of 17, none wrong. A stricter check (a range's upper bound, whole words in quotes, figures in a rule's reason; dates, bare years and section references exempt) still passes all 11 |
| Fully local derivation let wrong figures through the check | gemma4 derived 9 of 11 that pass the stricter check (10 of 11 the first), but two are wrong: it read "100% of the first 3% ... 50% of the next 3%" as tiers of 100% and 50% of pay. The scripted approval passed them, and gemma4 answering from its own layer stated two wrong figures as fact (a $3,680 match where the key says $3,220). With thinking on, under a JSON schema, gemma4 ran past 100,000 tokens without answering |
| A second reading caught the misplaced figures when Claude read, only partly when a local model did | `decision-derive check` can have a second model derive each entry again without the first answer; a disagreement fails the check. On gemma4's layer, Claude caught both wrong tiers and flagged none of the 9 right entries; granite4:micro caught both but flagged 5 right entries (it read the rates as 3); qwen3:14b caught one and agreed with the other, making gemma4's own mistake, so a wrong figure passed both checks. gemma4 reading Claude's all-right layer raised 3 false alarms of 11 ([a second reading](../examples/handbook/README.md#a-second-reading)) |

### Ask's starter model

`granite4:micro` was fastest of `granite4:micro`, `qwen3:4b` and `llama3.2:3b`, and the only one to call `decide`. On
the tariff and service desk examples' servers, three questions, once each:

| Question | `granite4:micro`, local, free | `claude-opus-5-5`, paid |
|---|---|---|
| Who supplies Product Line X's components? | Right | Right |
| Should sourcing move to Region B? | Passed the product's name, not its id `PX`; every branch failed | Right: 50%, and why 100% was rejected |
| Service desk: who handles a registry request? | Right route and ticket, but rewrote the ticket's address | Right, and did not claim more than the result showed |

Answers took 4 to 7 seconds a question for `granite4:micro` on a Mac, and about 10 for Claude.

### DMN files exported by other tools

| Outcome | Files |
|---|---|
| Load and give the TCK's expected results | 4 TCK models (simple table, multiple outputs, FIRST, COLLECT) |
| Load, and answer a few spot checks as their rows say | Camunda's `Example.dmn`, Kogito's `habitability.dmn` |
| Load and can be served unedited | 2 of the 6, Camunda's and Kogito's: the TCK's four name their inputs `Age`, which a tool argument cannot be |
| Refused: several decisions | Camunda's dinner decisions (2), Kogito's traffic violation (2) and loan eligibility (4) |
| Refused: another expression language | Camunda's JUEL and groovy tables |
| Refused: not a decision table | A TCK literal expression; a Kogito context |
| Refused: unsupported hit policy or entry | TCK `ANY` and `COLLECT` with `MIN`; a Kogito entry `? = Applicant.id` |

None of the TCK's cases reached a table's default outputs, so only the unit tests cover them.

### Failures found

| What | Where | Fix |
|---|---|---|
| The vector cache reached its 50,000 entries and evicted a text the same call was about to use; the run stopped with a `KeyError` | A100, first whole-day run, 28 minutes in, at 09:12 of the simulated day | The cache evicts only after the call has what it needs |
| Packed rows were right only with SDPA attention, which honours the mask keeping packed texts apart; eager attention would have let every text read its neighbours | A review caught it before any wrong number was published | The encoder loads with SDPA and refuses anything else |
| Python 3.15 was picked; torch has no wheels for it yet | A fresh install | Python is capped below 3.15 |
| The service desk's tools made a new HTTP client per call, about 17 ms each, holding `decide_many` to 23 a second | A100 | The tools share one client ([scenario reference](scenario-reference.md#tools)) |
| The DMN reader took the first decision table of a file of several decisions without a word: from Camunda's dinner decisions the Beverages table, whose input `desiredDish` is the other decision's answer; from Kogito's traffic violation the Fine table, dropping the decision built on it | Testing exported files. An environment would still have refused both tables, as their inputs are not lower-case names | Such files are refused |

## Discussion

**The GPU is the limit, not the CPU.** Encoding takes almost all of a call's time, and one copy of the model already
fills the GPU, so faster decisions come from encoding less or encoding better. That is what the gains came from:

- **Packing without padding.** On its own it bought little, because ranking each request's options in its own small
  pass then cost more than everything else. Ranking them in the questions' pass made packing pay.
- **Row size.** Smaller rows were faster because attention covers the whole row under the mask.
- **The tools.** A new HTTP client per call cost about 17 ms each and held `decide_many` to 23 a second; the tools'
  share of the time grows as CLM gets faster.

**Train CLM before trusting it.** Released, CLM routed about half the service desk's messages rightly. Training on
generated examples brought it to 96–98%; on a similar problem, most of the gain came by 100 to 200 examples. Trained
heads fit the exact wording, so reworded options need training again. A rare answer with one or two examples, such as
"within weeks", cannot be learned; label more of it first.

**CLM's place against a hosted model.** In one comparison, Claude was more accurate on unseen cases, and at 8 calls at
once faster than CLM on the Mac. CLM's strengths are elsewhere:

- it costs nothing per decision;
- the messages never leave the machine;
- on a GPU it decides a busy day faster than the day's peak needs;
- most of its wrong answers are marked uncertain, so they reach a person.

The CrowdStrike measurements point to better-trained heads, not a lower threshold, to reduce the 46% marked
uncertain. Its probabilities are relative,
so thresholds are tuned on labelled cases. As a yes or no on a single proposal, `check_call` was weak; deciding with
`decide` was more reliable.

**Rules made the local model dependable here; documents added sources.** On the made-up handbook, in one run, both
models said they could not know the company's figures rather than guess them. With the rules as tools, gemma4 matched
Claude, 16 of 17 each; with the handbook it fell to 14 of 17, and given the handbook alone it stated one wrong figure.
Documents mostly added citations and the policy text. Large tool results are a risk for local models: Ollama trims the
conversation silently, and neither the scenario nor the agent warns yet.

**Derived rules need a person.** The mechanical check catches figures that are not in the document, not figures read
into the wrong place. A second reading by Claude caught the misplaced ones; a second reading by a local model did so
only partly, and once agreed with the mistake. Agreement is not proof: every derived entry still needs a person's
approval.

**A small model shows unclear tool descriptions.** Every miss in the Ask comparison was the small model's: Claude got
all three on the same tools. Two models passed a component's name where its id was wanted, and "give the id, such as
C1" in the tariff descriptions fixed `granite4:micro`. Try a larger model before changing the tools, and test
descriptions with both sizes.

**Exported DMN files often need work.** Of the 16 files, chosen to cover what the tools write, 10 chain several
decisions or use features outside the subset; the reader now refuses those instead of serving part of them. Of the 6
that load, the Camunda and Kogito tables could be served unedited, and the four TCK tables needed their inputs renamed.

**Limitations.**

- **Small samples, one run each.** The comparison with Claude and the document, derivation and Ask comparisons were run
  once each; the handbook is made up.
- **Generated data.** Accuracy was measured mostly on generated messages, and the held-back examples come from the same
  generator as the training examples. The 55 held-back service desk examples appear in three runs: the route alone,
  the route with the questions, and the torch backend.
- **Not always the same work.** The first packing row compares different numbers of bookings, and the replay's rates
  on the Mac, A100 and H100 cover different parts of the day.
- **Hand-picked DMN files.** The 16 exported files were chosen to cover features, several from engine test suites, so
  their shares are not those of files businesses hold.
- **Untraced causes.** Whether training or the GPU's rounding made the difference between the H100's and the A100's
  heads was not measured.
- **CLM's document judgements:** "broader than needed" ordered its pairs worse than chance, and no rule reads either
  judgement.
