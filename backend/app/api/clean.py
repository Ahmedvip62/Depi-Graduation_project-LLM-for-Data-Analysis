import logging
from typing import Any, Dict

import numpy as np
from fastapi import APIRouter, HTTPException, status

from app.core.chunker import TextChunker
from app.core.profiler import DataProfiler
from app.core.session_manager import session_manager
from app.eda.auto_eda import generate_auto_eda
from app.models.schemas import CleaningRequest, CleaningResponse
from app.rag.embedder import get_embedder
from app.rag.store import get_chroma_store
from app.skills.cleaning import CleaningSkill

logger = logging.getLogger(__name__)
router = APIRouter()
cleaning_skill = CleaningSkill()


@router.post("/clean", response_model=CleaningResponse)
async def clean_dataset(request: CleaningRequest) -> CleaningResponse:
    # 1. Fetch existing session
    session = session_manager.get_session(request.session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {request.session_id} not found."
        )

    df = session.get("df")
    profile = session.get("profile")
    if df is None or profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session does not have a valid dataset loaded. Re-upload first."
        )

    original_rows = len(df)
    original_cols = len(df.columns)

    # 2. Call LLM to plan data cleaning
    logger.info("Requesting LLM data cleaning plan for session %s...", request.session_id)
    plan = await cleaning_skill.generate_cleaning_plan(profile, request.instructions)
    logger.info("Cleaning plan generated: %s", plan.get("explanation", ""))

    # 3. Execute the plan
    cleaned_df, actions_taken = cleaning_skill.execute_cleaning_plan(df, plan)
    
    # 4. Generate new profile and Auto-EDA
    filename = profile.get("file_name", "cleaned_dataset.csv")
    if not filename.startswith("cleaned_"):
        filename = f"cleaned_{filename}"

    new_profile = DataProfiler.profile(cleaned_df, filename)
    new_profile_dict = new_profile.model_dump()

    try:
        new_eda = generate_auto_eda(cleaned_df, new_profile_dict)
    except Exception:
        logger.exception("Auto-EDA failed for cleaned DataFrame")
        new_eda = {
            "summary": {
                "row_count": new_profile_dict.get("row_count", 0),
                "column_count": new_profile_dict.get("column_count", 0),
                "missing_pct": new_profile_dict.get("missing_pct", 0.0),
                "memory_human": "0 B",
                "numeric_count": len(new_profile_dict.get("numeric_columns", [])),
                "categorical_count": len(new_profile_dict.get("categorical_columns", [])),
                "datetime_count": len(new_profile_dict.get("datetime_columns", [])),
            },
            "charts": [],
            "suggestions": [],
        }

    # 5. Determine target session_id (create or update-in-place)
    target_session_id = request.session_id
    if request.create_new_session:
        target_session_id = session_manager.create_session()
        # Initialize the new session structure
        session_manager.update_session(target_session_id, "df", cleaned_df)
        session_manager.update_session(target_session_id, "profile", new_profile_dict)
        session_manager.update_session(target_session_id, "eda", new_eda)
        # Copy chat history and charts if needed
        session_manager.update_session(target_session_id, "chat_history", list(session.get("chat_history", [])))
        session_manager.update_session(target_session_id, "charts", list(session.get("charts", [])))
    else:
        # Update session in place
        session_manager.update_session(target_session_id, "df", cleaned_df)
        session_manager.update_session(target_session_id, "profile", new_profile_dict)
        session_manager.update_session(target_session_id, "eda", new_eda)

    # 6. Re-index RAG Chunks
    try:
        # Delete old Chroma collection if updating in place
        if not request.create_new_session:
            get_chroma_store().delete_collection(target_session_id)
            
        chunks = TextChunker.chunk_dataframe(cleaned_df, strategy="combined")
        if chunks:
            embeddings = get_embedder().embed_texts(chunks)
            get_chroma_store().add_chunks(target_session_id, chunks, embeddings)
    except Exception as exc:
        logger.exception("Error during RAG re-indexing for cleaned dataset")
        # Don't fail the whole request just because RAG indexing failed

    # 7. Build preview rows for return
    preview_limit = 20
    preview_rows = cleaned_df.head(preview_limit).replace({np.nan: None}).to_dict(orient="records")

    # Add a system message explaining the cleaning action to chat history
    cleaning_summary = (
        f"🧹 **Data Cleaning Session**\n"
        f"**Plan Explanation:** {plan.get('explanation', 'No explanation provided.')}\n\n"
        f"**Actions Taken:**\n" + "\n".join(f"- {a}" for a in actions_taken)
    )
    session_manager.append_chat(target_session_id, "assistant", cleaning_summary)

    return CleaningResponse(
        message="Dataset cleaned successfully.",
        session_id=target_session_id,
        original_rows=original_rows,
        cleaned_rows=len(cleaned_df),
        original_columns=original_cols,
        cleaned_columns=len(cleaned_df.columns),
        actions=actions_taken,
        explanation=plan.get("explanation") or "Auto-clean executed.",
        profile=new_profile,
        preview_rows=preview_rows
    )
