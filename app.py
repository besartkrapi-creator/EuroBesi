from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3, os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "sekret_shume_i_sigurt"

DB_NAME = "database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    user_id INTEGER,
                    description TEXT,
                    amount REAL,
                    FOREIGN KEY(project_id) REFERENCES projects(id),
                    FOREIGN KEY(user_id) REFERENCES users(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    user_id INTEGER,
                    content TEXT,
                    FOREIGN KEY(project_id) REFERENCES projects(id),
                    FOREIGN KEY(user_id) REFERENCES users(id))""")
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        role = request.form["role"]
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)",
                         (username, password, role))
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except:
            return "Gabim: Përdoruesi ekziston!"
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    if session["role"] == "admin":
        projects = conn.execute("SELECT * FROM projects").fetchall()
    else:
        projects = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()
    return render_template("dashboard.html", projects=projects, role=session["role"])

@app.route("/add_project", methods=["POST"])
def add_project():
    if session.get("role") == "admin":
        name = request.form["name"]
        conn = get_db()
        conn.execute("INSERT INTO projects (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
    return redirect(url_for("dashboard"))

@app.route("/project/<int:project_id>")
def project_detail(project_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    project = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    expenses = conn.execute("SELECT * FROM expenses WHERE project_id=?", (project_id,)).fetchall()
    reports = conn.execute("SELECT * FROM reports WHERE project_id=?", (project_id,)).fetchall()
    total = conn.execute("SELECT SUM(amount) as total FROM expenses WHERE project_id=?", (project_id,)).fetchone()["total"]
    conn.close()
    return render_template("project_detail.html", project=project, expenses=expenses, reports=reports, total=total)

@app.route("/add_expense/<int:project_id>", methods=["POST"])
def add_expense(project_id):
    desc = request.form["description"]
    amount = float(request.form["amount"])
    conn = get_db()
    conn.execute("INSERT INTO expenses (project_id, user_id, description, amount) VALUES (?,?,?,?)",
                 (project_id, session["user_id"], desc, amount))
    conn.commit()
    conn.close()
    return redirect(url_for("project_detail", project_id=project_id))

@app.route("/add_report/<int:project_id>", methods=["POST"])
def add_report(project_id):
    content = request.form["content"]
    conn = get_db()
    conn.execute("INSERT INTO reports (project_id, user_id, content) VALUES (?,?,?)",
                 (project_id, session["user_id"], content))
    conn.commit()
    conn.close()
    return redirect(url_for("project_detail", project_id=project_id))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
