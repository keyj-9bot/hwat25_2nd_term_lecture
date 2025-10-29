# -*- coding: utf-8 -*-
"""
📘 연암공대 화트25 학습지원시스템 (세션 안정형 Final Stable)
작성자: Key 교수님
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import pandas as pd
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "key_flask_secret"

# ───────────── 세션 안정화 (Render HTTPS 환경 대응) ─────────────
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)

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
            return pd.read_csv(path)
        except:
            pass
    return pd.DataFrame(columns=cols)

def save_csv(path, df):
    df.to_csv(path, index=False, encoding="utf-8-sig")

# ───────────── 라우트 ─────────────
@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email:
            flash("이메일을 입력하세요.", "danger")
            return redirect(url_for("login"))

        # 허용 이메일 로드
        if os.path.exists(ALLOWED_EMAILS):
            with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
                allowed = [e.strip() for e in f.readlines() if e.strip()]
        else:
            allowed = []

        # 로그인 처리
        if email in allowed:
            session["email"] = email
            session.permanent = True
            flash("로그인 성공!", "success")
            return redirect(url_for("home"))
        else:
            flash("등록되지 않은 이메일입니다.", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/home")
def home():
    email = session.get("email")
    if not email:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for("login"))
    return render_template("home.html", email=email)

@app.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.", "info")
    return redirect(url_for("login"))

# ───────────── 강의자료 업로드 ─────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    email = session.get("email")
    if not email:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for("login"))

    # 교수 이메일만 업로드 가능
    with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
        allowed = [e.strip() for e in f.readlines() if e.strip()]
    if email != allowed[0]:
        flash("접근 권한이 없습니다.", "danger")
        return redirect(url_for("home"))

    df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date"])
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        links = "; ".join([v for k, v in request.form.items() if k.startswith("link") and v])
        filenames = []

        # 파일 저장
        if "files" in request.files:
            files = request.files.getlist("files")
            for file in files:
                if file and file.filename:
                    fname = secure_filename(file.filename)
                    file.save(os.path.join(UPLOAD_FOLDER, fname))
                    filenames.append(fname)

        df.loc[len(df)] = {
            "title": title,
            "content": content,
            "files": "; ".join(filenames),
            "links": links,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        save_csv(DATA_LECTURE, df)
        flash("강의자료가 게시되었습니다.", "success")
        return redirect(url_for("upload_lecture"))

    return render_template("upload_lecture.html", lectures=df.to_dict("records"))

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ───────────── 앱 실행 ─────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
