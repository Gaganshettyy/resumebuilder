from flask import Flask, render_template, request, redirect
import sqlite3
from flask import send_file
import pdfkit
import tempfile


app = Flask(__name__)
DB = "database.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/employee")
def manage_employees():
    conn = get_db()
    employees = conn.execute("SELECT * FROM employee").fetchall()
    conn.close()
    return render_template("Manage_employees.html", employees=employees)


@app.route("/employee/save", methods=["POST"])
def save_employee():
    data = request.form
    conn = get_db()
    cur = conn.cursor()

    if data["mode"] == "add":
        cur.execute("""
            INSERT INTO employee
            (full_name, email, phone, location, summary, skills)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["full_name"],
            data["email"],
            data["phone"],
            data["location"],
            data["summary"],
            data["skills"]
        ))
    elif data["mode"] == "edit":
        cur.execute("""
            UPDATE employee SET
            full_name=?, email=?, phone=?, location=?, summary=?, skills=?
            WHERE employee_id=?
        """, (
            data["full_name"],
            data["email"],
            data["phone"],
            data["location"],
            data["summary"],
            data["skills"],
            data["employee_id"]
        ))
    else:
        return redirect("/employee")
        


    conn.commit()
    conn.close()
    return redirect("/employee")


@app.route("/employee/delete/<int:emp_id>")
def delete_employee(emp_id):
    conn = get_db()
    conn.execute("DELETE FROM employee_project WHERE employee_id=?", (emp_id,))
    conn.execute("DELETE FROM employee WHERE employee_id=?", (emp_id,))
    conn.commit()
    conn.close()
    return redirect("/employee")

@app.route("/project")
def manage_projects():
    conn = get_db()
    projects = conn.execute("SELECT * FROM project").fetchall()
    conn.close()
    return render_template("Manage_projects.html", projects=projects)


@app.route("/project/save", methods=["POST"])
def save_project():
    data = request.form
    conn = get_db()
    cur = conn.cursor()

    if data["mode"] == "add":
        cur.execute("""
            INSERT INTO project (project_name, description)
            VALUES (?, ?)
        """, (
            data["project_name"],
            data["description"]
        ))
    else:
        cur.execute("""
            UPDATE project SET
            project_name=?, description=?
            WHERE project_id=?
        """, (
            data["project_name"],
            data["description"],
            data["project_id"]
        ))

    conn.commit()
    conn.close()
    return redirect("/project")


@app.route("/project/delete/<int:proj_id>")
def delete_project(proj_id):
    conn = get_db()
    conn.execute("DELETE FROM employee_project WHERE project_id=?", (proj_id,))
    conn.execute("DELETE FROM project WHERE project_id=?", (proj_id,))
    conn.commit()
    conn.close()
    return redirect("/project")

@app.route("/assignment")
def manage_assignments():
    conn = get_db()

    assignments = conn.execute("""
        SELECT e.employee_id AS emp_id,
               p.project_id AS proj_id,
               e.full_name,
               p.project_name
        FROM employee_project ep
        JOIN employee e ON e.employee_id = ep.employee_id
        JOIN project p ON p.project_id = ep.project_id
    """).fetchall()

    employees = conn.execute("SELECT employee_id, full_name FROM employee").fetchall()
    projects = conn.execute("SELECT project_id, project_name FROM project").fetchall()

    conn.close()

    return render_template(
        "Manage_assignments.html",
        assignments=assignments,
        employees=employees,
        projects=projects
    )


@app.route("/assignment/save", methods=["POST"])
def save_assignment():
    emp_id = request.form["employee_id"]
    proj_id = request.form["project_id"]

    conn = get_db()

    
    exists = conn.execute("""
        SELECT 1 FROM employee_project
        WHERE employee_id=? AND project_id=?
    """, (emp_id, proj_id)).fetchone()

    if not exists:
        conn.execute("""
            INSERT INTO employee_project (employee_id, project_id)
            VALUES (?, ?)
        """, (emp_id, proj_id))

    conn.commit()
    conn.close()

    return redirect("/assignment")


@app.route("/assignment/delete/<int:emp_id>/<int:proj_id>")
def delete_assignment(emp_id, proj_id):
    conn = get_db()
    conn.execute("""
        DELETE FROM employee_project
        WHERE employee_id=? AND project_id=?
    """, (emp_id, proj_id))
    conn.commit()
    conn.close()
    return redirect("/assignment")

@app.route("/resume", methods=["GET", "POST"])
def resume():
    if request.method == "GET":
        return render_template("search.html")

    query = request.form["query"]

    conn = get_db()
    cur = conn.cursor()

    emp = cur.execute("""
        SELECT * FROM employee
        WHERE employee_id = ? OR full_name LIKE ?
    """, (query, f"%{query}%")).fetchone()

    if not emp:
        conn.close()
        return "Employee not found", 404

    projects = cur.execute("""
        SELECT p.project_name, p.description
        FROM project p
        JOIN employee_project ep ON ep.project_id = p.project_id
        WHERE ep.employee_id = ?
    """, (emp["employee_id"],)).fetchall()

    conn.close()

    html = render_template("resume.html", employee=emp, projects=projects)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        pdfkit.from_string(html, f.name)
        return send_file(
            f.name,
            as_attachment=True,
            download_name=f"{emp['full_name']}_resume.pdf"
        )

if __name__ == "__main__":
    app.run(debug=True)
