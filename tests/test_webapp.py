import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from init_db import init_db
from webapp.app import app, engine
from sqlalchemy import text

init_db(engine)
c = app.test_client()
fails = 0

def check(name, cond):
    global fails
    print(("PASS " if cond else "FAIL ") + name)
    fails += not cond

def flashes(r):
    return re.findall(r'<div class="flash (\w+)">(.*?)</div>', r.get_data(as_text=True))

def scalar(sql, **p):
    with engine.connect() as conn:
        return conn.execute(text(sql), p).scalar()

for url in ["/", "/users", "/users/1", "/users/1/edit", "/users/new", "/papers", "/papers/1",
            "/papers/1/edit", "/papers/new", "/reviews", "/reviews/new", "/reviews/1/edit",
            "/sessions", "/sessions/1", "/sessions/1/edit", "/sessions/new", "/schedule", "/conferences"]:
    check(f"GET {url}", c.get(url).status_code == 200)

r = c.post("/users/new", data=dict(given_name="Test", surname="User", email="test.user@example.com",
     affiliation="NU", country="KZ", phone_number="+7700", is_reviewer="on", years_experience="2",
     expertise="Databases, Testing", pools=["1"]), follow_redirects=True)
uid = scalar("SELECT user_id FROM app_user WHERE email='test.user@example.com'")
check("create user (reviewer)", uid is not None and scalar("SELECT COUNT(*) FROM reviewer_expertise WHERE reviewer_id=:u", u=uid) == 2)
r = c.post(f"/users/{uid}/edit", data=dict(given_name="Test2", surname="User", email="test.user@example.com",
     affiliation="NU", country="KZ", phone_number="+7700", is_reviewer="on", is_author="on",
     research_areas="AI", years_experience="3", expertise="Databases", pools=["1", "2"]), follow_redirects=True)
check("update user (add author role)", scalar("SELECT COUNT(*) FROM author WHERE author_id=:u", u=uid) == 1
      and scalar("SELECT COUNT(*) FROM conference_reviewer WHERE reviewer_id=:u", u=uid) == 2)
r = c.post("/users/new", data=dict(given_name="X", surname="Y", email="arman.armanov@example.com",
     affiliation="a", country="b", phone_number="1", is_author="on", research_areas="x"), follow_redirects=True)
check("duplicate email rejected", any("uq_app_user_email" in m for _, m in flashes(r)))
r = c.post("/users/new", data=dict(given_name="X", surname="Y", email="noroles@example.com",
     affiliation="a", country="b", phone_number="1"), follow_redirects=True)
check("user without role rejected", any("author role" in m for _, m in flashes(r)))
r = c.post("/users/1/delete", follow_redirects=True)
check("delete referenced user rejected", scalar("SELECT COUNT(*) FROM app_user WHERE user_id=1") == 1
      and any(cat == "error" for cat, _ in flashes(r)))

base = dict(track_id="1", title="New Paper", abstract="abc", submission_date="2026-02-10",
            status="submitted", session_id="", keywords="k1, k2", file_location="papers/new/v1.pdf",
            author_0="8", author_1="1", corresponding="0")
r = c.post("/papers/new", data=base, follow_redirects=True)
pid = scalar("SELECT paper_id FROM paper WHERE title='New Paper'")
check("create paper with authors/keywords/version", pid is not None
      and scalar("SELECT COUNT(*) FROM paper_author WHERE paper_id=:p", p=pid) == 2
      and scalar("SELECT COUNT(*) FROM paper_version WHERE paper_id=:p", p=pid) == 1)
r = c.post(f"/papers/{pid}/edit", data={**base, "title": "New Paper v2", "status": "under review"}, follow_redirects=True)
check("update paper", scalar("SELECT title FROM paper WHERE paper_id=:p", p=pid) == "New Paper v2")
c.post(f"/papers/{pid}/versions", data=dict(version_no="3", file_location="papers/x/v3.pdf"))
check("add version (gap allowed)", scalar("SELECT COUNT(*) FROM paper_version WHERE paper_id=:p", p=pid) == 2)
c.post(f"/papers/{pid}/versions/3/edit", data=dict(file_location="papers/x/v3b.pdf", change_note="n"))
check("edit version", scalar("SELECT file_location FROM paper_version WHERE paper_id=:p AND version_no=3", p=pid) == "papers/x/v3b.pdf")
c.post(f"/papers/{pid}/versions/3/delete")
check("delete version", scalar("SELECT COUNT(*) FROM paper_version WHERE paper_id=:p", p=pid) == 1)

r = c.post("/reviews/new", data=dict(paper_id=str(pid), reviewer_id="5", overall_score="4",
     recommendation="accept", comments_for_authors="ok", review_submission_date="2026-03-01"), follow_redirects=True)
rid = scalar("SELECT review_id FROM review WHERE paper_id=:p AND reviewer_id=5", p=pid)
check("create review", rid is not None)
r = c.post("/reviews/new", data=dict(paper_id=str(pid), reviewer_id="8", overall_score="5",
     recommendation="accept", comments_for_authors="self", review_submission_date="2026-03-01"), follow_redirects=True)
check("CHECK 1: self-review on save rejected", any("Self-review" in m for _, m in flashes(r))
      and scalar("SELECT COUNT(*) FROM review WHERE paper_id=:p AND reviewer_id=8", p=pid) == 0)
