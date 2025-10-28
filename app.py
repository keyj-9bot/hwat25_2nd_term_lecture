# -*- coding: utf-8 -*-
"""
📘 연암공대 화트25 화공트랙 강의자료 및 Q&A 시스템
작성자: Key 교수님
"""

from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "key_flask_secret"

DATA_FILE = "lecture_data.csv"
UPLOAD_FOLDER = "/tmp/uploads"
QUESTION_FILE = "/tmp/student_questions.csv"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ─────────────────────────────
# 데이터 로드 및 저장
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
    pd.DataFrame(data).to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

# ─────────────────────────────
# 홈
# ─────────────────────────────
@app.route("/")
def home():
    return render_template("home.html")

# ─────────────────────────────
# 강의자료 & 질문 페이지
# ─────────────────────────────
@app.route("/lecture", methods=["GET", "POST"])
def lecture():
    columns = ["번호", "질문", "비밀번호", "작성시각"]
    if not os.path.exists(QUESTION_FILE):
        pd.DataFrame(columns=columns).to_csv(QUESTION_FILE, index=False, encoding="utf-8-sig")
    try:
        df = pd.read_csv(QUESTION_FILE)
        if not set(columns).issubset(df.columns):
            df = pd.DataFrame(columns=columns)
    except:
        df = pd.DataFrame(columns=columns)

    if request.method == "POST":
        q = request.form.get("question", "").strip()
        pw = request.form.get("password", "").strip()
        if q:
            new_row = {
                "번호": len(df) + 1,
                "질문": q,
                "비밀번호": pw,
                "작성시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(QUESTION_FILE, index=False, encoding="utf-8-sig")
        return redirect(url_for("lecture"))

    data = load_data()
    return render_template("lecture.html", data=data, qdata=df.to_dict(orient="records"))

# ─────────────────────────────
# 교수 로그인 / 로그아웃
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
    return redirect("/")

# ─────────────────────────────
# 강의자료 업로드
# ─────────────────────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    if "user" not in session:
        return redirect(url_for("login"))

    data = load_data()
    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        notes = request.form.get("notes", "").strip()
        ref_sites = [x.strip() for x in request.form.getlist("ref_site") if x.strip()]
        files = request.files.getlist("file")

        filenames = []
        for file in files:
            if file.filename:
                path = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(path)
                filenames.append(file.filename)

        new_entry = {
            "번호": len(data) + 1,
            "내용": topic,
            "자료파일": "; ".join(filenames),
            "연관사이트": "; ".join(ref_sites),
            "비고": notes,
            "업로드시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        data.append(new_entry)
        save_data(data)
        return redirect(url_for("upload_lecture"))

    return render_template("upload_lecture.html", data=data)

@app.route("/download/<filename>")
def download(filename):
    if "user" not in session:
        return "로그인 필요", 403
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

# ─────────────────────────────
# 헬스체크
# ─────────────────────────────
@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
