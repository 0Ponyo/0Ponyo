import html
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime

API_KEY = os.environ["YOUTUBE_API_KEY"]
CHANNEL_ID = "UCLfy2P0XPuzeEKi0J4dWKxw"

README_PATH = "README.md"

START_MARKER = "<!-- BEGIN YOUTUBE-CARDS -->"
END_MARKER = "<!-- END YOUTUBE-CARDS -->"


def youtube_api(endpoint, params):
    params["key"] = API_KEY

    url = (
        f"https://www.googleapis.com/youtube/v3/{endpoint}?"
        + urllib.parse.urlencode(params)
    )

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "GitHub-Actions-YouTube-Updater"},
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def format_date(date_string):
    date = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
    return date.strftime("%b %d, %Y").replace(" 0", " ")


def get_videos():
    # Find the channel's uploads playlist.
    channel_data = youtube_api(
        "channels",
        {
            "part": "contentDetails",
            "id": CHANNEL_ID,
        },
    )

    items = channel_data.get("items", [])

    if not items:
        return []

    uploads_playlist = (
        items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    )

    # Get the six newest uploads.
    playlist_data = youtube_api(
        "playlistItems",
        {
            "part": "snippet,contentDetails",
            "playlistId": uploads_playlist,
            "maxResults": 6,
        },
    )

    playlist_items = playlist_data.get("items", [])

    if not playlist_items:
        return []

    video_ids = [
        item["contentDetails"]["videoId"]
        for item in playlist_items
    ]

    # Get titles, dates, views and likes.
    video_data = youtube_api(
        "videos",
        {
            "part": "snippet,statistics",
            "id": ",".join(video_ids),
        },
    )

    videos_by_id = {
        video["id"]: video
        for video in video_data.get("items", [])
    }

    videos = []

    for video_id in video_ids:
        video = videos_by_id.get(video_id)

        if not video:
            continue

        snippet = video["snippet"]
        statistics = video.get("statistics", {})

        videos.append(
            {
                "id": video_id,
                "title": snippet["title"],
                "published": format_date(snippet["publishedAt"]),
                "views": int(statistics.get("viewCount", 0)),
                "likes": statistics.get("likeCount"),
            }
        )

    return videos


def generate_cards(videos):
    if not videos:
        return '<p align="center"><i>No videos yet — check back soon!</i></p>'

    cells = []

    for video in videos:
        video_id = video["id"]
        title = html.escape(video["title"])
        published = html.escape(video["published"])

        views = f"{video['views']:,}"

        if video["likes"] is not None:
            likes = f"{int(video['likes']):,}"
            likes_text = f"👍 {likes} likes"
        else:
            likes_text = "👍 Likes hidden"

        thumbnail = (
            f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        )

        video_url = (
            f"https://www.youtube.com/watch?v={video_id}"
        )

        cell = f"""
<td width="50%" valign="top">
  <a href="{video_url}">
    <img src="{thumbnail}" width="100%" alt="{title}">
  </a>
  <br><br>
  <strong>{title}</strong>
  <br>
  👁️ {views} views · {likes_text}
  <br>
  📅 {published}
</td>
"""

        cells.append(cell)

    rows = []

    for i in range(0, len(cells), 2):
        row = cells[i:i + 2]

        if len(row) == 1:
            row.append('<td width="50%"></td>')

        rows.append(
            "<tr>\n"
            + "\n".join(row)
            + "\n</tr>"
        )

    return (
        "<table>\n"
        + "\n".join(rows)
        + "\n</table>"
    )


def update_readme(content):
    with open(README_PATH, "r", encoding="utf-8") as file:
        readme = file.read()

    start = readme.find(START_MARKER)
    end = readme.find(END_MARKER)

    if start == -1 or end == -1:
        raise RuntimeError(
            "Could not find the YouTube section markers in README.md"
        )

    end += len(END_MARKER)

    replacement = (
        START_MARKER
        + "\n"
        + content
        + "\n"
        + END_MARKER
    )

    updated = readme[:start] + replacement + readme[end:]

    with open(README_PATH, "w", encoding="utf-8") as file:
        file.write(updated)


def main():
    videos = get_videos()
    cards = generate_cards(videos)
    update_readme(cards)

    print(f"Updated README with {len(videos)} YouTube video(s).")


if __name__ == "__main__":
    main()
