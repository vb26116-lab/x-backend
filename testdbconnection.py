import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Get DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env file")
    exit()

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

print("🔍 Testing connection to database...")

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT NOW();"))
        for row in result:
            print("✅ Connection successful! Current time on DB:", row[0])
except Exception as e:
    print("❌ Connection failed:", e)
