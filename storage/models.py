from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy import Integer, String, DateTime, func, BigInteger
from datetime import datetime

class Base(DeclarativeBase):
    pass

class FlightSchedule(Base):
    __tablename__ = "flight_schedule"
    id = mapped_column(Integer, primary_key=True)
    flight_id = mapped_column(String(50), nullable=False)
    flight_status = mapped_column(String(50), nullable=False)
    flight_duration = mapped_column(Integer, nullable=False)
    flight_departure = mapped_column(DateTime, nullable=False)
    date_created = mapped_column(DateTime, nullable=False, default=func.now())
    trace_id = mapped_column(BigInteger, nullable=False)

    def to_dict(self):
        """Return a dictionary representation of a FlightSchedule instance."""
        return {
            "flight_id": self.flight_id,
            "flight_status": self.flight_status,
            "flight_duration": self.flight_duration,
            "flight_departure": self.flight_departure.isoformat() if self.flight_departure else None,
            "date_created": self.date_created.strftime("%Y-%m-%dT%H:%M:%S"),
            "trace_id": self.trace_id
        }


class PassengerCheckin(Base):
    __tablename__ = "passenger_checkin"
    id = mapped_column(Integer, primary_key=True)
    checkin_id = mapped_column(String(50), nullable=False)
    flight_id = mapped_column(String(50), nullable=False)
    luggage_weight = mapped_column(Integer, nullable=False)
    checkin_timestamp = mapped_column(DateTime, nullable=False)
    date_created = mapped_column(DateTime, nullable=False, default=func.now())
    trace_id = mapped_column(BigInteger, nullable=False)

    def to_dict(self):
        """Return a dictionary representation of a PassengerCheckin instance."""
        return {
            "checkin_id": self.checkin_id,
            "flight_id": self.flight_id,
            "luggage_weight": self.luggage_weight,
            "checkin_timestamp": self.checkin_timestamp.isoformat() if self.checkin_timestamp else None,
            "date_created": self.date_created.strftime("%Y-%m-%dT%H:%M:%S"),
            "trace_id": self.trace_id
        }