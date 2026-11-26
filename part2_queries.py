import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

from db_config import database_url, exec_script

BASE = Path(__file__).resolve().parent
SQL_DIR = BASE / "sql"
OUT_FILE = BASE / "part2_output.txt"

engine = create_engine(database_url(), future=True)

_out = open(OUT_FILE, "w", encoding="utf-8")


def say(s=""):
    print(s)
    _out.write(s + "\n")


def header(title):
    say()
    say("=" * 78)
    say(title)
    say("=" * 78)


def table(result):
    cols = list(result.keys())
    rows = [["NULL" if v is None else str(v) for v in r] for r in result]
    widths = [max([len(c)] + [len(r[i]) for r in rows]) for i, c in enumerate(cols)]
    line = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    say(line)
    say("| " + " | ".join(c.ljust(w) for c, w in zip(cols, widths)) + " |")
    say(line)
    for r in rows:
        say("| " + " | ".join(v.ljust(w) for v, w in zip(r, widths)) + " |")
    say(line)
    say(f"({len(rows)} row{'s' if len(rows) != 1 else ''})")


def run(conn, sql, params=None, label=None):
    if label:
        say(f"-- {label}")
    say("SQL:")
    for ln in sql.strip().splitlines():
        say("    " + ln)
    if params:
        say(f"Parameters: {params}")
    res = conn.execute(text(sql), params or {})
    if res.returns_rows:
        table(res)
    else:
        say(f"Rows affected: {res.rowcount}")
    say()
    return res


def run_file(conn, path):
    say(f"Executing script {path.relative_to(BASE)}")
    exec_script(conn, path.read_text(encoding="utf-8"))


TABLES = ["app_user", "author", "author_research_area", "reviewer", "reviewer_expertise",
          "conference", "conference_host", "conference_reviewer", "track",
          "conference_session", "paper", "paper_keyword", "paper_author",
          "paper_version", "review"]


def task_1_create():
    header("TASK 1 - CREATE statements (tables + constraints from sql/01_schema.sql)")
    with engine.begin() as conn:
        run_file(conn, SQL_DIR / "01_schema.sql")
        run(conn, """
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name""", label="Tables created")
        run(conn, """
SELECT tc.table_name, tc.constraint_type, COUNT(*) AS n
FROM information_schema.table_constraints tc
WHERE tc.table_schema = 'public'
  AND tc.constraint_type IN ('PRIMARY KEY','FOREIGN KEY','UNIQUE','CHECK')
  AND tc.constraint_name NOT LIKE '%_not_null'
GROUP BY tc.table_name, tc.constraint_type
ORDER BY tc.table_name, tc.constraint_type""", label="Constraints per table")


def task_2_insert():
    header("TASK 2 - INSERT statements (seed data from sql/02_seed.sql)")
    with engine.begin() as conn:
        run_file(conn, SQL_DIR / "02_seed.sql")
        union = "\nUNION ALL ".join(
            f"SELECT '{t}' AS table_name, COUNT(*) AS row_count FROM {t}" for t in TABLES)
        run(conn, union, label="Row count of every table")
    say("Restore the initial dataset at any time with:  python init_db.py")


def task_3_1():
    header("TASK 3.1 - Update phone number of Arman Armanov (identified by email)")
    p = {"email": "arman.armanov@example.com", "phone": "+77773414141"}
    sel = """
SELECT user_id, given_name, surname, email, phone_number
FROM app_user WHERE email = :email"""
    with engine.connect() as conn:
        trans = conn.begin()
        run(conn, sel, {"email": p["email"]}, "BEFORE")
        run(conn, """
UPDATE app_user
SET phone_number = :phone
WHERE email = :email""", p, "UPDATE")
        run(conn, sel, {"email": p["email"]}, "AFTER")
        trans.rollback()
        say("Transaction rolled back -> seed data restored.")


def task_3_2():
    header("TASK 3.2 - Conditional UPDATE of review deadlines (+7 Astana, +3 otherwise)")
    p = {"city": "Astana", "astana_days": 7, "other_days": 3}
    sel = """
SELECT conference_id, acronym, city, review_deadline
FROM conference ORDER BY conference_id"""
    with engine.connect() as conn:
        trans = conn.begin()
        run(conn, sel, label="BEFORE")
        run(conn, """
UPDATE conference
SET review_deadline = review_deadline +
    CASE WHEN city = :city THEN CAST(:astana_days AS INTEGER)
         ELSE CAST(:other_days AS INTEGER) END""", p, "UPDATE (date + integer days)")
        run(conn, sel, label="AFTER")
        trans.rollback()
        say("Transaction rolled back -> seed data restored.")


DEPENDENTS = """
SELECT p.paper_id, p.title, p.status,
       (SELECT COUNT(*) FROM paper_author  x WHERE x.paper_id = p.paper_id) AS authors,
       (SELECT COUNT(*) FROM paper_keyword x WHERE x.paper_id = p.paper_id) AS keywords,
       (SELECT COUNT(*) FROM paper_version x WHERE x.paper_id = p.paper_id) AS versions,
       (SELECT COUNT(*) FROM review        x WHERE x.paper_id = p.paper_id) AS reviews
FROM paper p
WHERE p.paper_id IN (4, 5, 9, 12)   -- Amina's papers (4,5 withdrawn+corresponding)
ORDER BY p.paper_id"""

