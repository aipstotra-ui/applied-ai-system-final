"""VibeFinder agent: plan -> retrieve -> build profile -> recommend -> verify -> (revise) -> answer.

The retrieved knowledge chunks decide the user profile that the original VibeFinder scorer ranks with,
so removing retrieval changes the output (it is not decoration printed next to a fixed answer).
"""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.guardrails import validate_query
from src.rag import Chunk, Retriever, load_knowledge
from src.recommender import DEFAULT_WEIGHTS, load_songs, recommend_songs

log = logging.getLogger("vibefinder")

ROOT = Path(__file__).resolve().parent.parent
SONGS_PATH = ROOT / "data" / "songs.csv"
KNOWLEDGE_DIR = ROOT / "data" / "knowledge"

MIN_CONFIDENCE = 0.55      # below this the agent asks the human to clarify instead of answering
MIN_TOP_SCORE_FRAC = 0.60  # verification: top song must earn >= 60% of the points available to it
MAX_ENERGY_SPREAD = 0.40   # retrieved entries that disagree this much on energy signal a contradictory request
MAX_ENERGY_GAP = 0.25      # verification: top song energy must be near the target

_ENERGY_RE = re.compile(r"energy\s*(?:of|at|=|:|around|about)?\s*(1(?:\.0+)?|0?\.\d+|0)\b")


@dataclass
class AgentResult:
    """Everything the CLI, tests and evaluation harness need from one request."""
    query: str
    status: str                      # ok | low_confidence | rejected | no_match
    message: str = ""
    profile: Dict = field(default_factory=dict)
    sources: List[Tuple[str, float]] = field(default_factory=list)   # (chunk title, similarity)
    recommendations: List[Tuple[Dict, float, str]] = field(default_factory=list)
    confidence: float = 0.0
    verified: bool = False
    trace: List[str] = field(default_factory=list)


