import os
import logging
from fastapi import APIRouter, HTTPException, Response

from storage.metadata_db.db import export_db
from storage.vector_db.runtime import get_vector_store

router = APIRouter(prefix="/database", tags=["database"])
logger = logging.getLogger(__name__)

@router.get("/export-metadata")
def export_metadata(file_path: str):
    """
    Exports the metadata database as a downloadable file.
    """

    try:
        buffer = export_db()
        
        logger.info(f"Buffer size after export: {buffer.getbuffer().nbytes} bytes")
        
        if not buffer:
            raise HTTPException(status_code=500, detail="Failed to serialize database.")

        # Return as downloadable response
        return Response(
            content=buffer.getvalue(),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={os.path.basename(file_path)}"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/export-vector-store")
def export_vectors(file_path: str):
    """
    Exports the vector collection as a downloadable file.
    Args:
        file_path (str): The filename for the downloaded file (e.g., "vectors.json").
    Returns:
        Response: A downloadable file stream.
    """
    try:
        vector_db = get_vector_store()
        buffer = vector_db.export(file_path)  # Get the BytesIO buffer
        return Response(
            content=buffer.getvalue(),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={file_path}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export vectors: {str(e)}")

