import json
import logging
import re
from typing import Any, Optional
import pandas as pd
import numpy as np

from app.config import settings
from app.llm.ollama_client import get_ollama_client
from app.llm.prompt_templates import build_profile_summary, build_cleaning_quality_report

logger = logging.getLogger(__name__)

CLEANING_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "drop_duplicates",
                            "fill_missing",
                            "normalize_column",
                            "drop_column",
                            "convert_type",
                            "remove_outliers",
                            "cap_outliers",
                            "standardize_text"
                        ]
                    },
                    "column": {"type": "string"},
                    "strategy": {
                        "type": "string",
                        "enum": ["mean", "median", "mode", "zero", "ffill", "bfill", "value"]
                    },
                    "value": {"type": "string"},
                    "new_name": {"type": "string"},
                    "target_type": {
                        "type": "string",
                        "enum": ["int", "float", "string", "datetime", "boolean"]
                    },
                    "reason": {"type": "string"}
                },
                "required": ["action"]
            }
        },
        "explanation": {"type": "string"}
    },
    "required": ["actions", "explanation"]
}


class CleaningSkill:
    @staticmethod
    def _build_prompt(profile: dict, instructions: Optional[str] = None) -> str:
        summary = build_profile_summary(profile or {})
        quality_report = build_cleaning_quality_report(profile or {})
        user_notes = f"\nUser Specific Instructions:\n{instructions}\n" if instructions else ""
        
        return f"""You are Universal Analyst, an expert data cleaning agent.
Given the dataset profile and QUALITY WARNINGS below, generate a sequential data cleaning plan.
Only suggest actions that resolve existing issues detected in the quality warnings.

## Dataset Profile
{summary}

## Quality Warnings & Recommendations
{quality_report}
{user_notes}
Return ONLY valid JSON corresponding to the required schema. Do not output markdown code fences (like ```json).

## Strategy Selection Rules (CRITICAL - follow these strictly):

### For fill_missing:
- If the quality warning says "Data is SKEWED" → you MUST use strategy="median"
- If the quality warning says "Data is roughly symmetric" → use strategy="mean"
- If the column is categorical/text → use strategy="mode"
- If the column is boolean → use strategy="mode"
- Only use strategy="zero" when zero is a meaningful baseline (e.g. counts, quantities)
- Use strategy="ffill" or "bfill" ONLY for time-series ordered data

### For outliers:
- If outlier % is LOW (<1%) → use "remove_outliers" to drop the rows
- If outlier % is MEDIUM (1-5%) → use "remove_outliers" carefully
- If outlier % is HIGH (>5%) → use "cap_outliers" instead (clips values to IQR bounds without losing rows)
- NEVER remove outliers from columns with fewer than 50 rows

### For type conversion:
- If quality warning says "TYPE MISMATCH: stored as object but detected as numeric" → use convert_type with target_type="float"
- If quality warning says "TYPE MISMATCH: ... looks like datetime" → use convert_type with target_type="datetime"

### For column dropping:
- Only drop columns flagged as "EMPTY" (100% null) or "CONSTANT" (1 unique value)
- Do NOT drop columns just because they have high missing % unless it's 100%

### General Rules:
- Be conservative: do not drop columns or rows unless they are highly redundant, empty, or contaminated with extreme outliers.
- Always provide a specific 'reason' that references the quality warning that triggered this action.
- Ensure column names match the profile EXACTLY.
- Standardize column names using 'normalize_column' if they have special characters, units, or spaces.
- Process actions in this order: drop_duplicates first, then fill_missing, then convert_type, then normalize_column, then outlier handling, then standardize_text, then drop_column last.
"""

    @staticmethod
    def _extract_json(text: str) -> Any:
        cleaned = (text or "").strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            first, last = cleaned.find("{"), cleaned.rfind("}")
            if first == -1 or last <= first:
                raise ValueError("No JSON object found in cleaning plan response.")
            return json.loads(cleaned[first : last + 1])

    async def generate_cleaning_plan(self, profile: dict, instructions: Optional[str] = None) -> dict[str, Any]:
        prompt = self._build_prompt(profile, instructions)
        client = get_ollama_client(settings.model_name)
        try:
            text = await client.generate_text(
                prompt,
                num_predict=2000,
                temperature=0.15,
                format=CLEANING_PLAN_SCHEMA
            )
            raw = self._extract_json(text)
            return raw
        except Exception as exc:
            logger.error("Failed to generate data cleaning plan: %s", exc)
            return {
                "actions": [],
                "explanation": f"LLM generation failed: {exc}. No cleaning steps could be planned."
            }

    def execute_cleaning_plan(self, df: pd.DataFrame, plan: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
        cleaned_df = df.copy()
        actions_taken = []
        
        actions = plan.get("actions") or []
        for index, action_item in enumerate(actions):
            action_type = action_item.get("action")
            col = action_item.get("column")
            reason = action_item.get("reason", "")
            
            try:
                if action_type == "drop_duplicates":
                    before = len(cleaned_df)
                    cleaned_df = cleaned_df.drop_duplicates()
                    diff = before - len(cleaned_df)
                    if diff > 0:
                        actions_taken.append(f"Removed {diff} duplicate row(s) (Reason: {reason})")
                    else:
                        actions_taken.append(f"Checked duplicates - no duplicate rows found.")
                        
                elif action_type == "fill_missing":
                    if col not in cleaned_df.columns:
                        continue
                    missing_count = int(cleaned_df[col].isna().sum())
                    if missing_count == 0:
                        continue
                    
                    strategy = action_item.get("strategy")
                    val = action_item.get("value")
                    
                    if strategy == "mean":
                        numeric_series = pd.to_numeric(cleaned_df[col], errors="coerce")
                        fill_val = numeric_series.mean()
                        if pd.isna(fill_val):
                            fill_val = 0.0
                        cleaned_df[col] = cleaned_df[col].fillna(fill_val)
                        actions_taken.append(f"Filled {missing_count} missing values in '{col}' using mean ({fill_val:,.2f}) (Reason: {reason})")
                    elif strategy == "median":
                        numeric_series = pd.to_numeric(cleaned_df[col], errors="coerce")
                        fill_val = numeric_series.median()
                        if pd.isna(fill_val):
                            fill_val = 0.0
                        cleaned_df[col] = cleaned_df[col].fillna(fill_val)
                        actions_taken.append(f"Filled {missing_count} missing values in '{col}' using median ({fill_val:,.2f}) (Reason: {reason})")
                    elif strategy == "mode":
                        modes = cleaned_df[col].mode()
                        fill_val = modes.iloc[0] if not modes.empty else "(missing)"
                        cleaned_df[col] = cleaned_df[col].fillna(fill_val)
                        actions_taken.append(f"Filled {missing_count} missing values in '{col}' using mode ('{fill_val}') (Reason: {reason})")
                    elif strategy == "zero":
                        cleaned_df[col] = cleaned_df[col].fillna(0)
                        actions_taken.append(f"Filled {missing_count} missing values in '{col}' with 0 (Reason: {reason})")
                    elif strategy == "ffill":
                        cleaned_df[col] = cleaned_df[col].ffill()
                        actions_taken.append(f"Forward-filled {missing_count} missing values in '{col}' (Reason: {reason})")
                    elif strategy == "bfill":
                        cleaned_df[col] = cleaned_df[col].bfill()
                        actions_taken.append(f"Backward-filled {missing_count} missing values in '{col}' (Reason: {reason})")
                    elif strategy == "value" and val is not None:
                        cleaned_df[col] = cleaned_df[col].fillna(val)
                        actions_taken.append(f"Filled {missing_count} missing values in '{col}' with custom value '{val}' (Reason: {reason})")

                elif action_type == "normalize_column":
                    if col not in cleaned_df.columns:
                        continue
                    new_name = action_item.get("new_name")
                    if new_name and new_name != col:
                        cleaned_df = cleaned_df.rename(columns={col: new_name})
                        actions_taken.append(f"Renamed column '{col}' to '{new_name}' (Reason: {reason})")

                elif action_type == "drop_column":
                    if col in cleaned_df.columns:
                        cleaned_df = cleaned_df.drop(columns=[col])
                        actions_taken.append(f"Dropped column '{col}' (Reason: {reason})")

                elif action_type == "convert_type":
                    if col not in cleaned_df.columns:
                        continue
                    target_type = action_item.get("target_type")
                    if target_type == "int":
                        cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors="coerce").fillna(0).astype(int)
                    elif target_type == "float":
                        cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors="coerce").fillna(0.0).astype(float)
                    elif target_type == "string":
                        cleaned_df[col] = cleaned_df[col].astype(str)
                    elif target_type == "datetime":
                        cleaned_df[col] = pd.to_datetime(cleaned_df[col], errors="coerce", format="mixed")
                    elif target_type == "boolean":
                        cleaned_df[col] = cleaned_df[col].astype(bool)
                    actions_taken.append(f"Converted '{col}' type to {target_type} (Reason: {reason})")

                elif action_type == "remove_outliers":
                    if col not in cleaned_df.columns:
                        continue
                    numeric_series = pd.to_numeric(cleaned_df[col], errors="coerce")
                    if pd.api.types.is_numeric_dtype(numeric_series):
                        q1 = numeric_series.quantile(0.25)
                        q3 = numeric_series.quantile(0.75)
                        iqr = q3 - q1
                        lower_bound = q1 - 1.5 * iqr
                        upper_bound = q3 + 1.5 * iqr
                        before = len(cleaned_df)
                        cleaned_df = cleaned_df[(cleaned_df[col] >= lower_bound) & (cleaned_df[col] <= upper_bound)]
                        diff = before - len(cleaned_df)
                        if diff > 0:
                            actions_taken.append(f"Removed {diff} outlier rows from '{col}' using IQR range [{lower_bound:,.2f}, {upper_bound:,.2f}] (Reason: {reason})")
                        else:
                            actions_taken.append(f"Checked outliers in '{col}' - no rows outside IQR range.")

                elif action_type == "cap_outliers":
                    if col not in cleaned_df.columns:
                        continue
                    numeric_series = pd.to_numeric(cleaned_df[col], errors="coerce")
                    if pd.api.types.is_numeric_dtype(numeric_series):
                        q1 = numeric_series.quantile(0.25)
                        q3 = numeric_series.quantile(0.75)
                        iqr = q3 - q1
                        lower_bound = q1 - 1.5 * iqr
                        upper_bound = q3 + 1.5 * iqr
                        capped = numeric_series.clip(lower=lower_bound, upper=upper_bound)
                        capped_count = int((numeric_series != capped).sum())
                        if capped_count > 0:
                            cleaned_df[col] = capped
                            actions_taken.append(
                                f"Capped {capped_count} outlier values in '{col}' to IQR bounds "
                                f"[{lower_bound:,.2f}, {upper_bound:,.2f}] (Reason: {reason})"
                            )
                        else:
                            actions_taken.append(f"Checked outliers in '{col}' - no values outside IQR range.")

                elif action_type == "standardize_text":
                    if col not in cleaned_df.columns:
                        continue
                    cleaned_df[col] = cleaned_df[col].astype(str).str.strip().str.lower()
                    actions_taken.append(f"Standardized text column '{col}' to lowercase & stripped whitespace (Reason: {reason})")

            except Exception as exc:
                actions_taken.append(f"Action '{action_type}' on '{col}' failed: {exc}")
                logger.warning("Cleaning action %s on '%s' failed: %s", action_type, col, exc)

        return cleaned_df.reset_index(drop=True), actions_taken
