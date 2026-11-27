# Retrieval strategy comparison

**Question:** is embedding RAG the best way to get Alabama law, guidance, glossary and how-to knowledge to the model, or does a simpler or different approach do as well or better?

**Status: theoretical analysis, not a measured comparison.** The full live comparison (6 strategies × 34 questions × N=3 on `claude-haiku-4-5`, estimated at $13–20) was **not run**, by decision, to keep API spend near zero. This report is built from:

1. **Corpus measurement** using the token-counting API (free).
2. **A live dry run:** 2 questions × 6 strategies × 1 run, plus one forced-cold cache probe. That is 13 question runs and 43 model calls, costing about $0.51. Raw data is in [`results/20261015T205355Z-dryrun.json`](results/20261015T205355Z-dryrun.json).
3. **An offline retrieval check:** the search layer only, with local embeddings and BM25 and no model calls. It checks whether each search-based strategy surfaces the expected source for every question that names one.
4. Reading the code, the corpus and the traces.

Nothing below is a statistically meaningful pass rate. Where a number comes from 2 questions it says so. The 13 hard questions are unreviewed (see [Hard questions](#hard-questions-needs-human-review)).

Branch: `experiment/retrieval-strategies`. The default strategy is still `rag_current`, and with it `handle_question` sends byte-identical requests to `main`. This was checked by snapshotting every `messages.create` argument before and after the refactor. All 99 tests pass: the 65 existing ones unchanged, plus 34 new.

---

## What was compared

| Strategy | How knowledge reaches the model | Citations come from |
|---|---|---|
| `rag_current` | `search_knowledge_base`: Chroma + `all-MiniLM-L6-v2`, top-3 **whole files** (no chunking) | Every file retrieved |
| `long_context` | The whole KB (105 files) in a system block with `cache_control`, placed first and followed by the instructions. No search tool. | § / AGO numbers and KB paths the answer names, mapped to files |
| `agentic_nav` | `list_categories`, `list_documents`, `read_document`, `search_text` (regex or literal grep), 5 tool rounds | Files passed to `read_document` |
| `agentic_nav_10` | Same, with 10 tool rounds | Same |
| `hybrid` | Chroma top-20 + BM25 top-20, merged with reciprocal-rank fusion (k=60), top-3 whole files | Every file retrieved |
| `glossary_inline` | `rag_current` with the 9 glossary files pasted into the system prompt and excluded from search | Retrieved files + paths/sections the answer names |

**Held identical across strategies:** the `handle_question` seam, PII redaction and the injection pre-filter, the four campaign-data tools, the `provide_answer`/`decline_to_answer` terminal tools and `tool_choice: any`, the forced wrap-up, `_build_final_answer` (disclaimer, refusal copy, PII notice), `max_tokens=1024`, and the model.

**System-prompt differences:** only the three sentences that name `search_knowledge_base` are reworded per strategy, along with the matching hint in `provide_answer`'s description. The scope, safety, current-numbering and Known-issue rules are verbatim.

**`_FLAGS.md` caveats:** every strategy attaches the same `Known issue:` line wherever a flagged file's text reaches the model. That happens in the search results, in each `<document>` of the long-context block, on `read_document`, and in the inline glossary. `search_text` hits are tagged `[has Known issue]`. All strategies share one parser (`knowledge_base.load_flags`).

Code: [`assistant/retrieval_strategies.py`](../assistant/retrieval_strategies.py), tests in [`tests/test_retrieval_strategies.py`](../tests/test_retrieval_strategies.py), runner in [`run_strategy_comparison.py`](run_strategy_comparison.py).

---

## Step 1: Corpus size

Counted with Anthropic `count_tokens` for `claude-haiku-4-5` ([`measure_corpus.py`](measure_corpus.py)):

| Category | Files | Tokens | Share |
|---|---|---|---|
| sos_guidance | 13 | 40,643 | 38.9% |
| ethics_law | 38 | 32,437 | 31.1% |
| fcpa_statute | 32 | 21,701 | 20.8% |
| ag_opinions | 5 | 6,211 | 6.0% |
| ethics_commission | 4 | 2,391 | 2.3% |
| glossary | 9 | 572 | 0.5% |
| howto | 4 | 408 | 0.4% |
| **Total** | **105** | **104,363** | |

Largest files: the Tyler portal manual (14,164 tokens), `candidate_filing_guidelines_2026` (4,842), `36-25-1_definitions` (4,615), `2026_fcpa_filing_calendar` (4,250), `36-25-4_ethics_commission_duties` (3,767).

**It fits comfortably.** The corpus is 52% of Haiku 4.5's 200k window. `long_context` includes everything and **nothing was left out**. There is roughly 75k tokens of headroom for the conversation and corpus growth. The corpus could grow about 1.7× before needing a larger-context model or pruning, and the portal manual is the obvious first candidate to drop.

### The finding that matters most: embeddings see about a quarter of the corpus

`all-MiniLM-L6-v2` has `max_seq_length = 256` word-pieces, and Chroma silently truncates longer input. Each KB file is embedded as one document, YAML front matter included. Measured with the model's own tokenizer:

- **83 of 105 files exceed 256 word-pieces.** Only about **26% of the corpus text** contributes to any embedding.
- Coverage of individual files: `36-25-1_definitions` 6%, the portal manual 2%, `17-5-8` 13%, `17-5-16.1` 13%.

So for `rag_current`, anything past roughly the first 200 words of a long file cannot influence whether that file is found. Once the file is found, the model gets the whole thing, because results are whole files. This is the main structural weakness of the current design, and it is a property of how the corpus was indexed, not of RAG as such.

---

## Dry-run measurements (2 questions per strategy, 1 run)

The questions were `compliance-reporting-thresholds` (original set) and `hard-lobbyist-meal-limit` (hard set). **Two questions cannot rank strategies.** The cost, token and latency shape per strategy is more informative than the pass rates.

| Strategy | Pass orig | Pass hard | Pass all | Flipped | Calls / q (mean) | Input tok mean / p95 | Output tok mean | Cache read mean | Cache write mean | Latency p50 / p95 | $ / q mean / p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rag_current | 1/1 | 1/1 | 2/2 | n/a (N=1) | 2.5 | 13,147 / 17,710 | 408 | 0 | 0 | 5.5s / 6.1s | $0.0152 / $0.0198 |
| long_context | 1/1 | 1/1 | 2/2 | n/a | 1.0 | 1,338 / 1,349 | 330 | 54,311 | 54,311 | 3.9s / 6.1s | $0.0763 / $0.1390 |
| agentic_nav | 1/1 | 0/1 | 1/2 | n/a | 6.0 | 19,856 / 21,375 | 440 | 0 | 0 | 4.7s / 9.6s | $0.0221 / $0.0245 |
| agentic_nav_10 | 1/1 | 1/1 | 2/2 | n/a | 5.5 | 25,338 / 31,512 | 491 | 0 | 0 | 6.2s / 9.3s | $0.0278 / $0.0347 |
| hybrid | 1/1 | 1/1 | 2/2 | n/a | 3.5 | 25,426 / 34,752 | 440 | 0 | 0 | 6.0s / 8.0s | $0.0276 / $0.0371 |
| glossary_inline | 1/1 | 1/1 | 2/2 | n/a | 2.5 | 14,024 / 18,025 | 402 | 0 | 0 | 5.4s / 6.3s | $0.0160 / $0.0197 |

"Input tok" means uncached input tokens. Costs use the pricing block at the top of `run_strategy_comparison.py` (Haiku 4.5, per million tokens: $1 input, $5 output, $1.25 cache write, $0.10 cache read). With p95 over 2 values, "p95" is simply the maximum.

### long_context: cold vs. warm cache

| Cache state | Calls | Cost per call | Latency per call |
|---|---|---|---|
| Cold (writes the ~108.6k-token prefix) | 2 (first question + forced-cold nonce probe) | **$0.139** | 6.1–6.5s |
| Warm (reads it) | 1 | **$0.0136** | 3.9s |

When warm, `long_context` was the cheapest and fastest strategy in the dry run. It answered both questions in **one call** because it never has to search. When cold it costs about 10× more. Caching worked as designed: `cache_read_input_tokens = 108,622` on the warm call, so the tools + KB block prefix was stable.

### Full-run cost the dry run implied (not spent)

| Strategy | Est. $ / question | Est. total (34 q × 3) |
|---|---|---|
| rag_current | $0.015 | $1.55 |
| long_context | $0.014 warm + 1 cold write per run | $1.77 |
| agentic_nav | $0.022 | $2.25 |
| agentic_nav_10 | $0.028 | $2.83 |
| hybrid | $0.028 | $2.82 |
| glossary_inline | $0.016 | $1.64 |
| cold probes | | $0.42 |
| **Total** | | **≈ $13.30** (realistic ceiling about $20) |

---

## Offline retrieval check: does search surface the right file?

These are free, local search calls. Each one uses the **raw question text** as the query and checks the top-3. For `glossary_inline`, the glossary counts as surfaced because it is always in the prompt. `long_context` surfaces everything by construction. `agentic_nav` can't be simulated without the model.

| Question | rag_current | hybrid | glossary_inline |
|---|---|---|---|
| compliance-reporting-thresholds | ✓ | ✓ | ✓ |
| compliance-legislative-blackout | ✗ | ✓ | ✗ |
| compliance-federal-committee-cap | ✓ | ✓ | ✓ |
| compliance-current-numbering-ago-94-00227 | ✓ | ✓ | ✓ |
| terminology-independent-expenditure | ✓ | ✓ | ✓ |
| terminology-pac | ✓ | ✓ | ✓ |
| howto-canvassing-contact | ✓ | ✓ | ✓ |
| howto-record-contribution | ✓ | ✓ | ✓ |
| howto-import-voter-list | ✓ | ✓ | ✓ |
| data-plus-compliance-federal-cap-violation | ✗ | ✗ | ✗ |
| hard-17-5-13-identification-crossref | ✓ | ✓ | ✓ |
| hard-late-report-second-offense | ✗ | ✗ | ✗ |
| hard-late-report-48-hour-grace | ✓ | ✓ | ✓ |
| hard-fake-audio-disclaimer | ✗ | ✓ | ✗ |
| hard-independent-candidate-sei-deadline | ✓ | ✓ | ✓ |
| hard-36-25-15c-no-sei-consequence | ✓ | ✓ | ✓ |
| hard-portal-delete-filed-transaction | ✓ | ✓ | ✓ |
| hard-portal-password-rules | ✓ | ✓ | ✓ |
| hard-lobbyist-meal-limit | ✗ | ✓ | ✗ |
| hard-ethics-law-candidate-definition (2 sources) | 1/2 | 1/2 | 1/2 |
| hard-church-disclosure | ✗ | ✓ | ✗ |
| hard-17-5-7.2-campaign-property | ✓ | ✓ | ✓ |
| hard-17-5-18-repealed | ✓ | ✓ | ✓ |
| **Expected sources surfaced** | **17/24** | **21/24** | **17/24** |

In an earlier spot check on a model-style query ("17-5-15.1 federal committee contribution cap"), `rag_current` returned three *other* sections and `hybrid` ranked § 17-5-15.1 first. Embeddings don't match section numbers well. BM25 does, because the tokenizer keeps `17-5-15.1` as a single token.

**This check understates `rag_current`.** In the real loop the model writes its own queries and searches repeatedly. On `hard-lobbyist-meal-limit`, `rag_current` missed with the raw question but **passed live**: its second query, "de minimis value ethics law definition amount", pulled in `36-25-1_definitions`. Retrieval misses here are a risk, not a guaranteed failure.

---

## Failures by strategy, and why

### Observed live (dry run)

| Strategy | Question | Cause | Detail |
|---|---|---|---|
| agentic_nav | hard-lobbyist-meal-limit | **Wandering / ran out of rounds** | Spent its 5 rounds on `list_categories`, three `search_text` calls ("lobbyist meal gift elected official", "lobbyist spending meal", "lobbyist gift limit") and `list_documents`. Literal grep can't bridge paraphrase: the statute says "Meals and other food and beverages provided to a public official". On the forced wrap-up, offered only the terminal tools, the model **still emitted a `read_document` call**. The orchestrator ignores non-terminal calls there, so the user got the stock "I wasn't able to put together a complete answer" reply. `agentic_nav_10` passed the same question in 6 calls. |

Every other dry-run pair passed.

### Predicted (offline retrieval misses; not observed live)

| Question | Strategies at risk | Likely cause |
|---|---|---|
| compliance-legislative-blackout | rag_current, glossary_inline | Retrieval miss: embeddings rank other sections above § 17-5-7. The existing eval passes, so the model's own queries recover. |
| data-plus-compliance-federal-cap-violation | all search strategies | Retrieval miss on the raw question ("Pete Wallace's committee…"), which names no law. The model has to formulate a law query; the existing eval shows it does. |
| hard-late-report-second-offense | all search strategies | Retrieval miss (paraphrase): "fine", "late" and "second time" share no vocabulary with "civil penalty… second offense". `long_context` and `agentic_nav` (grep "second offense" / "penalt") should handle it. |
| hard-fake-audio-disclaimer | rag_current, glossary_inline | Retrieval miss (paraphrase + deep): the audio rule is in § 17-5-16.1(c)(3), past the 13% of the file that gets embedded. |
| hard-lobbyist-meal-limit | rag_current, glossary_inline | Retrieval miss (deep): the meal limit is on line 171 of 185 in `36-25-1_definitions`, 6% of which gets embedded. Recovered live via a reformulated query. |
| hard-church-disclosure | rag_current, glossary_inline | Retrieval miss (deep): subsection (g) of § 17-5-8. |
| hard-ethics-law-candidate-definition | all search strategies | Cross-reference: the second hop (§ 36-25-1(3) → § 17-5-2) needs a second search that the model may not make. |

The other failure modes in the original plan, wrong section cited and model reasoning error, can't be predicted without live runs. The classifier for them is in `run_strategy_comparison.classify_failure`.

---

## Tradeoffs: an honest read

**`rag_current` is not the best design, but its main weakness is fixable without changing approach.** It works on the original 21 questions because those mostly hit short files near the top, and the model compensates with extra queries. Its blind spot is structural. Embeddings cover about 26% of the corpus, so deep and paraphrased content is found only if the model happens to phrase a second query well. Returning whole files also makes it expensive per hit: up to 14k tokens per result, re-sent uncached on every later round.

**`hybrid` is the lowest-risk improvement.** In the offline check it surfaced 21/24 sources versus 17/24. It fixes section-number lookups and some deep and paraphrase cases, with the same tool, prompt and citation behavior and a free local index. The downside showed in the dry run: it pulled in more and longer files (25k vs. 13k mean input tokens, 3.5 vs. 2.5 calls), which is about 1.8× the cost per question. That rests on two questions, though. An alternative fix for the same root cause is **chunking files before embedding**: section-level chunks with the file path kept as the citation. That attacks the 256-word-piece truncation directly and would also cut tokens per hit.

**`long_context` is the strongest option on paper, at this corpus size.** It cannot have a retrieval miss and it answered in one call. Warm, it was the cheapest ($0.014) and fastest (3.9s) strategy measured. The catches:
- **The cost depends on traffic.** The 5-minute cache TTL means a demo with gaps between questions pays the cold rate (about $0.14, 10× more) on most questions. The 1-hour TTL (2× write cost) or a keep-alive ping would be needed outside busy periods.
- **There is little room to grow.** The corpus uses 52% of the window today. Adding a second state or more guidance would push it past.
- **Long-context attention isn't free.** With 105 documents in context, Haiku may anchor on the wrong passage. The dry run is too small to see this.
- **Citations are inferred** from section numbers in the answer text. Glossary and how-to answers seldom name a path, so their citation checks would fail even when the content is right. That's why the runner reports a content-only pass rate alongside the strict one.

**`agentic_nav` is the most robust in principle and the most expensive in practice.** Grep finds deep text the embeddings can't see, and citations are exactly what was read. But it spends rounds browsing (list, then list, then read), grep fails on paraphrase, and 5 rounds wasn't enough on one of two questions. At 10 rounds it passed, at about $0.028 and 6–9s per question. This approach suits a stronger model better than Haiku.

**`glossary_inline` makes no practical difference.** The glossary is 572 tokens, below Haiku's 4,096-token cache minimum, and search already finds glossary entries reliably (all 3 terminology questions surfaced ✓ for every strategy). The approach is harmless but solves a problem this corpus doesn't have.

**If I had to choose without a full run:**
1. Switch the default to `hybrid`, or add chunked embeddings. Either is cheap and local, and it targets the measured weakness.
2. Keep `long_context` as the fallback option for a busy, low-latency deployment.
3. Re-test with the full run (or the cheaper version below) before changing the default.

---

## What makes this comparison unfair or too small to trust

- **No full run.** Live evidence is 2 questions × 1 run per strategy. Flip rates across runs were never measured.
- **The offline check uses raw questions as queries.** The model reformulates and repeats searches, so it understates search strategies. It can't evaluate `agentic_nav` at all.
- **The citation grading isn't symmetric.** RAG strategies "cite" every file retrieved, even unused ones, which makes the citation check lenient. `long_context` cites only what the answer names, which is stricter. `agentic_nav` cites what it read.
- **The round budget favors one-shot strategies.** 5 rounds is generous for RAG and tight for navigation. That's why `agentic_nav_10` exists.
- **The baseline has no caching.** `rag_current` keeps today's exact behavior, but its static ~3.8k-token system prompt and tool block could also be cached if they cleared the 4,096-token minimum.
- **Forced wrap-ups miss the cache.** That call offers a different tool list, so in `long_context` it re-writes the 108k-token prefix (about $0.14).
- **The hard questions are unreviewed** and were written by the same agent that built the strategies. They also lean toward deep and paraphrase cases where embeddings are known to be weak.
- **One model.** Haiku 4.5 only. A stronger model would likely help `agentic_nav` and `long_context` the most.
- **Concurrency.** The runner executes strategies in parallel threads, so latency includes some API-side contention.

**Cheapest way to get real numbers:** after reviewing the hard questions, run the hard set ×3 and the original set ×1, for about $7–10. The original set already passes almost every time, so repeating it adds little. The runner needs a small change to support different run counts per question set.

---

## Hard questions (NEEDS HUMAN REVIEW)

[`eval/eval_questions_hard.py`](../eval/eval_questions_hard.py) holds 13 questions, each carrying verbatim knowledge-base quotes with path and line number. [`tests/test_eval_questions_hard.py`](../tests/test_eval_questions_hard.py) fails if any quote isn't found verbatim at its cited line. **The expected answers were checked against the KB files, not against the current Code of Alabama.** The KB is a September 2026 snapshot, so verify each one against the real law before trusting results built on it.

| Id | Type | Expected answer (from the quoted source) |
|---|---|---|
| hard-17-5-13-identification-crossref | section number, cross-ref, flag | "Full name and complete address": the § 17-5-2(a)(5) pointer is stale, and the definition is now at (a)(8) |
| hard-late-report-second-offense | paraphrase | Lesser of $600 or 15% (§ 17-5-19.1(b)(2)) |
| hard-late-report-48-hour-grace | cross-ref, paraphrase | Not an offense if it's the first failure of the cycle and filed within 48 hours (§ 17-5-19.1(h)) |
| hard-fake-audio-disclaimer | paraphrase, deep | Disclaimer read at the beginning and end of the audio (§ 17-5-16.1(c)(3)) |
| hard-independent-candidate-sei-deadline | flag, cross-ref | 5 days after the first primary (§ 36-25-15(a)), not 5 days after the petition as the SOS guide says |
| hard-36-25-15c-no-sei-consequence | section number | Off the ballot and not qualified; the Commission may allow 5 more days for good cause |
| hard-portal-delete-filed-transaction | deep | Can't delete once filed; you must amend the report (portal manual, line ~1130 of 1,713) |
| hard-portal-password-rules | deep | Minimum 12 characters including upper, lower, number and special; change every 90 days (line ~771) |
| hard-lobbyist-meal-limit | deep, paraphrase | $25 per meal, $150 per year for a lobbyist (`36-25-1` line 171 of 185) |
| hard-ethics-law-candidate-definition | cross-ref | § 36-25-1(3) → § 17-5-2: qualifying, or raising or spending over $1,000 |
| hard-church-disclosure | deep, paraphrase | Exempt unless its expenditures are used to influence an election; members' donations need not be disclosed (§ 17-5-8(g)) |
| hard-17-5-7.2-campaign-property | section number, cross-ref | Liquidate at fair market value or donate within 120 days; office-use exception in (b) |
| hard-17-5-18-repealed | section number, flag | Repealed in 2013; penalties are now in § 17-5-19 / § 17-5-19.1 |

---

## Side findings (outside the experiment's scope)

1. **The forced wrap-up can produce no answer.** In the dry run, Haiku emitted a call to a tool that wasn't offered (`read_document`) on the terminal-tools-only call, so the user got the stock fallback. The same can happen in `rag_current` with `search_knowledge_base`. One fix: if the wrap-up has no terminal call, retry once, or offer `provide_answer` with `tool_choice: {"type": "tool", "name": "provide_answer"}`.
2. **The § 17-5-8 subsection numbering may not match.** The KB copy of § 17-5-8 puts monthly and weekly reports at **(b)(1)** and **(b)(2)**. The app's deadline data and the SDD cite `§ 17-5-8(a)(1)` / `(a)(2)`. Worth checking against the current Code.
3. **Front matter wastes embedding budget.** Each file's YAML header (title, source, URL, dates) is part of the 256 word-pieces that get embedded, which pushes real content further out of the window. This is cheap to fix while chunking.

---

## Reproducing

```bash
pip install -r experiments/requirements.txt
python -m experiments.measure_corpus                          # free (count_tokens)
python -m experiments.run_strategy_comparison --dry-run       # ~$0.50
python -m experiments.run_strategy_comparison                 # ~$13-20 - not run
RETRIEVAL_STRATEGY=hybrid streamlit run app.py                # try a strategy in the app
pytest
```
