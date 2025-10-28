
# -*- coding: utf-8 -*-
"""
📘 연암공대 화공트랙 강의자료 업로드 시스템 (교수 전용 접근제한 + 다중입력 지원 완성판)
작성자: Key 교수님
"""

from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "key_flask_secret"
DATA_FILE = "lecture_data.csv"


# ─────────────────────────────
# 📂 데이터 로드/저장
# ─────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            return df.to_dict(orient="records")
        except:
            return []
    return []


def save_data(data):
    df = pd.DataFrame(data)
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")


# ─────────────────────────────
# 🏠 홈/강의자료 페이지
# ─────────────────────────────
@app.route("/")
def home():
    data = load_data()
    return render_template("lecture.html", data=data)


@app.route("/lecture")
def lecture():
    data = load_data()
    return render_template("lecture.html", data=data)


# ─────────────────────────────
# 🔑 로그인 / 로그아웃
# ─────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # 간단한 교수 전용 로그인 예시 (필요 시 DB 또는 별도 파일 연동 가능)
        if username == "professor" and password == "keypass":
            session["user"] = username
            session["role"] = "professor"
            return redirect(url_for("upload_lecture"))
        else:
            return render_template("login.html", error="로그인 실패: 교수 계정만 접근 가능합니다.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ─────────────────────────────
# 📤 교수 전용 업로드 페이지
# ─────────────────────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    # 교수 전용 접근 제한
    if "user" not in session or session.get("role") != "professor":
        return redirect(url_for("login"))

    data = load_data()

    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        # 여러 입력값(자료파일, 연관사이트)을 모두 리스트로 받아 ';'로 연결
        file_urls = [x.strip() for x in request.form.getlist("file_url") if x.strip()]
        ref_sites = [x.strip() for x in request.form.getlist("ref_site") if x.strip()]
        notes = request.form.get("notes", "").strip()

        new_entry = {
            "번호": len(data) + 1,
            "내용": topic,
            "자료파일": "; ".join(file_urls),
            "연관사이트": "; ".join(ref_sites),
            "비고": notes,
            "업로드시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        data.append(new_entry)
        save_data(data)

        return redirect(url_for("upload_lecture"))

    return render_template("upload_lecture.html", data=data)


# ─────────────────────────────
# ✏️ 수정 / 삭제 기능
# ─────────────────────────────
@app.route("/edit/<int:index>", methods=["GET", "POST"])
def edit(index):
    if "user" not in session or session.get("role") != "professor":
        return redirect(url_for("login"))

    data = load_data()
    if index < 0 or index >= len(data):
        return redirect(url_for("upload_lecture"))

    if request.method == "POST":
        data[index]["내용"] = request.form.get("topic", "").strip()
        file_urls = [x.strip() for x in request.form.getlist("file_url") if x.strip()]
        ref_sites = [x.strip() for x in request.form.getlist("ref_site") if x.strip()]
        data[index]["자료파일"] = "; ".join(file_urls)
        data[index]["연관사이트"] = "; ".join(ref_sites)
        data[index]["비고"] = request.form.get("notes", "").strip()
        save_data(data)
        return redirect(url_for("upload_lecture"))

    return render_template("upload_lecture.html", data=data)


@app.route("/delete/<int:index>")
def delete(index):
    if "user" not in session or session.get("role") != "professor":
        return redirect(url_for("login"))

    data = load_data()
    if 0 <= index < len(data):
        del data[index]
        # 번호 재정렬
        for i, row in enumerate(data):
            row["번호"] = i + 1
        save_data(data)
    return redirect(url_for("upload_lecture"))


# ─────────────────────────────
# 🚀 실행
# ─────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

