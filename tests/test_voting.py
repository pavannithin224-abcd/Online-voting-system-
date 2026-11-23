import io, json, os, tempfile
os.environ["VOTING_DATA_FILE"] = os.path.join(tempfile.mkdtemp(), "d.json")
os.environ["VOTING_ADMIN_PASSWORD"] = "test-pass"
import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
import app as A

A.app.testing = True
A.voting_data.update({"candidates": ["a", "b"], "votes": {"a": 0, "b": 0}, "voted": []})
MATCH = {"v": True}
A.faces_match = lambda i, l: MATCH["v"]

def voter(img=b"ID-IMAGE-1"):
    c = A.app.test_client()
    c.post("/verify", data={"id_card": (io.BytesIO(img), "id.jpg")}, content_type="multipart/form-data")
    return c

def face(c):
    return c.post("/verify_face", data={"live_capture": (io.BytesIO(b"x"), "l.jpg")}, content_type="multipart/form-data")

def vote(c, who="a"):
    return c.post("/vote", json={"candidate": who})

def test_vote_requires_verification():
    c = A.app.test_client()
    assert vote(c).status_code == 403

def test_failed_face_cannot_vote():
    MATCH["v"] = False
    c = voter(b"ID-FAIL"); assert not face(c).get_json()["success"]
    assert vote(c).status_code == 403
    MATCH["v"] = True

def test_verified_voter_votes_once():
    c = voter(b"ID-A"); assert face(c).get_json()["success"]
    assert vote(c).status_code == 200
    assert vote(c).status_code == 403          # verification is single-use
    c2 = voter(b"ID-A")                        # same ID, new session
    assert face(c2).status_code == 403         # blocked before comparing
    assert vote(c2).status_code == 403
    assert A.voting_data["votes"]["a"] == 1

def test_second_person_can_vote():
    c = voter(b"ID-B"); face(c)
    assert vote(c, "b").status_code == 200
    assert A.voting_data["votes"]["b"] == 1

def test_unknown_candidate_rejected():
    c = voter(b"ID-C"); face(c)
    assert vote(c, "zzz").status_code == 400
    assert vote(c, "a").status_code == 200

def test_photos_deleted_after_verify():
    c = voter(b"ID-D"); assert c.get("/") .status_code == 200
    with c.session_transaction() as s: p = s["id_path"]
    assert os.path.exists(p); face(c); assert not os.path.exists(p)

def test_admin_auth():
    c = A.app.test_client()
    assert c.get("/results").status_code == 403
    c.post("/voting", data={"username": "admin", "password": "wrong"})
    assert c.get("/results").status_code == 403
    c.post("/voting", data={"username": "admin", "password": "test-pass"})
    r = c.get("/results"); assert r.status_code == 200 and r.get_json()["total_votes"] >= 2

def test_admin_disabled_without_password():
    A.ADMIN_PASSWORD = None
    c = A.app.test_client(); c.post("/voting", data={"username": "admin", "password": ""})
    assert c.get("/results").status_code == 403
    A.ADMIN_PASSWORD = "test-pass"
