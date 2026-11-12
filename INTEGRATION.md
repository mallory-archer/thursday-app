# Integrating the group assignment into the app

Do not edit `cluster_model.py` or `assignment_rules.py`. The app adapts to them. Do not change the frontend in this step.

## 1. What these two files do

`cluster_model.py` stores the three fitted k-means centroids for the skill ratings and exposes `predict_cluster`, which returns the nearest centroid for one student. `assignment_rules.py` calls that function for every student, orders clusters from most students to fewest (lower cluster number first when sizes match), sorts each cluster by `id`, and deals that sequence round-robin to groups 1 through `n_groups`, continuing the count across clusters. Neither file connects to a database: `assign_groups` takes a list of dicts and returns each student's `id`, `cluster`, and `group`.

## 2. Files to copy

Copy `cluster_model.py` and `assignment_rules.py` into a `model/` directory at the app repo root, next to this file:

```
app.py
model/cluster_model.py
model/assignment_rules.py
model/INTEGRATION.md
```

If those two Python files are already beside `app.py`, move them into `model/`. Leave one copy only. `assignment_rules.py` imports `predict_cluster` with `from cluster_model import predict_cluster`, so `model/` has to be on `sys.path` before that import. Do not change the import, and do not put the files in a package that would require `model.cluster_model`.

In `app.py`, before importing either module:

```python
import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent / "model"
sys.path.insert(0, str(MODEL_DIR))

from assignment_rules import assign_groups
from cluster_model import CENTROIDS
```

## 3. The two functions

`predict_cluster(skills)` takes one sequence of four numbers, in this order: `skill_programming`, `skill_data_stats`, `skill_frontend_design`, `skill_business_pitch`. It returns the cluster number `0`, `1`, or `2`.

```python
predict_cluster((3, 4, 2, 5))  # 0
```

`assign_groups(students, n_groups=8)` takes the whole class. Each student is a dict with `id` and those same four skill keys. It returns a list of dicts, one per student, in the same order as the input. Each dict has `id`, `cluster`, and `group`. Group numbers start at 1. Call it once for the whole class. A single student has no group until the rest of the class is dealt.

```python
assign_groups(
    [
        {"id": "a", "skill_programming": 3, "skill_data_stats": 4, "skill_frontend_design": 2, "skill_business_pitch": 5},
        {"id": "b", "skill_programming": 4, "skill_data_stats": 4, "skill_frontend_design": 1, "skill_business_pitch": 1},
    ],
    n_groups=2,
)
# [
#   {"id": "a", "cluster": 0, "group": 1},
#   {"id": "b", "cluster": 1, "group": 2},
# ]
```

`cluster_model.CENTROIDS` is a tuple of the three centroids, in cluster order `0`, `1`, `2`. Each centroid is the four skill averages in the same column order as `predict_cluster`. Use those values in the response. Do not recompute them.

`assignment_rules.py` also has `load_students` and `main`, which read `class_dataset.csv`. Do not call them. The running app has no CSV.

## 4. Where the data comes from

The fit was trained on `class_dataset.csv`. The app reads Postgres. `schema.sql` defines the tables. `deploy.py` loads that CSV into them. For this endpoint, read `students` only.

| What the model needs | CSV column | Postgres |
|---|---|---|
| `id` | `netid` | `students.netid` |
| `skill_programming` | `skill_programming` | `students.skill_programming` |
| `skill_data_stats` | `skill_data_stats` | `students.skill_data_stats` |
| `skill_frontend_design` | `skill_frontend_design` | `students.skill_frontend_design` |
| `skill_business_pitch` | `skill_business_pitch` | `students.skill_business_pitch` |

The response also needs each student's name, from `students.name` (CSV column `name`). Keep that name beside the call. `assign_groups` does not accept or return it.

Differences from the CSV:

- Pass `students.netid` as `id`. `students.id` is an integer identity primary key and is a different value. The deal sorts by `id`, so the integer key would assign different groups than the CSV run.
- The four skill columns are `SMALLINT` values from 1 to 5. In the CSV they were text numerals with the same values. `assign_groups` converts them with `float()`. Select them as numbers and put them on the dict under those four key names.
- The model repo's CSV has a `cluster` column written by the fit. `students` has no `cluster` column and no `group` column. Do not select one, and do not add one. Compute both by calling `assign_groups`.
- `deploy.py` splits `tools` and `availability` into `tools`, `availability`, `student_tools`, and `student_availability`. The model does not use those tables.

Query every student:

