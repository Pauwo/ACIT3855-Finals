from sqlalchemy import create_engine
from models import Base

# Database setup
engine = create_engine("sqlite:///storage.db")

def create_tables():
    Base.metadata.create_all(engine)
    print("Tables created successfully.")

def drop_tables():
    Base.metadata.drop_all(engine)
    print("Tables dropped successfully.")

if __name__ == "__main__":
    # Create or drop tables
    create_tables()
    # drop_tables()