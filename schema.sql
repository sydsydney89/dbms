-- Artist table
CREATE TABLE IF NOT EXISTS Artist (
    ArtistId   INTEGER PRIMARY KEY AUTOINCREMENT,
    ArtistName TEXT NOT NULL UNIQUE,
    Genre      TEXT NOT NULL
);

-- Concert table
CREATE TABLE IF NOT EXISTS Concert (
    ConcertId   INTEGER PRIMARY KEY AUTOINCREMENT,
    VenueName   TEXT NOT NULL,
    City        TEXT NOT NULL,
    ConcertDate TEXT NOT NULL,
    ArtistId    INTEGER NOT NULL,
    FOREIGN KEY (ArtistId) REFERENCES Artist(ArtistId)
);

-- Customer table
CREATE TABLE IF NOT EXISTS Customer (
    CustomerId   INTEGER PRIMARY KEY AUTOINCREMENT,
    CustomerName TEXT NOT NULL
);

-- Ticket table
CREATE TABLE IF NOT EXISTS Ticket (
    TicketId    INTEGER PRIMARY KEY AUTOINCREMENT,
    ConcertId   INTEGER NOT NULL,
    CustomerId  INTEGER NOT NULL,
    SeatNumber  TEXT NOT NULL,
    Price       REAL NOT NULL CHECK(Price >= 0),
    FOREIGN KEY (ConcertId)  REFERENCES Concert(ConcertId),
    FOREIGN KEY (CustomerId) REFERENCES Customer(CustomerId)
);

-- some artists to start with
INSERT OR IGNORE INTO Artist (ArtistName, Genre) VALUES
    ('Taylor Swift', 'Pop'),
    ('Kendrick Lamar', 'Hip-Hop'),
    ('Arctic Monkeys', 'Indie Rock'),
    ('Billie Eilish', 'Alt-Pop'),
    ('The Weeknd', 'R&B');

-- customers
INSERT OR IGNORE INTO Customer (CustomerName) VALUES
    ('Alice Johnson'),
    ('Bob Martinez'),
    ('Carol Lee'),
    ('David Kim');

-- concerts
INSERT OR IGNORE INTO Concert (VenueName, City, ConcertDate, ArtistId) VALUES
    ('Madison Square Garden', 'New York', '2026-06-15', 1),
    ('Staples Center', 'Los Angeles', '2026-07-04', 1),
    ('United Center', 'Chicago', '2026-08-20', 2),
    ('Crypto.com Arena', 'Los Angeles', '2026-09-10', 2),
    ('O2 Arena', 'London', '2026-07-22', 3),
    ('Hollywood Bowl', 'Los Angeles', '2026-10-05', 4),
    ('Rogers Centre', 'Toronto', '2026-11-12', 5);

-- tickets
INSERT OR IGNORE INTO Ticket (ConcertId, CustomerId, SeatNumber, Price) VALUES
    (1, 1, 'A1', 150.00),
    (1, 2, 'A2', 150.00),
    (2, 1, 'B5', 120.00),
    (3, 3, 'C10', 200.00),
    (3, 4, 'C11', 200.00),
    (4, 2, 'D3', 175.00),
    (5, 1, 'E7', 90.00),
    (6, 3, 'F2', 110.00),
    (7, 4, 'G9', 130.00),
    (7, 1, 'G10', 130.00);
