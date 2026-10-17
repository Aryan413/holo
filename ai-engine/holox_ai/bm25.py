"""BM25 ranking: the standard keyword-relevance formula used by search engines."""

import math
from collections import Counter


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._tf = [Counter(d) for d in docs]
        self._len = [len(d) for d in docs]
        n = len(docs)
        self._avg = (sum(self._len) / n) if n else 0.0

        doc_freq: Counter = Counter()
        for tf in self._tf:
            doc_freq.update(tf.keys())
        self._idf = {
            term: math.log(1 + (n - count + 0.5) / (count + 0.5))
            for term, count in doc_freq.items()
        }

    def score(self, query_tokens: list[str], candidates: list[int]) -> list[tuple[int, float]]:
        """Score each candidate document index against the query. Higher is more relevant."""
        terms = [t for t in dict.fromkeys(query_tokens) if t in self._idf]
        avg = self._avg or 1.0
        results = []
        for i in candidates:
            tf, doc_len = self._tf[i], self._len[i]
            total = 0.0
            for term in terms:
                freq = tf.get(term, 0)
                if freq:
                    norm = freq + self.k1 * (1 - self.b + self.b * doc_len / avg)
                    total += self._idf[term] * freq * (self.k1 + 1) / norm
            results.append((i, total))
        return results
