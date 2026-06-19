"""Deterministic TF-IDF + cosine similarity classifier for evidence → dimension mapping.

Zero external dependencies, zero LLM calls. Pure Python implementation.
Returns a confidence score (cosine similarity) for every classification.
"""

import re
import math
from collections import Counter


def _tokenize(text: str) -> list[str]:
    """Extract features from text — CJK bigrams + English words."""
    text = text.lower()
    tokens: list[str] = []

    # CJK character bigrams (overlapping pairs) + unigrams
    # NOTE: no 'r' prefix — \u must be interpreted as Unicode escape
    cjk_runs = re.findall('[一-鿿]+', text)
    for run in cjk_runs:
        for i in range(len(run) - 1):
            tokens.append(run[i:i+2])
        # Also add individual characters for short phrases
        if len(run) <= 4:
            for ch in run:
                tokens.append(ch)

    # English / alphanumeric words (length >= 2)
    en_tokens = re.findall(r'[a-z0-9]{2,}', text)
    tokens.extend(en_tokens)

    # Filter stop words
    stops = {
        'the', 'an', 'is', 'are', 'was', 'were', 'on', 'at', 'to', 'for',
        'of', 'and', 'or', 'it', 'its', 'be', 'by', 'as', 'with', 'from', 'that',
        'this', 'has', 'have', 'had', 'do', 'does', 'did', 'not', 'no',
        'but', 'if', 'so', 'we', 'you', 'he', 'she', 'they', 'can', 'will',
    }
    return [t for t in tokens if t not in stops]
class TfidfClassifier:
    """Classify evidence claims to dimensions using TF-IDF + cosine similarity."""

    def __init__(self, dimensions: list[dict]):
        """dimensions: list of {"name": ..., "description": ..., "subquestions": [...]}"""
        self._dimensions = dimensions
        self._dim_texts = [
            f"{d['name']} {d.get('description', '')} {' '.join(d.get('subquestions', []))}"
            for d in dimensions
        ]
        self._idf = self._compute_idf()
        self._dim_vectors = [self._vectorize(t) for t in self._dim_texts]

    def _compute_idf(self) -> dict[str, float]:
        """Compute inverse document frequency across all dimension texts."""
        all_docs = [set(_tokenize(t)) for t in self._dim_texts]
        df: Counter = Counter()
        for doc_tokens in all_docs:
            df.update(doc_tokens)

        n_docs = len(self._dim_texts)
        idf: dict[str, float] = {}
        for term, count in df.items():
            idf[term] = math.log((n_docs + 1) / (count + 1)) + 1.0
        return idf

    def _vectorize(self, text: str) -> dict[str, float]:
        """Convert text to a sparse TF-IDF vector."""
        tokens = _tokenize(text)
        if not tokens:
            return {}
        tf = Counter(tokens)
        max_tf = max(tf.values())
        return {
            term: (tf[term] / max_tf) * self._idf.get(term, 0.0)
            for term in tf
            if term in self._idf
        }

    @staticmethod
    def _cosine_similarity(v1: dict[str, float], v2: dict[str, float]) -> float:
        """Cosine similarity between two sparse vectors."""
        if not v1 or not v2:
            return 0.0
        all_keys = set(v1) | set(v2)
        dot = sum(v1.get(k, 0) * v2.get(k, 0) for k in all_keys)
        norm1 = math.sqrt(sum(v * v for v in v1.values()))
        norm2 = math.sqrt(sum(v * v for v in v2.values()))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def classify(self, text: str) -> tuple[int, float]:
        """Classify text to the most similar dimension.
        Returns (dimension_index, confidence_score).
        """
        query_vec = self._vectorize(text)
        if not query_vec:
            return 0, 0.0

        best_idx = 0
        best_score = 0.0
        for i, dim_vec in enumerate(self._dim_vectors):
            score = self._cosine_similarity(query_vec, dim_vec)
            if score > best_score:
                best_score = score
                best_idx = i

        return best_idx, best_score

    def classify_batch(self, texts: list[str]) -> list[tuple[int, float]]:
        """Classify multiple texts at once."""
        return [self.classify(t) for t in texts]
