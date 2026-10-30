#!/usr/bin/env python3
"""Serve a page of student names from the Railway database."""

import os
import sys
from pathlib import Path

import psycopg
from flask import Flask, jsonify, send_from_directory

ROOT = Path(__file__).resolve().parent
app = Flask(__name__, static_folder="static")


def load_env(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"Missing {path.name}. Set DATABASE_URL there before starting.")
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not set.")
    if "sslmode=" in url:
        return url
    separator = "&" if "?" in url else "?"
    # The private Railway hostname does not use the public proxy's SSL.
    if ".railway.internal" in url:
        return f"{url}{separator}sslmode=disable"
    return f"{url}{separator}sslmode=require"


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/students")
def student_names():
    with psycopg.connect(database_url(), connect_timeout=20) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM students ORDER BY name")
            names = [row[0] for row in cur.fetchall()]
    return jsonify([{"name": name} for name in names])


if __name__ == "__main__":
    if Path(sys.prefix).resolve() == Path(sys.base_prefix).resolve():
        raise SystemExit("Run this with the project venv: ./venv/bin/python app.py")
    load_env(ROOT / ".env")
    app.run(host="127.0.0.1", port=8080)
