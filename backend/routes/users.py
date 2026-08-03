"""Users route — Account and privacy management."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import firestore, storage, auth
from services.auth_service import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.delete("/me/datasets")
async def delete_all_datasets(current_user = Depends(get_current_user)):
    """Delete all datasets and associated storage files for the current user."""
    try:
        db = firestore.client()
        bucket = storage.bucket()
        user_id = current_user.uid

        # Get all datasets
        datasets_ref = db.collection('users').document(user_id).collection('datasets')
        datasets = datasets_ref.stream()

        count = 0
        for doc in datasets:
            data = doc.to_dict()
            file_path = data.get("file_path")
            
            # 1. Delete from Storage
            if file_path:
                try:
                    blob = bucket.blob(file_path)
                    if blob.exists():
                        blob.delete()
                except Exception as e:
                    logger.warning(f"Failed to delete storage blob {file_path}: {e}")

            # 2. Delete Firestore document
            doc.reference.delete()
            
            # (Optional: remove from in-memory store in data_service)
            from services.data_service import _dataframe_store
            if doc.id in _dataframe_store:
                del _dataframe_store[doc.id]

            count += 1
            
        # Get all conversations (since they belong to datasets)
        convs_ref = db.collection('users').document(user_id).collection('conversations')
        convs = convs_ref.stream()
        for doc in convs:
            doc.reference.delete()

        return {"message": f"Successfully deleted {count} datasets and associated data."}
    except Exception as e:
        logger.error(f"Error deleting datasets for {current_user.uid}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete datasets.")

@router.delete("/me")
async def delete_account(current_user = Depends(get_current_user)):
    """Delete all user data and the Firebase Auth account."""
    try:
        # 1. Delete all datasets and files first
        await delete_all_datasets(current_user)

        # 2. Delete user document
        db = firestore.client()
        user_ref = db.collection('users').document(current_user.uid)
        user_ref.delete()

        # 3. Delete Firebase Auth User
        auth.delete_user(current_user.uid)

        return {"message": "Account successfully deleted."}
    except Exception as e:
        logger.error(f"Error deleting account for {current_user.uid}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete account.")
