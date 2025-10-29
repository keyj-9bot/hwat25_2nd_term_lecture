# -*- coding: utf-8 -*-
"""
📘 연암공대 화트25 강의자료 학습 & Q&A 시스템 (세션 안정화 버전)
작성자: Key 교수님
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import pandas as pd
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "key_flask_secret"

# ✅ 세션 유지 설정 (Render HTTPS 환경 대응)
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="None",
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=3)
)

# ───────────── 설정 ─────────────
DATA_LECTURE = "lecture_data.csv"
DATA_QUESTIONS = "questions.csv"
DATA_COMMENTS = "comments.csv"
ALLOWED_EMAILS = "allowed_emails.txt"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ───────────── CSV 로드/저장 ─────────────
def load_csv(path, cols):
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            for col in cols:
                if col not in df.columns:
                    df[col] = ""
            return df
        except:
            pass
    return pd.DataFrame(columns=cols)

def save_csv(path, df):
    df.to_csv(path, index=False, encoding="utf-8-sig")

# ───────────── 파일 다운로드 ─────────────
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ───────────── 로그인 ─────────────
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()

        if not os.path.exists(ALLOWED_EMAILS):
            flash("허용 이메일 목록이 없습니다.")
            return redirect(url_for("login"))

        with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
            allowed = [e.strip() for e in f.readlines() if e.strip()]

        if email in allowed:
            session["email"] = email
            flash("로그인 성공!")
            return redirect(url_for("home"))
        else:
            flash("등록된 이메일이 아닙니다.")
    return render_template("login.html")

# ───────────── 로그아웃 ─────────────
@app.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.")
    return redirect(url_for("login"))

# ───────────── 홈 ─────────────
@app.route("/home")
def home():
    if "email" not in session:
        return redirect(url_for("login"))
    return render_template("home.html", email=session["email"])

# ───────────── 교수 업로드 ─────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    if "email" not in session:
        return redirect(url_for("login"))
    email = session["email"]

    with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
        allowed = [e.strip() for e in f.readlines() if e.strip()]
    professor_email = allowed[0] if allowed else None

    if email != professor_email:
        flash("교수만 접근 가능합니다.")
        return redirect(url_for("lecture"))

    df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date", "confirmed"])

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        date = datetime.now().strftime("%Y-%m-%d %H:%M")

        uploaded_files = request.files.getlist("files")
        filenames = []
        for file in uploaded_files:
            if file and file.filename:
                fname = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, fname))
                filenames.append(fname)
        file_str = ";".join(filenames)

        links = [v for k, v in request.form.items() if k.startswith("link") and v.strip()]
        link_str = ";".join(links)

        df.loc[len(df)] = [title, content, file_str, link_str, date, False]
        save_csv(DATA_LECTURE, df)
        flash("업로드 완료!")
        return redirect(url_for("upload_lecture"))

    df.fillna("", inplace=True)
    return render_template("upload_lecture.html", lectures=df.to_dict("records"))

# ───────────── 학습사이트 (Q&A + 강의자료) ─────────────
@app.route("/lecture", methods=["GET"])
def lecture():
    if "email" not in session:
        return redirect(url_for("login"))
    l_df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date", "confirmed"])
    lectures = l_df[l_df["confirmed"] == True].to_dict("records") if "confirmed" in l_df.columns else []
    return render_template("lecture.html", lectures=lectures, email=session["email"])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)


