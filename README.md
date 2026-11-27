# A3QAssistantPOC

Proof of concept for A3Q's AI assistant: a chat assistant that sits inside the VoteCivic/SignalVote campaign platform and helps campaign staff with Alabama campaign-finance (FCPA) compliance, political terminology, platform how-to questions and their own campaign's data.

## How it works

- **UI** (`app.py`): a Streamlit app that shows a sample campaign's data framed in a VoteCivic screenshot, with the chat beside it.
- **Orchestrator** (`assistant/orchestrator.py`): `handle_question` is the single entry point. It calls Claude with tools to search the knowledge base, read the campaign's contributions, expenditures, canvassing log and filing deadlines, and then either answer or decline.
- **Knowledge base** (`knowledge_base/`): about 90 Markdown source documents (the FCPA statute, the ethics law, Secretary of State guidance, AG opinions, Ethics Commission material, a glossary and how-tos), indexed in Chroma with sentence-transformers embeddings. `_INDEX.md` lists what is there and where it came from.
- **Safety** (`assistant/safety.py`): PII redaction, prompt-injection detection, refusals and a compliance disclaimer.

## Running locally

```bash
pip install -r requirements-dev.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then add your ANTHROPIC_API_KEY
streamlit run app.py
```

## Tests and evals

```bash
pytest                                                # unit tests
ANTHROPIC_API_KEY=... python -m eval.run_eval         # live eval; add --include-hard for the hard set
```

Eval results are written to `eval/results/`. Retrieval experiments and their write-ups live in `experiments/`.

Issues and specs are tracked as GitHub issues on this repo.
