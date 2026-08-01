"""Upload route — handles CSV, Excel, JSON file uploads."""
import os
import uuid
import logging
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from firebase_admin import firestore, storage

from models.schemas import UploadResponse
from services.data_service import load_dataset
from services.auth_service import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", 100)) * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json", ".parquet"}


@router.post("/", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
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

    dataset_id = str(uuid.uuid4())
    safe_name = f"{dataset_id}{ext}"
    
    # Save to temp file to load with Pandas
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
        temp_file.write(content)
        temp_file_path = temp_file.name

    # Load into pandas
    try:
        _, df = load_dataset(temp_file_path, file.filename, dataset_id=dataset_id, user_id=current_user.uid)
    except Exception as e:
        os.remove(temp_file_path)
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {str(e)}")

    # Upload to Firebase Storage
    try:
        bucket = storage.bucket()
        blob = bucket.blob(f"users/{current_user.uid}/datasets/{dataset_id}/{safe_name}")
        blob.upload_from_filename(temp_file_path)
    except Exception as e:
        os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Failed to upload to storage: {str(e)}")
        
    os.remove(temp_file_path)

    # Save metadata to Firestore
    db = firestore.client()
    doc_ref = db.collection('users').document(current_user.uid).collection('datasets').document(dataset_id)
    doc_ref.set({
        'id': dataset_id,
        'user_id': current_user.uid,
        'filename': safe_name,
        'original_filename': file.filename,
        'file_path': f"users/{current_user.uid}/datasets/{dataset_id}/{safe_name}",
        'file_size': len(content),
        'rows': len(df),
        'columns': len(df.columns),
        'created_at': firestore.SERVER_TIMESTAMP
    })

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
    current_user = Depends(get_current_user),
):
    """List all uploaded datasets."""
    db = firestore.client()
    datasets_ref = db.collection('users').document(current_user.uid).collection('datasets')
    query = datasets_ref.order_by('created_at', direction=firestore.Query.DESCENDING).limit(50)
    docs = query.stream()
    
    datasets = []
    for doc in docs:
        d = doc.to_dict()
        created_at = d.get('created_at')
        if created_at:
            created_at = created_at.isoformat()
        else:
            created_at = ""
            
        datasets.append({
            "id": d.get("id"),
            "filename": d.get("original_filename"),
            "rows": d.get("rows", 0),
            "columns": d.get("columns", 0),
            "file_size": d.get("file_size", 0),
            "created_at": created_at,
        })
    return datasets


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str, 
    current_user = Depends(get_current_user),
):
    """Delete a dataset and its file."""
    db = firestore.client()
    doc_ref = db.collection('users').document(current_user.uid).collection('datasets').document(dataset_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    dataset_data = doc.to_dict()
    file_path = dataset_data.get('file_path')
    
    # Remove file from Firebase Storage
    if file_path:
        try:
            bucket = storage.bucket()
            blob = bucket.blob(file_path)
            blob.delete()
        except Exception as e:
            logger.warning(f"Could not delete file from storage: {e}")

    doc_ref.delete()
    return {"message": "Dataset deleted successfully"}
