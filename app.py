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

app = Flask(__name__)
app.secret_key = "key_flask_secret"

# ───────────── 세션 안정화 (Render HTTPS 환경 대응) ─────────────
app.config.update(
    SESSION_COOKIE_SECURE=True,           # HTTPS에서만 쿠키 허용
    SESSION_COOKIE_SAMESITE="None",       # 크로스 도메인 세션 허용
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
)

# ───────────── 설정 ─────────────
DATA_LECTURE = "lecture_data.csv"
DATA_QUESTIONS = "questions.csv"
DATA_COMMENTS = "comments.csv"
ALLOWED_EMAILS = "allowed_emails.txt"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ──────────────── CSV 로드/저장 ────────────────
def load_csv(path, cols):
    """CSV 안전 로드 (자동 인코딩 감지 + 복구)"""
    import os
    import chardet
    import pandas as pd

    if not os.path.exists(path):
        return pd.DataFrame(columns=cols)

    try:
        # 기본 UTF-8 시도
        return pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        try:
            # 인코딩 자동 감지 후 재시도
            with open(path, "rb") as f:
                enc = chardet.detect(f.read())["encoding"] or "utf-8-sig"
            print(f"[Auto Encoding Detection] {path}: {enc}")
            return pd.read_csv(path, encoding=enc)
        except Exception as e:
            print(f"[CSV Load Recovery Error] {path}: {e}")
            return pd.DataFrame(columns=cols)
    except Exception as e:
        print(f"[CSV Load Error] {path}: {e}")
        return pd.DataFrame(columns=cols)


