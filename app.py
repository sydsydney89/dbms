"""
Flask app for the concert ticket manager project.
CSCE 45203 Spring 2026
"""
import os
import sqlite3
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, g

# Load .env when running locally; no-op if the file is absent (e.g. PythonAnywhere
# where env vars are set via the Web tab Environment Variables section).
load_dotenv()

app = Flask(__name__)

# SECRET_KEY must be set to a long random string in production.
app.secret_key = os.environ["SECRET_KEY"]

# DB_PATH defaults to concert.db beside this file so it works out-of-the-box
# and on PythonAnywhere without any extra config.
_default_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "concert.db")
DB_PATH = os.environ.get("DB_PATH") or _default_db

# Maximum allowed length for any single text input field.
_MAX_FIELD = 200

# Valid sort keys for concert_revenue - never interpolate user input directly.
_VALID_SORT = {"date", "revenue", "tickets"}


# --- db setup ---

def get_db():
    # reuse the same connection within a request
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv


def mutate(sql, args=()):
    db = get_db()
    db.execute(sql, args)
    db.commit()


# security headers on every response
@app.after_request
def set_security_headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self'; "
        "script-src 'none'; "
        "object-src 'none';"
    )
    return response


# error pages
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


# home page
@app.route("/")
def index():
    return render_template("index.html")


# --- function 1: add artist ---

@app.route("/add_artist", methods=["GET", "POST"])
def add_artist():
    if request.method == "POST":
        name  = request.form.get("name",  "").strip()[:_MAX_FIELD]
        genre = request.form.get("genre", "").strip()[:_MAX_FIELD]
        if not name or not genre:
            flash("Both fields are required.", "error")
        else:
            try:
                mutate("INSERT INTO Artist (ArtistName, Genre) VALUES (?, ?)", (name, genre))
                flash(f'Artist "{name}" added successfully.', "success")
                return redirect(url_for("add_artist"))
            except sqlite3.IntegrityError:
                flash(f'Artist "{name}" already exists.', "error")
    return render_template("add_artist.html")


# --- function 2: add concert ---

@app.route("/add_concert", methods=["GET", "POST"])
def add_concert():
    artists = query("SELECT ArtistId, ArtistName FROM Artist ORDER BY ArtistName")
    if request.method == "POST":
        venue     = request.form.get("venue",     "").strip()[:_MAX_FIELD]
        city      = request.form.get("city",      "").strip()[:_MAX_FIELD]
        date      = request.form.get("date",      "").strip()[:20]
        artist_id = request.form.get("artist_id", "").strip()[:10]
        if not all([venue, city, date, artist_id]):
            flash("All fields are required.", "error")
        else:
            mutate(
                "INSERT INTO Concert (VenueName, City, ConcertDate, ArtistId) VALUES (?, ?, ?, ?)",
                (venue, city, date, artist_id),
            )
            flash("Concert added successfully.", "success")
            return redirect(url_for("add_concert"))
    return render_template("add_concert.html", artists=artists)


# --- function 3: add customer ---

@app.route("/add_customer", methods=["GET", "POST"])
def add_customer():
    if request.method == "POST":
        name = request.form.get("name", "").strip()[:_MAX_FIELD]
        if not name:
            flash("Customer name is required.", "error")
        else:
            mutate("INSERT INTO Customer (CustomerName) VALUES (?)", (name,))
            flash(f'Customer "{name}" added successfully.', "success")
            return redirect(url_for("add_customer"))
    return render_template("add_customer.html")


# --- function 4: add ticket ---

@app.route("/add_ticket", methods=["GET", "POST"])
def add_ticket():
    concerts  = query("SELECT ConcertId, VenueName, City, ConcertDate FROM Concert ORDER BY ConcertDate")
    customers = query("SELECT CustomerId, CustomerName FROM Customer ORDER BY CustomerName")
    if request.method == "POST":
        concert_id  = request.form.get("concert_id",  "").strip()[:10]
        customer_id = request.form.get("customer_id", "").strip()[:10]
        seat        = request.form.get("seat",        "").strip()[:20]
        price       = request.form.get("price",       "").strip()[:20]
        if not all([concert_id, customer_id, seat, price]):
            flash("All fields are required.", "error")
        else:
            try:
                price_val = float(price)
                if price_val < 0:
                    raise ValueError
                mutate(
                    "INSERT INTO Ticket (ConcertId, CustomerId, SeatNumber, Price) VALUES (?, ?, ?, ?)",
                    (concert_id, customer_id, seat, price_val),
                )
                flash("Ticket added successfully.", "success")
                return redirect(url_for("add_ticket"))
            except ValueError:
                flash("Price must be a non-negative number.", "error")
    return render_template("add_ticket.html", concerts=concerts, customers=customers)


# --- function 5: view concerts, optional city filter ---

