from datetime import datetime
import json
import re
import time
from urllib.parse import quote

import requests
from flask import Blueprint, jsonify, request, current_app

from __init__ import db
from model.endgame import Player, Badge, PlayerBadge

endgame_api = Blueprint("endgame_api", __name__)


def _get_json():
    return request.get_json(silent=True) or {}


def _normalize_answer(answer: str) -> str:
    if not answer:
        return ""
    cleaned = answer.lower()
    cleaned = cleaned.replace("←", " ")
    cleaned = cleaned.replace("→", " ")
    cleaned = cleaned.replace("≥", ">=")
    cleaned = cleaned.replace("≤", "<=")
    cleaned = cleaned.replace("≠", "!=")
    cleaned = re.sub(r"[^a-z0-9_]+", " ", cleaned)
    return " ".join(cleaned.strip().split())


def _parse_iso(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _extract_json(text: str) -> dict:
    if not text:
        return {}
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def _strip_code_blocks(text: str) -> str:
    if not text:
        return ""
    # Remove fenced code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Remove inline code backticks
    text = re.sub(r"`([^`]*)`", r"\1", text)
    # Remove leftover double spaces
    return " ".join(text.split())


def _call_openai(prompt: str, text: str, strip_code_blocks: bool = True) -> str:
    api_key = current_app.config.get("OPENAI_API_KEY")
    model = current_app.config.get("OPENAI_MODEL") or "gpt-4o-mini"
    server = current_app.config.get("OPENAI_SERVER") or "https://api.openai.com/v1/chat/completions"
    if not api_key or not server:
        return ""

    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ]
    }

    try:
        response = requests.post(
            server,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json=payload,
            timeout=20
        )
        if response.status_code != 200:
            return ""
        openai_json = response.json()
        raw_text = openai_json["choices"][0]["message"]["content"]
        if strip_code_blocks:
            return _strip_code_blocks(raw_text)
        return (raw_text or "").strip()
    except (requests.RequestException, KeyError, IndexError, TypeError):
        return ""


def _find_video_url(payload):
    if isinstance(payload, str) and payload.startswith("http") and re.search(r"\.(mp4|mov|webm)(\?|$)", payload):
        return payload
    if isinstance(payload, dict):
        for value in payload.values():
            found = _find_video_url(value)
            if found:
                return found
    if isinstance(payload, list):
        for item in payload:
            found = _find_video_url(item)
            if found:
                return found
    return ""


def _call_pika_video(prompt: str) -> dict:
    api_key = current_app.config.get("PIKA_API_KEY")
    server = current_app.config.get("PIKA_SERVER")
    status_server = current_app.config.get("PIKA_STATUS_SERVER")
    model = current_app.config.get("PIKA_MODEL")
    if not api_key or not server:
        return {"success": False, "message": "Video generation is not configured (PIKA_SERVER/PIKA_API_KEY missing)"}

    payload = {"prompt": prompt}
    if model:
        payload["model"] = model

    try:
        response = requests.post(
            server,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json=payload,
            timeout=30
        )
        if response.status_code != 200:
            return {"success": False, "message": "PIKA request failed"}
        pika_json = response.json()
        video_url = _find_video_url(pika_json)
        if video_url:
            return {"success": True, "video_url": video_url}

        request_id = pika_json.get("id") or pika_json.get("request_id") or pika_json.get("job_id")
        status_url = pika_json.get("status_url")
        if request_id and status_server and not status_url:
            status_url = f"{status_server.rstrip('/')}/{request_id}"

        if status_url:
            for _ in range(2):
                time.sleep(1.5)
                status_response = requests.get(
                    status_url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=20
                )
                if status_response.status_code != 200:
                    continue
                status_json = status_response.json()
                status_video_url = _find_video_url(status_json)
                if status_video_url:
                    return {"success": True, "video_url": status_video_url}

        return {
            "success": True,
            "video_status": "pending",
            "video_request_id": request_id,
            "video_status_url": status_url
        }
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return {"success": False, "message": "PIKA error"}


