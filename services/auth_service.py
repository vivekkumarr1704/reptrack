"""Authentication helpers. Cloud passwords are managed only by Supabase Auth."""
from __future__ import annotations
import hashlib
import hmac
import re
import secrets
import streamlit as st
from . import db

PBKDF2_ROUNDS = 310_000


def validate_password(password: str) -> list[str]:
    issues = []
    if len(password) < 12: issues.append("Use at least 12 characters.")
    if not re.search(r"[A-Z]", password): issues.append("Add at least one uppercase letter.")
    if not re.search(r"[a-z]", password): issues.append("Add at least one lowercase letter.")
    if not re.search(r"\d", password): issues.append("Add at least one number.")
    if not re.search(r"[^A-Za-z0-9]", password): issues.append("Add at least one symbol.")
    return issues


def _local_hash(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), PBKDF2_ROUNDS).hex()


def register_user(full_name: str, username: str, email: str, password: str) -> tuple[bool, str]:
    full_name = full_name.strip()
    username = username.strip().lower()
    email = email.strip().lower()
    if len(full_name) < 2:
        return False, "Please enter your full name."
    if not re.fullmatch(r"[a-z0-9_.-]{3,24}", username):
        return False, "Username must be 3–24 characters and use only letters, numbers, dots, underscores, or hyphens."
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        return False, "Enter a valid email address."
    issues = validate_password(password)
    if issues:
        return False, "Password requirements: " + " ".join(issues)
    if not db.is_cloud_mode():
        import sqlite3
        if db.select_rows("profiles", {"username": username}) or db.select_rows("profiles", {"email": email}):
            return False, "That username or email is already registered. Try logging in."
        salt = secrets.token_hex(16)
        try:
            profile = db.register_local_user(username, email, full_name, salt, _local_hash(password, salt))
            st.session_state["vf_user"] = {"id": profile["id"], "email": profile["email"]}
            st.session_state["vf_profile"] = profile
            return True, "Account created. Welcome to RepTrack!"
        except sqlite3.IntegrityError:
            return False, "That username or email is already registered. Try logging in."
        except Exception as exc:
            return False, f"Could not create the account: {exc}"
    try:
        client = db.supabase_client(authenticated=False)
        result = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"full_name": full_name, "username": username}},
        })
        user = getattr(result, "user", None)
        session = getattr(result, "session", None)
        if not user:
            return False, "Sign-up did not return an account. Check the Supabase Auth configuration."
        if session:
            db._store_session(session)
            st.session_state["vf_user"] = {"id": user.id, "email": email}
            ok, message = ensure_profile(user)
            if not ok:
                return False, message
            st.session_state["vf_notice"] = ("success", "Account created. Welcome to RepTrack!")
            return True, "Account created. Welcome to RepTrack!"
        return True, "Account created. Check your email to confirm the account, then log in. Your username will be used to build your profile after the first successful login."
    except Exception as exc:
        return False, _friendly_auth_error(exc)


def login_user(identifier: str, password: str) -> tuple[bool, str]:
    identifier = identifier.strip()
    if not identifier or not password:
        return False, "Enter your username/email and password."
    if not db.is_cloud_mode():
        salt = db.local_salt(identifier)
        if not salt:
            return False, "The username/email or password is incorrect."
        profile = db.verify_local_credentials(identifier, _local_hash(password, salt))
        if not profile:
            return False, "The username/email or password is incorrect."
        st.session_state["vf_user"] = {"id": profile["id"], "email": profile["email"]}
        st.session_state["vf_profile"] = profile
        return True, "Welcome back!"
    email = identifier.lower()
    if "@" not in identifier:
        email = db.resolve_username_email(identifier) or ""
        if not email:
            if not db.cloud_config().get("service_role_key"):
                return False, "Cloud username login needs SUPABASE_SERVICE_ROLE_KEY in server-side Streamlit Secrets. You can log in with your email meanwhile."
            return False, "The username/email or password is incorrect."
    try:
        client = db.supabase_client(authenticated=False)
        result = client.auth.sign_in_with_password({"email": email, "password": password})
        session = getattr(result, "session", None)
        user = getattr(result, "user", None)
        if not session or not user:
            return False, "Login failed. Check your credentials and confirm your email if required."
        db._store_session(session)
        st.session_state["vf_user"] = {"id": user.id, "email": user.email}
        ok, message = ensure_profile(user)
        if not ok:
            return False, message
        return True, "Welcome back!"
    except Exception as exc:
        return False, _friendly_auth_error(exc)


