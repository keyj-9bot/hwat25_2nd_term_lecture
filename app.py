# -*- coding: utf-8 -*-
"""
📘 연암공대 화공트랙 강의자료 + 로그인 시스템 (Render 절대경로 대응)
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
import pandas as pd
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "key_flask_secret")

# ─────────────────────────────
# 📁 절대경로 지정
# ─────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "lecture_data.csv")
QNA_FILE = os.path.join(BASE_DIR, "lecture_qna.csv")
ALLOWED_EMAILS_FILE = os.path.join(BASE_DIR, "allowed_emails.txt")

# ✅ Render Health Check
@app.route("/health")
def health_check():
    return "OK", 200


# ─────────────────────────────
# 🔐 로그인
# ─────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    # 절대경로로 allowed_emails.txt 읽기
    if not os.path.exists(ALLOWED_EMAILS_FILE):
        return ⚠️ allowed_emails.txt 파일이 서버에 없습니다.", 500

    with open(ALLOWED_EMAILS_FILE, "r", encoding="utf-8-sig") as f:
        allowed_emails = [line.strip().lower() for line in f if line.strip()]

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if email in allowed_emails:
            session["user"] = email
            flash(f"✅ {email} 님 환영합니다!", "success")
            return redirect(url_for("lecture"))
        else:
            flash("❌ 허용되지 않은 이메일입니다.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("👋 로그아웃되었습니다.", "info")
    return redirect(url_for("login"))


# ─────────────────────────────
# 🚧 로그인 보호 데코레이터
# ─────────────────────────────
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            flash("로그인이 필요합니다.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# ─────────────────────────────
# 📘 강의자료 페이지
# ─────────────────────────────
@app.route("/lecture")
@login_required
def lecture():
    data = []
    if os.path.exists(DATA_FILE):
        data = pd.read_csv(DATA_FILE, dtype=str).fillna("").to_dict("records")
    return render_template("lecture.html", data=data)


# ✅ 홈 리디렉션
@app.route("/")
def home():
    return redirect(url_for("login"))

print("✅ Flask app loaded successfully, available routes:")
print([r.rule for r in app.url_map.iter_rules()])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
