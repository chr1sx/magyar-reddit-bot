import os, subprocess

class RedditService:
    def __init__(self):
        self.reddit = None

    def connect(self, client_id, client_secret, username, password, user_agent):
        import praw
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=user_agent,
        )
        me = self.reddit.user.me()
        return str(me)

    def submit_video(self, subreddit, title, video_path, thumbnail_path=None):
        sub = self.reddit.subreddit(subreddit)
        submission = sub.submit_video(
            title=title,
            video_path=video_path,
            thumbnail_path=thumbnail_path,
        )
        return submission.id, ("https://www.reddit.com" + submission.permalink)

def make_thumbnail(video_path, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True) if os.path.dirname(out_path) else None
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-ss", "00:00:01", "-vframes", "1", out_path],
        check=True, capture_output=True,
    )
    return out_path
