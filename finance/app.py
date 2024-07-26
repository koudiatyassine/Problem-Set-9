import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]
    rows = db.execute("""
        SELECT symbol, SUM(shares) AS shares
        FROM "transaction"
        WHERE user_id = ?
        GROUP BY symbol
    """, user_id)

    portfolio = []
    total_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]

    for row in rows:
        symbol = row["symbol"]
        shares = row["shares"]
        quote = lookup(symbol)
        if quote:
            price = quote["price"]
            total_value = shares * price
            portfolio.append({
                "symbol": symbol,
                "shares": shares,
                "price": price,
                "total": total_value
            })

    return render_template("index.html", portfolio=portfolio, cash=total_cash)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        shares = int(request.form.get("shares"))

        if not symbol or shares <= 0:
            return apology("Invalid symbol or number of shares", 400)

        quote = lookup(symbol)
        if quote is None:
            return apology("Invalid symbol", 400)

        price = quote["price"]
        total_cost = price * shares
        user_id = session["user_id"]
        cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]

        if total_cost > cash:
            return apology("Not enough cash", 400)

        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", total_cost, user_id)
        db.execute("""
            INSERT INTO "transaction" (user_id, symbol, shares, price)
            VALUES (?, ?, ?, ?)
        """, user_id, symbol, shares, price)

        flash("Bought!")
        return redirect("/")

    else:
        return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]
    rows = db.execute("""
        SELECT symbol, shares, price, transacted
        FROM "transaction"
        WHERE user_id = ?
        ORDER BY transacted DESC
    """, user_id)

    return render_template("history.html", transactions=rows)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            return apology("must provide username and/or password", 403)

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("invalid username and/or password", 403)

        session["user_id"] = rows[0]["id"]

        return redirect("/")

    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/")

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        if not symbol:
            return apology("Must provide symbol", 400)

        quote = lookup(symbol)
        if quote is None:
            return apology("Invalid symbol", 400)

        return render_template("quote.html", quote=quote)

    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or not confirmation:
            return apology("Must provide username and/or password", 400)

        if password != confirmation:
            return apology("Passwords do not match", 400)

        hash = generate_password_hash(password)

        try:
            db.execute("""
                INSERT INTO users (username, hash)
                VALUES (?, ?)
            """, username, hash)
        except:
            return apology("Username already taken", 400)

        session["user_id"] = db.execute("SELECT id FROM users WHERE username = ?", username)[0]["id"]

        return redirect("/")

    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        shares = int(request.form.get("shares"))

        if not symbol or shares <= 0:
            return apology("Invalid symbol or number of shares", 400)

        rows = db.execute("""
            SELECT shares
            FROM "transaction"
            WHERE user_id = ? AND symbol = ?
            ORDER BY transacted DESC
        """, session["user_id"], symbol)

        total_shares = sum(row["shares"] for row in rows)

        if shares > total_shares:
            return apology("Too many shares", 400)

        quote = lookup(symbol)
        if quote is None:
            return apology("Invalid symbol", 400)

        price = quote["price"]
        total_value = shares * price

        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", total_value, session["user_id"])
        db.execute("""
            INSERT INTO "transaction" (user_id, symbol, shares, price)
            VALUES (?, ?, ?, ?)
        """, session["user_id"], symbol, -shares, price)

        flash("Sold!")
        return redirect("/")

    else:
        symbols = db.execute("""
            SELECT symbol
            FROM "transaction"
            WHERE user_id = ?
            GROUP BY symbol
        """, session["user_id"])

        return render_template("sell.html", symbols=[row["symbol"] for row in symbols])

if __name__ == "__main__":
    app.run(debug=True)
