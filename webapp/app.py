import os
import sys
from datetime import datetime
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db_config import database_url  # noqa: E402

from webapp.checks import (CheckError, check_no_self_review, check_paper_authors,  # noqa: E402
                           check_paper_session, check_reviewer_in_pool,
                           check_session_papers)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
engine = create_engine(database_url(), pool_pre_ping=True)

STATUSES = ["submitted", "under review", "accepted", "rejected", "withdrawn"]
AUTHOR_ROWS = 6


def q(sql, **params):
    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()


def q1(sql, **params):
    rows = q(sql, **params)
    return rows[0] if rows else None


def none_if_blank(v):
    v = (v or "").strip()
    return v or None


def to_int(v, field):
    v = none_if_blank(v)
    if v is None:
        return None
    try:
        return int(v)
    except ValueError:
        raise CheckError(f"{field} must be an integer.")


def split_labels(v):
    seen, out = set(), []
    for part in (v or "").split(","):
        p = part.strip()
        if p and p.lower() not in seen:
            seen.add(p.lower())
            out.append(p)
    return out


def db_error_text(e: DBAPIError) -> str:
    orig = getattr(e, "orig", None)
    diag = getattr(orig, "diag", None)
    if diag is not None and diag.message_primary:
        msg = diag.message_primary
        if diag.constraint_name:
            msg += f" [constraint {diag.constraint_name}]"
        if diag.message_detail:
            msg += f" - {diag.message_detail}"
        return "Database rejected the change: " + msg
    return "Database error: " + str(orig or e)


def transaction(fn):
    try:
        with engine.begin() as conn:
            return True, fn(conn)
    except CheckError as e:
        flash(str(e), "error")
    except DBAPIError as e:
        flash(db_error_text(e), "error")
    return False, None


def ref_data():
    return {
        "conferences": q("SELECT conference_id, acronym, city FROM conference ORDER BY conference_id"),
        "tracks": q("""SELECT t.track_id, t.name, c.acronym, t.conference_id
                       FROM track t JOIN conference c USING (conference_id)
                       ORDER BY t.conference_id, t.track_id"""),
        "sessions": q("""SELECT s.session_id, s.title, c.acronym, s.conference_id
                         FROM conference_session s JOIN conference c USING (conference_id)
                         ORDER BY s.conference_id, s.session_id"""),
        "authors": q("""SELECT a.author_id, u.given_name || ' ' || u.surname AS name, u.email
                        FROM author a JOIN app_user u ON u.user_id = a.author_id
                        ORDER BY u.surname, u.given_name"""),
        "reviewers": q("""SELECT r.reviewer_id, u.given_name || ' ' || u.surname AS name, u.email
                          FROM reviewer r JOIN app_user u ON u.user_id = r.reviewer_id
                          ORDER BY u.surname, u.given_name"""),
        "papers": q("""SELECT p.paper_id, p.title, p.status, c.acronym
                       FROM paper p JOIN track t USING (track_id)
                       JOIN conference c ON c.conference_id = t.conference_id
                       ORDER BY p.paper_id"""),
        "statuses": STATUSES,
    }


@app.route("/")
def index():
    counts = q("""SELECT
        (SELECT COUNT(*) FROM app_user) AS users, (SELECT COUNT(*) FROM paper) AS papers,
        (SELECT COUNT(*) FROM review) AS reviews, (SELECT COUNT(*) FROM conference_session) AS sessions,
        (SELECT COUNT(*) FROM conference) AS conferences""")[0]
    return render_template("index.html", counts=counts)


@app.route("/conferences")
def conferences():
    confs = q("""SELECT c.*, (SELECT string_agg(host_name, '; ' ORDER BY host_name)
                              FROM conference_host h WHERE h.conference_id = c.conference_id) AS hosts
                 FROM conference c ORDER BY conference_id""")
    tracks = q("""SELECT t.*, c.acronym, u.given_name || ' ' || u.surname AS coordinator
                  FROM track t JOIN conference c USING (conference_id)
                  JOIN app_user u ON u.user_id = t.coordinator_id ORDER BY track_id""")
    pools = q("""SELECT c.acronym, u.user_id, u.given_name || ' ' || u.surname AS name
                 FROM conference_reviewer cr JOIN conference c USING (conference_id)
                 JOIN app_user u ON u.user_id = cr.reviewer_id
                 ORDER BY c.conference_id, u.user_id""")
    return render_template("conferences.html", confs=confs, tracks=tracks, pools=pools)


