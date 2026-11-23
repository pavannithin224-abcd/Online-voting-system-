import hashlib
import hmac
import json
import os
import secrets
import tempfile

from flask import Flask, render_template, request, jsonify, session, redirect, url_for

app = Flask(__name__)
# Secrets come from the environment. A random key is generated if none is set (sessions reset on restart).
app.secret_key = os.environ.get("VOTING_SECRET_KEY") or secrets.token_hex(32)
ADMIN_USER = os.environ.get("VOTING_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("VOTING_ADMIN_PASSWORD")  # no default: admin login is disabled until set

DATA_FILE = os.environ.get("VOTING_DATA_FILE", "voting_data.json")


def new_data():
    return {"title": "Election 2025", "candidates": [], "votes": {}, "voted": []}


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        data.setdefault("voted", [])
        return data
    return new_data()


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


voting_data = load_data()


def faces_match(id_path, live_path):
    """Face comparison. Imported lazily so the rest of the app (and tests) run without DeepFace."""
    from deepface import DeepFace
    return bool(DeepFace.verify(img1_path=id_path, img2_path=live_path).get("verified"))


def voter_key(id_bytes):
    """Stable fingerprint of the ID card image. Used to block a second vote; the image itself is not kept."""
    return hashlib.sha256(id_bytes).hexdigest()


# -----------------------
# FACE VERIFICATION FLOW
# -----------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/verify", methods=["POST"])
def verify():
    id_card = request.files.get("id_card")
    if not id_card:
        return "No ID card uploaded", 400
    data = id_card.read()
    if not data:
        return "Empty ID card upload", 400
    # Per-request temp file, so voters never overwrite each other's image.
    fd, path = tempfile.mkstemp(suffix=".jpg")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    old = session.pop("id_path", None)
    if old and os.path.exists(old):
        os.remove(old)
    session["id_path"] = path
    session["voter_key"] = voter_key(data)
    session["verified"] = False
    return render_template("verify.html")


@app.route("/verify_face", methods=["POST"])
def verify_face():
    id_path = session.get("id_path")
    if not id_path or not os.path.exists(id_path):
        return jsonify({"success": False, "message": "Upload your ID card first."}), 400
    live_capture = request.files.get("live_capture")
    if not live_capture:
        return jsonify({"success": False, "message": "No live photo received."}), 400
    if voter_key_voted(session.get("voter_key")):
        return jsonify({"success": False, "message": "This ID has already voted."}), 403
    fd, live_path = tempfile.mkstemp(suffix=".jpg")
    with os.fdopen(fd, "wb") as f:
        f.write(live_capture.read())
    try:
        ok = faces_match(id_path, live_path)
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})
    finally:
        # Face photos are deleted straight after the comparison.
        for p in (live_path, id_path):
            if os.path.exists(p):
                os.remove(p)
        session.pop("id_path", None)
    session["verified"] = ok
    if ok:
        return jsonify({"success": True, "message": "Face verified successfully!"})
    return jsonify({"success": False, "message": "Face verification failed!"})


def voter_key_voted(key):
    return bool(key) and key in voting_data["voted"]


# -----------------------
# VOTING LOGIC
# -----------------------

@app.route("/voting", methods=["GET", "POST"])
def voting():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if ADMIN_PASSWORD and hmac.compare_digest(username, ADMIN_USER) and hmac.compare_digest(password, ADMIN_PASSWORD):
            session["role"] = "admin"
            return redirect(url_for("voting"))
        return render_template("voting.html", role="voter", voting_data=voting_data, login_failed=True)

    role = session.get("role", "voter")
    return render_template("voting.html", role=role, voting_data=voting_data)


@app.route("/logout")
def logout():
    session.pop("role", None)
    return redirect(url_for("voting"))


@app.route("/add_candidate", methods=["POST"])
def add_candidate():
    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    name = (request.json or {}).get("name")
    if name and name not in voting_data["candidates"]:
        voting_data["candidates"].append(name)
        voting_data["votes"][name] = 0
        save_data(voting_data)
    return jsonify(voting_data)


@app.route("/set_title", methods=["POST"])
def set_title():
    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    title = (request.json or {}).get("title")
    if title:
        voting_data["title"] = title
        save_data(voting_data)
    return jsonify(voting_data)


@app.route("/vote", methods=["POST"])
def vote():
    # A vote needs a successful face verification in this session, and each ID can vote once.
    if not session.get("verified"):
        return jsonify({"status": "error", "message": "Face verification required."}), 403
    key = session.get("voter_key")
    if voter_key_voted(key):
        return jsonify({"status": "error", "message": "This ID has already voted."}), 409
    name = (request.json or {}).get("candidate")
    if name not in voting_data["votes"]:
        return jsonify({"status": "error", "message": "Unknown candidate."}), 400
    voting_data["votes"][name] += 1
    voting_data["voted"].append(key)
    save_data(voting_data)
    session["verified"] = False  # one verification buys one ballot
    return jsonify({"status": "success"})


@app.route("/results")
def results():
    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    return jsonify({k: voting_data[k] for k in ("title", "candidates", "votes")} | {"total_votes": len(voting_data["voted"])})


if __name__ == "__main__":
    app.run(debug=os.environ.get("VOTING_DEBUG") == "1")
