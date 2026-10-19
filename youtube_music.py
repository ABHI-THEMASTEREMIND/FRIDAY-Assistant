"""Find a playable YouTube video for FRIDAY's music command."""

from __future__ import annotations


class YouTubePlaybackUnavailable(RuntimeError):
    """Raised when the YouTube search helper cannot return a video."""


def find_first_video(query: str) -> tuple[str, str]:
    """Return a likely official music video ID and title for a spoken request."""
    try:
        from yt_dlp import YoutubeDL
    except ImportError as error:
        raise YouTubePlaybackUnavailable("The YouTube music helper is not installed.") from error

    options = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "noplaylist": True,
    }
    try:
        with YoutubeDL(options) as downloader:
            result = downloader.extract_info(
                f"ytsearch1:{query} official audio", download=False
            )
        entries = result.get("entries", [])
        if not entries or not entries[0].get("id"):
            raise YouTubePlaybackUnavailable("No matching YouTube video was found.")
        video = entries[0]
        return video["id"], video.get("title", query)
    except Exception as error:
        if isinstance(error, YouTubePlaybackUnavailable):
            raise
        raise YouTubePlaybackUnavailable(str(error)) from error
