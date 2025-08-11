import os
import uvicorn
from fastapi import FastAPI, Request
from main import build_app

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "secret-path")
BASE_URL = os.getenv("BASE_URL")

app = FastAPI()
tg_app = build_app()

@app.on_event("startup")
async def on_startup():
    await tg_app.bot.set_webhook(url=f"{BASE_URL}/webhook/{WEBHOOK_SECRET}")
    await tg_app.initialize()
    await tg_app.start()

@app.post(f"/webhook/{{secret}}")
async def webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        return {"ok": False}
    data = await request.json()
    update = tg_app.update_queue._factory.dict_to_update(data)
    await tg_app.process_update(update)
    return {"ok": True}

@app.get("/health")
async def health():
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