@app.route("/schedule")
def schedule():
    rows = q("""SELECT * FROM accepted_paper_schedule
                ORDER BY conference_id, session_date, start_time, session_id, paper_id""")
    return render_template("schedule.html", rows=rows)


@app.route("/users")
def users():
    rows = q("""SELECT u.*, a.author_id IS NOT NULL AS is_author, r.reviewer_id IS NOT NULL AS is_reviewer
                FROM app_user u
                LEFT JOIN author a ON a.author_id = u.user_id
                LEFT JOIN reviewer r ON r.reviewer_id = u.user_id
                ORDER BY u.user_id""")
    return render_template("users.html", rows=rows)


def load_user_form(uid):
    u = q1("SELECT * FROM app_user WHERE user_id = :id", id=uid)
    if u is None:
        return None
    a = q1("SELECT * FROM author WHERE author_id = :id", id=uid)
    r = q1("SELECT * FROM reviewer WHERE reviewer_id = :id", id=uid)
    form = dict(u)
    form["is_author"] = a is not None
    form["orcid"] = a["orcid"] if a else ""
    form["research_areas"] = ", ".join(x["area_label"] for x in q(
        "SELECT area_label FROM author_research_area WHERE author_id=:id ORDER BY area_label", id=uid))
    form["is_reviewer"] = r is not None
    form["years_experience"] = r["years_experience"] if r else ""
    form["expertise"] = ", ".join(x["area_label"] for x in q(
        "SELECT area_label FROM reviewer_expertise WHERE reviewer_id=:id ORDER BY area_label", id=uid))
    form["pools"] = [x["conference_id"] for x in q(
        "SELECT conference_id FROM conference_reviewer WHERE reviewer_id=:id", id=uid)]
    return form


def save_user(conn, uid, f):
    is_author = f.get("is_author") == "on"
    is_reviewer = f.get("is_reviewer") == "on"
    if not (is_author or is_reviewer):
        raise CheckError("Every user must have the author role, the reviewer role, or both.")
    p = {k: none_if_blank(f.get(k)) for k in
         ("given_name", "surname", "email", "affiliation", "country", "phone_number")}
    if uid is None:
        uid = conn.execute(text("""
            INSERT INTO app_user (given_name, surname, email, affiliation, country, phone_number)
            VALUES (:given_name, :surname, :email, :affiliation, :country, :phone_number)
            RETURNING user_id"""), p).scalar_one()
    else:
        conn.execute(text("""
            UPDATE app_user SET given_name=:given_name, surname=:surname, email=:email,
                   affiliation=:affiliation, country=:country, phone_number=:phone_number
            WHERE user_id=:uid"""), {**p, "uid": uid})

    if is_author:
        areas = split_labels(f.get("research_areas"))
        if not areas:
            raise CheckError("An author needs at least one research area.")
        conn.execute(text("""INSERT INTO author (author_id, orcid) VALUES (:id, :orcid)
                             ON CONFLICT (author_id) DO UPDATE SET orcid = EXCLUDED.orcid"""),
                     {"id": uid, "orcid": none_if_blank(f.get("orcid"))})
        conn.execute(text("DELETE FROM author_research_area WHERE author_id=:id"), {"id": uid})
        for a in areas:
            conn.execute(text("INSERT INTO author_research_area VALUES (:id, :a)"), {"id": uid, "a": a})
    else:
        conn.execute(text("DELETE FROM author WHERE author_id=:id"), {"id": uid})

    if is_reviewer:
        exp = split_labels(f.get("expertise"))
        if not exp:
            raise CheckError("A reviewer needs at least one expertise area.")
        years = to_int(f.get("years_experience"), "Years of experience")
        conn.execute(text("""INSERT INTO reviewer (reviewer_id, years_experience) VALUES (:id, :y)
                             ON CONFLICT (reviewer_id) DO UPDATE SET years_experience = EXCLUDED.years_experience"""),
                     {"id": uid, "y": years})
        conn.execute(text("DELETE FROM reviewer_expertise WHERE reviewer_id=:id"), {"id": uid})
        for a in exp:
            conn.execute(text("INSERT INTO reviewer_expertise VALUES (:id, :a)"), {"id": uid, "a": a})
        pools = [int(x) for x in f.getlist("pools")]
        conn.execute(text("""DELETE FROM conference_reviewer
                             WHERE reviewer_id=:id AND NOT (conference_id = ANY(:pools))"""),
                     {"id": uid, "pools": pools})
        for c in pools:
            conn.execute(text("""INSERT INTO conference_reviewer VALUES (:c, :id)
                                 ON CONFLICT DO NOTHING"""), {"c": c, "id": uid})
    else:
        conn.execute(text("DELETE FROM reviewer WHERE reviewer_id=:id"), {"id": uid})
    return uid


