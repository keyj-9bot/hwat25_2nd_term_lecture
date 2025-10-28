# -*- coding: utf-8 -*-
"""
📘 연암공대 화트25 학습게시판 (공통 로그인 + 교수 업로드 + 질문 등록/보기)
작성자: Key 교수님
"""

from flask import Flask, render_template, request, redirect, url_for, session
import os, pandas as pd
from datetime import datetime

app = Flask(__name__)
app.secret_key = "key_flask_secret"
DATA_FILE = "lecture_data.csv"
QUESTION_FILE = "questions.csv"
ALLOWED_FILE = "allowed_emails.txt"

# ─────────────────────────────
# 📂 파일 로드/저장
# ─────────────────────────────
def load_csv(path, cols):
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame(columns=cols)

def save_csv(df, path):
    df.to_csv(path, index=False, encoding="utf-8-sig")

# ─────────────────────────────
# 🏠 공통 로그인
# ─────────────────────────────
@app.route("/", methods=["GET", "POST"], endpoint="home")
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
            error = "등록되지 않은 이메일입니다."
    return render_template("home.html", error=error)

# ─────────────────────────────
# 📚 강의자료 보기 & 질문 등록
# ─────────────────────────────
@app.route("/lecture", methods=["GET", "POST"], endpoint="lecture")
def lecture():
    if "user" not in session:
        return redirect(url_for("home"))

    lectures = load_csv(DATA_FILE, ["title", "content", "file_link", "site_link", "uploaded_at"])
    questions = load_csv(QUESTION_FILE, ["email", "question", "password", "created_at"])

    if request.method == "POST":
        email = session["user"]
        question = request.form.get("question")
        pw = request.form.get("password")
        new_q = pd.DataFrame([{
            "email": email,
            "question": question,
            "password": pw,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }])
        questions = pd.concat([questions, new_q], ignore_index=True)
        save_csv(questions, QUESTION_FILE)
        return redirect(url_for("lecture"))

    return render_template("lecture.html",
                           lectures=lectures.to_dict(orient="records"),
                           questions=questions.to_dict(orient="records"))

# ─────────────────────────────
# 👨‍🏫 교수 로그인
# ─────────────────────────────
@app.route("/login_prof", methods=["GET", "POST"], endpoint="login_prof")
def login_prof():
    error = None
    if request.method == "POST":
        user = request.form.get("username")
        pw = request.form.get("password")
        if user == "professor" and pw == "keypass":
            session["professor"] = True
            return redirect(url_for("upload_lecture"))
        error = "교수 로그인 실패"
    return render_template("login_prof.html", error=error)

# ─────────────────────────────
# ⬆️ 강의자료 업로드
# ─────────────────────────────
@app.route("/upload_lecture", methods=["GET", "POST"], endpoint="upload_lecture")
def upload_lecture():
    if not session.get("professor"):
        return redirect(url_for("login_prof"))

    df = load_csv(DATA_FILE, ["title", "content", "file_link", "site_link", "uploaded_at"])
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
            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        df = pd.concat([df, new_data], ignore_index=True)
        save_csv(df, DATA_FILE)
        return redirect(url_for("lecture"))
    return render_template("upload_lecture.html")

# ─────────────────────────────
# 🚪 로그아웃
# ─────────────────────────────
@app.route("/logout", endpoint="logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ─────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
