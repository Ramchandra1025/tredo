from datetime import date, datetime, timedelta, timezone
from functools import wraps
import math
import re
import sqlite3
import time
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from database import CATEGORIES, ensure_user_records, get_db, init_db

app = Flask(__name__, static_folder="../frontend/static", static_url_path="/static")
app.config.from_object(Config)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=Config.SESSION_COOKIE_SECURE,
    PERMANENT_SESSION_LIFETIME=timedelta(days=14),
    MAX_CONTENT_LENGTH=1024 * 1024,
)
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
LIFE_RECOVERY = timedelta(hours=4)
MAX_LIVES = 5
TRADER_TYPES = [
    {"id": "beginner", "label": "Beginner Trader"},
    {"id": "intraday", "label": "Intraday Trader"},
    {"id": "swing", "label": "Swing Trader"},
    {"id": "options", "label": "Options Trader"},
    {"id": "long_term", "label": "Long-Term Investor"},
]
AVATAR_OPTIONS = [
    {"id": "maya", "name": "Maya", "role": "Curious learner"},
    {"id": "ari", "name": "Ari", "role": "Chart explorer"},
    {"id": "candela", "name": "Candela", "role": "Friendly mentor"},
    {"id": "leo", "name": "Leo", "role": "Steady beginner"},
    {"id": "nia", "name": "Nia", "role": "Market strategist"},
]
TRADER_TYPE_IDS = {item["id"] for item in TRADER_TYPES}
AVATAR_IDS = {item["id"] for item in AVATAR_OPTIONS}
init_db()
_login_failures = {}
_LOGIN_WINDOW_SECONDS = 600
_LOGIN_MAX_FAILURES = 8


def _utcnow():
    return datetime.now(timezone.utc).replace(microsecond=0)


