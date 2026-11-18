# Model Card: VibeFinder Agent (final project)

Builds on VibeFinder 1.0 (see [`docs/VIBEFINDER_1_model_card.md`](docs/VIBEFINDER_1_model_card.md) for the base model's own biases: genre-first scoring, a 20-song catalog, etc.).

## System summary

| | |
| --- | --- |
| Task | Turn a free-text request into a profile via retrieval, then rank a 20-song catalog |
| Components | TF-IDF retriever (44 hand-written knowledge entries, 3 sources), VibeFinder scorer, rule-based verifier, confidence score |
| Not used | No LLM, no embeddings, no user data, no network calls |
| Intended use | Classroom/portfolio demo of RAG + agent patterns on a toy catalog |
| Out of scope | Real music discovery, profiling listeners, anything with stakes |

## Limitations and biases

- **My assumptions are baked into the knowledge base.** I decided that "gym" means high-energy, produced, pop/EDM/hip hop. Someone who trains to folk or jazz gets the wrong profile. The same goes for cultural associations ("romantic" means r&b/jazz, "road trip" means country/folk/rock). Retrieval makes these assumptions explicit and editable, but they are still mine.
- **Genre and Western-genre bias.** The catalog and vocabulary cover 17 mostly Western genres and 13 mood labels. Music outside them (K-pop, Afrobeats, gamelan) gets `no_match` or a poor match.
- **Vocabulary-bound retrieval.** TF-IDF only matches words that appear in the knowledge base. The evaluation caught "falling asleep" failing because the entry said "sleep"; paraphrases I did not anticipate will fail the same way. Non-English requests are not supported.
- **One genre, one mood per request.** Mixed tastes ("jazz and metal") collapse to a single winner.
- **Circular self-checking.** The verifier checks the answer against the *profile the system itself built*. It confirms the scorer did its job, not that the profile matches what the user meant. The conflict check helps only for contradictions that show up as disagreeing energy values.
- **Confidence is a heuristic.** The 0.55 threshold was tuned on the same 15 cases used to report results, so the reported scores are optimistic. It is not a calibrated probability.
- **Tiny catalog.** With 20 songs, "top 3" is often most of a genre, and high confidence says little about quality.

## Could it be misused? How is that prevented?

- **Prompt injection / system manipulation.** Free text could be used to try to steer the system. Input is never executed or sent to a model; a pattern list rejects instruction-like text, length is capped at 300 characters, and control characters are stripped. The pattern list is simple and can be bypassed with rephrasing, which only matters if this later gets wired to an LLM, so that is the point to add stronger defenses.
- **Mood inference.** A system that maps feelings ("heartbreak", "lonely") to recommendations could be extended into profiling vulnerable users. This version stores nothing about users (logs contain request text only and are git-ignored). Any real deployment would need consent, retention limits, and care around sensitive moods.
- **Over-trusting the output.** The agent shows its retrieved sources, trace and confidence, and asks for clarification when unsure, so users can see why it answered.

## What surprised me while testing

- **Retrieval was only essential for some requests.** With retrieval off, the harness still passed 7/15 cases: refusals, plus requests that name a genre or mood outright ("jazz", "romantic", "metal"). Retrieval matters for the vague activity and situation requests, which is exactly what real users type.
- **A confident wrong answer.** "calm but also aggressive and loud" first scored 0.73 confidence, because averaging contradictory energies produced a profile the scorer could satisfy perfectly. All checks passed on a meaningless profile. I had to add a check on the *inputs to* the profile, not just the output.
- **Small data fixes beat code fixes.** The one real evaluation failure was fixed by adding two keywords, not by changing an algorithm.

## Testing summary

| Test input | Evaluation criteria | Result |
| --- | --- | --- |
| "I need something to study to" | lofi/ambient/classical top song, confidence >= 0.7 | Pass (Focus Flow, 0.90) |
| "gym workout, pumped up" | high-energy genre, confidence >= 0.7 | Pass (Gym Hero, 0.99) |
| "music for falling asleep" | ambient/classical/jazz | Fail at first (no_match), Pass after keyword fix (0.75) |
| "calm but also aggressive and loud" | flagged low_confidence | Fail at first (0.73 ok), Pass after conflict check (0.48) |
| "polka accordion" | no_match, human asked to rephrase | Pass |
| injection phrase / empty string | rejected before retrieval | Pass / Pass |
| Retrieval disabled (ablation) | should fail vague requests | 7/15 pass, as expected |
| pytest | 32 tests | 32/32 pass |

Full harness output: [`docs/eval_results.txt`](docs/eval_results.txt).

## Collaboration with AI

I built this extension with Claude Code (an AI coding assistant), which wrote most of the first draft of the retriever, agent and tests; I chose the base project and the requirements and the AI proposed the design. What follows records what it suggested and what changed.

- **Accepted: a stdlib TF-IDF retriever with a hand-written, multi-file knowledge base.** It kept the project reproducible offline with no API key, gave me a retrieval step whose behavior I can inspect line by line, and made the "retrieval off" ablation easy to run. I kept it as suggested.
- **Revised: the agent's confidence score.** The first version was simply the normalized top score blended with retrieval similarity. Testing showed it gave the contradictory request 0.73, so the formula was changed to add a conflict penalty. A related idea that I scoped down: an LLM-based paraphrase step for query rewriting. It would handle unseen wording better, but it would add an API key, non-determinism and cost, and make the evaluation unreproducible, so it is listed under future work instead of being built.
- **Also simplified:** the AI initially left `pandas` and `streamlit` in `requirements.txt` from the base project even though nothing imports them; I removed them so setup only installs what runs.
- **What I still verify myself:** the AI wrote the knowledge-base entries, so the domain assumptions in them (and the keyword choices) need my review. The "falling asleep" failure came from an entry the AI wrote without my catching it.

## Future work

Query rewriting with an LLM (behind the same verifier), a larger and more diverse catalog, per-user feedback to adjust the knowledge base, and a held-out test set so confidence thresholds are not tuned on the reporting data.
