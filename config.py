import os


# Configuration SQLITE
UPLOAD_FOLDER = "uploads"
DATABASE_FILE = "vehicle.db"  # SQLite file stored in project
DATABASE_URI = f"sqlite:///{DATABASE_FILE}"  # SQLite connection string
ALLOWED_EXTENSIONS = {"xls", "xlsx", "csv"}


# # Configuration TO PG
# DB_USERNAME = "your_username"
# DB_PASSWORD = "your_password"
# DB_HOST = "localhost"
# DB_PORT = "5432"
# DB_NAME = "your_database"
#
# # Construct the PostgreSQL connection string
# DATABASE_URI = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
