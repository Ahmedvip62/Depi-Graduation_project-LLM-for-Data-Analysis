"""LLM-driven prediction skill.

The pipeline:
1. Send the data profile to the LLM — it picks the best target column.
2. Analyze the task type (classification vs regression) from the profile.
3. Ask the LLM to choose the best scikit-learn model + hyperparameters.
4. Prepare data (impute, encode, split).
5. Train the chosen model and evaluate.
6. Return results as SSE-streamable dicts.
"""

import json
import logging
from typing import Any, AsyncGenerator

import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

# Models
from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge, Lasso
from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
)
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.svm import SVC, SVR
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor

from app.llm.ollama_client import OllamaClient
from app.llm.prompt_templates import build_profile_summary

logger = logging.getLogger(__name__)


# ── JSON schema for LLM target column selection ──────────────────────────────

def _target_selection_schema(columns: list[str]) -> dict[str, Any]:
    """Schema forcing the LLM to pick exactly one column as the target."""
    return {
        "type": "object",
        "properties": {
            "target_column": {
                "type": "string",
                "enum": columns,
                "description": "The column to predict.",
            },
            "reason": {
                "type": "string",
                "description": "Why this column is the best prediction target.",
            },
            "task_type": {
                "type": "string",
                "enum": ["classification", "regression"],
                "description": "Whether this is a classification or regression task.",
            },
        },
        "required": ["target_column", "reason", "task_type"],
    }


def _model_selection_schema(task_type: str) -> dict[str, Any]:
    """Schema forcing the LLM to pick a model + hyperparameters."""
    if task_type == "classification":
        models = [
            "logistic_regression",
            "random_forest_classifier",
            "gradient_boosting_classifier",
            "decision_tree_classifier",
            "svm_classifier",
            "knn_classifier",
        ]
    else:
        models = [
            "linear_regression",
            "ridge_regression",
            "lasso_regression",
            "random_forest_regressor",
            "gradient_boosting_regressor",
            "decision_tree_regressor",
            "svm_regressor",
            "knn_regressor",
        ]

    return {
        "type": "object",
        "properties": {
            "model": {
                "type": "string",
                "enum": models,
                "description": "The scikit-learn model to use.",
            },
            "reason": {
                "type": "string",
                "description": "Why this model is the best fit for the data characteristics.",
            },
            "hyperparameters": {
                "type": "object",
                "description": "Key hyperparameters for the selected model.",
            },
        },
        "required": ["model", "reason"],
    }


# ── Model factory ─────────────────────────────────────────────────────────────

_MODEL_MAP: dict[str, Any] = {
    # Classification
    "logistic_regression": LogisticRegression,
    "random_forest_classifier": RandomForestClassifier,
    "gradient_boosting_classifier": GradientBoostingClassifier,
    "decision_tree_classifier": DecisionTreeClassifier,
    "svm_classifier": SVC,
    "knn_classifier": KNeighborsClassifier,
    # Regression
    "linear_regression": LinearRegression,
    "ridge_regression": Ridge,
    "lasso_regression": Lasso,
    "random_forest_regressor": RandomForestRegressor,
    "gradient_boosting_regressor": GradientBoostingRegressor,
    "decision_tree_regressor": DecisionTreeRegressor,
    "svm_regressor": SVR,
    "knn_regressor": KNeighborsRegressor,
}

_MODEL_DISPLAY_NAMES: dict[str, str] = {
    "logistic_regression": "Logistic Regression",
    "random_forest_classifier": "Random Forest Classifier",
    "gradient_boosting_classifier": "Gradient Boosting Classifier",
    "decision_tree_classifier": "Decision Tree Classifier",
    "svm_classifier": "Support Vector Machine (SVC)",
    "knn_classifier": "K-Nearest Neighbors Classifier",
    "linear_regression": "Linear Regression",
    "ridge_regression": "Ridge Regression",
    "lasso_regression": "Lasso Regression",
    "random_forest_regressor": "Random Forest Regressor",
    "gradient_boosting_regressor": "Gradient Boosting Regressor",
    "decision_tree_regressor": "Decision Tree Regressor",
    "svm_regressor": "Support Vector Machine (SVR)",
    "knn_regressor": "K-Nearest Neighbors Regressor",
}


