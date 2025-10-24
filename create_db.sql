-- create_db.sql

-- Hapus tabel jika sudah ada (opsional, berguna untuk reset)
DROP TABLE IF EXISTS participants;
DROP TABLE IF EXISTS events;

-- Tabel 1: events
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    location VARCHAR(100) NOT NULL,
    quota INTEGER NOT NULL
);

-- Tabel 2: participants
CREATE TABLE participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    event_id INTEGER NOT NULL,
    FOREIGN KEY (event_id) REFERENCES events(id)
);

-- (Opsional) Tambahkan beberapa data awal untuk testing
INSERT INTO events (title, date, location, quota) VALUES
('Workshop Pemrograman Python', '2024-12-01', 'Gedung A, Ruang 101', 50),
('Seminar Teknologi Blockchain', '2024-12-05', 'Auditorium Utama', 200);