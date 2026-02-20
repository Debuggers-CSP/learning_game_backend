from flask import request, current_app, g
from functools import wraps
import jwt
from model.user import User
from model.robop_user import RobopUser

def _looks_like_jwt(token: str) -> bool:
    return isinstance(token, str) and token.count(".") == 2

def _get_jwt_from_request():
    # 1) Authorization header
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        tok = auth.split(" ", 1)[1].strip()
        if _looks_like_jwt(tok):
            return tok, "bearer"

    # 2) ✅ Prefer Robop cookie FIRST
    robop_tok = request.cookies.get("ROBOP_JWT")
    if _looks_like_jwt(robop_tok):
        return robop_tok, "robop_cookie"

    # 3) Main cookie (only if it looks like a JWT)
    token_cookie_name = current_app.config.get("JWT_TOKEN_NAME", "jwt")
    tok = request.cookies.get(token_cookie_name)
    if _looks_like_jwt(tok):
        return tok, "main_cookie"

    return None, None


def token_required(roles=None):
    def decorator(func_to_guard):
        @wraps(func_to_guard)
        def decorated(*args, **kwargs):
            if request.method == "OPTIONS":
                return ("", 200)

            token, source = _get_jwt_from_request()
            if not token:
                return {"message": "Authentication Token is missing!", "data": None, "error": "Unauthorized"}, 401

            try:
                data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])

                if source == "robop_cookie":
                    uid = data.get("uid")
                    if not uid:
                        return {"message": "Invalid Authentication token!", "data": None, "error": "Unauthorized"}, 401
                    current_user = RobopUser.query.filter_by(_uid=uid).first()
                else:
                    uid = data.get("_uid")
                    if not uid:
                        return {"message": "Invalid Authentication token!", "data": None, "error": "Unauthorized"}, 401
                    current_user = User.query.filter_by(_uid=uid).first()

                if current_user is None:
                    return {"message": "Invalid Authentication token!", "data": None, "error": "Unauthorized"}, 401

                g.current_user = current_user
                return func_to_guard(*args, **kwargs)

            except jwt.ExpiredSignatureError:
                return {"message": "Token has expired!", "data": None, "error": "Unauthorized"}, 401
            except Exception as e:
                return {"message": "Invalid Authentication token!", "data": None, "error": str(e)}, 401

        return decorated
    return decorator