def _safe_hyper(params: dict | None, model_key: str) -> dict:
    """Sanitise LLM-suggested hyperparameters so they don't crash sklearn."""
    if not params:
        return {}

    clean: dict[str, Any] = {}

    # n_estimators (tree ensembles)
    if "n_estimators" in params and "forest" in model_key or "boosting" in model_key:
        try:
            n = int(params["n_estimators"])
            clean["n_estimators"] = max(10, min(n, 500))
        except (TypeError, ValueError):
            pass

    # max_depth
    if "max_depth" in params:
        try:
            d = int(params["max_depth"])
            clean["max_depth"] = max(1, min(d, 50))
        except (TypeError, ValueError):
            pass

    # n_neighbors (KNN)
    if "n_neighbors" in params and "knn" in model_key:
        try:
            k = int(params["n_neighbors"])
            clean["n_neighbors"] = max(1, min(k, 50))
        except (TypeError, ValueError):
            pass

    # C (SVM / Logistic)
    if "C" in params and ("svm" in model_key or "logistic" in model_key):
        try:
            c = float(params["C"])
            clean["C"] = max(0.001, min(c, 1000.0))
        except (TypeError, ValueError):
            pass

    # alpha (Ridge / Lasso)
    if "alpha" in params and ("ridge" in model_key or "lasso" in model_key):
        try:
            a = float(params["alpha"])
            clean["alpha"] = max(0.0001, min(a, 100.0))
        except (TypeError, ValueError):
            pass

    # learning_rate (Gradient Boosting)
    if "learning_rate" in params and "boosting" in model_key:
        try:
            lr = float(params["learning_rate"])
            clean["learning_rate"] = max(0.001, min(lr, 1.0))
        except (TypeError, ValueError):
            pass

    return clean


def _build_model(model_key: str, hyperparams: dict | None = None):
    """Instantiate a sklearn model from a key and optional hyper-parameters."""
    cls = _MODEL_MAP.get(model_key)
    if cls is None:
        raise ValueError(f"Unknown model key: {model_key}")

    safe_params = _safe_hyper(hyperparams, model_key)

    # SVM classifier needs probability=True for some metrics
    if model_key == "svm_classifier":
        safe_params.setdefault("probability", True)

    # Max-iter bump for logistic regression convergence
    if model_key == "logistic_regression":
        safe_params.setdefault("max_iter", 1000)

    return cls(**safe_params)


# ── Data preparation ──────────────────────────────────────────────────────────

