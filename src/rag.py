"""Retrieval layer: a small TF-IDF search over the knowledge base in data/knowledge/.

Pure standard library so the project runs with no API keys and gives reproducible results.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

STOPWORDS = {
    "a", "an", "the", "to", "for", "some", "something", "music", "songs", "song", "play", "i", "me", "my",
    "want", "need", "like", "of", "and", "in", "on", "with", "that", "is", "it", "so", "feel", "feeling",
    "give", "recommend", "please", "am", "im", "be", "get", "something", "while", "when", "about", "at",
    "listen", "listening", "something", "really", "just", "kind", "bit", "little", "can", "you", "would",
}
_TOKEN = re.compile(r"[a-z0-9]+(?:[&'-][a-z0-9]+)*")
_SUFFIXES = ("ing", "ers", "es", "ed", "s")


@dataclass
class Chunk:
    """One retrievable knowledge entry plus the structured hints that drive profile building."""
    title: str
    source: str
    text: str
    keywords: List[str] = field(default_factory=list)
    genres: List[str] = field(default_factory=list)
    moods: List[str] = field(default_factory=list)
    energy: Optional[float] = None
    acoustic: Optional[bool] = None


def stem(token: str) -> str:
    """Very light suffix stripping so 'studying' matches 'study' and 'beats' matches 'beat'."""
    for suffix in _SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[: -len(suffix)]
    return token


def tokenize(text: str) -> List[str]:
    """Lowercase, split into word tokens, drop stopwords, stem."""
    return [stem(t) for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS]


def _split_list(value: str) -> List[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def load_knowledge(directory: Path) -> List[Chunk]:
    """Parse every *.md file in `directory` into chunks (one per '## ' section)."""
    chunks: List[Chunk] = []
    for path in sorted(Path(directory).glob("*.md")):
        current: Optional[Dict[str, str]] = None
        sections: List[Dict[str, str]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                current = {"title": line[3:].strip()}
                sections.append(current)
            elif current is not None and ":" in line and not line.startswith("#"):
                key, _, value = line.partition(":")
                current[key.strip().lower()] = value.strip()
        for sec in sections:
            acoustic = sec.get("acoustic", "").lower()
            chunks.append(Chunk(
                title=sec["title"],
                source=path.name,
                text=sec.get("text", ""),
                keywords=_split_list(sec.get("keywords", "")),
                genres=_split_list(sec.get("genres", "")),
                moods=_split_list(sec.get("moods", "")),
                energy=float(sec["energy"]) if sec.get("energy") else None,
                acoustic={"true": True, "false": False}.get(acoustic),
            ))
    return chunks


class Retriever:
    """TF-IDF + cosine similarity over knowledge chunks."""

    def __init__(self, chunks: List[Chunk]):
        if not chunks:
            raise ValueError("knowledge base is empty")
        self.chunks = chunks
        docs = [self._doc_tokens(c) for c in chunks]
        df = Counter(tok for doc in docs for tok in set(doc))
        n = len(docs)
        self.idf = {tok: math.log((1 + n) / (1 + count)) + 1.0 for tok, count in df.items()}
        self.vectors = [self._vectorize(doc) for doc in docs]

    @staticmethod
    def _doc_tokens(chunk: Chunk) -> List[str]:
        # Keywords are repeated so a direct keyword hit outweighs incidental prose overlap.
        body = f"{chunk.title} {chunk.text}"
        return tokenize(body) + tokenize(" ".join(chunk.keywords)) * 3

    def _vectorize(self, tokens: List[str]) -> Dict[str, float]:
        counts = Counter(t for t in tokens if t in self.idf)
        vec = {tok: (1 + math.log(c)) * self.idf[tok] for tok, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {tok: v / norm for tok, v in vec.items()}

    def search(self, query: str, k: int = 3, min_score: float = 0.10) -> List[Tuple[Chunk, float]]:
        """Return up to k (chunk, similarity) pairs at or above min_score, best first."""
        qvec = self._vectorize(tokenize(query))
        if not qvec:
            return []
        scored = []
        for chunk, vec in zip(self.chunks, self.vectors):
            sim = sum(weight * vec.get(tok, 0.0) for tok, weight in qvec.items())
            if sim >= min_score:
                scored.append((chunk, round(sim, 3)))
        return sorted(scored, key=lambda pair: (-pair[1], pair[0].title))[:k]
