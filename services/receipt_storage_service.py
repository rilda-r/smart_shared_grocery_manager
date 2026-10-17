"""
services/receipt_storage_service.py
===================================
Uploads receipt images/PDFs to Supabase Storage, linked to room and uploader.
Falls back safely to local storage if Supabase Storage credentials are not set.
"""

import os
import uuid
import logging
from typing import Tuple

logger = logging.getLogger("grocease.storage")

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "receipts")


def store_receipt_file(file_bytes: bytes, file_name: str, room_id: int, user_id: int) -> Tuple[str, str]:
    """
    Store the receipt file in Supabase Storage under bucket 'receipts',
    keyed by 'room_{room_id}/{user_id}_{uuid}_{filename}'.
    
    Returns (storage_path, storage_type: 'supabase'|'local').
    """
    clean_name = os.path.basename(file_name).replace(" ", "_")
    unique_key = f"room_{room_id}/user_{user_id}_{uuid.uuid4().hex[:8]}_{clean_name}"

    # 1. Attempt Supabase Storage
    try:
        import streamlit as st
        supabase_url = None
        supabase_key = None

        if hasattr(st, "secrets"):
            supabase_url = st.secrets.get("SUPABASE_URL")
            supabase_key = st.secrets.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url:
            supabase_url = os.environ.get("SUPABASE_URL")
        if not supabase_key:
            supabase_key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

        if supabase_url and supabase_key:
            from supabase import create_client
            client = create_client(supabase_url, supabase_key)
            # Try to upload
            res = client.storage.from_("receipts").upload(
                path=unique_key,
                file=file_bytes,
                file_options={"content-type": "image/png" if clean_name.lower().endswith(".png") else "image/jpeg"}
            )
            logger.info("Uploaded receipt to Supabase Storage: %s", unique_key)
            return unique_key, "supabase"
    except Exception as exc:
        logger.warning("Supabase Storage upload failed or unconfigured, falling back to local: %s", exc)

    # 2. Local fallback storage
    try:
        room_dir = os.path.join(UPLOAD_DIR, f"room_{room_id}")
        os.makedirs(room_dir, exist_ok=True)
        local_path = os.path.join(room_dir, f"user_{user_id}_{uuid.uuid4().hex[:8]}_{clean_name}")
        with open(local_path, "wb") as f:
            f.write(file_bytes)
        logger.info("Saved receipt to local storage: %s", local_path)
        return local_path, "local"
    except Exception as exc:
        logger.error("Failed to save receipt to local storage: %s", exc)
        return unique_key, "unpersisted"
