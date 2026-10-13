from __future__ import annotations
import calendar as pycalendar
import html
import json
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services import db
from services import auth_service
from services.analytics_service import count_completed_workouts, current_streak, longest_streak, kg_to_unit, unit_to_kg, workout_volume, total_reps
from components.ui import inject_css, metric_card, section, hero

st.set_page_config(page_title="RepTrack · Gym Companion", page_icon="💪", layout="wide", initial_sidebar_state="expanded")

MUSCLES = [
    ("Chest", "◈", "Pressing power"), ("Back", "↗", "Build your back"), ("Shoulders", "✳", "Strong delts"),
    ("Biceps", "⌁", "Arm focus"), ("Triceps", "⌇", "Arm extension"), ("Forearms", "⌂", "Grip strength"),
    ("Legs", "⌖", "Lower-body day"), ("Quadriceps", "↟", "Front of legs"), ("Hamstrings", "↙", "Posterior chain"),
    ("Glutes", "◉", "Hip strength"), ("Calves", "⌁", "Lower legs"), ("Abs / Core", "◎", "Core stability"),
    ("Cardio", "⌁", "Conditioning"),
]

MUSCLE_EMOJI = {"Chest":"◈", "Back":"↗", "Shoulders":"✳", "Biceps":"⌁", "Triceps":"⌇", "Forearms":"⌂", "Legs":"⌖", "Quadriceps":"↟", "Hamstrings":"↙", "Glutes":"◉", "Calves":"⌁", "Abs / Core":"◎", "Cardio":"♥"}


def now_local() -> datetime:
    return datetime.now(ZoneInfo("Asia/Kolkata"))


def uid() -> str:
    return str(st.session_state["vf_user"]["id"])


def profile() -> dict:
    p = st.session_state.get("vf_profile") or {}
    if not p and st.session_state.get("vf_user"):
        found = db.select_rows("profiles", {"id": uid()}, limit=1)
        if found:
            st.session_state["vf_profile"] = found[0]
            return found[0]
    return p


def user_rows(table: str, order_by: str | None = None, descending: bool = False, limit: int | None = None) -> list[dict]:
    return db.select_rows(table, {"user_id": uid()}, order_by=order_by, descending=descending, limit=limit)


def load_exercises() -> list[dict]:
    globals_ = db.select_rows("exercises", {"owner_id": None}, order_by="name")
    mine = db.select_rows("exercises", {"owner_id": uid()}, order_by="name")
    return globals_ + mine


def get_active_workout() -> dict | None:
    found = db.select_rows("workout_sessions", {"user_id": uid(), "status": "active"}, order_by="started_at", descending=True, limit=1)
    if found:
        st.session_state["vf_active_workout_id"] = found[0]["id"]
        return found[0]
    st.session_state.pop("vf_active_workout_id", None)
    return None


def get_workout(workout_id: str) -> dict | None:
    found = db.select_rows("workout_sessions", {"id": workout_id, "user_id": uid()}, limit=1)
    return found[0] if found else None


def get_workout_exercises(workout_id: str) -> list[dict]:
    return db.select_rows("workout_exercises", {"workout_id": workout_id, "user_id": uid()}, order_by="sort_order")


def get_sets(workout_exercise_id: str) -> list[dict]:
    return db.select_rows("workout_sets", {"workout_exercise_id": workout_exercise_id, "user_id": uid()}, order_by="set_number")


def set_page(page: str) -> None:
    st.session_state["vf_page"] = page


def body_weight_display(weight_kg: float | None, unit: str) -> str:
    if weight_kg is None:
        return "—"
    return f"{kg_to_unit(float(weight_kg), unit):.1f} {unit}"


def save_weight(entry_date: date, value: float, unit: str, notes: str = "") -> None:
    kg = round(unit_to_kg(float(value), unit), 2)
    date_text = entry_date.isoformat()
    existing = db.select_rows("body_weight_entries", {"user_id": uid(), "entry_date": date_text}, limit=1)
    if existing:
        db.update_rows("body_weight_entries", {"id": existing[0]["id"], "user_id": uid()}, {"weight_kg": kg, "notes": notes.strip()})
    else:
        db.insert_row("body_weight_entries", {"user_id": uid(), "entry_date": date_text, "weight_kg": kg, "notes": notes.strip()})