def _generate_fallback_svg() -> str:
        svg = """
        <svg xmlns='http://www.w3.org/2000/svg' width='900' height='320' viewBox='0 0 900 320'>
            <defs>
                <linearGradient id='bg' x1='0' x2='1' y1='0' y2='1'>
                    <stop offset='0%' stop-color='#0f172a'/>
                    <stop offset='100%' stop-color='#1e293b'/>
                </linearGradient>
            </defs>
            <rect width='900' height='320' fill='url(#bg)' rx='18' />
            <g font-family='Arial, sans-serif' fill='#e2e8f0' font-size='18'>
                <text x='30' y='48' font-size='22' font-weight='700'>Problem-Solving Flow</text>
            </g>
            <g font-family='Arial, sans-serif' fill='#0f172a' font-size='14' font-weight='700'>
                <rect x='30' y='80' width='150' height='60' rx='10' fill='#38bdf8'/>
                <text x='45' y='115'>Gather actions</text>
                <rect x='210' y='80' width='150' height='60' rx='10' fill='#22d3ee'/>
                <text x='232' y='115'>Loop actions</text>
                <rect x='390' y='80' width='150' height='60' rx='10' fill='#a7f3d0'/>
                <text x='410' y='115'>If / else</text>
                <rect x='570' y='80' width='150' height='60' rx='10' fill='#fcd34d'/>
                <text x='585' y='115'>Update result</text>
                <rect x='750' y='80' width='120' height='60' rx='10' fill='#fca5a5'/>
                <text x='765' y='115'>Output</text>
            </g>
            <g stroke='#94a3b8' stroke-width='4' fill='none'>
                <path d='M180 110 L210 110'/>
                <path d='M360 110 L390 110'/>
                <path d='M540 110 L570 110'/>
                <path d='M720 110 L750 110'/>
            </g>
            <g font-family='Arial, sans-serif' fill='#e2e8f0' font-size='13'>
                <text x='30' y='200'>Follow this order every time you solve the final action challenge.</text>
                <text x='30' y='225'>Loop once per action. Decide. Update the result.</text>
            </g>
        </svg>
        """
        return f"data:image/svg+xml;utf8,{quote(svg)}"


def _call_openai_image(prompt: str) -> str:
    api_key = current_app.config.get("OPENAI_API_KEY")
    server = current_app.config.get("OPENAI_IMAGE_SERVER") or "https://api.openai.com/v1/images/generations"
    model = current_app.config.get("OPENAI_IMAGE_MODEL") or "gpt-image-1"
    size = current_app.config.get("OPENAI_IMAGE_SIZE") or "1024x1024"
    if not api_key or not server:
        current_app.logger.warning("OpenAI image generation not configured: missing API key or server")
        return ""

    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "response_format": "b64_json"
    }

    try:
        response = requests.post(
            server,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json=payload,
            timeout=30
        )
        if response.status_code != 200:
            current_app.logger.warning(
                "OpenAI image generation failed with status %s: %s",
                response.status_code,
                response.text[:500] if response.text else ""
            )
            return ""
        data = response.json()
        b64_data = data["data"][0]["b64_json"]
        return f"data:image/png;base64,{b64_data}"
    except (requests.RequestException, KeyError, IndexError, TypeError) as exc:
        current_app.logger.warning("OpenAI image generation error: %s", exc)
        return ""


def _fallback_grade(answer: str) -> dict:
    expected = current_app.config.get("FINAL_CODE_ANSWER", "")
    normalized_answer = _normalize_answer(answer)
    normalized_expected = _normalize_answer(expected)
    if not expected:
        if answer.strip():
            return {"correct": True, "message": "Answer received", "steps": []}
        return {"correct": False, "message": "Answer is required", "steps": []}
    if normalized_answer == normalized_expected:
        return {"correct": True, "message": "Correct", "steps": []}
    from difflib import SequenceMatcher
    similarity = SequenceMatcher(None, normalized_answer, normalized_expected).ratio()
    if similarity >= 0.9:
        return {"correct": True, "message": "Correct", "steps": []}
    return {
        "correct": False,
        "message": "Unable to verify correctness. Please review and retry.",
        "steps": [
            "Re-check the problem requirements and expected output.",
            "Compare your solution structure with the expected approach.",
            "Fix any syntax or logic errors, then try again."
        ]
    }


