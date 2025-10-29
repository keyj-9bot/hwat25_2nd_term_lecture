# -*- coding: utf-8 -*-
"""
📘 연암공대 화트25 강의자료 학습 & Q&A 시스템 (세션 완전 안정판)
작성자: Key 교수님
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import pandas as pd
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "key_flask_secret"

# ✅ Render HTTPS 세션 완전호환 설정
app.config.update(
    SESSION_COOKIE_SECURE=True,        # HTTPS에서도 유지
    SESSION_COOKIE_SAMESITE="None",    # 크로스도메인 허용
    SESSION_PERMANENT=True,            # 브라우저 닫혀도 일정 시간 유지
    PERMANENT_SESSION_LIFETIME=timedelta(hours=3)  # 3시간 유지
)

# ─────────────── 설정 ───────────────
DATA_LECTURE = "lecture_data.csv"
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


# ─────────────── 홈 (최상위 라우트 일원화) ───────────────
@app.route("/")
def root():
    # 세션이 있으면 바로 홈으로
    if "email" in session:
        return redirect(url_for("home"))
    return redirect(url_for("login"))


# ─────────────── 로그인 ───────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()

        if not os.path.exists(ALLOWED_EMAILS):
            flash("허용된 이메일 목록 파일이 없습니다.", "error")
            return redirect(url_for("login"))

        with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
            allowed = [line.strip() for line in f if line.strip()]

        if email in allowed:
            # ✅ 세션 생성
            session.clear()
            session["email"] = email
            session.permanent = True
            flash("로그인 성공!", "success")
            return redirect(url_for("home"))
        else:
            flash("학교에 등록된 이메일이 아닙니다.", "error")
            return redirect(url_for("login"))

    # 이미 로그인 상태라면 홈으로 보내기
    if "email" in session:
        return redirect(url_for("home"))
    return render_template("login.html")


# ─────────────── 로그아웃 ───────────────
@app.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.", "info")
    return redirect(url_for("login"))


# ─────────────── 홈 ───────────────
@app.route("/home")
def home():
    if "email" not in session:
        flash("세션이 만료되었습니다. 다시 로그인하세요.", "error")
        return redirect(url_for("login"))
    return render_template("home.html", email=session["email"])


# ─────────────── 교수 업로드 ───────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
        allowed = [line.strip() for line in f if line.strip()]
    professor_email = allowed[0] if allowed else None

    if email != professor_email:
        flash("교수만 접근할 수 있습니다.", "error")
        return redirect(url_for("home"))

    df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date", "confirmed"])

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        date = datetime.now().strftime("%Y-%m-%d %H:%M")

        uploaded_files = request.files.getlist("files")
        filenames = []
        for file in uploaded_files:
            if file and file.filename:
                fname = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, fname))
                filenames.append(fname)
        file_str = ";".join(filenames)

        links = [v for k, v in request.form.items() if k.startswith("link") and v.strip()]
        link_str = ";".join(links)

        df.loc[len(df)] = [title, content, file_str, link_str, date, True]
        save_csv(DATA_LECTURE, df)
        flash("강의자료가 게시되었습니다.", "success")
        return redirect(url_for("upload_lecture"))

    df.fillna("", inplace=True)
    return render_template("upload_lecture.html", lectures=df.to_dict("records"))


# ─────────────── 파일 보기 ───────────────
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ─────────────── 실행 ───────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)


