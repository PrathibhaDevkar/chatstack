import os
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI
from pydantic import BaseModel
import httpx

DATABASE_URL = os.environ["DATABASE_URL"]
OLLAMA_URL = os.environ["OLLAMA_URL"]
MODEL = os.environ["MODEL"]


def get_conn():
    return psycopg.connect(DATABASE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the app starts: create the table if it doesn't exist
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """)
    yield


app = FastAPI(lifespan=lifespan)


class Message(BaseModel):
    role: str
    content: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/messages")
def add_message(msg: Message):
    with get_conn() as conn:
        row = conn.execute(
            "INSERT INTO messages (role, content) VALUES (%s, %s) RETURNING id",
            (msg.role, msg.content),
        ).fetchone()
    return {"id": row[0]}


@app.get("/messages")
def list_messages():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, role, content, created_at FROM messages ORDER BY id"
        ).fetchall()
    return [
        {"id": r[0], "role": r[1], "content": r[2], "created_at": r[3]}
        for r in rows
    ]

class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat(req: ChatRequest):
    # 1. Save the user's message and load the recent conversation
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (role, content) VALUES ('user', %s)",
            (req.message,),
        )
        rows = conn.execute(
            "SELECT role, content FROM messages ORDER BY id DESC LIMIT 10"
        ).fetchall()
    history = [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    # 2. Ask the LLM (it sees the last 10 messages, so it remembers context)
    resp = httpx.post(
        f"{OLLAMA_URL}/api/chat",
        json={"model": MODEL, "messages": history, "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    answer = resp.json()["message"]["content"]

    # 3. Save the answer
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (role, content) VALUES ('assistant', %s)",
            (answer,),
        )
    return {"answer": answer}