def _parse_datetime(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return _utcnow()
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _user_date(db, user_id):
    row = db.execute("SELECT timezone FROM user_settings WHERE user_id=?", (user_id,)).fetchone()
    try:
        zone = ZoneInfo(row["timezone"] if row else "UTC")
    except (ZoneInfoNotFoundError, TypeError):
        zone = timezone.utc
    return _utcnow().astimezone(zone).date()


def _notification(db, user_id, title, message, kind):
    db.execute(
        "INSERT INTO notifications(user_id,title,message,notification_type) VALUES(?,?,?,?)",
        (user_id, title, message, kind),
    )


def _refresh_lives(db, user_id):
    now = _utcnow()
    row = db.execute(
        "SELECT remaining_lives,last_regeneration_at FROM user_lives WHERE user_id=?", (user_id,)
    ).fetchone()
    if not row:
        db.execute("INSERT OR IGNORE INTO user_lives(user_id) VALUES(?)", (user_id,))
        return MAX_LIVES
    remaining = row["remaining_lives"]
    last = _parse_datetime(row["last_regeneration_at"])
    elapsed = max(0, int((now - last).total_seconds()))
    recovered = min(MAX_LIVES - remaining, elapsed // int(LIFE_RECOVERY.total_seconds()))
    if recovered:
        remaining += recovered
        last += LIFE_RECOVERY * recovered
        if remaining == MAX_LIVES:
            last = now
        db.execute(
            "UPDATE user_lives SET remaining_lives=?,last_regeneration_at=? WHERE user_id=?",
            (remaining, last.isoformat(timespec="seconds"), user_id),
        )
        _notification(db, user_id, "A life recovered", "Your learning energy is ready when you are.", "lives_regenerated")
    elif remaining == MAX_LIVES:
        db.execute(
            "UPDATE user_lives SET last_regeneration_at=? WHERE user_id=?",
            (now.isoformat(timespec="seconds"), user_id),
        )
    return remaining


def _profile(db, user_id):
    _refresh_lives(db, user_id)
    row = db.execute(
        """SELECT u.id,u.name,u.email,u.xp,u.trado_cash,u.created_at,
                  COALESCE(w.coins,0) coins,COALESCE(l.remaining_lives,5) remaining_lives,
                  COALESCE(s.current_streak,0) current_streak,COALESCE(s.longest_streak,0) longest_streak,
                  COALESCE(us.daily_goal_minutes,10) daily_goal_minutes,
                  COALESCE(us.timezone,'UTC') timezone,COALESCE(us.onboarding_complete,0) onboarding_complete,
                  COALESCE(us.trader_type,'beginner') trader_type,COALESCE(us.avatar_id,'candela') avatar_id
           FROM users u LEFT JOIN user_wallet w ON w.user_id=u.id
           LEFT JOIN user_lives l ON l.user_id=u.id LEFT JOIN user_streaks s ON s.user_id=u.id
           LEFT JOIN user_settings us ON us.user_id=u.id WHERE u.id=?""",
        (user_id,),
    ).fetchone()
    if not row:
        return None
    result = dict(row)
    result["trader_type_label"] = next(
        (item["label"] for item in TRADER_TYPES if item["id"] == result["trader_type"]),
        "Beginner Trader",
    )
    result["avatar_name"] = next(
        (item["name"] for item in AVATAR_OPTIONS if item["id"] == result["avatar_id"]),
        "Candela",
    )
    return result


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    with get_db() as db:
        return _profile(db, uid)


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return jsonify({"error": "Please log in first."}), 401
        return fn(*args, **kwargs)

    return wrapper


def _category_names(db, user_id):
    return [
        row["category_name"]
        for row in db.execute(
            "SELECT category_name FROM user_categories WHERE user_id=? ORDER BY rowid", (user_id,)
        ).fetchall()
    ]


def _reward(db, user_id, reward_type, amount, source, source_id):
    if amount <= 0:
        return False
    cur = db.execute(
        """INSERT OR IGNORE INTO reward_transactions(user_id,reward_type,amount,source,source_id)
           VALUES(?,?,?,?,?)""",
        (user_id, reward_type, amount, source, str(source_id)),
    )
    if cur.rowcount == 0:
        return False
    if reward_type == "xp":
        db.execute("UPDATE users SET xp=xp+? WHERE id=?", (amount, user_id))
    elif reward_type == "coins":
        db.execute("UPDATE user_wallet SET coins=coins+? WHERE user_id=?", (amount, user_id))
    return True


def _add_daily_xp(db, user_id, activity_date, amount):
    if amount:
        db.execute(
            """INSERT INTO daily_activity(user_id,activity_date,xp_earned) VALUES(?,?,?)
               ON CONFLICT(user_id,activity_date) DO UPDATE SET xp_earned=xp_earned+excluded.xp_earned""",
            (user_id, activity_date.isoformat(), amount),
        )


def _grant_achievements(db, user_id):
    levels = db.execute("SELECT COUNT(*) FROM user_progress WHERE user_id=?", (user_id,)).fetchone()[0]
    categories = db.execute(
        "SELECT COUNT(DISTINCT l.category) FROM user_progress p JOIN lessons l ON l.id=p.lesson_id WHERE p.user_id=?",
        (user_id,),
    ).fetchone()[0]
    questions = db.execute(
        "SELECT COUNT(*) FROM question_state WHERE user_id=? AND mastered=1", (user_id,)
    ).fetchone()[0]
    streak = db.execute(
        "SELECT current_streak FROM user_streaks WHERE user_id=?", (user_id,)
    ).fetchone()[0]
    values = {"levels": levels, "categories": categories, "questions": questions, "streak": streak}
    earned = []
    rows = db.execute("SELECT * FROM achievements").fetchall()
    for achievement in rows:
        if values.get(achievement["condition_type"], 0) < achievement["condition_value"]:
            continue
        cur = db.execute(
            "INSERT OR IGNORE INTO user_achievements(user_id,achievement_id) VALUES(?,?)",
            (user_id, achievement["id"]),
        )
        if cur.rowcount:
            db.execute(
                "INSERT OR IGNORE INTO user_rewards(user_id,badge) VALUES(?,?)",
                (user_id, achievement["title"]),
            )
            _notification(
                db,
                user_id,
                f"Achievement unlocked: {achievement['title']}",
                achievement["description"],
                "achievement_unlocked",
            )
            earned.append(dict(achievement))
    return earned


def _record_learning_activity(db, user_id, activity_date):
    row = db.execute(
        "SELECT current_streak,longest_streak,last_activity_date FROM user_streaks WHERE user_id=?",
        (user_id,),
    ).fetchone()
    today = activity_date.isoformat()
    if row["last_activity_date"] == today:
        return
    previous = activity_date - timedelta(days=1)
    current = row["current_streak"] + 1 if row["last_activity_date"] == previous.isoformat() else 1
    longest = max(row["longest_streak"], current)
    db.execute(
        "UPDATE user_streaks SET current_streak=?,longest_streak=?,last_activity_date=? WHERE user_id=?",
        (current, longest, today, user_id),
    )


def _maybe_daily_goal_reward(db, user_id, activity_date):
    setting = db.execute(
        "SELECT daily_goal_minutes FROM user_settings WHERE user_id=?", (user_id,)
    ).fetchone()
    activity = db.execute(
        "SELECT active_seconds FROM daily_activity WHERE user_id=? AND activity_date=?",
        (user_id, activity_date.isoformat()),
    ).fetchone()
    if not setting or not activity or activity["active_seconds"] < setting["daily_goal_minutes"] * 60:
        return False
    xp = _reward(db, user_id, "xp", 10, "daily_goal", activity_date.isoformat())
    coins = _reward(db, user_id, "coins", 10, "daily_goal", activity_date.isoformat())
    if xp:
        _add_daily_xp(db, user_id, activity_date, 10)
    if xp or coins:
        _notification(db, user_id, "Daily goal complete", "You reached today's learning goal. +10 XP and +10 coins.", "goal_completed")
        return True
    return False


def _lesson_access(db, user_id, lesson_id):
    lesson = db.execute(
        """SELECT l.id,l.category,l.title,l.level,l.content,m.description,m.estimated_minutes,
                  m.reward_xp,m.reward_coins,w.title world_title,w.sequence_order world_order
           FROM lessons l JOIN level_metadata m ON m.lesson_id=l.id
           JOIN learning_worlds w ON w.id=m.world_id WHERE l.id=?""",
        (lesson_id,),
    ).fetchone()
    if not lesson:
        return None, (jsonify({"error": "Level not found."}), 404)
    if lesson["category"] not in _category_names(db, user_id):
        return None, (jsonify({"error": "Choose this trading path in your learning settings first."}), 403)
    previous = db.execute(
        "SELECT id FROM lessons WHERE category=? AND level<? ORDER BY level DESC LIMIT 1",
        (lesson["category"], lesson["level"]),
    ).fetchone()
    if previous:
        prior_progress = db.execute(
            "SELECT completion_status FROM level_progress WHERE user_id=? AND lesson_id=?",
            (user_id, previous["id"]),
        ).fetchone()
        if not prior_progress or prior_progress["completion_status"] != "completed":
            return None, (jsonify({"error": "Complete the previous level to unlock this one.", "locked": True}), 403)
    db.execute(
        "INSERT OR IGNORE INTO level_progress(user_id,lesson_id) VALUES(?,?)", (user_id, lesson_id)
    )
    return lesson, None


def _accuracy(db, user_id, lesson_id):
    row = db.execute(
        """SELECT COUNT(*) attempted,SUM(CASE WHEN first_attempt_correct=1 THEN 1 ELSE 0 END) first_correct
           FROM question_state s JOIN questions q ON q.id=s.question_id
           WHERE s.user_id=? AND q.lesson_id=? AND s.attempt_count>0""",
        (user_id, lesson_id),
    ).fetchone()
    attempted = row["attempted"] or 0
    first_correct = row["first_correct"] or 0
    return attempted, first_correct, round(first_correct * 100 / attempted) if attempted else 0


def _level_data(db, user_id, lesson):
    level = dict(lesson)
    questions = db.execute(
        """SELECT q.id,q.question_text,q.options_json,q.sequence_order,s.mastered,s.attempt_count
           FROM questions q LEFT JOIN question_state s ON s.question_id=q.id AND s.user_id=?
           WHERE q.lesson_id=? ORDER BY q.sequence_order""",
        (user_id, lesson["id"]),
    ).fetchall()
    mastered = sum(1 for q in questions if q["mastered"])
    progress = db.execute(
        "SELECT * FROM level_progress WHERE user_id=? AND lesson_id=?", (user_id, lesson["id"])
    ).fetchone()
    level_one_flow = lesson["level"] == 1
    first_pass = level_one_flow and progress["current_question"] <= len(questions)
    active = (
        next((q for q in questions if q["sequence_order"] == progress["current_question"]), None)
        if first_pass
        else next((q for q in questions if not q["mastered"]), None)
    )
    attempted, first_correct, accuracy = _accuracy(db, user_id, lesson["id"])
    question = None
    if active and progress["completion_status"] != "completed":
        question = {
            "id": active["id"],
            "text": active["question_text"],
            "options": json_load_options(active["options_json"]),
            "number": active["sequence_order"],
            "attempts": active["attempt_count"],
        }
    return {
        "level": level,
        "question": question,
        "phase": "first_pass" if first_pass else "review" if level_one_flow else "standard",
        "total_questions": len(questions),
        "mastered_questions": mastered,
        "progress_percent": round(mastered * 100 / len(questions)) if questions else 0,
        "completion_status": progress["completion_status"],
        "completed_at": progress["completed_at"],
        "stars": progress["stars"],
        "attempted_questions": attempted,
        "first_attempt_correct": first_correct,
        "accuracy_percent": accuracy,
    }


def json_load_options(encoded):
    import json

    try:
        values = json.loads(encoded)
    except (TypeError, ValueError):
        values = []
    return [{"key": "ABCD"[i], "text": text} for i, text in enumerate(values[:4])]


def _finish_level(db, user_id, lesson, activity_date):
    existing = db.execute(
        "SELECT completion_status FROM level_progress WHERE user_id=? AND lesson_id=?",
        (user_id, lesson["id"]),
    ).fetchone()
    if existing and existing["completion_status"] == "completed":
        return {"xp": 0, "coins": 0, "stars": existing["stars"], "newly_completed": False, "achievements": []}
    attempted, first_correct, accuracy = _accuracy(db, user_id, lesson["id"])
    stars = 3 if accuracy >= 85 else 2 if accuracy >= 55 else 1
    now = _utcnow().isoformat(timespec="seconds")
    db.execute(
        """UPDATE level_progress SET current_question=7,completion_status='completed',completed_at=?,stars=?
           WHERE user_id=? AND lesson_id=?""",
        (now, stars, user_id, lesson["id"]),
    )
    inserted = db.execute(
        "INSERT OR IGNORE INTO user_progress(user_id,lesson_id,score,completed_at) VALUES(?,?,?,?)",
        (user_id, lesson["id"], accuracy, now),
    ).rowcount
    xp_amount = lesson["reward_xp"] if inserted else 0
    coin_amount = lesson["reward_coins"] if inserted else 0
    xp_awarded = _reward(db, user_id, "xp", xp_amount, "level_completion", lesson["id"])
    coins_awarded = _reward(db, user_id, "coins", coin_amount, "level_completion", lesson["id"])
    total_xp = (5 if attempted else 0) + (xp_amount if xp_awarded else 0)
    _add_daily_xp(db, user_id, activity_date, xp_amount if xp_awarded else 0)
    if inserted:
        db.execute(
            """INSERT INTO daily_activity(user_id,activity_date,lessons_completed) VALUES(?,?,1)
               ON CONFLICT(user_id,activity_date) DO UPDATE SET lessons_completed=lessons_completed+1""",
            (user_id, activity_date.isoformat()),
        )
    next_level = db.execute(
        "SELECT id,title FROM lessons WHERE category=? AND level>? ORDER BY level LIMIT 1",
        (lesson["category"], lesson["level"]),
    ).fetchone()
    if next_level:
        _notification(db, user_id, "A new level is open", f"{next_level['title']} is ready on your {lesson['category']} path.", "level_unlocked")
    earned = _grant_achievements(db, user_id)
    return {
        "xp": (5 if attempted else 0) + (xp_amount if xp_awarded else 0),
        "coins": coin_amount if coins_awarded else 0,
        "stars": stars,
        "accuracy_percent": accuracy,
        "attempted_questions": attempted,
        "first_attempt_correct": first_correct,
        "newly_completed": bool(inserted),
        "achievements": earned,
    }


def _submit_level_answer(db, user_id, lesson_id, answer, requested_question_id=None):
    lesson, error = _lesson_access(db, user_id, lesson_id)
    if error:
        return error[0].json, error[1]
    data = _level_data(db, user_id, lesson)
    active = data["question"]
    first_pass_mode = data["phase"] == "first_pass"
    review_mode = data["phase"] == "review"
    if data["completion_status"] == "completed":
        return {"correct": True, "completed": True, "duplicate": True, "progress": data}, 200
    if not active:
        return {"error": "This level has no available questions."}, 409
    if requested_question_id is not None:
        try:
            requested_question_id = int(requested_question_id)
        except (TypeError, ValueError):
            return {"error": "Question not found."}, 404
        requested_state = db.execute(
            """SELECT s.mastered FROM questions q LEFT JOIN question_state s
               ON s.question_id=q.id AND s.user_id=? WHERE q.id=? AND q.lesson_id=?""",
            (user_id, requested_question_id, lesson_id),
        ).fetchone()
        if not requested_state:
            return {"error": "Question not found."}, 404
        if requested_state["mastered"]:
            return {"correct": True, "mastered": True, "duplicate": True, "progress": data}, 200
        if requested_question_id != active["id"]:
            return {"error": "Master the current question before answering another one."}, 409
    selected = str(answer or "").strip().upper()
    option_map = {item["key"]: item["text"] for item in active["options"]}
    if selected not in option_map:
        return {"error": "Choose one of the available answers."}, 400

    question_id = active["id"]
    question = db.execute(
        "SELECT correct_option,explanation FROM questions WHERE id=?", (question_id,)
    ).fetchone()
    if not question:
        return {"error": "Question not found."}, 404
    previous = db.execute(
        "SELECT * FROM question_state WHERE user_id=? AND question_id=?", (user_id, question_id)
    ).fetchone()
    if previous and previous["mastered"]:
        return {"correct": True, "mastered": True, "duplicate": True, "progress": data}, 200

    attempt_number = (previous["attempt_count"] if previous else 0) + 1
    correct = selected == question["correct_option"]
    first_correct = int(correct) if attempt_number == 1 else previous["first_attempt_correct"]
    life_lost = 0
    lives = _refresh_lives(db, user_id)
    life_penalty_applied = previous["life_penalty_applied"] if previous else 0
    if not correct and attempt_number == 1:
        life_penalty_applied = 1
        if lives > 0:
            lives -= 1
            life_lost = 1
            db.execute("UPDATE user_lives SET remaining_lives=? WHERE user_id=?", (lives, user_id))
    if previous:
        db.execute(
            """UPDATE question_state SET attempt_count=?,first_attempt_correct=?,mastered=?,
               life_penalty_applied=?,updated_at=CURRENT_TIMESTAMP WHERE user_id=? AND question_id=?""",
            (attempt_number, first_correct, int(correct), life_penalty_applied, user_id, question_id),
        )
    else:
        db.execute(
            """INSERT INTO question_state(user_id,question_id,attempt_count,first_attempt_correct,mastered,life_penalty_applied)
               VALUES(?,?,?,?,?,?)""",
            (user_id, question_id, attempt_number, first_correct, int(correct), life_penalty_applied),
        )
    db.execute(
        """INSERT INTO question_attempts(user_id,question_id,selected_answer,is_correct,attempt_number,life_lost)
           VALUES(?,?,?,?,?,?)""",
        (user_id, question_id, selected, int(correct), attempt_number, life_lost),
    )

    if not correct:
        if first_pass_mode:
            db.execute(
                "UPDATE level_progress SET current_question=? WHERE user_id=? AND lesson_id=?",
                (active["number"] + 1, user_id, lesson_id),
            )
        updated = _level_data(db, user_id, lesson)
        return {
            "correct": False,
            "mastered": False,
            "can_continue": first_pass_mode,
            "message": (
                "Not quite. Read the explanation; this question will return in the review round."
                if first_pass_mode
                else "Not quite. Read the explanation, then try this question again."
            ),
            "correct_answer": question["correct_option"],
            "correct_answer_text": option_map.get(question["correct_option"], ""),
            "explanation": question["explanation"],
            "life_lost": bool(life_lost),
            "remaining_lives": lives,
            "progress": updated,
        }, 200

    activity_date = _user_date(db, user_id)
    _record_learning_activity(db, user_id, activity_date)
    question_xp = 5 if _reward(db, user_id, "xp", 5, "question_mastery", question_id) else 0
    _add_daily_xp(db, user_id, activity_date, question_xp)
    mastered = db.execute(
        """SELECT COUNT(*) FROM question_state s JOIN questions q ON q.id=s.question_id
           WHERE s.user_id=? AND q.lesson_id=? AND s.mastered=1""",
        (user_id, lesson_id),
    ).fetchone()[0]
    total = db.execute("SELECT COUNT(*) FROM questions WHERE lesson_id=?", (lesson_id,)).fetchone()[0]
    completion = None
    next_question = data["total_questions"] + 1 if review_mode else db.execute(
        "SELECT sequence_order FROM questions WHERE id=?", (question_id,)
    ).fetchone()["sequence_order"] + 1
    db.execute(
        "UPDATE level_progress SET current_question=? WHERE user_id=? AND lesson_id=?",
        (next_question, user_id, lesson_id),
    )
    if total and mastered == total:
        completion = _finish_level(db, user_id, lesson, activity_date)
    else:
        _grant_achievements(db, user_id)
    updated_lesson, _ = _lesson_access(db, user_id, lesson_id)
    progress = _level_data(db, user_id, updated_lesson)
    return {
        "correct": True,
        "mastered": True,
        "message": "Correct! This question is mastered.",
        "explanation": question["explanation"],
        "remaining_lives": _refresh_lives(db, user_id),
        "progress": progress,
        "xp_earned": completion["xp"] if completion else question_xp,
        "coins_earned": completion["coins"] if completion else 0,
        "completion": completion,
        "completed": bool(completion),
    }, 200


@app.get("/")
def home():
    return send_from_directory(FRONTEND, "index.html")


@app.get("/<path:page>")
def pages(page):
    target = FRONTEND / page
    if target.is_file() and FRONTEND.resolve() in target.resolve().parents:
        return send_from_directory(FRONTEND, page)
    return jsonify({"error": "Page not found"}), 404


@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    if not name or len(name) > 60 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        return jsonify({"error": "Enter your name and a valid email address."}), 400
    if not isinstance(password, str) or len(password) < 8:
        return jsonify({"error": "Use a password with at least 8 characters."}), 400
    if data.get("confirm_password") != password:
        return jsonify({"error": "Passwords do not match."}), 400
    if data.get("terms_accepted") is not True:
        return jsonify({"error": "Accept the terms to create your account."}), 400
    trader_type = str(data.get("trader_type") or "beginner")
    if trader_type not in TRADER_TYPE_IDS:
        return jsonify({"error": "Choose a valid trader type."}), 400
    try:
        with get_db() as db:
            cur = db.execute(
                "INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                (name, email, generate_password_hash(password)),
            )
            user_id = cur.lastrowid
            ensure_user_records(db, user_id, is_new=True)
            db.execute("UPDATE user_settings SET trader_type=? WHERE user_id=?", (trader_type, user_id))
    except sqlite3.IntegrityError:
        return jsonify({"error": "An account with this email already exists."}), 409
    session.clear()
    session["user_id"] = user_id
    session.permanent = True
    return jsonify({"message": "Account created.", "user": current_user()}), 201


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    now = time.monotonic()
    key = (request.remote_addr or "unknown", email[:254])
    failures = [stamp for stamp in _login_failures.get(key, []) if now - stamp < _LOGIN_WINDOW_SECONDS]
    if len(failures) >= _LOGIN_MAX_FAILURES:
        return jsonify({"error": "Too many sign-in attempts. Wait a few minutes and try again."}), 429
    with get_db() as db:
        user = db.execute("SELECT id,password_hash FROM users WHERE email=?", (email,)).fetchone()
    if not user or not isinstance(password, str) or not check_password_hash(user["password_hash"], password):
        failures.append(now)
        _login_failures[key] = failures
        return jsonify({"error": "Incorrect email or password."}), 401
    _login_failures.pop(key, None)
    session.clear()
    session["user_id"] = user["id"]
    session.permanent = bool(data.get("remember"))
    return jsonify({"message": "Logged in.", "user": current_user()})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out."})


@app.get("/api/me")
@login_required
def me():
    user = current_user()
    user["selected_categories"] = _category_names_for(user["id"])
    return jsonify({"user": user})


@app.get("/api/profile")
@login_required
def profile():
    user = current_user()
    with get_db() as db:
        selected = _category_names(db, user["id"])
        current_levels = []
        if selected:
            placeholders = ",".join("?" for _ in selected)
            completed = db.execute(
                f"SELECT COUNT(*) FROM user_progress p JOIN lessons l ON l.id=p.lesson_id "
                f"WHERE p.user_id=? AND l.category IN ({placeholders})",
                [user["id"], *selected],
            ).fetchone()[0]
            total = db.execute(
                f"SELECT COUNT(*) FROM lessons WHERE category IN ({placeholders})", selected
            ).fetchone()[0]
            level_rows = db.execute(
                f"""SELECT l.category,l.level,l.title,COALESCE(lp.completion_status,'in_progress') completion_status
                    FROM lessons l LEFT JOIN level_progress lp ON lp.lesson_id=l.id AND lp.user_id=?
                    WHERE l.category IN ({placeholders}) ORDER BY l.category,l.level""",
                [user["id"], *selected],
            ).fetchall()
            opened_categories = set()
            for level in level_rows:
                if level["category"] not in opened_categories and level["completion_status"] != "completed":
                    current_levels.append({
                        "category": level["category"],
                        "level": level["level"],
                        "title": level["title"],
                    })
                    opened_categories.add(level["category"])
        else:
            completed = total = 0
        achievements = db.execute(
            """SELECT a.slug,a.title,a.description,a.icon,ua.unlocked_at
               FROM user_achievements ua JOIN achievements a ON a.id=ua.achievement_id
               WHERE ua.user_id=? ORDER BY ua.unlocked_at DESC""",
            (user["id"],),
        ).fetchall()
    return jsonify({
        "user": user,
        "selected_categories": selected,
        "completed_levels": completed,
        "total_levels": total,
        "current_levels": current_levels,
        "achievements": [dict(item) for item in achievements],
        "trader_types": TRADER_TYPES,
        "avatars": AVATAR_OPTIONS,
    })


@app.put("/api/profile")
@login_required
def update_profile():
    data = request.get_json(silent=True) or {}
    name_value = data.get("name")
    name = name_value.strip() if isinstance(name_value, str) else ""
    trader_type = data.get("trader_type")
    avatar_id = data.get("avatar_id")
    goal = data.get("daily_goal_minutes")
    if not name or len(name) > 60:
        return jsonify({"error": "Enter a name between 1 and 60 characters."}), 400
    if not isinstance(trader_type, str) or trader_type not in TRADER_TYPE_IDS:
        return jsonify({"error": "Choose a valid trader type."}), 400
    if not isinstance(avatar_id, str) or avatar_id not in AVATAR_IDS:
        return jsonify({"error": "Choose one of the available characters."}), 400
    if isinstance(goal, bool) or goal not in (5, 10, 15, 20, 30):
        return jsonify({"error": "Choose a daily goal of 5, 10, 15, 20, or 30 minutes."}), 400
    with get_db() as db:
        db.execute("UPDATE users SET name=? WHERE id=?", (name, session["user_id"]))
        db.execute(
            """UPDATE user_settings SET trader_type=?,avatar_id=?,daily_goal_minutes=?,
               updated_at=CURRENT_TIMESTAMP WHERE user_id=?""",
            (trader_type, avatar_id, goal, session["user_id"]),
        )
    return jsonify({"message": "Profile saved.", "user": current_user()})


def _category_names_for(user_id):
    with get_db() as db:
        return _category_names(db, user_id)


@app.get("/api/categories")
@login_required
def categories():
    with get_db() as db:
        rows = db.execute(
            """SELECT c.name,c.description,c.icon,CASE WHEN uc.user_id IS NULL THEN 0 ELSE 1 END selected
               FROM trading_categories c LEFT JOIN user_categories uc ON uc.category_name=c.name AND uc.user_id=?
               ORDER BY c.rowid""",
            (session["user_id"],),
        ).fetchall()
    return jsonify({"categories": [dict(row) for row in rows]})


@app.get("/api/onboarding")
@login_required
def onboarding():
    uid = session["user_id"]
    with get_db() as db:
        setting = db.execute("SELECT * FROM user_settings WHERE user_id=?", (uid,)).fetchone()
        cats = db.execute("SELECT name,description,icon FROM trading_categories ORDER BY rowid").fetchall()
    return jsonify({
        "settings": dict(setting),
        "selected_categories": _category_names_for(uid),
        "categories": [dict(row) for row in cats],
    })


@app.put("/api/onboarding")
@app.put("/api/settings")
@login_required
def save_settings():
    data = request.get_json(silent=True) or {}
    uid = session["user_id"]
    with get_db() as db:
        setting = db.execute("SELECT * FROM user_settings WHERE user_id=?", (uid,)).fetchone()
        selected = data.get("categories", _category_names(db, uid))
        if not isinstance(selected, list) or not selected:
            return jsonify({"error": "Choose at least one learning category."}), 400
        valid = {row["name"] for row in db.execute("SELECT name FROM trading_categories").fetchall()}
        if any(not isinstance(item, str) or item not in valid for item in selected):
            return jsonify({"error": "Choose valid trading categories."}), 400
        goal = data.get("daily_goal_minutes", setting["daily_goal_minutes"])
        if isinstance(goal, bool) or goal not in (5, 10, 15, 20, 30):
            return jsonify({"error": "Choose a daily goal of 5, 10, 15, 20, or 30 minutes."}), 400
        tz = data.get("timezone", setting["timezone"])
        if not isinstance(tz, str) or len(tz) > 60:
            return jsonify({"error": "Choose a valid timezone."}), 400
        try:
            ZoneInfo(tz)
        except (ZoneInfoNotFoundError, ValueError):
            return jsonify({"error": "Choose a valid timezone."}), 400
        db.execute("DELETE FROM user_categories WHERE user_id=?", (uid,))
        db.executemany(
            "INSERT INTO user_categories(user_id,category_name) VALUES(?,?)",
            [(uid, item) for item in dict.fromkeys(selected)],
        )
        db.execute(
            """UPDATE user_settings SET daily_goal_minutes=?,timezone=?,onboarding_complete=1,
               updated_at=CURRENT_TIMESTAMP WHERE user_id=?""",
            (goal, tz, uid),
        )
    return jsonify({"message": "Learning preferences saved.", "user": current_user()})


@app.get("/api/lessons")
@login_required
def lessons():
    uid = session["user_id"]
    category = request.args.get("category")
    with get_db() as db:
        selected = _category_names(db, uid)
        if category and category not in selected:
            return jsonify({"error": "Choose this trading path in your learning settings first."}), 403
        params = [uid]
        filter_sql = ""
        if category:
            filter_sql = "WHERE l.category=?"
            params.append(category)
        elif selected:
            filter_sql = "WHERE l.category IN (" + ",".join("?" for _ in selected) + ")"
            params.extend(selected)
        rows = db.execute(
            f"""SELECT l.id,l.category,l.title,l.level,l.content,m.description,m.estimated_minutes,
                       m.world_id,w.title world_title,
                       CASE WHEN lp.completion_status='completed' THEN 1 ELSE 0 END completed,
                       COALESCE(lp.completion_status,'locked') completion_status,
                       COALESCE(lp.stars,0) stars,
                       (SELECT COUNT(*) FROM questions q WHERE q.lesson_id=l.id) total_questions,
                       (SELECT COUNT(*) FROM question_state qs JOIN questions q ON q.id=qs.question_id
                         WHERE qs.user_id=? AND q.lesson_id=l.id AND qs.mastered=1) mastered_questions
                FROM lessons l JOIN level_metadata m ON m.lesson_id=l.id
                JOIN learning_worlds w ON w.id=m.world_id
                LEFT JOIN level_progress lp ON lp.user_id=? AND lp.lesson_id=l.id
                {filter_sql} ORDER BY l.category,l.level""",
            [uid, uid, *params[1:]] if category or not selected else [uid, uid, *selected],
        ).fetchall()
        # Mark the first unfinished level in each category as current, and only unlock it.
        levels = [dict(row) for row in rows]
        first_open = {}
        for item in levels:
            if item["completion_status"] != "completed" and item["category"] not in first_open:
                first_open[item["category"]] = item["id"]
        for item in levels:
            item["state"] = "completed" if item["completed"] else (
                "current" if first_open.get(item["category"]) == item["id"] else "locked"
            )
    return jsonify({"lessons": levels})


@app.get("/api/lessons/<int:lesson_id>")
@login_required
def lesson_detail(lesson_id):
    uid = session["user_id"]
    with get_db() as db:
        lesson, error = _lesson_access(db, uid, lesson_id)
        if error:
            return error
        data = _level_data(db, uid, lesson)
        quiz = None
        if data["question"]:
            quiz = {
                "id": data["question"]["id"],
                "question": data["question"]["text"],
                **{f"option_{key.lower()}": value for key, value in ((item["key"], item["text"]) for item in data["question"]["options"])},
            }
    return jsonify({"lesson": data["level"], "question": data["question"], "quiz": quiz, "progress": data})


@app.get("/api/levels/<int:lesson_id>")
@login_required
def level_detail(lesson_id):
    uid = session["user_id"]
    with get_db() as db:
        lesson, error = _lesson_access(db, uid, lesson_id)
        if error:
            return error
        data = _level_data(db, uid, lesson)
        data["remaining_lives"] = _refresh_lives(db, uid)
    return jsonify(data)


@app.post("/api/levels/<int:lesson_id>/answer")
@login_required
def answer_level(lesson_id):
    payload = request.get_json(silent=True) or {}
    with get_db() as db:
        result, status = _submit_level_answer(
            db, session["user_id"], lesson_id, payload.get("answer"), payload.get("question_id")
        )
    return jsonify(result), status


@app.post("/api/lessons/<int:lesson_id>/complete")
@login_required
def complete_lesson(lesson_id):
    # Compatibility route: each request answers the current unmastered question.
    payload = request.get_json(silent=True) or {}
    with get_db() as db:
        result, status = _submit_level_answer(db, session["user_id"], lesson_id, payload.get("answer"))
    return jsonify(result), status


@app.post("/api/levels/<int:lesson_id>/hint")
@login_required
def level_hint(lesson_id):
    payload = request.get_json(silent=True) or {}
    uid = session["user_id"]
    try:
        question_id = int(payload.get("question_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "Question not found."}), 404
    with get_db() as db:
        lesson, error = _lesson_access(db, uid, lesson_id)
        if error:
            return error
        data = _level_data(db, uid, lesson)
        if not data["question"] or data["question"]["id"] != question_id:
            used = db.execute(
                "SELECT 1 FROM reward_transactions WHERE user_id=? AND reward_type='coins' AND source='hint' AND source_id=?",
                (uid, str(question_id)),
            ).fetchone()
            if not used:
                return jsonify({"error": "Hints are available for the current question."}), 409
        hint = db.execute(
            "SELECT sequence_order FROM questions WHERE id=? AND lesson_id=?", (question_id, lesson_id)
        ).fetchone()
        if not hint:
            return jsonify({"error": "Question not found."}), 404
        previous = db.execute(
            "SELECT 1 FROM reward_transactions WHERE user_id=? AND reward_type='coins' AND source='hint' AND source_id=?",
            (uid, str(question_id)),
        ).fetchone()
        hints = [
            "Look for the lesson definition that matches the central idea, then remove any promise of certainty.",
            "Follow the scenario step by step and identify what the example does—and does not—guarantee.",
            "Think about the possible downside if conditions move against the learner.",
            "Choose the habit that checks limits and conditions before taking action.",
            "Remove options that promise a guaranteed result; learning concepts describe risks as well as mechanics.",
            "Recall the main fact from the lesson and compare it with the wording of each choice.",
        ]
        charged = False
        if not previous:
            wallet = db.execute("SELECT coins FROM user_wallet WHERE user_id=?", (uid,)).fetchone()
            if not wallet or wallet["coins"] < 3:
                return jsonify({"error": "You need 3 coins for a hint. Complete a level to earn more."}), 400
            db.execute("UPDATE user_wallet SET coins=coins-3 WHERE user_id=?", (uid,))
            db.execute(
                "INSERT INTO reward_transactions(user_id,reward_type,amount,source,source_id) VALUES(?,'coins',-3,'hint',?)",
                (uid, str(question_id)),
            )
            charged = True
        coins = db.execute("SELECT coins FROM user_wallet WHERE user_id=?", (uid,)).fetchone()["coins"]
    return jsonify({"hint": hints[min(hint["sequence_order"] - 1, len(hints) - 1)], "coins": coins, "coins_spent": 3 if charged else 0})


@app.post("/api/activity")
@login_required
def record_activity():
    data = request.get_json(silent=True) or {}
    event_id = data.get("event_id")
    seconds = data.get("seconds")
    if not isinstance(event_id, str) or not re.fullmatch(r"[A-Za-z0-9-]{8,80}", event_id):
        return jsonify({"error": "A unique activity event ID is required."}), 400
    if isinstance(seconds, bool) or not isinstance(seconds, int) or not 1 <= seconds <= 45:
        return jsonify({"error": "Activity time must be between 1 and 45 seconds."}), 400
    uid = session["user_id"]
    with get_db() as db:
        today = _user_date(db, uid)
        inserted = db.execute(
            "INSERT OR IGNORE INTO activity_events(user_id,event_id,activity_date,seconds) VALUES(?,?,?,?)",
            (uid, event_id, today.isoformat(), seconds),
        ).rowcount
        if inserted:
            db.execute(
                """INSERT INTO daily_activity(user_id,activity_date,active_seconds) VALUES(?,?,?)
                   ON CONFLICT(user_id,activity_date) DO UPDATE SET active_seconds=active_seconds+excluded.active_seconds""",
                (uid, today.isoformat(), seconds),
            )
        activity = db.execute(
            "SELECT active_seconds FROM daily_activity WHERE user_id=? AND activity_date=?",
            (uid, today.isoformat()),
        ).fetchone()
        if activity and activity["active_seconds"] >= 60:
            _record_learning_activity(db, uid, today)
            _grant_achievements(db, uid)
        goal_complete = _maybe_daily_goal_reward(db, uid, today)
        setting = db.execute("SELECT daily_goal_minutes FROM user_settings WHERE user_id=?", (uid,)).fetchone()
        streak = db.execute("SELECT current_streak FROM user_streaks WHERE user_id=?", (uid,)).fetchone()["current_streak"]
    return jsonify({
        "active_seconds": activity["active_seconds"] if activity else 0,
        "active_minutes": round((activity["active_seconds"] if activity else 0) / 60, 1),
        "daily_goal_minutes": setting["daily_goal_minutes"],
        "goal_complete": goal_complete,
        "duplicate_event": not bool(inserted),
        "current_streak": streak,
    })


@app.get("/api/notifications")
@login_required
def notifications():
    uid = session["user_id"]
    with get_db() as db:
        rows = db.execute(
            "SELECT id,title,message,notification_type,is_read,created_at FROM notifications WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT 30",
            (uid,),
        ).fetchall()
        unread = db.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0", (uid,)
        ).fetchone()[0]
    return jsonify({"notifications": [dict(row) for row in rows], "unread_count": unread})


@app.post("/api/notifications/<int:notification_id>/read")
@login_required
def mark_notification_read(notification_id):
    with get_db() as db:
        cur = db.execute(
            "UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?",
            (notification_id, session["user_id"]),
        )
        if not cur.rowcount:
            return jsonify({"error": "Notification not found."}), 404
    return jsonify({"message": "Notification marked as read."})


@app.post("/api/notifications/read-all")
@login_required
def mark_all_notifications_read():
    with get_db() as db:
        db.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (session["user_id"],))
    return jsonify({"message": "Notifications marked as read."})


@app.get("/api/dashboard")
@login_required
def dashboard():
    uid = session["user_id"]
    with get_db() as db:
        user = _profile(db, uid)
        selected = _category_names(db, uid)
        category = request.args.get("category")
        if category and category not in selected:
            return jsonify({"error": "Choose this trading path in your learning settings first."}), 403
        active_category = category or (selected[0] if selected else None)
        today = _user_date(db, uid)
        activity = db.execute(
            "SELECT * FROM daily_activity WHERE user_id=? AND activity_date=?", (uid, today.isoformat())
        ).fetchone()
        activity = dict(activity) if activity else {
            "active_seconds": 0, "xp_earned": 0, "lessons_completed": 0,
        }
        total = db.execute(
            "SELECT COUNT(*) FROM lessons l WHERE l.category IN (" + ",".join("?" for _ in selected) + ")",
            selected,
        ).fetchone()[0] if selected else 0
        done = db.execute(
            "SELECT COUNT(*) FROM user_progress p JOIN lessons l ON l.id=p.lesson_id WHERE p.user_id=? AND l.category IN (" + ",".join("?" for _ in selected) + ")",
            [uid, *selected],
        ).fetchone()[0] if selected else 0
        badges = db.execute(
            "SELECT badge,awarded_at FROM user_rewards WHERE user_id=? ORDER BY awarded_at DESC", (uid,)
        ).fetchall()
        achievements = db.execute(
            """SELECT a.slug,a.title,a.description,a.icon,ua.unlocked_at
               FROM user_achievements ua JOIN achievements a ON a.id=ua.achievement_id
               WHERE ua.user_id=? ORDER BY ua.unlocked_at DESC""",
            (uid,),
        ).fetchall()
        recent = db.execute(
            """SELECT l.title,l.category,p.score,p.completed_at FROM user_progress p
               JOIN lessons l ON l.id=p.lesson_id WHERE p.user_id=? ORDER BY p.completed_at DESC LIMIT 5""",
            (uid,),
        ).fetchall()
        roadmap = []
        if active_category:
            levels = db.execute(
                """SELECT l.id,l.category,l.title,l.level,l.content,m.description,m.estimated_minutes,
                          m.reward_xp,m.reward_coins,w.title world_title,w.sequence_order world_order,
                          lp.completion_status,lp.stars
                   FROM lessons l JOIN level_metadata m ON m.lesson_id=l.id
                   JOIN learning_worlds w ON w.id=m.world_id
                   LEFT JOIN level_progress lp ON lp.user_id=? AND lp.lesson_id=l.id
                   WHERE l.category=? ORDER BY l.level""",
                (uid, active_category),
            ).fetchall()
            next_open = None
            for level in levels:
                if level["completion_status"] != "completed":
                    next_open = level["id"]
                    break
            for level in levels:
                mastered = db.execute(
                    """SELECT COUNT(*) FROM question_state s JOIN questions q ON q.id=s.question_id
                       WHERE s.user_id=? AND q.lesson_id=? AND s.mastered=1""",
                    (uid, level["id"]),
                ).fetchone()[0]
                total_questions = db.execute("SELECT COUNT(*) FROM questions WHERE lesson_id=?", (level["id"],)).fetchone()[0]
                state = "completed" if level["completion_status"] == "completed" else (
                    "current" if level["id"] == next_open else "locked"
                )
                roadmap.append({
                    **dict(level),
                    "state": state,
                    "stars": level["stars"] or 0,
                    "mastered_questions": mastered,
                    "total_questions": total_questions,
                    "progress_percent": round(mastered * 100 / total_questions) if total_questions else 0,
                })
        goal = user["daily_goal_minutes"]
        activity["active_minutes"] = round(activity["active_seconds"] / 60, 1)
        activity["goal_percent"] = min(100, round(activity["active_seconds"] / (goal * 60) * 100)) if goal else 0
        unread = db.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0", (uid,)
        ).fetchone()[0]
    return jsonify({
        "user": user,
        "completed": done,
        "total_lessons": total,
        "completion_percent": round(done / total * 100) if total else 0,
        "badges": [dict(item) for item in badges],
        "achievements": [dict(item) for item in achievements],
        "recent": [dict(item) for item in recent],
        "selected_categories": selected,
        "active_category": active_category,
        "categories": [{"name": name, "description": description, "icon": icon} for name, description, icon in CATEGORIES if name in selected],
        "roadmap": roadmap,
        "daily_activity": activity,
        "daily_goal_minutes": goal,
        "unread_notifications": unread,
    })


@app.get("/api/leaderboard")
@login_required
def leaderboard():
    with get_db() as db:
        rows = db.execute("SELECT name,xp FROM users ORDER BY xp DESC,name ASC LIMIT 20").fetchall()
    return jsonify({"leaderboard": [dict(row) for row in rows]})


@app.get("/api/trades")
@login_required
def trades():
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM virtual_trades WHERE user_id=? ORDER BY created_at DESC LIMIT 30",
            (session["user_id"],),
        ).fetchall()
    return jsonify({"trades": [dict(row) for row in rows]})


