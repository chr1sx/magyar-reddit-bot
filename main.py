import os, sys, json, threading, queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (load_config, save_config, load_posted, save_posted,
                    SESSION_PATH, APP_DIR)
from tg_client import TelegramService
from reddit_client import RedditService, make_thumbnail
from text_utils import process

cfg = load_config()
posted_ids = load_posted()

tg = TelegramService(SESSION_PATH)
rd = RedditService()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Magyar -> Reddit Bot")
        self.geometry("1020x780")
        self.minsize(900, 600)

        self.log_q = queue.Queue()
        self.posts = []          # list of dicts
        self.selected_post = None
        self.video_path = None
        self.thumb_path = None
        self.auto_thread = None
        self.auto_stop = threading.Event()

        self._build_ui()
        self._load_config_to_ui()
        self.after(200, self._drain_log)

    # ---------- UI ----------
    def _build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=6, pady=6)

        tab_tg = ttk.Frame(nb)
        tab_rd = ttk.Frame(nb)
        tab_bot = ttk.Frame(nb)
        tab_log = ttk.Frame(nb)
        nb.add(tab_tg, text="Telegram")
        nb.add(tab_rd, text="Reddit")
        nb.add(tab_bot, text="Bot")
        nb.add(tab_log, text="Log")

        self._build_tg_tab(tab_tg)
        self._build_rd_tab(tab_rd)
        self._build_bot_tab(tab_bot)
        self._build_log_tab(tab_log)

    def _build_tg_tab(self, f):
        lf = ttk.LabelFrame(f, text="Telegram credentials")
        lf.pack(fill="x", padx=8, pady=6)
        self.tg_api_id = self._entry_row(lf, "API ID", 0)
        self.tg_api_hash = self._entry_row(lf, "API Hash", 1)
        self.tg_phone = self._entry_row(lf, "Phone (+...)", 2)
        btns = ttk.Frame(lf); btns.grid(row=3, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Button(btns, text="Connect", command=self.on_tg_connect).pack(side="left", padx=2)
        ttk.Button(btns, text="Send code", command=self.on_tg_send_code).pack(side="left", padx=2)
        self.tg_code = tk.StringVar()
        ttk.Entry(btns, textvariable=self.tg_code, width=12).pack(side="left", padx=2)
        ttk.Button(btns, text="Sign in", command=self.on_tg_signin).pack(side="left", padx=2)
        self.tg_password = self._entry_row(lf, "2FA password (optional)", 4, show="*")
        self.tg_status = ttk.Label(lf, text="not connected")
        self.tg_status.grid(row=5, column=0, columnspan=2, sticky="w", pady=2)

        lf2 = ttk.LabelFrame(f, text="Telegram channel")
        lf2.pack(fill="x", padx=8, pady=6)
        self.channel = self._entry_row(lf2, "Channel username", 0)
        self.filter_text = self._entry_row(lf2, "Filter caption contains", 1)
        ttk.Label(lf2, text="Default: robert_magyar / ЙОБЛИК (also catches Три/Ду/Квадро-ЙОБЛИК variants)").grid(row=2, column=0, columnspan=2, sticky="w", padx=4)

        ttk.Button(f, text="Save config", command=self.save_cfg).pack(pady=6)

    def _build_rd_tab(self, f):
        lf = ttk.LabelFrame(f, text="Reddit credentials (script app)")
        lf.pack(fill="x", padx=8, pady=6)
        self.rd_client_id = self._entry_row(lf, "Client ID", 0)
        self.rd_client_secret = self._entry_row(lf, "Client Secret", 1, show="*")
        self.rd_username = self._entry_row(lf, "Username", 2)
        self.rd_password = self._entry_row(lf, "Password", 3, show="*")
        self.rd_user_agent = self._entry_row(lf, "User agent", 4)
        btns = ttk.Frame(lf); btns.grid(row=5, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Button(btns, text="Test Reddit login", command=self.on_rd_test).pack(side="left", padx=2)
        self.rd_status = ttk.Label(lf, text="not connected")
        self.rd_status.grid(row=6, column=0, columnspan=2, sticky="w", pady=2)

        lf2 = ttk.LabelFrame(f, text="Reddit target")
        lf2.pack(fill="x", padx=8, pady=6)
        self.subreddit = self._entry_row(lf2, "Subreddit", 0)
        self.download_dir = self._entry_row(lf2, "Download dir", 1)
        ttk.Button(lf2, text="Browse", command=self.browse_dir).grid(row=1, column=2, padx=2)
        self.title_template = self._entry_row(lf2, "Title template", 2)
        ttk.Label(lf2, text="Tokens: {caption} {date} {id}").grid(row=3, column=0, columnspan=3, sticky="w", padx=4)
        self.auto_interval = self._entry_row(lf2, "Auto interval (min)", 4)

        ttk.Button(f, text="Save config", command=self.save_cfg).pack(pady=6)

    def _entry_row(self, parent, label, row, show=None):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=2)
        var = tk.StringVar()
        e = ttk.Entry(parent, textvariable=var, width=52, show=show or "")
        e.grid(row=row, column=1, sticky="we", padx=4, pady=2)
        parent.columnconfigure(1, weight=1)
        return var

    def _build_bot_tab(self, f):
        top = ttk.Frame(f); top.pack(fill="x", padx=6, pady=4)
        self.rd_status_main = ttk.Label(top, text="Reddit: not tested")
        self.rd_status_main.pack(side="right", padx=6)
        ttk.Button(top, text="Test Reddit", command=self.on_rd_test_main).pack(side="right", padx=2)
        ttk.Label(top, text="Fetch limit:").pack(side="left")
        self.fetch_limit = tk.StringVar(value="20")
        ttk.Entry(top, textvariable=self.fetch_limit, width=6).pack(side="left", padx=4)
        ttk.Button(top, text="Fetch posts", command=self.on_fetch).pack(side="left", padx=4)
        ttk.Button(top, text="Download selected", command=self.on_download).pack(side="left", padx=4)
        ttk.Button(top, text="Post to Reddit", command=self.on_post).pack(side="left", padx=4)

        auto = ttk.Frame(f); auto.pack(fill="x", padx=6, pady=2)
        ttk.Button(auto, text="Start auto", command=self.start_auto).pack(side="left", padx=2)
        ttk.Button(auto, text="Stop auto", command=self.stop_auto).pack(side="left", padx=2)
        self.auto_status = ttk.Label(auto, text="auto: off")
        self.auto_status.pack(side="left", padx=6)

        paned = ttk.PanedWindow(f, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=6, pady=4)

        left = ttk.Frame(paned)
        self.tree = ttk.Treeview(left, columns=("id", "date", "caption"), show="headings", height=18)
        self.tree.heading("id", text="ID")
        self.tree.heading("date", text="Date")
        self.tree.heading("caption", text="Caption")
        self.tree.column("id", width=60)
        self.tree.column("date", width=150)
        self.tree.column("caption", width=360)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select_post)
        paned.add(left, weight=1)

        right = ttk.Frame(paned)
        ttk.Label(right, text="Caption (Telegram):").pack(anchor="w")
        self.caption_box = tk.Text(right, height=5, wrap="word")
        self.caption_box.pack(fill="x", pady=2)
        ttk.Label(right, text="Translated description:").pack(anchor="w")
        self.desc_box = tk.Text(right, height=4, wrap="word")
        self.desc_box.pack(fill="x", pady=2)
        ttk.Label(right, text="Title for Reddit:").pack(anchor="w")
        self.title_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.title_var).pack(fill="x", pady=2)
        ttk.Label(right, text="Video file:").pack(anchor="w")
        self.video_label = ttk.Label(right, text="(none)")
        self.video_label.pack(anchor="w", pady=2)
        ttk.Label(right, text="Thumbnail:").pack(anchor="w")
        self.thumb_label = ttk.Label(right, text="(none)")
        self.thumb_label.pack(anchor="w", pady=2)
        paned.add(right, weight=1)

    def _build_log_tab(self, f):
        self.log_text = tk.Text(f, wrap="word", state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)

    # ---------- helpers ----------
    def log(self, msg):
        self.log_q.put(msg)

    def _drain_log(self):
        try:
            while True:
                msg = self.log_q.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(200, self._drain_log)

    def run_in_thread(self, fn, on_done=None, on_error=None):
        def worker():
            try:
                res = fn()
                if on_done:
                    self.after(0, lambda r=res: on_done(r))
            except Exception as e:
                self.log("ERROR: %s" % e)
                if on_error:
                    self.after(0, lambda e=e: on_error(e))
        threading.Thread(target=worker, daemon=True).start()

    # ---------- config load/save ----------
    def _load_config_to_ui(self):
        c = cfg
        self.tg_api_id.set(c["tg"].get("api_id", ""))
        self.tg_api_hash.set(c["tg"].get("api_hash", ""))
        self.tg_phone.set(c["tg"].get("phone", ""))
        self.rd_client_id.set(c["reddit"].get("client_id", ""))
        self.rd_client_secret.set(c["reddit"].get("client_secret", ""))
        self.rd_username.set(c["reddit"].get("username", ""))
        self.rd_password.set(c["reddit"].get("password", ""))
        self.rd_user_agent.set(c["reddit"].get("user_agent", ""))
        self.channel.set(c.get("channel", "robert_magyar"))
        self.filter_text.set(c.get("filter_text", "ЙОБЛИК"))
        self.subreddit.set(c.get("subreddit", "UkraineWarVideoReport"))
        self.download_dir.set(c.get("download_dir", ""))
        self.title_template.set(c.get("title_template", "{caption}"))
        self.auto_interval.set(str(c.get("auto_interval_min", 60)))

    def save_cfg(self):
        global cfg
        cfg["tg"]["api_id"] = self.tg_api_id.get().strip()
        cfg["tg"]["api_hash"] = self.tg_api_hash.get().strip()
        cfg["tg"]["phone"] = self.tg_phone.get().strip()
        cfg["reddit"]["client_id"] = self.rd_client_id.get().strip()
        cfg["reddit"]["client_secret"] = self.rd_client_secret.get().strip()
        cfg["reddit"]["username"] = self.rd_username.get().strip()
        cfg["reddit"]["password"] = self.rd_password.get().strip()
        cfg["reddit"]["user_agent"] = self.rd_user_agent.get().strip()
        cfg["channel"] = self.channel.get().strip()
        cfg["filter_text"] = self.filter_text.get().strip()
        cfg["subreddit"] = self.subreddit.get().strip()
        cfg["download_dir"] = self.download_dir.get().strip()
        cfg["title_template"] = self.title_template.get().strip()
        try:
            cfg["auto_interval_min"] = int(self.auto_interval.get().strip())
        except Exception:
            cfg["auto_interval_min"] = 60
        save_config(cfg)
        self.log("Config saved.")

    def browse_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.download_dir.set(d)

    def _fmt_date(self, iso):
        try:
            d = (iso or "")[:10]
            y, m, day = d.split("-")
            return "%s.%s.%s" % (day, m, y)
        except Exception:
            return (iso or "")[:10]

    # ---------- Telegram actions ----------
    def on_tg_connect(self):
        self.save_cfg()
        def fn():
            return tg.call(tg.connect(cfg["tg"]["api_id"], cfg["tg"]["api_hash"]))
        def done(res):
            self.tg_status.config(text=("authorized" if res else "connected, need sign-in"))
            self.log("Telegram connect: %s" % res)
        self.run_in_thread(fn, done)

    def on_tg_send_code(self):
        self.save_cfg()
        phone = cfg["tg"]["phone"]
        def fn():
            return tg.call(tg.send_code(phone))
        def done(_):
            self.log("Code sent to %s" % phone)
        self.run_in_thread(fn, done)

    def on_tg_signin(self):
        code = self.tg_code.get().strip()
        pw = self.tg_password.get().strip() or None
        def fn():
            return tg.call(tg.sign_in(code, pw))
        def done(res):
            self.tg_status.config(text=("authorized" if res else "not authorized"))
            self.log("Sign in: %s" % res)
        self.run_in_thread(fn, done)

    # ---------- Reddit actions ----------
    def on_rd_test(self):
        self.save_cfg()
        c = cfg["reddit"]
        def fn():
            return rd.connect(c["client_id"], c["client_secret"], c["username"],
                              c["password"], c["user_agent"])
        def done(res):
            self.rd_status.config(text="logged in as %s" % res)
            self.rd_status_main.config(text="Reddit: %s" % res)
            self.log("Reddit OK: %s" % res)
        def err(e):
            self.rd_status.config(text="error")
            self.rd_status_main.config(text="Reddit: error")
        self.run_in_thread(fn, done, err)

    def on_rd_test_main(self):
        self.on_rd_test()

    # ---------- Fetch ----------
    def on_fetch(self):
        self.save_cfg()
        channel = cfg["channel"]
        flt = cfg["filter_text"]
        try:
            limit = int(self.fetch_limit.get().strip())
        except Exception:
            limit = 20
        def fn():
            return tg.call(tg.fetch_posts(channel, limit, flt))
        def done(res):
            self.posts = res
            self.tree.delete(*self.tree.get_children())
            for p in res:
                cap = p["caption"].replace("\n", " ")
                self.tree.insert("", "end", iid=str(p["id"]), values=(p["id"], p["date"][:16], cap[:80]))
            self.log("Fetched %d posts" % len(res))
        self.run_in_thread(fn, done)

    def on_select_post(self, _):
        sel = self.tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        p = next((x for x in self.posts if x["id"] == pid), None)
        if not p:
            return
        self.selected_post = p
        self.caption_box.delete("1.0", "end")
        self.caption_box.insert("1.0", p["caption"])
        pub_date = self._fmt_date(p["date"])
        res = process(p["caption"], pub_date)
        desc = res["description"] if res["description"] else p["caption"]
        self.desc_box.delete("1.0", "end")
        self.desc_box.insert("1.0", desc)
        title = res["title"]
        if not title:
            title = " ".join(p["caption"].replace("\n", " ").split())
        title = " ".join(title.split())
        if len(title) > 300:
            title = title[:297] + "..."
        self.title_var.set(title)
        self.video_path = None
        self.thumb_path = None
        self.video_label.config(text="(not downloaded)")
        self.thumb_label.config(text="(none)")

    # ---------- Download ----------
    def on_download(self):
        if not self.selected_post:
            messagebox.showinfo("Info", "Select a post first")
            return
        self.save_cfg()
        channel = cfg["channel"]
        pid = self.selected_post["id"]
        dest = cfg["download_dir"] or os.path.join(APP_DIR, "downloads")
        os.makedirs(dest, exist_ok=True)
        def fn():
            return tg.call(tg.download(channel, pid, dest))
        def done(path):
            self.video_path = path
            self.video_label.config(text=path)
            self.log("Downloaded: %s" % path)
            # thumbnail
            try:
                base = os.path.splitext(path)[0]
                tp = base + "_thumb.jpg"
                make_thumbnail(path, tp)
                self.thumb_path = tp
                self.thumb_label.config(text=tp)
            except Exception as e:
                self.log("Thumbnail failed: %s" % e)
        self.run_in_thread(fn, done)

    # ---------- Post ----------
    def on_post(self):
        if not self.video_path or not os.path.exists(self.video_path):
            messagebox.showinfo("Info", "Download video first")
            return
        title = self.title_var.get().strip()
        if not title:
            messagebox.showinfo("Info", "Title required")
            return
        self.save_cfg()
        subreddit = cfg["subreddit"]
        vpath = self.video_path
        tpath = self.thumb_path
        def fn():
            return rd.submit_video(subreddit, title, vpath, tpath)
        def done(res):
            rid, url = res
            self.log("Posted: %s %s" % (rid, url))
            if self.selected_post:
                posted_ids.add(str(self.selected_post["id"]))
                save_posted(posted_ids)
            messagebox.showinfo("Posted", url)
        def err(e):
            messagebox.showerror("Error", str(e))
        self.run_in_thread(fn, done, err)

    # ---------- Auto ----------
    def start_auto(self):
        if self.auto_thread and self.auto_thread.is_alive():
            return
        self.auto_stop.clear()
        self.auto_thread = threading.Thread(target=self._auto_loop, daemon=True)
        self.auto_thread.start()
        self.auto_status.config(text="auto: running")
        self.log("Auto started")

    def stop_auto(self):
        self.auto_stop.set()
        self.auto_status.config(text="auto: stopping")
        self.log("Auto stop requested")

    def _auto_loop(self):
        while not self.auto_stop.is_set():
            try:
                self._auto_once()
            except Exception as e:
                self.log("Auto error: %s" % e)
            # wait interval
            mins = cfg.get("auto_interval_min", 60)
            for _ in range(mins * 60):
                if self.auto_stop.is_set():
                    break
                threading.Event().wait(1)
        self.after(0, lambda: self.auto_status.config(text="auto: off"))

    def _auto_once(self):
        self.save_cfg()
        channel = cfg["channel"]
        flt = cfg["filter_text"]
        dest = cfg["download_dir"] or os.path.join(APP_DIR, "downloads")
        os.makedirs(dest, exist_ok=True)
        posts = tg.call(tg.fetch_posts(channel, 10, flt))
        new_posts = [p for p in posts if str(p["id"]) not in posted_ids]
        if not new_posts:
            self.log("Auto: no new posts")
            return
        for p in new_posts:
            if self.auto_stop.is_set():
                break
            self.log("Auto processing post %s" % p["id"])
            path = tg.call(tg.download(channel, p["id"], dest))
            # thumbnail
            tp = None
            try:
                base = os.path.splitext(path)[0]
                tp = base + "_thumb.jpg"
                make_thumbnail(path, tp)
            except Exception as e:
                self.log("thumb fail: %s" % e)
                tp = None
            pub_date = self._fmt_date(p["date"])
            res = process(p["caption"], pub_date)
            title = res["title"]
            if not title:
                title = " ".join(p["caption"].replace("\n", " ").split())
            title = " ".join(title.split())
            if len(title) > 300:
                title = title[:297] + "..."
            rid, url = rd.submit_video(cfg["subreddit"], title, path, tp)
            posted_ids.add(str(p["id"]))
            save_posted(posted_ids)
            self.log("Auto posted %s -> %s" % (p["id"], url))

if __name__ == "__main__":
    app = App()
    app.mainloop()
