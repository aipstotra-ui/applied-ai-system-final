"""
Command line runner for the VibeFinder music recommender simulation.

Usage (from the repo root):
    python -m src.main                              # every profile, default weights
    python -m src.main --profile pop                # one profile
    python -m src.main --weights energy-heavy       # run an experiment
    python -m src.main --profile rock -k 3
"""

import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.recommender import EXPERIMENT_WEIGHTS, load_songs, recommend_songs

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "songs.csv"

# Three "normal" listeners plus three adversarial / edge-case profiles.
PROFILES: Dict[str, Dict] = {
    "pop": {"label": "High-Energy Pop", "genre": "pop", "mood": "happy", "energy": 0.8},
    "lofi": {"label": "Chill Lofi", "genre": "lofi", "mood": "chill", "energy": 0.35, "likes_acoustic": True},
    "rock": {"label": "Deep Intense Rock", "genre": "rock", "mood": "intense", "energy": 0.9, "likes_acoustic": False},
    # Edge cases designed to try to "trick" the scorer.
    "sad-hype": {"label": "Conflicted: Sad but 0.9 Energy", "genre": "folk", "mood": "sad", "energy": 0.9},
    "unknown": {"label": "Unknown Genre (polka) + Mood (nostalgic)", "genre": "polka", "mood": "nostalgic", "energy": 0.5},
    "no-prefs": {"label": "Energy Only (0.5), No Genre/Mood", "energy": 0.5},
}


def describe(prefs: Dict) -> str:
    """Return a one-line summary of a profile's preferences."""
    keys = ("genre", "mood", "energy", "likes_acoustic")
    return ", ".join(f"{key}={prefs[key]}" for key in keys if key in prefs)


def print_recommendations(name: str, prefs: Dict, recs: List[Tuple[Dict, float, str]], weights_name: str) -> None:
    """Print a readable block: profile header, then each ranked song with its reasons."""
    width = 72
    print("=" * width)
    print(f"Profile: {prefs.get('label', name)}  [weights: {weights_name}]")
    print(f"Prefs:   {describe(prefs)}")
    print("-" * width)
    for rank, (song, score, explanation) in enumerate(recs, start=1):
        print(f"{rank}. {song['title']} - {song['artist']}  ({song['genre']}, {song['mood']})")
        print(f"   Score: {score:.2f}")
        for reason in explanation.split("; "):
            print(f"     • {reason}")
    print()


def main(argv: Optional[List[str]] = None) -> None:
    """Load the catalog and print top-k recommendations for the chosen profile(s)."""
    parser = argparse.ArgumentParser(description="VibeFinder music recommender simulation")
    parser.add_argument("--profile", choices=sorted(PROFILES), help="run a single profile (default: all)")
    parser.add_argument("--weights", choices=sorted(EXPERIMENT_WEIGHTS), default="default",
                        help="weight set to use (experiments)")
    parser.add_argument("-k", type=int, default=5, help="number of recommendations to show")
    args = parser.parse_args(argv)

    songs = load_songs(str(DATA_PATH))
    print(f"Loaded songs: {len(songs)}\n")

    weights = EXPERIMENT_WEIGHTS[args.weights]
    names = [args.profile] if args.profile else list(PROFILES)
    for name in names:
        prefs = PROFILES[name]
        recs = recommend_songs(prefs, songs, k=args.k, weights=weights)
        print_recommendations(name, prefs, recs, args.weights)


if __name__ == "__main__":
    main()
