# -*- coding: utf-8 -*-
"""
📘 연암공대 화공트랙 강의자료 업로드 시스템 (교수 자동 인식 + 관리자 삭제 + 비번 4자리 제한 완전판)
작성자: Key 교수님
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
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
ALLOWED_EMAILS_FILE = "allowed_emails.txt"

# ─────────────────────────────
# 📂 CSV 로드 / 저장
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
# 📧 허용 이메일 로드
# ─────────────────────────────
def get_allowed_emails():
    """허용된 이메일 목록 로드"""
    try:
        with open(ALLOWED_EMAILS_FILE, "r", encoding="utf-8") as f:
            emails = [line.strip() for line in f.readlines() if line.strip()]
        return emails
    except Exception as e:
        print(f"⚠️ allowed_emails.txt 읽기 오류: {e}")
        return []


# ─────────────────────────────
# 🏠 홈
# ─────────────────────────────
@app.route("/")
def home():
    return redirect(url_for("lecture"))


# ─────────────────────────────
# 🔐 이메일 로그인 (교수 자동 인식)
# ─────────────────────────────
@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip()
    allowed_emails = get_allowed_emails()

    if email not in allowed_emails:
        flash("❌ 등록되지 않은 이메일입니다.")
        return redirect(url_for("home"))

    # ✅ 첫 번째 이메일 = 교수 계정
    if email == allowed_emails[0]:
        session["prof"] = True
        session["email"] = email
        flash("👨‍🏫 교수 계정으로 로그인되었습니다.")
        return redirect(url_for("upload_lecture"))
    else:
        session["prof"] = False
        session["email"] = email
        flash("✅ 학생 계정으로 로그인되었습니다.")
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
# 💬 질문 등록 (비밀번호 4자리 제한)
# ─────────────────────────────
@app.route("/add_question", methods=["POST"])
def add_question():
    title = request.form.get("title")
    content = request.form.get("content")
    password = request.form.get("password", "").strip()

    # ✅ 비밀번호는 정확히 숫자 4자리만 허용
    if not password.isdigit() or len(password) != 4:
        flash("❌ 비번을 4자리로 입력하세요.")
        return redirect(url_for("lecture"))

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
    flash("✅ 질문이 등록되었습니다.")
    return redirect(url_for("lecture"))


# ─────────────────────────────
# 🗑️ 질문 삭제 (교수는 비밀번호 생략)
# ─────────────────────────────
@app.route("/delete_question/<int:qid>", methods=["POST"])
def delete_question(qid):
    df = load_csv(DATA_QUESTIONS, ["id", "email", "title", "content", "password", "created_at"])
    q = df[df["id"] == qid].iloc[0]

    if not session.get("prof"):  # 학생일 경우
        password = request.form.get("password", "")
        if password != str(q["password"]):
            flash("⚠️ 등록 시 저장한 비번을 입력하세요.")
            return redirect(url_for("lecture"))

    df = df[df["id"] != qid]
    save_csv(DATA_QUESTIONS, df)
    flash("🗑️ 질문이 삭제되었습니다.")
    return redirect(url_for("lecture"))


# ─────────────────────────────
# 💭 댓글 추가 / 삭제 (교수는 비밀번호 생략)
# ─────────────────────────────
@app.route("/add_comment/<int:qid>", methods=["POST"])
def add_comment(qid):
    df = load_csv(DATA_COMMENTS, ["cid", "qid", "email", "comment", "password", "created_at"])
    new_cid = len(df) + 1
    comment = request.form.get("content")
    password = request.form.get("password", "").strip()

    if not password.isdigit() or len(password) != 4:
        flash("❌ 댓글 비번은 4자리 숫자여야 합니다.")
        return redirect(url_for("lecture"))

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
    flash("💬 댓글이 등록되었습니다.")
    return redirect(url_for("lecture"))


@app.route("/delete_comment/<int:cid>", methods=["POST"])
def delete_comment(cid):
    df = load_csv(DATA_COMMENTS, ["cid", "qid", "email", "comment", "password", "created_at"])
    c = df[df["cid"] == cid].iloc[0]

    if not session.get("prof"):
        password = request.form.get("password", "")
        if password != str(c["password"]):
            flash("⚠️ 등록 시 저장한 비번을 입력하세요.")
            return redirect(url_for("lecture"))

    df = df[df["cid"] != cid]
    save_csv(DATA_COMMENTS, df)
    flash("💬 댓글이 삭제되었습니다.")
    return redirect(url_for("lecture"))


# ─────────────────────────────
# 👨‍🏫 교수 전용 강의자료 업로드
# ─────────────────────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    if not session.get("prof"):
        flash("🔒 교수 전용 페이지입니다.")
        return redirect(url_for("lecture"))

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
        flash("✅ 강의자료가 업로드되었습니다.")
        return redirect(url_for("upload_lecture"))

    return render_template("upload_lecture.html", lectures=df.to_dict(orient="records"))


@app.route("/delete_lecture", methods=["POST"])
def delete_lecture():
    if not session.get("prof"):
        return redirect(url_for("lecture"))
    title = request.form.get("title")
    df = load_csv(DATA_LECTURE, ["title", "content", "file_link", "site_link", "uploaded_at"])
    df = df[df["title"] != title]
    save_csv(DATA_LECTURE, df)
    flash("🗑️ 강의자료가 삭제되었습니다.")
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
