from functools import wraps

from flask import flash, redirect, session, url_for


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user_id") is None:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped
