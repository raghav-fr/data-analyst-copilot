"""
Chart Service — generates EDA and statistical charts using matplotlib/seaborn/plotly.
Returns base64-encoded PNG images for the frontend.
"""
import io
import base64
import logging
from typing import Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Use non-interactive backend
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns

# Light theme palette
BG_COLOR = "#ffffff"
PANEL_BG = "#f8fafc"
BORDER = "#e2e8f0"
TEXT_COLOR = "#0f172a"
MUTED_TEXT = "#475569"
ACCENT = "#4f8ef7"
ACCENT2 = "#22d3ee"
COLORS = ["#4f8ef7", "#22d3ee", "#f59e0b", "#10b981", "#f43f5e", "#a78bfa", "#fb923c", "#34d399"]


def _apply_theme(fig, ax=None):
    """Apply consistent light theme to figure."""
    fig.patch.set_facecolor(BG_COLOR)
    if ax:
        axes = [ax] if not isinstance(ax, (list, np.ndarray)) else ax.flatten()
        for a in axes:
            a.set_facecolor(PANEL_BG)
            a.spines["top"].set_visible(False)
            a.spines["right"].set_visible(False)
            a.spines["left"].set_color(BORDER)
            a.spines["bottom"].set_color(BORDER)
            a.tick_params(colors=MUTED_TEXT, labelsize=9)
            a.xaxis.label.set_color(MUTED_TEXT)
            a.yaxis.label.set_color(MUTED_TEXT)
            a.title.set_color(TEXT_COLOR)
    return fig


