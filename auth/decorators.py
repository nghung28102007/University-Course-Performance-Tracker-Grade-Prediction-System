"""
Access control decorators for role-based authorization.
Uses Flask session to determine user role.
"""
from functools import wraps
from flask import session, abort, redirect, url_for


def require_role(*allowed_roles):
    """
    Decorator that restricts route access to specific roles.
    Admin always has access. Usage: @require_role('instructor', 'student')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_role = session.get("user_role", "guest")
            if user_role == "admin" or user_role in allowed_roles:
                return func(*args, **kwargs)
            abort(403)
        return wrapper
    return decorator


def login_required(func):
    """Decorator that requires any authenticated user."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_role" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


def set_session_role(role, user_id=None, user_name=None):
    """Set the current user's session role and info."""
    session["user_role"] = role
    session["user_id"] = user_id
    session["user_name"] = user_name
