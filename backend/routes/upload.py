"""Upload route — handles background processing of datasets uploaded to Firebase Storage."""
import os
import uuid
import logging
import tempfile
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from firebase_admin import firestore, storage

from services.data_service import load_dataset
from services.auth_service import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


class ProcessDatasetRequest(BaseModel):
    dataset_id: str
    filename: str
    file_path: str
    file_size: int


def _process_dataset_background(dataset_id: str, user_id: str, file_path: str, filename: str, file_size: int):
    """Background task to load a dataset from Firebase Storage, parse it with Pandas, and update Firestore metadata."""
    logger.info(f"Background processing started for dataset {dataset_id}")
    temp_file_path = None
    db = firestore.client()
    doc_ref = db.collection('users').document(user_id).collection('datasets').document(dataset_id)
    
    try:
        # Download from Storage
        bucket = storage.bucket()
        blob = bucket.blob(file_path)
        
        ext = os.path.splitext(filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            blob.download_to_filename(temp_file.name)
            temp_file_path = temp_file.name

        # Load into pandas
        _, df = load_dataset(temp_file_path, filename, dataset_id=dataset_id, user_id=user_id)

        # Update Firestore
        doc_ref.update({
            'status': 'ready',
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': df.columns.tolist(),
        })
        logger.info(f"Dataset {dataset_id} processing complete: {len(df)} rows × {len(df.columns)} cols")
        
    except Exception as e:
        logger.error(f"Failed to process dataset {dataset_id}: {str(e)}")
        doc_ref.update({
            'status': 'error',
            'error_message': str(e)
        })
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@router.post("/process", status_code=202)
async def process_dataset(
    request: ProcessDatasetRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
):
    """Initiate background processing for a dataset already uploaded to Firebase Storage."""
    db = firestore.client()
    doc_ref = db.collection('users').document(current_user.uid).collection('datasets').document(request.dataset_id)
    
    # Save initial metadata
    doc_ref.set({
        'id': request.dataset_id,
        'user_id': current_user.uid,
        'filename': request.filename,
        'original_filename': request.filename,
        'file_path': request.file_path,
        'file_size': request.file_size,
        'status': 'processing',
        'created_at': firestore.SERVER_TIMESTAMP
    })

    # Queue background processing
    background_tasks.add_task(
        _process_dataset_background,
        request.dataset_id,
        current_user.uid,
        request.file_path,
        request.filename,
        request.file_size
    )

    return {"message": "Processing started", "dataset_id": request.dataset_id}


@router.get("/{dataset_id}/status")
async def get_dataset_status(
    dataset_id: str,
    current_user = Depends(get_current_user),
):
    """Check the processing status of a dataset."""
    db = firestore.client()
    doc_ref = db.collection('users').document(current_user.uid).collection('datasets').document(dataset_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    return doc.to_dict()


@router.get("/datasets")
async def list_datasets(
    current_user = Depends(get_current_user),
):
    """List all uploaded datasets."""
    db = firestore.client()
    datasets_ref = db.collection('users').document(current_user.uid).collection('datasets')
    # Filter for successfully ready datasets or processing datasets
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
            "status": d.get("status", "ready"),  # fallback to ready for old datasets
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
