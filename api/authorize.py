from flask import request, current_app, g
from flask_login import current_user
from functools import wraps
import jwt
from model.robop_user import RobopUser  


def _get_token_from_request():
    """
    Priority:
      1) Authorization: Bearer <token>
      2) Cookie: JWT_TOKEN_NAME
    """
    auth_header = request.headers.get("Authorization", "") or ""
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()

    cookie_name = current_app.config.get("JWT_TOKEN_NAME")
    if cookie_name:
        return request.cookies.get(cookie_name)
    return None


def auth_required(roles=None):
    def decorator(func_to_guard):
        @wraps(func_to_guard)
        def decorated(*args, **kwargs):
            # ✅ Always allow CORS preflight through
            if request.method == "OPTIONS":
                return ("", 200)

            user = None

            # Method 1: Flask-Login session auth
            try:
                if current_user.is_authenticated:
                    user = current_user
                    g.current_user = user
            except Exception:
                # If flask-login isn't configured on this blueprint/app, don't crash
                user = None

            # Method 2: JWT (Bearer header OR cookie)
            if user is None:
                token = _get_token_from_request()
                if not token:
                    return {
                        "message": "Authentication Token is missing!",
                        "data": None,
                        "error": "Unauthorized"
                    }, 401

                try:
                    data = jwt.decode(
                        token,
                        current_app.config["SECRET_KEY"],
                        algorithms=["HS256"]
                    )

                    uid = data.get("_uid")
                    if not uid:
                        return {
                            "message": "Invalid token payload (missing _uid).",
                            "data": None,
                            "error": "Unauthorized"
                        }, 401

                    user = RobopUser.query.filter_by(_uid=uid).first()
                    if user is None:
                        return {
                            "message": "Invalid Authentication token!",
                            "data": None,
                            "error": "Unauthorized"
                        }, 401

                    g.current_user = user

                except jwt.ExpiredSignatureError:
                    return {
                        "message": "Token has expired!",
                        "data": None,
                        "error": "Unauthorized"
                    }, 401
                except jwt.InvalidTokenError:
                    return {
                        "message": "Invalid token!",
                        "data": None,
                        "error": "Unauthorized"
                    }, 401
                except Exception as e:
                    return {
                        "message": "Something went wrong decoding the token!",
                        "data": None,
                        "error": str(e)
                    }, 500

            # Role check
            if roles:
                required_roles = roles if isinstance(roles, list) else [roles]
                if getattr(user, "role", None) not in required_roles:
                    return {
                        "message": f"Insufficient permissions. Required roles: {', '.join(required_roles)}",
                        "data": None,
                        "error": "Forbidden"
                    }, 403

            return func_to_guard(*args, **kwargs)

        return decorated

    return decorator


def token_required(roles=None):
    return auth_required(roles)
