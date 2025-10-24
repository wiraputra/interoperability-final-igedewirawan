# main.py
from fastapi.security import APIKeyHeader 
from sqlalchemy.orm import Session
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.middleware.cors import CORSMiddleware # Penting untuk Frontend
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pydantic import BaseModel
from typing import List
import datetime

# 1. Konfigurasi Database (SQLite)
DATABASE_URL = "sqlite:///./campus_events.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Definisi Model SQLAlchemy (ORM) - Sesuai dengan tabel di create_db.sql
class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    date = Column(Date)
    location = Column(String)
    quota = Column(Integer)
    
    participants = relationship("Participant", back_populates="event")

class Participant(Base):
    __tablename__ = "participants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"))

    event = relationship("Event", back_populates="participants")

# Membuat tabel di database (jika belum ada)
Base.metadata.create_all(bind=engine)

# 3. Definisi Skema Pydantic (untuk validasi data API)
class EventBase(BaseModel):
    title: str
    date: datetime.date
    location: str
    quota: int

class EventCreate(EventBase):
    pass

class EventSchema(EventBase):
    id: int
    
    class Config:
        # Pydantic V2 menggunakan 'from_attributes' bukan 'orm_mode'
        from_attributes = True

# --- Mulai penambahan untuk langkah 3 ---
class ParticipantBase(BaseModel):
    name: str
    email: str
    event_id: int

class ParticipantCreate(ParticipantBase):
    pass

class ParticipantSchema(ParticipantBase):
    id: int

    class Config:
        from_attributes = True
# --- Selesai penambahan untuk langkah 3 ---


# Inisialisasi aplikasi FastAPI
app = FastAPI(title="Campus Event API")

# Middleware untuk CORS (agar bisa diakses dari frontend JavaScript)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================================
# [BARU] DEFINISI MEKANISME API KEY
# ==========================================================
API_KEY = "12345"
API_KEY_NAME = "X-API-KEY"

api_key_header_scheme = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def get_api_key(api_key: str = Security(api_key_header_scheme)):
    if api_key == API_KEY:
        return api_key
    else:
        raise HTTPException(
            status_code=403, 
            detail="Could not validate credentials: Invalid API Key"
        )
# ==========================================================


# Dependency untuk mendapatkan sesi database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === ENDPOINTS UNTUK EVENTS ===

# 1. GET /events -> Menampilkan semua event (TIDAK PERLU AUTH)
@app.get("/events", response_model=List[EventSchema], tags=["Events"])
def read_events(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    events = db.query(Event).offset(skip).limit(limit).all()
    return events

# 2. POST /events -> Menambah event baru (PERLU AUTH)
@app.post("/events", response_model=EventSchema, tags=["Events"])
def create_event(
    event: EventCreate, 
    db: Session = Depends(get_db), 
    api_key: str = Depends(get_api_key) # <-- [MODIFIKASI] Diterapkan di sini
):
    db_event = Event(**event.dict())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

# 3. GET /events/{id} -> Menampilkan detail satu event (TIDAK PERLU AUTH)
@app.get("/events/{event_id}", response_model=EventSchema, tags=["Events"])
def read_event(event_id: int, db: Session = Depends(get_db)):
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return db_event

# 4. PUT /events/{id} -> Mengubah data event (PERLU AUTH)
@app.put("/events/{event_id}", response_model=EventSchema, tags=["Events"])
def update_event(
    event_id: int, 
    event: EventCreate, 
    db: Session = Depends(get_db), 
    api_key: str = Depends(get_api_key) # <-- [MODIFIKASI] Diterapkan di sini
):
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    
    db_event.title = event.title
    db_event.date = event.date
    db_event.location = event.location
    db_event.quota = event.quota
    
    db.commit()
    db.refresh(db_event)
    return db_event

# 5. DELETE /events/{id} -> Menghapus event (PERLU AUTH)
@app.delete("/events/{event_id}", tags=["Events"])
def delete_event(
    event_id: int, 
    db: Session = Depends(get_db), 
    api_key: str = Depends(get_api_key) # <-- [MODIFIKASI] Diterapkan di sini
):
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    
    db.delete(db_event)
    db.commit()
    return {"message": f"Event with id {event_id} has been deleted"}


# === ENDPOINTS UNTUK PARTICIPANTS ===

# POST /register -> Menambahkan peserta baru ke event (TIDAK PERLU AUTH)
@app.post("/register", response_model=ParticipantSchema, tags=["Participants"])
def register_participant(participant: ParticipantCreate, db: Session = Depends(get_db)):
    db_event = db.query(Event).filter(Event.id == participant.event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    participant_count = db.query(Participant).filter(Participant.event_id == participant.event_id).count()
    if participant_count >= db_event.quota:
        raise HTTPException(status_code=400, detail="Event is full")

    db_participant = Participant(**participant.dict())
    db.add(db_participant)
    db.commit()
    db.refresh(db_participant)
    return db_participant

# GET /participants -> Menampilkan daftar semua peserta (Bisa dibuat perlu auth jika admin saja yang boleh lihat)
@app.get("/participants", response_model=List[ParticipantSchema], tags=["Participants"])
def read_participants(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    participants = db.query(Participant).offset(skip).limit(limit).all()
    return participants