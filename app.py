# -*- coding: utf-8 -*-
"""
📘 연암공대 화공트랙 강의자료 + 로그인 + Q&A + 업로드 시스템 (교수 첫줄 이메일 자동인식 버전)
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
import pandas as pd
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "key_flask_secret")

# ─────────────────────────────
# 📁 절대경로 지정
# ─────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "lecture_data.csv")
QNA_FILE = os.path.join(BASE_DIR, "lecture_qna.csv")
ALLOWED_EMAILS_FILE = os.path.join(BASE_DIR, "allowed_emails.txt")

# ✅ Render Health Check
@app.route("/health")
def health_check():
    return "OK", 200


# ─────────────────────────────
# 🔐 로그인
# ─────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if not os.path.exists(ALLOWED_EMAILS_FILE):
        return "⚠️ allowed_emails.txt 파일이 서버에 없습니다.", 500

    # 허용 이메일 목록 불러오기
    with open(ALLOWED_EMAILS_FILE, "r", encoding="utf-8-sig") as f:
        allowed_emails = [line.strip().lower() for line in f if line.strip()]

    # ✅ 첫 번째 이메일 = 교수 계정
    professor_email = allowed_emails[0] if allowed_emails else None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if email in allowed_emails:
            session["user"] = email
            session["is_professor"] = (email == professor_email)
            return redirect(url_for("lecture"))
        else:
            flash("❌ 허용되지 않은 이메일입니다.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("is_professor", None)
    flash("👋 로그아웃되었습니다.", "info")
    return redirect(url_for("login"))


# ─────────────────────────────
# 🚧 로그인 보호
# ─────────────────────────────
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            flash("로그인이 필요합니다.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# ─────────────────────────────
# 📘 강의자료 + Q&A
# ─────────────────────────────
@app.route("/lecture", methods=["GET", "POST"])
@login_required
def lecture():
    data = []
    if os.path.exists(DATA_FILE):
        data = pd.read_csv(DATA_FILE, dtype=str).fillna("").to_dict("records")

    qna = []
    if os.path.exists(QNA_FILE):
        qna = pd.read_csv(QNA_FILE, dtype=str).fillna("").to_dict("records")

    if request.method == "POST":
        action = request.form.get("action")

        # 🟢 질문 등록
        if action == "add_qna":
            name = request.form.get("name", "익명")
            question = request.form.get("question", "")
            password = request.form.get("password", "")
            if not question or not password:
                flash("질문 내용과 비밀번호를 입력하세요.", "warning")
            else:
                qna.append({
                    "이름": name,
                    "질문": question,
                    "비밀번호": password,
                    "등록시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                pd.DataFrame(qna).to_csv(QNA_FILE, index=False, encoding="utf-8-sig")
                flash("✅ 질문이 등록되었습니다.", "success")

        # 🔴 질문 삭제
        elif action == "delete_qna":
            try:
                index_str = request.form.get("index", "")
                if not index_str.isdigit():
                    flash("⚠️ 삭제 항목 인덱스가 올바르지 않습니다.", "danger")
                    return redirect(url_for("lecture"))

                index = int(index_str)
                password = request.form.get("password", "")
                if 0 <= index < len(qna):
                    if qna[index]["비밀번호"] == password or password == "5555":
                        del qna[index]
                        pd.DataFrame(qna).to_csv(QNA_FILE, index=False, encoding="utf-8-sig")
                        flash("🗑️ 질문이 삭제되었습니다.", "info")
                    else:
                        flash("❌ 비밀번호가 일치하지 않습니다.", "danger")
                else:
                    flash("❌ 해당 질문을 찾을 수 없습니다.", "danger")
            except Exception as e:
                flash(f"⚠️ 삭제 중 오류 발생: {e}", "danger")

        return redirect(url_for("lecture"))

    return render_template("lecture.html", data=data, qna=qna)


# ─────────────────────────────
# 📤 교수 전용 업로드
# ─────────────────────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
@login_required
def upload_lecture():
    # ✅ 첫 줄 이메일(교수)만 접근 가능
    if not session.get("is_professor", False):
        flash("📛 업로드 권한이 없습니다.", "danger")
        return redirect(url_for("lecture"))

    data = []
    if os.path.exists(DATA_FILE):
        data = pd.read_csv(DATA_FILE, dtype=str).fillna("").to_dict("records")

    edit_index = request.args.get("edit")
    edit_data = None
    if edit_index and edit_index.isdigit():
        idx = int(edit_index)
        if 0 <= idx < len(data):
            edit_data = data[idx]

    if request.method == "POST":
        delete_index = request.form.get("delete_row")
        if delete_index:
            try:
                idx = int(delete_index)
                del data[idx]
                pd.DataFrame(data).to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
                flash("🗑️ 자료가 삭제되었습니다.", "info")
            except Exception as e:
                flash(f"삭제 오류: {e}", "danger")
            return redirect(url_for("upload_lecture"))

        topic = request.form.get("topic", "")
        notes = request.form.get("notes", "")
        sites = request.form.getlist("related_site")
        sites_str = ";".join([s.strip() for s in sites if s.strip()])
        upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        files = request.files.getlist("file_upload")
        upload_dir = os.path.join(BASE_DIR, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        file_urls = []
        for f in files:
            if f and f.filename:
                save_path = os.path.join(upload_dir, f.filename)
                f.save(save_path)
                file_urls.append(f"/uploads/{f.filename}")
        file_str = ";".join(file_urls) if file_urls else "-"

        new_entry = {
            "내용(Topic)": topic,
            "자료파일(File URL)": file_str,
            "연관사이트(Related Site)": sites_str or "-",
            "비고(Notes)": notes,
            "업로드시각": upload_time,
        }

        if "edit_index" in request.form:
            idx = int(request.form.get("edit_index"))
            data[idx] = new_entry
            flash("✏️ 수정되었습니다.", "success")
        else:
            data.append(new_entry)
            flash("📤 새 강의자료가 업로드되었습니다.", "success")

        pd.DataFrame(data).to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
        return redirect(url_for("upload_lecture"))

    return render_template("upload_lecture.html", data=data, edit_data=edit_data)


# ✅ 홈 리디렉션
@app.route("/")
def home():
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)

