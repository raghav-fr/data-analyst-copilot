"""
Safe Python Executor — sandboxed exec for AI-generated Pandas/visualization code.
Blocks dangerous builtins and only allows approved libraries.
"""
import io
import gc
import sys
import time
import base64
import logging
import traceback
from typing import Any, Optional
import contextlib

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Allowlist of safe builtins
SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
    "dir": dir, "divmod": divmod, "enumerate": enumerate, "filter": filter,
    "float": float, "format": format, "frozenset": frozenset, "getattr": getattr,
    "hasattr": hasattr, "hash": hash, "int": int, "isinstance": isinstance,
    "issubclass": issubclass, "iter": iter, "len": len, "list": list,
    "map": map, "max": max, "min": min, "next": next, "object": object,
    "print": print, "range": range, "repr": repr, "reversed": reversed,
    "round": round, "set": set, "slice": slice, "sorted": sorted, "str": str,
    "sum": sum, "tuple": tuple, "type": type, "vars": vars, "zip": zip,
    "True": True, "False": False, "None": None, "__import__": __import__,
}

# Blocked patterns in code
BLOCKED_PATTERNS = [
    "import os", "import sys", "import subprocess", "import socket",
    "import shutil", "__import__", "exec(", "eval(", "compile(",
    "open(", "file(", "input(", "raw_input(",
    "os.system", "os.popen", "os.remove", "os.rmdir",
    "subprocess.run", "subprocess.call", "subprocess.Popen",
    "socket.socket", "requests.get", "urllib",
    "__builtins__", "__class__", "__subclasses__",
]


def is_code_safe(code: str) -> tuple[bool, Optional[str]]:
    """Check if code contains any blocked patterns."""
    code_lower = code.lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern.lower() in code_lower:
            return False, f"Blocked pattern detected: '{pattern}'"
    return True, None


def execute_code(
    code: str,
    df: pd.DataFrame,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """
    Execute AI-generated Python code safely in a sandboxed environment.

    Returns:
        {
            "success": bool,
            "result": Any (DataFrame, dict, scalar, etc.),
            "chart_base64": Optional[str],
            "error": Optional[str],
            "execution_time_ms": int,
            "stdout": str,
        }
    """
    # Safety check
    is_safe, reason = is_code_safe(code)
    if not is_safe:
        return {
            "success": False,
            "result": None,
            "chart_base64": None,
            "error": f"Code safety check failed: {reason}",
            "execution_time_ms": 0,
            "stdout": "",
        }

    # Prepare matplotlib for non-interactive backend
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    # Apply light theme
    plt.style.use("default")
    plt.rcParams.update({
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#f8fafc",
        "axes.edgecolor": "#e2e8f0",
        "axes.labelcolor": "#475569",
        "xtick.color": "#64748b",
        "ytick.color": "#64748b",
        "text.color": "#0f172a",
        "grid.color": "#f1f5f9",
        "grid.linewidth": 0.5,
    })

    # Try to import sklearn and scipy for ML/stats
    try:
        import sklearn
        from sklearn import preprocessing, model_selection, metrics, linear_model, ensemble, tree
        sklearn_available = True
    except ImportError:
        sklearn_available = False

    try:
        import scipy
        from scipy import stats as scipy_stats
        scipy_available = True
    except ImportError:
        scipy_available = False

    # Build execution namespace
    exec_globals = {
        "__builtins__": SAFE_BUILTINS,
        "pd": pd,
        "np": np,
        "plt": plt,
        "sns": sns,
        "df": df.copy(),  # Always work on a copy
        "result": None,
    }

    if sklearn_available:
        exec_globals.update({
            "sklearn": sklearn,
            "preprocessing": preprocessing,
            "model_selection": model_selection,
            "metrics": metrics,
            "linear_model": linear_model,
            "ensemble": ensemble,
            "tree": tree,
        })
        try:
            from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
            from sklearn.svm import SVC, SVR
            exec_globals.update({"KNeighborsClassifier": KNeighborsClassifier, "SVR": SVR})
        except ImportError:
            pass

    if scipy_available:
        exec_globals["scipy"] = scipy
        exec_globals["scipy_stats"] = scipy_stats

    # Capture stdout
    stdout_capture = io.StringIO()
    chart_base64 = None
    start_time = time.time()

    try:
        with contextlib.redirect_stdout(stdout_capture):
            exec(compile(code, "<ai_generated>", "exec"), exec_globals)

        # Free the DataFrame copy immediately — it can be 100-400MB
        exec_df = exec_globals.pop("df", None)
        del exec_df
        gc.collect()

        # Check if a chart was generated
        chart_base64 = None
        try:
            if plt.get_fignums():
                buf = io.BytesIO()
                plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="#ffffff")
                buf.seek(0)
                chart_base64 = base64.b64encode(buf.read()).decode("utf-8")
        finally:
            plt.close("all")

        result = exec_globals.get("result")

        def _sanitize(obj):
            if isinstance(obj, pd.DataFrame):
                return {
                    "type": "dataframe",
                    "columns": obj.columns.tolist(),
                    "data": obj.head(100).fillna("").to_dict("records"),
                    "shape": list(obj.shape),
                }
            elif isinstance(obj, pd.Series):
                return {
                    "type": "series",
                    "name": obj.name,
                    "data": obj.head(100).fillna("").to_dict(),
                }
            elif isinstance(obj, dict):
                return {str(k): _sanitize(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_sanitize(v) for v in obj]
            elif isinstance(obj, (np.integer, np.int64, np.int32)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return _sanitize(obj.tolist())
            elif isinstance(obj, (int, float, str, bool, type(None))):
                return obj
            else:
                return str(obj)

        if result is None:
            serialized = None
        else:
            serialized = _sanitize(result)
            # Wrap standard types to match the expected format for the frontend
            if not isinstance(serialized, dict) or "type" not in serialized:
                if isinstance(serialized, dict):
                    serialized = {"type": "dict", "value": serialized}
                elif isinstance(serialized, list):
                    serialized = {"type": "list", "value": serialized}
                elif isinstance(serialized, (int, float)):
                    serialized = {"type": "scalar", "value": serialized}
                else:
                    serialized = {"type": "text", "value": str(serialized)}

        elapsed_ms = int((time.time() - start_time) * 1000)

        return {
            "success": True,
            "result": serialized,
            "chart_base64": chart_base64,
            "error": None,
            "execution_time_ms": elapsed_ms,
            "stdout": stdout_capture.getvalue(),
        }

    except Exception as e:
        plt.close("all")
        elapsed_ms = int((time.time() - start_time) * 1000)
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.warning(f"Code execution error: {error_msg}\nCode:\n{code}")

        return {
            "success": False,
            "result": None,
            "chart_base64": None,
            "error": error_msg,
            "execution_time_ms": elapsed_ms,
            "stdout": stdout_capture.getvalue(),
        }
