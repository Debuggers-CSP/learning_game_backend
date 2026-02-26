# api/pseudocodeanswer_bank_api.py
from flask import Blueprint, request, jsonify, make_response
from model.pseudocodeanswer1_bank import PseudocodeAnswerBank
import os

pseudocodeanswer_bank_api = Blueprint(
    "pseudocodeanswer_bank_api",
    __name__,
    url_prefix="/api/pseudocodeanswer_bank"
)

_allowed = os.getenv("ALLOWED_ORIGINS", "").strip()
ALLOWED_ORIGINS = [o.strip() for o in _allowed.split(",") if o.strip()] or ["*"]


def _corsify(resp):
    origin = request.headers.get("Origin", "")
    if "*" in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
    else:
        if origin in ALLOWED_ORIGINS:
            resp.headers["Access-Control-Allow-Origin"] = origin

    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Vary"] = "Origin"
    resp.headers["Access-Control-Allow-Credentials"] = "false"
    return resp


def _no_cache(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@pseudocodeanswer_bank_api.route("/answer", methods=["OPTIONS"])
def answer_preflight():
    resp = make_response("", 204)
    resp = _no_cache(resp)
    resp = _corsify(resp)
    return resp


@pseudocodeanswer_bank_api.route("/answer", methods=["GET"])
def get_answer():
    qid = request.args.get("question_id", type=int)
    if not qid:
        resp = jsonify({"success": False, "message": "Missing question_id"})
        resp = _corsify(resp)
        resp = _no_cache(resp)
        return resp, 400

    row = PseudocodeAnswerBank.query.filter_by(question_id=qid).first()
    if not row:
        resp = jsonify({"success": False, "message": "Answer not found"})
        resp = _corsify(resp)
        resp = _no_cache(resp)
        return resp, 404

    resp = jsonify({
        "success": True,
        "question_id": qid,
        "level": row.level,
        "answer": row.answer
    })
    resp = _corsify(resp)
    resp = _no_cache(resp)
    return resp, 200