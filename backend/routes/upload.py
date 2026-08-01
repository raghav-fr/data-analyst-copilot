"""Upload route — handles CSV, Excel, JSON file uploads."""
import os
import uuid
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from models.db_models import Dataset
from models.schemas import UploadResponse
from services.data_service import load_dataset
from services.auth_service import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", 100)) * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json", ".parquet"}


@router.post("/", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Upload a dataset file. Supports CSV, Excel, JSON, Parquet."""
    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // 1024 // 1024}MB"
        )

    # Save to disk
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        f.write(content)

    # Load into pandas
    try:
        dataset_id, df = load_dataset(file_path, file.filename, user_id=current_user.uid)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {str(e)}")

    # Save metadata to DB
    db_dataset = Dataset(
        id=dataset_id,
        user_id=current_user.uid,
        filename=safe_name,
        original_filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        rows=len(df),
        columns=len(df.columns),
    )
    db.add(db_dataset)
    await db.commit()

    logger.info(f"Uploaded: {file.filename} → {dataset_id} ({len(df)} rows × {len(df.columns)} cols)")

    return UploadResponse(
        dataset_id=dataset_id,
        filename=file.filename,
        rows=len(df),
        columns=len(df.columns),
        column_names=df.columns.tolist(),
        file_size=len(content),
        message=f"Successfully loaded {len(df):,} rows and {len(df.columns)} columns.",
    )


@router.get("/datasets")
async def list_datasets(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """List all uploaded datasets."""
    from sqlalchemy import select
    result = await db.execute(
        select(Dataset)
        .where(Dataset.user_id == current_user.uid)
        .order_by(Dataset.created_at.desc())
        .limit(50)
    )
    datasets = result.scalars().all()
    return [
        {
            "id": d.id,
            "filename": d.original_filename,
            "rows": d.rows,
            "columns": d.columns,
            "file_size": d.file_size,
            "created_at": d.created_at.isoformat(),
        }
        for d in datasets
    ]


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Delete a dataset and its file."""
    from sqlalchemy import select, delete as sql_delete
    result = await db.execute(
        select(Dataset)
        .where(Dataset.id == dataset_id)
        .where(Dataset.user_id == current_user.uid)
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Remove file
    if os.path.exists(dataset.file_path):
        os.remove(dataset.file_path)

    await db.execute(sql_delete(Dataset).where(Dataset.id == dataset_id))
    await db.commit()
    return {"message": "Dataset deleted successfully"}
