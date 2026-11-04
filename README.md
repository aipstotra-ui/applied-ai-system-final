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
   .venv\Scripts\Activate.ps1     # Windows PowerShell
   ```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the tests from the repo root:

```bash
pytest
```

`tests/test_recommender.py` covers the `Recommender` class; `tests/test_scoring.py` covers loading,
scoring (closeness, partial genre, case-insensitivity, acoustic preference), ranking order, and the
no-mood experiment.

### CLI options

```bash
python -m src.main --profile lofi -k 3
```

```bash
python -m src.main --weights energy-heavy
```

- `--profile {pop, lofi, rock, sad-hype, unknown, no-prefs}` — run one profile (default: all)
- `--weights {default, energy-heavy, no-mood}` — run an experiment
- `-k N` — number of recommendations (default 5)

---

## Sample Recommendation Output

Default "pop / happy / energy 0.8" profile (`python -m src.main --profile pop`):

```
Loaded songs: 20

========================================================================
Profile: High-Energy Pop  [weights: default]
Prefs:   genre=pop, mood=happy, energy=0.8
------------------------------------------------------------------------
1. Sunrise City - Neon Echo  (pop, happy)
   Score: 4.47
     • genre match: pop (+2.00)
     • mood match: happy (+1.00)
     • energy 0.82 vs target 0.80 (+1.47)
2. Rooftop Lights - Indigo Parade  (indie pop, happy)
   Score: 3.44
     • related genre: indie pop ~ pop (+1.00)
     • mood match: happy (+1.00)
     • energy 0.76 vs target 0.80 (+1.44)
3. Gym Hero - Max Pulse  (pop, intense)
   Score: 3.30
     • genre match: pop (+2.00)
     • energy 0.93 vs target 0.80 (+1.30)
4. Fiesta Calle - Los Brillantes  (latin, happy)
   Score: 2.44
     • mood match: happy (+1.00)
     • energy 0.84 vs target 0.80 (+1.44)
5. Concrete Crown - Blocktalk  (hip hop, confident)
   Score: 1.47
     • energy 0.78 vs target 0.80 (+1.47)
```

The results match intuition: *Sunrise City* is a pop, happy, 0.82-energy song — almost a perfect match.
*Rooftop Lights* (indie pop) gets partial genre credit and beats *Gym Hero*, because Gym Hero is pop but
"intense," not "happy."

### Stress test: all six profiles

`python -m src.main` runs three normal listeners and three adversarial/edge-case profiles:

| Key | Profile | Why it's here |
| --- | --- | --- |
| `pop` | High-Energy Pop: pop / happy / 0.8 | baseline from the starter |
| `lofi` | Chill Lofi: lofi / chill / 0.35 / likes acoustic | opposite end of the energy scale |
| `rock` | Deep Intense Rock: rock / intense / 0.9 / not acoustic | genre with only ONE song in the catalog |
| `sad-hype` | folk / **sad** / **0.9 energy** | conflicting preferences — every sad song is low-energy |
| `unknown` | **polka** / nostalgic / 0.5 | genre that doesn't exist in the catalog |
| `no-prefs` | energy 0.5 only | no genre or mood at all |

<details>
<summary>Full terminal output for all six profiles (default weights)</summary>

```
Loaded songs: 20

========================================================================
Profile: High-Energy Pop  [weights: default]
Prefs:   genre=pop, mood=happy, energy=0.8
------------------------------------------------------------------------
1. Sunrise City - Neon Echo  (pop, happy)
   Score: 4.47
     • genre match: pop (+2.00)
     • mood match: happy (+1.00)
     • energy 0.82 vs target 0.80 (+1.47)
2. Rooftop Lights - Indigo Parade  (indie pop, happy)
   Score: 3.44
     • related genre: indie pop ~ pop (+1.00)
     • mood match: happy (+1.00)
     • energy 0.76 vs target 0.80 (+1.44)
3. Gym Hero - Max Pulse  (pop, intense)
   Score: 3.30
     • genre match: pop (+2.00)
     • energy 0.93 vs target 0.80 (+1.30)
4. Fiesta Calle - Los Brillantes  (latin, happy)
   Score: 2.44
     • mood match: happy (+1.00)
     • energy 0.84 vs target 0.80 (+1.44)
5. Concrete Crown - Blocktalk  (hip hop, confident)
   Score: 1.47
     • energy 0.78 vs target 0.80 (+1.47)

========================================================================
Profile: Chill Lofi  [weights: default]
Prefs:   genre=lofi, mood=chill, energy=0.35, likes_acoustic=True
------------------------------------------------------------------------
1. Library Rain - Paper Lanterns  (lofi, chill)
   Score: 4.93
     • genre match: lofi (+2.00)
     • mood match: chill (+1.00)
     • energy 0.35 vs target 0.35 (+1.50)
     • acoustic sound fit 0.86 (+0.43)
2. Midnight Coding - LoRoom  (lofi, chill)
   Score: 4.75
     • genre match: lofi (+2.00)
     • mood match: chill (+1.00)
     • energy 0.42 vs target 0.35 (+1.40)
     • acoustic sound fit 0.71 (+0.35)
