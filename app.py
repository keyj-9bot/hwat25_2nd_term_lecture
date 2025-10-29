# -*- coding: utf-8 -*-
"""
📘 연암공대 화트25 학습지원시스템 (세션 안정형 Final Stable + Q&A 완전판)
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
    try:
        if os.path.exists(path):
            df = pd.read_csv(path)
            missing_cols = [c for c in cols if c not in df.columns]
            for col in missing_cols:
                df[col] = ""
            return df[cols]
    except Exception as e:
        print(f"[CSV Load Error] {path}: {e}")
    return pd.DataFrame(columns=cols)

def save_csv(path, df):
    try:
        df.to_csv(path, index=False, encoding="utf-8-sig")
    except Exception as e:
        print(f"[CSV Save Error] {path}: {e}")

# ───────────── 기본 라우트 ─────────────
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

        allowed = []
        if os.path.exists(ALLOWED_EMAILS):
            with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
                allowed = [e.strip() for e in f.readlines() if e.strip()]

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

    allowed = []
    if os.path.exists(ALLOWED_EMAILS):
        with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
            allowed = [e.strip() for e in f.readlines() if e.strip()]

    if not allowed or email != allowed[0]:
        flash("접근 권한이 없습니다.", "danger")
        return redirect(url_for("home"))

    df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date"])
    if request.method == "POST":
        title = request.form["title"].strip()
        content = request.form["content"].strip()
        links = "; ".join([v for k, v in request.form.items() if k.startswith("link") and v.strip()])
        filenames = []

        if "files" in request.files:
            files = request.files.getlist("files")
            for file in files:
                if file and file.filename:
                    # ⚙️ secure_filename + 한글 파일명 유지
                    original_name = file.filename
                    safe_name = secure_filename(original_name)
                    save_path = os.path.join(UPLOAD_FOLDER, safe_name)
                    file.save(save_path)
                    filenames.append(original_name)

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

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    # 경로 문제 방지
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except FileNotFoundError:
        flash("파일을 찾을 수 없습니다.", "danger")
        return redirect(url_for("lecture"))

# ───────────── 학습 사이트 (강의자료 + Q&A) ─────────────
@app.route("/lecture", methods=["GET", "POST"])
def lecture():
    email = session.get("email")
    if not email:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for("login"))

    df_lecture = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date"])
    df_questions = load_csv(DATA_QUESTIONS, ["id", "title", "content", "email", "date"])
    df_comments = load_csv(DATA_COMMENTS, ["question_id", "comment", "email"])

    # 15일 지난 강의자료 자동삭제
    today = datetime.now()
    valid_rows = []
    for _, row in df_lecture.iterrows():
        try:
            d = datetime.strptime(str(row["date"]), "%Y-%m-%d %H:%M")
            if (today - d).days <= 15:
                valid_rows.append(row)
        except:
            continue
    df_lecture = pd.DataFrame(valid_rows, columns=["title", "content", "files", "links", "date"])
    save_csv(DATA_LECTURE, df_lecture)

    # 질문 등록
    if request.method == "POST" and "title" in request.form:
        new_id = len(df_questions) + 1
        new_q = {
            "id": new_id,
            "title": request.form["title"].strip(),
            "content": request.form["content"].strip(),
            "email": email,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        df_questions = pd.concat([df_questions, pd.DataFrame([new_q])], ignore_index=True)
        save_csv(DATA_QUESTIONS, df_questions)
        flash("질문이 등록되었습니다.", "success")
        return redirect(url_for("lecture"))

    return render_template(
        "lecture.html",
        lectures=df_lecture.to_dict("records"),
        questions=df_questions.to_dict("records"),
        comments=df_comments.to_dict("records"),
        user_email=email,
    )

# 💬 댓글 등록
@app.route("/add_comment/<int:question_id>", methods=["POST"])
def add_comment(question_id):
    email = session.get("email")
    if not email:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for("login"))

    comment = request.form["comment"].strip()
    if comment:
        df = load_csv(DATA_COMMENTS, ["question_id", "comment", "email"])
        df = pd.concat(
            [df, pd.DataFrame([{"question_id": question_id, "comment": comment, "email": email}])],
            ignore_index=True,
        )
        save_csv(DATA_COMMENTS, df)
        flash("댓글이 등록되었습니다.", "success")
    return redirect(url_for("lecture"))

# ❌ 질문 삭제
@app.route("/delete_question/<int:q_id>", methods=["POST"])
def delete_question(q_id):
    email = session.get("email")
    df = load_csv(DATA_QUESTIONS, ["id", "title", "content", "email", "date"])
    df = df[~((df["id"] == q_id) & (df["email"] == email))]
    save_csv(DATA_QUESTIONS, df)
    flash("질문이 삭제되었습니다.", "info")
    return redirect(url_for("lecture"))

# ❌ 댓글 삭제
@app.route("/delete_comment/<int:q_id>/<int:c_idx>", methods=["POST"])
def delete_comment(q_id, c_idx):
    email = session.get("email")
    df = load_csv(DATA_COMMENTS, ["question_id", "comment", "email"])
    df = df.drop(df[(df.index == c_idx) & (df["question_id"] == q_id) & (df["email"] == email)].index)
    save_csv(DATA_COMMENTS, df)
    flash("댓글이 삭제되었습니다.", "info")
    return redirect(url_for("lecture"))

# ───────────── Health Check (Render 배포 안정화용) ─────────────
@app.route("/health")
def health():
    return "OK", 200



# ───────────── 앱 실행 ─────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