@app.route("/view_concerts")
def view_concerts():
    cities  = [r["City"] for r in query("SELECT DISTINCT City FROM Concert ORDER BY City")]
    selected_city = request.args.get("city", "")
    if selected_city:
        concerts = query(
            "SELECT c.ConcertId, c.VenueName, c.City, c.ConcertDate, a.ArtistName "
            "FROM Concert c JOIN Artist a ON c.ArtistId = a.ArtistId "
            "WHERE c.City = ? ORDER BY c.ConcertDate",
            (selected_city,),
        )
    else:
        concerts = query(
            "SELECT c.ConcertId, c.VenueName, c.City, c.ConcertDate, a.ArtistName "
            "FROM Concert c JOIN Artist a ON c.ArtistId = a.ArtistId "
            "ORDER BY c.ConcertDate"
        )
    return render_template("view_concerts.html", concerts=concerts, cities=cities, selected_city=selected_city)


# --- function 6: concerts by artist (join) ---

@app.route("/concerts_by_artist")
def concerts_by_artist():
    artists = query("SELECT ArtistId, ArtistName FROM Artist ORDER BY ArtistName")
    selected_id = request.args.get("artist_id", "")
    concerts = []
    selected_name = ""
    if selected_id:
        concerts = query(
            "SELECT a.ArtistName, c.VenueName, c.City, c.ConcertDate "
            "FROM Concert c JOIN Artist a ON c.ArtistId = a.ArtistId "
            "WHERE a.ArtistId = ? ORDER BY c.ConcertDate",
            (selected_id,),
        )
        row = query("SELECT ArtistName FROM Artist WHERE ArtistId = ?", (selected_id,), one=True)
        selected_name = row["ArtistName"] if row else ""
    return render_template(
        "concerts_by_artist.html",
        artists=artists,
        concerts=concerts,
        selected_id=selected_id,
        selected_name=selected_name,
    )


# --- function 7: total spending per customer ---

@app.route("/customer_spending")
def customer_spending():
    customers   = query("SELECT CustomerId, CustomerName FROM Customer ORDER BY CustomerName")
    selected_id = request.args.get("customer_id", "")
    if selected_id:
        results = query(
            "SELECT cu.CustomerId, cu.CustomerName, COALESCE(SUM(t.Price), 0) AS TotalSpent "
            "FROM Customer cu LEFT JOIN Ticket t ON cu.CustomerId = t.CustomerId "
            "WHERE cu.CustomerId = ? "
            "GROUP BY cu.CustomerId, cu.CustomerName",
            (selected_id,),
        )
    else:
        results = query(
            "SELECT cu.CustomerId, cu.CustomerName, COALESCE(SUM(t.Price), 0) AS TotalSpent "
            "FROM Customer cu LEFT JOIN Ticket t ON cu.CustomerId = t.CustomerId "
            "GROUP BY cu.CustomerId, cu.CustomerName "
            "ORDER BY TotalSpent DESC"
        )
    return render_template("customer_spending.html", results=results, customers=customers, selected_id=selected_id)


# --- function 8: top 3 artists by revenue ---

@app.route("/top_artists")
def top_artists():
    results = query(
        "SELECT a.ArtistName, COALESCE(SUM(t.Price), 0) AS TotalRevenue "
        "FROM Artist a "
        "LEFT JOIN Concert c  ON a.ArtistId  = c.ArtistId "
        "LEFT JOIN Ticket  t  ON c.ConcertId = t.ConcertId "
        "GROUP BY a.ArtistId, a.ArtistName "
        "ORDER BY TotalRevenue DESC "
        "LIMIT 3"
    )
    return render_template("top_artists.html", results=results)


# --- bonus: per-concert revenue report ---

@app.route("/concert_revenue")
def concert_revenue():
    genres = [r["Genre"] for r in query("SELECT DISTINCT Genre FROM Artist ORDER BY Genre")]
    selected_genre = request.args.get("genre", "")
    sort = request.args.get("sort", "date")  # date | revenue | tickets

    # make sure sort param is one we expect before putting it in SQL
    if sort not in _VALID_SORT:
        sort = "date"
    order_map = {
        "revenue": "TotalRevenue DESC",
        "tickets": "TicketsSold DESC",
        "date":    "c.ConcertDate ASC",
    }
    order_clause = order_map[sort]

    base_sql = (
        "SELECT a.ArtistName, a.Genre, c.VenueName, c.City, c.ConcertDate, "
        "COUNT(t.TicketId) AS TicketsSold, "
        "COALESCE(SUM(t.Price), 0) AS TotalRevenue "
        "FROM Concert c "
        "JOIN Artist a ON c.ArtistId = a.ArtistId "
        "LEFT JOIN Ticket t ON c.ConcertId = t.ConcertId "
    )

    if selected_genre:
        results = query(
            base_sql + "WHERE a.Genre = ? GROUP BY c.ConcertId ORDER BY " + order_clause,
            (selected_genre,),
        )
    else:
        results = query(base_sql + "GROUP BY c.ConcertId ORDER BY " + order_clause)

    # Summary aggregates across the filtered result set
    total_revenue = sum(r["TotalRevenue"] for r in results)
    total_tickets = sum(r["TicketsSold"] for r in results)

    return render_template(
        "concert_revenue.html",
        results=results,
        genres=genres,
        selected_genre=selected_genre,
        sort=sort,
        total_revenue=total_revenue,
        total_tickets=total_tickets,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
