# -*- coding: utf-8 -*-
"""
📘 화트25 강의자료 및 Q&A 등록시스템 (Yonam College)
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
PASSWORD_FILE = "/tmp/prof_password.txt"
QUESTION_FILE = "/tmp/student_questions.csv"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ─────────────────────────────
# 🔐 비밀번호 초기화
# ─────────────────────────────
if not os.path.exists(PASSWORD_FILE):
    with open(PASSWORD_FILE, "w", encoding="utf-8") as f:
        f.write("keypass")


def get_password():
    try:
        with open(PASSWORD_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        return "keypass"


def set_password(new_pw):
    with open(PASSWORD_FILE, "w", encoding="utf-8") as f:
        f.write(new_pw.strip())


# ─────────────────────────────
# 📂 CSV 로드 및 저장
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


# ─────────────────────────────
# 🏠 홈
# ─────────────────────────────
@app.route("/")
def home():
    return render_template("home.html")


# ─────────────────────────────
# 💬 학생 질문 페이지
# ─────────────────────────────
@app.route("/lecture", methods=["GET", "POST"])
def lecture():
    if not os.path.exists(QUESTION_FILE):
        pd.DataFrame(columns=["번호", "질문", "비밀번호", "작성시각"]).to_csv(QUESTION_FILE, index=False)

    try:
        df = pd.read_csv(QUESTION_FILE)
    except:
        df = pd.DataFrame(columns=["번호", "질문", "비밀번호", "작성시각"])

    if request.method == "POST":
        question = request.form.get("question", "").strip()
        pw = request.form.get("password", "").strip()
        if question:
            new_row = {
                "번호": len(df) + 1,
                "질문": question,
                "비밀번호": pw,
                "작성시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(QUESTION_FILE, index=False, encoding="utf-8-sig")
        return redirect(url_for("lecture"))

    data = load_data()
    return render_template("lecture.html", data=data, qdata=df.to_dict(orient="records"))


# ─────────────────────────────
# 💬 질문 수정/삭제
# ─────────────────────────────
@app.route("/edit_question/<int:index>", methods=["POST"])
def edit_question(index):
    df = pd.read_csv(QUESTION_FILE)
    pw = request.form.get("pw", "")
    new_text = request.form.get("new_text", "").strip()
    if 0 <= index < len(df) and df.loc[index, "비밀번호"] == pw:
        df.loc[index, "질문"] = new_text
        df.to_csv(QUESTION_FILE, index=False, encoding="utf-8-sig")
    return redirect(url_for("lecture"))


@app.route("/delete_question/<int:index>", methods=["POST"])
def delete_question(index):
    df = pd.read_csv(QUESTION_FILE)
    pw = request.form.get("pw", "")
    if 0 <= index < len(df) and df.loc[index, "비밀번호"] == pw:
        df = df.drop(index)
        df["번호"] = range(1, len(df) + 1)
        df.to_csv(QUESTION_FILE, index=False, encoding="utf-8-sig")
    return redirect(url_for("lecture"))


# ─────────────────────────────
# 🔑 교수 로그인 / 로그아웃
# ─────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == "professor" and password == get_password():
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
# 📤 강의자료 업로드
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
        uploaded_files = request.files.getlist("file")

        filenames = []
        for file in uploaded_files:
            if file.filename:
                save_path = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(save_path)
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
    if "user" not in session or session.get("role") != "professor":
        return "접근 권한이 없습니다.", 403
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


# ─────────────────────────────
# 🩺 Health Check
# ─────────────────────────────
@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