def _grade_final_answer(answer: str) -> dict:
    result = None
    prompt = (
        "You are grading a student's final code answer. "
        "Return ONLY valid JSON with this schema: "
        "{\"verdict\":\"Correct\"|\"Incorrect\",\"explanation\":string,\"steps\":string[]}\n"
        "If verdict is Correct, explanation should be 'Correct' and steps must be an empty array. "
        "If verdict is Incorrect, provide a short explanation and 3-6 numbered fix steps as strings."
    )

    openai_text = _call_openai(prompt, f"Student answer:\n{answer}")
    if openai_text:
        parsed = _extract_json(openai_text)
        verdict = (parsed.get("verdict") or "").strip().lower()
        explanation = (parsed.get("explanation") or "").strip()
        steps = parsed.get("steps") if isinstance(parsed.get("steps"), list) else []

        if verdict in {"correct", "incorrect"}:
            correct = verdict == "correct"
            if correct:
                result = {"correct": True, "message": "Correct", "steps": []}
            else:
                cleaned_steps = [str(step).strip() for step in steps if str(step).strip()]
                result = {
                    "correct": False,
                    "message": explanation or "Incorrect",
                    "steps": cleaned_steps[:6] if cleaned_steps else [
                        "Identify the incorrect logic or missing edge cases.",
                        "Adjust the algorithm to match required behavior.",
                        "Re-test with sample inputs and refine."
                    ]
                }

    return result or _fallback_grade(answer)