GLOBAL_COUNTS = """
SELECT (SELECT COUNT(*) FROM paper)         AS papers,
       (SELECT COUNT(*) FROM paper_author)  AS paper_authors,
       (SELECT COUNT(*) FROM paper_keyword) AS keywords,
       (SELECT COUNT(*) FROM paper_version) AS versions,
       (SELECT COUNT(*) FROM review)        AS reviews,
       (SELECT COUNT(*) FROM app_user)      AS users,
       (SELECT COUNT(*) FROM track)         AS tracks,
       (SELECT COUNT(*) FROM conference)    AS conferences"""


def task_4_1():
    header("TASK 4.1 - Delete withdrawn papers whose corresponding author is Amina Aminova")
    p = {"email": "amina.aminova@example.com", "status": "withdrawn"}
    with engine.connect() as conn:
        trans = conn.begin()
        run(conn, DEPENDENTS, label="BEFORE - Amina's papers and their dependent rows")
        run(conn, GLOBAL_COUNTS, label="BEFORE - table counts")
        run(conn, """
DELETE FROM paper p
WHERE p.status = :status
  AND EXISTS (SELECT 1
              FROM paper_author pa
              JOIN app_user u ON u.user_id = pa.author_id
              WHERE pa.paper_id = p.paper_id
                AND pa.is_corresponding
                AND u.email = :email)""", p,
            "DELETE (authorship, keywords, versions, reviews removed by ON DELETE CASCADE)")
        run(conn, DEPENDENTS, label="AFTER - papers 4 and 5 are gone, 9 and 12 remain")
        run(conn, GLOBAL_COUNTS, label="AFTER - table counts (users/tracks/conferences unchanged)")
        trans.rollback()
        say("Transaction rolled back -> seed data restored.")


def task_4_2():
    header("TASK 4.2 - Delete empty sessions of conferences held in Astana")
    p = {"city": "Astana"}
    sel = """
SELECT s.session_id, s.title, c.acronym, c.city,
       (SELECT COUNT(*) FROM paper p WHERE p.session_id = s.session_id) AS papers
FROM conference_session s JOIN conference c ON c.conference_id = s.conference_id
ORDER BY s.session_id"""
    with engine.connect() as conn:
        trans = conn.begin()
        run(conn, sel, label="BEFORE")
        run(conn, """
DELETE FROM conference_session s
USING conference c
WHERE c.conference_id = s.conference_id
  AND c.city = :city
  AND NOT EXISTS (SELECT 1 FROM paper p WHERE p.session_id = s.session_id)""", p, "DELETE")
        run(conn, sel, label="AFTER")
        run(conn, "SELECT COUNT(*) AS conferences FROM conference", label="All conferences kept")
        trans.rollback()
        say("Transaction rolled back -> seed data restored.")


def task_5():
    with engine.connect() as conn:
        header("TASK 5.1 - Accepted papers with corresponding author, track and conference")
        run(conn, """
SELECT p.paper_id, p.title,
       u.given_name || ' ' || u.surname AS corresponding_author,
       u.email                          AS corresponding_email,
       t.name                           AS track_name,
       c.conference_id, c.acronym
FROM paper p
JOIN track t         ON t.track_id = p.track_id
JOIN conference c    ON c.conference_id = t.conference_id
JOIN paper_author pa ON pa.paper_id = p.paper_id AND pa.is_corresponding
JOIN app_user u      ON u.user_id = pa.author_id
WHERE p.status = :status
ORDER BY p.paper_id""", {"status": "accepted"})

        header("TASK 5.2 - Papers whose abstract contains 'machine learning' (case-insensitive)")
        run(conn, """
SELECT paper_id, title
FROM paper
WHERE abstract ILIKE '%' || :phrase || '%'
ORDER BY paper_id""", {"phrase": "machine learning"})

        header("TASK 5.3 - All versions of a selected paper (newest first)")
        run(conn, """
SELECT version_no, file_location, uploaded_at
FROM paper_version
WHERE paper_id = :paper_id
ORDER BY version_no DESC""", {"paper_id": 3})

        header("TASK 5.4 - Pool reviewers with 'Databases' expertise and >= 3 years")
        run(conn, """
SELECT u.user_id AS reviewer_id,
       u.given_name || ' ' || u.surname AS full_name,
       u.email
FROM conference_reviewer cr
JOIN reviewer r ON r.reviewer_id = cr.reviewer_id
JOIN app_user u ON u.user_id = r.reviewer_id
WHERE cr.conference_id = :conference_id
  AND r.years_experience >= :min_years
  AND EXISTS (SELECT 1 FROM reviewer_expertise e
              WHERE e.reviewer_id = r.reviewer_id AND e.area_label = :area)
ORDER BY u.user_id""", {"conference_id": 1, "area": "Databases", "min_years": 3})


