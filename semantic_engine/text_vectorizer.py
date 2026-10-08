import re
import math
from collections import Counter

TOKEN_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z+\.#]*")


def tokenize(text):
    if not text:
        return []
    return [t.lower() for t in TOKEN_PATTERN.findall(text)]


class TfidfVectorizer:
    """A from-scratch TF-IDF vector space model (stdlib only — no numpy/sklearn).
    fit() learns term weights from a corpus; transform() turns any text into a
    sparse {term: weight} vector that can be compared with cosine similarity."""

    def __init__(self):
        self.idf = {}

    def fit(self, documents):
        doc_count = len(documents)
        doc_freq = Counter()
        for doc in documents:
            for token in set(tokenize(doc)):
                doc_freq[token] += 1
        # smoothed idf, same formula scikit-learn's TfidfVectorizer uses by default
        self.idf = {
            term: math.log((1 + doc_count) / (1 + freq)) + 1
            for term, freq in doc_freq.items()
        }
        return self

    def transform(self, text):
        tokens = tokenize(text)
        if not tokens:
            return {}
        term_counts = Counter(tokens)
        max_count = max(term_counts.values())
        vector = {}
        for term, count in term_counts.items():
            if term not in self.idf:
                continue  # out-of-vocabulary term, not in the fitted corpus — ignored
            tf = count / max_count
            vector[term] = tf * self.idf[term]
        return vector