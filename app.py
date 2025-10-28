

# -*- coding: utf-8 -*-
"""
📘 연암공대 화공트랙 강의자료 + 로그인 + Q&A + 교수 업로드 시스템 (Render 안정버전)
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

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if email in allowed_emails:
            session["user"] = email
            session["is_professor"] = (email == allowed_emails[0])  # 첫 번째 메일 = 교수
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
# 🚧 로그인 보호 데코레이터
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
# 📘 강의자료 + Q&A 페이지
# ─────────────────────────────
@app.route("/lecture", methods=["GET", "POST"])
@login_required
def lecture():
    # 강의자료 불러오기 (안전 처리)
    data = []
    if os.path.exists(DATA_FILE):
        try:
            if os.path.getsize(DATA_FILE) > 0:
                data = pd.read_csv(DATA_FILE, dtype=str).fillna("").to_dict("records")
        except Exception:
            data = []

    # Q&A 불러오기 (빈 파일 대비)
    qna = []
    if os.path.exists(QNA_FILE):
        try:
            if os.path.getsize(QNA_FILE) > 0:
                qna = pd.read_csv(QNA_FILE, dtype=str).fillna("").to_dict("records")
        except pd.errors.EmptyDataError:
            qna = []
        except Exception as e:
            print(f"[경고] QNA_FILE 로드 중 오류 발생: {e}")
            qna = []

    # POST 요청 처리 (질문 등록 / 삭제)
    if request.method == "POST":
        action = request.form.get("action")

        # 🟢 학생 질문 등록
        if action == "add_qna":
            name = request.form.get("name", "익명")
            question = request.form.get("question", "")
            password = request.form.get("password", "")
            if not question or not password:
                flash("질문 내용과 비밀번호를 입력하세요.", "warning")
            else:
                new_entry = {
                    "이름": name,
                    "질문": question,
                    "비밀번호": password,
                    "등록시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                qna.append(new_entry)
                pd.DataFrame(qna).to_csv(QNA_FILE, index=False, encoding="utf-8-sig")
                flash("✅ 질문이 등록되었습니다.", "success")

        # 🔴 학생 질문 삭제
        elif action == "delete_qna":
            try:
                index = int(request.form.get("index", -1))
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
                flash(f"⚠️ 삭제 처리 중 오류 발생: {e}", "danger")
                print(f"[오류] delete_qna 중 예외 발생 → {e}")

        # ✅ POST 처리 후 페이지 새로고침
        return redirect(url_for("lecture"))

    return render_template("lecture.html", data=data, qna=qna)


# ─────────────────────────────
# 🧑‍🏫 교수용 강의자료 업로드 페이지
# ─────────────────────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
@login_required
def upload_lecture():
    if not session.get("is_professor"):
        flash("⛔ 접근 권한이 없습니다. (교수 전용 페이지)", "danger")
        return redirect(url_for("lecture"))

    data = []
    if os.path.exists(DATA_FILE):
        try:
            if os.path.getsize(DATA_FILE) > 0:
                data = pd.read_csv(DATA_FILE, dtype=str).fillna("").to_dict("records")
        except Exception:
            data = []

    # 편집 데이터 선택
    edit_index = request.args.get("edit")
    edit_data = None
    if edit_index is not None and edit_index.isdigit():
        idx = int(edit_index)
        if 0 <= idx < len(data):
            edit_data = data[idx]

    # 업로드 및 수정 처리
    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        notes = request.form.get("notes", "").strip()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 여러 파일 및 사이트를 문자열로 병합
        files = ";".join([f for f in request.form.getlist("file_upload") if f.strip()])
        sites = ";".join([s for s in request.form.getlist("related_site") if s.strip()])

        new_entry = {
            "내용(Topic)": topic or "-",
            "자료파일(File URL)": files or "-",
            "연관사이트(Related Site)": sites or "-",
            "비고(Notes)": notes or "-",
            "업로드시각": now,
        }

        if "edit_index" in request.form:
            idx = int(request.form["edit_index"])
            if 0 <= idx < len(data):
                data[idx] = new_entry
                flash("✏️ 강의자료가 수정되었습니다.", "success")
        else:
            data.append(new_entry)
            flash("📤 새 강의자료가 업로드되었습니다.", "success")

        pd.DataFrame(data).to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
        return redirect(url_for("upload_lecture"))

    # 삭제 처리
    if request.method == "POST" and "delete_row" in request.form:
        idx = int(request.form["delete_row"])
        if 0 <= idx < len(data):
            del data[idx]
            pd.DataFrame(data).to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
            flash("🗑️ 강의자료가 삭제되었습니다.", "info")
        return redirect(url_for("upload_lecture"))

    return render_template("upload_lecture.html", data=data, edit_data=edit_data)


# ✅ 홈 리디렉션
@app.route("/")
def home():
    return redirect(url_for("login"))


# ─────────────────────────────
# 🔍 실행 정보 로그
# ─────────────────────────────
print("✅ Flask app loaded successfully, available routes:")
print([r.rule for r in app.url_map.iter_rules()])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
