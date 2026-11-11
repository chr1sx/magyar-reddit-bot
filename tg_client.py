import asyncio, threading, os

class TelegramService:
    def __init__(self, session_path):
        self.session_path = session_path
        self.loop = None
        self.thread = None
        self.client = None
        self.authorized = False
        self.phone = None
        self._qr = None

    def _ensure_loop(self):
        if self.thread is not None and self.thread.is_alive():
            return
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def call(self, coro):
        self._ensure_loop()
        fut = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return fut.result()

    async def connect(self, api_id, api_hash):
        from telethon import TelegramClient
        self.client = TelegramClient(self.session_path, int(api_id), api_hash)
        await self.client.connect()
        self.authorized = await self.client.is_user_authorized()
        return self.authorized

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            self.client = None
            self.authorized = False

    async def send_code(self, phone):
        self.phone = phone
        await self.client.send_code_request(phone)

    async def sign_in(self, code, password=None):
        from telethon.errors import SessionPasswordNeededError
        try:
            await self.client.sign_in(self.phone, code)
        except SessionPasswordNeededError:
            if not password:
                raise
            await self.client.sign_in(password=password)
        self.authorized = await self.client.is_user_authorized()
        return self.authorized

    async def qr_start(self):
        self._qr = await self.client.qr_login()
        return self._qr.url

    async def qr_wait(self, password=None):
        from telethon.errors import SessionPasswordNeededError
        try:
            await self._qr.wait()
        except SessionPasswordNeededError:
            if not password:
                raise
            await self.client.sign_in(password=password)
        self.authorized = await self.client.is_user_authorized()
        return self.authorized

    async def fetch_posts(self, channel, limit, filter_text):
        entity = await self.client.get_entity(channel)
        msgs = await self.client.get_messages(entity, limit=limit)
        results = []
        for m in msgs:
            if not getattr(m, "media", None):
                continue
            is_video = bool(getattr(m, "video", None))
            if not is_video and getattr(m, "document", None):
                mt = getattr(m.document, "mime_type", "") or ""
                if "video" in mt:
                    is_video = True
            if not is_video:
                continue
            caption = m.message or ""
            if filter_text:
                kws = [k.strip().lower() for k in filter_text.split(",") if k.strip()]
                if kws and not any(k in caption.lower() for k in kws):
                    continue
            results.append({
                "id": m.id,
                "date": m.date.isoformat() if m.date else "",
                "caption": caption,
            })
        return results

    async def download(self, channel, msg_id, dest_dir):
        entity = await self.client.get_entity(channel)
        m = await self.client.get_messages(entity, ids=msg_id)
        os.makedirs(dest_dir, exist_ok=True)
        path = await m.download_media(file=dest_dir)
        return path
