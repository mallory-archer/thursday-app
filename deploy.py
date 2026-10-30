#!/usr/bin/env python3
"""Apply schema.sql and load class_dataset.csv into DATABASE_URL."""

import csv
import os
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent
TABLES = (
    "students",
    "tools",
    "availability",
    "student_tools",
    "student_availability",
)


def load_env(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"Missing {path.name}. Set DATABASE_URL there before deploying.")
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise SystemExit("DATABASE_URL is not set.")
    if "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}sslmode=require"
    return url


def split_sql(script: str) -> list[str]:
    """Split a SQL script on semicolons, keeping quoted strings intact."""
    statements: list[str] = []
    buf: list[str] = []
    in_single = False
    in_comment = False
    i = 0
    length = len(script)
    while i < length:
        char = script[i]
        nxt = script[i + 1] if i + 1 < length else ""
        if in_comment:
            if char == "\n":
                in_comment = False
            i += 1
            continue
        if in_single:
            buf.append(char)
            if char == "'" and nxt == "'":
                buf.append(nxt)
                i += 2
                continue
            if char == "'":
                in_single = False
            i += 1
            continue
        if char == "-" and nxt == "-":
            in_comment = True
            i += 2
            continue
        if char == "'":
            in_single = True
            buf.append(char)
            i += 1
            continue
        if char == ";":
            statement = "".join(buf).strip()
            if statement:
                statements.append(statement)
            buf = []
            i += 1
            continue
        buf.append(char)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def split_list(value: str) -> list[str]:
    tokens: list[str] = []
    for part in value.split(";"):
        token = part.strip()
        if token and token not in tokens:
            tokens.append(token)
    return tokens


def require_tokens(netid: str, field: str, tokens: list[str], known: dict[str, int]) -> list[int]:
    missing = [token for token in tokens if token not in known]
    if missing:
        names = ", ".join(missing)
        raise SystemExit(f"{netid} lists unknown {field}: {names}")
    return [known[token] for token in tokens]


def load_dataset(cur: psycopg.Cursor) -> int:
    csv_path = ROOT / "class_dataset.csv"
    if not csv_path.is_file():
        raise SystemExit(f"Missing {csv_path.name}.")

    with csv_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit(f"{csv_path.name} has no data rows.")

    cur.execute("SELECT name, id FROM tools")
    tools = dict(cur.fetchall())
    cur.execute("SELECT label, id FROM availability")
    slots = dict(cur.fetchall())

    loaded = 0
    for row in rows:
        netid = row["netid"].strip()
        tool_ids = require_tokens(netid, "tools", split_list(row["tools"]), tools)
        slot_ids = require_tokens(
            netid, "availability", split_list(row["availability"]), slots
        )
        cur.execute(
            """
            INSERT INTO students (
                netid, name, school_year, intro_programming,
                skill_programming, skill_data_stats, skill_frontend_design,
                skill_business_pitch, working_style, interests, semester_goal,
                submitted_at
            ) VALUES (
                %(netid)s, %(name)s, %(school_year)s, %(intro_programming)s,
                %(skill_programming)s, %(skill_data_stats)s,
                %(skill_frontend_design)s, %(skill_business_pitch)s,
                %(working_style)s, %(interests)s, %(semester_goal)s,
                %(submitted_at)s
            )
            ON CONFLICT (netid) DO UPDATE SET
                name = EXCLUDED.name,
                school_year = EXCLUDED.school_year,
                intro_programming = EXCLUDED.intro_programming,
                skill_programming = EXCLUDED.skill_programming,
                skill_data_stats = EXCLUDED.skill_data_stats,
                skill_frontend_design = EXCLUDED.skill_frontend_design,
                skill_business_pitch = EXCLUDED.skill_business_pitch,
                working_style = EXCLUDED.working_style,
                interests = EXCLUDED.interests,
                semester_goal = EXCLUDED.semester_goal,
                submitted_at = EXCLUDED.submitted_at
            RETURNING id
            """,
            {
                "netid": netid,
                "name": row["name"].strip(),
                "school_year": row["school_year"].strip(),
                "intro_programming": row["intro_programming"].strip(),
                "skill_programming": int(row["skill_programming"]),
                "skill_data_stats": int(row["skill_data_stats"]),
                "skill_frontend_design": int(row["skill_frontend_design"]),
                "skill_business_pitch": int(row["skill_business_pitch"]),
                "working_style": row["working_style"] or None,
                "interests": row["interests"] or None,
                "semester_goal": row["semester_goal"] or None,
                "submitted_at": row["submitted_at"].strip(),
            },
        )
        (student_id,) = cur.fetchone()
        cur.execute("DELETE FROM student_tools WHERE student_id = %s", (student_id,))
        cur.execute(
            "DELETE FROM student_availability WHERE student_id = %s", (student_id,)
        )
        cur.executemany(
            "INSERT INTO student_tools (student_id, tool_id) VALUES (%s, %s)",
            [(student_id, tool_id) for tool_id in tool_ids],
        )
        cur.executemany(
            "INSERT INTO student_availability (student_id, availability_id) VALUES (%s, %s)",
            [(student_id, slot_id) for slot_id in slot_ids],
        )
        loaded += 1
    return loaded


def main() -> None:
    if Path(sys.prefix).resolve() == Path(sys.base_prefix).resolve():
        raise SystemExit("Run this with the project venv: ./venv/bin/python deploy.py")

    load_env(ROOT / ".env")
    schema_path = ROOT / "schema.sql"
    if not schema_path.is_file():
        raise SystemExit(f"Missing {schema_path.name}.")
    statements = split_sql(schema_path.read_text())
    if not statements:
        raise SystemExit(f"{schema_path.name} has no statements to run.")

    with psycopg.connect(database_url(), connect_timeout=20) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename = ANY(%s)
                ORDER BY tablename
                """,
                (list(TABLES),),
            )
            existing = {row[0] for row in cur.fetchall()}
            if not existing:
                for statement in statements:
                    cur.execute(statement)
                print("Deployed schema.")
            elif existing != set(TABLES):
                missing = ", ".join(sorted(set(TABLES) - existing))
                raise SystemExit(f"Database is missing tables: {missing}.")
            else:
                print("Schema already present.")

            loaded = load_dataset(cur)
            print(f"Loaded {loaded} students from class_dataset.csv.")
            for table in TABLES:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                (count,) = cur.fetchone()
                print(f"  {table}: {count} rows")
        conn.commit()


if __name__ == "__main__":
    main()
