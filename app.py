# -*- coding: utf-8 -*-
"""
📘 연암공대 화트25 강의자료 학습 & Q&A 시스템 (개선 완전판)
작성자: Key 교수님
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import pandas as pd
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "key_flask_secret"
app.config['TEMPLATES_AUTO_RELOAD'] = True


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
            return pd.read_csv(path)
        except:
            pass
    return pd.DataFrame(columns=cols)


def save_csv(path, df):
    df.to_csv(path, index=False, encoding="utf-8-sig")


# ─────────────── 로그인 확인 ───────────────
def check_login():
    return "email" in session


# ──────────────── 로그인 ────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()

        # 허용된 이메일만 로그인 허용
        if os.path.exists(ALLOWED_EMAILS):
            with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
                allowed = [line.strip() for line in f.readlines()]
        else:
            allowed = []

        if email in allowed:
            session["email"] = email
            flash(f"✅ 로그인 성공: {email}")
            return redirect(url_for("upload_lecture"))
        else:
            flash("❌ 등록되지 않은 이메일입니다.")
            return redirect(url_for("login"))

    return render_template("login.html")



@app.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.")
    return redirect(url_for("login"))


# ─────────────── 강의자료 업로드 ───────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    if not check_login():
        flash("로그인이 필요합니다.")
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        files = request.files.getlist("files")
        links = request.form.getlist("links")
        upload_time = datetime.now().strftime("%Y-%m-%d %H:%M")

        saved_files = []
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(save_path)
                saved_files.append(filename)

        df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "time"])
        df.loc[len(df)] = [title, content, ";".join(saved_files), ";".join(links), upload_time]
        save_csv(DATA_LECTURE, df)
        flash("강의자료가 업로드되었습니다.")
        return redirect(url_for("lecture"))

    return render_template("upload_lecture.html")


@app.route("/uploads/<path:filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


# ─────────────── 학습사이트(Q&A 포함) ───────────────
@app.route("/lecture")
def lecture():
    if not check_login():
        flash("로그인이 필요합니다.")
        return redirect(url_for("login"))

    df_lecture = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "time"])
    df_question = load_csv(DATA_QUESTIONS, ["id", "title", "content", "email", "date"])
    df_comment = load_csv(DATA_COMMENTS, ["question_id", "email", "comment", "date"])

    return render_template("lecture.html",
                           lectures=df_lecture[::-1].iterrows(),
                           questions=df_question[::-1].iterrows(),
                           comments=df_comment)


# ─────────────── 질문 등록 ───────────────
@app.route("/add_question", methods=["POST"])
def add_question():
    title = request.form["title"]
    content = request.form["content"]
    email = session.get("email", "익명")
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    df = load_csv(DATA_QUESTIONS, ["id", "title", "content", "email", "date"])
    new_id = df["id"].max() + 1 if not df.empty else 1
    df.loc[len(df)] = [new_id, title, content, email, date]
    save_csv(DATA_QUESTIONS, df)
    flash("질문이 등록되었습니다.")
    return redirect(url_for("lecture"))


# ─────────────── 질문 삭제 ───────────────
@app.route("/delete_question/<int:id>")
def delete_question(id):
    df = load_csv(DATA_QUESTIONS, ["id", "title", "content", "email", "date"])
    df = df[df["id"] != id]
    save_csv(DATA_QUESTIONS, df)
    flash("질문이 삭제되었습니다.")
    return redirect(url_for("lecture"))


# ─────────────── 질문 수정 ───────────────
@app.route("/edit_question/<int:id>", methods=["GET", "POST"])
def edit_question(id):
    df = load_csv(DATA_QUESTIONS, ["id", "title", "content", "email", "date"])
    question = df.loc[df["id"] == id]
    if question.empty:
        flash("질문을 찾을 수 없습니다.")
        return redirect(url_for("lecture"))

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        df.loc[df["id"] == id, ["title", "content"]] = [title, content]
        save_csv(DATA_QUESTIONS, df)
        flash("질문이 수정되었습니다.")
        return redirect(url_for("lecture"))

    q = question.iloc[0]
    return render_template("edit_question.html", question=q)


# ─────────────── 댓글 등록 ───────────────
@app.route("/add_comment/<int:question_id>", methods=["POST"])
def add_comment(question_id):
    email = session.get("email", "익명")
    comment = request.form["comment"]
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    df = load_csv(DATA_COMMENTS, ["question_id", "email", "comment", "date"])
    df.loc[len(df)] = [question_id, email, comment, date]
    save_csv(DATA_COMMENTS, df)
    flash("댓글이 등록되었습니다.")
    return redirect(url_for("lecture"))

# ─────────────────────────────
# 🔒 캐시 무효화 (HTML 자동 새로고침)
# ─────────────────────────────
@app.after_request
def add_header(response):
    """
    모든 HTML 응답에 캐시 무효화 헤더를 추가.
    브라우저와 Render가 항상 최신 템플릿을 로드하도록 함.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if __name__ == "__main__":
    app.run(debug=True)


