import json, os

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
SESSION_PATH = os.path.join(APP_DIR, "magyar.session")
POSTED_PATH = os.path.join(APP_DIR, "posted_ids.json")

DEFAULT_CONFIG = {
    "tg": {"api_id": "", "api_hash": "", "phone": ""},
    "reddit": {
        "client_id": "", "client_secret": "", "username": "",
        "password": "", "user_agent": "magyar-reddit-bot/1.0"
    },
    "channel": "robert_magyar",
    "filter_text": "ЙОБЛИК,Йобла тижня",
    "subreddit": "UkraineWarVideoReport",
    "download_dir": os.path.join(APP_DIR, "downloads"),
    "title_template": "{caption}",
    "auto_interval_min": 30,
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                c = json.load(f)
            # merge defaults
            for k, v in DEFAULT_CONFIG.items():
                if k not in c:
                    c[k] = v
                elif isinstance(v, dict):
                    for kk, vv in v.items():
                        c[k].setdefault(kk, vv)
            # migrate old single filter
            if c.get("filter_text", "").strip() == "ЙОБЛИК":
                c["filter_text"] = "ЙОБЛИК,Йобла тижня"
            return c
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_CONFIG))

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def load_posted():
    if os.path.exists(POSTED_PATH):
        try:
            with open(POSTED_PATH, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_posted(s):
    with open(POSTED_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(s), f)
