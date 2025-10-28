# -*- coding: utf-8 -*-
"""
📘 연암공대 화공트랙 강의자료 & Q&A 통합 시스템
작성자: Key 교수님 (2025)
- 교수 전용 업로드
- 학생 질문 비밀번호 기반 수정/삭제
- 실제 파일 업로드 (/tmp/uploads/)
- 네비게이션 통합 디자인
"""

from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "key_flask_secret"

# ─────────────────────────────
# 📁 데이터 파일
# ─────────────────────────────
DATA_FILE = "lecture_data.csv"
QUESTION_FILE = "/tmp/student_questions.csv"
UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ─────────────────────────────
# 📂 데이터 로드/저장
# ─────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            return df.to_dict(orient="records")
        except:
            return []
    return []

def save_data(data):
    df = pd.DataFrame(data)
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

def load_questions():
    if os.path.exists(QUESTION_FILE):
        try:
            df = pd.read_csv(QUESTION_FILE)
            return df.to_dict(orient="records")
        except:
            return []
    return []

def save_questions(data):
    df = pd.DataFrame(data)
    df.to_csv(QUESTION_FILE, index=False, encoding="utf-8-sig")


# ─────────────────────────────
# 🏠 홈
# ─────────────────────────────
@app.route("/")
def home():
    return render_template("home.html")


# ─────────────────────────────
# 📄 강의자료 & Q&A
# ─────────────────────────────
@app.route("/lecture", methods=["GET", "POST"])
def lecture():
    lectures = load_data()
    questions = load_questions()

    # 학생 질문 등록
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        pw = request.form.get("password", "").strip()
        if question and pw:
            new_q = {
                "번호": len(questions) + 1,
                "질문": question,
                "비밀번호": pw,
                "작성시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            questions.append(new_q)
            save_questions(questions)
        return redirect(url_for("lecture"))

    return render_template("lecture.html", lectures=lectures, questions=questions)


# ─────────────────────────────
# ✏️ 학생 질문 수정/삭제
# ─────────────────────────────
@app.route("/edit_question/<int:index>", methods=["POST"])
def edit_question(index):
    questions = load_questions()
    if 0 <= index < len(questions):
        pw = request.form.get("password", "")
        new_text = request.form.get("new_text", "")
        if questions[index]["비밀번호"] == pw:
            questions[index]["질문"] = new_text
            save_questions(questions)
        else:
            return "<script>alert('비밀번호가 일치하지 않습니다.');history.back();</script>"
    return redirect(url_for("lecture"))

@app.route("/delete_question/<int:index>", methods=["POST"])
def delete_question(index):
    questions = load_questions()
    pw = request.form.get("password", "")
    if 0 <= index < len(questions):
        if questions[index]["비밀번호"] == pw:
            del questions[index]
            for i, q in enumerate(questions):
                q["번호"] = i + 1
            save_questions(questions)
        else:
            return "<script>alert('비밀번호가 일치하지 않습니다.');history.back();</script>"
    return redirect(url_for("lecture"))


# ─────────────────────────────
# 🔑 로그인 / 로그아웃
# ─────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == "professor" and password == "keypass":
            session["user"] = username
            session["role"] = "professor"
            return redirect(url_for("upload_lecture"))
        else:
            return render_template("login.html", error="로그인 실패: 교수 전용입니다.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ─────────────────────────────
# 📤 교수 전용 업로드
# ─────────────────────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    if "user" not in session or session.get("role") != "professor":
        return redirect(url_for("login"))

    data = load_data()

    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        notes = request.form.get("notes", "").strip()
        ref_sites = [x.strip() for x in request.form.getlist("ref_site") if x.strip()]

        uploaded_files = []
        for f in request.files.getlist("file_url"):
            if f.filename:
                filepath = os.path.join(UPLOAD_FOLDER, f.filename)
                f.save(filepath)
                uploaded_files.append(f.filename)

        new_entry = {
            "번호": len(data) + 1,
            "내용": topic,
            "자료파일": "; ".join(uploaded_files) if uploaded_files else "없음",
            "연관사이트": "; ".join(ref_sites),
            "비고": notes,
            "업로드시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        data.append(new_entry)
        save_data(data)

        return redirect(url_for("upload_lecture"))

    return render_template("upload_lecture.html", data=data)


# ─────────────────────────────
# 📥 파일 다운로드
# ─────────────────────────────
@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


# ─────────────────────────────
# 🩺 Render Health Check
# ─────────────────────────────
@app.route("/health")
def health():
    return {"status": "ok"}, 200


# ─────────────────────────────
# 🚀 실행
# ─────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
