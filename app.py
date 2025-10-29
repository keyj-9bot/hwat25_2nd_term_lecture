# -*- coding: utf-8 -*-
"""
📘 연암공대 화트25 강의자료 학습 & Q&A 시스템 (교수 확인게시 + 학생 열람 완전판)
작성자: Key 교수님
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import pandas as pd
import os
from datetime import datetime
from werkzeug.utils import secure_filename

# ─────────────────────────────
# 🌐 기본 설정
# ─────────────────────────────
app = Flask(__name__)
app.secret_key = "key_flask_secret"
app.config['TEMPLATES_AUTO_RELOAD'] = True

DATA_LECTURE = "lecture_data.csv"
DATA_QUESTIONS = "questions.csv"
DATA_COMMENTS = "comments.csv"
ALLOWED_EMAILS = "allowed_emails.txt"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ─────────────────────────────
# 📄 CSV 로드/저장
# ─────────────────────────────
def load_csv(path, cols):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception:
            pass
    return pd.DataFrame(columns=cols)


def save_csv(path, df):
    df.to_csv(path, index=False, encoding="utf-8-sig")


# ─────────────────────────────
# 🔑 로그인 확인
# ─────────────────────────────
def check_login():
    return "email" in session


# ─────────────────────────────
# 🏠 기본 페이지
# ─────────────────────────────
@app.route("/")
def home():
    return redirect(url_for("login"))


# ─────────────────────────────
# 👥 로그인 (교수·학생 공용)
# ─────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not os.path.exists(ALLOWED_EMAILS):
            flash("⚠️ allowed_emails.txt 파일이 없습니다.")
            return render_template("login.html")

        with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
            allowed = [line.strip().lower() for line in f if line.strip()]

        if email not in allowed:
            flash("❌ 등록된 이메일만 로그인할 수 있습니다.")
            return render_template("login.html")

        session["email"] = email
        session["role"] = "professor" if email == allowed[0] else "student"

        if session["role"] == "professor":
            flash("👨‍🏫 교수님 환영합니다.")
            return redirect(url_for("upload_lecture"))
        else:
            flash("👩‍🎓 학생 로그인 완료.")
            return redirect(url_for("lecture"))

    return render_template("login.html")


# ─────────────────────────────
# 🚪 로그아웃
# ─────────────────────────────
@app.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.")
    return redirect(url_for("login"))


# ─────────────────────────────
# 📤 강의자료 업로드 (교수 전용)
# ─────────────────────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    if not check_login() or session.get("role") != "professor":
        flash("⚠️ 교수 전용 페이지입니다.")
        return redirect(url_for("lecture"))

    df = load_csv(DATA_LECTURE, ["id", "title", "content", "files", "links", "date", "confirmed"])

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        date = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 파일 업로드
        uploaded_files = []
        for file in request.files.getlist("files"):
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                uploaded_files.append(filename)

        links = [v for k, v in request.form.items() if k.startswith("link") and v.strip()]
        new_id = len(df) + 1

        new_row = pd.DataFrame([{
            "id": new_id,
            "title": title,
            "content": content,
            "files": ";".join(uploaded_files),
            "links": ";".join(links),
            "date": date,
            "confirmed": False
        }])

        df = pd.concat([df, new_row], ignore_index=True)
        save_csv(DATA_LECTURE, df)
        flash("📘 강의자료가 업로드되었습니다. (확인 버튼 클릭 시 학습사이트에 게시됩니다.)")
        return redirect(url_for("upload_lecture"))

    return render_template("upload_lecture.html", lectures=df.to_dict("records"))


# ─────────────────────────────
# ✅ 강의자료 게시(확인)
# ─────────────────────────────
@app.route("/confirm_lecture/<int:lec_id>", methods=["POST"])
def confirm_lecture(lec_id):
    df = load_csv(DATA_LECTURE, ["id", "title", "content", "files", "links", "date", "confirmed"])
    df.loc[df["id"] == lec_id, "confirmed"] = True
    save_csv(DATA_LECTURE, df)
    flash("✅ 학습사이트에 게시되었습니다.")
    return redirect(url_for("upload_lecture"))


# ─────────────────────────────
# ✏️ 강의자료 수정
# ─────────────────────────────
@app.route("/edit_lecture/<int:lec_id>", methods=["GET", "POST"])
def edit_lecture(lec_id):
    if session.get("role") != "professor":
        return redirect(url_for("lecture"))

    df = load_csv(DATA_LECTURE, ["id", "title", "content", "files", "links", "date", "confirmed"])
    lec = df.loc[df["id"] == lec_id].iloc[0]

    if request.method == "POST":
        df.loc[df["id"] == lec_id, "title"] = request.form["title"]
        df.loc[df["id"] == lec_id, "content"] = request.form["content"]
        df.loc[df["id"] == lec_id, "links"] = ";".join([v for k, v in request.form.items() if k.startswith("link") and v.strip()])
        save_csv(DATA_LECTURE, df)
        flash("✏️ 수정이 완료되었습니다.")
        return redirect(url_for("upload_lecture"))

    return render_template("edit_lecture.html", lec=lec)


# ─────────────────────────────
# 🗑️ 강의자료 삭제
# ─────────────────────────────
@app.route("/delete_lecture/<int:lec_id>", methods=["POST"])
def delete_lecture(lec_id):
    df = load_csv(DATA_LECTURE, ["id", "title", "content", "files", "links", "date", "confirmed"])
    df = df[df["id"] != lec_id]
    save_csv(DATA_LECTURE, df)
    flash("🗑️ 강의자료가 삭제되었습니다.")
    return redirect(url_for("upload_lecture"))


# ─────────────────────────────
# 💬 학습사이트 (학생/교수 공용)
# ─────────────────────────────
@app.route("/lecture", methods=["GET", "POST"])
def lecture():
    l_df = load_csv(DATA_LECTURE, ["id", "title", "content", "files", "links", "date", "confirmed"])
    q_df = load_csv(DATA_QUESTIONS, ["id", "email", "title", "content", "date"])
    c_df = load_csv(DATA_COMMENTS, ["question_id", "email", "comment", "date"])

    lectures = l_df[l_df["confirmed"] == True]  # 게시된 자료만 표시

    if request.method == "POST":
        new_id = len(q_df) + 1
        title = request.form["title"]
        content = request.form["content"]
        email = session.get("email", "익명")
        date = datetime.now().strftime("%Y-%m-%d %H:%M")

        q_df.loc[len(q_df)] = [new_id, email, title, content, date]
        save_csv(DATA_QUESTIONS, q_df)
        flash("질문이 등록되었습니다.")
        return redirect(url_for("lecture"))

    return render_template(
        "lecture.html",
        lectures=lectures.to_dict("records"),
        questions=q_df.to_dict("records"),
        comments=c_df.to_dict("records"),
        email=session.get("email"),
        role=session.get("role")
    )


# ─────────────────────────────
# 💭 댓글 등록
# ─────────────────────────────
@app.route("/add_comment/<int:question_id>", methods=["POST"])
def add_comment(question_id):
    email = session.get("email", "익명")
    comment = request.form["comment"]
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    df = load_csv(DATA_COMMENTS, ["question_id", "email", "comment", "date"])
    df.loc[len(df)] = [question_id, email, comment, date]
    save_csv(DATA_COMMENTS, df)
    flash("💬 댓글이 등록되었습니다.")
    return redirect(url_for("lecture"))


# ─────────────────────────────
# 📁 파일 다운로드
# ─────────────────────────────
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ─────────────────────────────
# 🚫 캐시 무효화
# ─────────────────────────────
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ─────────────────────────────
# 🚀 실행
# ─────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)



