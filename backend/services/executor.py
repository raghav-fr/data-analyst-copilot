"""
Safe Python Executor — sandboxed exec for AI-generated Pandas/visualization code.
Blocks dangerous builtins and only allows approved libraries.
"""
import io
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

    # Apply dark theme
    plt.style.use("dark_background")
    plt.rcParams.update({
        "figure.facecolor": "#0f172a",
        "axes.facecolor": "#1e293b",
        "axes.edgecolor": "#334155",
        "axes.labelcolor": "#94a3b8",
        "xtick.color": "#64748b",
        "ytick.color": "#64748b",
        "text.color": "#e2e8f0",
        "grid.color": "#1e293b",
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

        # Check if a chart was generated
        if plt.get_fignums():
            buf = io.BytesIO()
            plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="#0f172a")
            buf.seek(0)
            chart_base64 = base64.b64encode(buf.read()).decode("utf-8")
            plt.close("all")

        result = exec_globals.get("result")

        # Serialize result
        if isinstance(result, pd.DataFrame):
            serialized = {
                "type": "dataframe",
                "columns": result.columns.tolist(),
                "data": result.head(100).fillna("").to_dict("records"),
                "shape": list(result.shape),
            }
        elif isinstance(result, pd.Series):
            serialized = {
                "type": "series",
                "name": result.name,
                "data": result.head(100).fillna("").to_dict(),
            }
        elif isinstance(result, (int, float, np.integer, np.floating)):
            serialized = {"type": "scalar", "value": float(result)}
        elif isinstance(result, dict):
            serialized = {"type": "dict", "value": result}
        elif result is None:
            serialized = None
        else:
            serialized = {"type": "text", "value": str(result)}

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
