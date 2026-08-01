"""Export route — CSV, Excel, PDF, JSON exports."""
import os
import io
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from services.auth_service import get_current_user
from fastapi.responses import FileResponse, StreamingResponse
from models.schemas import ExportRequest
from services.data_service import get_dataframe, get_dataset_meta

logger = logging.getLogger(__name__)
router = APIRouter()

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")


@router.post("/")
async def export_dataset(request: ExportRequest):
    """Export dataset in the requested format."""
    df = get_dataframe(request.dataset_id, current_user.uid)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    meta = get_dataset_meta(request.dataset_id) or {}
    filename = meta.get("filename", "export")
    base_name = os.path.splitext(filename)[0]

    fmt = request.format.lower()

    if fmt == "csv":
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        buf.seek(0)
        return StreamingResponse(
            io.BytesIO(buf.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{base_name}.csv"'}
        )

    elif fmt == "json":
        buf = io.BytesIO(df.to_json(orient="records", indent=2).encode())
        return StreamingResponse(
            buf,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{base_name}.json"'}
        )

    elif fmt == "excel":
        buf = io.BytesIO()
        with _get_excel_writer(buf) as writer:
            df.to_excel(writer, sheet_name="Data", index=False)
            if request.include_profile:
                _write_profile_sheet(writer, df)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{base_name}.xlsx"'}
        )

    elif fmt == "pdf":
        pdf_bytes = await _generate_pdf_report(df, meta, request)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{base_name}_report.pdf"'}
        )

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}")


def _get_excel_writer(buf):
    import pandas as pd
    return pd.ExcelWriter(buf, engine="xlsxwriter")


def _write_profile_sheet(writer, df):
    import pandas as pd
    import numpy as np
    profile_data = {
        "Column": df.columns.tolist(),
        "Type": [str(dtype) for dtype in df.dtypes],
        "Missing": df.isnull().sum().tolist(),
        "Missing%": [round(v / len(df) * 100, 2) for v in df.isnull().sum()],
        "Unique": df.nunique().tolist(),
    }
    profile_df = pd.DataFrame(profile_data)
    profile_df.to_excel(writer, sheet_name="Profile", index=False)

    desc = df.describe().T.reset_index()
    desc.columns = ["Column"] + list(desc.columns[1:])
    desc.to_excel(writer, sheet_name="Statistics", index=False)


async def _generate_pdf_report(df, meta, request):
    """Generate a PDF report using reportlab."""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor, black, white
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=50, leftMargin=50,
                                topMargin=50, bottomMargin=50)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        title_style = ParagraphStyle(
            "Title", parent=styles["Title"],
            fontSize=22, textColor=HexColor("#6366f1"),
            spaceAfter=6, alignment=TA_CENTER
        )
        elements.append(Paragraph("Data Analysis Report", title_style))
        elements.append(Paragraph(
            f"Dataset: {meta.get('filename', 'Unknown')} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            ParagraphStyle("Sub", parent=styles["Normal"], fontSize=9,
                           textColor=HexColor("#94a3b8"), alignment=TA_CENTER)
        ))
        elements.append(Spacer(1, 20))
        elements.append(HRFlowable(width="100%", thickness=1, color=HexColor("#334155")))
        elements.append(Spacer(1, 16))

        # Dataset Overview
        elements.append(Paragraph("Dataset Overview", styles["Heading2"]))
        overview_data = [
            ["Metric", "Value"],
            ["Total Rows", f"{len(df):,}"],
            ["Total Columns", str(len(df.columns))],
            ["Missing Values", f"{int(df.isnull().sum().sum()):,}"],
            ["Duplicate Rows", f"{int(df.duplicated().sum()):,}"],
            ["Memory Usage", f"{round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2)} MB"],
        ]
        t = Table(overview_data, colWidths=[3 * inch, 3 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#6366f1")),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f8fafc"), HexColor("#f1f5f9")]),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 16))

        # Column Summary
        elements.append(Paragraph("Column Summary", styles["Heading2"]))
        col_data = [["Column", "Type", "Missing", "Missing%", "Unique"]]
        for col in df.columns[:20]:
            col_data.append([
                col[:30],
                str(df[col].dtype),
                str(int(df[col].isnull().sum())),
                f"{round(df[col].isnull().sum() / len(df) * 100, 1)}%",
                str(int(df[col].nunique())),
            ])

        ct = Table(col_data, colWidths=[2.5 * inch, 1.2 * inch, 1 * inch, 1 * inch, 1 * inch])
        ct.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#22d3ee")),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#0f172a")),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#e2e8f0")),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(ct)

        doc.build(elements)
        buf.seek(0)
        return buf.read()

    except ImportError:
        # Fallback: return simple text PDF
        return b"%PDF-1.0\n% Simple PDF - install reportlab for full reports"
