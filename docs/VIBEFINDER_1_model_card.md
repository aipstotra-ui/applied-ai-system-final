# 🎧 Model Card: VibeFinder 1.0

## 1. Model Name

**VibeFinder 1.0** — a small, explainable, content-based music recommender that runs in the terminal.

---

## 2. Goal / Task and Intended Use

**Goal.** Given a listener's taste profile, VibeFinder predicts which songs in a small catalog they will
like most and shows the top 5, each with a list of reasons ("genre match: pop (+2.00)").

**Intended use.**

- Classroom exploration of how recommenders turn data into ranked suggestions.
- Experimenting with weights to see how small design choices change what people are shown.
- Practicing how to spot and explain bias in a simple model.

**Assumptions about the user.** The user can describe their taste with *one* favorite genre, *one*
favorite mood, a target energy from 0.0 (calm) to 1.0 (intense), and optionally whether they like
acoustic sound. Their taste doesn't change by time of day or activity.

**Not intended for.**

- Real users or a real product — the catalog is 20 made-up songs.
- Judging the quality of an artist or a genre. A low score means "doesn't fit this profile," not "bad song."
- Any decision with stakes (paying artists, promoting songs, profiling listeners).
- Listeners with mixed or changing tastes; the profile only holds one genre and one mood.

---

## 3. How the Model Works (Algorithm Summary)

Think of VibeFinder as a judge holding a scorecard. It looks at every song in the catalog, one at a time,
and hands out points:

- **Genre.** If the song's genre is exactly the listener's favorite, it gets **2 points**. If it's a close
  cousin by name (the listener likes "pop" and the song is "indie pop"), it gets **1 point**.
- **Mood.** If the song's mood is exactly the listener's favorite mood, it gets **1 point**.
- **Energy.** Up to **1.5 points** for being *close* to the energy the listener wants. A perfect match gets
  all 1.5; a song that's 0.2 away gets 1.2; a song on the opposite end gets almost nothing. Being louder
  isn't better — being *closer* is.
- **Acoustic sound (optional).** Up to **0.5 points**: acoustic songs earn more for someone who likes
  acoustic, and electronic/produced songs earn more for someone who doesn't.

The best possible score is 5.0. After every song has a score, VibeFinder sorts them from highest to
lowest (ties go alphabetically by title so the output is always the same) and shows the top 5.
Each recommendation prints the exact reasons and points it earned, so nothing is hidden.

**Changes from the starter:** implemented CSV loading with numeric conversion, the scoring rule above
(including partial genre credit and case-insensitive matching), ranking with `sorted()`, the
`Recommender` class on top of the same scoring function, and a CLI that runs six profiles and three
weight sets.

---

## 4. Data Used

- **Size:** 20 songs in `data/songs.csv` (10 from the starter + 10 I added).
- **Features per song:** genre, mood, energy (0–1), tempo in BPM, valence (positivity, 0–1),
  danceability (0–1), acousticness (0–1). Only genre, mood, energy, and acousticness are used in scoring.
- **What I added:** hip hop, classical, metal, country, reggae, EDM, R&B, folk, blues, and Latin songs, plus
  new moods (confident, peaceful, angry, nostalgic, euphoric, romantic, sad) that weren't in the starter.
- **Balance:** 15 genres. Lofi has 3 songs, pop has 2, and the other 13 genres have exactly 1 each.
  Moods: happy 3, chill 3, relaxed 2, sad 2, intense 2, everything else 1.
- **Limits:** the songs and numbers are invented, not measured from real audio. There is no lyrics,
  language, artist popularity, release year, or listening history. Whole areas of music (K-pop, gospel,
  punk, Afrobeats, soundtracks…) are missing. "Ground truth" — what a person would actually enjoy — doesn't
  exist here; I judged results against my own intuition.

---

## 5. Strengths

- **Clear-cut profiles work well.** The Chill Lofi and High-Energy Pop users get lists that feel right:
  the top 2–3 songs match genre, mood, and energy all at once.
- **Energy closeness behaves sensibly.** Calm users are steered away from loud songs and vice versa,
  instead of everyone getting the "most energetic" songs.
- **Fully explainable.** Every point is printed, so it's easy to answer "why is this song here?" — real
  apps rarely show this.
- **Graceful when data is missing.** An unknown genre or an empty profile still produces a list (ranked by
  energy) instead of crashing.

---

## 6. Limitations and Bias (Observed Behavior)

