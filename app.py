# -*- coding: utf-8 -*-
"""
📘 화트25 강의자료 및 Q&A 등록시스템
 - allowed_emails.txt 기반 공통 로그인
 - 교수 전용 업로드 (professor / keypass)
 - 학생 질문 등록 및 보기
 - Render Health Check 포함
작성자: Key 교수님
"""

from flask import Flask, render_template, request, redirect, url_for, session
import os, pandas as pd
from datetime import datetime

app = Flask(__name__)
app.secret_key = "key_flask_secret"

# 데이터 파일
DATA_FILE = "lecture_data.csv"
QUESTION_FILE = "questions.csv"
ALLOWED_FILE = "allowed_emails.txt"

# ─────────────────────────────
# 📂 CSV 로드/저장
# ─────────────────────────────
def load_csv(path, cols):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except:
            pass
    return pd.DataFrame(columns=cols)

def save_csv(df, path):
    df.to_csv(path, index=False, encoding="utf-8-sig")

# ─────────────────────────────
# 🏠 공통 로그인 페이지
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
# 📚 강의자료 페이지 + 질문 등록
# ─────────────────────────────
@app.route("/lecture", methods=["GET", "POST"], endpoint="lecture")
def lecture():
    if "user" not in session:
        return redirect(url_for("home"))

    lectures = load_csv(DATA_FILE, ["title", "content", "file_link", "site_link", "uploaded_at"])
    questions = load_csv(QUESTION_FILE, ["email", "question", "password", "created_at"])

    if request.method == "POST":
        q_text = request.form.get("question", "").strip()
        pw = request.form.get("password", "").strip()
        if q_text:
            new_q = pd.DataFrame([{
                "email": session["user"],
                "question": q_text,
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
# 👨‍🏫 교수 로그인 (업로드 전용)
# ─────────────────────────────
@app.route("/login_prof", methods=["GET", "POST"], endpoint="login_prof")
def login_prof():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == "professor" and password == "keypass":
            session["professor"] = True
            return redirect(url_for("upload_lecture"))
        else:
            error = "로그인 실패: 교수 계정만 접근 가능합니다."
    return render_template("login_prof.html", error=error)

# ─────────────────────────────
# 📤 교수 전용 강의자료 업로드
# ─────────────────────────────
@app.route("/upload_lecture", methods=["GET", "POST"], endpoint="upload_lecture")
def upload_lecture():
    if not session.get("professor"):
        return redirect(url_for("login_prof"))

    lectures = load_csv(DATA_FILE, ["title", "content", "file_link", "site_link", "uploaded_at"])

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        file_link = request.form.get("file_link", "").strip()
        site_link = request.form.get("site_link", "").strip()

        if title:
            new_entry = pd.DataFrame([{
                "title": title,
                "content": content,
                "file_link": file_link,
                "site_link": site_link,
                "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }])
            lectures = pd.concat([lectures, new_entry], ignore_index=True)
            save_csv(lectures, DATA_FILE)

        return redirect(url_for("lecture"))

    return render_template("upload_lecture.html", data=lectures.to_dict(orient="records"))

# ─────────────────────────────
# 🚪 로그아웃
# ─────────────────────────────
@app.route("/logout", endpoint="logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ─────────────────────────────
# 🩺 Render Health Check
# ─────────────────────────────
@app.route("/health")
def health():
    return "OK", 200

# ─────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