def render_auth() -> None:
    st.markdown('<div class="vf-auth-wrap">', unsafe_allow_html=True)
    left, right = st.columns([1, 1.2], vertical_alignment="center")
    with left:
        st.markdown('<div class="vf-brand"><span class="vf-brand-mark">R</span><span>RepTrack</span></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("# Train with intention.")
        st.markdown("Your workouts. Your progress. One private space.")
        st.markdown('<div class="vf-card"><div class="vf-eyebrow">YOUR DAILY EDGE</div><h3>Show up. Log it. Get stronger.</h3><div class="vf-muted">Track sets, reps, body weight and consistency—then see the work add up.</div></div>', unsafe_allow_html=True)
        st.caption("Create your own profile. Your workout history stays associated with your account.")
    with right:
        st.markdown('<div class="vf-card">', unsafe_allow_html=True)
        login_tab, signup_tab, reset_tab = st.tabs(["Log in", "Create profile", "Reset password"])
        with login_tab:
            st.markdown("### Welcome back")
            st.caption("Enter your email or username and your password.")
            with st.form("vf_login_form", clear_on_submit=False):
                identifier = st.text_input("Email or username", placeholder="you@example.com or username")
                password = st.text_input("Password", type="password", placeholder="Your secure password")
                submitted = st.form_submit_button("Log in →", type="primary", use_container_width=True)
            if submitted:
                ok, message = auth_service.login_user(identifier, password)
                if ok:
                    st.session_state["vf_notice"] = ("success", message)
                    st.rerun()
                else:
                    st.error(message)
        with signup_tab:
            st.markdown("### Your profile starts here")
            st.caption("Your name will appear in the dashboard greeting: “Hey, [your name]!”")
            with st.form("vf_signup_form", clear_on_submit=False):
                full_name = st.text_input("Full name", placeholder="Your name")
                username = st.text_input("Username", placeholder="alex.fit")
                email = st.text_input("Email address", placeholder="you@example.com")
                pass1 = st.text_input("Create password", type="password", placeholder="At least 12 characters")
                pass2 = st.text_input("Confirm password", type="password")
                st.markdown('<div class="vf-footnote">Use 12+ characters with uppercase, lowercase, a number and a symbol. Avoid reusing an important password.</div>', unsafe_allow_html=True)
                submitted = st.form_submit_button("Create my account →", type="primary", use_container_width=True)
            if submitted:
                if pass1 != pass2:
                    st.error("The passwords do not match.")
                else:
                    ok, message = auth_service.register_user(full_name, username, email, pass1)
                    if ok:
                        st.success(message)
                        if st.session_state.get("vf_user"):
                            st.rerun()
                    else:
                        st.error(message)
        with reset_tab:
            st.markdown("### Reset your password")
            st.caption("For cloud accounts, a reset link is sent by Supabase Auth.")
            with st.form("vf_reset_form"):
                reset_email = st.text_input("Account email", placeholder="you@example.com")
                reset_submit = st.form_submit_button("Send reset link", use_container_width=True)
            if reset_submit:
                ok, message = auth_service.send_password_reset(reset_email)
                (st.success if ok else st.warning)(message)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    if not db.is_cloud_mode():
        st.info("Local mode is active for testing. Before deploying to Streamlit Cloud, configure Supabase in Streamlit Secrets so accounts and progress persist across cloud restarts and devices.")
    else:
        st.caption("Secure cloud authentication is powered by Supabase Auth.")


def render_header() -> None:
    p = profile()
    full_name = (p.get("full_name") or "Athlete").strip()
    username = p.get("username") or "athlete"
    c1, c2 = st.columns([3, 2], vertical_alignment="center")
    with c1:
        st.markdown('<div class="vf-brand"><span class="vf-brand-mark">R</span><span>RepTrack</span><span class="vf-chip">TRACK · TRAIN · GROW</span></div>', unsafe_allow_html=True)
    with c2:
        r1, r2 = st.columns([3, 1], vertical_alignment="center")
        with r1:
            st.markdown(f'<div style="text-align:right"><div style="font-weight:800">{html.escape(full_name)}</div><div class="vf-muted" style="font-size:.78rem">@{html.escape(username)}</div></div>', unsafe_allow_html=True)
        with r2:
            st.markdown(f'<div style="display:flex;justify-content:center;align-items:center;width:40px;height:40px;margin-left:auto;border-radius:50%;background:var(--vf-lime);color:#151a0b;font-weight:900;font-size:1.05rem">{html.escape((full_name[:1] or "V").upper())}</div>', unsafe_allow_html=True)
    st.markdown('<div class="vf-divider"></div>', unsafe_allow_html=True)
    pages = [("Home", "⌂"), ("Workout", "↗"), ("Calendar", "▦"), ("Progress", "⌁"), ("Profile", "◉")]
    current = st.session_state.get("vf_page", "Home")
    cols = st.columns(5, gap="small")
    for col, (name, icon) in zip(cols, pages):
        with col:
            if st.button(f"{icon}  {name}", key=f"nav_{name.lower()}", type="primary" if current == name else "secondary", use_container_width=True):
                st.session_state["vf_page"] = name
                st.session_state.pop("vf_selected_workout_exercise_id", None)
                st.rerun()
    with st.sidebar:
        st.markdown('<div class="vf-brand"><span class="vf-brand-mark">R</span><span>RepTrack</span></div>', unsafe_allow_html=True)
        st.caption("Your personal training space")
        st.markdown(f"**{full_name}**")
        st.caption(f"@{username}")
        st.markdown("---")
        st.markdown("**Quick navigation**")
        for name, icon in pages:
            if st.button(f"{icon}  {name}", key=f"side_{name.lower()}", use_container_width=True, type="primary" if current == name else "secondary"):
                st.session_state["vf_page"] = name
                st.session_state.pop("vf_selected_workout_exercise_id", None)
                st.rerun()
        st.markdown("---")
        if db.is_cloud_mode():
            st.success("Cloud sync enabled", icon="☁️")
        else:
            st.warning("Local testing mode", icon="💻")
            st.caption("Configure Supabase before cloud deployment to retain data across restarts.")
        if st.button("Log out", key="vf_logout", use_container_width=True):
            auth_service.logout_user()
            st.rerun()
        st.markdown('<div class="vf-footnote">RepTrack · Private by design. Keep your credentials safe.</div>', unsafe_allow_html=True)


def render_home() -> None:
    p = profile()
    full_name = (p.get("full_name") or "Athlete").strip()
    first_name = full_name.split()[0] if full_name else "Athlete"
    unit = p.get("preferred_unit") or "kg"
    today = now_local().date()
    sessions = user_rows("workout_sessions", order_by="workout_date", descending=True)
    completed = [w for w in sessions if w.get("status") == "completed"]
    week_start = today - timedelta(days=today.weekday())
    week_count = sum(1 for w in completed if week_start.isoformat() <= str(w.get("workout_date"))[:10] <= today.isoformat())
    weights = user_rows("body_weight_entries", order_by="entry_date", descending=True)
    current_weight = float(weights[0]["weight_kg"]) if weights else None
    active = get_active_workout()

    hero("YOUR TRAINING SPACE", f"Hey, {first_name}.", "What are we training today? Make every set count.")
    if active:
        st.markdown('<div class="vf-card" style="border-color:rgba(195,245,60,.45);margin-bottom:1rem"><div class="vf-eyebrow">WORKOUT IN PROGRESS</div><h3 style="margin-top:0">Pick up where you left off</h3><div class="vf-muted">Started ' + html.escape(str(active.get("workout_date", "today"))) + ' · ' + html.escape(active.get("muscle_groups") or "Custom workout") + '</div></div>', unsafe_allow_html=True)
        if st.button("Resume workout →", type="primary", use_container_width=True):
            set_page("Workout")
            st.rerun()
    weekly_goal = int(p.get("weekly_goal") if p.get("weekly_goal") is not None else 4)
    m1, m2, m3, m4 = st.columns(4, gap="small")
    with m1: metric_card("WORKOUTS DONE", str(len(completed)), "All-time completed sessions", "↗")
    with m2: metric_card("THIS WEEK", f"{week_count}/{weekly_goal}" if weekly_goal > 0 else str(week_count), "Sessions toward your goal" if weekly_goal > 0 else "No weekly target set", "▦")
    with m3: metric_card("CURRENT STREAK", f"{current_streak(sessions, today)} days", "Consecutive completed days", "✦")
    with m4: metric_card("LATEST WEIGHT", body_weight_display(current_weight, unit), "Most recent entry", "◎")

    section("Start your next session", "Choose a muscle group, log your sets, and keep moving.")
    c1, c2, c3 = st.columns([1, 1, 1], gap="medium")
    with c1:
        st.markdown('<div class="vf-card"><div style="font-size:1.6rem;color:var(--vf-lime)">↗</div><h3>Start a workout</h3><div class="vf-muted">Select muscles and build your exercise list.</div></div>', unsafe_allow_html=True)
        if st.button("Choose muscle groups →", key="home_choose", type="primary", use_container_width=True):
            set_page("Workout"); st.rerun()
    with c2:
        st.markdown('<div class="vf-card"><div style="font-size:1.6rem;color:var(--vf-lime)">▦</div><h3>View your calendar</h3><div class="vf-muted">See workout days and revisit any session.</div></div>', unsafe_allow_html=True)
        if st.button("Open calendar →", key="home_calendar", use_container_width=True):
            set_page("Calendar"); st.rerun()
    with c3:
        st.markdown('<div class="vf-card"><div style="font-size:1.6rem;color:var(--vf-lime)">⌁</div><h3>Check your progress</h3><div class="vf-muted">Track body weight, volume and consistency.</div></div>', unsafe_allow_html=True)
        if st.button("View progress →", key="home_progress", use_container_width=True):
            set_page("Progress"); st.rerun()

    section("Log body weight", "One entry per date. Your graph updates from saved measurements.")
    last_entry = next((w for w in weights if str(w.get("entry_date"))[:10] == today.isoformat()), None)
    default_weight = kg_to_unit(float(last_entry["weight_kg"]), unit) if last_entry else (kg_to_unit(current_weight, unit) if current_weight else 70.0)
    with st.form("home_weight_form"):
        cols = st.columns([1, 1.2, 2])
        with cols[0]: weight_date = st.date_input("Date", value=today, key="home_weight_date")
        with cols[1]: weight_value = st.number_input(f"Body weight ({unit})", min_value=1.0, max_value=500.0, value=float(default_weight), step=0.1, key="home_weight_value")
        with cols[2]: weight_note = st.text_input("Note (optional)", placeholder="Morning weigh-in, after rest day…", key="home_weight_note")
        save = st.form_submit_button("Save weight entry", type="primary", use_container_width=True)
    if save:
        try:
            save_weight(weight_date, weight_value, unit, weight_note)
            st.success(f"Saved {weight_value:.1f} {unit} for {weight_date.strftime('%d %b %Y')}.")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not save weight: {exc}")

    section("Recent workouts", "Your most recent completed sessions.")
    if not completed:
        st.markdown('<div class="vf-card"><h4>No workouts recorded yet</h4><div class="vf-muted">Your first completed workout will appear here. Start simple and build consistency.</div></div>', unsafe_allow_html=True)
    else:
        for workout in completed[:3]:
            col1, col2 = st.columns([4, 1], vertical_alignment="center")
            with col1:
                st.markdown(f"**{html.escape(str(workout.get('workout_date')))}**  ·  {html.escape(workout.get('muscle_groups') or 'Workout')}  \n<span class='vf-muted'>{html.escape(workout.get('notes') or 'Session completed')}</span>", unsafe_allow_html=True)
            with col2:
                if st.button("View log", key=f"home_w_{workout['id']}", use_container_width=True):
                    st.session_state["vf_calendar_selected"] = str(workout.get("workout_date"))[:10]
                    set_page("Calendar"); st.rerun()


def start_workout(muscles: list[str]) -> None:
    if not muscles:
        st.warning("Choose at least one muscle group first.")
        return
    existing = get_active_workout()
    if existing:
        st.session_state["vf_active_workout_id"] = existing["id"]
        st.info("You already have an active session. Resume it below.")
        return
    now = now_local()
    row = db.insert_row("workout_sessions", {
        "user_id": uid(), "workout_date": now.date().isoformat(), "started_at": now.isoformat(),
        "status": "active", "muscle_groups": ", ".join(muscles), "notes": "", "ended_at": None, "duration_minutes": None,
    })
    st.session_state["vf_active_workout_id"] = row["id"]
    st.session_state.pop("vf_selected_workout_exercise_id", None)
    st.session_state["vf_notice"] = ("success", "Workout started. Your sets will save to your account as you log them.")
    st.rerun()


def add_exercise_to_workout(workout: dict, exercise: dict) -> None:
    existing = db.select_rows("workout_exercises", {"workout_id": workout["id"], "user_id": uid(), "exercise_id": exercise["id"]}, limit=1)
    # Re-adding an exercise is allowed intentionally, since a workout may repeat a movement.
    rows = get_workout_exercises(workout["id"])
    db.insert_row("workout_exercises", {
        "user_id": uid(), "workout_id": workout["id"], "exercise_id": exercise["id"],
        "exercise_name": exercise["name"], "sort_order": len(rows), "notes": "",
    })


def render_exercise_detail(workout: dict, workout_exercise: dict) -> None:
    all_ex = load_exercises()
    ex = next((item for item in all_ex if item.get("id") == workout_exercise.get("exercise_id")), None)
    if not ex:
        ex = {"name": workout_exercise.get("exercise_name", "Exercise"), "muscle_group": "Custom", "target_muscles": "", "equipment": "", "difficulty": "Beginner", "instructions": "Add your technique notes below.", "video_url": ""}
    if st.button("← Back to workout", key="exercise_back"):
        st.session_state.pop("vf_selected_workout_exercise_id", None); st.rerun()
    hero("EXERCISE DETAIL", ex.get("name", "Exercise"), f"{ex.get('muscle_group','')} · {ex.get('equipment','Bodyweight')} · {ex.get('difficulty','Beginner')}")
    col1, col2 = st.columns([1, 1.45], gap="large")
    with col1:
        st.markdown('<div class="vf-card"><div class="vf-exercise-visual" style="height:160px;font-size:3.2rem">' + html.escape(MUSCLE_EMOJI.get(ex.get("muscle_group"), "↗")) + '</div><div style="margin-top:.8rem"><span class="vf-pill">' + html.escape(ex.get("muscle_group", "Exercise")) + '</span><span class="vf-pill">' + html.escape(ex.get("difficulty", "Beginner")) + '</span></div><h3>Target muscles</h3><div class="vf-muted">' + html.escape(ex.get("target_muscles") or "See exercise notes") + '</div><div class="vf-divider"></div><h3>Equipment</h3><div class="vf-muted">' + html.escape(ex.get("equipment") or "As required") + '</div></div>', unsafe_allow_html=True)
        if ex.get("video_url"):
            st.link_button("Watch exercise demo ↗", ex["video_url"], use_container_width=True)
    with col2:
        st.markdown('<div class="vf-card"><h3>How to perform it</h3><div style="white-space:pre-wrap;line-height:1.7;color:var(--vf-text)">' + html.escape(ex.get("instructions") or "Add your own form notes.") + '</div><div class="vf-divider"></div><h4>Quick form reminders</h4><div class="vf-muted">Move with control, keep a comfortable range of motion, and stop if you feel sharp pain. Use a load you can manage with good technique.</div></div>', unsafe_allow_html=True)
        with st.expander("Add personal technique notes"):
            with st.form(f"exercise_note_{workout_exercise['id']}"):
                notes = st.text_area("My cues / machine setup", value=workout_exercise.get("notes") or "", height=100)
                if st.form_submit_button("Save notes", type="primary"):
                    db.update_rows("workout_exercises", {"id": workout_exercise["id"], "user_id": uid()}, {"notes": notes})
                    st.success("Notes saved."); st.rerun()
    st.markdown("### Log your sets")
    unit = profile().get("preferred_unit") or "kg"
    sets = get_sets(workout_exercise["id"])
    if sets:
        completed = sum(1 for s in sets if bool(s.get("completed")))
        volume = workout_volume(sets)
        a, b, c = st.columns(3)
        with a: metric_card("SETS LOGGED", str(len(sets)), f"{completed} marked complete", "#")
        with b: metric_card("REPS", str(total_reps(sets)), "Across completed sets", "↗")
        with c: metric_card("VOLUME", f"{kg_to_unit(volume, unit):,.0f} {unit}", "Weight × reps; completed sets", "⌁")
        for row in sets:
            label = f"Set {row.get('set_number')} · {kg_to_unit(float(row.get('weight_kg') or 0), unit):g} {unit} × {int(row.get('reps') or 0)} reps"
            with st.expander(("✅ " if bool(row.get("completed")) else "◯ ") + label):
                with st.form(f"edit_set_{row['id']}"):
                    e1, e2, e3, e4 = st.columns([1.2, 1, 1, 1])
                    with e1: w = st.number_input(f"Weight ({unit})", min_value=0.0, max_value=1000.0, value=float(kg_to_unit(float(row.get("weight_kg") or 0), unit)), step=0.5, key=f"set_w_{row['id']}")
                    with e2: reps = st.number_input("Reps", min_value=0, max_value=500, value=int(row.get("reps") or 0), step=1, key=f"set_r_{row['id']}")
                    with e3: rpe = st.number_input("RPE (0 = skip)", min_value=0.0, max_value=10.0, value=float(row.get("rpe") or 0), step=0.5, key=f"set_rpe_{row['id']}")
                    with e4: done = st.checkbox("Completed", value=bool(row.get("completed")), key=f"set_done_{row['id']}")
                    save = st.form_submit_button("Save set changes", type="primary")
                if save:
                    db.update_rows("workout_sets", {"id": row["id"], "user_id": uid()}, {"weight_kg": round(unit_to_kg(float(w), unit), 3), "reps": int(reps), "rpe": float(rpe) if rpe else None, "completed": bool(done)})
                    st.success("Set updated."); st.rerun()
                if st.button("Delete this set", key=f"delete_set_{row['id']}"):
                    db.delete_rows("workout_sets", {"id": row["id"], "user_id": uid()})
                    st.rerun()
    else:
        st.caption("No sets yet. Log your first set below.")
    with st.form(f"add_set_{workout_exercise['id']}"):
        st.markdown("**Add a set**")
        last = sets[-1] if sets else None
        default_weight = kg_to_unit(float(last.get("weight_kg") or 0), unit) if last else 0.0
        default_reps = int(last.get("reps") or 10) if last else 10
        s1, s2, s3 = st.columns([1.2, 1, 1])
        with s1: new_weight = st.number_input(f"Weight ({unit})", min_value=0.0, max_value=1000.0, value=float(default_weight), step=0.5, key=f"new_weight_{workout_exercise['id']}")
        with s2: new_reps = st.number_input("Repetitions", min_value=1, max_value=500, value=default_reps, step=1, key=f"new_reps_{workout_exercise['id']}")
        with s3: new_rpe = st.number_input("RPE (0 = skip)", min_value=0.0, max_value=10.0, value=0.0, step=0.5, key=f"new_rpe_{workout_exercise['id']}")
        added = st.form_submit_button("＋ Save completed set", type="primary", use_container_width=True)
    if added:
        number = max([int(x.get("set_number") or 0) for x in sets], default=0) + 1
        db.insert_row("workout_sets", {"user_id": uid(), "workout_id": workout["id"], "workout_exercise_id": workout_exercise["id"],
                                        "set_number": number, "weight_kg": round(unit_to_kg(float(new_weight), unit), 3),
                                        "reps": int(new_reps), "rpe": float(new_rpe) if new_rpe else None, "completed": True})
        st.success(f"Set {number} saved to your workout."); st.rerun()


def render_workout() -> None:
    active = get_active_workout()
    if not active:
        hero("WORKOUT BUILDER", "Build today's session.", "Pick your focus. Your selected exercises and sets are saved as you go.")
        st.markdown("#### Choose muscle groups")
        st.caption("Select one or more. You can combine Back + Biceps, Chest + Triceps, or build your own split.")
        if "vf_muscle_choices" not in st.session_state:
            st.session_state["vf_muscle_choices"] = []
        cols = st.columns(3, gap="small")
        selected_now = []
        for i, (muscle, symbol, desc) in enumerate(MUSCLES):
            with cols[i % 3]:
                st.markdown(f'<div class="vf-card" style="margin-bottom:.5rem;min-height:78px"><div style="font-size:1.4rem;color:var(--vf-lime)">{html.escape(symbol)}</div><div style="font-weight:800">{html.escape(muscle)}</div><div class="vf-muted" style="font-size:.78rem">{html.escape(desc)}</div></div>', unsafe_allow_html=True)
                key = "muscle_pick_" + muscle.replace(" ", "_").replace("/", "_")
                is_default = muscle in st.session_state["vf_muscle_choices"]
                checked = st.checkbox(f"Select {muscle}", value=is_default, key=key)
                if checked: selected_now.append(muscle)
        st.session_state["vf_muscle_choices"] = selected_now
        if selected_now:
            st.markdown("**Selected:** " + " · ".join(f"`{m}`" for m in selected_now))
        if st.button("Start workout →", type="primary", use_container_width=True):
            try:
                start_workout(selected_now)
            except Exception as exc:
                st.error(f"Could not start workout: {exc}")
        with st.expander("Build a custom workout instead"):
            st.caption("Choose any muscle group and then add your own exercises once the session starts.")
        return

    selected_detail_id = st.session_state.get("vf_selected_workout_exercise_id")
    if selected_detail_id:
        row = db.select_rows("workout_exercises", {"id": selected_detail_id, "workout_id": active["id"], "user_id": uid()}, limit=1)
        if row:
            render_exercise_detail(active, row[0])
            return
        st.session_state.pop("vf_selected_workout_exercise_id", None)

    hero("ACTIVE SESSION", "Let's get to work.", f"{active.get('workout_date')} · {active.get('muscle_groups') or 'Custom workout'}")
    duration_txt = ""
    try:
        started = datetime.fromisoformat(str(active.get("started_at")).replace("Z", "+00:00"))
        elapsed = max(0, int((now_local() - started.astimezone(ZoneInfo("Asia/Kolkata"))).total_seconds() // 60))
        duration_txt = f"{elapsed} min elapsed"
    except Exception:
        pass
    exercises = get_workout_exercises(active["id"])
    all_sets = db.select_rows("workout_sets", {"workout_id": active["id"], "user_id": uid()})
    c1, c2, c3 = st.columns(3)
    with c1: metric_card("EXERCISES", str(len(exercises)), "Movements in this session", "↗")
    with c2: metric_card("SETS LOGGED", str(len(all_sets)), "Saved automatically", "#")
    with c3: metric_card("SESSION TIME", duration_txt or "In progress", "Time since start", "◷")

    section("Add exercises", "Tap any exercise to add it to today's training.")
    all_exercises = load_exercises()
    group_names = [x.strip() for x in (active.get("muscle_groups") or "").split(",") if x.strip()]
    default_library = [e for e in all_exercises if e.get("muscle_group") in group_names]
    if not default_library:
        default_library = all_exercises
    search = st.text_input("Search exercise library", placeholder="Try T-Bar Row, Lat Pulldown…", key="exercise_search")
    filtered = [e for e in default_library if search.lower() in e.get("name", "").lower() or search.lower() in e.get("muscle_group", "").lower()]
    if not filtered:
        st.info("No exercises match that search. Clear it or create a custom exercise below.")
    else:
        grid = st.columns(3, gap="medium")
        for idx, exercise in enumerate(filtered):
            with grid[idx % 3]:
                st.markdown(f'<div class="vf-exercise"><div class="vf-exercise-visual">{html.escape(MUSCLE_EMOJI.get(exercise.get("muscle_group"), "↗"))}</div><div style="display:flex;gap:5px;flex-wrap:wrap;margin-top:.65rem"><span class="vf-pill">{html.escape(exercise.get("muscle_group", ""))}</span></div><h4 style="margin:.55rem 0 .25rem">{html.escape(exercise.get("name", "Exercise"))}</h4><div class="vf-muted" style="font-size:.8rem;min-height:2.3rem">{html.escape(exercise.get("target_muscles") or exercise.get("equipment") or "Gym movement")}</div></div>', unsafe_allow_html=True)
                if st.button("＋ Add exercise", key=f"add_ex_{active['id']}_{exercise['id']}", use_container_width=True):
                    try:
                        add_exercise_to_workout(active, exercise)
                        st.success(f"{exercise['name']} added."); st.rerun()
                    except Exception as exc:
                        st.error(f"Could not add exercise: {exc}")
                if exercise.get("video_url") and st.button("View demo ↗", key=f"demo_ex_{active['id']}_{exercise['id']}", use_container_width=True):
                    st.link_button("Open demo", exercise["video_url"])

    with st.expander("＋ Create a custom exercise"):
        with st.form("custom_exercise_form"):
            n1, n2 = st.columns(2)
            with n1: custom_name = st.text_input("Exercise name", placeholder="Incline cable curl")
            with n2: custom_group = st.selectbox("Muscle group", [m[0] for m in MUSCLES], index=0)
            target = st.text_input("Target muscles", placeholder="Biceps, brachialis")
            equipment = st.text_input("Equipment", placeholder="Cable machine")
            difficulty = st.selectbox("Difficulty", ["Beginner", "Intermediate", "Advanced"])
            instructions = st.text_area("How to perform it", placeholder="Starting position, movement cues, common mistakes…")
            video = st.text_input("Demo URL (optional)", placeholder="https://…")
            custom_submit = st.form_submit_button("Save custom exercise", type="primary")
        if custom_submit:
            if not custom_name.strip():
                st.error("Enter an exercise name.")
            else:
                try:
                    created_exercise = db.insert_row("exercises", {"owner_id": uid(), "name": custom_name.strip(), "muscle_group": custom_group,
                        "target_muscles": target.strip(), "equipment": equipment.strip(), "difficulty": difficulty,
                        "instructions": instructions.strip(), "image_url": "", "video_url": video.strip(), "is_custom": True})
                    if created_exercise:
                        add_exercise_to_workout(active, created_exercise)
                    st.success("Custom exercise saved and added to this workout."); st.rerun()
                except Exception as exc:
                    st.error(f"Could not save custom exercise: {exc}")

    section("Today's exercise list", "Open an exercise to log each set individually.")
    exercises = get_workout_exercises(active["id"])
    if not exercises:
        st.markdown('<div class="vf-card"><h4>Your session is ready</h4><div class="vf-muted">Add exercises from the library above. Nothing is lost if you leave this page.</div></div>', unsafe_allow_html=True)
    else:
        for i, ex in enumerate(exercises):
            sets = get_sets(ex["id"])
            done_sets = sum(1 for s in sets if bool(s.get("completed")))
            col1, col2, col3 = st.columns([3, 1.2, 1], vertical_alignment="center")
            with col1:
                st.markdown(f"**{i+1:02d} · {html.escape(ex.get('exercise_name','Exercise'))}**  \n<span class='vf-muted'>{len(sets)} sets logged · {done_sets} completed</span>", unsafe_allow_html=True)
            with col2:
                if st.button("Log sets →", key=f"open_workout_ex_{ex['id']}", type="primary", use_container_width=True):
                    st.session_state["vf_selected_workout_exercise_id"] = ex["id"]; st.rerun()
            with col3:
                if st.button("Remove", key=f"remove_workout_ex_{ex['id']}", use_container_width=True):
                    for s in db.select_rows("workout_sets", {"workout_exercise_id": ex["id"], "user_id": uid()}):
                        db.delete_rows("workout_sets", {"id": s["id"], "user_id": uid()})
                    db.delete_rows("workout_exercises", {"id": ex["id"], "user_id": uid()})
                    st.rerun()
            st.markdown('<div class="vf-divider"></div>', unsafe_allow_html=True)

    with st.expander("Session notes"):
        with st.form(f"session_notes_{active['id']}"):
            notes = st.text_area("Notes", value=active.get("notes") or "", placeholder="Energy, technique cues, what to improve next time…")
            if st.form_submit_button("Save session notes"):
                db.update_rows("workout_sessions", {"id": active["id"], "user_id": uid()}, {"notes": notes})
                st.success("Session notes saved."); st.rerun()

    st.markdown('<div class="vf-divider"></div>', unsafe_allow_html=True)
    f1, f2 = st.columns([1, 1])
    with f1:
        if st.button("Finish workout ✓", key="finish_workout_start", type="primary", use_container_width=True):
            st.session_state["vf_confirm_finish_workout"] = True
    with f2:
        if st.button("Abandon session", key="abandon_workout", use_container_width=True):
            st.session_state["vf_confirm_abandon_workout"] = True
    if st.session_state.get("vf_confirm_finish_workout"):
        st.warning("Finish and save this session as a completed gym day?")
        summary_exercises = get_workout_exercises(active["id"])
        summary_sets = db.select_rows("workout_sets", {"workout_id": active["id"], "user_id": uid()})
        summary_unit = profile().get("preferred_unit") or "kg"
        sum1, sum2, sum3 = st.columns(3)
        with sum1: metric_card("EXERCISES", str(len(summary_exercises)), "In this session", "↗")
        with sum2: metric_card("SETS COMPLETED", str(sum(1 for s in summary_sets if bool(s.get("completed")))), f"{total_reps(summary_sets)} total reps", "#")
        with sum3: metric_card("TRAINING VOLUME", f"{kg_to_unit(workout_volume(summary_sets), summary_unit):,.0f} {summary_unit}", "Completed sets × reps", "⌁")
        y, n = st.columns(2)
        with y:
            if st.button("Yes, finish session", key="confirm_finish_yes", type="primary", use_container_width=True):
                now = now_local()
                try:
                    started = datetime.fromisoformat(str(active.get("started_at")).replace("Z", "+00:00")).astimezone(ZoneInfo("Asia/Kolkata"))
                    minutes = max(0, int((now - started).total_seconds() // 60))
                except Exception:
                    minutes = None
                db.update_rows("workout_sessions", {"id": active["id"], "user_id": uid(), "status": "active"}, {"status": "completed", "ended_at": now.isoformat(), "duration_minutes": minutes})
                st.session_state.pop("vf_confirm_finish_workout", None)
                st.session_state.pop("vf_active_workout_id", None)
                st.session_state.pop("vf_selected_workout_exercise_id", None)
                st.session_state["vf_notice"] = ("success", "Workout completed and saved to your calendar. Nice work!")
                st.rerun()
        with n:
            if st.button("Keep working", key="confirm_finish_no", use_container_width=True):
                st.session_state.pop("vf_confirm_finish_workout", None); st.rerun()
    if st.session_state.get("vf_confirm_abandon_workout"):
        st.warning("This session will be saved as abandoned and will not count as a completed gym day.")
        y, n = st.columns(2)
        with y:
            if st.button("Abandon session", key="confirm_abandon_yes", type="primary", use_container_width=True):
                db.update_rows("workout_sessions", {"id": active["id"], "user_id": uid(), "status": "active"}, {"status": "abandoned", "ended_at": now_local().isoformat()})
                st.session_state.pop("vf_confirm_abandon_workout", None); st.session_state.pop("vf_active_workout_id", None); st.session_state.pop("vf_selected_workout_exercise_id", None)
                st.rerun()
        with n:
            if st.button("Keep session", key="confirm_abandon_no", use_container_width=True):
                st.session_state.pop("vf_confirm_abandon_workout", None); st.rerun()


def render_calendar() -> None:
    hero("YOUR HISTORY", "Every session adds up.", "Pick a date to reopen your workout details, sets, and weight entry.")
    today = now_local().date()
    if "vf_calendar_month" not in st.session_state:
        st.session_state["vf_calendar_month"] = date(today.year, today.month, 1)
    month = st.session_state["vf_calendar_month"]
    prev_col, title_col, next_col = st.columns([1, 4, 1], vertical_alignment="center")
    with prev_col:
        if st.button("← Previous", key="calendar_prev", use_container_width=True):
            st.session_state["vf_calendar_month"] = date(month.year - (1 if month.month == 1 else 0), 12 if month.month == 1 else month.month - 1, 1); st.rerun()
    with title_col:
        st.markdown(f"<h2 style='text-align:center;margin:0'>{month.strftime('%B %Y')}</h2>", unsafe_allow_html=True)
    with next_col:
        if st.button("Next →", key="calendar_next", use_container_width=True):
            st.session_state["vf_calendar_month"] = date(month.year + (1 if month.month == 12 else 0), 1 if month.month == 12 else month.month + 1, 1); st.rerun()
    all_workouts = user_rows("workout_sessions", order_by="workout_date")
    completed_dates = {str(w.get("workout_date"))[:10] for w in all_workouts if w.get("status") == "completed"}
    active_dates = {str(w.get("workout_date"))[:10] for w in all_workouts if w.get("status") == "active"}
    selected_text = st.session_state.get("vf_calendar_selected", today.isoformat())
    try: selected_date = date.fromisoformat(str(selected_text)[:10])
    except Exception: selected_date = today
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    head_cols = st.columns(7, gap="small")
    for col, wd in zip(head_cols, weekdays):
        with col: st.markdown(f"<div style='text-align:center;color:var(--vf-muted);font-weight:800;font-size:.78rem;padding:.5rem 0'>{wd}</div>", unsafe_allow_html=True)
    weeks = pycalendar.monthcalendar(month.year, month.month)
    for week_i, week in enumerate(weeks):
        cols = st.columns(7, gap="small")
        for day_i, day_num in enumerate(week):
            with cols[day_i]:
                if not day_num:
                    st.markdown('<div style="height:2.9rem"></div>', unsafe_allow_html=True)
                    continue
                d = date(month.year, month.month, day_num)
                dstr = d.isoformat()
                mark = " ✓" if dstr in completed_dates else (" •" if dstr in active_dates else "")
                prefix = "• " if d == today and dstr not in completed_dates else ""
                label = f"{prefix}{day_num}{mark}"
                if st.button(label, key=f"cal_{dstr}", type="primary" if dstr == str(selected_text)[:10] else "secondary", use_container_width=True):
                    st.session_state["vf_calendar_selected"] = dstr; st.rerun()
    st.markdown('<div class="vf-divider"></div>', unsafe_allow_html=True)
    selected = date.fromisoformat(str(st.session_state.get("vf_calendar_selected", today.isoformat()))[:10])
    left, right = st.columns([1.5, 1], gap="large")
    with left:
        section(selected.strftime("%A, %d %B %Y"), "Workout history for the selected date")
        day_workouts = [w for w in all_workouts if str(w.get("workout_date"))[:10] == selected.isoformat()]
        if not day_workouts:
            st.markdown('<div class="vf-card"><h4>No saved workout for this date</h4><div class="vf-muted">Dates are not auto-marked. A check appears after you finish and save a session.</div></div>', unsafe_allow_html=True)
        for workout in day_workouts:
            status = workout.get("status", "")
            st.markdown(f'<div class="vf-card"><div class="vf-eyebrow">{html.escape(status.upper())}</div><h3 style="margin:0 0 .3rem">{html.escape(workout.get("muscle_groups") or "Workout")}</h3><div class="vf-muted">{html.escape(str(workout.get("duration_minutes") or "—"))} min · {html.escape(workout.get("notes") or "No notes")}</div></div>', unsafe_allow_html=True)
            exrows = get_workout_exercises(workout["id"])
            if exrows:
                for ex in exrows:
                    sets = db.select_rows("workout_sets", {"workout_exercise_id": ex["id"], "user_id": uid()}, order_by="set_number")
                    st.markdown(f"**{html.escape(ex.get('exercise_name','Exercise'))}**")
                    if sets:
                        unit = profile().get("preferred_unit") or "kg"
                        df = pd.DataFrame([{"Set":s.get("set_number"), f"Weight ({unit})":round(kg_to_unit(float(s.get("weight_kg") or 0), unit), 2), "Reps":s.get("reps"), "RPE":s.get("rpe") or "—", "Completed":"Yes" if bool(s.get("completed")) else "No"} for s in sets])
                        st.dataframe(df, hide_index=True, use_container_width=True)
                    else:
                        st.caption("No sets logged for this exercise.")
            if workout.get("status") == "active":
                if st.button("Resume this session", key=f"resume_calendar_{workout['id']}", type="primary"):
                    set_page("Workout"); st.rerun()
            if workout.get("status") in ("completed", "abandoned"):
                with st.expander("Edit date / notes"):
                    with st.form(f"edit_workout_{workout['id']}"):
                        new_date = st.date_input("Workout date", value=date.fromisoformat(str(workout.get("workout_date"))[:10]), key=f"wd_{workout['id']}")
                        new_notes = st.text_area("Notes", value=workout.get("notes") or "", key=f"wn_{workout['id']}")
                        save = st.form_submit_button("Save changes", type="primary")
                    if save:
                        db.update_rows("workout_sessions", {"id": workout["id"], "user_id": uid()}, {"workout_date": new_date.isoformat(), "notes": new_notes})
                        st.success("Workout updated."); st.rerun()
                if st.button("Delete this workout log", key=f"del_workout_{workout['id']}"):
                    st.session_state["vf_delete_workout_id"] = workout["id"]
                if st.session_state.get("vf_delete_workout_id") == workout["id"]:
                    st.warning("Delete this workout and its sets permanently?")
                    y, n = st.columns(2)
                    with y:
                        if st.button("Confirm delete", key=f"confirm_del_{workout['id']}", type="primary"):
                            exs = db.select_rows("workout_exercises", {"workout_id": workout["id"], "user_id": uid()})
                            for e in exs:
                                for s in db.select_rows("workout_sets", {"workout_exercise_id": e["id"], "user_id": uid()}): db.delete_rows("workout_sets", {"id": s["id"], "user_id": uid()})
                                db.delete_rows("workout_exercises", {"id": e["id"], "user_id": uid()})
                            db.delete_rows("workout_sessions", {"id": workout["id"], "user_id": uid()})
                            st.session_state.pop("vf_delete_workout_id", None); st.rerun()
                    with n:
                        if st.button("Cancel", key=f"cancel_del_{workout['id']}"):
                            st.session_state.pop("vf_delete_workout_id", None); st.rerun()
    with right:
        section("Day summary", "Your recorded activity")
        unit = profile().get("preferred_unit") or "kg"
        wt = db.select_rows("body_weight_entries", {"user_id": uid(), "entry_date": selected.isoformat()}, limit=1)
        st.markdown('<div class="vf-card"><div class="vf-metric-label">BODY WEIGHT</div><div class="vf-metric-value">' + html.escape(body_weight_display(float(wt[0]["weight_kg"]) if wt else None, unit)) + '</div><div class="vf-metric-foot">' + ("Saved for this date" if wt else "No measurement recorded") + '</div></div>', unsafe_allow_html=True)
        with st.form("calendar_weight_form"):
            old = kg_to_unit(float(wt[0]["weight_kg"]), unit) if wt else 70.0
            weight = st.number_input(f"Log weight ({unit})", min_value=1.0, max_value=500.0, value=float(old), step=0.1)
            note = st.text_input("Note (optional)", value=(wt[0].get("notes") or "") if wt else "")
            save = st.form_submit_button("Save weight for selected date", type="primary", use_container_width=True)
        if save:
            save_weight(selected, weight, unit, note); st.success("Weight saved."); st.rerun()
        st.markdown('<div class="vf-card"><div class="vf-metric-label">DAY STATUS</div><div style="font-size:1rem;font-weight:800">' + ("Workout completed ✓" if selected.isoformat() in completed_dates else ("Workout in progress" if selected.isoformat() in active_dates else "No completed workout")) + '</div><div class="vf-metric-foot">Rest days are not automatically marked as missed.</div></div>', unsafe_allow_html=True)


def render_progress() -> None:
    hero("PROGRESS LAB", "Progress you can measure.", "All charts are built from your saved workouts and weigh-ins—not sample data.")
    p = profile(); unit = p.get("preferred_unit") or "kg"; today = now_local().date()
    workouts = user_rows("workout_sessions", order_by="workout_date")
    completed = [w for w in workouts if w.get("status") == "completed"]
    weights = user_rows("body_weight_entries", order_by="entry_date")
    sets = user_rows("workout_sets", order_by="created_at")
    completed_ids = {w["id"] for w in completed}
    completed_sets = [s for s in sets if s.get("workout_id") in completed_ids and bool(s.get("completed", True))]
    week_start = today - timedelta(days=today.weekday())
    weekly = sum(1 for w in completed if week_start.isoformat() <= str(w.get("workout_date"))[:10] <= today.isoformat())
    goal = int(p.get("weekly_goal") if p.get("weekly_goal") is not None else 4)
    cols = st.columns(4, gap="small")
    with cols[0]: metric_card("TOTAL WORKOUTS", str(len(completed)), "Completed sessions", "↗")
    with cols[1]: metric_card("THIS WEEK", f"{weekly}/{goal}", "Weekly target", "▦")
    with cols[2]: metric_card("LONGEST STREAK", f"{longest_streak(workouts)} days", "Consecutive workout dates", "✦")
    with cols[3]: metric_card("TRAINING VOLUME", f"{kg_to_unit(workout_volume(completed_sets), unit):,.0f} {unit}", "Completed sets × reps", "⌁")
    progress_pct = min(weekly / goal, 1) * 100 if goal > 0 else 0
    progress_label = f"{min(weekly, goal)} of {goal} sessions logged" if goal > 0 else f"{weekly} sessions logged · no weekly target set"
    progress_percent_label = f"{round(progress_pct)}%" if goal > 0 else "—"
    st.markdown('<div class="vf-card" style="margin-top:1rem"><div style="display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap"><div><div class="vf-metric-label">WEEKLY CONSISTENCY</div><div style="font-weight:800;font-size:1.05rem">' + html.escape(progress_label) + '</div></div><div style="color:var(--vf-lime);font-weight:850;font-size:1.4rem">' + html.escape(progress_percent_label) + '</div></div><div class="vf-progress-track" style="margin-top:.8rem"><div class="vf-progress-fill" style="width:' + str(progress_pct) + '%"></div></div></div>', unsafe_allow_html=True)

    section("Body weight", "Choose a window to explore your measurements.")
    period = st.selectbox("Time range", ["7 days", "30 days", "90 days", "6 months", "1 year", "All time"], index=1, key="weight_period")
    days_map = {"7 days":7, "30 days":30, "90 days":90, "6 months":183, "1 year":365}
    filtered_weights = weights if period == "All time" else [w for w in weights if str(w.get("entry_date"))[:10] >= (today - timedelta(days=days_map[period]-1)).isoformat()]
    if filtered_weights:
        df = pd.DataFrame([{"Date": pd.to_datetime(str(w["entry_date"])[:10]), f"Weight ({unit})": round(kg_to_unit(float(w["weight_kg"]), unit), 2), "Notes": w.get("notes") or ""} for w in filtered_weights])
        fig = px.line(df, x="Date", y=f"Weight ({unit})", markers=True, hover_data=["Notes"], template="plotly_dark" if p.get("theme", "dark") == "dark" else "plotly_white")
        fig.update_traces(line=dict(color="#c3f53c", width=3), marker=dict(size=7, color="#c3f53c"), hovertemplate="%{x|%d %b %Y}<br>%{y:.1f} " + unit + "<extra></extra>")
        if p.get("body_weight_goal_kg"):
            goal_line = kg_to_unit(float(p["body_weight_goal_kg"]), unit)
            fig.add_hline(y=goal_line, line_dash="dash", line_color="#9a86ff", annotation_text=f"Goal {goal_line:.1f} {unit}", annotation_position="top left")
        fig.update_layout(margin=dict(l=10,r=10,t=16,b=10), height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#d5d9e2" if p.get("theme", "dark") == "dark" else "#2d3340"), yaxis_title=f"Weight ({unit})", xaxis_title="", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        if len(filtered_weights) >= 2:
            first = float(filtered_weights[0]["weight_kg"]); last = float(filtered_weights[-1]["weight_kg"])
            change = kg_to_unit(last-first, unit)
            k1, k2, k3 = st.columns(3)
            with k1: metric_card("FIRST ENTRY", body_weight_display(first, unit), str(filtered_weights[0]["entry_date"]), "◎")
            with k2: metric_card("LATEST ENTRY", body_weight_display(last, unit), str(filtered_weights[-1]["entry_date"]), "◎")
            with k3: metric_card("NET CHANGE", f"{change:+.1f} {unit}", "Across selected measurements", "↕")
    else:
        st.markdown('<div class="vf-card"><h4>Your weight graph starts with your first entry</h4><div class="vf-muted">Log your body weight from Home or from the Calendar. No missing dates will be filled with invented values.</div></div>', unsafe_allow_html=True)

    section("Workout frequency", "Completed sessions by week.")
    if completed:
        wf = pd.DataFrame([{"Date":pd.to_datetime(str(w["workout_date"])[:10])} for w in completed])
        wf["Week"] = wf["Date"].dt.to_period("W-SUN").dt.start_time
        freq = wf.groupby("Week", as_index=False).size().rename(columns={"size":"Workouts"})
        fig2 = px.bar(freq, x="Week", y="Workouts", template="plotly_dark" if p.get("theme", "dark") == "dark" else "plotly_white")
        fig2.update_traces(marker_color="#c3f53c", marker_line_width=0)
        fig2.update_layout(margin=dict(l=10,r=10,t=12,b=10), height=280, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#d5d9e2" if p.get("theme", "dark") == "dark" else "#2d3340"), xaxis_title="Week", yaxis_title="Completed workouts")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Finish a workout to start seeing your training-frequency chart.")

    section("Muscle-group balance", "Based on the muscle groups saved in completed sessions.")
    muscle_counts = {}
    for w in completed:
        for g in [x.strip() for x in (w.get("muscle_groups") or "").split(",") if x.strip()]: muscle_counts[g] = muscle_counts.get(g, 0) + 1
    if muscle_counts:
        mf = pd.DataFrame([{"Muscle group":k, "Sessions":v} for k,v in sorted(muscle_counts.items(), key=lambda item:item[1], reverse=True)])
        fig3 = px.bar(mf, x="Sessions", y="Muscle group", orientation="h", template="plotly_dark" if p.get("theme", "dark") == "dark" else "plotly_white")
        fig3.update_traces(marker_color="#c3f53c", marker_line_width=0)
        fig3.update_layout(margin=dict(l=10,r=10,t=12,b=10), height=max(260, len(mf)*35), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#d5d9e2" if p.get("theme", "dark") == "dark" else "#2d3340"), xaxis_title="Sessions", yaxis_title="")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.caption("Completed workouts will appear here once you have saved them.")

    section("Personal records", "Highest saved completed-set weight per exercise.")
    completed_exercises = db.select_rows("workout_exercises", {"user_id": uid()})
    exercise_map = {e["id"]: e.get("exercise_name", "Exercise") for e in completed_exercises}
    records = {}
    for s in completed_sets:
        name = exercise_map.get(s.get("workout_exercise_id"), "Exercise")
        weight = float(s.get("weight_kg") or 0)
        if name not in records or weight > records[name]: records[name] = weight
    if records:
        pr_df = pd.DataFrame([{"Exercise":k, f"Best weight ({unit})":round(kg_to_unit(v, unit),2)} for k,v in sorted(records.items(), key=lambda x:x[1], reverse=True)])
        st.dataframe(pr_df, hide_index=True, use_container_width=True)
    else:
        st.caption("Personal records will show up after you finish a workout with logged sets.")


def render_profile() -> None:
    p = profile()
    full_name = p.get("full_name") or "Athlete"
    hero("YOUR ACCOUNT", "Your profile. Your progress.", "Personalize how RepTrack tracks your training.")
    left, right = st.columns([1, 1.2], gap="large")
    with left:
        st.markdown('<div class="vf-card"><div style="display:flex;align-items:center;gap:1rem"><div style="height:66px;width:66px;border-radius:22px;display:flex;align-items:center;justify-content:center;background:var(--vf-lime);color:#14190b;font-size:1.8rem;font-weight:900">' + html.escape((full_name[:1] or "V").upper()) + '</div><div><h2 style="margin:0">' + html.escape(full_name) + '</h2><div class="vf-muted">@' + html.escape(p.get("username") or "athlete") + '</div><div class="vf-muted" style="font-size:.8rem">' + html.escape(p.get("email") or "") + '</div></div></div><div class="vf-divider"></div><div class="vf-metric-label">MEMBER SINCE</div><div style="font-weight:750">' + html.escape(str(p.get("created_at", "—"))[:10]) + '</div><div class="vf-metric-foot">Your account and training records are private to you.</div></div>', unsafe_allow_html=True)
        section("Account security", "Use a strong password and keep it private.")
        with st.expander("Change password"):
            if db.is_cloud_mode():
                with st.form("change_password_form"):
                    pw1 = st.text_input("New password", type="password")
                    pw2 = st.text_input("Confirm new password", type="password")
                    change = st.form_submit_button("Update password", type="primary")
                if change:
                    issues = auth_service.validate_password(pw1)
                    if pw1 != pw2: st.error("Passwords do not match.")
                    elif issues: st.error(" ".join(issues))
                    else:
                        try:
                            client = db.supabase_client(authenticated=True)
                            client.auth.update_user({"password": pw1})
                            st.success("Password updated.")
                        except Exception as exc: st.error(f"Could not update password: {exc}")
            else:
                st.info("Local testing mode stores a salted PBKDF2 password hash. Change it after deploying cloud authentication or use a fresh local account. The cloud password-reset flow becomes available after Supabase is configured.")
    with right:
        section("Profile settings", "Your name appears in the “Hey, [name]” home greeting.")
        with st.form("profile_settings_form"):
            name = st.text_input("Full name", value=p.get("full_name") or "")
            username = st.text_input("Username", value=p.get("username") or "")
            unit = st.selectbox("Preferred weight unit", ["kg", "lb"], index=0 if (p.get("preferred_unit") or "kg") == "kg" else 1)
            theme = st.selectbox("Appearance", ["dark", "light"], index=0 if (p.get("theme") or "dark") == "dark" else 1)
            goal = st.number_input("Weekly workout goal", min_value=0, max_value=14, value=int(p.get("weekly_goal") if p.get("weekly_goal") is not None else 4), step=1, help="Set to 0 if you do not want a weekly target.")
            current_goal_kg = p.get("body_weight_goal_kg")
            goal_display = kg_to_unit(float(current_goal_kg), unit) if current_goal_kg else 0.0
            weight_goal = st.number_input(f"Optional body-weight goal ({unit}); 0 = none", min_value=0.0, max_value=500.0, value=float(goal_display), step=0.1)
            save = st.form_submit_button("Save profile settings", type="primary", use_container_width=True)
        if save:
            if not name.strip(): st.error("Full name cannot be blank.")
            elif not username.strip(): st.error("Username cannot be blank.")
            elif not all(c.isalnum() or c in "_.-" for c in username.strip()) or len(username.strip()) < 3: st.error("Username should be 3+ characters and use letters, numbers, dots, underscores or hyphens.")
            else:
                try:
                    updates = {"full_name": name.strip(), "username": username.strip().lower(), "preferred_unit": unit, "theme": theme, "weekly_goal": int(goal), "body_weight_goal_kg": round(unit_to_kg(weight_goal, unit), 2) if weight_goal else None}
                    db.update_rows("profiles", {"id": uid()}, updates)
                    fresh = db.select_rows("profiles", {"id": uid()}, limit=1)
                    if fresh: st.session_state["vf_profile"] = fresh[0]
                    st.success("Profile settings saved."); st.rerun()
                except Exception as exc: st.error(f"Could not save profile: {exc}")
        st.markdown('<div class="vf-card"><h4>Cloud sync</h4><div class="vf-muted">' + ("Supabase cloud database is configured. Sign in from another device with the same account to access synced records." if db.is_cloud_mode() else "This install currently uses a local SQLite file. Configure Supabase in Streamlit Secrets before deploying online; the Streamlit Cloud filesystem is not a durable personal database.") + '</div></div>', unsafe_allow_html=True)

    section("Export your data", "Download your saved information for your own records.")
    profile_export = {k:v for k,v in p.items() if k not in ("password", "password_hash", "salt")}
    export_data = {
        "profile": profile_export,
        "workout_sessions": user_rows("workout_sessions"),
        "workout_exercises": user_rows("workout_exercises"),
        "workout_sets": user_rows("workout_sets"),
        "body_weight_entries": user_rows("body_weight_entries"),
        "custom_exercises": db.select_rows("exercises", {"owner_id": uid()}),
    }
    a, b = st.columns(2)
    with a:
        st.download_button("Download JSON archive", data=json.dumps(export_data, indent=2, default=str), file_name=f"reptrack-export-{now_local().date().isoformat()}.json", mime="application/json", use_container_width=True)
    with b:
        all_sets = export_data["workout_sets"]
        st.download_button("Download sets CSV", data=pd.DataFrame(all_sets).to_csv(index=False), file_name="reptrack-sets.csv", mime="text/csv", use_container_width=True)


def main() -> None:
    try:
        db.init_database()
    except Exception as exc:
        st.error("Database setup did not finish.")
        st.exception(exc)
        st.stop()

    user = auth_service.current_user()
    theme = (st.session_state.get("vf_profile") or {}).get("theme", "dark") if user else "dark"
    inject_css(theme)

    if not user:
        render_auth()
        return

    if not st.session_state.get("vf_page"):
        st.session_state["vf_page"] = "Home"
    render_header()
    notice = st.session_state.pop("vf_notice", None)
    if notice:
        level, message = notice
        (st.success if level == "success" else st.info)(message)

    page = st.session_state.get("vf_page", "Home")
    try:
        if page == "Home": render_home()
        elif page == "Workout": render_workout()
        elif page == "Calendar": render_calendar()
        elif page == "Progress": render_progress()
        elif page == "Profile": render_profile()
        else: set_page("Home"); render_home()
    except Exception as exc:
        st.error("Something went wrong while loading this section. Your saved database records are not intentionally deleted.")
        st.caption("Check the error below if you are developing locally.")
        st.exception(exc)


if __name__ == "__main__":
    main()
