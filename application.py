import os
import datetime

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL(os.getenv("postgres://nzceofjjspnwpz:ecf64a0b2bbcf37f14ad71d4de273d4e78eed42073a985b97fbbbbe7184a8a8e@ec2-63-32-7-190.eu-west-1.compute.amazonaws.com:5432/d727tha8209cvm"))

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    funds = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
    rows = db.execute("SELECT * FROM user_stocks WHERE id = ?", session["user_id"])
    cash = funds[0]['cash']
    current_value = {}
    stock_value = {}
    a = 0
    total = cash
    loops = len(rows)
    for row in rows:
        symbol = lookup(rows[a]['symbol'])
        current_value[a] = symbol['price']*rows[a]['quantity']
        stock_value[a] = symbol['price']
        total = total + current_value[a]
        a += 1
    return render_template('index.html', rows=rows, cash=cash, current_value=current_value, stock_value=stock_value, loops=loops, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Enter a stock symbol")
        symbol = request.form.get("symbol")
        if lookup(symbol) == None:
            return apology("The stock symbol '" + symbol + "' does not exist")
        if request.form.get("shares") == '':
            return apology("Enter a number of stocks to buy")
        if request.form.get("shares").isdecimal() == False:
            return apology("You can only enter positive whole numbers here")
        else:
            transaction = "buy"
            stock = lookup(request.form.get("symbol"))
            purchase = float(stock["price"])*float(request.form.get("shares"))
            funds = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
            if funds[0]['cash'] < purchase:
                return apology("You don't have enough cash!")
            else:
                new_balance = funds[0]['cash'] - purchase
                current_time = datetime.datetime.now()
                db.execute("INSERT INTO user_history (id, stocks, symbol, quantity, price, time, type) VALUES (?,?,?,?,?,?,?)",
                           session["user_id"], stock['name'], stock['symbol'], request.form.get("shares"), stock['price'], current_time, transaction)
                db.execute("UPDATE users SET cash = ? WHERE id = ?", new_balance, session["user_id"])
                current_quantity = db.execute(
                    "SELECT quantity FROM user_stocks WHERE id = ? AND symbol = ?", session["user_id"], stock["symbol"])
                if current_quantity == []:
                    db.execute("INSERT INTO user_stocks (id, stocks, symbol, quantity) VALUES (?,?,?,?)",
                               session["user_id"], stock['name'], stock['symbol'], request.form.get("shares"))
                else:
                    new_quantity = int(current_quantity[0]['quantity']) + int(request.form.get("shares"))
                    db.execute("UPDATE user_stocks SET quantity = ? WHERE id = ? AND symbol = ?",
                               new_quantity, session["user_id"], stock["symbol"])
                return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    funds = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
    rows = db.execute("SELECT * FROM user_history WHERE id = ?", session["user_id"])
    cash = funds[0]['cash']
    price = {}
    quantity = {}
    total_value = {}
    stock_value = {}
    sales = 0
    buys = 0
    a = 0
    loops = len(rows)
    for row in rows:
        price[a] = rows[a]['price']
        quantity[a] = rows[a]['quantity']
        total_value[a] = price[a]*quantity[a]
        if rows[a]['type'] == 'buy':
            buys = buys + total_value[a]
        if rows[a]['type'] == 'sale':
            sales = sales + total_value[a]
        a += 1
    return render_template('history.html', rows=rows, cash=cash, total_value=total_value, loops=loops, buys=buys, sales=sales)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Enter a stock symbol")
        symbol = request.form.get("symbol")
        if lookup(symbol) == None:
            return apology("The stock symbol '" + symbol + "' does not exist")
        if lookup(symbol) != None:
            return render_template("quoted.html", name=lookup(symbol)["name"], price=lookup(symbol)["price"], symbol=lookup(symbol)["symbol"])
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        if not request.form.get("password"):
            return apology("must provide password")

        # Ensure confirmation password was submitted
        elif not request.form.get("confirmation"):
            return apology("must confirm password")

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        if len(rows) == 1:
            return apology("The username '" + request.form.get("username") + "' is already taken")
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords do not match")

        db.execute("INSERT INTO users (username, hash) VALUES (?,?)", request.form.get(
            "username"), generate_password_hash(request.form.get("password")))
        return render_template("registered.html")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Enter a stock symbol")
        symbol = request.form.get("symbol")
        if lookup(symbol) == None:
            return apology("The stock symbol '" + symbol + "' does not exist")
        if request.form.get("shares") == '':
            return apology("Enter a number of stocks to sell")
        if request.form.get("shares").isdecimal() == False:
            return apology("You can only enter positive whole numbers here")
        else:
            transaction = "sale"
            stock = lookup(request.form.get("symbol"))
            funds = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
            quantity = db.execute("SELECT quantity FROM user_stocks WHERE symbol = ? AND id = ?",
                                  stock['symbol'], session["user_id"])
            if len(quantity) == 0:
                return apology("You don't have any of these stocks")
            sale = float(stock["price"])*float(request.form.get("shares"))
            if int(request.form.get("shares")) > int(quantity[0]['quantity']):
                return apology("You do not have that many " + request.form.get("symbol") + " stocks.")
            else:
                new_balance = funds[0]['cash'] + sale
                current_time = datetime.datetime.now()
                new_quantity = int(quantity[0]['quantity']) - int(request.form.get("shares"))
                db.execute("INSERT INTO user_history (id, stocks, symbol, quantity, price, time, type) VALUES (?,?,?,?,?,?,?)",
                           session["user_id"], stock['name'], stock['symbol'], request.form.get("shares"), stock['price'], current_time, transaction)
                db.execute("UPDATE users SET cash = ? WHERE id = ?", new_balance, session["user_id"])
                if new_quantity > 0:
                    db.execute("UPDATE user_stocks SET quantity = ? WHERE id = ? AND symbol = ?",
                               new_quantity, session["user_id"], stock['symbol'])
                else:
                    db.execute("DELETE FROM user_stocks WHERE id = ? AND symbol = ?", session["user_id"], stock['symbol'])
                return redirect("/")

    else:
        shares = db.execute("SELECT symbol FROM user_stocks WHERE id = ?", session["user_id"])
        total_shares = len(shares)
        return render_template('sell.html', shares=shares, total_shares=total_shares)


@app.route("/account")
@login_required
def account():
    return render_template('account.html')


@app.route("/password_change", methods=["GET", "POST"])
@login_required
def password_change():
    if request.method == "POST":
        if not request.form.get('old_password'):
            return apology("Type in your old password")
        if not request.form.get('password'):
            return apology("Type in a new password")
        if not request.form.get('confirmation'):
            return apology("Confirm your password")
        rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        if not check_password_hash(rows[0]["hash"], request.form.get("old_password")):
            return apology("invalid password")
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("New passwords do not match")
        db.execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(
            request.form.get("password")), session["user_id"])
        return redirect("/")
    else:
        return render_template("password_change.html")


@app.route("/add_cash", methods=["GET", "POST"])
@login_required
def add_cash():
    if request.method == "POST":
        if not request.form.get('amount'):
            return apology("Type in an amount to add")
        balance = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        new_balance = float(balance[0]['cash']) + float(request.form.get('amount'))
        db.execute("UPDATE users SET cash = ? WHERE id = ?", new_balance, session["user_id"])
        return redirect("/")
    else:
        balance = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        return render_template("add_cash.html", balance=balance[0]['cash'])


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
