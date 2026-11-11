# Integrating the group assignment into the app

Do not edit `cluster_model.py` or `assignment_rules.py`. The app adapts to them.

## 1. What these two files do

`cluster_model.py` stores the three fitted k-means centroids as plain numbers and exposes `predict_cluster`, which returns the nearest centroid for four skill ratings. `assignment_rules.py` calls that function for every student, orders clusters from most students to fewest (lower cluster number first on a tie), sorts each cluster by `id`, and deals that sequence round-robin to groups 1 through `n_groups`, continuing the count across clusters. Neither file connects to a database: `assign_groups` takes a list of dicts and returns each student's `id`, `cluster`, and `group`.

## 2. Files to copy

Copy `cluster_model.py` and `assignment_rules.py` into the app root, the directory that contains `app.py`. They must stay side by side: `assignment_rules.py` imports `predict_cluster` with `from cluster_model import predict_cluster`. Copy nothing else. Do not copy a CSV, and do not add pandas or scikit-learn.

## 3. The two functions

`predict_cluster(skills)` takes the four ratings in this order: `skill_programming`, `skill_data_stats`, `skill_frontend_design`, `skill_business_pitch`. It returns the cluster number `0`, `1`, or `2`.

```python
predict_cluster((3, 4, 2, 5))  # 0
```

`assign_groups(students, n_groups=8)` takes a list of dicts. Each dict has `id` and those four skill keys. It returns a list of dicts, in the same order as the input, each with `id`, `cluster`, and `group`. Groups are numbered from 1. The default `n_groups` is 8; the route should use that default.

```python
assign_groups(
    [
        {
            "id": "a",
            "skill_programming": 3,
            "skill_data_stats": 4,
            "skill_frontend_design": 2,
            "skill_business_pitch": 5,
        },
        {
            "id": "b",
            "skill_programming": 4,
            "skill_data_stats": 4,
            "skill_frontend_design": 1,
            "skill_business_pitch": 1,
        },
    ],
    n_groups=2,
)
# [
#   {"id": "a", "cluster": 0, "group": 1},
#   {"id": "b", "cluster": 1, "group": 2},
# ]
```

Leave `load_students` and the file's `main` unused. They read `class_dataset.csv` from disk. The route reads Postgres.

## 4. Where the data comes from

`schema.sql` defines the roster. `deploy.py` loads `class_dataset.csv` into it. The models need five inputs. Pass `netid` as `id`.

| Input on the dict | Table and column | How this differs from the CSV |
| --- | --- | --- |
| `id` | `students.netid` (`TEXT`, unique) | The CSV column is `netid`. `students.id` is a separate integer identity primary key. Do not pass that integer. `assign_groups` sorts by `id`, and the checked grouping sorted these netid strings. `deploy.py` stores `netid` stripped. |
| `skill_programming` | `students.skill_programming` | `SMALLINT` from 1 to 5. `deploy.py` inserts it with `int(...)`. The CSV cell is text. `assign_groups` calls `float()` on the value, which accepts the integer. |
| `skill_data_stats` | `students.skill_data_stats` | Same as `skill_programming`. |
| `skill_frontend_design` | `students.skill_frontend_design` | Same as `skill_programming`. |
| `skill_business_pitch` | `students.skill_business_pitch` | Same as `skill_programming`. |

The dict keys must be those skill names. `assign_groups` looks them up by name.

`students.name` is not a model input. Keep it beside the call, keyed by `netid`, and use it only when building `members`. The model return value's `id` is the `netid` you passed in.

`schema.sql` has no `cluster` column and no `group` column. `deploy.py` does not load one. A `cluster` column on the modeling CSV is leftover from the fit and is not in the database. `predict_cluster` computes the label. Tools and availability live in `tools`, `availability`, `student_tools`, and `student_availability`. The models do not use them.

No schema change is required. The route computes clusters and groups from the skill columns on each request.

## 5. Backend

Add `GET /api/groups` in `app.py`, using the same `psycopg.connect(database_url(), connect_timeout=20)` pattern as `GET /api/students`.

Read every student: `netid`, `name`, and the four skill columns from `students`. Build the dicts described in section 4, call `assign_groups` with the default of 8 groups, and hold each `name` by `netid` so you can fill `members` without asking the model for a name.

Import `CENTROIDS` from `cluster_model` for the centroid values. Do not recompute them. Each centroid is the four ratings in the same order as `predict_cluster`.

Return one JSON object:

- `n_groups`: `8`.
- `groups`: one object per group, groups 1 through 8. Each has `group` (the number), `members` (a list of `students.name` strings and nothing else), and `cluster_counts` (a list of `{cluster, count}` for clusters 0, 1, and 2, including counts of 0).
- `clusters`: one object per entry in `CENTROIDS`. Each has `cluster` (the index), `students` (how many assigned students are in that cluster; a count, not a list of people), and `centroid` (the four numbers).
- `groups_missing_a_cluster`: how many groups have a `count` of 0 for at least one cluster that appears in the class.

Do not return any one person's cluster. Use the per-student `cluster` from `assign_groups` only to add up `cluster_counts` and `clusters[].students`. `members` is names only.

## 6. Frontend

Change nothing in `static/index.html` or `static/app.js`. They still list names from `GET /api/students`.

`GET /api/groups` is there for a later page. The body looks like this (one group and one cluster shown; the real body has all eight groups and all three clusters):

```json
{
  "n_groups": 8,
  "groups": [
    {
      "group": 1,
      "members": ["A student name", "Another student name", "A third student name"],
      "cluster_counts": [
        {"cluster": 0, "count": 2},
        {"cluster": 1, "count": 1},
        {"cluster": 2, "count": 0}
      ]
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

`members` does not say which cluster a person is in. `cluster_counts` says how many people in that group came from each cluster. `clusters` describes each cluster as a whole: how many students are in it, and the centroid that defines it. A `count` of 0 means that group is missing that cluster. `groups_missing_a_cluster` is the number of groups for which that happens.

## 7. Packaging

`Dockerfile` copies `app.py` and `static/` only. Add the two modules next to that copy of `app.py`:

```dockerfile
COPY cluster_model.py .
COPY assignment_rules.py .
```

`WORKDIR` is `/app`, and gunicorn loads `app:app` from there, so those copies are importable. `requirements.txt` stays as it is. `.dockerignore` ignores `*.csv` and does not ignore these `.py` files.

## 8. Test

Start the app the way it already starts (`./venv/bin/python app.py`). It listens on `http://127.0.0.1:8080`. The database must already contain this class, loaded by `deploy.py`.

```bash
curl -s http://127.0.0.1:8080/api/groups
```

Expect `n_groups` of 8, group sizes of 3, 3, 3, 3, 3, 3, 3, and 2, and `groups_missing_a_cluster` of 6. The counts behind those sizes, from the run of these files on this class:

| Group | Students | Cluster 0 | Cluster 1 | Cluster 2 |
| --- | --- | --- | --- | --- |
| 1 | 3 | 2 | 1 | 0 |
| 2 | 3 | 2 | 1 | 0 |
| 3 | 3 | 2 | 0 | 1 |
| 4 | 3 | 2 | 0 | 1 |
| 5 | 3 | 2 | 0 | 1 |
| 6 | 3 | 1 | 1 | 1 |
| 7 | 3 | 1 | 1 | 1 |
| 8 | 2 | 1 | 1 | 0 |

Cluster totals are 13, 5, and 5. Groups 6 and 7 have every cluster. The other six are each missing one.
