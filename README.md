# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

**VibeFinder 1.0** is a small, explainable, content-based music recommender that runs in the terminal ("CLI-first").
It loads a 20-song catalog from `data/songs.csv`, compares every song to a user's "taste profile"
(favorite genre, favorite mood, target energy, and optionally a preference for acoustic sound), gives each
song a weighted score, and returns the top *k* songs along with the exact reasons each one earned its points.
The project also stress-tests the scorer with normal and adversarial profiles, runs weight-sensitivity
experiments, and documents the biases it found in [`model_card.md`](model_card.md).

---

## How The System Works

### How real platforms do it

Real platforms like Spotify, YouTube, and TikTok mix two big ideas:

- **Collaborative filtering** uses *other people's behavior*. If listeners who like the same songs as you
  also love a track you've never heard, the system guesses you'll love it too. It needs no knowledge of
  what a song sounds like — only who played, saved, skipped, or playlisted it. Its weakness is the
  **cold-start problem**: brand-new songs and brand-new users have no history to learn from.
- **Content-based filtering** uses *attributes of the items themselves* — genre, mood, tempo, energy,
  acousticness, even audio embeddings and lyrics. It recommends songs that look similar to what you
  already like. It works for brand-new songs, but tends to keep you inside a "filter bubble."

The data these systems use falls into two groups:

| Signal type | Examples |
| --- | --- |
| Explicit feedback | likes/hearts, thumbs-down, follows, ratings |
| Implicit feedback | plays, **skips** (especially in the first 30 s), replays, listen time, saves, adding to playlists, searching for an artist |
| Song features | genre, mood tags, tempo (BPM), energy, valence (positivity), danceability, acousticness |
| Context | time of day, device, whether you're in a "workout" or "sleep" playlist |

At scale, platforms generate a few hundred **candidates** from many sources, **score** each candidate with
a learned model, then **re-rank** for diversity, freshness, and business rules before showing a feed.

### What VibeFinder prioritizes

VibeFinder is a pure **content-based** recommender (we have no other users to learn from). It prioritizes
**genre first, then mood, then how close the song's energy is to what you want**, with a small optional
bonus for acoustic vs. produced sound. Every point is explained, so a user can see *why* a song ranked where it did.

### Features used

**`Song`** (one row of `data/songs.csv`)

| Feature | Type | Used in scoring? |
| --- | --- | --- |
| `id`, `title`, `artist` | identity | no (display only) |
| `genre` | category | ✅ exact or partial match |
| `mood` | category | ✅ exact match |
| `energy` | 0.0–1.0 | ✅ closeness to target |
| `acousticness` | 0.0–1.0 | ✅ optional bonus |
| `tempo_bpm`, `valence`, `danceability` | numeric | loaded but not scored (kept for future work) |

**`UserProfile`** / `user_prefs` dict

| Field (dataclass) | Key (dict) | Meaning |
| --- | --- | --- |
| `favorite_genre` | `genre` | e.g. `"pop"` |
| `favorite_mood` | `mood` | e.g. `"happy"` |
| `target_energy` | `energy` | 0.0 (calm) – 1.0 (intense) |
| `likes_acoustic` | `likes_acoustic` | `True` / `False` / omitted (no preference) |

### Algorithm Recipe (finalized)

**Scoring Rule — judges ONE song** (max 5.0 points):

| Rule | Points |
| --- | --- |
| Genre exactly matches (case-insensitive) | **+2.0** |
| Genre partially matches (e.g. user `pop` vs. song `indie pop`) | **+1.0** |
| Mood exactly matches | **+1.0** |
| Energy closeness | **+1.5 × (1 − \|song.energy − target\|)** |
| Acoustic preference (if given) | **+0.5 × acousticness** if `likes_acoustic`, else **+0.5 × (1 − acousticness)** |

Why closeness instead of "higher is better"? A user who wants energy 0.4 should be *penalized* by a
0.95-energy EDM banger, not rewarded. `1 − |difference|` is 1.0 for a perfect match and shrinks linearly
as the song drifts away in either direction.

Why genre > mood? Genre describes the whole sound palette (instruments, production, tempo range), while
mood is more subjective and noisier as a single tag. But mood + a close energy (1.0 + 1.5) can still beat a
genre match with the wrong energy, so a great off-genre song isn't completely buried.

**Ranking Rule — orders the WHOLE list:** score every song with the Scoring Rule, sort by score from high
to low (ties broken alphabetically by title so results are repeatable), and return the top *k*.
We need both rules: the scoring rule answers "how good is this one song for this user?", and the ranking
rule answers "out of everything, what should we show first?" — that's also where diversity rules would go.

### Data flow

```
 INPUT                       PROCESS (the loop)                          OUTPUT
 user_prefs ─┐
             ├─► for each song in songs.csv:                       ┌─► sort by score (desc)
 songs.csv ──┘      score, reasons = score_song(user_prefs, song)  │   take top k
                    keep (song, score, reasons) ───────────────────┘   print title, score, reasons
```

### Expected biases (written before coding)

- **Genre dominance:** a +2.0 genre bonus may push a mediocre same-genre song above a perfect-vibe song
  from another genre — a filter bubble.
- **Catalog imbalance:** genres with more songs (lofi has 3, pop has 2) give those fans more good options;
  a user whose genre has one song (or zero) will get weaker lists.
- **Exact string matching:** "chill" and "relaxed" mean nearly the same thing but get no mood credit.
- **Middle-energy advantage:** energy closeness is relative, so songs near 0.5 are "never too far" from
  anybody, while extreme songs are only good for extreme users.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Sample Recommendation Output

Paste a sample of your recommender's output here as a text block so a reader can see what it produces:

```
# e.g.:
# User profile: genre=indie, mood=chill, energy=low
# Recommendations:
#   1. ...
#   2. ...
#   3. ...
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Experiments You Tried

Use this section to document the experiments you ran. For example:

- What happened when you changed the weight on genre from 2.0 to 0.5
- What happened when you added tempo or valence to the score
- How did your system behave for different types of users

---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this