def _prepare_data(
    df: pd.DataFrame,
    target_column: str,
    task_type: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str], LabelEncoder | None]:
    """Prepare features and target. Returns X_train, X_test, y_train, y_test, feature_names, label_encoder."""

    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found in the dataset.")

    # Separate target
    y = df[target_column].copy()
    X = df.drop(columns=[target_column]).copy()

    # Drop columns that are useless for prediction (IDs, high-cardinality text, dates)
    drop_cols = []
    for col in X.columns:
        if X[col].nunique() < 2:
            drop_cols.append(col)
            continue
        # Drop datetime columns (would need special treatment)
        if pd.api.types.is_datetime64_any_dtype(X[col]):
            drop_cols.append(col)
            continue
        # Drop very high cardinality text columns (likely IDs)
        if X[col].dtype == object:
            uniqueness = X[col].nunique() / max(len(X), 1)
            if uniqueness > 0.9:
                drop_cols.append(col)

    if drop_cols:
        X = X.drop(columns=drop_cols)

    if X.empty or X.shape[1] == 0:
        raise ValueError("No usable feature columns remain after filtering IDs and constants.")

    feature_names = list(X.columns)

    # Encode target for classification
    label_encoder = None
    if task_type == "classification":
        if y.dtype == object or str(y.dtype) == "category":
            label_encoder = LabelEncoder()
            y = y.fillna("__MISSING__")
            y = pd.Series(label_encoder.fit_transform(y))
        else:
            y = y.fillna(y.mode()[0] if not y.mode().empty else 0)
    else:
        y = pd.to_numeric(y, errors="coerce")
        y = y.fillna(y.median() if not y.isna().all() else 0)

    # Process features
    numeric_cols = X.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = X.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

    # Impute numeric
    if numeric_cols:
        num_imputer = SimpleImputer(strategy="median")
        X[numeric_cols] = num_imputer.fit_transform(X[numeric_cols])

    # Encode categorical
    cat_encoders = {}
    for col in categorical_cols:
        X[col] = X[col].fillna("__MISSING__").astype(str)
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col])
        cat_encoders[col] = le

    # Final conversion to numeric, drop any remaining non-numeric
    X = X.apply(pd.to_numeric, errors="coerce")
    X = X.fillna(0)

    # Train/test split
    test_size = 0.2
    # Ensure at least 2 samples per split
    if len(X) < 10:
        test_size = max(1 / len(X), 0.2)

    stratify = y if task_type == "classification" and y.nunique() > 1 and y.nunique() <= 50 else None

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X.values, y.values, test_size=test_size, random_state=42, stratify=stratify
        )
    except ValueError:
        # Fallback without stratification
        X_train, X_test, y_train, y_test = train_test_split(
            X.values, y.values, test_size=test_size, random_state=42
        )

    # Scale features
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    return X_train, X_test, y_train, y_test, feature_names, label_encoder


# ── Evaluation ────────────────────────────────────────────────────────────────

def _evaluate_classification(
    model, X_test, y_test, label_encoder: LabelEncoder | None
) -> dict[str, Any]:
    y_pred = model.predict(X_test)

    labels = None
    if label_encoder is not None:
        labels = list(label_encoder.classes_)

    cm = confusion_matrix(y_test, y_pred).tolist()
    avg = "weighted" if len(set(y_test)) > 2 else "binary"

    metrics = {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred, average=avg, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, average=avg, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_test, y_pred, average=avg, zero_division=0)), 4),
        "confusion_matrix": cm,
        "class_labels": labels,
    }

    # Sample predictions
    sample_size = min(20, len(X_test))
    actual = y_test[:sample_size]
    predicted = y_pred[:sample_size]
    if label_encoder is not None:
        actual = label_encoder.inverse_transform(actual.astype(int))
        predicted = label_encoder.inverse_transform(predicted.astype(int))

    samples = []
    for i in range(sample_size):
        samples.append({
            "index": i,
            "actual": str(actual[i]),
            "predicted": str(predicted[i]),
            "correct": str(actual[i]) == str(predicted[i]),
        })

    metrics["sample_predictions"] = samples
    return metrics


def _evaluate_regression(model, X_test, y_test) -> dict[str, Any]:
    y_pred = model.predict(X_test)

    mae = float(mean_absolute_error(y_test, y_pred))
    mse = float(mean_squared_error(y_test, y_pred))
    rmse = float(np.sqrt(mse))
    r2 = float(r2_score(y_test, y_pred))

    metrics = {
        "mae": round(mae, 4),
        "mse": round(mse, 4),
        "rmse": round(rmse, 4),
        "r2_score": round(r2, 4),
    }

    # Sample predictions
    sample_size = min(20, len(X_test))
    samples = []
    for i in range(sample_size):
        samples.append({
            "index": i,
            "actual": round(float(y_test[i]), 4),
            "predicted": round(float(y_pred[i]), 4),
            "error": round(float(abs(y_test[i] - y_pred[i])), 4),
        })

    metrics["sample_predictions"] = samples
    return metrics


