# -*- coding: utf-8 -*-
"""
📘 연암공대 화트25 강의자료 학습 & Q&A 시스템 (최종 개선 완전판)
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
            df = pd.read_csv(path)
            df = df.reindex(columns=cols, fill_value="")
            return df
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
    return redirect(url_for("login"))


# ─────────────── 로그인 ───────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email:
            flash("⚠️ 이메일을 입력하세요.")
            return redirect(url_for("login"))

        # 이메일 허용 목록
        if os.path.exists(ALLOWED_EMAILS):
            with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
                allowed_emails = [line.strip() for line in f.readlines()]
        else:
            allowed_emails = []

        # 세션 저장
        session["email"] = email
        session["is_professor"] = email == (allowed_emails[0] if allowed_emails else "")

        flash("✅ 로그인 성공: 학교 이메일 확인 완료.")
        if session["is_professor"]:
            return redirect(url_for("upload_lecture"))
        else:
            return redirect(url_for("lecture"))

    return render_template("login.html")


# ─────────────── 로그아웃 ───────────────
@app.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.")
    return redirect(url_for("login"))


# ─────────────── 강의자료 업로드 ───────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    if not check_login():
        return redirect(url_for("login"))
    if not session.get("is_professor", False):
        flash("⚠️ 교수 전용 페이지입니다.")
        return redirect(url_for("lecture"))

    df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date", "confirmed"])

    if request.method == "POST":
        try:
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            date = datetime.now().strftime("%Y-%m-%d %H:%M")

            upload_dir = os.path.join(os.getcwd(), UPLOAD_FOLDER)
            os.makedirs(upload_dir, exist_ok=True)

            # 파일 저장
            files = []
            for file in request.files.getlist("files"):
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    if not filename:
                        continue
                    save_path = os.path.join(upload_dir, filename)
                    file.save(save_path)
                    files.append(filename)

            # 링크 처리
            links = [v for k, v in request.form.items() if k.startswith("link") and v.strip()]

            new_row = pd.DataFrame([{
                "title": title,
                "content": content,
                "files": ";".join(files),
                "links": ";".join(links),
                "date": date,
                "confirmed": False
            }])

            df = pd.concat([df, new_row], ignore_index=True)
            save_csv(DATA_LECTURE, df)
            flash("📚 강의자료가 업로드되었습니다.")
        except Exception as e:
            flash(f"🚨 업로드 오류: {e}")

        return redirect(url_for("upload_lecture"))

    df.fillna("", inplace=True)
    return render_template("upload_lecture.html", lectures=df.to_dict("records"))


# ─────────────── 강의자료 파일 다운로드 ───────────────
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ─────────────── 강의자료 삭제 ───────────────
@app.route("/delete_lecture/<int:lec_index>", methods=["POST"])
def delete_lecture(lec_index):
    if not check_login():
        return redirect(url_for("login"))
    if not session.get("is_professor", False):
        flash("⚠️ 교수 전용 기능입니다.")
        return redirect(url_for("lecture"))

    df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date", "confirmed"])
    if lec_index < len(df):
        df = df.drop(index=lec_index).reset_index(drop=True)
        save_csv(DATA_LECTURE, df)
        flash("🗑️ 강의자료가 삭제되었습니다.")
    else:
        flash("⚠️ 존재하지 않는 항목입니다.")

    return redirect(url_for("upload_lecture"))


# ─────────────── 강의자료 게시(확인) ───────────────
@app.route("/confirm_lecture/<int:lec_index>", methods=["POST"])
def confirm_lecture(lec_index):
    if not check_login():
        return redirect(url_for("login"))
    if not session.get("is_professor", False):
        flash("⚠️ 교수 전용 기능입니다.")
        return redirect(url_for("lecture"))

    df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date", "confirmed"])
    if lec_index < len(df):
        df.at[lec_index, "confirmed"] = True
        save_csv(DATA_LECTURE, df)
        flash("✅ 학습사이트에 게시되었습니다.")
    else:
        flash("⚠️ 존재하지 않는 항목입니다.")
    return redirect(url_for("upload_lecture"))


# ─────────────── 학습 사이트 (학생/교수 공용) ───────────────
@app.route("/lecture", methods=["GET", "POST"])
def lecture():
    l_df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date", "confirmed"])
    q_df = load_csv(DATA_QUESTIONS, ["id", "email", "title", "content", "date"])
    c_df = load_csv(DATA_COMMENTS, ["question_id", "email", "comment", "date"])

    # 질문 등록
    if request.method == "POST":
        new_id = len(q_df) + 1
        title = request.form["title"]
        content = request.form["content"]
        email = session.get("email", "익명")
        date = datetime.now().strftime("%Y-%m-%d %H:%M")

        q_df.loc[len(q_df)] = [new_id, email, title, content, date]
        save_csv(DATA_QUESTIONS, q_df)
        flash("💬 질문이 등록되었습니다.")
        return redirect(url_for("lecture"))

    lectures = l_df[l_df["confirmed"] == True].to_dict("records")
    questions = q_df.to_dict("records")
    comments = c_df.to_dict("records")

    return render_template("lecture.html",
                           lectures=lectures,
                           questions=questions,
                           comments=comments,
                           email=session.get("email"),
                           is_professor=session.get("is_professor", False))


# ─────────────── 댓글 등록 ───────────────
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


# ─────────────── 캐시 무효화 ───────────────
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if __name__ == "__main__":
    app.run(debug=True)