def _generate_guidance(answer: str) -> dict:
    prompt = (
        "You are a tutoring assistant for beginners. Provide a step-by-step walkthrough "
        "that explains how to build a solution and how the code is written, without giving full code or pseudocode. "
        "Use this structure in order: gather actions → loop once per action → decide with if/else → "
        "update result → output final result. "
        "Include UI guidance for a confused learner (what to click or do next). "
        "Return ONLY valid JSON with this schema: "
        "{\"title\":string,\"steps\":string[],\"ui_steps\":string[],"
        "\"video\":{\"title\":string,\"scenes\":[{\"title\":string,\"narration\":string,\"on_screen\":string}]}}\n"
        "Keep steps short, actionable, and avoid revealing a full solution."
    )

    openai_text = _call_openai(prompt, f"Student context:\n{answer}")
    if openai_text:
        parsed = _extract_json(openai_text)
        title = (parsed.get("title") or "Walkthrough").strip() or "Walkthrough"
        steps = parsed.get("steps") if isinstance(parsed.get("steps"), list) else []
        ui_steps = parsed.get("ui_steps") if isinstance(parsed.get("ui_steps"), list) else []
        cleaned_steps = [
            _strip_code_blocks(str(step)).strip()
            for step in steps
            if str(step).strip()
        ]
        cleaned_ui_steps = [
            _strip_code_blocks(str(step)).strip()
            for step in ui_steps
            if str(step).strip()
        ]
        video = parsed.get("video") if isinstance(parsed.get("video"), dict) else {}
        video_title = _strip_code_blocks(str(video.get("title") or f"{title} Video")).strip() or f"{title} Video"
        scenes = video.get("scenes") if isinstance(video.get("scenes"), list) else []
        cleaned_scenes = []
        for scene in scenes:
            if not isinstance(scene, dict):
                continue
            scene_title = _strip_code_blocks(str(scene.get("title") or "")).strip() or "Step"
            narration = _strip_code_blocks(str(scene.get("narration") or "")).strip()
            on_screen = _strip_code_blocks(str(scene.get("on_screen") or "")).strip()
            if narration or on_screen:
                cleaned_scenes.append({
                    "title": scene_title,
                    "narration": narration or on_screen,
                    "on_screen": on_screen or narration
                })

        if not cleaned_scenes and cleaned_steps:
            cleaned_scenes = [
                {"title": f"Step {index + 1}", "narration": step, "on_screen": step}
                for index, step in enumerate(cleaned_steps[:8])
            ]
        video_notice = "Generated step-by-step video narration from your walkthrough."

        if cleaned_steps:
            durations = [7 for _ in cleaned_steps[:8]]
            video_url = ""
            video_status = ""
            video_request_id = ""
            video_status_url = ""
            pika_prompt = (
                "Create a short, friendly educational walkthrough video for a coding maze game. "
                f"Title: {video_title}. "
                "Keep it concise, motivational, and beginner-friendly. "
                f"Key steps: {'; '.join(cleaned_steps[:6])}."
            )
            pika_result = _call_pika_video(pika_prompt)
            if pika_result.get("success") and pika_result.get("video_url"):
                video_url = pika_result.get("video_url")
                video_notice = "Generated a real video walkthrough."
            elif pika_result.get("video_status") == "pending":
                video_status = "pending"
                video_request_id = pika_result.get("video_request_id") or ""
                video_status_url = pika_result.get("video_status_url") or ""
                video_notice = "Video is generating. Please try again in a moment."
            elif pika_result.get("message"):
                video_notice = pika_result.get("message")

            return {
                "success": True,
                "title": title,
                "steps": cleaned_steps[:8],
                "durations": durations,
                "ui_steps": cleaned_ui_steps[:6],
                "video": {
                    "title": video_title,
                    "scenes": cleaned_scenes[:8]
                },
                "video_notice": video_notice,
                "video_url": video_url,
                "video_status": video_status,
                "video_request_id": video_request_id,
                "video_status_url": video_status_url
            }

    fallback_steps = [
        "Gather the ordered list of actions and define what the result represents.",
        "Loop once per action, in order.",
        "Use if/else decisions to interpret the current action.",
        "Update the running result based on that action.",
        "Output the final result after the loop ends."
    ]
    fallback_ui_steps = [
        "Type your current understanding into the answer box.",
        "Click Generate Walkthrough to get guided steps.",
        "Click Play Walkthrough to follow the steps with audio.",
        "Revise your answer and press Check Answer.",
        "If correct, click Save Completion."
    ]
    fallback_scenes = [
        {"title": "Actions", "narration": "Gather the actions and define the result.", "on_screen": "Gather actions and define result."},
        {"title": "Loop", "narration": "Loop once per action in order.", "on_screen": "Loop once per action."},
        {"title": "Decide", "narration": "Use if/else decisions to interpret each action.", "on_screen": "Decide with if/else."},
        {"title": "Update", "narration": "Update the running result after each action.", "on_screen": "Update the result."},
        {"title": "Output", "narration": "Output the final result after the loop.", "on_screen": "Output the final result."}
    ]
    fallback_notice = "Generated step-by-step video narration from fallback guidance."
    fallback_video_url = ""
    fallback_video_status = ""
    fallback_video_request_id = ""
    fallback_video_status_url = ""
    fallback_prompt = (
        "Create a short, friendly educational walkthrough video for a coding maze game. "
        "Title: Walkthrough Video. "
        f"Key steps: {'; '.join(fallback_steps[:6])}."
    )
    fallback_result = _call_pika_video(fallback_prompt)
    if fallback_result.get("success") and fallback_result.get("video_url"):
        fallback_video_url = fallback_result.get("video_url")
        fallback_notice = "Generated a real video walkthrough."
    elif fallback_result.get("video_status") == "pending":
        fallback_video_status = "pending"
        fallback_video_request_id = fallback_result.get("video_request_id") or ""
        fallback_video_status_url = fallback_result.get("video_status_url") or ""
        fallback_notice = "Video is generating. Please try again in a moment."
    elif fallback_result.get("message"):
        fallback_notice = fallback_result.get("message")

    return {
        "success": True,
        "title": "Walkthrough",
        "steps": fallback_steps,
        "durations": [7 for _ in fallback_steps],
        "ui_steps": fallback_ui_steps,
        "video": {
            "title": "Walkthrough Video",
            "scenes": fallback_scenes
        },
        "video_notice": fallback_notice,
        "video_url": fallback_video_url,
        "video_status": fallback_video_status,
        "video_request_id": fallback_video_request_id,
        "video_status_url": fallback_video_status_url
    }


