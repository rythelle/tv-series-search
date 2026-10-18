import re
from collections import Counter

_HTML_TAG = re.compile(r"<[^>]+>")
# Letters only (Unicode), 4+ long — keeps accented Portuguese words like "reviravolta" intact.
_WORD = re.compile(r"[^\W\d_]{4,}", re.UNICODE)
_STOPWORDS = {
    # English
    "this", "that", "with", "from", "they", "their", "have", "been",
    "into", "when", "while", "about", "after", "before", "which", "where",
    "just", "some", "them", "then", "than", "such", "very", "much", "more",
    "show", "shows", "series", "season", "episode", "episodes", "watch",
    "watching", "really", "there", "here", "thing", "things", "what",
    "word", "words", "stuff", "part", "parts", "kind", "lot", "lots",
    # Portuguese
    "esse", "essa", "este", "esta", "isso", "aqui", "tudo", "nada", "ainda",
    "porque", "quando", "também", "tambem", "mais", "menos", "muito", "muita",
    "como", "pelo", "pela", "pelos", "pelas", "para", "sobre", "entre", "cada",
    "série", "serie", "episódio", "episodio", "temporada", "temporadas",
    "assistir", "vendo", "mesmo", "mesma", "foram", "seria", "está", "estava",
    "sendo", "fica", "ficou", "coisa", "coisas", "nossa", "gente",
}
_POSITIVE_WORDS = {
    # English
    "love", "loved", "amazing", "great", "excellent", "brilliant", "best",
    "awesome", "fantastic", "wonderful", "perfect", "masterpiece", "favorite",
    # Portuguese
    "amei", "amo", "adorei", "adoro", "incrível", "incrivel", "ótimo", "otimo",
    "excelente", "maravilhoso", "maravilhosa", "perfeito", "perfeita", "melhor",
    "sensacional", "espetacular", "genial", "brilhante", "emocionante",
    "favorito", "favorita", "recomendo", "lindo", "linda", "impecável", "impecavel",
}
_NEGATIVE_WORDS = {
    # English
    "hate", "hated", "terrible", "awful", "boring", "worst", "bad",
    "disappointing", "disappointment", "weak", "dull", "mediocre",
    # Portuguese
    "odiei", "odeio", "terrível", "terrivel", "horrível", "horrivel",
    "péssimo", "pessimo", "ruim", "chato", "chata", "entediante", "tedioso",
    "decepção", "decepcao", "decepcionante", "pior", "fraco", "fraca", "lixo",
}


def _strip_html(text: str) -> str:
    return _HTML_TAG.sub(" ", text)


def _extract_keywords(summary: str, limit: int = 3) -> list[str]:
    plain = _strip_html(summary).lower()
    seen: list[str] = []
    for word in _WORD.findall(plain):
        if word in _STOPWORDS or word in seen:
            continue
        seen.append(word)
        if len(seen) == limit:
            break
    return seen


def _comment_themes(comments: list[str], limit: int = 2, exclude: set[str] = frozenset()) -> list[str]:
    counts: Counter[str] = Counter()
    for comment in comments:
        plain = _strip_html(comment).lower()
        for word in dict.fromkeys(_WORD.findall(plain)):
            if word in _STOPWORDS or word in _POSITIVE_WORDS or word in _NEGATIVE_WORDS or word in exclude:
                continue
            counts[word] += 1
    return [word for word, _ in counts.most_common(limit)]


def _dominant_tone(comments: list[str]) -> str | None:
    if not comments:
        return None
    positive = negative = 0
    for comment in comments:
        words = set(_WORD.findall(comment.lower()))
        positive += len(words & _POSITIVE_WORDS)
        negative += len(words & _NEGATIVE_WORDS)
    if positive == negative == 0:
        return None
    return "positive" if positive >= negative else "negative"


def compose_heuristic_insight(
    genres: list[str], summary: str, comments: list[str], subject_noun: str = "title"
) -> str:
    parts: list[str] = []
    if genres:
        parts.append(f"A {', '.join(genres)} {subject_noun}")
    else:
        parts.append(f"This {subject_noun}")

    keywords = _extract_keywords(summary)
    if keywords:
        parts.append(f"centered on {', '.join(keywords)}")

    themes = _comment_themes(comments, exclude=set(keywords))
    if themes:
        parts.append(f"viewers keep bringing up {', '.join(themes)}")

    tone = _dominant_tone(comments)
    if tone == "positive":
        parts.append("and the overall viewer reaction has been positive")
    elif tone == "negative":
        parts.append("and viewer reaction has leaned negative")

    return ", ".join(parts) + "."
