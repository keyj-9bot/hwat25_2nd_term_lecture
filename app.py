# -*- coding: utf-8 -*-
"""
📘 연암공대 화트25 강의자료 학습 & Q&A 시스템 (최종 완전판)
작성자: Key 교수님
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import pandas as pd
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "key_flask_secret"

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

# ─────────────── 파일 업로드 라우트 ───────────────
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ─────────────── 로그인 ───────────────
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        if not os.path.exists(ALLOWED_EMAILS):
            flash("허용 이메일 목록 파일이 없습니다.")
            return redirect(url_for("login"))

        with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
            allowed = [e.strip() for e in f.readlines() if e.strip()]

        if email in allowed:
            session["email"] = email
            flash("로그인 성공!")
            return redirect(url_for("home"))
        else:
            flash("학교에 등록된 이메일로 로그인하세요.")
    return render_template("login.html")

# ─────────────── 로그아웃 ───────────────
@app.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.")
    return redirect(url_for("login"))

# ─────────────── 홈 ───────────────
@app.route("/home")
def home():
    if "email" not in session:
        return redirect(url_for("login"))
    return render_template("home.html", email=session["email"])

# ─────────────── 교수 업로드 ───────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    if "email" not in session:
        return redirect(url_for("login"))
    email = session["email"]

    # 교수 이메일 (첫 줄)
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

        # 파일 처리
        uploaded_files = request.files.getlist("files")
        filenames = []
        for file in uploaded_files:
            if file and file.filename:
                fname = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, fname))
                filenames.append(fname)
        file_str = ";".join(filenames)

        # 링크 처리
        links = [v for k, v in request.form.items() if k.startswith("link") and v.strip()]
        link_str = ";".join(links)

        df.loc[len(df)] = [title, content, file_str, link_str, date, False]
        save_csv(DATA_LECTURE, df)
        flash("업로드 완료!")
        return redirect(url_for("upload_lecture"))

    df.fillna("", inplace=True)
    return render_template("upload_lecture.html", lectures=df.to_dict("records"))

# ─────────────── 강의자료 게시 ───────────────
@app.route("/confirm_lecture/<int:lec_id>", methods=["POST"])
def confirm_lecture(lec_id):
    df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date", "confirmed"])
    if lec_id < len(df):
        df.loc[lec_id, "confirmed"] = True
        save_csv(DATA_LECTURE, df)
        flash("강의자료가 게시되었습니다.")
    return redirect(url_for("upload_lecture"))

# ─────────────── 강의자료 삭제 ───────────────
@app.route("/delete_lecture/<int:lec_id>", methods=["POST"])
def delete_lecture(lec_id):
    df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date", "confirmed"])
    if lec_id < len(df):
        df.drop(index=lec_id, inplace=True)
        df.reset_index(drop=True, inplace=True)
        save_csv(DATA_LECTURE, df)
        flash("삭제되었습니다.")
    return redirect(url_for("upload_lecture"))

# ─────────────── 학습사이트(Q&A 포함) ───────────────
@app.route("/lecture", methods=["GET", "POST"])
def lecture():
    q_df = load_csv(DATA_QUESTIONS, ["id", "email", "title", "content", "date"])
    c_df = load_csv(DATA_COMMENTS, ["question_id", "email", "comment", "date"])
    l_df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date", "confirmed"])

    # ① 15일 지난 자료 자동 삭제
    now = datetime.now()
    try:
        l_df["date"] = pd.to_datetime(l_df["date"], errors="coerce")
        l_df = l_df[(now - l_df["date"]).dt.days <= 15]
    except:
        pass
    save_csv(DATA_LECTURE, l_df)

    # ② 게시 완료 자료만 표시
    if "confirmed" in l_df.columns:
        lectures = l_df[l_df["confirmed"] == True].to_dict("records")
    else:
        lectures = []

    # ③ 질문 등록
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

    return render_template("lecture.html",
                           lectures=lectures,
                           questions=q_df.to_dict("records"),
                           comments=c_df.to_dict("records"),
                           user_email=session.get("email"))

# ─────────────── 질문/댓글 삭제 ───────────────
@app.route("/delete_question/<int:q_id>", methods=["POST"])
def delete_question(q_id):
    email = session.get("email", "")
    df = load_csv(DATA_QUESTIONS, ["id", "email", "title", "content", "date"])
    if not df.empty:
        df = df[df["id"] != q_id] if email else df
        save_csv(DATA_QUESTIONS, df)
    flash("질문이 삭제되었습니다.")
    return redirect(url_for("lecture"))

@app.route("/delete_comment/<int:c_idx>/<int:q_id>", methods=["POST"])
def delete_comment(c_idx, q_id):
    email = session.get("email", "")
    df = load_csv(DATA_COMMENTS, ["question_id", "email", "comment", "date"])
    if not df.empty and c_idx < len(df) and df.loc[c_idx, "email"] == email:
        df.drop(index=c_idx, inplace=True)
        df.reset_index(drop=True, inplace=True)
        save_csv(DATA_COMMENTS, df)
        flash("댓글이 삭제되었습니다.")
    return redirect(url_for("lecture"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)