**Main weakness found: genre labels form a filter bubble, and the catalog makes it worse.** Because a
genre match (+2.0) is worth twice a mood match (+1.0), the system trusts the *label* more than the
*vibe*. For the "happy pop" listener, *Gym Hero* — an intense workout track — ranks #3, above the happy
Latin song *Fiesta Calle*, only because it's tagged "pop." This hurts most for listeners of genres with one
song: the Deep Intense Rock listener gets *Storm Runner* and then a pop workout song, EDM, and metal,
while the lofi listener gets three real lofi songs. So the system quietly serves lofi and pop fans better
than everyone else — not because of their taste, but because of how many songs happen to share their label.

Other patterns I observed:

- **Exact string matching misses obvious neighbors.** Metal (*Iron Cathedral*, energy 0.97) is musically the
  closest song to rock, but it ranks #4 for the rock listener — below EDM — because "metal" ≠ "rock" and
  "angry" ≠ "intense." Likewise "chill" and "relaxed" get no shared credit.
- **Conflicting preferences are settled by the weights, not the user.** For "sad but energy 0.9," the slow
  sad folk song *Paper Boats* (energy 0.26) still wins by a mile, because genre + mood (3.0) outweighs the
  maximum energy bonus (1.5). The system never notices that the request is contradictory.
- **Middle-energy songs are "safe" for everyone.** Songs around 0.5 energy are never far from any target,
  so they fill the bottom of many lists (the same five mid-energy songs fill the polka and energy-only lists).
- **Silent failure.** A polka fan gets no warning that polka isn't in the catalog; they just get mid-energy
  songs from other genres.

---

## 7. Evaluation Process

**Profiles tested** (all output is in the README's "Stress test" section):

1. **High-Energy Pop** — pop / happy / 0.8
2. **Chill Lofi** — lofi / chill / 0.35 / likes acoustic
3. **Deep Intense Rock** — rock / intense / 0.9 / not acoustic
4. **Conflicted** — folk / sad / 0.9 energy (adversarial: every sad song is slow)
5. **Unknown Genre** — polka / nostalgic / 0.5 (adversarial: genre not in catalog)
6. **Energy Only** — energy 0.5, no genre or mood (edge case)

**What I looked for:** does the #1 song make sense, do the reasons add up, does the list change when the
profile changes, and does any one song show up everywhere?

**Experiments:** (1) weight shift — energy doubled, genre halved; (2) feature removal — mood turned off.
Run with `python -m src.main --weights energy-heavy` / `--weights no-mood`. Results are in the README.

**Automated checks:** 11 pytest tests cover CSV loading, score math, closeness (not magnitude),
partial genre credit, case-insensitivity, acoustic preference, sort order, `k`, not mutating the catalog,
and the no-mood experiment.

**What surprised me:**

- *Gym Hero* showing up for "happy pop" even though it clearly isn't happy — one word ("pop") was enough.
- The sad-but-hyped profile: I expected loud songs to win; instead the slow folk song won easily. When I
  doubled the energy weight, it only won by 0.11 points — one small weight change nearly flipped the answer.
- How little "taste" the system needs to look convincing: three rules already produce lists that feel curated.

### Comparing profiles, pair by pair

- **Pop vs. Lofi:** Pop gets bright songs around 0.8 energy (*Sunrise City*, *Rooftop Lights*); lofi shifts
  to quiet, acoustic tracks around 0.35 (*Library Rain*, *Midnight Coding*). No song appears on both lists —
  energy and genre pull them to opposite ends of the catalog, which is exactly what should happen.
- **Pop vs. Rock:** Both want high energy, so loud songs overlap — *Gym Hero* is #3 for pop and #2 for rock.
  For pop it's there because of the genre label; for rock it's there because it's "intense" and loud. Same
  song, different reasons, which makes sense.
- **Pop vs. Conflicted (sad, 0.9):** Pop's top songs are high-energy *and* happy; the conflicted profile's
  #1 is slow and sad. Once you get past the two sad songs, the conflicted list becomes "loud songs" (rock,
  pop, EDM) — basically the pop/rock list without the happiness.
- **Pop vs. Unknown (polka):** Pop gets strong matches with scores above 4; polka's best score is 2.42 and
  only one song matches anything (the nostalgic country song). Low scores everywhere are a sign the
  catalog can't serve this user.
- **Pop vs. Energy Only:** Pop's list is shaped by labels; the energy-only list is just "songs closest to
  0.5" (reggae, R&B, country, blues, lofi). It shows what's left of the model when genre and mood are gone.