@app.route("/users/new", methods=["GET", "POST"])
@app.route("/users/<int:uid>/edit", methods=["GET", "POST"])
def user_form(uid=None):
    if request.method == "POST":
        ok, new_id = transaction(lambda c: save_user(c, uid, request.form))
        if ok:
            flash(f"User {new_id} saved.", "ok")
            return redirect(url_for("user_detail", uid=new_id))
        form = request.form.to_dict()
        form["is_author"] = request.form.get("is_author") == "on"
        form["is_reviewer"] = request.form.get("is_reviewer") == "on"
        form["pools"] = [int(x) for x in request.form.getlist("pools")]
    else:
        form = load_user_form(uid) if uid else {"pools": []}
        if form is None:
            flash("User not found.", "error")
            return redirect(url_for("users"))
    return render_template("user_form.html", form=form, uid=uid, **ref_data())


@app.route("/users/<int:uid>")
def user_detail(uid):
    form = load_user_form(uid)
    if form is None:
        flash("User not found.", "error")
        return redirect(url_for("users"))
    papers = q("""SELECT p.paper_id, p.title, p.status, pa.author_position, pa.is_corresponding
                  FROM paper_author pa JOIN paper p USING (paper_id)
                  WHERE pa.author_id=:id ORDER BY p.paper_id""", id=uid)
    reviews = q("""SELECT r.review_id, r.paper_id, p.title, r.overall_score, r.recommendation
                   FROM review r JOIN paper p USING (paper_id)
                   WHERE r.reviewer_id=:id ORDER BY r.review_id""", id=uid)
    pools = q("""SELECT c.acronym FROM conference_reviewer cr JOIN conference c USING (conference_id)
                 WHERE cr.reviewer_id=:id ORDER BY c.conference_id""", id=uid)
    return render_template("user_detail.html", u=form, uid=uid, papers=papers,
                           reviews=reviews, pools=pools)


@app.route("/users/<int:uid>/delete", methods=["POST"])
def user_delete(uid):
    ok, n = transaction(lambda c: c.execute(
        text("DELETE FROM app_user WHERE user_id=:id"), {"id": uid}).rowcount)
    if ok:
        flash(f"User {uid} deleted." if n else "User not found.", "ok" if n else "error")
        return redirect(url_for("users"))
    return redirect(url_for("user_detail", uid=uid))


@app.route("/papers")
def papers():
    rows = q("""SELECT p.paper_id, p.title, p.status, p.session_id, t.name AS track, c.acronym,
                       u.given_name || ' ' || u.surname AS corresponding
                FROM paper p JOIN track t USING (track_id)
                JOIN conference c ON c.conference_id = t.conference_id
                LEFT JOIN paper_author pa ON pa.paper_id = p.paper_id AND pa.is_corresponding
                LEFT JOIN app_user u ON u.user_id = pa.author_id
                ORDER BY p.paper_id""")
    return render_template("papers.html", rows=rows)


def load_paper_form(pid):
    p = q1("SELECT * FROM paper WHERE paper_id=:id", id=pid)
    if p is None:
        return None
    form = dict(p)
    auths = q("""SELECT author_id, is_corresponding FROM paper_author
                 WHERE paper_id=:id ORDER BY author_position""", id=pid)
    form["author_ids"] = [a["author_id"] for a in auths] + [None] * (AUTHOR_ROWS - len(auths))
    form["corresponding"] = next((i for i, a in enumerate(auths) if a["is_corresponding"]), 0)
    form["keywords"] = ", ".join(k["keyword"] for k in q(
        "SELECT keyword FROM paper_keyword WHERE paper_id=:id ORDER BY keyword", id=pid))
    return form


