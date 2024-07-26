import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///birthdays.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Access form data
        name = request.form.get("name")
        month = request.form.get("month")
        day = request.form.get("day")

        # Ensure all fields are provided
        if not name or not month or not day:
            return redirect("/error")

        # Convert month and day to integers and validate
        try:
            month = int(month)
            day = int(day)
        except ValueError:
            return redirect("/error")

        if month < 1 or month > 12 or day < 1 or day > 31:
            return redirect("/error")

        # Insert data into database
        db.execute("INSERT INTO birthdays (name, month, day) VALUES(?, ?, ?)", name, month, day)

        return redirect("/")

    else:
        # Query for all birthdays
        birthdays = db.execute("SELECT * FROM birthdays")

        # Render birthdays page
        return render_template("index.html", birthdays=birthdays)

@app.route("/delete", methods=["POST"])
def delete():
    birthday_id = request.form.get("id")
    db.execute("DELETE FROM birthdays WHERE id = ?", birthday_id)
    return redirect("/")

@app.route("/error")
def error():
    return render_template("error.html")

if __name__ == "__main__":
    app.run(debug=True)