- **Lofi vs. Rock:** Complete opposites — lofi gets acoustic, slow songs; rock (not acoustic, 0.9) gets
  electronic, loud ones. The acoustic bonus pushes in opposite directions for the two, so it widens the gap.
- **Lofi vs. Conflicted:** Lofi's list is consistent (every song is calm), while the conflicted list jumps
  from a 0.26-energy folk song to 0.9+ rock and EDM. The lofi user asked for one coherent vibe; the
  conflicted user didn't, and the output shows that.
- **Lofi vs. Unknown:** Lofi has 3 genre matches and the top scores are near the 5.0 maximum; polka has
  zero. Same model, very different quality — the difference is the catalog, not the user.
- **Lofi vs. Energy Only:** *Midnight Coding* (0.42 energy) appears in both, but for lofi it's #2 with
  genre + mood + energy, while for energy-only it's #5 on energy alone.
- **Rock vs. Conflicted:** *Storm Runner*, *Gym Hero*, and *Laser Bloom* appear on both because both want
  ~0.9 energy. Rock puts them at the top; conflicted puts them *below* the sad songs, because the sad mood
  tag outweighs energy.
- **Rock vs. Unknown:** Both users have a "thin" genre (rock has 1 song, polka has 0). Rock still gets one
  perfect match and then loud fillers; polka gets only mid-energy fillers. Both show the catalog-size bias.
- **Rock vs. Energy Only:** Rock's list is all 0.8+ energy, while energy-only's list is all 0.42–0.55. The
  energy rule cleanly separates them.
- **Conflicted vs. Unknown:** In both, only one or two songs match a label, and the rest are filled by
  energy. The difference is that the conflicted user's filler is loud songs and the polka user's is mid-tempo.
- **Conflicted vs. Energy Only:** Same idea — once the labels run out, both lists are "closest energy."
  The conflicted list just starts with two sad songs on top.
- **Unknown vs. Energy Only:** Almost identical lists. The only difference is *Dusty Back Roads* jumping to
  #1 for polka thanks to the "nostalgic" mood match. This proves the genre "polka" contributed nothing.

**Plain-language takeaway:** *Gym Hero* keeps appearing for people who want "happy pop" because the
system gives more points for the word "pop" than for the word "happy," and Gym Hero is pop and loud.
It's not that the system thinks Gym Hero is happy — it just values the genre label more than the mood.

---

## 8. Ideas for Improvement

1. **Genre and mood similarity instead of exact matches.** A small lookup table (rock ↔ metal ↔ punk,
   chill ↔ relaxed ↔ peaceful) would give partial credit to close neighbors and reduce the filter bubble.
2. **Diversity in the ranking rule.** After scoring, avoid showing more than two songs from the same
   genre/artist in the top 5, so the list mixes "safe bets" and discoveries.
3. **Use more features and multiple tastes.** Score valence, tempo, and danceability; let a profile hold
   several genres with weights; and warn the user when their genre isn't in the catalog or their
   preferences conflict.
4. **Learn the weights from feedback.** Track likes/skips and nudge weights toward what each user actually
   responds to — the first step toward collaborative filtering.

---

## 9. Personal Reflection

> *Draft — rewrite in your own words before submitting.*

**Biggest learning moment.** Seeing *Gym Hero* rank for "happy pop" made bias concrete for me. I wrote
the weights myself and thought "genre matters more than mood" was a reasonable choice, but I didn't
realize it meant "the label matters more than how the song actually feels." A single number I picked
decided what a whole type of listener sees.

**How AI tools helped, and where I double-checked.** The AI assistant was fast at drafting the CSV loader,
the scoring function, the extra songs, and the edge-case profiles (the "sad but 0.9 energy" idea came from
asking for adversarial users). I still had to check its work: the first version printed per-reason points
that didn't add up to the total because of rounding (e.g. "+1.42" but a total ending in .43), so I made
each component round before being added. I also verified the experiment conclusions by actually running
them instead of trusting a prediction — the "energy-heavy" change helped pop and lofi but made rock worse,
which I wouldn't have guessed.

**What surprised me.** Three simple rules and 20 songs already produce lists that *feel* curated. That
makes me more skeptical of real apps: a recommendation can feel personal while really being driven by a
few labels and how many songs share them.

**What I'd try next.** Add a genre/mood similarity table, a diversity rule in the ranker, and a simple
feedback loop where skipping a song lowers the weight of whatever earned it its points.
