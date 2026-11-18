# AI Interactions Log

Stretch features attempted: **RAG enhancement** (multiple sources), **agentic workflow** (reasoning traces below), and **test harness** (`scripts/evaluate.py`).

---

## Agentic Workflow: reasoning traces

The agent (`src/agent.py`) records one trace per request: guardrail, plan, retrieve, profile, recommend, verify, optional revise, confidence. Traces below are real output (`python -m src.main --ask "..." --trace`); full logs are in [`docs/`](docs/).

### Trace 1: clear request ([`docs/sample_study.txt`](docs/sample_study.txt))

```text
Request: 'I need something to study to'
  1. GUARDRAIL input accepted
  2. PLAN explicit terms: genres=[] moods=[] energy=None
  3. RETRIEVE Studying and deep focus (0.40)
  4. PROFILE genre=lofi, mood=focused, energy=0.35, likes_acoustic=True
  5. RECOMMEND top='Focus Flow' score=4.81
  6. VERIFY passed
  8. ANSWER confidence 0.90
```

### Trace 2: stated terms override retrieval ([`docs/sample_explicit.txt`](docs/sample_explicit.txt))

```text
Request: 'jazz for a rainy day, energy 0.3'
  2. PLAN explicit terms: genres=['jazz'] moods=[] energy=0.3
  3. RETRIEVE Rainy day (0.30), Jazz (0.20)
  4. PROFILE genre=jazz, mood=relaxed, energy=0.3, likes_acoustic=True
  5. RECOMMEND top='Coffee Shop Stories' score=4.85
  6. VERIFY passed
  8. ANSWER confidence 0.82
```

### Trace 3: contradiction detected, human asked to clarify ([`docs/sample_conflict.txt`](docs/sample_conflict.txt))

```text
Request: 'calm but also aggressive and loud'
  3. RETRIEVE Venting anger (0.22), Angry and aggressive (0.18), Sleep and winding down (0.15)
  4. PROFILE genre=metal, mood=angry, energy=0.74, likes_acoustic=False
  6. VERIFY passed
  7b. CONFLICT retrieved entries disagree on energy (0.15-0.95); lowering confidence
  8. HUMAN-IN-THE-LOOP confidence 0.48 < 0.55; asking for clarification
```

Note that VERIFY passed even though the profile is meaningless; the separate conflict check is what caught it (see `model_card.md`).

## RAG enhancement: before/after

Same request, retrieval off vs on (`VibeFinderAgent(use_retrieval=False)` vs default):

| Request | Retrieval OFF | Retrieval ON |
| --- | --- | --- |
| "I need something to study to" | `no_match`: nothing to build a profile from | lofi / focused / 0.35 energy, top = Focus Flow |
| "gym workout, pumped up" | `no_match` | pop / intense / 0.9 energy, top = Gym Hero |
| "jazz for cooking on a sunday" | profile = genre only; mood/energy missing | jazz / relaxed / 0.4 energy, top = Coffee Shop Stories |

Three separate knowledge sources (activities, moods, genres) feed one retriever; a request can pull from several (the rainy-day jazz request retrieved from `activities.md` and `genres.md`).

## Test harness

`python scripts/evaluate.py` runs 15 predefined requests, prints pass/fail, confidence and a retrieval ablation; output in [`docs/eval_results.txt`](docs/eval_results.txt).
