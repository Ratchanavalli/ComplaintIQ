"""
Sentiment Analyzer
==================
Rule-based lexicon sentiment analysis — no NLTK downloads required.

Uses a curated word list of positive and negative words to calculate
a polarity score, then classifies as positive / neutral / negative.

Score ranges
------------
 > +0.05  → positive
 -0.05 to +0.05 → neutral
 < -0.05  → negative
"""

import re

# ── Sentiment lexicons ────────────────────────────────────────────────────────

POSITIVE_WORDS = {
    "good", "great", "excellent", "amazing", "wonderful", "fantastic",
    "outstanding", "superb", "brilliant", "perfect", "happy", "pleased",
    "satisfied", "impressed", "resolved", "helpful", "quick", "fast",
    "efficient", "friendly", "professional", "smooth", "easy", "love",
    "best", "awesome", "thank", "thanks", "appreciate", "grateful",
    "delighted", "glad", "nice", "fine", "okay", "ok", "decent",
    "acceptable", "reasonable", "fair", "prompt", "responsive",
}

NEGATIVE_WORDS = {
    "bad", "terrible", "horrible", "awful", "worst", "poor", "unacceptable",
    "disappointed", "disappointing", "frustrating", "frustrated", "angry",
    "furious", "outraged", "annoyed", "upset", "disgusted", "disgusting",
    "useless", "broken", "defective", "damaged", "wrong", "missing",
    "failed", "failure", "problem", "issue", "complaint", "complain",
    "never", "not", "no", "never", "cannot", "cant", "wont", "dont",
    "didnt", "hasnt", "havent", "refused", "ignored", "rude", "unprofessional",
    "late", "delayed", "delay", "lost", "stolen", "fraud", "scam",
    "lie", "lied", "cheat", "cheated", "theft", "terrible", "dreadful",
    "atrocious", "appalling", "shocking", "disgraceful", "pathetic",
    "ridiculous", "unacceptable", "inexcusable", "incompetent",
    "waiting", "waited", "hours", "weeks", "still", "yet", "nothing",
    "nobody", "never", "impossible", "lawsuit", "lawyer", "legal",
    "sue", "escalate", "hazard", "dangerous", "unsafe", "injured",
    "hurt", "serious", "urgent", "immediately", "demand",
}

# Intensifiers boost the score of the next word
INTENSIFIERS = {
    "very", "extremely", "absolutely", "completely", "totally",
    "utterly", "highly", "really", "so", "quite", "deeply",
}

# Negators flip the sign of the next sentiment word
NEGATORS = {
    "not", "never", "no", "neither", "nor", "barely", "hardly",
    "scarcely", "without", "cant", "cannot", "wont", "dont",
    "didnt", "hasnt", "havent", "isnt", "wasnt", "arent", "werent",
}

POSITIVE_THRESHOLD = 0.05
NEGATIVE_THRESHOLD = -0.05


def _tokenize(text: str) -> list[str]:
    """Simple word tokenizer — no NLTK needed."""
    text = text.lower()
    text = re.sub(r"[^\w\s']", " ", text)
    text = re.sub(r"n't", " not", text)
    text = re.sub(r"'s", " ", text)
    return [w for w in text.split() if w]


def analyze_sentiment(text: str) -> dict:
    """
    Analyse sentiment of a complaint without any external downloads.

    Returns
    -------
    {
        "sentiment":    "positive" | "neutral" | "negative",
        "polarity":     float,   # -1.0 to +1.0
        "subjectivity": float,   # 0.0 to 1.0 (ratio of opinion words)
    }
    """
    tokens = _tokenize(text)
    if not tokens:
        return {"sentiment": "neutral", "polarity": 0.0, "subjectivity": 0.0}

    pos_count = 0.0
    neg_count = 0.0
    opinion_words = 0

    i = 0
    while i < len(tokens):
        word = tokens[i]
        multiplier = 1.0

        # Look back for intensifier
        if i > 0 and tokens[i - 1] in INTENSIFIERS:
            multiplier = 1.5

        # Look back for negator (within 3 words)
        negated = False
        for j in range(max(0, i - 3), i):
            if tokens[j] in NEGATORS:
                negated = True
                break

        if word in POSITIVE_WORDS:
            opinion_words += 1
            if negated:
                neg_count += multiplier
            else:
                pos_count += multiplier

        elif word in NEGATIVE_WORDS:
            opinion_words += 1
            if negated:
                pos_count += multiplier * 0.5   # double negative = mild positive
            else:
                neg_count += multiplier

        i += 1

    total = pos_count + neg_count
    if total == 0:
        polarity = 0.0
        subjectivity = 0.0
    else:
        # Normalise to -1 → +1
        polarity = round((pos_count - neg_count) / (total + 1e-9), 4)
        subjectivity = round(min(opinion_words / len(tokens), 1.0), 4)

    if polarity >= POSITIVE_THRESHOLD:
        sentiment = "positive"
    elif polarity <= NEGATIVE_THRESHOLD:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return {
        "sentiment": sentiment,
        "polarity": polarity,
        "subjectivity": subjectivity,
    }