def _chat_response(message: str, history: list, role: str = "") -> dict:
    lowered = (message or "").lower()
    role_key = (role or "").strip().lower()
    if not lowered.strip():
        return {
            "success": True,
            "reply": "pass"
        }

    if any(phrase in lowered for phrase in [
        "video",
        "show me",
        "animate",
        "visual",
        "walkthrough video",
        "demo"
    ]):
        history_text = ""
        for item in history[-8:]:
            role = (item.get("role") or "user").capitalize()
            content = item.get("content") or ""
            history_text += f"{role}: {content}\n"
        video_prompt = (
            "Create a short, friendly educational video summarizing the student's journey in a coding maze game. "
            "Highlight key choices, what they learned, and the outcome in simple language. "
            f"Conversation context:\n{history_text}\nUser request: {message}"
        )
        video_result = _call_pika_video(video_prompt)
        if video_result.get("success") and video_result.get("video_url"):
            return {
                "success": True,
                "reply": "Here’s a short video summary of your game journey.",
                "video_url": video_result.get("video_url")
            }
        if video_result.get("video_status") == "pending":
            return {
                "success": True,
                "reply": "Your video is generating. Please ask again in a moment.",
                "video_status": "pending"
            }
        if video_result.get("message"):
            return {
                "success": True,
                "reply": video_result.get("message")
            }
        return {
            "success": True,
            "reply": "I couldn’t generate a video right now. Please try again in a moment."
        }

    role_instructions = ""
    if role_key == "hint_coach":
        role_instructions = (
            "You are the Hint Coach. Provide a minimal code nudge or stub with TODO comments. "
        )
    elif role_key == "debugger":
        role_instructions = (
            "You are the Debugger. Provide a corrected code snippet focused on the likely bug location. "
        )
    elif role_key == "teacher":
        role_instructions = (
            "You are the Teacher. Provide a clean, readable reference solution with brief comments. "
        )
    elif role_key == "checker":
        role_instructions = (
            "You are the Checker. Provide the corrected code that matches the expected behavior. "
        )

    prompt = (
        "You are a ChatGPT‑style coding assistant for a student coding maze endgame. "
        f"{role_instructions}"
        "Return ONLY Python code. Do not use Markdown. Do not include explanations. "
        "If details are missing, return a short code comment asking for the needed info."
    )
    history_text = ""
    for item in history[-10:]:
        role = (item.get("role") or "user").capitalize()
        content = item.get("content") or ""
        history_text += f"{role}: {content}\n"

    openai_text = _call_openai(prompt, f"Conversation:\n{history_text}\nUser: {message}", strip_code_blocks=False)
    if openai_text:
        return {"success": True, "reply": openai_text.strip()}

    return {
        "success": True,
        "reply": "# Please share the exact requirements and expected output."
    }


def _get_earned_badges(player_id: int) -> list:
    badge_rows = (
        PlayerBadge.query
        .filter_by(player_id=player_id)
        .order_by(PlayerBadge.timestamp.asc())
        .all()
    )
    return [row.to_dict() for row in badge_rows]


def _get_earned_badges_frontend(player_id: int) -> list:
    badge_rows = (
        PlayerBadge.query
        .filter_by(player_id=player_id)
        .order_by(PlayerBadge.timestamp.asc())
        .all()
    )
    return [
        {
            "badgeId": row.badge_id,
            "badgeName": row.badge.badge_name if row.badge else None,
            "attempts": row.attempts,
            "earnedAt": row.timestamp.isoformat() if row.timestamp else None,
        }
        for row in badge_rows
    ]


def _get_or_create_player(player_id: int) -> Player:
    player = Player.query.get(player_id)
    if player:
        return player
    player = Player(id=player_id, username=f"Player {player_id}")
    db.session.add(player)
    db.session.commit()
    return player


@endgame_api.route("/player/<int:player_id>", methods=["GET"])
def get_player(player_id):
    player = _get_or_create_player(player_id)
    data = player.to_dict()
    data["display_name"] = player.username
    data["character_class"] = None
    return jsonify({"success": True, "player": data}), 200


@endgame_api.route("/api/endgame/player/<int:player_id>", methods=["GET"])
def get_player_api(player_id):
    return get_player(player_id)