```sql
SELECT netid, name,
       skill_programming, skill_data_stats,
       skill_frontend_design, skill_business_pitch
FROM students
```

Build one dict per row: `id` set to `netid`, plus the four skill keys. Hold `name` in a separate map keyed by `netid`.

## 5. Backend

Add `GET /api/groups` in `app.py`. Leave `GET /` and `GET /api/students` as they are.

The route reads every student with the query above, using the existing `database_url()` and `psycopg.connect` pattern. Call `assign_groups` once with `n_groups=8`. Build the JSON below. Use each returned `cluster` only to count. Do not put any student's cluster on that student, in a member object, or anywhere else in the response. `members` is a list of name strings.

```json
{
  "n_groups": 8,
  "groups": [
    {
      "group": 1,
      "members": ["Kashish Satija", "Natalie Chen", "Roxane Framroze"],
      "cluster_counts": {"0": 2, "1": 1, "2": 0}
    }
  ],
  "clusters": [
    {
      "cluster": 0,
      "students": 13,
      "centroid": [2.923076923076923, 3.0769230769230766, 2.8461538461538463, 4.0]
    }
  ],
  "groups_missing_a_cluster": 6
}
```

- `n_groups` is `8`.
- `groups` has one object per group number from 1 to 8. `members` is the names of the students whose `group` is that number. `cluster_counts` maps `"0"`, `"1"`, and `"2"` to how many of that group's members came from that cluster. Include a key even when the count is 0.
- `clusters` has one object per centroid, in order 0, 1, 2. `students` is how many students were assigned that cluster. `centroid` is the matching entry of `CENTROIDS`, as a list of four numbers.
- `groups_missing_a_cluster` is how many groups have a 0 in `cluster_counts`. A group that has students from all three clusters does not count.

## 6. Frontend

Do not change `static/index.html` or `static/app.js`. The existing page keeps listing names from `GET /api/students`.

`GET /api/groups` is the payload a later page can render. `n_groups` is how many groups were dealt. Each item in `groups` is one group: its number, the member names, and how many members came from each cluster. A `0` in `cluster_counts` means that group has nobody from that cluster. `groups_missing_a_cluster` is the number of groups with at least one such zero. Each item in `clusters` is a cluster summary for the whole class: the cluster number, how many students are in it, and its centroid in the order programming, data/stats, frontend, pitch. The JSON does not say which person is in which cluster.

## 7. Packaging

`Dockerfile` copies `requirements.txt`, `app.py`, and `static/`. Add the model directory so the image contains it:

```
COPY model ./model
```

Put that next to `COPY app.py .`. `requirements.txt` stays as it is. These modules use the standard library only. Nothing about pandas or scikit-learn is added. `.dockerignore` already excludes `*.csv`, which is another reason the route must not call `load_students`.

Local `./venv/bin/python app.py` sees `model/` on disk without an image rebuild. A deploy does not, until this `COPY` is in the image.

## 8. Test

Start the app the usual way, from the app root, so it loads `.env` and listens on port 8080:

```
./venv/bin/python app.py
```

In another terminal:

```
curl -s http://127.0.0.1:8080/api/groups
```

Expect HTTP 200 and JSON with `n_groups` of 8 and `groups_missing_a_cluster` of 6. Group sizes and cluster counts:

| Group | Students | cluster 0 | cluster 1 | cluster 2 |
|---|---|---|---|---|
| 1 | 3 | 2 | 1 | 0 |
| 2 | 3 | 2 | 1 | 0 |
| 3 | 3 | 2 | 0 | 1 |
| 4 | 3 | 2 | 0 | 1 |
| 5 | 3 | 2 | 0 | 1 |
| 6 | 3 | 1 | 1 | 1 |
| 7 | 3 | 1 | 1 | 1 |
| 8 | 2 | 1 | 1 | 0 |

Cluster summaries: cluster 0 has 13 students, cluster 1 has 5, cluster 2 has 5. Member names for those groups, in any order:

1. Kashish Satija, Natalie Chen, Roxane Framroze
2. Ali Shehadi, Olivia Rong, Xiangyue Fan
3. Dev Ganguli, Hajin Jung, Simon Gu
4. Avirul Islam, Hendry Jimenez Tejeda, Yulong Ou
5. Alex Xu, Edward Huang, Jin Michael Qian
6. Maxson Cook, Muhammad Hamza, Myra Rafiq
7. Adriana Escobedo, Sheharyar Khan, Solomon Kim
8. Allan You, Rania Aamer

Reload `/` in the browser. The page still shows only the name list.
