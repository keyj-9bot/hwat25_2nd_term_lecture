# -*- coding: utf-8 -*-
"""
📘 화공트랙 강의자료 및 Q&A 시스템 (공통 로그인 + 교수 업로드 전용)
작성자: Key 교수님
"""

from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "key_flask_secret"

DATA_FILE = "lecture_data.csv"
ALLOWED_FILE = "allowed_emails.txt"
QUESTION_FILE = "/tmp/student_questions.csv"

# ─────────────────────────────
# 📂 파일 존재 확인 및 자동 생성
# ─────────────────────────────
def ensure_files():
    if not os.path.exists(ALLOWED_FILE):
        with open(ALLOWED_FILE, "w", encoding="utf-8") as f:
            f.write("professor@yc.ac.kr\n")

    if not os.path.exists(DATA_FILE):
        pd.DataFrame(columns=["번호", "내용", "자료파일", "연관사이트", "비고", "업로드시각"]).to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

    if not os.path.exists(QUESTION_FILE):
        pd.DataFrame(columns=["번호", "질문", "비밀번호", "작성시각"]).to_csv(QUESTION_FILE, index=False, encoding="utf-8-sig")


def load_data():
    ensure_files()
    return pd.read_csv(DATA_FILE).to_dict(orient="records")


def save_data(data):
    pd.DataFrame(data).to_csv(DATA_FILE, index=False, encoding="utf-8-sig")


# ─────────────────────────────
# 🏠 공통 로그인 (학생/교수)
# ─────────────────────────────
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not os.path.exists(ALLOWED_FILE):
            return render_template("home.html", error="허용 이메일 파일이 없습니다. 관리자에게 문의하세요.")

        with open(ALLOWED_FILE, "r", encoding="utf-8") as f:
            allowed_emails = [line.strip().lower() for line in f.readlines()]

        if email in allowed_emails:
            session["common_user"] = email
            return redirect(url_for("lecture"))
        else:
            return render_template("home.html", error="등록되지 않은 사용자입니다.")

    return render_template("home.html")


# ─────────────────────────────
# 📚 강의자료 & Q&A (공통 접근)
# ─────────────────────────────
@app.route("/lecture", methods=["GET", "POST"])
def lecture():
    if "common_user" not in session:
        return redirect(url_for("home"))

    ensure_files()
    data = load_data()

    if request.method == "POST":
        question = request.form.get("question", "").strip()
        password = request.form.get("password", "").strip()

        if question:
            df = pd.read_csv(QUESTION_FILE)
            new_entry = {
                "번호": len(df) + 1,
                "질문": question,
                "비밀번호": password,
                "작성시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            df.to_csv(QUESTION_FILE, index=False, encoding="utf-8-sig")

        return redirect(url_for("lecture"))

    q_data = pd.read_csv(QUESTION_FILE).to_dict(orient="records")
    return render_template("lecture.html", data=data, q_data=q_data)


# ─────────────────────────────
# 🔑 교수 전용 로그인
# ─────────────────────────────
@app.route("/login_prof", methods=["GET", "POST"])
def login_prof():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == "professor" and password == "keypass":
            session["professor"] = True
            return redirect(url_for("upload_lecture"))
        else:
            return render_template("login_prof.html", error="로그인 실패: 교수 계정만 접근 가능합니다.")
    return render_template("login_prof.html")


# ─────────────────────────────
# 📤 교수 전용 업로드
# ─────────────────────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    if not session.get("professor"):
        return redirect(url_for("login_prof"))

    data = load_data()

    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        notes = request.form.get("notes", "").strip()

        file_urls = [x.strip() for x in request.form.getlist("file_url") if x.strip()]
        ref_sites = [x.strip() for x in request.form.getlist("ref_site") if x.strip()]

        new_entry = {
            "번호": len(data) + 1,
            "내용": topic,
            "자료파일": "; ".join(file_urls),
            "연관사이트": "; ".join(ref_sites),
            "비고": notes,
            "업로드시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        data.append(new_entry)
        save_data(data)
        return redirect(url_for("upload_lecture"))

    return render_template("upload_lecture.html", data=data)


# ─────────────────────────────
# 🚪 로그아웃 (모든 세션 종료)
# ─────────────────────────────
@app.route("/logout")
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
# 🚀 실행
# ─────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
