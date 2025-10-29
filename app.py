# -*- coding: utf-8 -*-
"""
📘 연암공대 화트25 학습사이트 (강의자료 + Q&A 통합 완전판)
작성자: Key 교수님
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import pandas as pd
import os, re
from datetime import datetime

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
            return pd.read_csv(path)
        except:
            pass
    return pd.DataFrame(columns=cols)

def save_csv(path, df):
    df.to_csv(path, index=False, encoding="utf-8-sig")

# ─────────────── 파일명 정제 (한글 유지 + 특수문자 제거) ───────────────
def clean_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name)

# ─────────────── 홈(로그인) ───────────────
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        email = request.form.get("email").strip().lower()
        if not os.path.exists(ALLOWED_EMAILS):
            flash("allowed_emails.txt 파일이 없습니다.")
            return render_template("home.html")

        with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
            allowed = [line.strip().lower() for line in f if line.strip()]

        if email not in allowed:
            flash("등록되지 않은 이메일입니다.")
            return render_template("home.html")

        session["email"] = email
        session["role"] = "professor" if email == allowed[0] else "student"
        return redirect(url_for("lecture"))

    return render_template("home.html")

# ─────────────── 학습 사이트 (강의자료 + Q&A) ───────────────
@app.route("/lecture")
def lecture():
    if "email" not in session:
        return redirect(url_for("home"))

    lectures = load_csv(DATA_LECTURE, ["title", "content", "file_name", "site_links", "uploaded_at"])
    questions = load_csv(DATA_QUESTIONS, ["id", "email", "title", "content", "created_at"])
    comments = load_csv(DATA_COMMENTS, ["cid", "qid", "email", "content", "created_at"])

    if not lectures.empty:
        lectures = lectures.sort_values(by="uploaded_at", ascending=False).reset_index(drop=True)

    return render_template("lecture.html",
                           lectures=lectures.to_dict(orient="records"),
                           questions=questions.to_dict(orient="records"),
                           comments=comments.to_dict(orient="records"),
                           role=session.get("role"),
                           email=session.get("email"))

# ─────────────── 교수 업로드 ───────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    if "role" not in session or session["role"] != "professor":
        flash("교수 전용 페이지입니다.")
        return redirect(url_for("lecture"))

    df = load_csv(DATA_LECTURE, ["title", "content", "file_name", "site_links", "uploaded_at"])

    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        site_links = "; ".join(request.form.getlist("site_link"))

        uploaded_files = request.files.getlist("files")
        saved_files = []

        for file in uploaded_files:
            if file and file.filename:
                filename = clean_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                saved_files.append(filename)

        new_row = {
            "title": title,
            "content": content,
            "file_name": ", ".join(saved_files),
            "site_links": site_links,
            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_csv(DATA_LECTURE, df)
        flash("📘 강의자료가 업로드되었습니다.")
        return redirect(url_for("upload_lecture"))

    return render_template("upload_lecture.html")

# ─────────────── 강의자료 삭제 ───────────────
@app.route("/delete_lecture/<int:index>", methods=["POST"])
def delete_lecture(index):
    df = load_csv(DATA_LECTURE, ["title", "content", "file_name", "site_links", "uploaded_at"])
    if not df.empty and 0 <= index < len(df):
        df = df.drop(index).reset_index(drop=True)
        save_csv(DATA_LECTURE, df)
        flash("🗑️ 자료가 삭제되었습니다.")
    return redirect(url_for("lecture"))

# ─────────────── 질문 및 댓글 기능 ───────────────
@app.route("/add_question", methods=["POST"])
def add_question():
    if "email" not in session:
        return redirect(url_for("home"))
    df = load_csv(DATA_QUESTIONS, ["id", "email", "title", "content", "created_at"])
    new_row = {
        "id": len(df) + 1,
        "email": session["email"],
        "title": request.form.get("title"),
        "content": request.form.get("content"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_csv(DATA_QUESTIONS, df)
    flash("✅ 질문이 등록되었습니다.")
    return redirect(url_for("lecture"))

@app.route("/delete_question/<int:qid>", methods=["POST"])
def delete_question(qid):
    df = load_csv(DATA_QUESTIONS, ["id", "email", "title", "content", "created_at"])
    target = df[df["id"] == qid].iloc[0]
    if session["role"] == "professor" or target["email"] == session["email"]:
        df = df[df["id"] != qid]
        save_csv(DATA_QUESTIONS, df)
        flash("🗑️ 질문이 삭제되었습니다.")
    else:
        flash("⚠️ 본인 질문만 삭제할 수 있습니다.")
    return redirect(url_for("lecture"))

@app.route("/add_comment/<int:qid>", methods=["POST"])
def add_comment(qid):
    df = load_csv(DATA_COMMENTS, ["cid", "qid", "email", "content", "created_at"])
    new_row = {
        "cid": len(df) + 1,
        "qid": qid,
        "email": session["email"],
        "content": request.form.get("content"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_csv(DATA_COMMENTS, df)
    flash("💬 댓글이 등록되었습니다.")
    return redirect(url_for("lecture"))

@app.route("/delete_comment/<int:cid>", methods=["POST"])
def delete_comment(cid):
    df = load_csv(DATA_COMMENTS, ["cid", "qid", "email", "content", "created_at"])
    target = df[df["cid"] == cid].iloc[0]
    if session["role"] == "professor" or target["email"] == session["email"]:
        df = df[df["cid"] != cid]
        save_csv(DATA_COMMENTS, df)
        flash("🗑️ 댓글이 삭제되었습니다.")
    else:
        flash("⚠️ 본인 댓글만 삭제할 수 있습니다.")
    return redirect(url_for("lecture"))

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)