def task_6():
    with engine.connect() as conn:
        header("TASK 6.1 - Per track: distinct papers and distinct authors")
        run(conn, """
SELECT t.track_id, t.name AS track_name, t.conference_id,
       COUNT(DISTINCT p.paper_id)   AS paper_count,
       COUNT(DISTINCT pa.author_id) AS author_count
FROM track t
LEFT JOIN paper p         ON p.track_id = t.track_id
LEFT JOIN paper_author pa ON pa.paper_id = p.paper_id
GROUP BY t.track_id, t.name, t.conference_id
ORDER BY t.track_id""")

        header("TASK 6.2 - Per reviewer: completed reviews and average overall score")
        run(conn, """
SELECT r.reviewer_id,
       u.given_name || ' ' || u.surname AS full_name,
       COUNT(rv.review_id)                     AS review_count,
       ROUND(AVG(rv.overall_score), 2)         AS avg_overall_score
FROM reviewer r
JOIN app_user u     ON u.user_id = r.reviewer_id
LEFT JOIN review rv ON rv.reviewer_id = r.reviewer_id
GROUP BY r.reviewer_id, u.given_name, u.surname
ORDER BY r.reviewer_id""")

        header("TASK 6.3 - Per conference: papers, accepted papers, avg review score")
        run(conn, """
WITH paper_stats AS (
    SELECT t.conference_id,
           COUNT(*)                                     AS total_papers,
           COUNT(*) FILTER (WHERE p.status = 'accepted') AS accepted_papers
    FROM paper p JOIN track t ON t.track_id = p.track_id
    GROUP BY t.conference_id
),
review_stats AS (
    SELECT t.conference_id, AVG(rv.overall_score) AS avg_score
    FROM review rv
    JOIN paper p ON p.paper_id = rv.paper_id
    JOIN track t ON t.track_id = p.track_id
    GROUP BY t.conference_id
)
SELECT c.conference_id, c.acronym,
       COALESCE(ps.total_papers, 0)    AS total_papers,
       COALESCE(ps.accepted_papers, 0) AS accepted_papers,
       ROUND(rs.avg_score, 2)          AS avg_overall_score
FROM conference c
LEFT JOIN paper_stats  ps ON ps.conference_id = c.conference_id
LEFT JOIN review_stats rs ON rs.conference_id = c.conference_id
ORDER BY c.conference_id""")

        header("TASK 6.4 - Reviewers with more reviews than the average per reviewer")
        run(conn, """
WITH review_counts AS (
    SELECT r.reviewer_id, COUNT(rv.review_id) AS review_count
    FROM reviewer r
    LEFT JOIN review rv ON rv.reviewer_id = r.reviewer_id
    GROUP BY r.reviewer_id
),
overall AS (
    SELECT AVG(review_count) AS avg_reviews FROM review_counts
)
SELECT rc.reviewer_id,
       u.given_name || ' ' || u.surname AS full_name,
       rc.review_count,
       ROUND(o.avg_reviews, 2)          AS overall_avg_reviews
FROM review_counts rc
JOIN app_user u ON u.user_id = rc.reviewer_id
CROSS JOIN overall o
WHERE rc.review_count > o.avg_reviews
ORDER BY rc.review_count DESC, rc.reviewer_id""")


def task_7():
    header("TASK 7 - Acceptance rate per conference (derived attribute)")
    with engine.connect() as conn:
        run(conn, """
SELECT c.conference_id, c.acronym,
       COUNT(p.paper_id) FILTER (WHERE p.status = 'accepted') AS accepted_count,
       COUNT(p.paper_id) FILTER (WHERE p.status = 'rejected') AS rejected_count,
       ROUND(100.0 * COUNT(p.paper_id) FILTER (WHERE p.status = 'accepted')
             / NULLIF(COUNT(p.paper_id) FILTER (WHERE p.status IN ('accepted', 'rejected')), 0),
             2) AS acceptance_rate_pct
FROM conference c
LEFT JOIN track t ON t.conference_id = c.conference_id
LEFT JOIN paper p ON p.track_id = t.track_id
GROUP BY c.conference_id, c.acronym
ORDER BY c.conference_id""")


def task_8():
    header("TASK 8 - View accepted_paper_schedule")
    with engine.begin() as conn:
        view_sql = (SQL_DIR / "03_view.sql").read_text(encoding="utf-8")
        say("SQL:")
        for ln in view_sql.strip().splitlines():
            say("    " + ln)
        exec_script(conn, view_sql)
        say("View created.\n")
        run(conn, """
SELECT *
FROM accepted_paper_schedule
ORDER BY conference_id, session_date, start_time, session_id, paper_id""",
            label="Query the view")


if __name__ == "__main__":
    say(f"Database: {engine.url.render_as_string(hide_password=True)}")
    task_1_create()
    task_2_insert()
    task_3_1()
    task_3_2()
    task_4_1()
    task_4_2()
    task_5()
    task_6()
    task_7()
    task_8()
    _out.close()
    print(f"\nOutput saved to {OUT_FILE}", file=sys.stderr)
