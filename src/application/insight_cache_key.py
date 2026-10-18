import hashlib


def build_insight_cache_key(
    target_type: str, target_id: int, genres: list[str], summary: str,
    comment_count: int, max_comment_id: int, series_summary: str = "",
) -> str:
    raw = "|".join(
        [
            target_type,
            str(target_id),
            ",".join(sorted(genres)),
            summary,
            str(comment_count),
            str(max_comment_id),
            series_summary or "",
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
