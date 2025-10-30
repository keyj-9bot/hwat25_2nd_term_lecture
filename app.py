# -*- coding: utf-8 -*-
"""
📘 연암공대 화트25 강의자료 학습 & Q&A 시스템 (직전 안정판 / 단일 CSV)
작성자: Key 교수님
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import pandas as pd
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import chardet

app = Flask(__name__)
app.secret_key = "key_flask_secret"

# ───────────── 세션 안정화 (Render HTTPS 대응) ─────────────
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="None",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
)

# ───────────── 설정 ─────────────
DATA_LECTURE = "lecture_data.csv"
DATA_QUESTIONS = "questions.csv"
DATA_COMMENTS = "comments.csv"
ALLOWED_EMAILS = "allowed_emails.txt"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ───────────── CSV 로드/저장 ─────────────
def load_csv(path, cols):
    """CSV 안전 로드"""
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                raw = f.read()
                enc = chardet.detect(raw)["encoding"] or "utf-8"
            return pd.read_csv(path, encoding=enc)
        except Exception as e:
            print(f"[CSV Load Error] {e}")
    return pd.DataFrame(columns=cols)

def save_csv(path, df):
    df.to_csv(path, index=False, encoding="utf-8-sig")

# ───────────── 교수 이메일 확인 ─────────────
def get_professor_email():
    if os.path.exists(ALLOWED_EMAILS):
        with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
            for line in f:
                email = line.strip()
                if email:
                    return email
    return None

@app.context_processor
def inject_is_professor():
    email = session.get("email")
    return dict(is_professor=(email == get_professor_email()))

# ───────────── 로그인/홈/로그아웃 ─────────────
@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email:
            flash("이메일을 입력하세요.", "danger")
            return redirect(url_for("login"))

        allowed = []
        if os.path.exists(ALLOWED_EMAILS):
            with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
                allowed = [e.strip() for e in f.readlines() if e.strip()]

        if email in allowed:
            session["email"] = email
            session.permanent = True
            flash("로그인 성공!", "success")
            return redirect(url_for("home"))
        else:
            flash("등록되지 않은 이메일입니다.", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/home")
def home():
    if not session.get("email"):
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for("login"))
    return render_template("home.html", email=session["email"])

@app.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.", "info")
    return redirect(url_for("login"))

# ───────────── 교수용 업로드 페이지 ─────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    df = load_csv(DATA_LECTURE, ["title","content","files","links","date","confirmed"])
    df = df.fillna('')

    if request.method == "POST":
        try:
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            date = datetime.now().strftime("%Y-%m-%d")
            confirmed = "no"

            # 링크 처리
            links = ";".join([v.strip() for k, v in request.form.items() if "link" in k and v.strip()])

            # 파일 처리
            file_names = []
            if "files" in request.files:
                for f in request.files.getlist("files"):
                    if f and f.filename:
                        safe_name = secure_filename(f.filename.replace(" ", "_"))
                        save_path = os.path.join(UPLOAD_FOLDER, safe_name)
                        f.save(save_path)
                        file_names.append(safe_name)
            files_str = ";".join(file_names)

            # 데이터 추가
            new_row = {"title": title, "content": content, "files": files_str,
                       "links": links, "date": date, "confirmed": confirmed}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_csv(DATA_LECTURE, df)
            flash("자료가 업로드되었습니다.", "success")
        except Exception as e:
            print(f"[UPLOAD ERROR] {e}")
            flash("업로드 중 오류 발생", "danger")
        return redirect(url_for("upload_lecture"))

    return render_template("upload_lecture.html", lectures=df.to_dict("records"))

# 파일 접근
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# 게시 확정
@app.route("/confirm_lecture/<int:index>", methods=["POST"])
def confirm_lecture(index):
    df = load_csv(DATA_LECTURE, ["title","content","files","links","date","confirmed"])
    if 0 <= index < len(df):
        df.at[index, "confirmed"] = "yes"
        save_csv(DATA_LECTURE, df)
        flash("📢 게시 확정되었습니다.", "success")
    return redirect(url_for("upload_lecture"))

# 업로드 삭제
@app.route("/delete_lecture/<int:lec_index>", methods=["POST"])
def delete_lecture(lec_index):
    df = load_csv(DATA_LECTURE, ["title","content","files","links","date","confirmed"])
    if 0 <= lec_index < len(df):
        df = df.drop(index=lec_index).reset_index(drop=True)
        save_csv(DATA_LECTURE, df)
        flash("자료가 삭제되었습니다.", "info")
    return redirect(url_for("upload_lecture"))

# ───────────── 학습 자료 페이지 ─────────────
@app.route("/lecture")
def lecture():
    df_lecture = load_csv(DATA_LECTURE, ["title","content","files","links","date","confirmed"])
    df_lecture = df_lecture.fillna('')
    df_lecture = df_lecture[df_lecture["confirmed"] == "yes"]

    # 15일 이내 자료만 유지
    today = datetime.now()
    valid_rows = []
    for _, row in df_lecture.iterrows():
        try:
            d = datetime.strptime(str(row["date"]), "%Y-%m-%d")
            if (today - d).days <= 15:
                valid_rows.append(row)
        except:
            continue

    df_lecture = pd.DataFrame(valid_rows, columns=["title","content","files","links","date","confirmed"])
    save_csv(DATA_LECTURE, df_lecture)

    # Q&A 데이터 불러오기
    df_questions = load_csv(DATA_QUESTIONS, ["id","title","content","email","date"])
    df_comments = load_csv(DATA_COMMENTS, ["question_id","comment","email","date"])

    return render_template(
        "lecture.html",
        lectures=df_lecture.to_dict("records"),
        questions=df_questions.to_dict("records"),
        comments=df_comments.to_dict("records"),
        session=session
    )

# ───────────── Q&A ─────────────
@app.route("/add_question", methods=["POST"])
def add_question():
    email = session.get("email", "")
    if not email:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for("login"))

    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    if title and content:
        df = load_csv(DATA_QUESTIONS, ["id","title","content","email","date"])
        new_id = len(df) + 1
        df = pd.concat([df, pd.DataFrame([{
            "id": new_id, "title": title, "content": content,
            "email": email, "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }])], ignore_index=True)
        save_csv(DATA_QUESTIONS, df)
        flash("질문이 등록되었습니다.", "success")
    return redirect(url_for("lecture"))

@app.route("/edit_question/<int:q_id>", methods=["POST"])
def edit_question(q_id):
    email = session.get("email", "")
    df = load_csv(DATA_QUESTIONS, ["id","title","content","email","date"])
    if 0 <= q_id - 1 < len(df):
        if df.iloc[q_id - 1]["email"] == email or "professor" in email:
            df.at[q_id - 1, "title"] = request.form.get("edited_title", "")
            df.at[q_id - 1, "content"] = request.form.get("edited_content", "")
            df.at[q_id - 1, "date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_csv(DATA_QUESTIONS, df)
            flash("질문이 수정되었습니다.", "info")
    return redirect(url_for("lecture"))

@app.route("/delete_question/<int:q_id>", methods=["POST"])
def delete_question(q_id):
    email = session.get("email", "")
    df = load_csv(DATA_QUESTIONS, ["id","title","content","email","date"])
    if 0 <= q_id - 1 < len(df):
        if df.iloc[q_id - 1]["email"] == email or "professor" in email:
            df = df.drop(index=q_id - 1).reset_index(drop=True)
            save_csv(DATA_QUESTIONS, df)
            flash("질문이 삭제되었습니다.", "info")
    return redirect(url_for("lecture"))

@app.route("/add_comment/<int:q_id>", methods=["POST"])
def add_comment(q_id):
    email = session.get("email", "")
    comment = request.form.get("comment", "").strip()
    if email and comment:
        df = load_csv(DATA_COMMENTS, ["question_id","comment","email","date"])
        df = pd.concat([df, pd.DataFrame([{
            "question_id": q_id, "comment": comment, "email": email,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }])], ignore_index=True)
        save_csv(DATA_COMMENTS, df)
        flash("댓글이 등록되었습니다.", "success")
    return redirect(url_for("lecture"))

@app.route("/edit_comment/<int:q_id>/<int:c_idx>", methods=["POST"])
def edit_comment(q_id, c_idx):
    email = session.get("email", "")
    df = load_csv(DATA_COMMENTS, ["question_id","comment","email","date"])
    if 0 <= c_idx < len(df):
        if df.iloc[c_idx]["question_id"] == q_id and (df.iloc[c_idx]["email"] == email or "professor" in email):
            df.at[c_idx, "comment"] = request.form.get("edited_comment", "")
            df.at[c_idx, "date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_csv(DATA_COMMENTS, df)
            flash("댓글이 수정되었습니다.", "info")
    return redirect(url_for("lecture"))

@app.route("/delete_comment/<int:q_id>/<int:c_idx>", methods=["POST"])
def delete_comment(q_id, c_idx):
    email = session.get("email", "")
    df = load_csv(DATA_COMMENTS, ["question_id","comment","email","date"])
    if 0 <= c_idx < len(df):
        if df.iloc[c_idx]["question_id"] == q_id and (df.iloc[c_idx]["email"] == email or "professor" in email):
            df = df.drop(index=c_idx).reset_index(drop=True)
            save_csv(DATA_COMMENTS, df)
            flash("댓글이 삭제되었습니다.", "info")
    return redirect(url_for("lecture"))

# ───────────── Health Check ─────────────
@app.route("/health")
def health():
    return "OK", 200

# ───────────── 앱 실행 ─────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"✅ Server running on port {port}")
    app.run(host="0.0.0.0", port=port)

