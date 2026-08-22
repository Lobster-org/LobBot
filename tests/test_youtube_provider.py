from unittest.mock import MagicMock, patch

from app.modules.music.models.track import Track
from app.modules.music.providers.youtube import YouTubeProvider


def test_search_enables_youtube_javascript_runtime():
    youtube_dl = MagicMock()
    youtube_dl.return_value.__enter__.return_value.extract_info.return_value = {
        "entries": []
    }

    with patch(
        "app.modules.music.providers.youtube.yt_dlp.YoutubeDL",
        youtube_dl,
    ):
        YouTubeProvider()._search("test", 5)

    options = youtube_dl.call_args.args[0]
    assert options["js_runtimes"] == {"node": {}}


def test_download_enables_youtube_javascript_runtime(tmp_path):
    youtube_dl = MagicMock()
    track = Track(
        title="Test",
        url="https://www.youtube.com/watch?v=video-id",
        source="youtube",
        source_id="video-id",
    )
    output_path = str(tmp_path / "video-id.webm")

    with patch(
        "app.modules.music.providers.youtube.yt_dlp.YoutubeDL",
        youtube_dl,
    ):
        result = YouTubeProvider()._download(track, output_path)

    options = youtube_dl.call_args.args[0]
    assert options["js_runtimes"] == {"node": {}}
    assert options["format"] == "bestaudio/best"
    assert result == output_path
