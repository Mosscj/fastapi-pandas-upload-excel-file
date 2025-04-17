from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Table, Column, Integer, String, DateTime, MetaData, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import pandas as pd
import uuid
import os

# Import configuration
from config import DATABASE_URI, UPLOAD_FOLDER, ALLOWED_EXTENSIONS

app = FastAPI(
    title="Excel Upload API",
    description="This API allows users to upload an Excel file and insert data into a SQL database.",
    version="1.0.0"
)

# Database connection
engine = create_engine(DATABASE_URI, connect_args={"check_same_thread": False})

# Define metadata for table creation
metadata = MetaData()

your_table = Table(
    "vehicles", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("active_status", String, default=True),
    Column("unit_id", String, unique=True, nullable=False),
    Column("license_plate_no", String, nullable=False),
    Column("vin_no", String, nullable=False),
    Column("vehicle_brand_name", String, nullable=False),
    Column("type", String, nullable=True),
    Column("model", String, nullable=False),
    Column("updated_datetime", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
)

# Recreate the table
metadata.create_all(engine)

# Create table if not exists
metadata.create_all(engine)

# Database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Expected database columns
database_columns = {
    "id": "id",
    "active_status": "active_status",
    "unit_id": "unit_id",
    "license_plate_no": "license_plate_no",
    "vin_no": "vin_no",
    "vehicle_brand_name": "vehicle_brand_name",
    "type": "type",
    "model": "model",
    "updated_datetime": "updated_datetime",
}


# Custom column mapping (Excel Column -> Database Column)
column_mapping = {
    "สถานะ": "active_status",
    "UNIT ID": "unit_id",
    "หมายเลขทะเบียน": "license_plate_no",
    "หมายเลขตัวถัง": "vin_no",
    "ชนิดรถ (ยี่ห้อรถ)": "vehicle_brand_name",
    "ชนิดการจดทะเบียน": "type",
    "แบบ/รุ่น GPS": "model",
    "วันที่แก้ไขข้อมูลล่าสุด": "updated_datetime"
    #"สถานะการเชื่อมต่อ (จากฐานข้อมูลกลาง)"
    #"สถานะการเชื่อมต่อกับเครื่องอ่านบัตร"
}

# Utility function: Check if file extension is allowed
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Response models
class UploadResponse(BaseModel):
    message: str

class ErrorResponse(BaseModel):
    detail: str

@app.post("/upload/", summary="Upload an Excel or CSV file", response_model=UploadResponse,
          responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def upload_file(file: UploadFile = File(...)):
    """
    Upload an Excel or CSV file and overwrite the data in the database.

    - **file**: The Excel (.xls, .xlsx) or CSV (.csv) file to be uploaded.
    - **Returns**: A message confirming successful upload or an error message.
    """

    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .xls, .xlsx, or .csv allowed.")

    # Generate a unique filename to avoid overwrites
    file_extension = file.filename.rsplit(".", 1)[1].lower()
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

    # Save file to local storage
    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    try:
        # Read file based on format
        if file_extension in {"xls", "xlsx"}:
            try:
                df = pd.read_excel(file_path, engine=None, skiprows=5, dtype={"unit_id": str})
            except ValueError:
                raise HTTPException(status_code=400, detail="Error reading Excel file. Ensure it's a valid file.")
        elif file_extension == "csv":
            df = pd.read_csv(file_path, skiprows=5,dtype={"unit_id": str})
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format.")

        # Rename columns based on mapping
        df.rename(columns=column_mapping, inplace=True)

        # Find common columns between DataFrame and database schema
        common_columns = df.columns.intersection(database_columns.values())

        if common_columns.empty:
            raise HTTPException(status_code=400, detail="No matching columns found in database")


        # Filter DataFrame to only include matching columns
        df_filtered = df[common_columns]
        # Ensure 'active_status' is cleaned and mapped correctly
        if "active_status" in df_filtered.columns:
            df_filtered.loc[:, "active_status"] = df_filtered["active_status"].astype(str).str.strip().map(
                {"ใช้งาน": "A", "ไม่ใช้งาน": "D"}  # Adjust mappings as needed
            )

        # Ensure 'unit_id' is treated as a string and cleaned up properly
        if "unit_id" in df_filtered.columns:
            df_filtered.loc[:, "unit_id"] = df_filtered["unit_id"].astype(str).str.strip()
            df_filtered.loc[:, "unit_id"] = df_filtered["unit_id"].apply(
                lambda x: x[2:-1] if x.startswith('="') and x.endswith('"') else x
            )
        # Open database session
        session = SessionLocal()
        try:
            # Clear existing data before inserting new data
            session.execute(delete(your_table))
            session.commit()

            # Insert new records
            for _, row in df_filtered.iterrows():
                session.execute(
                    your_table.insert().values(
                        unit_id=row["unit_id"],
                        active_status=row.get("active_status", "A"),
                        license_plate_no=row["license_plate_no"],
                        vin_no=row["vin_no"],
                        vehicle_brand_name=row["vehicle_brand_name"],
                        type=row["type"],
                        model=row["model"],
                        updated_datetime=datetime.utcnow()
                    )
                )
            session.commit()
        finally:
            session.close()

        # Delete the file after processing
        os.remove(file_path)

        return {"message": "File uploaded, and data overwritten successfully"}

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