def save_csv(path, df):
    """CSV 안전 저장 (UTF-8-SIG로 통일)"""
    import os
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
    if "email" not in session:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for("login"))

    df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date", "confirmed"])

    # ✅ confirmed 컬럼 없거나 NaN일 경우 자동 보정
    if "confirmed" not in df.columns:
        df["confirmed"] = "no"
    df["confirmed"] = df["confirmed"].fillna("no")

    # ✅ 업로드 처리
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        # 파일 처리
        uploaded_files = request.files.getlist("files")
        file_names = []
        for file in uploaded_files:
            if file and file.filename:
                safe_name = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, safe_name))
                file_names.append(safe_name)
        files_str = ";".join(file_names)

        # 링크 처리
        links = [v for k, v in request.form.items() if k.startswith("link") and v.strip()]
        links_str = ";".join(links)

        # CSV에 추가
        new_row = {
            "title": title,
            "content": content,
            "files": files_str,
            "links": links_str,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "confirmed": "no"
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_csv(DATA_LECTURE, df)
        flash("강의자료가 업로드되었습니다. '게시 확정'을 눌러야 학습사이트에 표시됩니다.", "success")
        return redirect(url_for("upload_lecture"))

    return render_template("upload_lecture.html", lectures=df.to_dict("records"))






@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except FileNotFoundError:
        flash("파일을 찾을 수 없습니다.", "danger")
        return redirect(url_for("lecture"))


# ✅ 강의자료 게시 확정 (confirm)
@app.route("/confirm_lecture", methods=["POST"])
def confirm_lecture():
    """게시 확정 버튼 처리"""
    if "email" not in session:
        return redirect(url_for("login"))

    # HTML form에서 전달된 index 받기
    index = int(request.form.get("index", -1))

    # CSV 로드
    df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date", "confirmed"])

    # 유효한 인덱스 범위 내일 때만 처리
    if 0 <= index < len(df):
        df.at[index, "confirmed"] = "yes"  # 혹은 True로 저장해도 무방 (문자열 통일 권장)
        save_csv(DATA_LECTURE, df)
        flash("📢 해당 자료가 게시 확정되었습니다.", "success")

    return redirect(url_for("upload_lecture"))

     








# ❌ 강의자료 삭제
@app.route("/delete_lecture/<int:lec_index>", methods=["POST"])
def delete_lecture(lec_index):
    """강의자료 삭제"""
    df = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date", "confirmed"])

    if lec_index < len(df):
        deleted_row = df.iloc[lec_index]
        df = df.drop(index=lec_index).reset_index(drop=True)
        save_csv(DATA_LECTURE, df)

        # 파일 삭제 (옵션)
        if deleted_row.get("files"):
            for f in str(deleted_row["files"]).split(";"):
                path = os.path.join(UPLOAD_FOLDER, f.strip())
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass

        flash("강의자료가 삭제되었습니다 🗑️", "info")

    return redirect(url_for("upload_lecture"))






# ───────────── 학습 사이트 (강의자료 + Q&A) ─────────────
@app.route("/lecture", methods=["GET", "POST"])
def lecture():
    email = session.get("email")
    if not email:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for("login"))

    # ✅ 안전한 CSV 로드
    df_lecture = load_csv(DATA_LECTURE, ["title", "content", "files", "links", "date", "confirmed"])
    df_questions = load_csv(DATA_QUESTIONS, ["id", "title", "content", "email", "date"])
    df_comments = load_csv(DATA_COMMENTS, ["question_id", "comment", "email"])

    # ✅ confirmed 컬럼 보정 (없거나 NaN일 경우 'no'로 설정)
    if "confirmed" not in df_lecture.columns:
        df_lecture["confirmed"] = "no"
    df_lecture["confirmed"] = df_lecture["confirmed"].fillna("no")

    # ✅ "yes"로 표시된 게시 확정 자료만 표시
    df_lecture = df_lecture[df_lecture["confirmed"].astype(str).str.lower() == "yes"]

    # ✅ 15일 이내 자료만 유지 (날짜 오류 발생시 무시)
    today = datetime.now()
    valid_rows = []
    for _, row in df_lecture.iterrows():
        try:
            d = datetime.strptime(str(row["date"]), "%Y-%m-%d %H:%M")
            if (today - d).days <= 15:
                valid_rows.append(row)
        except Exception as e:
            print(f"[Date Parse Error] {e}")
            continue

    df_lecture = pd.DataFrame(valid_rows, columns=["title", "content", "files", "links", "date", "confirmed"])
    save_csv(DATA_LECTURE, df_lecture)

    # ✅ Q&A 질문 등록
    if request.method == "POST" and "title" in request.form:
        new_id = len(df_questions) + 1
        new_q = {
            "id": new_id,
            "title": request.form["title"].strip(),
            "content": request.form["content"].strip(),
            "email": email,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        df_questions = pd.concat([df_questions, pd.DataFrame([new_q])], ignore_index=True)
        save_csv(DATA_QUESTIONS, df_questions)
        flash("질문이 등록되었습니다.", "success")
        return redirect(url_for("lecture"))

    return render_template(
        "lecture.html",
        lectures=df_lecture.to_dict("records"),
        questions=df_questions.to_dict("records"),
        comments=df_comments.to_dict("records"),
        user_email=email,
    )


# 💬 댓글 등록
@app.route("/add_comment/<int:question_id>", methods=["POST"])
def add_comment(question_id):
    email = session.get("email")
    if not email:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for("login"))

    comment = request.form["comment"].strip()
    if comment:
        df = load_csv(DATA_COMMENTS, ["question_id", "comment", "email"])
        df = pd.concat(
            [df, pd.DataFrame([{"question_id": question_id, "comment": comment, "email": email}])],
            ignore_index=True,
        )
        save_csv(DATA_COMMENTS, df)
        flash("댓글이 등록되었습니다.", "success")
    return redirect(url_for("lecture"))

# ❌ 질문 삭제
@app.route("/delete_question/<int:q_id>", methods=["POST"])
def delete_question(q_id):
    email = session.get("email")
    df = load_csv(DATA_QUESTIONS, ["id", "title", "content", "email", "date"])
    df = df[~((df["id"] == q_id) & (df["email"] == email))]
    save_csv(DATA_QUESTIONS, df)
    flash("질문이 삭제되었습니다.", "info")
    return redirect(url_for("lecture"))

# ❌ 댓글 삭제
@app.route("/delete_comment/<int:q_id>/<int:c_idx>", methods=["POST"])
def delete_comment(q_id, c_idx):
    email = session.get("email")
    df = load_csv(DATA_COMMENTS, ["question_id", "comment", "email"])
    df = df.drop(df[(df.index == c_idx) & (df["question_id"] == q_id) & (df["email"] == email)].index)
    save_csv(DATA_COMMENTS, df)
    flash("댓글이 삭제되었습니다.", "info")
    return redirect(url_for("lecture"))

# ───────────── Health Check (Render 배포 안정화용) ─────────────
@app.route("/health")
def health():
    return "OK", 200

# ───────────── 앱 실행 ─────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"✅ Server running on port {port}")
    app.run(host="0.0.0.0", port=port)
