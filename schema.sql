-- Class roster schema (PostgreSQL)
--
-- Source columns in class_dataset.csv split into:
--   students              one row per submission (scalar fields)
--   tools                 controlled list of tools (Python, SQL, ...)
--   availability          controlled list of time slots
--   student_tools         which tools each student listed
--   student_availability  which slots each student listed
--
-- tools and availability in the CSV are semicolon-separated. Split those
-- values on load and insert one bridge row per token. Match tokens to
-- tools.name and availability.label.

CREATE TABLE students (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    netid                   TEXT NOT NULL UNIQUE,
    name                    TEXT NOT NULL,
    school_year            TEXT NOT NULL CHECK (school_year IN (
                                'First-year',
                                'Sophomore',
                                'Junior',
                                'Senior'
                            )),
    intro_programming       TEXT NOT NULL CHECK (intro_programming IN (
                                'took_it',
                                'equivalent',
                                'neither'
                            )),
    skill_programming       SMALLINT NOT NULL CHECK (skill_programming BETWEEN 1 AND 5),
    skill_data_stats        SMALLINT NOT NULL CHECK (skill_data_stats BETWEEN 1 AND 5),
    skill_frontend_design   SMALLINT NOT NULL CHECK (skill_frontend_design BETWEEN 1 AND 5),
    skill_business_pitch    SMALLINT NOT NULL CHECK (skill_business_pitch BETWEEN 1 AND 5),
    working_style           TEXT,
    interests               TEXT,
    semester_goal           TEXT,
    submitted_at            TIMESTAMPTZ NOT NULL
);

-- Lookup of tools students reported. name matches the CSV token exactly.
CREATE TABLE tools (
    id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE
);

-- Lookup of availability slots. label matches the CSV token exactly.
-- day_group and time_of_day let you filter without parsing the label.
CREATE TABLE availability (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    label       TEXT NOT NULL UNIQUE,
    day_group   TEXT NOT NULL CHECK (day_group IN ('weekday', 'weekend')),
    time_of_day TEXT NOT NULL CHECK (time_of_day IN ('morning', 'afternoon', 'evening')),
    UNIQUE (day_group, time_of_day)
);

-- Bridge: a student can list many tools, and a tool can belong to many students.
CREATE TABLE student_tools (
    student_id  INTEGER NOT NULL REFERENCES students (id) ON DELETE CASCADE,
    tool_id     INTEGER NOT NULL REFERENCES tools (id) ON DELETE RESTRICT,
    PRIMARY KEY (student_id, tool_id)
);

CREATE INDEX student_tools_tool_id_idx ON student_tools (tool_id);

-- Bridge: a student can list many slots, and a slot can belong to many students.
CREATE TABLE student_availability (
    student_id      INTEGER NOT NULL REFERENCES students (id) ON DELETE CASCADE,
    availability_id INTEGER NOT NULL REFERENCES availability (id) ON DELETE RESTRICT,
    PRIMARY KEY (student_id, availability_id)
);

CREATE INDEX student_availability_availability_id_idx
    ON student_availability (availability_id);

-- Reference data observed in class_dataset.csv.
INSERT INTO tools (name) VALUES
    ('Python'),
    ('SQL'),
    ('Excel'),
    ('JavaScript'),
    ('R');

INSERT INTO availability (label, day_group, time_of_day) VALUES
    ('Weekday mornings',   'weekday', 'morning'),
    ('Weekday afternoons', 'weekday', 'afternoon'),
    ('Weekday evenings',   'weekday', 'evening'),
    ('Weekend mornings',   'weekend', 'morning'),
    ('Weekend afternoons', 'weekend', 'afternoon'),
    ('Weekend evenings',   'weekend', 'evening');
