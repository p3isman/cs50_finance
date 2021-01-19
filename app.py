from utils import *
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
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

# Database connection
db = SQL('sqlite:///finance.db')

# Custom filter
app.add_template_filter(usd)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route("/")
@login_required
def index():
    # Get owned stocks
    shares = db.execute("""SELECT symbol, SUM(shares) AS shares FROM transactions 
        WHERE user_id = :user_id GROUP BY symbol HAVING SUM(shares) > 0""",
        user_id=session["user_id"])

    return render_template("index.html", shares=shares, lookup=lookup)



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":

        symbol = request.form.get("quote")

        if lookup(symbol) is None:
            return apology("Can't find quote!")

        price = lookup(symbol)["price"]
        amount = int(request.form.get("amount"))
        rows = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
        cash = rows[0]["cash"]
       
        if (price * amount) > cash:
            return apology("Can't afford purchase!")
        elif amount < 1:
            return apology("Please enter a positive amount of shares!")
        else:
            cash -= price * amount
            # Update cash
            db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash=cash, id=session["user_id"])

            # Update history
            db.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (:user_id, :symbol, :shares, :price)", 
                user_id=session["user_id"], symbol=symbol, shares=amount, price=price)

            return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Must provide username", 403)

            # Ensure password was submitted
        elif not request.form.get("password"):
                return apology("Must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
            username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("Invalid username and/or password", 403)

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
    if request.method == "POST":
        quote = request.form.get("quote")
        response = lookup(quote)
        # Check if symbol exists
        if response:
            return render_template("show_quote.html", name=response['name'], 
                price=response['price'], symbol=response['symbol'])
        else:
            return apology("Quote does not exist!", 422)
    
    else: 
        return render_template("get_quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        rows = db.execute("SELECT username FROM users")

        # Username checking
        if len(username) < 4:
            return apology("Username must contain at least 4 characters!", 422)
        if check_for_duplicates("username", username, rows):
            return apology("Username already exists!")

        # Password checking
        elif request.form.get("password") != request.form.get("password2"):
            return apology("Passwords don't match!", 422)
        elif len(request.form.get("password")) < 4:
            return apology("Password must contain at least 4 characters", 422)

        else:
            password_hash = generate_password_hash(request.form.get("password"))
            db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", 
                username=username, hash=password_hash)
            return redirect("/")
            
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":

        symbol = request.form.get("quote")
        price = lookup(symbol)["price"]

        if not price or type(price) is not float:
            return apology("Can't find quote!")

        amount = int(request.form.get("amount"))
        rows = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
        cash = rows[0]["cash"]
       
        rows = db.execute("""SELECT SUM(shares) AS shares FROM transactions 
            WHERE symbol = :symbol AND user_id = :user_id""",
            symbol=symbol, user_id=session["user_id"])

        if amount > rows[0]["shares"]:
            return apology("You don't own enough shares!")
        elif amount < 1:
            return apology("Please enter a positive amount of shares!")
        else:
            cash += price * amount
            # Update cash
            db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash=cash, id=session["user_id"])

            # Update history
            db.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (:user_id, :symbol, :shares, :price)", 
                user_id=session["user_id"], symbol=symbol, shares = -1 * amount, price=price)

            return redirect("/")

    else:
        return render_template("sell.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
