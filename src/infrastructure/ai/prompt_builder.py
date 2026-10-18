import re

from application.dto.insight_dto import InsightContext

_HTML_TAG = re.compile(r"<[^>]+>")


class PromptBuilder:
    def __init__(self, max_chars: int = 4000):
        self._max_chars = max_chars

    def build(self, context: InsightContext) -> str:
        is_episode = context.target_type == "episode"
        summary = _HTML_TAG.sub(" ", context.summary).strip()
        summary_label = "Episode summary" if is_episode else "Summary"
        lines = [
            f"Genres: {', '.join(context.genres) or 'unknown'}",
            f"{summary_label}: {summary}",
        ]
        if context.series_summary:
            series_summary = _HTML_TAG.sub(" ", context.series_summary).strip()
            label = "Series summary (background context only)" if is_episode else "Series summary"
            lines.append(f"{label}: {series_summary}")
        if context.recent_comments:
            comments_block = "\n".join(f"- {comment}" for comment in context.recent_comments)
            lines.append(f"Recent viewer comments:\n{comments_block}")
        if is_episode:
            lines.append(
                "Write a short, insightful one-paragraph take on this specific episode for a "
                "viewer. Focus on what makes this episode distinct, drawing on its summary, the "
                "genres, and the viewer comments; use the series summary only as background and "
                "do not merely describe the series as a whole."
            )
        else:
            lines.append("Write a short, insightful one-paragraph take on this title for a viewer.")
        return "\n".join(lines)[: self._max_chars]
