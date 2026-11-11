"""Assign students to groups by dealing clusters round-robin."""

import csv
from pathlib import Path

from cluster_model import predict_cluster

SKILL_COLUMNS = (
    "skill_programming",
    "skill_data_stats",
    "skill_frontend_design",
    "skill_business_pitch",
)

DATA_PATH = Path(__file__).resolve().parent / "class_dataset.csv"


def assign_groups(students, n_groups=8):
    """Return each student's id, cluster, and group.

    Clusters are ordered from most students to fewest, with the lower cluster
    number first when two clusters are the same size. Students are sorted by
    id inside a cluster. That sequence is dealt to groups 1..n_groups, and the
    count continues across clusters.
    """
    labeled = []
    for student in students:
        skills = tuple(float(student[column]) for column in SKILL_COLUMNS)
        labeled.append(
            {
                "id": student["id"],
                "cluster": predict_cluster(skills),
                "group": None,
            }
        )

    by_cluster = {}
    for student in labeled:
        by_cluster.setdefault(student["cluster"], []).append(student)
    for members in by_cluster.values():
        members.sort(key=lambda student: student["id"])

    cluster_order = sorted(
        by_cluster,
        key=lambda cluster: (-len(by_cluster[cluster]), cluster),
    )
    deal = []
    for cluster in cluster_order:
        deal.extend(by_cluster[cluster])

    for index, student in enumerate(deal):
        student["group"] = (index % n_groups) + 1

    return [
        {"id": student["id"], "cluster": student["cluster"], "group": student["group"]}
        for student in labeled
    ]


def load_students(path):
    students = []
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            student = {"id": row["netid"]}
            for column in SKILL_COLUMNS:
                student[column] = float(row[column])
            students.append(student)
    return students


def main():
    n_groups = 8
    assignments = assign_groups(load_students(DATA_PATH), n_groups)
    clusters = sorted({student["cluster"] for student in assignments})
    groups = range(1, n_groups + 1)

    missing = 0
    for group in groups:
        members = [student for student in assignments if student["group"] == group]
        counts = {
            cluster: sum(student["cluster"] == cluster for student in members)
            for cluster in clusters
        }
        count_text = ", ".join(
            f"cluster {cluster}: {counts[cluster]}" for cluster in clusters
        )
        print(f"Group {group}: {len(members)} students ({count_text})")
        if any(counts[cluster] == 0 for cluster in clusters):
            missing += 1

    print(f"Groups missing a cluster: {missing}")


if __name__ == "__main__":
    main()
