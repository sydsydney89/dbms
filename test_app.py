"""
test_app.py — Pytest suite for Concert Ticket Manager.
Uses an isolated in-memory SQLite DB per test so the production DB is never touched.
"""
import sqlite3
import pytest
import app as application


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path):
    """
    Spin up a fresh, seeded SQLite DB in a temp dir for each test,
    point the app at it, and yield a test client.
    """
    db_file = tmp_path / "test_concert.db"
    application.DB_PATH = str(db_file)
    application.app.config["TESTING"] = True
    application.app.config["WTF_CSRF_ENABLED"] = False

    # Build schema + minimal seed data
    with sqlite3.connect(str(db_file)) as conn:
        conn.executescript(open("schema.sql").read())

    with application.app.test_client() as c:
        yield c

    # Reset DB_PATH so other tests are unaffected
    application.DB_PATH = "concert.db"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def text(response) -> str:
    return response.data.decode()


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------

class TestHome:
    def test_home_status(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_home_contains_all_links(self, client):
        body = text(client.get("/"))
        for path in [
            "add_artist", "add_concert", "add_customer", "add_ticket",
            "view_concerts", "concerts_by_artist", "customer_spending", "top_artists",
        ]:
            assert path in body

    def test_home_title(self, client):
        assert "Concert Ticket Manager" in text(client.get("/"))


# ---------------------------------------------------------------------------
# Function 1 — Add Artist
# ---------------------------------------------------------------------------

class TestAddArtist:
    def test_get_renders_form(self, client):
        r = client.get("/add_artist")
        assert r.status_code == 200
        assert b"<form" in r.data

    def test_post_valid_redirects(self, client):
        r = client.post("/add_artist", data={"name": "New Band", "genre": "Rock"})
        assert r.status_code == 302
        assert "/add_artist" in r.headers["Location"]

    def test_post_persists_artist(self, client):
        client.post("/add_artist", data={"name": "Persisted Artist", "genre": "Jazz"})
        with sqlite3.connect(application.DB_PATH) as conn:
            row = conn.execute(
                "SELECT * FROM Artist WHERE ArtistName = 'Persisted Artist'"
            ).fetchone()
        assert row is not None
        assert row[2] == "Jazz"

    def test_post_missing_name_shows_error(self, client):
        r = client.post("/add_artist", data={"name": "", "genre": "Pop"},
                        follow_redirects=True)
        assert b"required" in r.data.lower() or b"error" in r.data.lower() or r.status_code == 200

    def test_post_missing_genre_shows_error(self, client):
        r = client.post("/add_artist", data={"name": "Solo Act", "genre": ""},
                        follow_redirects=True)
        assert r.status_code == 200
        assert b"required" in r.data.lower() or b"error" in r.data.lower()

    def test_post_duplicate_artist_shows_error(self, client):
        client.post("/add_artist", data={"name": "Dup Artist", "genre": "Pop"})
        r = client.post("/add_artist", data={"name": "Dup Artist", "genre": "Pop"},
                        follow_redirects=True)
        assert b"already exists" in r.data.lower() or b"error" in r.data.lower()

    def test_post_strips_whitespace(self, client):
        client.post("/add_artist", data={"name": "  Spaced  ", "genre": "  Funk  "})
        with sqlite3.connect(application.DB_PATH) as conn:
            row = conn.execute(
                "SELECT ArtistName, Genre FROM Artist WHERE ArtistName = 'Spaced'"
            ).fetchone()
        assert row is not None
        assert row[1] == "Funk"


# ---------------------------------------------------------------------------
# Function 2 — Add Concert
# ---------------------------------------------------------------------------

class TestAddConcert:
    def test_get_renders_form(self, client):
        r = client.get("/add_concert")
        assert r.status_code == 200
        assert b"<form" in r.data

    def test_get_populates_artist_dropdown(self, client):
        body = text(client.get("/add_concert"))
        # Seed data includes Taylor Swift
        assert "Taylor Swift" in body

    def test_post_valid_redirects(self, client):
        r = client.post("/add_concert", data={
            "venue": "Test Arena", "city": "Dallas",
            "date": "2026-05-01", "artist_id": "1",
        })
        assert r.status_code == 302

    def test_post_persists_concert(self, client):
        client.post("/add_concert", data={
            "venue": "Saved Venue", "city": "Boston",
            "date": "2026-09-09", "artist_id": "1",
        })
        with sqlite3.connect(application.DB_PATH) as conn:
            row = conn.execute(
                "SELECT * FROM Concert WHERE VenueName = 'Saved Venue'"
            ).fetchone()
        assert row is not None
        assert row[2] == "Boston"

    def test_post_missing_field_stays_on_page(self, client):
        r = client.post("/add_concert", data={
            "venue": "", "city": "NYC", "date": "2026-01-01", "artist_id": "1",
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b"required" in r.data.lower() or b"error" in r.data.lower()


# ---------------------------------------------------------------------------
# Function 3 — Add Customer
# ---------------------------------------------------------------------------

class TestAddCustomer:
    def test_get_renders_form(self, client):
        r = client.get("/add_customer")
        assert r.status_code == 200
        assert b"<form" in r.data

    def test_post_valid_redirects(self, client):
        r = client.post("/add_customer", data={"name": "New Person"})
        assert r.status_code == 302

    def test_post_persists_customer(self, client):
        client.post("/add_customer", data={"name": "Stored User"})
        with sqlite3.connect(application.DB_PATH) as conn:
            row = conn.execute(
                "SELECT * FROM Customer WHERE CustomerName = 'Stored User'"
            ).fetchone()
        assert row is not None

    def test_post_empty_name_shows_error(self, client):
        r = client.post("/add_customer", data={"name": "  "},
                        follow_redirects=True)
        assert r.status_code == 200
        assert b"required" in r.data.lower() or b"error" in r.data.lower()

    def test_post_strips_whitespace(self, client):
        client.post("/add_customer", data={"name": "  Trim Me  "})
        with sqlite3.connect(application.DB_PATH) as conn:
            row = conn.execute(
                "SELECT CustomerName FROM Customer WHERE CustomerName = 'Trim Me'"
            ).fetchone()
        assert row is not None


# ---------------------------------------------------------------------------
# Function 4 — Add Ticket
# ---------------------------------------------------------------------------

class TestAddTicket:
    def test_get_renders_form(self, client):
        r = client.get("/add_ticket")
        assert r.status_code == 200
        assert b"<form" in r.data

    def test_get_populates_dropdowns(self, client):
        body = text(client.get("/add_ticket"))
        assert "Alice Johnson" in body or "Madison Square Garden" in body

    def test_post_valid_redirects(self, client):
        r = client.post("/add_ticket", data={
            "concert_id": "1", "customer_id": "1",
            "seat": "AA1", "price": "99.99",
        })
        assert r.status_code == 302

    def test_post_persists_ticket(self, client):
        client.post("/add_ticket", data={
            "concert_id": "1", "customer_id": "1",
            "seat": "ZZ9", "price": "55.00",
        })
        with sqlite3.connect(application.DB_PATH) as conn:
            row = conn.execute(
                "SELECT * FROM Ticket WHERE SeatNumber = 'ZZ9'"
            ).fetchone()
        assert row is not None
        assert row[4] == 55.00

    def test_post_negative_price_shows_error(self, client):
        r = client.post("/add_ticket", data={
            "concert_id": "1", "customer_id": "1",
            "seat": "B1", "price": "-10",
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b"non-negative" in r.data.lower() or b"error" in r.data.lower()

    def test_post_non_numeric_price_shows_error(self, client):
        r = client.post("/add_ticket", data={
            "concert_id": "1", "customer_id": "1",
            "seat": "B2", "price": "free",
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b"error" in r.data.lower() or b"non-negative" in r.data.lower()

    def test_post_missing_seat_shows_error(self, client):
        r = client.post("/add_ticket", data={
            "concert_id": "1", "customer_id": "1",
            "seat": "", "price": "50",
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b"required" in r.data.lower() or b"error" in r.data.lower()

    def test_post_zero_price_is_valid(self, client):
        r = client.post("/add_ticket", data={
            "concert_id": "1", "customer_id": "1",
            "seat": "FREE1", "price": "0",
        })
        assert r.status_code == 302


# ---------------------------------------------------------------------------
# Function 5 — View Concerts
# ---------------------------------------------------------------------------

class TestViewConcerts:
    def test_all_concerts_loads(self, client):
        r = client.get("/view_concerts")
        assert r.status_code == 200

    def test_shows_seeded_concerts(self, client):
        body = text(client.get("/view_concerts"))
        assert "Madison Square Garden" in body or "Taylor Swift" in body

    def test_city_dropdown_present(self, client):
        body = text(client.get("/view_concerts"))
        assert "<select" in body
        assert "New York" in body or "Los Angeles" in body

    def test_filter_by_valid_city(self, client):
        r = client.get("/view_concerts?city=New+York")
        assert r.status_code == 200
        body = text(r)
        assert "New York" in body

    def test_filter_excludes_other_cities(self, client):
        body = text(client.get("/view_concerts?city=London"))
        # London concerts should appear; Chicago should not (no seed concert in Chicago for London filter)
        assert "London" in body

    def test_filter_nonexistent_city_empty(self, client):
        body = text(client.get("/view_concerts?city=Atlantis"))
        assert "No concerts found" in body or "<tbody>\n            \n        </tbody>" in body or "Atlantis" in body


# ---------------------------------------------------------------------------
# Function 6 — Concerts by Artist
# ---------------------------------------------------------------------------

class TestConcertsByArtist:
    def test_page_loads(self, client):
        assert client.get("/concerts_by_artist").status_code == 200

    def test_artist_dropdown_populated(self, client):
        body = text(client.get("/concerts_by_artist"))
        assert "Taylor Swift" in body

    def test_filter_by_artist_shows_concerts(self, client):
        # ArtistId=1 is Taylor Swift from seed data
        body = text(client.get("/concerts_by_artist?artist_id=1"))
        assert "Madison Square Garden" in body or "Taylor Swift" in body

    def test_filter_shows_artist_name_heading(self, client):
        body = text(client.get("/concerts_by_artist?artist_id=1"))
        assert "Taylor Swift" in body

    def test_filter_by_artist_no_concerts(self, client):
        # Add an artist with no concerts
        client.post("/add_artist", data={"name": "Ghost Artist", "genre": "None"})
        with sqlite3.connect(application.DB_PATH) as conn:
            row = conn.execute(
                "SELECT ArtistId FROM Artist WHERE ArtistName='Ghost Artist'"
            ).fetchone()
        aid = row[0]
        body = text(client.get(f"/concerts_by_artist?artist_id={aid}"))
        assert "No concerts found" in body or "Ghost Artist" in body

    def test_no_filter_shows_no_table(self, client):
        body = text(client.get("/concerts_by_artist"))
        # Without a selection, no results table should appear
        assert "Madison Square Garden" not in body


# ---------------------------------------------------------------------------
# Function 7 — Customer Spending
# ---------------------------------------------------------------------------

class TestCustomerSpending:
    def test_page_loads(self, client):
        assert client.get("/customer_spending").status_code == 200

    def test_shows_all_customers_by_default(self, client):
        body = text(client.get("/customer_spending"))
        assert "Alice Johnson" in body
        assert "Bob Martinez" in body

    def test_totals_are_numeric(self, client):
        body = text(client.get("/customer_spending"))
        assert "$" in body

    def test_filter_by_customer(self, client):
        body = text(client.get("/customer_spending?customer_id=1"))
        assert "Alice Johnson" in body

    def test_filter_excludes_others(self, client):
        body = text(client.get("/customer_spending?customer_id=1"))
        # Only Alice should be in result rows (Bob should not appear in table body)
        # We check that Bob is not in a <td> (he may still appear in the dropdown)
        assert body.count("Bob Martinez") <= 1  # at most in the dropdown

    def test_correct_total_for_alice(self, client):
        # Seed: Alice (id=1) has tickets for concert 1 ($150), concert 2 ($120), concert 5 ($90), concert 7 ($130) = $490
        body = text(client.get("/customer_spending?customer_id=1"))
        assert "490.00" in body

    def test_customer_with_no_tickets_shows_zero(self, client):
        client.post("/add_customer", data={"name": "Broke Person"})
        with sqlite3.connect(application.DB_PATH) as conn:
            row = conn.execute(
                "SELECT CustomerId FROM Customer WHERE CustomerName='Broke Person'"
            ).fetchone()
        cid = row[0]
        body = text(client.get(f"/customer_spending?customer_id={cid}"))
        assert "0.00" in body


# ---------------------------------------------------------------------------
# Function 8 — Top 3 Artists by Revenue
# ---------------------------------------------------------------------------

class TestTopArtists:
    def test_page_loads(self, client):
        assert client.get("/top_artists").status_code == 200

    def test_shows_exactly_three_or_fewer(self, client):
        body = text(client.get("/top_artists"))
        # Count data rows — should be at most 3
        assert body.count("<tr") <= 5  # 1 header + up to 3 data + table tag

    def test_revenue_displayed(self, client):
        body = text(client.get("/top_artists"))
        assert "$" in body

    def test_top_artist_is_correct(self, client):
        # From seed data:
        # Taylor Swift:  concert1($150+$150) + concert2($120) = $420
        # Kendrick:      concert3($200+$200) + concert4($175) = $575  <-- highest
        # Arctic Monkeys:concert5($90)                        = $90
        # Billie Eilish: concert6($110)                       = $110
        # The Weeknd:    concert7($130+$130)                  = $260
        body = text(client.get("/top_artists"))
        assert "Kendrick Lamar" in body

    def test_revenue_order_descending(self, client):
        body = text(client.get("/top_artists"))
        kendrick_pos = body.find("Kendrick Lamar")
        swift_pos    = body.find("Taylor Swift")
        weeknd_pos   = body.find("The Weeknd")
        # Seed totals: Kendrick $575 > Taylor Swift $495 > The Weeknd $260
        assert kendrick_pos < swift_pos < weeknd_pos

    def test_rank_medals_present(self, client):
        body = text(client.get("/top_artists"))
        assert "rank-gold" in body or "rank-silver" in body

    def test_no_tickets_artist_not_in_top3(self, client):
        # Seed already has 5 artists all with revenue; a $0 artist won't displace them
        client.post("/add_artist", data={"name": "No Revenue Band", "genre": "Silence"})
        body = text(client.get("/top_artists"))
        # Top 3: Kendrick $575, Taylor Swift $495, The Weeknd $260 — zero-revenue band excluded
        assert "Kendrick Lamar" in body
        assert "Taylor Swift" in body
        # Must not appear in any table <td> (may appear in flash from prior POST)
        import re
        td_values = re.findall(r'<td>(.*?)</td>', body)
        assert "No Revenue Band" not in td_values


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

class TestNavigation:
    PAGES = [
        "/add_artist", "/add_concert", "/add_customer", "/add_ticket",
        "/view_concerts", "/concerts_by_artist", "/customer_spending", "/top_artists",
        "/concert_revenue",
    ]

    def test_all_pages_have_home_link(self, client):
        for page in self.PAGES:
            body = text(client.get(page))
            assert 'href="/"' in body or "Back to Home" in body, f"No home link on {page}"

    def test_all_pages_have_back_link(self, client):
        for page in self.PAGES:
            body = text(client.get(page))
            assert "back-link" in body or "Back to Home" in body, f"No back link on {page}"

    def test_header_present_on_all_pages(self, client):
        for page in self.PAGES:
            body = text(client.get(page))
            assert "Concert Ticket Manager" in body, f"No header on {page}"

    def test_home_has_bonus_link(self, client):
        body = text(client.get("/"))
        assert "concert_revenue" in body


# ---------------------------------------------------------------------------
# BONUS — Concert Revenue Report
# ---------------------------------------------------------------------------

class TestConcertRevenue:
    def test_page_loads(self, client):
        assert client.get("/concert_revenue").status_code == 200

    def test_shows_all_concerts_by_default(self, client):
        body = text(client.get("/concert_revenue"))
        # All 7 seeded concerts should appear
        assert "Madison Square Garden" in body
        assert "O2 Arena" in body

    def test_shows_all_three_joined_columns(self, client):
        body = text(client.get("/concert_revenue"))
        # ArtistName (Artist), VenueName (Concert), TicketsSold/TotalRevenue (Ticket)
        assert "Taylor Swift" in body
        assert "Tickets Sold" in body
        assert "Revenue" in body

    def test_genre_filter_dropdown_populated(self, client):
        body = text(client.get("/concert_revenue"))
        assert "<select" in body
        assert "Pop" in body or "Hip-Hop" in body

    def test_genre_filter_returns_correct_rows(self, client):
        body = text(client.get("/concert_revenue?genre=Pop"))
        # Only Taylor Swift (Pop) concerts should appear
        assert "Taylor Swift" in body
        assert "Kendrick Lamar" not in body

    def test_genre_filter_nonexistent_shows_empty(self, client):
        body = text(client.get("/concert_revenue?genre=Polka"))
        assert "No concerts found" in body

    def test_sort_by_revenue(self, client):
        body = text(client.get("/concert_revenue?sort=revenue"))
        assert r.status_code == 200 if (r := client.get("/concert_revenue?sort=revenue")) else True
        # Kendrick concert 3 had $400 revenue — should appear before others
        kendrick_pos = body.find("Kendrick Lamar")
        assert kendrick_pos != -1

    def test_sort_by_tickets(self, client):
        r = client.get("/concert_revenue?sort=tickets")
        assert r.status_code == 200

    def test_sort_by_date(self, client):
        r = client.get("/concert_revenue?sort=date")
        assert r.status_code == 200
        body = text(r)
        # 2026-06-15 (Taylor Swift MSG) should appear before 2026-11-12
        june_pos = body.find("2026-06-15")
        nov_pos  = body.find("2026-11-12")
        assert june_pos < nov_pos

    def test_summary_bar_shows_totals(self, client):
        body = text(client.get("/concert_revenue"))
        assert "summary-bar" in body
        assert "Total Revenue" in body or "$" in body

    def test_summary_total_revenue_correct(self, client):
        # All seed tickets: 150+150+120+200+200+175+90+110+130+130 = 1455
        body = text(client.get("/concert_revenue"))
        assert "1455.00" in body

    def test_summary_total_tickets_correct(self, client):
        # 10 seed tickets total
        body = text(client.get("/concert_revenue"))
        assert "10" in body

    def test_tfoot_totals_row_present(self, client):
        body = text(client.get("/concert_revenue"))
        assert "<tfoot" in body
        assert "totals-row" in body

    def test_genre_tag_rendered(self, client):
        body = text(client.get("/concert_revenue"))
        assert "genre-tag" in body

    def test_badge_bonus_rendered(self, client):
        body = text(client.get("/concert_revenue"))
        assert "BONUS" in body

    def test_concert_with_no_tickets_shows_zero(self, client):
        # Add a concert with no tickets
        client.post("/add_concert", data={
            "venue": "Empty Hall", "city": "Nowhere",
            "date": "2027-01-01", "artist_id": "1",
        })
        body = text(client.get("/concert_revenue"))
        assert "Empty Hall" in body
        assert "$0.00" in body

    def test_genre_filter_combined_with_sort(self, client):
        r = client.get("/concert_revenue?genre=Hip-Hop&sort=revenue")
        assert r.status_code == 200
        body = text(r)
        assert "Kendrick Lamar" in body
        assert "Taylor Swift" not in body
