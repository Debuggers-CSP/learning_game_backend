import jwt
from functools import wraps
from flask import request, jsonify, current_app, g
from model.robop_user import RobopUser  

def robop_token_required():
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            print("cookies keys:", list(request.cookies.keys()))
            print("ROBOP_JWT present:", "ROBOP_JWT" in request.cookies)
            print("ROBOP_JWT prefix:", (request.cookies.get("ROBOP_JWT", "")[:20]))

            token = request.cookies.get("ROBOP_JWT")
            if not token:
                return jsonify({"success": False, "message": "Missing token"}), 401

            try:
                payload = jwt.decode(
                    token,
                    current_app.config["SECRET_KEY"],
                    algorithms=["HS256"]
                )
                print("jwt payload:", payload)
            except Exception as e:
                print("JWT decode error:", repr(e))
                return jsonify({"success": False, "message": "Invalid token"}), 401

            uid = payload.get("uid")
            if not uid:
                return jsonify({"success": False, "message": "Token missing uid"}), 401

            user = RobopUser.query.filter_by(_uid=uid).first()
            print("found user?", bool(user), "uid:", uid)

            if not user:
                return jsonify({"success": False, "message": "User not found"}), 401

            g.robop_user = user
            g.current_user = user
            return fn(*args, **kwargs)

        return wrapper
    return decorator