# -*- coding: utf-8 -*-
"""
📘 연암공대 화공트랙 강의자료 + Q&A + 로그인 시스템 (allowed_emails.txt 기반)
- 학생/교수: allowed_emails.txt 내 이메일이면 로그인 가능
- 로그인하지 않으면 내부 페이지 접근 불가
- 세션 기반 로그인 (Render 호환)
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
import pandas as pd
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "key_flask_secret")

# ─────────────────────────────
# 📁 파일 경로
# ─────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "lecture_data.csv")
QNA_FILE = os.path.join(BASE_DIR, "lecture_qna.csv")
ALLOWED_EMAILS_FILE = os.path.join(BASE_DIR, "allowed_emails.txt")
PROFESSOR_PASSWORD = os.getenv("PROFESSOR_PASSWORD", "5555")

# ✅ Render Health Check용
@app.route("/health")
def health_check():
    return "OK", 200


# ─────────────────────────────
# 📂 파일 로드/저장
# ─────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            return pd.read_csv(DATA_FILE, dtype=str).fillna("").to_dict("records")
        except Exception:
            return []
    return []

def save_data(data):
    pd.DataFrame(data).to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

def load_qna():
    if not os.path.exists(QNA_FILE):
        pd.DataFrame(columns=["이름", "질문", "답변", "비밀번호", "등록시각"]).to_csv(
            QNA_FILE, index=False, encoding="utf-8-sig"
        )
    return pd.read_csv(QNA_FILE, dtype=str).fillna("")

def save_qna(df):
    df.to_csv(QNA_FILE, index=False, encoding="utf-8-sig")

def load_allowed_emails():
    """허용된 이메일 목록을 읽음 (Render 절대경로 호환)"""
    if os.path.exists(ALLOWED_EMAILS_FILE):
        with open(ALLOWED_EMAILS_FILE, "r", encoding="utf-8") as f:
            return [line.strip().lower() for line in f if line.strip()]
    return []


# ─────────────────────────────
# 🔐 로그인 시스템
# ─────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("로그인이 필요합니다.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/login", methods=["GET", "POST"])
def login():
    """allowed_emails.txt 기반 로그인"""
    allowed_emails = load_allowed_emails()

    if not allowed_emails:
        flash("⚠️ allowed_emails.txt 파일이 비어 있거나 존재하지 않습니다.", "danger")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if email in allowed_emails:
            session["user"] = email
            flash(f"{email} 님 환영합니다!", "success")
            return redirect(url_for("lecture_list"))
        else:
            flash("❌ 허용되지 않은 이메일 주소입니다.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("👋 로그아웃되었습니다.", "info")
    return redirect(url_for("login"))


# ─────────────────────────────
# 📘 강의자료 + Q&A 게시판
# ─────────────────────────────
@app.route("/lecture", methods=["GET", "POST"])
@login_required
def lecture_list():
    data = load_data()
    qna_df = load_qna()
    wrong_pw_index = None
    temp_reply = ""

    if request.method == "POST":
        action = request.form.get("action")

        # 🧑‍🎓 질문 등록
        if action == "add_qna":
            name = request.form.get("name", "").strip() or "익명"
            question = request.form.get("question", "").strip()
            password = request.form.get("password", "").strip()

            if not question:
                flash("질문 내용을 입력하세요.", "warning")
                return redirect(url_for("lecture_list"))

            if not password.isdigit() or len(password) != 4:
                flash("비밀번호는 숫자 4자리여야 합니다.", "danger")
                return redirect(url_for("lecture_list"))

            new_row = pd.DataFrame([{
                "이름": name,
                "질문": question,
                "답변": "",
                "비밀번호": password,
                "등록시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }])
            qna_df = pd.concat([qna_df, new_row], ignore_index=True)
            save_qna(qna_df)
            flash("질문이 등록되었습니다.", "success")
            return redirect(url_for("lecture_list"))

        # 🧑‍🎓 질문 삭제
        elif action == "delete_qna":
            index = int(request.form.get("index", -1))
            password = request.form.get("password", "").strip()
            if 0 <= index < len(qna_df):
                if password == str(qna_df.iloc[index]["비밀번호"]):
                    qna_df = qna_df.drop(index).reset_index(drop=True)
                    save_qna(qna_df)
                    flash("질문이 삭제되었습니다.", "success")
                else:
                    flash("비밀번호가 일치하지 않습니다.", "danger")
            return redirect(url_for("lecture_list"))

        # 👨‍🏫 교수 답변 등록/수정
        elif action == "reply_qna":
            index = int(request.form.get("index", -1))
            reply = request.form.get("reply", "").strip()
            password = request.form.get("password", "").strip()

            if password != PROFESSOR_PASSWORD:
                flash("교수 비밀번호가 올바르지 않습니다.", "danger")
                wrong_pw_index = index
                temp_reply = reply
            else:
                if 0 <= index < len(qna_df):
                    qna_df.at[index, "답변"] = reply
                    save_qna(qna_df)
                    flash("답변이 등록(수정)되었습니다.", "success")
            return render_template(
                "lecture.html",
                data=data,
                qna=qna_df.to_dict("records"),
                wrong_pw_index=wrong_pw_index,
                temp_reply=temp_reply,
            )

        # 👨‍🏫 교수 답변 삭제
        elif action == "delete_reply":
            index = int(request.form.get("index", -1))
            password = request.form.get("password", "").strip()
            if password == PROFESSOR_PASSWORD and 0 <= index < len(qna_df):
                qna_df.at[index, "답변"] = ""
                save_qna(qna_df)
                flash("답변이 삭제되었습니다.", "info")
            else:
                flash("교수 비밀번호가 올바르지 않습니다.", "danger")
            return redirect(url_for("lecture_list"))

    return render_template(
        "lecture.html",
        data=data,
        qna=qna_df.to_dict("records"),
        wrong_pw_index=wrong_pw_index,
        temp_reply=temp_reply,
    )


# ─────────────────────────────
# 📤 강의자료 업로드
# ─────────────────────────────
@app.route("/lecture_upload", methods=["GET", "POST"])
@login_required
def lecture_upload():
    data = load_data()

    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        file_urls = request.form.get("file_urls", "").strip()
        sites = request.form.get("sites", "").strip()
        notes = request.form.get("notes", "").strip()

        if not topic:
            flash("내용(Topic)을 입력하세요.", "warning")
            return redirect(url_for("lecture_upload"))

        new_entry = {
            "내용(Topic)": topic,
            "자료파일(File URL)": file_urls,
            "연관사이트(Related Site)": sites,
            "비고(Notes)": notes,
            "업로드시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        data.append(new_entry)
        save_data(data)
        flash("📘 강의자료가 등록되었습니다.", "success")
        return redirect(url_for("lecture_list"))

    return render_template("lecture_upload.html", data=data)


# ─────────────────────────────
# 📘 자료 수정/삭제 페이지
# ─────────────────────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
@login_required
def upload_lecture():
    data = load_data()
    edit_index = request.args.get("edit")
    edit_data = None

    if edit_index is not None and edit_index.isdigit():
        idx = int(edit_index)
        if 0 <= idx < len(data):
            edit_data = data[idx]

    if request.method == "POST":
        delete_row = request.form.get("delete_row")
        if delete_row is not None:
            idx = int(delete_row)
            if 0 <= idx < len(data):
                data.pop(idx)
                save_data(data)
                flash("🗑️ 자료가 삭제되었습니다.", "info")
                return redirect(url_for("upload_lecture"))

        topic = request.form.get("topic", "").strip()
        notes = request.form.get("notes", "").strip()

        file_urls = []
        related_sites = []
        for key in request.form:
            if key.startswith("file_upload"):
                file_urls.append(request.form[key])
            if key.startswith("related_site"):
                related_sites.append(request.form[key])

        file_urls = ";".join([f for f in file_urls if f.strip()])
        related_sites = ";".join([s for s in related_sites if s.strip()])

        new_entry = {
            "내용(Topic)": topic,
            "자료파일(File URL)": file_urls or "-",
            "연관사이트(Related Site)": related_sites or "-",
            "비고(Notes)": notes or "-",
            "업로드시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        if "edit_index" in request.form:
            idx = int(request.form["edit_index"])
            if 0 <= idx < len(data):
                data[idx] = new_entry
                flash("✏️ 강의자료가 수정되었습니다.", "success")
        else:
            data.append(new_entry)
            flash("📤 새 강의자료가 등록되었습니다.", "success")

        save_data(data)
        return redirect(url_for("upload_lecture"))

    return render_template("upload_lecture.html", data=data, edit_data=edit_data)


# ✅ 기본 홈페이지 → 로그인으로 리디렉션
@app.route("/")
def home():
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