@endgame_api.route("/player/<int:player_id>/badges", methods=["GET"])
def get_player_badges(player_id):
    _get_or_create_player(player_id)
    return jsonify({"success": True, "badges": _get_earned_badges_frontend(player_id)}), 200


@endgame_api.route("/api/endgame/player/<int:player_id>/badges", methods=["GET"])
def get_player_badges_api(player_id):
    return get_player_badges(player_id)


@endgame_api.route("/player/<int:player_id>/score", methods=["GET"])
def get_player_score(player_id):
    player = _get_or_create_player(player_id)

    badge_rows = (
        PlayerBadge.query
        .filter_by(player_id=player_id)
        .order_by(PlayerBadge.timestamp.asc())
        .all()
    )

    earned_badges = [row.to_dict() for row in badge_rows]
    attempts_per_stop = [
        {
            "badge_id": row.badge_id,
            "badge_name": row.badge.badge_name if row.badge else None,
            "attempts": row.attempts,
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        }
        for row in badge_rows
    ]

    response = {
        "success": True,
        "player": player.to_dict(),
        "earned_badges": earned_badges,
        "attempts_per_stop": attempts_per_stop,
        "attempts_by_badge": [
            {
                "badge_id": row.badge_id,
                "badge_name": row.badge.badge_name if row.badge else None,
                "attempts": row.attempts,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            }
            for row in badge_rows
        ],
        "completion_status": bool(player.completed_at),
        "final": {
            "completed_at": player.completed_at.isoformat() if player.completed_at else None,
            "final_attempts": player.final_attempts,
            "final_badge": None,
            "final_correct": player.final_correct,
        }
    }

    if player.final_badge_id:
        badge = Badge.query.get(player.final_badge_id)
        if badge:
            response["final"]["final_badge"] = badge.to_dict()

    return jsonify(response), 200


@endgame_api.route("/api/endgame/player/<int:player_id>/score", methods=["GET"])
def get_player_score_api(player_id):
    return get_player_score(player_id)


@endgame_api.route("/player/<int:player_id>/final-check", methods=["POST"])
def final_check(player_id):
    player = _get_or_create_player(player_id)

    data = _get_json()
    body_player_id = data.get("playerId")
    if body_player_id is not None and int(body_player_id) != int(player_id):
        return jsonify({"correct": False, "message": "playerId mismatch", "steps": []}), 400

    answer = (data.get("answer") or "").strip()
    if not answer:
        return jsonify({"correct": False, "message": "Answer is required", "steps": []}), 400

    max_len = 2000
    if len(answer) > max_len:
        answer = answer[:max_len]

    result = _grade_final_answer(answer)

    player.final_answer = answer
    player.final_correct = result["correct"]
    db.session.commit()

    return jsonify(result), 200


@endgame_api.route("/api/endgame/player/<int:player_id>/final-check", methods=["POST"])
def final_check_api(player_id):
    return final_check(player_id)


@endgame_api.route("/api/endgame/final-check", methods=["POST"])
def final_check_frontend():
    data = _get_json()
    answer = (data.get("answer") or "").strip()
    if not answer:
        return jsonify({"correct": False, "message": "Answer is required", "steps": []}), 400

    max_len = 2000
    if len(answer) > max_len:
        answer = answer[:max_len]

    player_id = data.get("playerId")
    player = None
    if player_id is not None:
        try:
            player = Player.query.get(int(player_id))
        except (TypeError, ValueError):
            return jsonify({"correct": False, "message": "Invalid playerId", "steps": []}), 400
        if not player:
            return jsonify({"correct": False, "message": "Player not found", "steps": []}), 404

    result = _grade_final_answer(answer)

    if player:
        player.final_answer = answer
        player.final_correct = result["correct"]
        db.session.commit()

    return jsonify(result), 200


