"""Tests for the functional API: load_songs, score_song, recommend_songs."""

from pathlib import Path

import pytest

from src.recommender import EXPERIMENT_WEIGHTS, load_songs, recommend_songs, score_song

DATA = Path(__file__).resolve().parent.parent / "data" / "songs.csv"


def make_song(**overrides):
    song = {
        "id": 1, "title": "T", "artist": "A", "genre": "pop", "mood": "happy",
        "energy": 0.8, "tempo_bpm": 120.0, "valence": 0.8, "danceability": 0.8, "acousticness": 0.2,
    }
    song.update(overrides)
    return song


def test_load_songs_converts_numeric_columns():
    songs = load_songs(str(DATA))
    assert len(songs) == 20
    first = songs[0]
    assert isinstance(first["id"], int)
    for field in ("energy", "tempo_bpm", "valence", "danceability", "acousticness"):
        assert isinstance(first[field], float)


def test_perfect_match_scores_genre_mood_and_full_energy():
    score, reasons = score_song({"genre": "pop", "mood": "happy", "energy": 0.8}, make_song())
    assert score == pytest.approx(2.0 + 1.0 + 1.5)
    assert any("genre match" in r for r in reasons)
    assert any("mood match" in r for r in reasons)


def test_energy_rewards_closeness_not_magnitude():
    prefs = {"energy": 0.4}
    close, _ = score_song(prefs, make_song(energy=0.45))
    loud, _ = score_song(prefs, make_song(energy=0.95))
    assert close > loud


def test_partial_genre_match_gets_partial_credit():
    score, reasons = score_song({"genre": "pop"}, make_song(genre="indie pop"))
    assert score == pytest.approx(1.0)
    assert "related genre" in reasons[0]


def test_matching_is_case_insensitive():
    score, _ = score_song({"genre": "POP", "mood": "Happy"}, make_song())
    assert score == pytest.approx(3.0)


def test_acoustic_preference_both_directions():
    acoustic = make_song(acousticness=0.9)
    yes, _ = score_song({"likes_acoustic": True}, acoustic)
    no, _ = score_song({"likes_acoustic": False}, acoustic)
    assert yes == pytest.approx(0.45)
    assert no == pytest.approx(0.05)


def test_recommend_songs_sorted_desc_and_limited_to_k():
    songs = load_songs(str(DATA))
    recs = recommend_songs({"genre": "lofi", "mood": "chill", "energy": 0.35}, songs, k=3)
    assert len(recs) == 3
    scores = [score for _, score, _ in recs]
    assert scores == sorted(scores, reverse=True)
    assert recs[0][0]["genre"] == "lofi"
    assert isinstance(recs[0][2], str) and recs[0][2]


def test_recommend_songs_does_not_mutate_catalog():
    songs = load_songs(str(DATA))
    before = [s["id"] for s in songs]
    recommend_songs({"genre": "rock", "energy": 0.9}, songs, k=5)
    assert [s["id"] for s in songs] == before


def test_no_mood_experiment_ignores_mood():
    score, reasons = score_song({"mood": "happy"}, make_song(), EXPERIMENT_WEIGHTS["no-mood"])
    assert score == 0.0
    assert reasons == []
