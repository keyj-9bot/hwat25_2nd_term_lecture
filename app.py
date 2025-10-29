
# -*- coding: utf-8 -*-
"""
📘 연암공대 화공트랙 강의자료 업로드 시스템 (질문 수정·삭제 + 교수 로그인 보강 완전판)
작성자: Key 교수님
"""

from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "key_flask_secret"

# ─────────────────────────────
# 📂 CSV 파일 경로
# ─────────────────────────────
DATA_LECTURE = "lecture_data.csv"
DATA_QUESTIONS = "questions.csv"
DATA_COMMENTS = "comments.csv"

# ─────────────────────────────
# 📂 CSV 로드 / 저장 함수
# ─────────────────────────────
def load_csv(path, cols):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception as e:
            print(f"⚠️ CSV 로드 오류 ({path}): {e}")
    return pd.DataFrame(columns=cols)


def save_csv(path, df):
    df.to_csv(path, index=False, encoding="utf-8-sig")


# ─────────────────────────────
# 🏠 홈
# ─────────────────────────────
@app.route("/")
def home():
    return redirect(url_for("lecture"))


# ─────────────────────────────
# 📘 강의자료 및 Q&A
# ─────────────────────────────
@app.route("/lecture", methods=["GET"])
def lecture():
    lectures = load_csv(DATA_LECTURE, ["title", "content", "file_link", "site_link", "uploaded_at"])
    questions = load_csv(DATA_QUESTIONS, ["id", "email", "title", "content", "password", "created_at"])
    comments = load_csv(DATA_COMMENTS, ["cid", "qid", "email", "comment", "password", "created_at"])

    return render_template(
        "lecture.html",
        lectures=lectures.to_dict(orient="records"),
        questions=questions.to_dict(orient="records"),
        comments=comments.to_dict(orient="records"),
    )


# ─────────────────────────────
# 💬 질문 등록
# ─────────────────────────────
@app.route("/add_question", methods=["POST"])
def add_question():
    title = request.form.get("title")
    content = request.form.get("content")
    password = request.form.get("password")

    if len(password) < 4:
        return "❌ 비밀번호는 최소 4자리 이상이어야 합니다", 400

    df = load_csv(DATA_QUESTIONS, ["id", "email", "title", "content", "password", "created_at"])
    new_id = len(df) + 1
    new_row = {
        "id": new_id,
        "email": session.get("email", ""),
        "title": title,
        "content": content,
        "password": password,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_csv(DATA_QUESTIONS, df)
    return redirect(url_for("lecture"))


# ─────────────────────────────
# ✏️ 질문 수정 (GET/POST)
# ─────────────────────────────
@app.route("/edit_question/<int:qid>", methods=["POST", "GET"])
def edit_question(qid):
    df = load_csv(DATA_QUESTIONS, ["id", "email", "title", "content", "password", "created_at"])
    q = df[df["id"] == qid].iloc[0]

    if request.method == "GET":
        # 수정 페이지 렌더링
        return render_template("edit_question.html", question=q)

    # POST 요청 — 수정 처리
    password = request.form.get("password")
    if password != str(q["password"]):
        return "❌ 비밀번호가 일치하지 않습니다", 403

    new_title = request.form.get("title")
    new_content = request.form.get("content")
    df.loc[df["id"] == qid, ["title", "content"]] = [new_title, new_content]
    save_csv(DATA_QUESTIONS, df)

    return redirect(url_for("lecture"))


# ─────────────────────────────
# 🗑️ 질문 삭제
# ─────────────────────────────
@app.route("/delete_question/<int:qid>", methods=["POST"])
def delete_question(qid):
    df = load_csv(DATA_QUESTIONS, ["id", "email", "title", "content", "password", "created_at"])
    password = request.form.get("password")
    q = df[df["id"] == qid].iloc[0]
    if password != str(q["password"]):
        return "❌ 비밀번호가 일치하지 않습니다", 403

    df = df[df["id"] != qid]
    save_csv(DATA_QUESTIONS, df)
    return redirect(url_for("lecture"))


# ─────────────────────────────
# 💭 댓글 추가 / 삭제
# ─────────────────────────────
@app.route("/add_comment/<int:qid>", methods=["POST"])
def add_comment(qid):
    df = load_csv(DATA_COMMENTS, ["cid", "qid", "email", "comment", "password", "created_at"])
    new_cid = len(df) + 1
    comment = request.form.get("content")
    password = request.form.get("password")

    new_row = {
        "cid": new_cid,
        "qid": qid,
        "email": session.get("email", ""),
        "comment": comment,
        "password": password,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_csv(DATA_COMMENTS, df)
    return redirect(url_for("lecture"))


@app.route("/delete_comment/<int:cid>", methods=["POST"])
def delete_comment(cid):
    df = load_csv(DATA_COMMENTS, ["cid", "qid", "email", "comment", "password", "created_at"])
    password = request.form.get("password")
    c = df[df["cid"] == cid].iloc[0]
    if password != str(c["password"]):
        return "❌ 비밀번호가 일치하지 않습니다", 403

    df = df[df["cid"] != cid]
    save_csv(DATA_COMMENTS, df)
    return redirect(url_for("lecture"))


# ─────────────────────────────
# 👨‍🏫 교수 로그인 / 로그아웃 / 업로드
# ─────────────────────────────
@app.route("/login_prof", methods=["GET", "POST"])
def login_prof():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()

        if username == "professor" and password == "key1234":
            session["prof"] = username
            return redirect(url_for("upload_lecture"))
        else:
            error = "아이디 또는 비밀번호가 올바르지 않습니다."
            return render_template("login_prof.html", error=error)

    return render_template("login_prof.html")


@app.route("/logout_prof")
def logout_prof():
    session.pop("prof", None)
    return redirect(url_for("login_prof"))


@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    if "prof" not in session:
        return redirect(url_for("login_prof"))

    df = load_csv(DATA_LECTURE, ["title", "content", "file_link", "site_link", "uploaded_at"])
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        file_link = request.form.get("file_link")
        site_link = request.form.get("site_link")

        new_row = {
            "title": title,
            "content": content,
            "file_link": file_link,
            "site_link": site_link,
            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
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
# ✅ Render 헬스체크
# ─────────────────────────────
@app.route("/health")
def health():
    return "OK", 200


# ─────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)