3. Focus Flow - LoRoom  (lofi, focused)
   Score: 3.81
     • genre match: lofi (+2.00)
     • energy 0.40 vs target 0.35 (+1.42)
     • acoustic sound fit 0.78 (+0.39)
4. Spacewalk Thoughts - Orbit Bloom  (ambient, chill)
   Score: 2.86
     • mood match: chill (+1.00)
     • energy 0.28 vs target 0.35 (+1.40)
     • acoustic sound fit 0.92 (+0.46)
5. Coffee Shop Stories - Slow Stereo  (jazz, relaxed)
   Score: 1.92
     • energy 0.37 vs target 0.35 (+1.47)
     • acoustic sound fit 0.89 (+0.45)

========================================================================
Profile: Deep Intense Rock  [weights: default]
Prefs:   genre=rock, mood=intense, energy=0.9, likes_acoustic=False
------------------------------------------------------------------------
1. Storm Runner - Voltline  (rock, intense)
   Score: 4.93
     • genre match: rock (+2.00)
     • mood match: intense (+1.00)
     • energy 0.91 vs target 0.90 (+1.48)
     • produced/electronic sound fit 0.90 (+0.45)
2. Gym Hero - Max Pulse  (pop, intense)
   Score: 2.93
     • mood match: intense (+1.00)
     • energy 0.93 vs target 0.90 (+1.46)
     • produced/electronic sound fit 0.95 (+0.47)
3. Laser Bloom - Pulsewidth  (edm, euphoric)
   Score: 1.91
     • energy 0.95 vs target 0.90 (+1.43)
     • produced/electronic sound fit 0.96 (+0.48)
4. Iron Cathedral - Graveforge  (metal, angry)
   Score: 1.88
     • energy 0.97 vs target 0.90 (+1.40)
     • produced/electronic sound fit 0.97 (+0.48)
5. Fiesta Calle - Los Brillantes  (latin, happy)
   Score: 1.79
     • energy 0.84 vs target 0.90 (+1.41)
     • produced/electronic sound fit 0.75 (+0.38)

========================================================================
Profile: Conflicted: Sad but 0.9 Energy  [weights: default]
Prefs:   genre=folk, mood=sad, energy=0.9
------------------------------------------------------------------------
1. Paper Boats - Wren & Willow  (folk, sad)
   Score: 3.54
     • genre match: folk (+2.00)
     • mood match: sad (+1.00)
     • energy 0.26 vs target 0.90 (+0.54)
2. Last Call Blues - Eddie Marsh  (blues, sad)
   Score: 1.81
     • mood match: sad (+1.00)
     • energy 0.44 vs target 0.90 (+0.81)
3. Storm Runner - Voltline  (rock, intense)
   Score: 1.48
     • energy 0.91 vs target 0.90 (+1.48)
4. Gym Hero - Max Pulse  (pop, intense)
   Score: 1.46
     • energy 0.93 vs target 0.90 (+1.46)
5. Laser Bloom - Pulsewidth  (edm, euphoric)
   Score: 1.43
     • energy 0.95 vs target 0.90 (+1.43)

========================================================================
Profile: Unknown Genre (polka) + Mood (nostalgic)  [weights: default]
Prefs:   genre=polka, mood=nostalgic, energy=0.5
------------------------------------------------------------------------
1. Dusty Back Roads - Hollis Creek  (country, nostalgic)
   Score: 2.42
     • mood match: nostalgic (+1.00)
     • energy 0.55 vs target 0.50 (+1.42)
2. Island Sway - Kaya Roots  (reggae, relaxed)
   Score: 1.47
     • energy 0.52 vs target 0.50 (+1.47)
3. Velvet Hours - Sienna June  (r&b, romantic)
   Score: 1.47
     • energy 0.48 vs target 0.50 (+1.47)
4. Last Call Blues - Eddie Marsh  (blues, sad)
   Score: 1.41
     • energy 0.44 vs target 0.50 (+1.41)
5. Midnight Coding - LoRoom  (lofi, chill)
   Score: 1.38
     • energy 0.42 vs target 0.50 (+1.38)

========================================================================
Profile: Energy Only (0.5), No Genre/Mood  [weights: default]
Prefs:   energy=0.5
------------------------------------------------------------------------
1. Island Sway - Kaya Roots  (reggae, relaxed)
   Score: 1.47
     • energy 0.52 vs target 0.50 (+1.47)
2. Velvet Hours - Sienna June  (r&b, romantic)
   Score: 1.47
     • energy 0.48 vs target 0.50 (+1.47)
3. Dusty Back Roads - Hollis Creek  (country, nostalgic)
   Score: 1.42
     • energy 0.55 vs target 0.50 (+1.42)
4. Last Call Blues - Eddie Marsh  (blues, sad)
   Score: 1.41
     • energy 0.44 vs target 0.50 (+1.41)
5. Midnight Coding - LoRoom  (lofi, chill)
   Score: 1.38
     • energy 0.42 vs target 0.50 (+1.38)
