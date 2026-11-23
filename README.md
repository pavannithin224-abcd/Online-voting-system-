# Smart Voting System

A Flask web app where a voter proves who they are with **face verification** before voting, and an admin sets up the election and watches the results. Built as an academic project and presented as a paper at ICEST 2026.

> **Status: academic prototype, not for real elections.** The voting logic has automated tests (below); face-matching accuracy has not been measured. See *Known limitations*.

## How it works

1. The voter uploads a photo of their ID card.
2. The browser captures a live webcam photo.
3. **DeepFace** compares the two faces and returns verified or not verified.
4. A verified voter reaches the voting page and picks a candidate. Voters never see the results.
5. The admin logs in to add candidates, set the election title and see live results.

| Route | Purpose |
|---|---|
| `/` | ID upload |
| `/verify`, `/verify_face` | Upload ID, then face match with DeepFace |
| `/voting` | Voter ballot, or admin dashboard after admin login |
| `/add_candidate`, `/set_title` | Admin only |
| `/results` | Admin only (JSON) |
| `/vote` | Records a vote |

Votes and candidates are stored in a local `voting_data.json`.

## Run it

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install flask deepface
set VOTING_ADMIN_PASSWORD=choose-a-password     # macOS/Linux: export ...
set VOTING_SECRET_KEY=any-long-random-string
python app.py
```

Open http://127.0.0.1:5000. The first face check downloads DeepFace's model weights, so it needs internet once.

| Variable | Purpose |
|---|---|
| `VOTING_ADMIN_PASSWORD` | Admin password. **Admin login is disabled until this is set.** |
| `VOTING_ADMIN_USER` | Admin username (default `admin`) |
| `VOTING_SECRET_KEY` | Flask session key (random per start if unset) |
| `VOTING_DEBUG=1` | Enable Flask debug mode (off by default) |

## How one vote per person is enforced

- A vote is accepted only from a session that just passed face verification, and each verification is good for **one** ballot.
- The ID card image is fingerprinted (SHA-256) and the fingerprint is stored with the votes. A second vote from the same ID is refused (HTTP 409), even from a new session.
- ID and webcam photos live in per-request temp files and are **deleted right after the face comparison**.
- Admin routes check the admin session; results are not visible to voters.

## Tests

```bash
pip install pytest
python -m pytest tests
```

8 tests cover: no vote without verification, failed face cannot vote, one vote per ID (including a new session), a second person can still vote, unknown candidate rejected, photos deleted after verification, admin auth, and admin login disabled without a password. Face matching is stubbed in the tests, so they check the voting logic, not DeepFace's accuracy.

## Known limitations (read before reusing)

- **The voter fingerprint is a hash of the ID image bytes.** A different photo of the same card gives a different hash, so one person could vote again. A real system needs a voter roll or the ID number checked against a registry.
- Face matching has **no liveness check**: a photo of a face could fool it. Accuracy has not been measured.
- Votes are stored in plain JSON (`voting_data.json`) with no encryption or audit log.
- No HTTPS and no rate limiting. Use only for demos, class elections or learning.

## Planned improvements

Voter roll with ID-number checks, SQLite instead of JSON, liveness detection, encrypted vote storage, audit log, multi-election support.

## Tech

Python, Flask, DeepFace, HTML/CSS/JavaScript, JSON storage.

*Author: Pavan D, [GitHub](https://github.com/pavannithin224-abcd).*