@endgame_api.route("/player/<int:player_id>/final-badge", methods=["POST"])
def award_final_badge(player_id):
    player = _get_or_create_player(player_id)

    if not player.final_correct:
        return jsonify({"success": False, "message": "Final answer not correct"}), 400

    badge = Badge.query.filter_by(badge_name="Master").first()
    if not badge:
        badge = Badge(badge_name="Master")
        db.session.add(badge)
        db.session.commit()

    existing = PlayerBadge.query.filter_by(player_id=player_id, badge_id=badge.id).first()
    if not existing:
        attempts_value = player.final_attempts if player.final_attempts is not None else 0
        final_badge_row = PlayerBadge(
            player_id=player.id,
            badge_id=badge.id,
            attempts=attempts_value,
            timestamp=datetime.utcnow()
        )
        db.session.add(final_badge_row)
        db.session.commit()

    if player.final_badge_id != badge.id:
        player.final_badge_id = badge.id

    if player.completed_at is None:
        player.completed_at = datetime.utcnow()

    db.session.commit()

    return jsonify({
        "success": True,
        "earned_badges": _get_earned_badges(player_id)
    }), 200


@endgame_api.route("/player/<int:player_id>/complete", methods=["POST"])
def complete_player(player_id):
    player = _get_or_create_player(player_id)

    data = _get_json()
    attempts = data.get("attempts")
    badge_id = data.get("badge_id")
    badge_name = data.get("badge_name")
    timestamp = _parse_iso(data.get("timestamp"))

    if attempts is None:
        return jsonify({"success": False, "message": "Missing attempts"}), 400

    badge = None
    if badge_id is None and badge_name:
        badge = Badge.query.filter_by(badge_name=badge_name).first()
        badge_id = badge.id if badge else None
    elif badge_id is not None:
        badge = Badge.query.get(badge_id)
        if not badge:
            return jsonify({"success": False, "message": "Badge not found"}), 404

    player.completed_at = timestamp or datetime.utcnow()
    player.final_attempts = attempts
    if badge_id is not None:
        player.final_badge_id = badge_id
        final_badge_row = PlayerBadge(
            player_id=player.id,
            badge_id=badge_id,
            attempts=attempts,
            timestamp=timestamp or datetime.utcnow()
        )
        db.session.add(final_badge_row)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Completion saved",
        "final": {
            "completed_at": player.completed_at.isoformat() if player.completed_at else None,
            "final_attempts": player.final_attempts,
            "final_badge": badge.to_dict() if badge else None,
        }
    }), 200


@endgame_api.route("/api/endgame/player/<int:player_id>/complete", methods=["POST"])
def complete_player_api(player_id):
    return complete_player(player_id)


@endgame_api.route("/player/<int:player_id>/guidance", methods=["POST"])
def generate_guidance(player_id):
    _get_or_create_player(player_id)

    data = _get_json()
    answer = (data.get("answer") or "").strip()

    result = _generate_guidance(answer)
    return jsonify(result), 200


@endgame_api.route("/api/endgame/player/<int:player_id>/guidance", methods=["POST"])
def generate_guidance_api(player_id):
    return generate_guidance(player_id)


@endgame_api.route("/player/<int:player_id>/chat", methods=["POST"])
def chat_with_ai(player_id):
    _get_or_create_player(player_id)

    data = _get_json()
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"success": False, "message": "Message is required"}), 400

    history = data.get("history") if isinstance(data.get("history"), list) else []

    role = (data.get("role") or "").strip()
    result = _chat_response(message, history, role)
    return jsonify(result), 200


@endgame_api.route("/api/endgame/player/<int:player_id>/chat", methods=["POST"])
def chat_with_ai_api(player_id):
    return chat_with_ai(player_id)


@endgame_api.route("/leaderboard", methods=["GET"])
def leaderboard():
    players = Player.query.all()
    payload = []

    for player in players:
        total_attempts = (
            db.session.query(db.func.sum(PlayerBadge.attempts))
            .filter(PlayerBadge.player_id == player.id)
            .scalar()
        ) or 0

        payload.append({
            "player": player.to_dict(),
            "total_attempts": total_attempts,
        })

    payload.sort(
        key=lambda item: (
            item["player"]["completed_at"] is None,
            item["player"]["completed_at"] or "",
            item["total_attempts"],
        )
    )

    return jsonify({"success": True, "leaderboard": payload}), 200
