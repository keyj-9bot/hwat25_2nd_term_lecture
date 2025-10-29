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


# ─────────────── 기본 홈 라우트 ───────────────
@app.route("/")
def home():
    # 로그인 페이지로 자동 이동
    return redirect(url_for("login_prof"))



# ─────────────── 교수 로그인 ───────────────
@app.route("/login_prof", methods=["GET", "POST"])
def login_prof():
    if request.method == "POST":
        email = request.form.get("email", "").strip()

        # 허용된 이메일만 로그인 허용
        if os.path.exists(ALLOWED_EMAILS):
            with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
                allowed_emails = [line.strip() for line in f.readlines()]

            if email in allowed_emails:
                session["email"] = email
                flash("✅ 교수님 환영합니다!")
                return redirect(url_for("upload_lecture"))
            else:
                flash("❌ 등록된 이메일만 로그인할 수 있습니다.")
                return redirect(url_for("login_prof"))
        else:
            flash("⚠️ 허용된 이메일 파일이 없습니다.")
            return redirect(url_for("login_prof"))

    return render_template("login_prof.html")


# ─────────────── 로그아웃 ───────────────
@app.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.")
    return redirect(url_for("login_prof"))


# ─────────────── 강의자료 업로드 ───────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    if not check_login():
        return redirect(url_for("login_prof"))

    df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date"])
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        date = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 파일 저장
        files = []
        for file in request.files.getlist("files"):
            if file and file.filename:
                filename = secure_filename(file.filename)
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(save_path)
                files.append(filename)

        # 관련 사이트 링크
        links = [v for k, v in request.form.items() if k.startswith("link") and v.strip()]

        new_row = pd.DataFrame([{
            "title": title,
            "content": content,
            "files": ";".join(files),
            "links": ";".join(links),
            "date": date
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        save_csv(DATA_LECTURE, df)
        flash("📚 강의자료가 업로드되었습니다.")
        return redirect(url_for("upload_lecture"))

    return render_template("upload_lecture.html", lectures=df.to_dict("records"))


# ─────────────── 강의자료 다운로드 ───────────────
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ─────────────── 학습사이트(Q&A 포함) ───────────────
@app.route("/lecture", methods=["GET", "POST"])
def lecture():
    q_df = load_csv(DATA_QUESTIONS, ["id", "email", "title", "content", "date"])
    c_df = load_csv(DATA_COMMENTS, ["question_id", "email", "comment", "date"])

    if request.method == "POST":
        new_id = len(q_df) + 1
        title = request.form["title"]
        content = request.form["content"]
        email = request.form.get("email", "익명")
        date = datetime.now().strftime("%Y-%m-%d %H:%M")

        q_df.loc[len(q_df)] = [new_id, email, title, content, date]
        save_csv(DATA_QUESTIONS, q_df)
        flash("질문이 등록되었습니다.")
        return redirect(url_for("lecture"))

    questions = q_df.to_dict("records")
    comments = c_df.to_dict("records")
    return render_template("lecture.html", questions=questions, comments=comments)


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


# ─────────────── 캐시 무효화 ───────────────
@app.after_request
def add_header(response):
    """모든 HTML 응답에 캐시 무효화 헤더 추가"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if __name__ == "__main__":
    app.run(debug=True)



