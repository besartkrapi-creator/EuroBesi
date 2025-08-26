from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "sekreti_eurobesi"
DB_NAME = "database.db"

# ==========================
# Funksionet për databazën
# ==========================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # tabela users
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    # tabela projects
    c.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)
    # tabela expenses
    c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            description TEXT,
            amount REAL,
            user_id INTEGER,
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    # tabela reports
    c.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            content TEXT,
            user_id INTEGER,
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


def create_default_admin():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", ("admin",))
    if not c.fetchone():
        hashed_pw = generate_password_hash("admin123")
        c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)",
                  ("admin", hashed_pw, "admin"))
        conn.commit()
    conn.close()


# ==========================
# Routes
# ==========================
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
        else:
            return "⚠️ Kredencialet janë gabim"

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        hashed_pw = generate_password_hash(password)
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)",
                      (username, hashed_pw, role))
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except:
            return "⚠️ Ky username ekziston!"

    return render_template("register.html")


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


@app.route("/project/<int:project_id>", methods=["GET", "POST"])
def project_detail(project_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM projects WHERE id=?", (project_id,))
    project = c.fetchone()

    c.execute("SELECT * FROM expenses WHERE project_id=?", (project_id,))
    expenses = c.fetchall()

    c.execute("SELECT * FROM reports WHERE project_id=?", (project_id,))
    reports = c.fetchall()

    # llogarit totalin e shpenzimeve
    total = sum([e["amount"] for e in expenses]) if expenses else 0

    conn.close()
    return render_template("project_detail.html",
                           project=project,
                           expenses=expenses,
                           reports=reports,
                           total=total)


@app.route("/project/<int:project_id>/expense", methods=["POST"])
def add_expense(project_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    description = request.form["description"]
    amount = float(request.form["amount"])

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO expenses (project_id, description, amount, user_id) VALUES (?,?,?,?)",
              (project_id, description, amount, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/project/<int:project_id>/report", methods=["POST"])
def add_report(project_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    content = request.form["content"]

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO reports (project_id, content, user_id) VALUES (?,?,?)",
              (project_id, content, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/add_project", methods=["POST"])
def add_project():
    if "user_id" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    name = request.form["name"]
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO projects (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ==========================
# Run / Deploy
# ==========================
if __name__ == "__main__":
    init_db()
    create_default_admin()
    app.run(debug=True)

# Ky bllok siguron që databaza dhe admini default të krijohen edhe në Render
with app.app_context():
    init_db()
    create_default_admin()
