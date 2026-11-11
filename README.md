# Magyar -> Reddit Bot (GUI)

A small desktop (Tkinter) bot that watches the Telegram channel
`t.me/robert_magyar` for new daily videos (caption contains `ЙОБЛИК☠️ДНЯ`),
lets you edit the Reddit title, downloads the video, and posts it to
`r/UkraineWarVideoReport`.

## Setup

1. Install Python 3.11+ and ffmpeg on PATH.
2. `pip install -r requirements.txt`
3. Run `python main.py`

## Telegram credentials

Create an app at https://my.telegram.org -> "API development tools" to get
`api_id` and `api_hash`. Enter them in the Config tab, then Connect -> Send code
-> Sign in (handle 2FA password if enabled).

## Reddit credentials

Create a "script" app at https://www.reddit.com/prefs/apps and fill client id/secret,
username, password and a user agent.

## Usage

- Config tab: fill credentials, channel (default `robert_magyar`), filter
  (`ЙОБЛИК`), subreddit, download dir, title template. Save.
- Bot tab: "Fetch posts" -> select a post -> edit title -> "Download selected"
  -> "Post to Reddit".
- Auto mode checks for new posts every N minutes (default 30), downloads and
  posts them. The Ukrainian caption is parsed to build an English translated
  description and a Reddit title in the agreed format, with the Telegram
  publication date. Already-posted IDs are stored in `posted_ids.json`.

## Notes

- Large Telegram videos cannot be fetched via the public web preview, so the
  Telethon (MTProto) API is used. The first run may take a moment to download.
- Reddit video processing happens server-side; the post URL is returned
  immediately but the video may take a minute to be playable.
- The Post4U project (https://github.com/ShadowSlayer03/Post4U-Schedule-Social-Media-Posts)
  can be used as an alternative scheduler backend; this bot posts directly via PRAW.

## Files

- `main.py` - Tkinter GUI
- `tg_client.py` - Telethon wrapper
- `reddit_client.py` - PRAW wrapper + ffmpeg thumbnail
- `config.py` - config persistence