r = c.post(f"/papers/{pid}/edit", data={**base, "author_2": "5"}, follow_redirects=True)
check("CHECK 1: adding reviewer as author rejected", any("Self-review" in m for _, m in flashes(r))
      and scalar("SELECT COUNT(*) FROM paper_author WHERE paper_id=:p", p=pid) == 2)
r = c.post("/reviews/new", data=dict(paper_id=str(pid), reviewer_id="7", overall_score="5",
     recommendation="accept", comments_for_authors="x", review_submission_date="2026-03-01"), follow_redirects=True)
check("reviewer outside pool rejected", any("pool" in m for _, m in flashes(r)))
r = c.post("/reviews/new", data=dict(paper_id=str(pid), reviewer_id="5", overall_score="9",
     recommendation="accept", comments_for_authors="x", review_submission_date="2026-03-01"), follow_redirects=True)
check("score 9 rejected (CHECK)", any("ck_review_score" in m or "uq_review" in m for _, m in flashes(r)))
c.post(f"/reviews/{rid}/edit", data=dict(paper_id=str(pid), reviewer_id="5", overall_score="2",
     recommendation="reject", comments_for_authors="changed", review_submission_date="2026-03-02"))
check("update review", scalar("SELECT overall_score FROM review WHERE review_id=:r", r=rid) == 2)
c.post(f"/reviews/{rid}/delete")
check("delete review", scalar("SELECT COUNT(*) FROM review WHERE review_id=:r", r=rid) == 0)

r = c.post("/sessions/new", data=dict(conference_id="1", title="Test Session", session_date="2026-06-17",
     start_time="16:00", end_time="17:00", room_label="C1", chair_id="3"), follow_redirects=True)
sid = scalar("SELECT session_id FROM conference_session WHERE title='Test Session'")
check("create session", sid is not None)
r = c.post("/sessions/new", data=dict(conference_id="1", title="Bad", session_date="2026-06-17",
     start_time="16:00", end_time="15:00", room_label="C1", chair_id="3"), follow_redirects=True)
check("end before start rejected", any("ck_session_times" in m for _, m in flashes(r)))
r = c.post(f"/sessions/{sid}/assign", data=dict(paper_id="7"), follow_redirects=True)   # submitted paper
check("CHECK 2: non-accepted paper rejected", any("only accepted" in m for _, m in flashes(r)))
r = c.post(f"/sessions/{sid}/assign", data=dict(paper_id="10"), follow_redirects=True)  # accepted, other conference
check("CHECK 2: other-conference paper rejected", any("belongs to conference" in m for _, m in flashes(r))
      and scalar("SELECT session_id FROM paper WHERE paper_id=10") == 3)
r = c.post(f"/sessions/{sid}/assign", data=dict(paper_id="3"), follow_redirects=True)   # accepted, conf 1
check("valid assignment", scalar("SELECT session_id FROM paper WHERE paper_id=3") == sid)
r = c.post(f"/sessions/{sid}/edit", data=dict(conference_id="2", title="Test Session", session_date="2026-06-17",
     start_time="16:00", end_time="17:00", room_label="C1", chair_id="3"), follow_redirects=True)
check("CHECK 2: changing session conference rejected", any("belongs to conference" in m for _, m in flashes(r))
      and scalar("SELECT conference_id FROM conference_session WHERE session_id=:s", s=sid) == 1)
p3 = dict(track_id="2", title="Feature Stores at Scale", abstract="x", submission_date="2026-02-05",
          status="rejected", session_id=str(sid), keywords="feature store", author_0="6", author_1="5",
          author_2="12", corresponding="0")
r = c.post("/papers/3/edit", data=p3, follow_redirects=True)
check("CHECK 2: status change of scheduled paper rejected", any("only accepted" in m for _, m in flashes(r))
      and scalar("SELECT status FROM paper WHERE paper_id=3") == "accepted")
r = c.post("/papers/3/edit", data={**p3, "status": "accepted", "track_id": "4"}, follow_redirects=True)
check("CHECK 2: track change to other conference rejected", any("belongs to conference" in m for _, m in flashes(r)))
c.post(f"/sessions/{sid}/edit", data=dict(conference_id="1", title="Renamed", session_date="2026-06-17",
     start_time="16:00", end_time="17:30", room_label="C1", chair_id="3"))
check("update session", scalar("SELECT title FROM conference_session WHERE session_id=:s", s=sid) == "Renamed")
c.post(f"/sessions/{sid}/delete")
check("delete session (paper unscheduled)", scalar("SELECT COUNT(*) FROM conference_session WHERE session_id=:s", s=sid) == 0
      and scalar("SELECT session_id FROM paper WHERE paper_id=3") is None)

c.post(f"/papers/{pid}/delete")
check("delete paper (cascade)", scalar("SELECT COUNT(*) FROM paper_version WHERE paper_id=:p", p=pid) == 0)
c.post(f"/users/{uid}/delete")
check("delete user", scalar("SELECT COUNT(*) FROM app_user WHERE user_id=:u", u=uid) == 0)

init_db(engine)
print("\nALL PASSED" if not fails else f"\n{fails} FAILED")
sys.exit(1 if fails else 0)
