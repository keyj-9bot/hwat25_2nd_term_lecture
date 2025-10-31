# -*- coding: utf-8 -*-
"""
📘 연암공대 화트25 학습지원시스템 (Final Stable + Q&A 완전판)
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

# ───────────── 세션 안정화 (Render HTTPS 환경 대응) ─────────────
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="None",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
)

# ───────────── 설정 ─────────────
UPLOAD_FOLDER = "/data/uploads"
DATA_LECTURE = "/data/lecture_data.csv"
DATA_QUESTIONS = "/data/questions.csv"
DATA_COMMENTS = "/data/comments.csv"
DATA_UPLOADS = "/data/uploads_data.csv"     # ✅ 업로드 전용 CSV
DATA_POSTS = "/data/posts_data.csv"         # ✅ 학습사이트 게시 전용 CSV
ALLOWED_EMAILS = "allowed_emails.txt"

# 업로드 폴더 생성 (디스크 경로 기준)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ───────────── CSV 로드/저장 ─────────────
def load_csv(path, cols):
    """CSV 안전 로드 (자동 인코딩 감지)"""
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
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")

# ───────────── 공용 함수 ─────────────
def get_professor_email():
    """allowed_emails.txt의 첫 줄(교수 이메일)을 반환"""
    if os.path.exists(ALLOWED_EMAILS):
        with open(ALLOWED_EMAILS, "r", encoding="utf-8") as f:
            for line in f:
                email = line.strip()
                if email:
                    return email
    return None

# ───────────── 템플릿 공용 변수 주입 ─────────────
@app.context_processor
def inject_is_professor():
    email = session.get("email")
    return dict(is_professor=(email == get_professor_email()))

# ───────────── 기본 라우트 ─────────────
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
    email = session.get("email")
    if not email:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for("login"))
    return render_template("home.html", email=email)

@app.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.", "info")
    return redirect(url_for("login"))

# ───────────── 교수용 업로드 페이지 ─────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    df = load_csv(DATA_UPLOADS, ["title", "content", "files", "links", "date", "confirmed"])
    df = df.fillna('')

    if request.method == "POST":
        try:
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            date = datetime.now().strftime("%Y-%m-%d")
            confirmed = "no"

            # 🔗 링크 처리
            link_values = [v.strip() for k, v in request.form.items() if "link" in k and v.strip()]
            links = ";".join(link_values)

            # 📂 파일 처리
            file_names = []
            if "files" in request.files:
                files = request.files.getlist("files")
                for f in files:
                    if f and f.filename:
                        orig_name = f.filename
                        safe_name = orig_name.replace(" ", "_").replace("/", "").replace("\\", "")
                        save_path = os.path.join(UPLOAD_FOLDER, safe_name)
                        f.save(save_path)
                        file_names.append(safe_name)
            files_str = ";".join(file_names)

            # 🧩 새 행 추가
            new_row = {
                "title": title,
                "content": content,
                "files": files_str,
                "links": links,
                "date": date,
                "confirmed": confirmed
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_csv(DATA_UPLOADS, df)
            flash("자료가 성공적으로 업로드되었습니다.", "success")
        except Exception as e:
            print(f"[UPLOAD ERROR] {e}")
            flash("업로드 중 오류가 발생했습니다.", "danger")
        return redirect(url_for("upload_lecture"))

    # ✅ 학습사이트 게시 목록 로드 (재게시 버튼용) ← ★ 이 위치로 이동해야 정상 작동
    df_posts = load_csv(DATA_POSTS, ["title", "content", "files", "links", "date", "confirmed"])
    post_titles = df_posts["title"].dropna().tolist()

    # ✅ post_titles를 함께 전달
    return render_template("upload_lecture.html", lectures=df.to_dict("records"), post_titles=post_titles)





@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except FileNotFoundError:
        flash("파일을 찾을 수 없습니다.", "danger")
        return redirect(url_for("lecture"))

# ✅ 게시 확정
@app.route("/confirm_lecture/<int:index>", methods=["POST"])
def confirm_lecture(index):
    df_uploads = load_csv(DATA_UPLOADS, ["title", "content", "files", "links", "date", "confirmed"])
    df_posts = load_csv(DATA_POSTS, ["title", "content", "files", "links", "date", "confirmed"])
    if 0 <= index < len(df_uploads):
        row = df_uploads.iloc[index]
        row["confirmed"] = "yes"
        # 게시DB에 추가 (중복방지)
        if not ((df_posts["title"] == row["title"]) & (df_posts["date"] == row["date"])).any():
            df_posts = pd.concat([df_posts, pd.DataFrame([row])], ignore_index=True)
            save_csv(DATA_POSTS, df_posts)
        df_uploads.at[index, "confirmed"] = "yes"
        save_csv(DATA_UPLOADS, df_uploads)
        flash("📢 학습사이트에 게시되었습니다.", "success")
    return redirect(url_for("upload_lecture"))

# 🗑️ 강의자료 삭제
@app.route("/delete_lecture/<int:index>", methods=["POST"])
def delete_lecture(index):
    """업로드 데이터만 삭제 (게시자료는 영향 없음)"""
    df = load_csv(DATA_UPLOADS, ["title", "content", "files", "links", "date", "confirmed"])
    if 0 <= index < len(df):
        deleted_row = df.iloc[index]
        df = df.drop(index=index).reset_index(drop=True)
        save_csv(DATA_UPLOADS, df)
        flash("업로드 자료가 삭제되었습니다 (게시자료는 유지).", "info")
    return redirect(url_for("upload_lecture"))

# 🗑️ 학습사이트 게시자료 삭제(교수만)
@app.route("/delete_confirmed/<int:index>", methods=["POST"])
def delete_confirmed(index):
    email = session.get("email", "")
    if email != get_professor_email():
        flash("교수만 삭제할 수 있습니다.", "danger")
        return redirect(url_for("lecture"))

    df_posts = load_csv(DATA_POSTS, ["title", "content", "files", "links", "date", "confirmed"])
    if 0 <= index < len(df_posts):
        df_posts = df_posts.drop(index=index).reset_index(drop=True)
        save_csv(DATA_POSTS, df_posts)
        flash("게시된 자료가 삭제되었습니다.", "info")
    return redirect(url_for("lecture"))

# ───────────── 학습 사이트 (학생용) ─────────────
@app.route("/lecture")
def lecture():
    # ✅ 강의자료 불러오기
    df_posts = load_csv(DATA_POSTS, ["title", "content", "files", "links", "date", "confirmed"])
    df_posts = df_posts.fillna('')
    today = datetime.now()

    # ✅ 15일 경과 자료 자동 삭제
    recent_posts = []
    for _, row in df_posts.iterrows():
        try:
            d = datetime.strptime(str(row["date"]).split()[0], "%Y-%m-%d")
            if (today - d).days <= 15:
                recent_posts.append(row)
        except:
            continue
    df_posts = pd.DataFrame(recent_posts, columns=["title", "content", "files", "links", "date", "confirmed"])
    save_csv(DATA_POSTS, df_posts)
    lectures = df_posts.to_dict("records")

    # ✅ 질문 및 댓글 불러오기
    df_questions = load_csv(DATA_QUESTIONS, ["id", "title", "content", "email", "date"])
    df_comments = load_csv(DATA_COMMENTS, ["question_id", "comment", "email", "date"])

    questions = df_questions.to_dict("records")
    comments = df_comments.to_dict("records")

    # ✅ 세 데이터 모두 템플릿에 전달
    return render_template(
        "lecture.html",
        lectures=lectures,
        questions=questions,
        comments=comments
    )


# ───────────── 질문 등록/수정/삭제 ─────────────
@app.route("/add_question", methods=["POST"])
def add_question():
    email = session.get("email", "")
    if not email:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for("login"))

    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    if title and content:
        df = load_csv(DATA_QUESTIONS, ["id", "title", "content", "email", "date"])
        new_id = len(df) + 1
        new_q = {
            "id": new_id,
            "title": title,
            "content": content,
            "email": email,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        df = pd.concat([df, pd.DataFrame([new_q])], ignore_index=True)
        save_csv(DATA_QUESTIONS, df)
        flash("질문이 등록되었습니다.", "success")
    else:
        flash("제목과 내용을 모두 입력해주세요.", "warning")
    return redirect(url_for("lecture"))


@app.route("/edit_question/<int:q_id>", methods=["POST"])
def edit_question(q_id):
    email = session.get("email", "")
    df = load_csv(DATA_QUESTIONS, ["id", "title", "content", "email", "date"])
    if 0 <= q_id - 1 < len(df):
        target = df.iloc[q_id - 1]
        if target["email"] == email or email == get_professor_email():
            new_title = request.form.get("edited_title", "").strip()
            new_content = request.form.get("edited_content", "").strip()
            if new_title:
                df.at[q_id - 1, "title"] = new_title
            if new_content:
                df.at[q_id - 1, "content"] = new_content
            df.at[q_id - 1, "date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_csv(DATA_QUESTIONS, df)
            flash("질문이 수정되었습니다.", "info")
    return redirect(url_for("lecture"))


@app.route("/delete_question/<int:q_id>", methods=["POST"])
def delete_question(q_id):
    email = session.get("email", "")
    df = load_csv(DATA_QUESTIONS, ["id", "title", "content", "email", "date"])
    if 0 <= q_id - 1 < len(df):
        target = df.iloc[q_id - 1]
        if target["email"] == email or email == get_professor_email():
            df = df.drop(index=q_id - 1).reset_index(drop=True)
            save_csv(DATA_QUESTIONS, df)
            flash("질문이 삭제되었습니다.", "info")
    return redirect(url_for("lecture"))

# ───────────── 댓글 등록/수정/삭제 ─────────────
@app.route("/add_comment/<int:q_id>", methods=["POST"])
def add_comment(q_id):
    email = session.get("email", "")
    if not email:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for("login"))

    comment = request.form.get("comment", "").strip()
    if comment:
        df = load_csv(DATA_COMMENTS, ["question_id", "comment", "email", "date"])
        new_row = {
            "question_id": q_id,
            "comment": comment,
            "email": email,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_csv(DATA_COMMENTS, df)
        flash("댓글이 등록되었습니다.", "success")
    return redirect(url_for("lecture"))


@app.route("/edit_comment/<int:q_id>/<int:c_idx>", methods=["POST"])
def edit_comment(q_id, c_idx):
    email = session.get("email", "")
    df = load_csv(DATA_COMMENTS, ["question_id", "comment", "email", "date"])
    if 0 <= c_idx < len(df):
        target = df.iloc[c_idx]
        if target["question_id"] == q_id and (target["email"] == email or email == get_professor_email()):
            new_comment = request.form.get("edited_comment", "").strip()
            df.at[c_idx, "comment"] = new_comment
            df.at[c_idx, "date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_csv(DATA_COMMENTS, df)
            flash("댓글이 수정되었습니다.", "info")
    return redirect(url_for("lecture"))


@app.route("/delete_comment/<int:q_id>/<int:c_idx>", methods=["POST"])
def delete_comment(q_id, c_idx):
    email = session.get("email", "")
    df = load_csv(DATA_COMMENTS, ["question_id", "comment", "email", "date"])
    if 0 <= c_idx < len(df):
        target = df.iloc[c_idx]
        if target["question_id"] == q_id and (target["email"] == email or email == get_professor_email()):
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