def ensure_profile(user) -> tuple[bool, str]:
    """Create the app profile on first successful authentication, including after email confirmation."""
    uid = str(getattr(user, "id", "") or "")
    email = str(getattr(user, "email", "") or "")
    if not uid or not email:
        return False, "Could not identify the signed-in account. Please log in again."
    try:
        found = db.select_rows("profiles", {"id": uid}, limit=1)
        if found:
            st.session_state["vf_profile"] = found[0]
            return True, "Profile ready."
        meta = getattr(user, "user_metadata", None) or {}
        if hasattr(meta, "model_dump"):
            meta = meta.model_dump()
        elif not isinstance(meta, dict):
            meta = dict(meta) if meta else {}
        full_name = str(meta.get("full_name") or email.split("@")[0]).strip()
        username = str(meta.get("username") or email.split("@")[0]).lower().strip()
        profile = {
            "id": uid, "username": username, "email": email.lower(), "full_name": full_name,
            "weekly_goal": 4, "preferred_unit": "kg", "theme": "dark", "body_weight_goal_kg": None,
        }
        created = db.insert_row("profiles", profile)
        st.session_state["vf_profile"] = created or profile
        return True, "Profile ready."
    except Exception as exc:
        message = str(exc).lower()
        if "unique" in message or "duplicate" in message or "23505" in message:
            return False, "This username is already taken. Ask the app owner to correct the profile username in Supabase, then log in again."
        return False, f"Could not load your profile: {exc}"


def current_user() -> dict | None:
    user = st.session_state.get("vf_user")
    if not user:
        return None
    if not db.is_cloud_mode():
        profile = db.select_rows("profiles", {"id": user.get("id")}, limit=1)
        if not profile:
            st.session_state.pop("vf_user", None)
            st.session_state.pop("vf_profile", None)
            return None
        st.session_state["vf_profile"] = profile[0]
        return user
    try:
        client = db.supabase_client(authenticated=True)
        response = client.auth.get_user()
        auth_user = getattr(response, "user", None)
        if not auth_user:
            return None
        st.session_state["vf_user"] = {"id": auth_user.id, "email": auth_user.email}
        ok, _ = ensure_profile(auth_user)
        return st.session_state["vf_user"] if ok else None
    except Exception:
        return None


def logout_user() -> None:
    if db.is_cloud_mode():
        try:
            db.supabase_client(authenticated=True).auth.sign_out()
        except Exception:
            pass
    for key in ["vf_user", "vf_profile", "vf_access_token", "vf_refresh_token", "vf_active_workout_id", "vf_selected_exercise_id", "vf_selected_workout_exercise_id", "vf_selected_muscles", "vf_muscle_choices", "vf_calendar_selected", "vf_calendar_month", "vf_delete_workout_id", "vf_confirm_finish_workout", "vf_confirm_abandon_workout", "vf_notice", "vf_page"]:
        st.session_state.pop(key, None)


def send_password_reset(email: str) -> tuple[bool, str]:
    email = email.strip().lower()
    if not email or "@" not in email:
        return False, "Enter your account email address."
    if not db.is_cloud_mode():
        return False, "Local demo accounts do not have email delivery configured. Use your saved password or create a new local account."
    try:
        client = db.supabase_client(authenticated=False)
        client.auth.reset_password_for_email(email)
        return True, "If the email is registered, Supabase will send password-reset instructions. Check your inbox and spam folder."
    except Exception as exc:
        return False, _friendly_auth_error(exc)


def _friendly_auth_error(exc: Exception) -> str:
    text = str(exc)
    lower = text.lower()
    if "invalid login credentials" in lower or "invalid email or password" in lower:
        return "The username/email or password is incorrect."
    if "email not confirmed" in lower:
        return "Please confirm your email using the link Supabase sent you, then log in."
    if "already registered" in lower or "already exists" in lower:
        return "An account with that email already exists. Try logging in."
    if "rate limit" in lower:
        return "Too many attempts. Please wait a little and try again."
    return f"Authentication issue: {text[:240]}"
