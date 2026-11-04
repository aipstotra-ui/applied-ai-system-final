"""Core logic for the VibeFinder music recommender simulation."""

import csv
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple

# Points awarded by score_song. Kept in one place so experiments can swap them out.
DEFAULT_WEIGHTS: Dict[str, float] = {
    "genre": 2.0,          # exact genre match
    "genre_partial": 1.0,  # one genre name contains the other ("pop" vs "indie pop")
    "mood": 1.0,           # exact mood match
    "energy": 1.5,         # multiplied by closeness: 1 - |song energy - target|
    "acoustic": 0.5,       # multiplied by how well acousticness fits likes_acoustic
}

# Experiment variants used in Phase 4 (see README "Experiments You Tried").
EXPERIMENT_WEIGHTS: Dict[str, Dict[str, float]] = {
    "default": DEFAULT_WEIGHTS,
    # Weight shift: double energy, halve genre.
    "energy-heavy": {**DEFAULT_WEIGHTS, "genre": 1.0, "genre_partial": 0.5, "energy": 3.0},
    # Feature removal: ignore mood entirely.
    "no-mood": {**DEFAULT_WEIGHTS, "mood": 0.0},
}

INT_FIELDS = ("id",)
FLOAT_FIELDS = ("energy", "tempo_bpm", "valence", "danceability", "acousticness")


@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

    def to_prefs(self) -> Dict:
        """Convert the profile into the user_prefs dict used by score_song."""
        return {
            "genre": self.favorite_genre,
            "mood": self.favorite_mood,
            "energy": self.target_energy,
            "likes_acoustic": self.likes_acoustic,
        }


class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song], weights: Optional[Dict[str, float]] = None):
        """Store the catalog and the scoring weights to use."""
        self.songs = songs
        self.weights = weights or DEFAULT_WEIGHTS

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top k Song objects for this user, best first."""
        prefs = user.to_prefs()
        scored = [(song, score_song(prefs, asdict(song), self.weights)[0]) for song in self.songs]
        ranked = sorted(scored, key=lambda pair: (-pair[1], pair[0].title))
        return [song for song, _ in ranked[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a human-readable explanation of how this song was scored."""
        score, reasons = score_song(user.to_prefs(), asdict(song), self.weights)
        return f"Score {score:.2f}: " + "; ".join(reasons)


def load_songs(csv_path: str) -> List[Dict]:
    """Read songs.csv into a list of dicts with numeric columns converted to int/float."""
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            song: Dict = {key: value.strip() for key, value in row.items()}
            for field in INT_FIELDS:
                song[field] = int(song[field])
            for field in FLOAT_FIELDS:
                song[field] = float(song[field])
            songs.append(song)
    return songs


def _genre_points(user_genre: str, song_genre: str, weights: Dict[str, float]) -> Tuple[float, Optional[str]]:
    """Score the genre rule: full points for an exact match, partial for a related genre."""
    if not user_genre:
        return 0.0, None
    if user_genre == song_genre:
        return weights["genre"], f"genre match: {song_genre} (+{weights['genre']:.2f})"
    if user_genre in song_genre.split() or song_genre in user_genre.split():
        return weights["genre_partial"], (
            f"related genre: {song_genre} ~ {user_genre} (+{weights['genre_partial']:.2f})"
        )
    return 0.0, None


def score_song(user_prefs: Dict, song: Dict, weights: Optional[Dict[str, float]] = None) -> Tuple[float, List[str]]:
    """Score one song against user_prefs; return (score, list of reasons with points)."""
    w = weights or DEFAULT_WEIGHTS
    score = 0.0
    reasons: List[str] = []

    # 1. Genre: categorical match.
    user_genre = str(user_prefs.get("genre", "")).strip().lower()
    points, reason = _genre_points(user_genre, song["genre"].lower(), w)
    if reason and points > 0:
        score += points
        reasons.append(reason)

    # 2. Mood: categorical match.
    user_mood = str(user_prefs.get("mood", "")).strip().lower()
    if user_mood and user_mood == song["mood"].lower() and w["mood"] > 0:
        score += w["mood"]
        reasons.append(f"mood match: {song['mood']} (+{w['mood']:.2f})")

    # 3. Energy: reward closeness to the target, not "more" or "less".
    if user_prefs.get("energy") is not None:
        target = float(user_prefs["energy"])
        gap = abs(song["energy"] - target)
        points = round(w["energy"] * max(0.0, 1.0 - gap), 2)
        score += points
        reasons.append(f"energy {song['energy']:.2f} vs target {target:.2f} (+{points:.2f})")

    # 4. Acoustic preference: optional; omitted or None means "no preference".
    likes_acoustic = user_prefs.get("likes_acoustic")
    if likes_acoustic is not None and w["acoustic"] > 0:
        fit = song["acousticness"] if likes_acoustic else 1.0 - song["acousticness"]
        points = round(w["acoustic"] * fit, 2)
        score += points
        label = "acoustic" if likes_acoustic else "produced/electronic"
        reasons.append(f"{label} sound fit {fit:.2f} (+{points:.2f})")

    return round(score, 2), reasons


def recommend_songs(
    user_prefs: Dict, songs: List[Dict], k: int = 5, weights: Optional[Dict[str, float]] = None
) -> List[Tuple[Dict, float, str]]:
    """Score every song, sort high-to-low (ties by title), and return the top k as (song, score, explanation)."""
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song, weights)
        scored.append((song, score, "; ".join(reasons) or "no matching features"))
    # sorted() returns a NEW list and leaves `songs` untouched; .sort() would reorder in place.
    return sorted(scored, key=lambda item: (-item[1], item[0]["title"]))[:k]
