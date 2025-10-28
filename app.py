# -*- coding: utf-8 -*-
"""
📘 연암공대 화트25 학습게시판 (공통 이메일 로그인 + 교수 업로드 시스템)
작성자: Key 교수님
"""

from flask import Flask, render_template, request, redirect, url_for, session
import os
import pandas as pd

app = Flask(__name__)
app.secret_key = "key_flask_secret"
DATA_FILE = "lecture_data.csv"
ALLOWED_FILE = "allowed_emails.txt"

# ─────────────────────────────
# 📂 데이터 로드/저장 함수
# ─────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=["title", "content", "file_link", "site_link", "uploaded_at"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

# ─────────────────────────────
# 🏠 홈(공통 이메일 로그인)
# ─────────────────────────────
@app.route("/", methods=["GET", "POST"])
def home():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        try:
            with open(ALLOWED_FILE, "r", encoding="utf-8") as f:
                allowed = [line.strip().lower() for line in f if line.strip()]
        except FileNotFoundError:
            allowed = []

        if email in allowed:
            session["user"] = email
            return redirect(url_for("lecture"))
        else:
            error = "등록되지 않은 이메일 주소입니다."

    return render_template("home.html", error=error)

# ─────────────────────────────
# 📚 강의자료 보기 (공통)
# ─────────────────────────────
@app.route("/lecture")
def lecture():
    if "user" not in session:
        return redirect(url_for("home"))

    df = load_data()
    return render_template("lecture.html", tables=df.to_dict(orient="records"))

# ─────────────────────────────
# 👨‍🏫 교수 로그인
# ─────────────────────────────
@app.route("/login_prof", methods=["GET", "POST"])
def login_prof():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == "professor" and password == "keypass":
            session["professor"] = True
            return redirect(url_for("upload_lecture"))
        else:
            error = "로그인 실패: 교수 계정만 접근 가능합니다."

    return render_template("login_prof.html", error=error)

# ─────────────────────────────
# ⬆️ 강의자료 업로드 (교수 전용)
# ─────────────────────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    if not session.get("professor"):
        return redirect(url_for("login_prof"))

    df = load_data()
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        file_link = request.form.get("file_link")
        site_link = request.form.get("site_link")

        new_data = pd.DataFrame([{
            "title": title,
            "content": content,
            "file_link": file_link,
            "site_link": site_link,
            "uploaded_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        df = pd.concat([df, new_data], ignore_index=True)
        save_data(df)
        return redirect(url_for("lecture"))

    return render_template("upload_lecture.html", tables=df.to_dict(orient="records"))

# ─────────────────────────────
# 🚪 로그아웃
# ─────────────────────────────
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ─────────────────────────────
# 🧭 메인
# ─────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