```

</details>

---

## Experiments You Tried

Weights live in one dictionary (`EXPERIMENT_WEIGHTS` in `src/recommender.py`), so each experiment is a
command-line flag rather than a code edit. The math stays valid in every variant: each rule still adds a
non-negative number, energy closeness is still clamped to 0–1, and the scores are only compared within one
run, so changing the maximum possible score doesn't break the ranking.

### Experiment 1 — Weight shift: double energy, halve genre (`--weights energy-heavy`)

genre 2.0 → **1.0**, related genre 1.0 → 0.5, energy 1.5 → **3.0**.

| Profile | Default top 5 | Energy-heavy top 5 | What changed |
| --- | --- | --- | --- |
| High-Energy Pop | Sunrise City, Rooftop Lights, **Gym Hero**, Fiesta Calle, Concrete Crown | Sunrise City, Rooftop Lights, **Fiesta Calle**, Gym Hero, Concrete Crown | happy Latin song passes the "intense" pop song |
| Chill Lofi | Library Rain, Midnight Coding, **Focus Flow**, Spacewalk Thoughts, Coffee Shop Stories | Library Rain, Midnight Coding, **Spacewalk Thoughts**, Focus Flow, Coffee Shop Stories | chill ambient passes "focused" lofi |
| Deep Intense Rock | … 5. Sunrise City | … 5. **Fiesta Calle** | a happy Latin song sneaks into a rock list |
| Sad but 0.9 energy | Paper Boats 3.54 vs #2 1.81 | Paper Boats **3.08** vs Storm Runner **2.97** | the sad folk song nearly loses to a rock banger |

**Verdict: different, and only partly more accurate.** For the pop and lofi listeners the new order feels
*better* — "vibe" (mood + energy) beat the genre label. But for the rock listener it got *worse*: once
genre matters less, any loud song qualifies, so a cheerful Latin party track shows up in a "deep intense
rock" list. Energy alone can't tell "angry loud" from "happy loud."

### Experiment 2 — Feature removal: ignore mood (`--weights no-mood`)

- **High-Energy Pop:** *Gym Hero* jumps from #3 to **#2**, above *Rooftop Lights*, because the only thing that
  was holding it back was the missing "happy" tag. This made the list *less* accurate for someone who
  wants happy music.
- **Chill Lofi:** *Focus Flow* (lofi/focused) climbs above *Midnight Coding* (lofi/chill); the list becomes
  "all the lofi, sorted by energy."
- **Unknown (polka/nostalgic):** the only song that matched anything (*Dusty Back Roads*, nostalgic) drops
  from #1 to #3 — the user's one meaningful signal is thrown away.

**Verdict:** removing mood makes genre even more dominant. Mood is the main thing that lets the system tell
apart two songs from the same genre.

### Asking "why did this song rank first?"

For the pop profile, *Gym Hero* keeps showing up at #3 even though it's a gym-workout track, not a happy
one. The reason is pure arithmetic: genre is worth **2.0** and mood only **1.0**, so Gym Hero's
`2.00 (pop) + 1.30 (energy 0.93)` = **3.30** beats *Fiesta Calle*'s `1.00 (happy) + 1.44 (energy 0.84)` = **2.44**.
The system trusts the word "pop" more than the word "happy."

---

## Limitations and Risks

- **Tiny catalog:** 20 songs, and 13 of the 15 genres have only one song. A rock fan gets exactly one
  rock song and then whatever is loud.
- **Genre filter bubble:** a genre match (+2.0) is worth more than a mood match (+1.0), so the system
  sticks to labels over vibes and almost never surfaces a great song from a neighboring genre.
- **Exact string matching:** "chill" ≠ "relaxed", "rock" ≠ "metal", "polka" matches nothing — the system
  doesn't know which labels are related (only the simple "pop" ⊂ "indie pop" case is handled).
- **Conflicting tastes are silently "resolved" by the weights**, not by asking the user (see the sad-but-0.9
  energy profile).
- **No lyrics, language, artist, or listening history** — it can't learn from skips, so it never improves.
- Tempo, valence, and danceability are loaded but not scored yet.

See [`model_card.md`](model_card.md) for the full bias analysis.

---

## Reflection

Read the full [**Model Card**](model_card.md) for intended use, data, bias analysis, pair-by-pair
profile comparisons, and a personal reflection.

**How recommenders turn data into predictions.** A recommender doesn't "understand" music; it turns a
song into a handful of numbers and labels (features), turns a person into target values for those same
features, and then measures how close they are. The prediction "you'll like this" is really "this song
scored highest on rules someone chose." Splitting the work into a *scoring rule* (judge one song) and a
*ranking rule* (sort them all) made that clear — and it showed me that most of the "intelligence" is in
the weights, which are design decisions, not facts.

**Where bias shows up.** Bias crept in from two places I didn't expect to matter: the weights and the
dataset. Making genre worth twice as much as mood meant a loud workout track (*Gym Hero*) kept showing up
for people who asked for happy music, just because of its "pop" tag. And because lofi has three songs
while rock, metal, and folk have one each, lofi fans get better lists than everyone else through no
choice of their own. At real-world scale, the same effects would decide which artists get heard.