def _fig_to_base64(fig) -> str:
    """Convert matplotlib figure to base64 string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
    buf.seek(0)
    result = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return result


def generate_histogram(df: pd.DataFrame, column: str) -> str:
    """Histogram with KDE overlay."""
    series = df[column].dropna()
    fig, ax = plt.subplots(figsize=(8, 5))
    _apply_theme(fig, ax)

    ax.hist(series, bins=30, color=ACCENT, alpha=0.7, edgecolor=BORDER, linewidth=0.5)

    # KDE overlay
    try:
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(series)
        x_range = np.linspace(series.min(), series.max(), 200)
        ax2 = ax.twinx()
        ax2.plot(x_range, kde(x_range), color=ACCENT2, linewidth=2, alpha=0.8)
        ax2.set_yticks([])
        ax2.set_facecolor(PANEL_BG)
    except Exception:
        pass

    ax.set_title(f"Distribution of {column}", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel(column, labelpad=8)
    ax.set_ylabel("Frequency", labelpad=8)

    # Add stats annotation
    stats_text = f"Mean: {series.mean():.2f}  |  Median: {series.median():.2f}  |  Std: {series.std():.2f}"
    ax.text(0.5, -0.12, stats_text, transform=ax.transAxes, ha="center",
            fontsize=8, color=MUTED_TEXT)

    fig.tight_layout()
    return _fig_to_base64(fig)


def generate_boxplot(df: pd.DataFrame, column: str) -> str:
    """Styled boxplot."""
    series = df[column].dropna()
    fig, ax = plt.subplots(figsize=(8, 5))
    _apply_theme(fig, ax)

    bp = ax.boxplot(series, patch_artist=True, vert=True,
                    boxprops=dict(facecolor=ACCENT, alpha=0.6, linewidth=1.5),
                    medianprops=dict(color=ACCENT2, linewidth=2.5),
                    whiskerprops=dict(color=MUTED_TEXT, linewidth=1.5),
                    capprops=dict(color=MUTED_TEXT, linewidth=1.5),
                    flierprops=dict(marker="o", color=COLORS[4], alpha=0.5, markersize=4))

    ax.set_title(f"Boxplot of {column}", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("")
    ax.set_ylabel(column, labelpad=8)
    ax.set_xticks([])

    # Overlay jitter
    jitter = np.random.normal(1, 0.04, size=min(len(series), 200))
    ax.scatter(jitter, series.sample(min(len(series), 200), random_state=42),
               alpha=0.3, s=10, color=ACCENT2, zorder=3)

    fig.tight_layout()
    return _fig_to_base64(fig)


def generate_correlation_heatmap(df: pd.DataFrame) -> str:
    """Correlation heatmap for numeric columns."""
    numeric_df = df.select_dtypes(include=[np.number])
    if len(numeric_df.columns) < 2:
        return None

    corr = numeric_df.corr()
    n = len(corr.columns)
    fig_size = max(8, min(16, n * 0.9))
    fig, ax = plt.subplots(figsize=(fig_size, fig_size * 0.8))
    _apply_theme(fig, ax)

    # Custom colormap
    import matplotlib.colors as mcolors
    cmap = plt.cm.RdYlGn

    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(
        corr, ax=ax, annot=True, fmt=".2f", cmap=cmap,
        vmin=-1, vmax=1, square=True, linewidths=0.5,
        linecolor=BORDER, cbar_kws={"shrink": 0.8},
        annot_kws={"size": max(6, 10 - n // 3), "color": "white"},
    )

    ax.set_title("Correlation Heatmap", fontsize=13, fontweight="bold", pad=12)
    plt.xticks(rotation=45, ha="right", fontsize=9, color=MUTED_TEXT)
    plt.yticks(rotation=0, fontsize=9, color=MUTED_TEXT)

    # Style colorbar
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(colors=MUTED_TEXT, labelsize=8)

    fig.tight_layout()
    return _fig_to_base64(fig)


def generate_countplot(df: pd.DataFrame, column: str, top_n: int = 15) -> str:
    """Count plot for categorical columns."""
    value_counts = df[column].value_counts().head(top_n)
    fig, ax = plt.subplots(figsize=(10, 5))
    _apply_theme(fig, ax)

    bars = ax.barh(value_counts.index.astype(str), value_counts.values,
                   color=COLORS[:len(value_counts)], alpha=0.85, edgecolor=BORDER)

    # Value labels
    for bar, val in zip(bars, value_counts.values):
        ax.text(bar.get_width() + max(value_counts.values) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:,}", va="center", ha="left", fontsize=8, color=MUTED_TEXT)

    ax.set_title(f"Value Counts: {column}", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Count", labelpad=8)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.3, color=BORDER)

    fig.tight_layout()
    return _fig_to_base64(fig)


def generate_scatter_plot(df: pd.DataFrame, x_col: str, y_col: str, hue_col: Optional[str] = None) -> str:
    """Scatter plot with optional color grouping."""
    fig, ax = plt.subplots(figsize=(9, 6))
    _apply_theme(fig, ax)

    if hue_col and hue_col in df.columns:
        categories = df[hue_col].unique()[:8]
        for i, cat in enumerate(categories):
            mask = df[hue_col] == cat
            ax.scatter(df.loc[mask, x_col], df.loc[mask, y_col],
                       label=str(cat), color=COLORS[i % len(COLORS)],
                       alpha=0.6, s=30, edgecolors="none")
        ax.legend(fontsize=8, labelcolor=TEXT_COLOR, facecolor=PANEL_BG, edgecolor=BORDER)
    else:
        ax.scatter(df[x_col], df[y_col], color=ACCENT, alpha=0.5, s=30, edgecolors="none")

    # Trendline
    try:
        x_clean = df[x_col].dropna()
        y_clean = df[y_col].dropna()
        common_idx = x_clean.index.intersection(y_clean.index)
        z = np.polyfit(x_clean[common_idx], y_clean[common_idx], 1)
        p = np.poly1d(z)
        x_line = np.linspace(x_clean.min(), x_clean.max(), 100)
        ax.plot(x_line, p(x_line), color=ACCENT2, linewidth=1.5, alpha=0.8, linestyle="--")
    except Exception:
        pass

    ax.set_xlabel(x_col, labelpad=8)
    ax.set_ylabel(y_col, labelpad=8)
    ax.set_title(f"{x_col} vs {y_col}", fontsize=13, fontweight="bold", pad=12)
    ax.grid(alpha=0.2, color=BORDER)

    fig.tight_layout()
    return _fig_to_base64(fig)


def generate_pairplot(df: pd.DataFrame, columns: Optional[list] = None) -> str:
    """Pairplot for numeric columns."""
    numeric_df = df.select_dtypes(include=[np.number])
    if columns:
        numeric_df = numeric_df[[c for c in columns if c in numeric_df.columns]]

    # Limit to 5 columns for readability
    numeric_df = numeric_df.iloc[:, :5].dropna()

    if len(numeric_df.columns) < 2:
        return None

    n = len(numeric_df.columns)
    fig, axes = plt.subplots(n, n, figsize=(n * 2.5, n * 2.5))
    fig.patch.set_facecolor(BG_COLOR)

    for i, col_i in enumerate(numeric_df.columns):
        for j, col_j in enumerate(numeric_df.columns):
            ax = axes[i, j]
            ax.set_facecolor(PANEL_BG)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color(BORDER)
            ax.spines["bottom"].set_color(BORDER)
            ax.tick_params(colors=MUTED_TEXT, labelsize=7)

            if i == j:
                ax.hist(numeric_df[col_i], bins=20, color=ACCENT, alpha=0.7, edgecolor="none")
            else:
                ax.scatter(numeric_df[col_j], numeric_df[col_i], s=5,
                           color=ACCENT, alpha=0.4, edgecolors="none")

            if i == 0:
                ax.set_title(col_j, fontsize=8, color=TEXT_COLOR, pad=4)
            if j == 0:
                ax.set_ylabel(col_i, fontsize=8, color=MUTED_TEXT)

    fig.suptitle("Pair Plot", fontsize=12, fontweight="bold", color=TEXT_COLOR, y=1.01)
    fig.tight_layout()
    return _fig_to_base64(fig)


def generate_line_chart(df: pd.DataFrame, x_col: str, y_col: str) -> str:
    """Line chart for time series or sequential data."""
    fig, ax = plt.subplots(figsize=(10, 5))
    _apply_theme(fig, ax)

    sorted_df = df[[x_col, y_col]].dropna().sort_values(x_col)
    ax.plot(sorted_df[x_col], sorted_df[y_col], color=ACCENT, linewidth=2, alpha=0.9)
    ax.fill_between(sorted_df[x_col], sorted_df[y_col], alpha=0.15, color=ACCENT)

    ax.set_xlabel(x_col, labelpad=8)
    ax.set_ylabel(y_col, labelpad=8)
    ax.set_title(f"{y_col} over {x_col}", fontsize=13, fontweight="bold", pad=12)
    ax.grid(alpha=0.2, color=BORDER)
    plt.xticks(rotation=30, ha="right")

    fig.tight_layout()
    return _fig_to_base64(fig)


def generate_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, agg: str = "sum", top_n: int = 20) -> str:
    """Grouped/aggregated bar chart."""
    agg_df = df.groupby(x_col)[y_col].agg(agg).sort_values(ascending=False).head(top_n)

    fig, ax = plt.subplots(figsize=(max(8, len(agg_df) * 0.5), 6))
    _apply_theme(fig, ax)

    gradient_colors = plt.cm.cool(np.linspace(0.3, 0.9, len(agg_df)))
    bars = ax.bar(agg_df.index.astype(str), agg_df.values, color=gradient_colors, alpha=0.85, edgecolor=BORDER)

    # Labels on bars
    for bar in bars:
        val = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, val + max(agg_df.values) * 0.01,
                f"{val:,.1f}", ha="center", va="bottom", fontsize=7, color=MUTED_TEXT)

    ax.set_xlabel(x_col, labelpad=8)
    ax.set_ylabel(f"{agg}({y_col})", labelpad=8)
    ax.set_title(f"{agg.title()} of {y_col} by {x_col}", fontsize=13, fontweight="bold", pad=12)
    ax.grid(axis="y", alpha=0.2, color=BORDER)
    plt.xticks(rotation=45, ha="right", fontsize=8)

    fig.tight_layout()
    return _fig_to_base64(fig)


def generate_missing_heatmap(df: pd.DataFrame) -> str:
    """Missing value heatmap."""
    fig, ax = plt.subplots(figsize=(max(8, len(df.columns) * 0.5), 6))
    _apply_theme(fig, ax)

    missing_pct = (df.isnull().sum() / len(df) * 100).sort_values(ascending=False)
    missing_pct = missing_pct[missing_pct > 0]

    if missing_pct.empty:
        ax.text(0.5, 0.5, "✅ No missing values!", transform=ax.transAxes,
                ha="center", va="center", fontsize=14, color=COLORS[3])
        ax.set_title("Missing Values", fontsize=13, fontweight="bold")
        return _fig_to_base64(fig)

    colors = [COLORS[4] if v > 30 else COLORS[2] if v > 10 else COLORS[3] for v in missing_pct.values]
    bars = ax.barh(missing_pct.index, missing_pct.values, color=colors, alpha=0.8, edgecolor=BORDER)

    for bar, val in zip(bars, missing_pct.values):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=8, color=MUTED_TEXT)

    ax.set_xlabel("Missing (%)", labelpad=8)
    ax.set_title("Missing Values by Column", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlim(0, max(missing_pct.values) * 1.15)
    ax.invert_yaxis()

    fig.tight_layout()
    return _fig_to_base64(fig)
