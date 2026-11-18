"""
Command line runner for the VibeFinder music recommender simulation.

Usage (from the repo root):
    python -m src.main                              # every profile, default weights
    python -m src.main --profile pop                # one profile
    python -m src.main --weights energy-heavy       # run an experiment
    python -m src.main --profile rock -k 3
    python -m src.main --ask "something to study to"          # AI agent: RAG + self-check
    python -m src.main --ask "gym, energy 0.9" --trace        # also print the agent's reasoning steps
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


def run_agent(query: str, k: int, show_trace: bool) -> None:
    """Answer one natural-language request with the RAG agent and print the result."""
    from src.agent import VibeFinderAgent, setup_logging

    setup_logging()
    result = VibeFinderAgent().ask(query, k=k)
    print("=" * 72)
    print(f"Request:    {result.query!r}")
    print(f"Status:     {result.status}   confidence={result.confidence:.2f}   verified={result.verified}")
    if result.message:
        print(f"Message:    {result.message}")
    if result.sources:
        print("Retrieved:  " + "; ".join(f"{title} ({sim:.2f})" for title, sim in result.sources))
    if result.profile:
        print("Profile:    " + describe(result.profile))
    print("-" * 72)
    for rank, (song, score, explanation) in enumerate(result.recommendations, start=1):
        print(f"{rank}. {song['title']} - {song['artist']}  ({song['genre']}, {song['mood']})  score {score:.2f}")
        for reason in explanation.split("; "):
            print(f"     • {reason}")
    if show_trace:
        print("-" * 72)
        print("Agent trace:")
        for step in result.trace:
            print(f"  {step}")
    print()


def main(argv: Optional[List[str]] = None) -> None:
    """Load the catalog and print top-k recommendations for the chosen profile(s)."""
    parser = argparse.ArgumentParser(description="VibeFinder music recommender simulation")
    parser.add_argument("--profile", choices=sorted(PROFILES), help="run a single profile (default: all)")
    parser.add_argument("--weights", choices=sorted(EXPERIMENT_WEIGHTS), default="default",
                        help="weight set to use (experiments)")
    parser.add_argument("--ask", metavar="TEXT", help="natural-language request answered by the RAG agent")
    parser.add_argument("--trace", action="store_true", help="with --ask: print the agent's reasoning trace")
    parser.add_argument("-k", type=int, default=5, help="number of recommendations to show")
    args = parser.parse_args(argv)

    if args.ask is not None:
        run_agent(args.ask, args.k if args.k != 5 else 3, args.trace)
        return

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
