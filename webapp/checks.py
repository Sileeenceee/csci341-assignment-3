from sqlalchemy import text


class CheckError(Exception):
    """A business rule was violated; message is shown to the user."""


def check_no_self_review(conn, paper_id):
    rows = conn.execute(text("""
        SELECT r.review_id, u.given_name || ' ' || u.surname AS name
        FROM review r
        JOIN paper_author pa ON pa.paper_id = r.paper_id AND pa.author_id = r.reviewer_id
        JOIN app_user u ON u.user_id = r.reviewer_id
        WHERE r.paper_id = :pid"""), {"pid": paper_id}).all()
    if rows:
        names = ", ".join(r.name for r in rows)
        raise CheckError(f"Self-review rejected: {names} authored paper {paper_id} "
                         f"and cannot review it.")


def check_paper_session(conn, paper_id):
    row = conn.execute(text("""
        SELECT p.paper_id, p.status, p.session_id,
               t.conference_id AS track_conf, s.conference_id AS session_conf
        FROM paper p
        JOIN track t ON t.track_id = p.track_id
        LEFT JOIN conference_session s ON s.session_id = p.session_id
        WHERE p.paper_id = :pid"""), {"pid": paper_id}).first()
    if row is None or row.session_id is None:
        return
    if row.status != "accepted":
        raise CheckError(f"Invalid session assignment: paper {paper_id} has status "
                         f"'{row.status}'; only accepted papers can be scheduled. "
                         f"Clear the session first.")
    if row.track_conf != row.session_conf:
        raise CheckError(f"Invalid session assignment: paper {paper_id}'s track belongs to "
                         f"conference {row.track_conf} but session {row.session_id} belongs "
                         f"to conference {row.session_conf}.")


def check_session_papers(conn, session_id):
    pids = conn.execute(text("SELECT paper_id FROM paper WHERE session_id = :sid"),
                        {"sid": session_id}).scalars().all()
    for pid in pids:
        check_paper_session(conn, pid)


def check_track_papers(conn, track_id):
    pids = conn.execute(text("SELECT paper_id FROM paper WHERE track_id = :tid"),
                        {"tid": track_id}).scalars().all()
    for pid in pids:
        check_paper_session(conn, pid)


def check_reviewer_in_pool(conn, paper_id, reviewer_id):
    ok = conn.execute(text("""
        SELECT 1 FROM paper p
        JOIN track t ON t.track_id = p.track_id
        JOIN conference_reviewer cr ON cr.conference_id = t.conference_id
                                   AND cr.reviewer_id = :rid
        WHERE p.paper_id = :pid"""), {"pid": paper_id, "rid": reviewer_id}).first()
    if not ok:
        raise CheckError(f"Reviewer {reviewer_id} is not in the reviewer pool of the "
                         f"conference of paper {paper_id}.")


def check_paper_authors(author_ids, corresponding_index):
    if not author_ids:
        raise CheckError("A paper needs at least one author.")
    if len(set(author_ids)) != len(author_ids):
        raise CheckError("The same author is listed twice.")
    if corresponding_index is None or not (0 <= corresponding_index < len(author_ids)):
        raise CheckError("Exactly one corresponding author must be selected among the listed authors.")