@app.post("/api/trades")
@login_required
def create_trade():
    data = request.get_json(silent=True) or {}
    symbol = str(data.get("symbol", "")).strip().upper()
    side = str(data.get("side", "")).upper()
    try:
        quantity, price = float(data.get("quantity", 0)), float(data.get("price", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Quantity and price must be numbers."}), 400
    if (
        not re.fullmatch(r"[A-Z0-9._-]{1,12}", symbol) or side not in ("BUY", "SELL")
        or not math.isfinite(quantity) or not math.isfinite(price) or quantity <= 0 or price <= 0
    ):
        return jsonify({"error": "Enter a symbol, BUY/SELL, and positive quantity and price."}), 400
    total = round(quantity * price, 2)
    if not math.isfinite(total):
        return jsonify({"error": "Trade amount is too large."}), 400
    uid = session["user_id"]
    with get_db() as db:
        user = db.execute("SELECT trado_cash FROM users WHERE id=?", (uid,)).fetchone()
        if side == "BUY" and user["trado_cash"] < total:
            return jsonify({"error": "Not enough virtual cash."}), 400
        if side == "BUY":
            db.execute("UPDATE users SET trado_cash=trado_cash-? WHERE id=?", (total, uid))
        else:
            db.execute("UPDATE users SET trado_cash=trado_cash+? WHERE id=?", (total, uid))
        db.execute(
            "INSERT INTO virtual_trades(user_id,symbol,side,quantity,price,total) VALUES(?,?,?,?,?,?)",
            (uid, symbol, side, quantity, price, total),
        )
    return jsonify({"message": "Virtual trade recorded.", "user": current_user()}), 201


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({"error": "Request is too large."}), 413


@app.errorhandler(500)
def server_error(error):
    app.logger.exception(error)
    return jsonify({"error": "An internal server error occurred."}), 500


if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False))
