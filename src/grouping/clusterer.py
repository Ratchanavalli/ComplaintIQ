"""
Complaint Grouper / Clusterer
==============================
Uses TF-IDF vectorisation + K-Means clustering to group similar complaints.

The number of clusters is estimated automatically using the elbow method when
not supplied explicitly.
"""

import re
import string
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


# ── Text pre-processing ───────────────────────────────────────────────────────

_STOP_WORDS = {
    "i", "me", "my", "we", "our", "you", "your", "it", "its", "the", "a",
    "an", "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "should", "may",
    "might", "shall", "can", "to", "of", "in", "for", "on", "with", "at",
    "by", "from", "and", "or", "but", "if", "as", "this", "that", "these",
    "those", "not", "no", "just", "about", "after", "before", "when",
    "where", "who", "how", "what", "which", "there", "here", "so",
}


def _preprocess(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\d+", " ", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    tokens = [w for w in text.split() if w not in _STOP_WORDS and len(w) > 2]
    return " ".join(tokens)


# ── Optimal-k estimation (silhouette) ─────────────────────────────────────────

def _best_k(matrix, k_min: int = 2, k_max: int = 8) -> int:
    """Pick k that maximises the silhouette score."""
    n_samples = matrix.shape[0]
    k_max = min(k_max, n_samples - 1)
    if k_max < k_min:
        return k_min

    best_k, best_score = k_min, -1.0
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(matrix)
        try:
            score = silhouette_score(matrix, labels, sample_size=min(300, n_samples))
        except ValueError:
            continue
        if score > best_score:
            best_score, best_k = score, k
    return best_k


# ── Public API ────────────────────────────────────────────────────────────────

def cluster_complaints(
    complaint_texts: list[str],
    n_clusters: Optional[int] = None,
) -> dict:
    """
    Group complaints by semantic similarity.

    Parameters
    ----------
    complaint_texts : list of raw complaint strings
    n_clusters      : explicit cluster count; auto-detected when None

    Returns
    -------
    {
        "labels":    list[int],      # cluster id per complaint (same order)
        "n_clusters": int,
        "top_terms": dict[int, list[str]],  # top 5 TF-IDF terms per cluster
        "sizes":     dict[int, int],        # complaint count per cluster
    }
    """
    if len(complaint_texts) < 2:
        return {
            "labels": [0] * len(complaint_texts),
            "n_clusters": 1,
            "top_terms": {0: []},
            "sizes": {0: len(complaint_texts)},
        }

    processed = [_preprocess(t) for t in complaint_texts]

    vectorizer = TfidfVectorizer(max_features=500, ngram_range=(1, 2))
    tfidf_matrix = vectorizer.fit_transform(processed)

    k = n_clusters if n_clusters else _best_k(tfidf_matrix)

    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(tfidf_matrix).tolist()

    # Top terms per cluster (from centroid weights)
    feature_names = vectorizer.get_feature_names_out()
    top_terms: dict[int, list[str]] = {}
    for cluster_id in range(k):
        centroid = km.cluster_centers_[cluster_id]
        top_idx = np.argsort(centroid)[::-1][:5]
        top_terms[cluster_id] = [feature_names[i] for i in top_idx]

    sizes: dict[int, int] = {i: labels.count(i) for i in range(k)}

    return {
        "labels": labels,
        "n_clusters": k,
        "top_terms": top_terms,
        "sizes": sizes,
    }


def build_cluster_label(top_terms: list[str], category: str) -> str:
    """Create a human-readable cluster label from its top terms."""
    terms_str = ", ".join(top_terms[:3]) if top_terms else "general"
    return f"{category.replace('_', ' ').title()} – {terms_str}"