def save_paper(conn, pid, f):
    # authors: rows in display order -> positions 1..n
    rows = [to_int(f.get(f"author_{i}"), "Author") for i in range(AUTHOR_ROWS)]
    corr_row = to_int(f.get("corresponding"), "Corresponding author")
    author_ids, corr_index = [], None
    for i, aid in enumerate(rows):
        if aid is not None:
            if i == corr_row:
                corr_index = len(author_ids)
            author_ids.append(aid)
    check_paper_authors(author_ids, corr_index)

    p = {"track_id": to_int(f.get("track_id"), "Track"),
         "title": none_if_blank(f.get("title")),
         "abstract": none_if_blank(f.get("abstract")),
         "submission_date": none_if_blank(f.get("submission_date")),
         "status": none_if_blank(f.get("status")),
         "session_id": to_int(f.get("session_id"), "Session")}
    # Check 2 (status part) before touching the row, so the message is clear
    if p["session_id"] is not None and p["status"] != "accepted":
        raise CheckError(f"Invalid session assignment: only accepted papers can be scheduled "
                         f"(status is '{p['status']}'). Clear the session or set status to accepted.")
    if pid is None:
        pid = conn.execute(text("""
            INSERT INTO paper (track_id, title, abstract, submission_date, status, session_id)
            VALUES (:track_id, :title, :abstract, :submission_date, :status, NULL)
            RETURNING paper_id"""), p).scalar_one()
        file_location = none_if_blank(f.get("file_location"))
        if not file_location:
            raise CheckError("A new paper needs a file location for version 1.")
        conn.execute(text("""INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at)
                             VALUES (:pid, 1, :loc, CURRENT_TIMESTAMP)"""),
                     {"pid": pid, "loc": file_location})
    else:
        conn.execute(text("""
            UPDATE paper SET track_id=:track_id, title=:title, abstract=:abstract,
                   submission_date=:submission_date, status=:status, session_id=NULL
            WHERE paper_id=:pid"""), {**p, "pid": pid})

    conn.execute(text("UPDATE paper SET session_id=:sid WHERE paper_id=:pid"),
                 {"sid": p["session_id"], "pid": pid})
    check_paper_session(conn, pid)             # same-conference rule

    conn.execute(text("DELETE FROM paper_author WHERE paper_id=:pid"), {"pid": pid})
    for pos, aid in enumerate(author_ids, start=1):
        conn.execute(text("""INSERT INTO paper_author (paper_id, author_id, author_position, is_corresponding)
                             VALUES (:pid, :aid, :pos, :corr)"""),
                     {"pid": pid, "aid": aid, "pos": pos, "corr": pos - 1 == corr_index})
    check_no_self_review(conn, pid)            # check 1 when authors change

    kws = split_labels(f.get("keywords"))
    if not kws:
        raise CheckError("A paper needs at least one keyword.")
    conn.execute(text("DELETE FROM paper_keyword WHERE paper_id=:pid"), {"pid": pid})
    for k in kws:
        conn.execute(text("INSERT INTO paper_keyword VALUES (:pid, :k)"), {"pid": pid, "k": k})
    return pid


@app.route("/papers/new", methods=["GET", "POST"])
@app.route("/papers/<int:pid>/edit", methods=["GET", "POST"])
def paper_form(pid=None):
    if request.method == "POST":
        ok, new_id = transaction(lambda c: save_paper(c, pid, request.form))
        if ok:
            flash(f"Paper {new_id} saved.", "ok")
            return redirect(url_for("paper_detail", pid=new_id))
        form = request.form.to_dict()
        form["author_ids"] = [to_int_safe(request.form.get(f"author_{i}")) for i in range(AUTHOR_ROWS)]
        form["corresponding"] = to_int_safe(request.form.get("corresponding"))
        form["track_id"] = to_int_safe(form.get("track_id"))
        form["session_id"] = to_int_safe(form.get("session_id"))
    else:
        if pid:
            form = load_paper_form(pid)
            if form is None:
                flash("Paper not found.", "error")
                return redirect(url_for("papers"))
        else:
            form = {"author_ids": [None] * AUTHOR_ROWS, "corresponding": 0, "status": "submitted",
                    "submission_date": datetime.now().date().isoformat()}
    return render_template("paper_form.html", form=form, pid=pid, author_rows=AUTHOR_ROWS, **ref_data())


