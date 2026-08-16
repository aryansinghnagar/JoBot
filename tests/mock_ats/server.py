from datetime import datetime, timezone
import hashlib
import uuid
from flask import Flask, jsonify, request
from tests.mock_ats.data import SAMPLE_JOBS

app = Flask(__name__)

# In-memory storage (reset on restart)
jobs = {}
applications = {}
verification_receipts = {}


def _seed_jobs():
    jobs.clear()
    applications.clear()
    verification_receipts.clear()
    for job in SAMPLE_JOBS:
        jobs[job["id"]] = job


_seed_jobs()


@app.route("/jobs", methods=["GET"])
def list_jobs():
    return jsonify({"jobs": list(jobs.values())})


@app.route("/jobs/<job_id>", methods=["GET"])
def get_job(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/apply", methods=["POST"])
def apply():
    data = request.get_json() or {}
    required = ["job_id", "name", "email"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    job = jobs.get(data["job_id"])
    if not job:
        return jsonify({"error": "Job not found"}), 404

    submission_id = str(uuid.uuid4())
    idempotency_key = hashlib.sha256(
        f"{data['job_id']}:{data['email']}".encode()
    ).hexdigest()

    if idempotency_key in applications:
        return jsonify({"error": "Duplicate application"}), 409

    now_iso = datetime.now(timezone.utc).isoformat()
    applications[idempotency_key] = {
        "submission_id": submission_id,
        "idempotency_key": idempotency_key,
        "job_id": data["job_id"],
        "name": data["name"],
        "email": data["email"],
        "phone": data.get("phone"),
        "resume": data.get("resume"),
        "submitted_at": now_iso,
        "status": "SUBMITTED",
    }

    receipt = {
        "submission_id": submission_id,
        "idempotency_key": idempotency_key,
        "status": "SUBMITTED",
        "submitted_at": now_iso,
        "signature": hashlib.sha256(
            f"{submission_id}:{idempotency_key}".encode()
        ).hexdigest(),
    }
    verification_receipts[submission_id] = receipt

    return jsonify(receipt), 200


@app.route("/verify/<submission_id>", methods=["GET"])
def verify(submission_id):
    receipt = verification_receipts.get(submission_id)
    if not receipt:
        return jsonify({"error": "Submission receipt not found"}), 404
    return jsonify(receipt), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5800, debug=False)
