# -*- coding: utf-8 -*-
"""
📘 연암공대 화트25 강의자료 학습 & Q&A 시스템 (통합 로그인 + 교수 권한 완전판)
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
ALLOWED_EMAILS = "allowed_emails.txt"  # 교수 이메일 목록
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

def is_professor():
    """현재 로그인한 사용자가 allowed_emails.txt의 첫 번째 교수인지 확인"""
    if not check_login():
        return False
    if not os.path.exists(ALLOWED_EMAILS):
        return False
    with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
        allowed_emails = [line.strip() for line in f if line.strip()]
    if len(allowed_emails) == 0:
        return False
    return session.get("email") == allowed_emails[0]

# ─────────────── 홈 ───────────────
@app.route("/")
def home():
    return redirect(url_for("login"))

# ─────────────── 통합 로그인 ───────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()

        # 이메일 형식 검사
        if "@" not in email or "." not in email:
            flash("⚠️ 유효한 이메일 주소를 입력하세요.")
            return redirect(url_for("login"))

        # 교수 이메일 목록 읽기
        professors = []
        if os.path.exists(ALLOWED_EMAILS):
            with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
                professors = [line.strip() for line in f if line.strip()]

        session["email"] = email
        flash("✅ 로그인 성공했습니다.")

        # 첫 번째 교수 이메일이면 업로드 권한 부여
        if len(professors) > 0 and email == professors[0]:
            session["role"] = "professor"
            return redirect(url_for("upload_lecture"))
        else:
            session["role"] = "student"
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

    # 교수만 접근 가능
    if not is_professor():
        flash("⚠️ 교수님만 접근할 수 있습니다.")
        return redirect(url_for("lecture"))

    df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date"])

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        date = datetime.now().strftime("%Y-%m-%d %H:%M")

        files = []
        for file in request.files.getlist("files"):
            if file and file.filename:
                filename = secure_filename(file.filename)
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(save_path)
                files.append(filename)

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

# ─────────────── 학습 사이트(Q&A) ───────────────
@app.route("/lecture", methods=["GET", "POST"])
def lecture():
    q_df = load_csv(DATA_QUESTIONS, ["id", "email", "title", "content", "date"])
    c_df = load_csv(DATA_COMMENTS, ["question_id", "email", "comment", "date"])
    l_df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date"])  # ✅ 추가

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
        questions=q_df.to_dict("records"),
        comments=c_df.to_dict("records"),
        lectures=l_df.to_dict("records"),  # ✅ 추가
        is_prof=(session.get("email") in open(ALLOWED_EMAILS, encoding="utf-8").read())
    )



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

# ─────────────── 질문/댓글 삭제 (교수 전용) ───────────────
@app.route("/delete_question/<int:question_id>")
def delete_question(question_id):
    if not is_professor():
        flash("⚠️ 교수님만 삭제할 수 있습니다.")
        return redirect(url_for("lecture"))

    q_df = load_csv(DATA_QUESTIONS, ["id", "email", "title", "content", "date"])
    c_df = load_csv(DATA_COMMENTS, ["question_id", "email", "comment", "date"])

    q_df = q_df[q_df["id"] != question_id]
    c_df = c_df[c_df["question_id"] != question_id]

    save_csv(DATA_QUESTIONS, q_df)
    save_csv(DATA_COMMENTS, c_df)
    flash("🗑️ 질문과 관련 댓글이 모두 삭제되었습니다.")
    return redirect(url_for("lecture"))

@app.route("/delete_comment/<int:comment_index>")
def delete_comment(comment_index):
    if not is_professor():
        flash("⚠️ 교수님만 삭제할 수 있습니다.")
        return redirect(url_for("lecture"))

    c_df = load_csv(DATA_COMMENTS, ["question_id", "email", "comment", "date"])
    if comment_index < len(c_df):
        c_df = c_df.drop(index=comment_index)
        save_csv(DATA_COMMENTS, c_df)
        flash("💬 댓글이 삭제되었습니다.")
    return redirect(url_for("lecture"))

# ─────────────── 파일 다운로드 ───────────────
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ─────────────── 캐시 무효화 ───────────────
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == "__main__":
    app.run(debug=True)



