from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os

app = Flask(__name__)
app.secret_key = "sekreti_eurobesi"
DB_NAME = "database.db"
@app.before_request
def initialize():
    if not hasattr(app, "db_initialized"):
        init_db()
        create_default_admin()
        app.db_initialized = True

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, description TEXT, amount REAL, user_id INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, content TEXT, user_id INTEGER)")
    conn.commit()
    conn.close()

def create_default_admin():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", ("admin",))
    if not c.fetchone():
        hashed_pw = generate_password_hash("admin123")
        c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)", ("admin", hashed_pw, "admin"))
        conn.commit()
    conn.close()

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            session["username"] = user[1]
            session["role"] = user[3]
            return redirect(url_for("dashboard"))
        return "⚠️ Kredencialet janë gabim"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM projects")
    projects = c.fetchall()
    conn.close()
    return render_template("dashboard.html", projects=projects, role=session["role"])

@app.route("/add_project", methods=["POST"])
def add_project():
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))
    name = request.form["name"]
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO projects (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/add_user", methods=["POST"])
def add_user():
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))
    username = request.form["username"]
    password = request.form["password"]
    role = request.form["role"]
    hashed_pw = generate_password_hash(password)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)", (username, hashed_pw, role))
        conn.commit()
    except:
        conn.close()
        return "⚠️ Ky përdorues ekziston!"
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/project/<int:project_id>")
def project_detail(project_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM projects WHERE id=?", (project_id,))
    project = c.fetchone()
    if session["role"] == "admin":
        c.execute("SELECT e.*, u.username FROM expenses e JOIN users u ON e.user_id=u.id WHERE project_id=?", (project_id,))
        expenses = c.fetchall()
        c.execute("SELECT r.*, u.username FROM reports r JOIN users u ON r.user_id=u.id WHERE project_id=?", (project_id,))
        reports = c.fetchall()
    else:
        c.execute("SELECT e.*, u.username FROM expenses e JOIN users u ON e.user_id=u.id WHERE project_id=? AND user_id=?", (project_id, session["user_id"]))
        expenses = c.fetchall()
        c.execute("SELECT r.*, u.username FROM reports r JOIN users u ON r.user_id=u.id WHERE project_id=? AND user_id=?", (project_id, session["user_id"]))
        reports = c.fetchall()
    total = sum([e["amount"] for e in expenses]) if expenses else 0
    conn.close()
    return render_template("project_detail.html", project=project, expenses=expenses, reports=reports, total=total)

@app.route("/project/<int:project_id>/expense", methods=["POST"])
def add_expense(project_id):
    description = request.form["description"]
    amount = float(request.form["amount"])
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO expenses (project_id, description, amount, user_id) VALUES (?,?,?,?)", (project_id, description, amount, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect(url_for("project_detail", project_id=project_id))

@app.route("/project/<int:project_id>/report", methods=["POST"])
def add_report(project_id):
    content = request.form["content"]
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO reports (project_id, content, user_id) VALUES (?,?,?)", (project_id, content, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect(url_for("project_detail", project_id=project_id))

@app.route("/export_excel/<int:project_id>")
def export_excel(project_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT description, amount FROM expenses WHERE project_id=?", (project_id,))
    data = c.fetchall()
    conn.close()
    df = pd.DataFrame(data, columns=["Përshkrimi", "Shuma"])
    file_path = f"project_{project_id}_raport.xlsx"
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)

@app.route("/export_pdf/<int:project_id>")
def export_pdf(project_id):
    file_path = f"project_{project_id}_raport.pdf"
    c = canvas.Canvas(file_path, pagesize=A4)
    if os.path.exists("static/logo.png"):
        c.drawImage("static/logo.png", 40, 750, width=100, height=50)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, 800, "Raport Projekti – EuroBesi")
    y = 730
    conn = sqlite3.connect(DB_NAME)
    c_db = conn.cursor()
    c_db.execute("SELECT description, amount FROM expenses WHERE project_id=?", (project_id,))
    for row in c_db.fetchall():
        c.setFont("Helvetica", 12)
        c.drawString(100, y, f"{row[0]} - {row[1]} EUR")
        y -= 20
    conn.close()
    c.save()
    return send_file(file_path, as_attachment=True)

if __name__ == "__main__":
    init_db()
    create_default_admin()
    app.run(debug=True)
