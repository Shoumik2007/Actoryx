"""db.py — the database: two tables, described as Python classes (SQLAlchemy). SQLite stores it in one file, energy.db.
The same code works with MySQL or PostgreSQL — only DATABASE_URL changes (see reference/mysql_fastapi_app.py)."""
from datetime import datetime
from pathlib import Path

from sqlalchemy import JSON, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = "sqlite:///energy.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(engine)


class Base(DeclarativeBase):
    pass


class Reading(Base):
    """One 15-minute reading from the campus main substation (TR-MAIN, 630 kVA) and the 500 kWp rooftop plant."""
    __tablename__ = "readings"
    timestamp: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    load_kw: Mapped[float] = mapped_column(Float)
    solar_kw: Mapped[float] = mapped_column(Float)
    ambient_c: Mapped[float] = mapped_column(Float)
    irradiance_wm2: Mapped[float] = mapped_column(Float)


class Calculation(Base):
    """Every calculation anyone asks the API for — the API now has a memory."""
    __tablename__ = "calculations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(30))
    inputs: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


def data_file(name="campus_feb_mar_2026.csv"):
    """Find the CSV next to this file (as on a Hugging Face Space), or v1/data/<name> from any day's folder."""
    here = Path(__file__).resolve().parent
    if (here / name).exists():
        return here / name
    for folder in Path(__file__).resolve().parents:
        if (folder / "data" / name).exists():
            return folder / "data" / name
    raise FileNotFoundError(f"data/{name} not found — run data/make_data.py")


class ApplianceRow(Base):
    """Monday's appliance list — now a table, so it survives a server restart."""
    __tablename__ = "appliances"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(40))
    watts: Mapped[float] = mapped_column(Float)
    hours: Mapped[float] = mapped_column(Float)


Base.metadata.create_all(engine)                               # create the tables if they don't exist yet


def seed_readings():
    """Fill the readings table from the CSV if it's empty (e.g. on a fresh cloud server)."""
    import pandas as pd
    from sqlalchemy import func, select
    with Session() as s:
        if s.scalar(select(func.count()).select_from(Reading)):
            return
        csv = pd.read_csv(data_file(), parse_dates=["timestamp"])
        s.add_all(Reading(**row) for row in csv.to_dict("records"))
        s.commit()


seed_readings()