def to_int_safe(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


@app.route("/papers/<int:pid>")
def paper_detail(pid):
    p = q1("""SELECT p.*, t.name AS track, c.acronym, c.conference_id, s.title AS session_title
              FROM paper p JOIN track t USING (track_id)
              JOIN conference c ON c.conference_id = t.conference_id
              LEFT JOIN conference_session s ON s.session_id = p.session_id
              WHERE p.paper_id=:id""", id=pid)
    if p is None:
        flash("Paper not found.", "error")
        return redirect(url_for("papers"))
    authors = q("""SELECT pa.*, u.given_name || ' ' || u.surname AS name, u.email
                   FROM paper_author pa JOIN app_user u ON u.user_id = pa.author_id
                   WHERE pa.paper_id=:id ORDER BY pa.author_position""", id=pid)
    keywords = q("SELECT keyword FROM paper_keyword WHERE paper_id=:id ORDER BY keyword", id=pid)
    versions = q("SELECT * FROM paper_version WHERE paper_id=:id ORDER BY version_no DESC", id=pid)
    reviews = q("""SELECT r.*, u.given_name || ' ' || u.surname AS reviewer
                   FROM review r JOIN app_user u ON u.user_id = r.reviewer_id
                   WHERE r.paper_id=:id ORDER BY r.review_id""", id=pid)
    next_v = (max([v["version_no"] for v in versions]) + 1) if versions else 1
    return render_template("paper_detail.html", p=p, authors=authors, keywords=keywords,
                           versions=versions, reviews=reviews, next_v=next_v)


@app.route("/papers/<int:pid>/delete", methods=["POST"])
def paper_delete(pid):
    ok, n = transaction(lambda c: c.execute(
        text("DELETE FROM paper WHERE paper_id=:id"), {"id": pid}).rowcount)
    if ok:
        flash(f"Paper {pid} deleted (versions, authorship, keywords and reviews cascaded).", "ok")
        return redirect(url_for("papers"))
    return redirect(url_for("paper_detail", pid=pid))


@app.route("/papers/<int:pid>/versions", methods=["POST"])
def version_add(pid):
    f = request.form
    ok, _ = transaction(lambda c: c.execute(text("""
        INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note)
        VALUES (:pid, :v, :loc, COALESCE(CAST(:at AS TIMESTAMP), CURRENT_TIMESTAMP), :note)"""),
        {"pid": pid, "v": to_int(f.get("version_no"), "Version number"),
         "loc": none_if_blank(f.get("file_location")), "at": none_if_blank(f.get("uploaded_at")),
         "note": none_if_blank(f.get("change_note"))}))
    if ok:
        flash("Version added.", "ok")
    return redirect(url_for("paper_detail", pid=pid))


@app.route("/papers/<int:pid>/versions/<int:v>/edit", methods=["POST"])
def version_edit(pid, v):
    f = request.form
    ok, _ = transaction(lambda c: c.execute(text("""
        UPDATE paper_version SET file_location=:loc, change_note=:note,
               uploaded_at = COALESCE(CAST(:at AS TIMESTAMP), uploaded_at)
        WHERE paper_id=:pid AND version_no=:v"""),
        {"pid": pid, "v": v, "loc": none_if_blank(f.get("file_location")),
         "note": none_if_blank(f.get("change_note")), "at": none_if_blank(f.get("uploaded_at"))}))
    if ok:
        flash(f"Version {v} updated.", "ok")
    return redirect(url_for("paper_detail", pid=pid))


@app.route("/papers/<int:pid>/versions/<int:v>/delete", methods=["POST"])
def version_delete(pid, v):
    def do(conn):
        n = conn.execute(text("SELECT COUNT(*) FROM paper_version WHERE paper_id=:pid"),
                         {"pid": pid}).scalar_one()
        if n <= 1:
            raise CheckError("A paper must keep at least one version.")
        conn.execute(text("DELETE FROM paper_version WHERE paper_id=:pid AND version_no=:v"),
                     {"pid": pid, "v": v})
    ok, _ = transaction(do)
    if ok:
        flash(f"Version {v} deleted.", "ok")
    return redirect(url_for("paper_detail", pid=pid))


@app.route("/reviews")
def reviews():
    rows = q("""SELECT r.review_id, r.paper_id, p.title, r.reviewer_id,
                       u.given_name || ' ' || u.surname AS reviewer,
                       r.overall_score, r.recommendation, r.review_submission_date
                FROM review r JOIN paper p USING (paper_id)
                JOIN app_user u ON u.user_id = r.reviewer_id
                ORDER BY r.review_id""")
    return render_template("reviews.html", rows=rows)


def save_review(conn, rid, f):
    p = {"paper_id": to_int(f.get("paper_id"), "Paper"),
         "reviewer_id": to_int(f.get("reviewer_id"), "Reviewer"),
         "overall_score": to_int(f.get("overall_score"), "Overall score"),
         "recommendation": none_if_blank(f.get("recommendation")),
         "comments_for_authors": none_if_blank(f.get("comments_for_authors")),
         "confidential_comments": none_if_blank(f.get("confidential_comments")),
         "review_submission_date": none_if_blank(f.get("review_submission_date"))}
    if rid is None:
        rid = conn.execute(text("""
            INSERT INTO review (paper_id, reviewer_id, overall_score, recommendation,
                                comments_for_authors, confidential_comments, review_submission_date)
            VALUES (:paper_id, :reviewer_id, :overall_score, :recommendation,
                    :comments_for_authors, :confidential_comments, :review_submission_date)
            RETURNING review_id"""), p).scalar_one()
    else:
        conn.execute(text("""
            UPDATE review SET paper_id=:paper_id, reviewer_id=:reviewer_id,
                   overall_score=:overall_score, recommendation=:recommendation,
                   comments_for_authors=:comments_for_authors,
                   confidential_comments=:confidential_comments,
                   review_submission_date=:review_submission_date
            WHERE review_id=:rid"""), {**p, "rid": rid})
    check_no_self_review(conn, p["paper_id"])                       # check 1
    check_reviewer_in_pool(conn, p["paper_id"], p["reviewer_id"])   # optional rule
    return rid


@app.route("/reviews/new", methods=["GET", "POST"])
@app.route("/reviews/<int:rid>/edit", methods=["GET", "POST"])
def review_form(rid=None):
    if request.method == "POST":
        ok, new_id = transaction(lambda c: save_review(c, rid, request.form))
        if ok:
            flash(f"Review {new_id} saved.", "ok")
            return redirect(url_for("reviews"))
        form = request.form.to_dict()
        for k in ("paper_id", "reviewer_id", "overall_score"):
            form[k] = to_int_safe(form.get(k))
    elif rid:
        form = q1("SELECT * FROM review WHERE review_id=:id", id=rid)
        if form is None:
            flash("Review not found.", "error")
            return redirect(url_for("reviews"))
    else:
        form = {"paper_id": to_int_safe(request.args.get("paper_id")),
                "review_submission_date": datetime.now().date().isoformat()}
    return render_template("review_form.html", form=form, rid=rid, **ref_data())


@app.route("/reviews/<int:rid>/delete", methods=["POST"])
def review_delete(rid):
    ok, n = transaction(lambda c: c.execute(
        text("DELETE FROM review WHERE review_id=:id"), {"id": rid}).rowcount)
    if ok:
        flash(f"Review {rid} deleted.", "ok")
    return redirect(url_for("reviews"))


@app.route("/sessions")
def sessions():
    rows = q("""SELECT s.*, c.acronym, c.city, u.given_name || ' ' || u.surname AS chair,
                       (SELECT COUNT(*) FROM paper p WHERE p.session_id = s.session_id) AS papers
                FROM conference_session s JOIN conference c USING (conference_id)
                JOIN app_user u ON u.user_id = s.chair_id
                ORDER BY s.conference_id, s.session_date, s.start_time""")
    return render_template("sessions.html", rows=rows)


def save_session(conn, sid, f):
    p = {"conference_id": to_int(f.get("conference_id"), "Conference"),
         "title": none_if_blank(f.get("title")),
         "session_date": none_if_blank(f.get("session_date")),
         "start_time": none_if_blank(f.get("start_time")),
         "end_time": none_if_blank(f.get("end_time")),
         "room_label": none_if_blank(f.get("room_label")),
         "chair_id": to_int(f.get("chair_id"), "Chair")}
    if sid is None:
        sid = conn.execute(text("""
            INSERT INTO conference_session (conference_id, title, session_date, start_time,
                                            end_time, room_label, chair_id)
            VALUES (:conference_id, :title, :session_date, :start_time, :end_time,
                    :room_label, :chair_id)
            RETURNING session_id"""), p).scalar_one()
    else:
        conn.execute(text("""
            UPDATE conference_session SET conference_id=:conference_id, title=:title,
                   session_date=:session_date, start_time=:start_time, end_time=:end_time,
                   room_label=:room_label, chair_id=:chair_id
            WHERE session_id=:sid"""), {**p, "sid": sid})
        check_session_papers(conn, sid)          # check 2 when the session's conference changes
    return sid


@app.route("/sessions/new", methods=["GET", "POST"])
@app.route("/sessions/<int:sid>/edit", methods=["GET", "POST"])
def session_form(sid=None):
    if request.method == "POST":
        ok, new_id = transaction(lambda c: save_session(c, sid, request.form))
        if ok:
            flash(f"Session {new_id} saved.", "ok")
            return redirect(url_for("session_detail", sid=new_id))
        form = request.form.to_dict()
        for k in ("conference_id", "chair_id"):
            form[k] = to_int_safe(form.get(k))
    elif sid:
        form = q1("SELECT * FROM conference_session WHERE session_id=:id", id=sid)
        if form is None:
            flash("Session not found.", "error")
            return redirect(url_for("sessions"))
        form = dict(form)
        form["start_time"] = form["start_time"].strftime("%H:%M")
        form["end_time"] = form["end_time"].strftime("%H:%M")
    else:
        form = {}
    return render_template("session_form.html", form=form, sid=sid, **ref_data())


@app.route("/sessions/<int:sid>")
def session_detail(sid):
    s = q1("""SELECT s.*, c.acronym, c.city, u.given_name || ' ' || u.surname AS chair
              FROM conference_session s JOIN conference c USING (conference_id)
              JOIN app_user u ON u.user_id = s.chair_id WHERE s.session_id=:id""", id=sid)
    if s is None:
        flash("Session not found.", "error")
        return redirect(url_for("sessions"))
    papers = q("""SELECT p.paper_id, p.title, p.status, t.name AS track
                  FROM paper p JOIN track t USING (track_id)
                  WHERE p.session_id=:id ORDER BY p.paper_id""", id=sid)
    return render_template("session_detail.html", s=s, papers=papers,
                           papers_ref=ref_data()["papers"])


@app.route("/sessions/<int:sid>/assign", methods=["POST"])
def session_assign(sid):
    pid = to_int_safe(request.form.get("paper_id"))

    def do(conn):
        st = conn.execute(text("SELECT status FROM paper WHERE paper_id=:p"), {"p": pid}).scalar()
        if st is None:
            raise CheckError("Paper not found.")
        if st != "accepted":
            raise CheckError(f"Invalid session assignment: paper {pid} has status '{st}'; "
                             f"only accepted papers can be scheduled.")
        conn.execute(text("UPDATE paper SET session_id=:s WHERE paper_id=:p"), {"s": sid, "p": pid})
        check_paper_session(conn, pid)                 # check 2
    ok, _ = transaction(do)
    if ok:
        flash(f"Paper {pid} assigned to session {sid}.", "ok")
    return redirect(url_for("session_detail", sid=sid))


@app.route("/sessions/<int:sid>/unassign/<int:pid>", methods=["POST"])
def session_unassign(sid, pid):
    ok, _ = transaction(lambda c: c.execute(text(
        "UPDATE paper SET session_id=NULL WHERE paper_id=:p AND session_id=:s"), {"p": pid, "s": sid}))
    if ok:
        flash(f"Paper {pid} removed from session {sid}.", "ok")
    return redirect(url_for("session_detail", sid=sid))


@app.route("/sessions/<int:sid>/delete", methods=["POST"])
def session_delete(sid):
    ok, _ = transaction(lambda c: c.execute(
        text("DELETE FROM conference_session WHERE session_id=:id"), {"id": sid}))
    if ok:
        flash(f"Session {sid} deleted (its papers became unscheduled).", "ok")
    return redirect(url_for("sessions"))


@app.route("/reset", methods=["POST"])
def reset():
    from init_db import init_db
    try:
        init_db(engine)
        flash("Database restored to the original seed data.", "ok")
    except DBAPIError as e:
        flash(db_error_text(e), "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
