import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.chunker import TextChunker
from app.core.ingestion import IngestionEngine
from app.core.profiler import DataProfiler
from app.core.session_manager import session_manager
from app.eda.auto_eda import generate_auto_eda
from app.rag.embedder import get_embedder
from app.rag.store import get_chroma_store
from app.skills.cleaning import CleaningSkill

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_EXTENSIONS = {"csv", "json", "parquet", "pdf", "sqlite", "db"}
MAX_FILE_SIZE_MB = 200


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    auto_clean: bool = Form(True),
    cleaning_instructions: Optional[str] = Form(None)
) -> Dict[str, Any]:
    # --- Validate filename ---
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    # --- Read and size-check ---
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f}MB). Maximum is {MAX_FILE_SIZE_MB}MB.",
        )

    # --- Parse and profile ---
    try:
        df = IngestionEngine.parse_file(content, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error parsing %s", filename)
        raise HTTPException(status_code=500, detail=f"Failed to parse file: {exc}")

    profile = DataProfiler.profile(df, filename)
    profile_dict = profile.model_dump()

    actions_taken = []
    plan_explanation = ""

    # --- Auto-Clean ---
    if auto_clean:
        logger.info("Auto-cleaning enabled for %s. Requesting LLM cleaning plan...", filename)
        cleaner = CleaningSkill()
        plan = await cleaner.generate_cleaning_plan(profile_dict, cleaning_instructions)
        plan_explanation = plan.get("explanation", "")
        logger.info("Cleaning plan generated: %s", plan_explanation)

        df, actions_taken = cleaner.execute_cleaning_plan(df, plan)
        
        # Re-profile after cleaning
        cleaned_filename = f"cleaned_{filename}"
        profile = DataProfiler.profile(df, cleaned_filename)
        profile_dict = profile.model_dump()

    # --- Auto-EDA ---
    try:
        eda = generate_auto_eda(df, profile_dict)
    except Exception:
        logger.exception("Auto-EDA failed for %s", filename)
        eda = {
            "summary": {
                "row_count": profile_dict.get("row_count", 0),
                "column_count": profile_dict.get("column_count", 0),
                "missing_pct": profile_dict.get("missing_pct", 0.0),
                "memory_human": "0 B",
                "numeric_count": len(profile_dict.get("numeric_columns", [])),
                "categorical_count": len(profile_dict.get("categorical_columns", [])),
                "datetime_count": len(profile_dict.get("datetime_columns", [])),
            },
            "charts": [],
            "suggestions": [],
        }

    # --- Chunk and embed for RAG ---
    try:
        chunks = TextChunker.chunk_dataframe(df, strategy="combined")
        if chunks:
            embeddings = get_embedder().embed_texts(chunks)
        else:
            embeddings = []
    except Exception as exc:
        logger.exception("Error during chunking/embedding for %s", filename)
        raise HTTPException(status_code=500, detail=f"Embedding failed: {exc}")

    # --- Create session and persist ---
    session_id = session_manager.create_session()
    if chunks:
        get_chroma_store().add_chunks(session_id, chunks, embeddings)

    session_manager.update_session(session_id, "df", df)
    session_manager.update_session(session_id, "profile", profile_dict)
    session_manager.update_session(session_id, "eda", eda)

    if auto_clean:
        cleaning_summary = (
            f"🧹 **Auto Data Cleaning executed on upload**\n"
            f"**Plan Explanation:** {plan_explanation}\n\n"
            f"**Actions Taken:**\n" + ("\n".join(f"- {a}" for a in actions_taken) if actions_taken else "None")
        )
        session_manager.append_chat(session_id, "assistant", cleaning_summary)

    logger.info("Upload complete: %s -> session %s (%d rows)", filename, session_id, len(df))
    result = {"session_id": session_id, "profile": profile_dict, "eda": eda}
    if auto_clean:
        result["cleaning_applied"] = True
        result["cleaning_actions"] = actions_taken
        result["cleaning_explanation"] = plan_explanation
    else:
        result["cleaning_applied"] = False
    return result