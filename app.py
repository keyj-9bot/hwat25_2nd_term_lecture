# -*- coding: utf-8 -*-
"""
📘 연암공대 화트25 강의자료 학습 & Q&A 시스템 (세션 안정판 + 자동삭제 + Q&A)
작성자: Key 교수님
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import pandas as pd
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "key_flask_secret"

# ✅ 세션 설정 (Render HTTPS 대응)
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="None",
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=3)
)

# ─────────────── 설정 ───────────────
DATA_LECTURE = "lecture_data.csv"
DATA_QUESTIONS = "questions.csv"
DATA_COMMENTS = "comments.csv"
ALLOWED_EMAILS = "allowed_emails.txt"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ─────────────── CSV 로드/저장 ───────────────
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


# ─────────────── 자동 삭제(15일 경과자료) ───────────────
def auto_delete_old_lectures():
    df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date", "confirmed"])
    if not df.empty:
        now = datetime.now()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df[df["date"].notna()]
        df = df[df["date"] > now - timedelta(days=15)]
        save_csv(DATA_LECTURE, df)


# ─────────────── 기본 홈 ───────────────
@app.route("/")
def index():
    if "email" in session:
        return redirect(url_for("home"))
    return redirect(url_for("login"))


# ─────────────── 로그인 ───────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not os.path.exists(ALLOWED_EMAILS):
            flash("허용된 이메일 목록 파일이 없습니다.", "error")
            return redirect(url_for("login"))

        with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
            allowed = [e.strip() for e in f.readlines() if e.strip()]

        if email in allowed:
            session["email"] = email
            session.permanent = True
            flash("로그인 성공!", "success")
            return redirect(url_for("home"))
        else:
            flash("학교에 등록된 이메일이 아닙니다.", "error")
            return redirect(url_for("login"))
    return render_template("login.html")


# ─────────────── 로그아웃 ───────────────
@app.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.", "info")
    return redirect(url_for("login"))


# ─────────────── 홈 ───────────────
@app.route("/home")
def home():
    if "email" not in session:
        flash("세션이 만료되었습니다. 다시 로그인하세요.", "error")
        return redirect(url_for("login"))
    return render_template("home.html", email=session["email"])


# ─────────────── 교수 업로드 ───────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
        allowed = [e.strip() for e in f.readlines() if e.strip()]
    professor_email = allowed[0] if allowed else None

    if email != professor_email:
        flash("교수만 접근할 수 있습니다.", "error")
        return redirect(url_for("lecture"))

    df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date", "confirmed"])
    auto_delete_old_lectures()

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

        df.loc[len(df)] = [title, content, file_str, link_str, date, True]
        save_csv(DATA_LECTURE, df)
        flash("강의자료가 게시되었습니다.", "success")
        return redirect(url_for("upload_lecture"))

    df.fillna("", inplace=True)
    return render_template("upload_lecture.html", lectures=df.to_dict("records"))


# ─────────────── 학습 사이트 (Q&A 하단) ───────────────
@app.route("/lecture", methods=["GET", "POST"])
def lecture():
    if "email" not in session:
        return redirect(url_for("login"))

    auto_delete_old_lectures()
    df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date", "confirmed"])
    lectures = df[df["confirmed"] == True].to_dict("records")

    qdf = load_csv(DATA_QUESTIONS, ["id", "email", "question", "date"])
    cdf = load_csv(DATA_COMMENTS, ["qid", "email", "comment", "date"])

    if request.method == "POST":
        qid = request.form.get("qid")
        if "question" in request.form:
            new_id = len(qdf) + 1
            qdf.loc[len(qdf)] = [new_id, session["email"], request.form["question"], datetime.now().strftime("%Y-%m-%d %H:%M")]
            save_csv(DATA_QUESTIONS, qdf)
        elif "comment" in request.form:
            cdf.loc[len(cdf)] = [qid, session["email"], request.form["comment"], datetime.now().strftime("%Y-%m-%d %H:%M")]
            save_csv(DATA_COMMENTS, cdf)
        return redirect(url_for("lecture"))

    return render_template("lecture.html", lectures=lectures, questions=qdf.to_dict("records"), comments=cdf.to_dict("records"), email=session["email"])


# ─────────────── Q&A 수정/삭제 ───────────────
@app.route("/delete_question/<int:qid>")
def delete_question(qid):
    if "email" not in session:
        return redirect(url_for("login"))
    qdf = load_csv(DATA_QUESTIONS, ["id", "email", "question", "date"])
    qdf = qdf[qdf["id"] != qid]
    save_csv(DATA_QUESTIONS, qdf)
    flash("질문이 삭제되었습니다.", "info")
    return redirect(url_for("lecture"))


@app.route("/delete_comment/<int:index>")
def delete_comment(index):
    if "email" not in session:
        return redirect(url_for("login"))
    cdf = load_csv(DATA_COMMENTS, ["qid", "email", "comment", "date"])
    if 0 <= index < len(cdf):
        cdf.drop(index=index, inplace=True)
        save_csv(DATA_COMMENTS, cdf)
    flash("댓글이 삭제되었습니다.", "info")
    return redirect(url_for("lecture"))


# ─────────────── 파일 보기 ───────────────
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ─────────────── 실행 ───────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)


