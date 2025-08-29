from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3, os
import pandas as pd
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "sekreti_eurobesi"
DB_NAME = "database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, name TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, project_id INTEGER, description TEXT, amount REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY, project_id INTEGER, report_text TEXT)")
    conn.commit()
    conn.close()

@app.before_request
def initialize():
    if not hasattr(app, "db_initialized"):
        init_db()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (username,password,role) VALUES (?,?,?)", ("admin","admin","admin"))
        conn.commit()
        conn.close()
        app.db_initialized = True

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        username=request.form["username"]
        password=request.form["password"]
        conn=sqlite3.connect(DB_NAME)
        c=conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?",(username,password))
        user=c.fetchone()
        conn.close()
        if user:
            session["user"]=user[1]
            session["role"]=user[3]
            return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session: return redirect(url_for("login"))
    conn=sqlite3.connect(DB_NAME)
    c=conn.cursor()
    c.execute("SELECT * FROM projects")
    projects=c.fetchall()
    conn.close()
    return render_template("dashboard.html", projects=projects, role=session["role"])

@app.route("/add_project", methods=["POST"])
def add_project():
    if session.get("role")!="admin": return redirect(url_for("dashboard"))
    name=request.form["name"]
    conn=sqlite3.connect(DB_NAME)
    c=conn.cursor()
    c.execute("INSERT INTO projects (name) VALUES (?)",(name,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/project/<int:project_id>")
def project_detail(project_id):
    if "user" not in session: return redirect(url_for("login"))
    conn=sqlite3.connect(DB_NAME)
    c=conn.cursor()
    c.execute("SELECT * FROM expenses WHERE project_id=?",(project_id,))
    expenses=c.fetchall()
    c.execute("SELECT * FROM reports WHERE project_id=?",(project_id,))
    reports=c.fetchall()
    conn.close()
    total=sum([e[3] for e in expenses]) if expenses else 0
    return render_template("project_detail.html", expenses=expenses, reports=reports, project_id=project_id, total=total)

@app.route("/add_expense/<int:project_id>", methods=["POST"])
def add_expense(project_id):
    desc=request.form["description"]
    amount=float(request.form["amount"])
    conn=sqlite3.connect(DB_NAME)
    c=conn.cursor()
    c.execute("INSERT INTO expenses (project_id,description,amount) VALUES (?,?,?)",(project_id,desc,amount))
    conn.commit()
    conn.close()
    return redirect(url_for("project_detail", project_id=project_id))

@app.route("/add_report/<int:project_id>", methods=["POST"])
def add_report(project_id):
    text=request.form["report"]
    conn=sqlite3.connect(DB_NAME)
    c=conn.cursor()
    c.execute("INSERT INTO reports (project_id,report_text) VALUES (?,?)",(project_id,text))
    conn.commit()
    conn.close()
    return redirect(url_for("project_detail", project_id=project_id))

@app.route("/export_excel/<int:project_id>")
def export_excel(project_id):
    conn=sqlite3.connect(DB_NAME)
    df=pd.read_sql_query("SELECT description,amount FROM expenses WHERE project_id=?",conn,params=(project_id,))
    conn.close()
    file_path=f"expenses_{project_id}.xlsx"
    df.to_excel(file_path,index=False)
    return send_file(file_path, as_attachment=True)

@app.route("/export_pdf/<int:project_id>")
def export_pdf(project_id):
    conn=sqlite3.connect(DB_NAME)
    c=conn.cursor()
    c.execute("SELECT description,amount FROM expenses WHERE project_id=?",(project_id,))
    data=c.fetchall()
    conn.close()
    file_path=f"report_{project_id}.pdf"
    cpdf=canvas.Canvas(file_path)
    cpdf.drawString(200,800,"EuroBesi Raport")
    y=750
    for d in data:
        cpdf.drawString(100,y,f"{d[0]} - {d[1]} EUR")
        y-=20
    cpdf.save()
    return send_file(file_path, as_attachment=True)

if __name__=="__main__":
    app.run(debug=True)