def _get_feature_importances(model, feature_names: list[str]) -> list[dict[str, Any]]:
    """Extract feature importances from the trained model."""
    importances = None

    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    elif hasattr(model, "coef_"):
        coefs = model.coef_
        if coefs.ndim > 1:
            importances = np.mean(np.abs(coefs), axis=0)
        else:
            importances = np.abs(coefs)

    if importances is None:
        return []

    # Sort by importance descending
    indices = np.argsort(importances)[::-1]
    result = []
    for i in indices[:15]:  # Top 15 features
        result.append({
            "feature": feature_names[i] if i < len(feature_names) else f"feature_{i}",
            "importance": round(float(importances[i]), 4),
        })

    return result


# ── Prompt builders ───────────────────────────────────────────────────────────

def _target_selection_prompt(profile_summary: str) -> str:
    return f"""You are a senior data scientist. Analyze this dataset profile and determine the BEST column to use as a prediction target.

## Data Profile
{profile_summary}

## Instructions
- Choose the column that would be most valuable and meaningful to predict.
- Prefer columns that are likely outcome/result/target variables (e.g., price, status, label, category, revenue, sales, churn, survival, outcome).
- Avoid choosing ID columns, datetime columns, or columns that are just indices.
- Avoid choosing columns with very high cardinality text (those are inputs, not targets).
- Determine whether predicting this column is a classification task (categorical/discrete target) or a regression task (continuous numeric target).
- Be concise in your reasoning."""


