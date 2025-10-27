# -*- coding: utf-8 -*-
"""
📘 연암공대 화공트랙 강의자료 + Q&A (교수 답변 수정 기능 포함)
- 학생: 자기 비밀번호(4자리)로 질문 삭제 가능
- 교수: 비밀번호 기본값 5555 (변경 가능)
"""

from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "key_flask_secret"

DATA_FILE = "lecture_data.csv"
QNA_FILE = "lecture_qna.csv"
PROFESSOR_PASSWORD = "5555"


# ✅ Render Health Check용 별도 라우트 (중복 방지)
@app.route("/health")
def health_check():
    return "✅ Flask app deployed successfully on Render!"


# ─────────────────────────────
# 📂 데이터 로드/저장
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


# ─────────────────────────────
# 📘 강의자료 + Q&A 게시판
# ─────────────────────────────
@app.route("/lecture", methods=["GET", "POST"])
def lecture_list():
    data = load_data()
    qna_df = load_qna()
    wrong_pw_index = None
    temp_reply = ""

    if request.method == "POST":
        action = request.form.get("action")

        # 🧑‍🎓 학생 질문 등록
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

        # 🧑‍🎓 학생 질문 삭제
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

        # 👨‍🏫 교수 답변 등록 / 수정 (통합)
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


# ✅ 기본 홈페이지 (index.html 렌더링)
@app.route("/")
def home():
    return render_template("index.html")


# ─────────────────────────────
# 📤 강의자료 업로드 페이지
# ─────────────────────────────
@app.route("/lecture_upload", methods=["GET", "POST"])
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
# 📘 강의자료 업로드 (upload_lecture.html 렌더링)
# ─────────────────────────────
@app.route("/upload_lecture", methods=["GET", "POST"])
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
            if key == "file_upload" or key.startswith("file_upload"):
                file_urls.append(request.form[key])
            if key == "related_site" or key.startswith("related_site"):
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


if __name__ == "__main__":
    app.run(debug=True)
