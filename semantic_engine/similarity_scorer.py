import math


def cosine_similarity(vec_a, vec_b):
    """Cosine similarity between two sparse {term: weight} vectors."""
    if not vec_a or not vec_b:
        return 0.0
    common_terms = set(vec_a) & set(vec_b)
    dot = sum(vec_a[t] * vec_b[t] for t in common_terms)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def text_similarity(vectorizer, text_a, text_b):
    """Convenience wrapper: vectorize two raw texts with a fitted vectorizer, then score."""
    return cosine_similarity(vectorizer.transform(text_a), vectorizer.transform(text_b))