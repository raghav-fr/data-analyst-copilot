"""
Authentication Service for Firebase.
"""
import os
import logging
import json
import base64
from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Initialize Firebase Admin SDK
def init_firebase():
    if not firebase_admin._apps:
        try:
            # 1. Try to initialize using a path to the service account JSON
            cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
            # 2. Try to initialize using a base64 encoded JSON string
            cred_base64 = os.getenv("FIREBASE_SERVICE_ACCOUNT_BASE64")
            
            if cred_path:
                if not os.path.isabs(cred_path):
                    # Resolve relative to the backend directory
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    cred_path = os.path.normpath(os.path.join(base_dir, cred_path))
            
            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin initialized using service account path.")
            elif cred_base64:
                decoded = base64.b64decode(cred_base64).decode("utf-8")
                cred_dict = json.loads(decoded)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin initialized using base64 credentials.")
            else:
                # 3. Fallback: tries to use GOOGLE_APPLICATION_CREDENTIALS or default credentials
                firebase_admin.initialize_app()
                logger.info("Firebase Admin initialized using default credentials.")
        except Exception as e:
            logger.warning(f"Could not initialize Firebase Admin SDK: {e}. Auth will fail.")

# Call initialization once at module load
init_firebase()


class CurrentUser:
    def __init__(self, uid: str, email: str = None):
        self.uid = uid
        self.email = email


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> CurrentUser:
    """FastAPI Dependency to verify Firebase JWT and return the user."""
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    try:
        # Verify the token using Firebase Admin SDK
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token.get("uid")
        email = decoded_token.get("email")
        
        if not uid:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
            
        return CurrentUser(uid=uid, email=email)
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
