# -*- coding: utf-8 -*-
"""
📘 연암공대 화트25 학습지원시스템 (Final Stable + Q&A 완전판)
작성자: Key 교수님
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import pandas as pd
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "key_flask_secret"

# ───────────── 세션 안정화 (Render HTTPS 환경 대응) ─────────────
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="None",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
)

# ───────────── 설정 ─────────────
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
DATA_LECTURE = "lecture_data.csv"
DATA_QUESTIONS = "questions.csv"
DATA_COMMENTS = "comments.csv"
DATA_UPLOADS = "uploads_data.csv"     # ✅ 업로드 전용 CSV
DATA_POSTS = "posts_data.csv"         # ✅ 학습사이트 게시 전용 CSV
ALLOWED_EMAILS = "allowed_emails.txt"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ───────────── CSV 로드/저장 ─────────────
def load_csv(path, cols):
    """CSV 안전 로드 (헤더 오류 시 자동 초기화)"""
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            if df.empty or list(df.columns) != cols:
                return pd.DataFrame(columns=cols)
            return df
        except Exception as e:
            print(f"[CSV Load Error] {e}")
            return pd.DataFrame(columns=cols)
    else:
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


# ───────────── 템플릿 변수 주입 ─────────────
@app.context_processor
def inject_is_professor():
    email = session.get("email")
    return dict(is_professor=(email == get_professor_email()))


# ───────────── 기본 라우트 ─────────────
@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/lecture")
def lecture():
    # ✅ 로그인 세션 확인 (없으면 로그인 페이지로 이동)
    if "user" not in session:
        flash("🔒 로그인 후 이용 가능합니다.", "warning")
        return redirect(url_for("login"))

    df_posts = load_csv(DATA_POSTS, ["title", "content", "files", "links", "date", "confirmed"])
    df_posts = df_posts.fillna('')
    today = datetime.now()

    # ✅ 15일 지난 자료 자동 제거
    recent_posts = []
    for _, row in df_posts.iterrows():
        try:
            date_str = str(row.get("date", "")).split()[0]
            if not date_str or date_str.lower() == "nan":
                continue
            d = datetime.strptime(date_str, "%Y-%m-%d")
            if (today - d).days <= 15:
                recent_posts.append(row)
        except Exception as e:
            print(f"[LECTURE ERROR] {e} / row={row}")
            continue

    df_posts = pd.DataFrame(recent_posts, columns=["title", "content", "files", "links", "date", "confirmed"])
    save_csv(DATA_POSTS, df_posts)
    lectures = df_posts.to_dict("records")

    df_questions = load_csv(DATA_QUESTIONS, ["id", "title", "content", "email", "date"])
    df_comments = load_csv(DATA_COMMENTS, ["question_id", "comment", "email", "date"])

    return render_template(
        "lecture.html",
        lectures=lectures,
        questions=df_questions.to_dict("records"),
        comments=df_comments.to_dict("records"),
    )



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


# ───────────── 교수용 업로드 ─────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
def upload_lecture():
    # ✅ 로그인 및 교수 계정 확인
    email = session.get("email")
    if not email:
        flash("🔒 로그인 후 이용 가능합니다.", "warning")
        return redirect(url_for("login"))
    if email != get_professor_email():
        flash("⚠️ 교수 전용 페이지입니다.", "danger")
        return redirect(url_for("lecture"))

    df = load_csv(DATA_UPLOADS, ["title", "content", "files", "links", "date", "confirmed"]).fillna('')

    if request.method == "POST":
        try:
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            date = datetime.now().strftime("%Y-%m-%d")
            confirmed = "no"

            # 🔗 링크
            link_values = [v.strip() for k, v in request.form.items() if "link" in k and v.strip()]
            links = ";".join(link_values)

            # 📂 파일
            file_names = []
            if "files" in request.files:
                for f in request.files.getlist("files"):
                    if f and f.filename:
                        fname = f.filename.replace(" ", "_").replace("/", "").replace("\\", "")
                        f.save(os.path.join(UPLOAD_FOLDER, fname))
                        file_names.append(fname)
            files_str = ";".join(file_names)

            new_row = {
                "title": title,
                "content": content,
                "files": files_str,
                "links": links,
                "date": date,
                "confirmed": confirmed,
            }

            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_csv(DATA_UPLOADS, df)
            flash("자료가 성공적으로 업로드되었습니다.", "success")

        except Exception as e:
            print(f"[UPLOAD ERROR] {e}")
            flash("업로드 중 오류가 발생했습니다.", "danger")

        return redirect(url_for("upload_lecture"))

    # ✅ 게시된 자료 목록도 함께 로드
    df_posts = load_csv(DATA_POSTS, ["title", "content", "files", "links", "date", "confirmed"])
    return render_template("upload_lecture.html", lectures=df.to_dict("records"), post_titles=df_posts["title"].tolist())


# ───────────── 강의자료 수정 ─────────────
@app.route("/edit_lecture/<int:index>", methods=["POST"])
def edit_lecture(index):
    df = load_csv(DATA_UPLOADS, ["title", "content", "files", "links", "date", "confirmed"])
    if 0 <= index < len(df):
        lec = df.loc[index].copy()
        title = request.form.get("title", lec["title"])
        content = request.form.get("content", lec["content"])
        links = request.form.get("links", lec["links"])

        # 🔹 전체 파일 삭제
        if request.form.get("delete_file") == "1" and lec.get("files"):
            for f in str(lec["files"]).split(";"):
                path = os.path.join(UPLOAD_FOLDER, f)
                if os.path.exists(path):
                    os.remove(path)
            lec["files"] = ""

        # 🔹 일부 파일 삭제
        delete_list = request.form.get("delete_files", "")
        if delete_list:
            for fname in delete_list.split(";"):
                path = os.path.join(UPLOAD_FOLDER, fname.strip())
                if os.path.exists(path):
                    os.remove(path)
            remaining = [f for f in str(lec["files"]).split(";") if f.strip() and f.strip() not in delete_list.split(";")]
            lec["files"] = ";".join(remaining)

        # 🔹 새 파일 추가 (복수 가능, 한글 유지)
        if "new_files" in request.files:
            new_files = request.files.getlist("new_files")
            added = []
            for nf in new_files:
                if nf and nf.filename:
                    fname = nf.filename.replace(" ", "_").replace("/", "").replace("\\", "")
                    nf.save(os.path.join(UPLOAD_FOLDER, fname))
                    added.append(fname)
            if added:
                combined = str(lec["files"]).split(";") + added
                lec["files"] = ";".join(f for f in combined if f.strip())

        # 🔹 데이터 반영
        df.loc[index, ["title", "content", "links", "files"]] = [str(title), str(content), str(links), lec["files"]]
        save_csv(DATA_UPLOADS, df)
        flash("📘 강의자료가 수정되었습니다.", "success")
        print(f"[EDIT] '{title}' 수정 완료 / 파일: {lec['files']}")
    return redirect(url_for("upload_lecture"))


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
        title = str(row["title"]).strip()
        date = str(row["date"]).strip()

        # ✅ 게시 또는 재게시 (dtype 일관성 유지)
        df_uploads.at[index, "confirmed"] = str("yes")

        # 중복 게시 방지
        if not ((df_posts["title"] == title) & (df_posts["date"] == date)).any():
            df_posts = pd.concat([df_posts, pd.DataFrame([row])], ignore_index=True)
            save_csv(DATA_POSTS, df_posts)

        save_csv(DATA_UPLOADS, df_uploads)
        flash("📢 학습사이트에 게시되었습니다.", "success")
        print(f"[CONFIRM] '{title}' → 게시 완료 (업로드 목록 반영)")

    return redirect(url_for("upload_lecture"))






# 🗑️ 강의자료 삭제
@app.route("/delete_lecture/<int:index>", methods=["POST"])
def delete_lecture(index):
    df = load_csv(DATA_UPLOADS, ["title", "content", "files", "links", "date", "confirmed"])
    if 0 <= index < len(df):
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
    df_uploads = load_csv(DATA_UPLOADS, ["title", "content", "files", "links", "date", "confirmed"])

    if 0 <= index < len(df_posts):
        row = df_posts.iloc[index]
        title = str(row["title"]).strip()
        date = str(row["date"]).strip()

        # 🔹 학습사이트 게시자료 삭제
        df_posts = df_posts.drop(index=index).reset_index(drop=True)
        save_csv(DATA_POSTS, df_posts)
        flash("게시된 자료가 학습사이트에서 삭제되었습니다.", "info")

        # 🔹 업로드 목록 상태 변경 → 재게시
        for i in range(len(df_uploads)):
            if str(df_uploads.at[i, "title"]).strip() == title and str(df_uploads.at[i, "date"]).strip() == date:
                df_uploads.at[i, "confirmed"] = "retry"
                print(f"[DELETE CONFIRMED] '{title}' 삭제됨 → 업로드 목록 상태 'retry'(재게시)로 변경 완료")
                break

        save_csv(DATA_UPLOADS, df_uploads)

    return redirect(url_for("lecture"))





# ───────────── Q&A 질문 등록/수정/삭제 ─────────────
@app.route("/add_question", methods=["POST"])
def add_question():
    email = session.get("email", "")
    if not email:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for("login"))

    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    if not title or not content:
        flash("제목과 내용을 모두 입력해주세요.", "warning")
        return redirect(url_for("lecture"))

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
    return redirect(url_for("lecture"))


@app.route("/edit_question/<int:q_id>", methods=["POST"])
def edit_question(q_id):
    email = session.get("email", "")
    df = load_csv(DATA_QUESTIONS, ["id", "title", "content", "email", "date"])
    if 0 <= q_id - 1 < len(df):
        row = df.iloc[q_id - 1]
        if row["email"] == email or email == get_professor_email():
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
        row = df.iloc[q_id - 1]
        if row["email"] == email or email == get_professor_email():
            df = df.drop(index=q_id - 1).reset_index(drop=True)
            save_csv(DATA_QUESTIONS, df)
            flash("질문이 삭제되었습니다.", "info")
    return redirect(url_for("lecture"))


# ───────────── Q&A 댓글 등록/수정/삭제 ─────────────
@app.route("/add_comment/<int:q_id>", methods=["POST"])
def add_comment(q_id):
    email = session.get("email", "")
    if not email:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for("login"))

    comment = request.form.get("comment", "").strip()
    if not comment:
        flash("댓글 내용을 입력해주세요.", "warning")
        return redirect(url_for("lecture"))

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
        row = df.iloc[c_idx]
        if row["email"] == email or email == get_professor_email():
            new_comment = request.form.get("edited_comment", "").strip()
            if new_comment:
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
        row = df.iloc[c_idx]
        if row["email"] == email or email == get_professor_email():
            df = df.drop(index=c_idx).reset_index(drop=True)
            save_csv(DATA_COMMENTS, df)
            flash("댓글이 삭제되었습니다.", "info")
    return redirect(url_for("lecture"))



# ───────────── 데이터 확인용 (교수 전용) ─────────────
@app.route("/check_data")
def check_data():
    email = session.get("email")

    # ✅ 로그인 여부 확인
    if not email:
        flash("🔒 로그인 후 이용 가능합니다.", "warning")
        return redirect(url_for("login"))

    # ✅ 교수 전용 접근 제한
    if email != get_professor_email():
        flash("🚫 접근 권한이 없습니다. 교수님 계정으로 로그인하세요.", "danger")
        return redirect(url_for("home"))

    # ✅ 데이터 디렉터리 탐색
    data_dir = "/data"
    file_info = []

    for root, _, files in os.walk(data_dir):
        for f in files:
            path = os.path.join(root, f)
            try:
                size_kb = round(os.path.getsize(path) / 1024, 2)
                mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
                rel_path = os.path.relpath(path, data_dir)
                file_info.append({"name": rel_path, "size": size_kb, "mtime": mtime})
            except:
                continue

    file_info = sorted(file_info, key=lambda x: x["name"])
    return render_template("check_data.html", files=file_info)



# ───────────── Health Check ─────────────
@app.route("/health")
def health():
    return "OK", 200


# ───────────── 앱 실행 ─────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"✅ Server running on port {port}")
    app.run(host="0.0.0.0", port=port)

