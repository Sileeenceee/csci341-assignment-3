# CSCI 341 Assignment 3 – Research Conference & Paper Review Management System

## 1. Contents

| Path | Purpose |
|---|---|
| `sql/01_schema.sql` | Tables, keys and constraints (re-runnable: it drops the old objects first) |
| `sql/02_seed.sql` | Fictional sample data |
| `sql/03_view.sql` | View `accepted_paper_schedule` (Task 8) |
| `conference_review_dump.sql` | Plain `pg_dump` export of the schema, seed data and view |
| `init_db.py` | Creates and populates the database (01 + 02 + 03). Run it again to restore the seed data |
| `part2_queries.py` | Part 2: tasks 1–8 through SQLAlchemy. Output is written to `part2_output.txt` |
| `webapp/` | Part 3: Flask web application (`app.py`, `checks.py`, `templates/`) |
| `tests/test_webapp.py` | Automated CRUD and constraint-check test of the web app |
| `requirements.txt`, `vercel.json`, `api/index.py` | Dependencies and Vercel deployment configuration (`Procfile`, `render.yaml`: alternative for Render) |
| `links.txt`, `executive_summary.md` | Links and summary for submission |

## 2. Software versions

* PostgreSQL 17.4. Any version from 14 onwards works.
* Python 3.13
* SQLAlchemy 2.0.36, psycopg 3.2.3, Flask 3.1.0, gunicorn 23.0.0

## 3. Setup, database restoration and running

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
createdb conference_review                     # once
export DATABASE_URL=postgresql://localhost/conference_review   # this is also the default