def _model_selection_prompt(profile_summary: str, target_info: dict) -> str:
    return f"""You are a senior data scientist. Based on the dataset profile and target column analysis, choose the BEST scikit-learn model.

## Data Profile
{profile_summary}

## Target Column Analysis
- Target column: {target_info.get('target_column', 'unknown')}
- Task type: {target_info.get('task_type', 'unknown')}
- Reason for selection: {target_info.get('reason', '')}

## Instructions
- Consider the dataset size (row count), number of features, feature types, and data quality.
- For small datasets (<1000 rows): prefer simpler models (logistic/linear regression, decision tree, KNN).
- For medium datasets (1000-50000 rows): tree ensembles (random forest, gradient boosting) usually excel.
- For large datasets (>50000 rows): gradient boosting or linear models are efficient choices.
- If there are many features relative to samples, prefer regularized models (ridge, lasso, or tree-based).
- If the data has outliers, prefer robust models (tree-based over linear).
- Suggest sensible hyperparameters based on the data characteristics.
- Be concise in your reasoning."""


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def run_prediction_pipeline(
    session: dict[str, Any],
    ollama_client: OllamaClient,
) -> AsyncGenerator[dict[str, Any], None]:
    """Full prediction pipeline yielding SSE-ready dicts.

    Events yielded:
      - {"type": "prediction_status", "status": str, "detail": str}
      - {"type": "prediction_target", "target": dict}
      - {"type": "prediction_model", "model": dict}
      - {"type": "prediction_result", "result": dict}
      - {"type": "prediction_error", "message": str}
    """
    df = session.get("df")
    if df is None or df.empty:
        yield {"type": "prediction_error", "message": "No dataset loaded in this session."}
        return

    profile = session.get("profile") or {}
    profile_summary = build_profile_summary(profile)
    columns = list((profile.get("columns") or {}).keys())

    if not columns:
        yield {"type": "prediction_error", "message": "Dataset has no columns to analyze."}
        return

    # ── Step 1: LLM picks the target column ──────────────────────────────

    yield {"type": "prediction_status", "status": "analyzing", "detail": "LLM is analyzing the dataset to choose the best target column..."}

    target_schema = _target_selection_schema(columns)
    target_prompt = _target_selection_prompt(profile_summary)

    try:
        target_raw = await ollama_client.generate_text(
            target_prompt,
            num_predict=400,
            temperature=0.2,
            format=target_schema,
        )
        target_info = json.loads(target_raw)
    except Exception as exc:
        logger.error("LLM target selection failed: %s", exc)
        yield {"type": "prediction_error", "message": f"LLM could not select a target column: {exc}"}
        return

    target_column = target_info.get("target_column")
    task_type = target_info.get("task_type", "classification")
    target_reason = target_info.get("reason", "")

    if not target_column or target_column not in columns:
        yield {"type": "prediction_error", "message": f"LLM selected invalid target column: {target_column}"}
        return

    yield {
        "type": "prediction_target",
        "target": {
            "column": target_column,
            "task_type": task_type,
            "reason": target_reason,
        },
    }

    # ── Step 2: LLM picks the model ──────────────────────────────────────

    yield {"type": "prediction_status", "status": "selecting_model", "detail": "LLM is choosing the best ML model for this data..."}

    model_schema = _model_selection_schema(task_type)
    model_prompt = _model_selection_prompt(profile_summary, target_info)

    try:
        model_raw = await ollama_client.generate_text(
            model_prompt,
            num_predict=500,
            temperature=0.2,
            format=model_schema,
        )
        model_info = json.loads(model_raw)
    except Exception as exc:
        logger.error("LLM model selection failed: %s", exc)
        yield {"type": "prediction_error", "message": f"LLM could not select a model: {exc}"}
        return

    model_key = model_info.get("model", "")
    model_reason = model_info.get("reason", "")
    model_hypers = model_info.get("hyperparameters") or {}

    if model_key not in _MODEL_MAP:
        # Fallback to a safe default
        model_key = "random_forest_classifier" if task_type == "classification" else "random_forest_regressor"
        model_reason += " (LLM suggested an unavailable model; falling back to Random Forest)"

    yield {
        "type": "prediction_model",
        "model": {
            "key": model_key,
            "display_name": _MODEL_DISPLAY_NAMES.get(model_key, model_key),
            "task_type": task_type,
            "reason": model_reason,
            "hyperparameters": model_hypers,
        },
    }

    # ── Step 3: Prepare data ─────────────────────────────────────────────

    yield {"type": "prediction_status", "status": "preparing", "detail": "Preparing data: imputing, encoding, splitting (80/20)..."}

    try:
        X_train, X_test, y_train, y_test, feature_names, label_encoder = _prepare_data(
            df, target_column, task_type
        )
    except Exception as exc:
        logger.error("Data preparation failed: %s", exc)
        yield {"type": "prediction_error", "message": f"Data preparation failed: {exc}"}
        return

    yield {
        "type": "prediction_status",
        "status": "prepared",
        "detail": f"Data prepared: {len(X_train)} training samples, {len(X_test)} test samples, {len(feature_names)} features.",
    }

    # ── Step 4: Train ────────────────────────────────────────────────────

    yield {"type": "prediction_status", "status": "training", "detail": f"Training {_MODEL_DISPLAY_NAMES.get(model_key, model_key)}..."}

    try:
        model = _build_model(model_key, model_hypers)
        model.fit(X_train, y_train)
    except Exception as exc:
        logger.error("Model training failed: %s", exc)
        yield {"type": "prediction_error", "message": f"Model training failed: {exc}"}
        return

    # ── Step 5: Evaluate ─────────────────────────────────────────────────

    yield {"type": "prediction_status", "status": "evaluating", "detail": "Evaluating model performance..."}

    try:
        if task_type == "classification":
            metrics = _evaluate_classification(model, X_test, y_test, label_encoder)
        else:
            metrics = _evaluate_regression(model, X_test, y_test)

        feature_importances = _get_feature_importances(model, feature_names)
    except Exception as exc:
        logger.error("Evaluation failed: %s", exc)
        yield {"type": "prediction_error", "message": f"Model evaluation failed: {exc}"}
        return

    # ── Final result ─────────────────────────────────────────────────────

    yield {
        "type": "prediction_result",
        "result": {
            "target_column": target_column,
            "target_reason": target_reason,
            "task_type": task_type,
            "model_key": model_key,
            "model_display_name": _MODEL_DISPLAY_NAMES.get(model_key, model_key),
            "model_reason": model_reason,
            "hyperparameters": model_hypers,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "feature_count": len(feature_names),
            "feature_names": feature_names,
            "feature_importances": feature_importances,
            "metrics": metrics,
        },
    }
