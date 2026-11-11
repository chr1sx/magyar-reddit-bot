import re

MONTH_UA_TO_EN = {
    "січня": "January", "лютого": "February", "березня": "March",
    "квітня": "April", "травня": "May", "червня": "June",
    "липня": "July", "серпня": "August", "вересня": "September",
    "жовтня": "October", "листопада": "November", "грудня": "December",
}

_MONTH_ALT = "|".join(MONTH_UA_TO_EN.keys())

DAY_PAT = re.compile(
    r'Протягом\s*(\d{1,2})\s*(' + _MONTH_ALT + r').{0,15}?(\d[\d\s]{0,8})\s*☠',
    re.IGNORECASE | re.DOTALL,
)
RANGE_PAT = re.compile(
    r'Протягом\s*(\d{1,2})\s*-\s*(\d{1,2})\s*(' + _MONTH_ALT + r')\b.{0,15}?(\d[\d\s]{0,8})\s*☠',
    re.IGNORECASE | re.DOTALL,
)

WEEKLY_PAT = re.compile(
    r'Йобла\s+тижня,?\s*(\d+)\s*випуск',
    re.IGNORECASE,
)

def _num(s):
    return int("".join(s.split()))

def parse_daily(caption):
    info = {
        "day": None, "day_count": None,
        "range_start": None, "range_end": None, "range_total": None,
        "month_ua": None, "month": None,
    }
    dm = DAY_PAT.search(caption or "")
    if dm:
        info["day"] = int(dm.group(1))
        info["month_ua"] = dm.group(2).lower()
        info["month"] = MONTH_UA_TO_EN.get(info["month_ua"], info["month_ua"])
        try:
            info["day_count"] = _num(dm.group(3))
        except ValueError:
            info["day_count"] = None
    rm = RANGE_PAT.search(caption or "")
    if rm:
        info["range_start"] = int(rm.group(1))
        info["range_end"] = int(rm.group(2))
        if not info["month_ua"]:
            info["month_ua"] = rm.group(3).lower()
            info["month"] = MONTH_UA_TO_EN.get(info["month_ua"], info["month_ua"])
        try:
            info["range_total"] = _num(rm.group(4))
        except ValueError:
            info["range_total"] = None
    if info["month"] is None:
        info["month"] = "November"
    return info

def parse_weekly(caption):
    m = WEEKLY_PAT.search(caption or "")
    ep = int(m.group(1)) if m else None
    return {"episode": ep}

def classify(caption):
    c = caption or ""
    if WEEKLY_PAT.search(c):
        return "weekly"
    if "ЙОБЛИК" in c.upper() or "Йобла" in c:
        # daily if has Протягом with a number
        if re.search(r'Протягом', c, re.I):
            return "daily"
    return "other"

def build_daily_description(info):
    parts = []
    if info["day"] is not None and info["day_count"] is not None:
        parts.append("On {month} {day}: {count} ☠️🩸 Russian invaders eliminated.".format(
            month=info["month"], day=info["day"], count=f"{info['day_count']:,}"))
    if info["range_start"] is not None and info["range_end"] is not None and info["range_total"] is not None:
        parts.append("{month} {start}–{end}: {total} ☠️🩸 Russian invaders eliminated.".format(
            month=info["month"], start=info["range_start"], end=info["range_end"],
            total=f"{info['range_total']:,}"))
    return "\n".join(parts)

def build_daily_title(info, pub_date):
    if info["day"] is None or info["day_count"] is None:
        return None
    title = ("Elimination of russian invaders by operators of the Ukrainian 414th UAS Brigade "
             "\u201cMagyar\u2019s Birds.\u201d "
             "On {month} {day}, \u201cMagyar\u2019s Birds\u201d eliminated {day_count} occupiers".format(
                 month=info["month"], day=info["day"], day_count=info["day_count"]))
    if info["range_start"] is not None and info["range_end"] is not None and info["range_total"] is not None:
        title += (", bringing the total for {month} {start}\u2013{end} to {total:,}.".format(
            month=info["month"], start=info["range_start"], end=info["range_end"],
            total=info["range_total"]))
    else:
        title += "."
    title += " Published {date}".format(date=pub_date)
    return title

def build_weekly_title(info, pub_date):
    ep = info.get("episode")
    if ep is None:
        return None
    return ("The Ukrainian 414th UAS Brigade \u201cMagyar's Birds\u201d continues to eliminate "
            "large numbers of russian invaders. Selection of best hits, episode {ep}. Published {date}".format(
                ep=ep, date=pub_date))

def build_weekly_description(info, caption):
    return "Selection of best hits by pilots of the 414th UAS Brigade \u201cMagyar's Birds\u201d."

def process(caption, pub_date):
    kind = classify(caption)
    if kind == "weekly":
        info = parse_weekly(caption)
        title = build_weekly_title(info, pub_date)
        desc = build_weekly_description(info, caption)
        return {"type": kind, "info": info, "title": title, "description": desc}
    if kind == "daily":
        info = parse_daily(caption)
        title = build_daily_title(info, pub_date)
        desc = build_daily_description(info)
        return {"type": kind, "info": info, "title": title, "description": desc}
    return {"type": "other", "info": None, "title": None, "description": caption}

# backward compat
def parse_caption(caption):
    return parse_daily(caption)

def build_description(info):
    return build_daily_description(info)

def build_title(info, pub_date):
    return build_daily_title(info, pub_date)
