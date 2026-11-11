#!/usr/bin/env python3
"""Serve a page of student names from the Railway database."""

import os
import sys
from pathlib import Path

import psycopg
from flask import Flask, jsonify, send_from_directory

from assignment_rules import assign_groups
from cluster_model import CENTROIDS

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


@app.get("/groups")
def group_assignments():
    return send_from_directory(app.static_folder, "groups.html")


@app.get("/api/students")
def student_names():
    with psycopg.connect(database_url(), connect_timeout=20) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM students ORDER BY name")
            names = [row[0] for row in cur.fetchall()]
    return jsonify([{"name": name} for name in names])


@app.get("/api/groups")
def groups():
    with psycopg.connect(database_url(), connect_timeout=20) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT netid, name, skill_programming, skill_data_stats,
                       skill_frontend_design, skill_business_pitch
                FROM students
                ORDER BY netid
                """
            )
            rows = cur.fetchall()

    names_by_netid = {}
    students = []
    for (
        netid,
        name,
        skill_programming,
        skill_data_stats,
        skill_frontend_design,
        skill_business_pitch,
    ) in rows:
        names_by_netid[netid] = name
        students.append(
            {
                "id": netid,
                "skill_programming": skill_programming,
                "skill_data_stats": skill_data_stats,
                "skill_frontend_design": skill_frontend_design,
                "skill_business_pitch": skill_business_pitch,
            }
        )

    assignments = assign_groups(students)
    n_groups = 8
    cluster_ids = range(len(CENTROIDS))
    members = {group: [] for group in range(1, n_groups + 1)}
    counts = {
        group: {cluster: 0 for cluster in cluster_ids}
        for group in range(1, n_groups + 1)
    }
    cluster_sizes = {cluster: 0 for cluster in cluster_ids}

    for assignment in assignments:
        group = assignment["group"]
        cluster = assignment["cluster"]
        members[group].append(names_by_netid[assignment["id"]])
        counts[group][cluster] += 1
        cluster_sizes[cluster] += 1

    present = {cluster for cluster, size in cluster_sizes.items() if size}
    groups_payload = []
    groups_missing_a_cluster = 0
    for group in range(1, n_groups + 1):
        cluster_counts = [
            {"cluster": cluster, "count": counts[group][cluster]}
            for cluster in cluster_ids
        ]
        if any(counts[group][cluster] == 0 for cluster in present):
            groups_missing_a_cluster += 1
        groups_payload.append(
            {
                "group": group,
                "members": members[group],
                "cluster_counts": cluster_counts,
            }
        )

    return jsonify(
        {
            "n_groups": n_groups,
            "groups": groups_payload,
            "clusters": [
                {
                    "cluster": cluster,
                    "students": cluster_sizes[cluster],
                    "centroid": list(centroid),
                }
                for cluster, centroid in enumerate(CENTROIDS)
            ],
            "groups_missing_a_cluster": groups_missing_a_cluster,
        }
    )


if __name__ == "__main__":
    if Path(sys.prefix).resolve() == Path(sys.base_prefix).resolve():
        raise SystemExit("Run this with the project venv: ./venv/bin/python app.py")
    load_env(ROOT / ".env")
    app.run(host="127.0.0.1", port=8080)
