# -*- coding: utf-8 -*-
"""
📘 연암공대 화공트랙 강의자료 & Q&A 시스템 (수정·삭제 완전판)
작성자: Key 교수님
업데이트: 2025-10-29
"""

from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "key_flask_secret"

# ─────────────────────────────
# 📂 파일 경로
# ─────────────────────────────
DATA_LECTURE = "lecture_data.csv"
DATA_QA = "questions.csv"
DATA_COMMENT = "comments.csv"
ALLOWED_EMAILS = "allowed_emails.txt"

# ─────────────────────────────
# 🧭 CSV 로드 및 저장
# ─────────────────────────────
def load_csv(path, cols):
    try:
        if not os.path.exists(path) or os.stat(path).st_size == 0:
            return pd.DataFrame(columns=cols)
        df = pd.read_csv(path)
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        return df
    except Exception as e:
        print(f"⚠️ CSV 로드 오류 ({path}): {e}")
        return pd.DataFrame(columns=cols)

def save_csv(path, df):
    df.to_csv(path, index=False, encoding="utf-8-sig")

# ─────────────────────────────
# 🏠 메인 (이메일 로그인)
# ─────────────────────────────
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not os.path.exists(ALLOWED_EMAILS):
            return render_template("home.html", error="이메일 목록 파일이 없습니다.")
        with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
            allowed = [e.strip() for e in f.readlines()]
        if email in allowed:
            session["email"] = email
            return redirect(url_for("lecture"))
        else:
            return render_template("home.html", error="등록되지 않은 이메일입니다.")
    return render_template("home.html")

# ─────────────────────────────
# 👨‍🏫 교수 로그인
# ─────────────────────────────
@app.route("/login_prof", methods=["GET", "POST"])
def login_prof():
    if request.method == "POST":
        pw = request.form.get("password", "")
        if pw == "key1234":  # 교수용 비밀번호
            session["prof"] = True
            return redirect(url_for("upload_lecture"))
        return render_template("login_prof.html", error="비밀번호가 올바르지 않습니다.")
    return render_template("login_prof.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ─────────────────────────────
# 📚 강의자료 페이지
# ─────────────────────────────
@app.route("/lecture")
def lecture():
    if "email" not in session:
        return redirect(url_for("home"))
    lectures = load_csv(DATA_LECTURE, ["title", "content", "file_link", "site_link", "uploaded_at"])
    qas = load_csv(DATA_QA, ["id", "email", "question", "password", "created_at"])
    comments = load_csv(DATA_COMMENT, ["cid", "qid", "email", "comment", "password", "created_at"])
    return render_template("lecture.html",
                           email=session["email"],
                           lectures=lectures.to_dict(orient="records"),
                           qas=qas.to_dict(orient="records"),
                           comments=comments.to_dict(orient="records"))

# ─────────────────────────────
# 💬 Q&A 등록/수정/삭제
# ─────────────────────────────
@app.route("/add_question", methods=["POST"])
def add_question():
    email = request.form.get("email", "")
    question = request.form.get("question", "")
    password = request.form.get("password", "")
    if not email or not question or not password:
        return redirect(url_for("lecture"))
    df = load_csv(DATA_QA, ["id", "email", "question", "password", "created_at"])
    new = pd.DataFrame([{
        "id": len(df) + 1,
        "email": email,
        "question": question,
        "password": password,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }])
    df = pd.concat([df, new], ignore_index=True)
    save_csv(DATA_QA, df)
    return redirect(url_for("lecture"))

@app.route("/edit_question", methods=["POST"])
def edit_question():
    qid = int(request.form.get("qid"))
    password = request.form.get("password", "")
    new_text = request.form.get("new_text", "")
    df = load_csv(DATA_QA, ["id", "email", "question", "password", "created_at"])
    for i in range(len(df)):
        if df.loc[i, "id"] == qid and df.loc[i, "password"] == password:
            df.loc[i, "question"] = new_text
            save_csv(DATA_QA, df)
            return redirect(url_for("lecture"))
    return redirect(url_for("lecture"))

@app.route("/delete_question", methods=["POST"])
def delete_question():
    qid = int(request.form.get("qid"))
    password = request.form.get("password", "")
    df = load_csv(DATA_QA, ["id", "email", "question", "password", "created_at"])
    df = df[~((df["id"] == qid) & (df["password"] == password))]
    save_csv(DATA_QA, df)
    return redirect(url_for("lecture"))

# ─────────────────────────────
# 💭 댓글 등록/삭제
# ─────────────────────────────
@app.route("/add_comment", methods=["POST"])
def add_comment():
    qid = int(request.form.get("qid"))
    email = request.form.get("email", "")
    comment = request.form.get("comment", "")
    password = request.form.get("password", "")
    if not comment or not password:
        return redirect(url_for("lecture"))
    df = load_csv(DATA_COMMENT, ["cid", "qid", "email", "comment", "password", "created_at"])
    new = pd.DataFrame([{
        "cid": len(df) + 1,
        "qid": qid,
        "email": email,
        "comment": comment,
        "password": password,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }])
    df = pd.concat([df, new], ignore_index=True)
    save_csv(DATA_COMMENT, df)
    return redirect(url_for("lecture"))

@app.route("/delete_comment", methods=["POST"])
def delete_comment():
    cid = int(request.form.get("cid"))
    password = request.form.get("password", "")
    df = load_csv(DATA_COMMENT, ["cid", "qid", "email", "comment", "password", "created_at"])
    df = df[~((df["cid"] == cid) & (df["password"] == password))]
    save_csv(DATA_COMMENT, df)
    return redirect(url_for("lecture"))

# ─────────────────────────────
# 📤 교수 업로드 페이지 (비번 없이 수정/삭제 가능)
# ─────────────────────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    if "prof" not in session:
        return redirect(url_for("login_prof"))
    df = load_csv(DATA_LECTURE, ["title", "content", "file_link", "site_link", "uploaded_at"])

    if request.method == "POST":
        title = request.form.get("title", "")
        content = request.form.get("content", "")
        file_link = request.form.get("file_link", "")
        site_link = request.form.get("site_link", "")
        new = pd.DataFrame([{
            "title": title,
            "content": content,
            "file_link": file_link,
            "site_link": site_link,
            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }])
        df = pd.concat([df, new], ignore_index=True)
        save_csv(DATA_LECTURE, df)
        return redirect(url_for("upload_lecture"))

    return render_template("upload_lecture.html", lectures=df.to_dict(orient="records"))

@app.route("/delete_lecture", methods=["POST"])
def delete_lecture():
    if "prof" not in session:
        return redirect(url_for("login_prof"))
    title = request.form.get("title")
    df = load_csv(DATA_LECTURE, ["title", "content", "file_link", "site_link", "uploaded_at"])
    df = df[df["title"] != title]
    save_csv(DATA_LECTURE, df)
    return redirect(url_for("upload_lecture"))

# ─────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