def setup_logging(log_dir: Path = ROOT / "logs") -> None:
    """Send agent logs to logs/agent.log (called by the CLI and eval script, not by unit tests)."""
    log_dir.mkdir(exist_ok=True)
    handler = logging.FileHandler(log_dir / "agent.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)


class VibeFinderAgent:
    """Orchestrates retrieval, profile building, ranking, self-checking and confidence scoring."""

    def __init__(self, songs: Optional[List[Dict]] = None, retriever: Optional[Retriever] = None,
                 use_retrieval: bool = True):
        self.songs = songs if songs is not None else load_songs(str(SONGS_PATH))
        self.retriever = retriever or Retriever(load_knowledge(KNOWLEDGE_DIR))
        self.use_retrieval = use_retrieval
        self.genres = sorted({s["genre"].lower() for s in self.songs}, key=lambda g: -len(g))
        self.moods = sorted({s["mood"].lower() for s in self.songs}, key=lambda m: -len(m))

    # ---- step helpers -------------------------------------------------------------------------

    def _explicit_terms(self, query: str) -> Tuple[List[str], List[str], Optional[float]]:
        """Find genre/mood words and 'energy 0.8' stated directly in the request."""
        lowered = query.lower()
        found_genres, found_moods = [], []
        remaining = lowered
        for genre in self.genres:  # longest first so "indie pop" is not also counted as "pop"
            pattern = rf"(?<![a-z]){re.escape(genre)}(?![a-z])"
            if re.search(pattern, remaining):
                found_genres.append(genre)
                remaining = re.sub(pattern, " ", remaining)
        for mood in self.moods:
            if re.search(rf"(?<![a-z]){re.escape(mood)}(?![a-z])", lowered):
                found_moods.append(mood)
        match = _ENERGY_RE.search(lowered)
        return found_genres, found_moods, float(match.group(1)) if match else None

    def _build_profile(self, hits: List[Tuple[Chunk, float]], explicit: Tuple) -> Dict:
        """Turn retrieved chunks (similarity-weighted votes) plus explicit terms into user prefs."""
        genres, moods, energy = explicit
        genre_votes: Dict[str, float] = defaultdict(float)
        mood_votes: Dict[str, float] = defaultdict(float)
        energy_num = energy_den = acoustic_vote = 0.0
        for chunk, sim in hits:
            for rank, g in enumerate(chunk.genres):
                genre_votes[g] += sim / (rank + 1)
            for rank, m in enumerate(chunk.moods):
                mood_votes[m] += sim / (rank + 1)
            if chunk.energy is not None:
                energy_num += sim * chunk.energy
                energy_den += sim
            if chunk.acoustic is not None:
                acoustic_vote += sim * (1 if chunk.acoustic else -1)
        for g in genres:
            genre_votes[g] += 1.0   # a genre named outright beats anything inferred
        for m in moods:
            mood_votes[m] += 1.0
        profile: Dict = {}
        if genre_votes:
            profile["genre"] = max(genre_votes, key=lambda g: (genre_votes[g], g))
        if mood_votes:
            profile["mood"] = max(mood_votes, key=lambda m: (mood_votes[m], m))
        if energy is not None:
            profile["energy"] = min(1.0, max(0.0, energy))
        elif energy_den:
            profile["energy"] = round(energy_num / energy_den, 2)
        if abs(acoustic_vote) > 1e-9:
            profile["likes_acoustic"] = acoustic_vote > 0
        profile["_genre_votes"] = dict(genre_votes)
        return profile

    @staticmethod
    def _max_points(profile: Dict) -> float:
        w = DEFAULT_WEIGHTS
        total = 0.0
        total += w["genre"] if "genre" in profile else 0.0
        total += w["mood"] if "mood" in profile else 0.0
        total += w["energy"] if "energy" in profile else 0.0
        total += w["acoustic"] if "likes_acoustic" in profile else 0.0
        return total or 1.0

    def _verify(self, profile: Dict, recs: List[Tuple[Dict, float, str]]) -> Tuple[bool, List[str]]:
        """Self-check the top result against the profile. Returns (passed, list of failed checks)."""
        if not recs:
            return False, ["no recommendations returned"]
        top, score, _ = recs[0]
        problems = []
        genre_ok = "genre" not in profile or profile["genre"] in top["genre"].lower() or top["genre"].lower() in profile["genre"]
        mood_ok = "mood" not in profile or profile["mood"] == top["mood"].lower()
        if not (genre_ok or mood_ok):
            problems.append(f"top song '{top['title']}' matches neither genre nor mood")
        if "energy" in profile and abs(top["energy"] - profile["energy"]) > MAX_ENERGY_GAP:
            problems.append(f"top song energy {top['energy']:.2f} is far from target {profile['energy']:.2f}")
        if score / self._max_points(profile) < MIN_TOP_SCORE_FRAC:
            problems.append(f"top score {score:.2f} is under {MIN_TOP_SCORE_FRAC:.0%} of available points")
        return not problems, problems

    # ---- main entry point ---------------------------------------------------------------------

    def ask(self, query: str, k: int = 3) -> AgentResult:
        """Run the full pipeline for one natural-language request."""
        result = AgentResult(query=str(query), status="ok")
        trace = result.trace

        check = validate_query(query)
        if not check.ok:
            result.status, result.message = "rejected", f"Request rejected: {check.reason}."
            trace.append(f"1. GUARDRAIL rejected input: {check.reason}")
            log.warning("rejected query=%r reason=%s", str(query)[:80], check.reason)
            return result
        query = check.cleaned
        result.query = query
        trace.append("1. GUARDRAIL input accepted")

        explicit = self._explicit_terms(query)
        trace.append(f"2. PLAN explicit terms: genres={explicit[0]} moods={explicit[1]} energy={explicit[2]}")

        hits = self.retriever.search(query, k=3) if self.use_retrieval else []
        result.sources = [(c.title, s) for c, s in hits]
        trace.append("3. RETRIEVE " + (", ".join(f"{c.title} ({s:.2f})" for c, s in hits) or "nothing relevant found"))

        if not hits and not (explicit[0] or explicit[1] or explicit[2] is not None):
            result.status = "no_match"
            result.message = ("I couldn't connect that to any music situation, mood or genre I know. "
                              "Try something like 'music for studying' or 'sad folk with low energy'.")
            trace.append("4. STOP no retrieval hits and no explicit terms; asking the human to rephrase")
            log.info("no_match query=%r", query)
            return result

        profile = self._build_profile(hits, explicit)
        votes = profile.pop("_genre_votes")
        trace.append(f"4. PROFILE {self._fmt(profile)}")

        recs = recommend_songs(profile, self.songs, k=k)
        passed, problems = self._verify(profile, recs)
        trace.append(f"5. RECOMMEND top='{recs[0][0]['title']}' score={recs[0][1]:.2f}")
        trace.append("6. VERIFY " + ("passed" if passed else "failed: " + "; ".join(problems)))

        if not passed:
            revised = self._revise(profile, votes, recs)
            if revised:
                profile, recs, passed = revised
                trace.append(f"7. REVISE retried with {self._fmt(profile)} -> top='{recs[0][0]['title']}' "
                             f"score={recs[0][1]:.2f}; verify {'passed' if passed else 'still failed'}")
            else:
                trace.append("7. REVISE no better alternative found")

        top_sim = hits[0][1] if hits else 0.5 if (explicit[0] or explicit[1]) else 0.0
        norm_score = recs[0][1] / self._max_points(profile)
        confidence = 0.4 * min(1.0, top_sim / 0.5) + 0.6 * norm_score
        if not passed:
            confidence -= 0.15
        energies = [c.energy for c, _ in hits if c.energy is not None]
        if explicit[2] is None and energies and max(energies) - min(energies) > MAX_ENERGY_SPREAD:
            confidence -= 0.25
            trace.append(f"7b. CONFLICT retrieved entries disagree on energy ({min(energies):.2f}-{max(energies):.2f}); lowering confidence")
        result.confidence = round(max(0.0, min(1.0, confidence)), 2)
        result.profile, result.recommendations, result.verified = profile, recs, passed

        if result.confidence < MIN_CONFIDENCE:
            result.status = "low_confidence"
            result.message = (f"I'm only {result.confidence:.0%} sure about this. Please add a genre, mood or "
                              "activity so I can do better. Best guess below.")
            trace.append(f"8. HUMAN-IN-THE-LOOP confidence {result.confidence:.2f} < {MIN_CONFIDENCE}; asking for clarification")
        else:
            result.status = "ok"
            trace.append(f"8. ANSWER confidence {result.confidence:.2f}")
        log.info("query=%r status=%s confidence=%.2f verified=%s top=%s", query, result.status,
                 result.confidence, passed, recs[0][0]["title"])
        return result

    def _revise(self, profile: Dict, votes: Dict[str, float], recs) -> Optional[Tuple[Dict, List, bool]]:
        """One retry: swap to the runner-up genre, and drop the acoustic preference. Keep it only if better."""
        best = (recs[0][1] / self._max_points(profile), profile, recs, False)
        ranked = sorted(votes, key=lambda g: (-votes[g], g))
        candidates = []
        for genre in ranked[1:2] + [None]:
            alt = dict(profile)
            if genre:
                alt["genre"] = genre
            else:
                alt.pop("genre", None)
            alt.pop("likes_acoustic", None)
            candidates.append(alt)
        for alt in candidates:
            alt_recs = recommend_songs(alt, self.songs, k=len(recs))
            passed, _ = self._verify(alt, alt_recs)
            norm = alt_recs[0][1] / self._max_points(alt)
            if (passed, norm) > (best[3], best[0]):
                best = (norm, alt, alt_recs, passed)
        if best[1] is profile:
            return None
        return best[1], best[2], best[3]

    @staticmethod
    def _fmt(profile: Dict) -> str:
        return ", ".join(f"{k}={v}" for k, v in profile.items())