python init_db.py          # create + populate. Run it again at any time to RESTORE the seed data
python part2_queries.py    # Part 2, tasks 1–8. Results also go to part2_output.txt
flask --app webapp.app run # Part 3 at http://127.0.0.1:5000
python tests/test_webapp.py  # optional automated test (it resets the DB before and after)
```

You can also restore from the dump: `createdb conference_review && psql conference_review < conference_review_dump.sql`.
In the web app, the **"Reset database to seed data"** button on the home page restores the seed data.

`part2_queries.py` re-creates the schema and data itself (tasks 1 and 2). Each UPDATE and DELETE task
runs in a transaction. The task prints the rows before and after the change, then **rolls back**. Every
task therefore runs against the original seed dataset.

### Deployment (Vercel + Neon PostgreSQL)
The app is deployed at **https://csci341-assignment3-eosin.vercel.app** with a persistent PostgreSQL database on Neon.

1. Create a PostgreSQL database (Neon, or any provider) and copy its connection string.
2. Import the GitHub repository into Vercel. `vercel.json` and `api/index.py` expose the Flask app as a Python function.
   Set the environment variables `DATABASE_URL` (the connection string) and `SECRET_KEY` (any random string).
3. Load the seed data once. Either run `DATABASE_URL="<connection string>" python init_db.py` from your machine,
   or open the deployed app and press **"Reset database to seed data"** on the home page.

`render.yaml` and `Procfile` are kept as an alternative configuration for Render (start command `gunicorn webapp.app:app`).

## 4. Schema, keys and references

Primary keys are in **bold**. FK = foreign key. The deletion action is shown in brackets.

| Table | Columns | Keys / constraints |
|---|---|---|
| app_user | **user_id**, given_name, surname, email, affiliation, country, phone_number | email UNIQUE; all NOT NULL |
| author | **author_id**, orcid (optional) | author_id FK → app_user [CASCADE]; orcid UNIQUE |
| author_research_area | **author_id, area_label** | FK → author [CASCADE] |
| reviewer | **reviewer_id**, years_experience | FK → app_user [CASCADE]; CHECK years_experience ≥ 0 |
| reviewer_expertise | **reviewer_id, area_label** | FK → reviewer [CASCADE] |
| conference | **conference_id**, name, acronym, description, city, country, start_date, end_date, submission_deadline, review_deadline | acronym UNIQUE; CHECK end_date ≥ start_date; CHECK review_deadline ≥ submission_deadline |
| conference_host | **conference_id, host_name** | FK → conference [CASCADE] |
| conference_reviewer (pool) | **conference_id, reviewer_id** | FK → conference [CASCADE], FK → reviewer [CASCADE] |
| track | **track_id**, conference_id, name, description, research_area, coordinator_id | FK → conference [CASCADE]; coordinator_id FK → reviewer [NO ACTION]; (conference_id, coordinator_id) FK → conference_reviewer; UNIQUE(conference_id, name) |
| conference_session | **session_id**, conference_id, title, session_date, start_time, end_time, room_label, chair_id | FK → conference [CASCADE]; chair_id FK → reviewer [NO ACTION]; (conference_id, chair_id) FK → conference_reviewer; CHECK end_time > start_time |
| paper | **paper_id**, track_id, title, abstract, submission_date, status, session_id (optional) | track_id FK → track [NO ACTION]; session_id FK → conference_session [SET NULL]; CHECK status ∈ {submitted, under review, accepted, rejected, withdrawn}; CHECK session_id IS NULL OR status = 'accepted' |
| paper_keyword | **paper_id, keyword** | FK → paper [CASCADE] |
| paper_author | **paper_id, author_id**, author_position, is_corresponding | FK → paper [CASCADE]; FK → author [NO ACTION]; UNIQUE(paper_id, author_position); CHECK author_position > 0; partial UNIQUE index: at most one corresponding author per paper |
| paper_version | **paper_id, version_no**, file_location, uploaded_at, change_note (optional) | FK → paper **[CASCADE]**; CHECK version_no > 0 |
| review | **review_id**, paper_id, reviewer_id, overall_score, recommendation, comments_for_authors, confidential_comments (optional), review_submission_date | FK → paper [CASCADE]; FK → reviewer [NO ACTION]; UNIQUE(paper_id, reviewer_id); CHECK overall_score BETWEEN 1 AND 5; CHECK recommendation ∈ {accept, reject} |

The multivalued attributes (research areas, expertise, hosts and keywords) and the author list each have their own relation. No column stores a comma-separated list. The web forms accept comma-separated input as a convenience, but the application splits that input into separate rows before saving.

**Deletion behaviour**
* Deleting a paper removes its versions, authorship rows, keywords and reviews (CASCADE).
* Deleting a session leaves its papers in place and sets their `session_id` to NULL.
* Deleting a conference removes its hosts, pool, tracks and sessions. It is **rejected** if any of its tracks still has papers. Users and reviewers are never deleted with a conference.
* Deleting a user removes their author and reviewer profiles. It is **rejected** if the user authored a paper, wrote a review, or coordinates a track or chairs a session. Those referenced records must be removed first.
* Only completed reviews are stored. Every review column except `confidential_comments` is NOT NULL.
* Versions are identified by (paper_id, version_no). Gaps are allowed, and the highest number is the current version.

## 5. Required application checks (`webapp/checks.py`)

All related changes run in one transaction (`engine.begin()`). If a check fails, the whole transaction is
rolled back and a red error message is shown. Database constraint violations are also caught and
reported, with the constraint name.

1. **No self-reviews.** `check_no_self_review(paper_id)` runs after a review is created or edited, and
   after a paper's author list changes. The change is rejected if any reviewer of the paper is also one of its authors.
2. **Valid session assignments.** A scheduled paper must be `accepted`, and its track's conference must
   equal its session's conference. The check runs in four places:
   * when a paper is assigned to a session (session page or paper form);
   * when a paper's status or track changes (paper form);
   * when a session's conference changes (session form; `check_session_papers`);
   * as a backstop, the DB CHECK `ck_paper_session_accepted` enforces the status part.

   Invalid changes are **rejected**.

## 6. Other business rules

The sample data satisfies all of them.

| Rule | Enforced automatically? |
|---|---|
| Every user has the author role, the reviewer role, or both | Yes – web app (user form) |
| Exactly one corresponding author per paper | At most one: DB partial unique index. At least one: web app |
| A paper has at least one author, one keyword and one version | Yes – web app (paper form; the last version cannot be deleted) |
| An author has at least one research area; a reviewer has at least one expertise area | Yes – web app |
| Track coordinators and session chairs belong to the conference's reviewer pool | Yes – DB composite FKs |
| A reviewer reviews only papers of conferences whose pool they belong to | Yes – web app |
| No duplicate author in a paper; no duplicate author position | Yes – DB primary key / UNIQUE |
| Review deadline is not before the submission deadline | Yes – DB CHECK |
| Session date lies within the conference dates; reviews are submitted before the review deadline; papers are submitted before the submission deadline | Not enforced. They hold in the sample data |

## 7. Design assumptions
* Author and reviewer are role subtypes of `app_user` and share its primary key. A user can hold both roles.
* `phone_number`, `affiliation` and `country` are mandatory, as in the reference schema. `orcid` is optional and unique.
* `paper.session_id` models the "at most one session per paper" rule.
* Conferences, tracks, hosts and labels are reference data loaded by the seed script. They are read-only in the web app. Reviewer pools can be edited from the user form.
* No authentication and no real file uploads. `paper_version.file_location` stores a path.

## 8. Sample data and query parameter values

The database holds 13 users, 13 papers, 17 versions, 18 reviews and 3 conferences:
* CADS 2026 in Astana
* SSAI 2026 in Almaty
* SRLT 2026 in Tashkent, which has no papers

The data includes the following cases:
* Author-only users: 2, 6, 9 and 12.
* Reviewer-only users: 3, 4, 7, 10 and 11.
* Users with both roles: 1, 5, 8 and 13.
* All five paper statuses.
* Papers with several authors and papers with several versions.
* Empty tracks 3 and 6.
* Reviewer 10, who has no reviews.
* Accepted papers with a session (1, 2 and 10) and without one (3 and 12).
* Empty session 2 in Astana, which task 4.2 deletes, and empty session 4 in Tashkent, which it keeps.

| Task | Parameters | Expected effect / result |
|---|---|---|
| 3.1 | email = `arman.armanov@example.com`, phone = `+77773414141` | 1 row updated |
| 3.2 | city = `Astana`, +7 / +3 days | CADS +7 days; SSAI and SRLT +3 days |
| 4.1 | email = `amina.aminova@example.com`, status = `withdrawn` | Papers 4 and 5 deleted. Paper 9 is kept (withdrawn, but Amina is not the corresponding author). Paper 12 is kept (accepted) |
| 4.2 | city = `Astana` | Session 2 deleted |
| 5.1 | status = `accepted` | Papers 1, 2, 3, 10, 12 |
| 5.2 | phrase = `machine learning` | Papers 1, 3, 11 (matched case-insensitively) |
| 5.3 | paper_id = `3` | Versions 3 and 1 (gap) |
| 5.4 | conference_id = `1`, area = `Databases`, min_years = `3` | Reviewers 1, 3, 4, 5 |
| 6.4 | — | Average = 2.00 reviews per reviewer. Reviewers 3 (4 reviews), 4 (4) and 7 (3) are above it |
| 7 | — | CADS 75.00 %, SSAI 66.67 %, SRLT NULL |
| 8 | — | Papers 1, 2 (session 1) and 10 (session 3) |

## 9. Web app demo checklist
* **Self-review rejected:**
  * Reviews → New review → paper 6, reviewer 1 (Arman authored paper 6) → error.
  * Or edit paper 1 and add **Kenji Tanaka** as an author. Kenji already reviewed paper 1, so the change is rejected.
* **Invalid session assignment rejected:**
  * Sessions → session 1 → assign paper 7 (submitted) → error.
  * Assign paper 10 (accepted, but from SSAI) → error.
  * Or edit paper 1, set its status to `rejected` and keep session 1 → error.
