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
async def export_dataset(request: ExportRequest, current_user = Depends(get_current_user)):
    """Export dataset in the requested format."""
    df = get_dataframe(request.dataset_id, current_user.uid)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    meta = get_dataset_meta(request.dataset_id, current_user.uid) or {}
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
        pdf_bytes = await _generate_pdf_report(df, meta, request, current_user)
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


async def _generate_pdf_report(df, meta, request, current_user):
    """Generate a PDF report using reportlab, including detailed profile, EDA, and chats."""
    try:
        import base64
        import html
        import pandas as pd
        from firebase_admin import firestore
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor, white
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image, PageBreak, KeepTogether
        )
        from reportlab.lib.enums import TA_CENTER
        from services.data_service import get_df_info
        from services.chart_service import (
            generate_missing_heatmap, generate_correlation_heatmap, generate_histogram
        )

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=40, leftMargin=40,
                                topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()
        elements = []
        db = firestore.client()

        # Styles
        title_style = ParagraphStyle(
            "Title", parent=styles["Title"],
            fontSize=22, textColor=HexColor("#6366f1"),
            spaceAfter=6, alignment=TA_CENTER
        )
        heading_style = styles["Heading2"]
        subheading_style = ParagraphStyle(
            "Subheading", parent=styles["Heading3"],
            textColor=HexColor("#334155"),
            spaceAfter=8
        )
        normal_style = styles["Normal"]
        desc_style = ParagraphStyle(
            "Desc", parent=styles["Normal"],
            textColor=HexColor("#475569"),
            leading=14,
            spaceAfter=15
        )
        chat_user_style = ParagraphStyle(
            "ChatUser", parent=styles["Normal"],
            textColor=HexColor("#0f172a"),
            backColor=HexColor("#f1f5f9"),
            borderPadding=(8, 10, 8, 10),
            spaceAfter=10,
            spaceBefore=10,
            borderRadius=4,
        )
        chat_ai_style = ParagraphStyle(
            "ChatAI", parent=styles["Normal"],
            textColor=HexColor("#0f172a"),
            backColor=HexColor("#e0e7ff"),
            borderPadding=(8, 10, 8, 10),
            spaceAfter=15,
            borderRadius=4,
        )

        # Fetch AI EDA Summary from Firestore
        eda_summary = ""
        try:
            doc_ref = db.collection('users').document(current_user.uid).collection('datasets').document(request.dataset_id)
            ds_doc = doc_ref.get()
            if ds_doc.exists:
                eda_summary = ds_doc.to_dict().get("eda_summary_insight", "")
        except Exception:
            pass

        # ------------------- 1. TITLE & METADATA -------------------
        elements.append(Paragraph("Data Analysis Project Report", title_style))
        elements.append(Paragraph(
            f"Dataset: {meta.get('filename', 'Unknown')} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            ParagraphStyle("Sub", parent=styles["Normal"], fontSize=9,
                           textColor=HexColor("#94a3b8"), alignment=TA_CENTER)
        ))
        elements.append(Spacer(1, 15))
        elements.append(HRFlowable(width="100%", thickness=1, color=HexColor("#334155")))
        elements.append(Spacer(1, 15))

        # Dataset Description / AI Summary
        if eda_summary:
            import re
            elements.append(Paragraph("Dataset Description & AI Summary", heading_style))
            clean_summary = html.escape(eda_summary).replace("\n", "<br/>")
            # Replace **bold** with <b>bold</b>
            clean_summary = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', clean_summary)
            elements.append(Paragraph(clean_summary, desc_style))
            elements.append(Spacer(1, 10))

        # ------------------- 2. DATASET OVERVIEW -------------------
        elements.append(Paragraph("1. Dataset Overview", heading_style))
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
        elements.append(Spacer(1, 20))

        # ------------------- 3. DETAILED COLUMN PROFILE -------------------
        elements.append(PageBreak())
        elements.append(Paragraph("2. Detailed Column Profile", heading_style))
        elements.append(Paragraph("A breakdown of each column's statistics and characteristics, mirroring the UI structure.", desc_style))
        
        for col in df.columns[:30]:  # Limit to 30 columns for sanity
            col_type = str(df[col].dtype)
            missing = int(df[col].isnull().sum())
            missing_pct = round(missing / len(df) * 100, 1)
            unique = int(df[col].nunique())
            
            # Card header
            card_data = [
                [f"Column: {col}", f"Type: {col_type}"]
            ]
            
            # Basic stats
            card_data.append([
                f"Missing: {missing} ({missing_pct}%)",
                f"Unique: {unique}"
            ])
            
            # Detailed stats based on type
            if pd.api.types.is_numeric_dtype(df[col]):
                series = df[col].dropna()
                if not series.empty:
                    mean_val = round(float(series.mean()), 2)
                    med_val = round(float(series.median()), 2)
                    std_val = round(float(series.std()), 2)
                    min_val = round(float(series.min()), 2)
                    max_val = round(float(series.max()), 2)
                    card_data.append([f"Mean: {mean_val} | Median: {med_val} | Std: {std_val}", f"Min: {min_val} | Max: {max_val}"])
            else:
                top_vals = df[col].value_counts().head(3)
                top_str = ", ".join([f"{k} ({v})" for k, v in top_vals.items()])
                card_data.append(["Top Values:", top_str])
            
            ct = Table(card_data, colWidths=[3.5 * inch, 2.5 * inch])
            ct.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#e0e7ff")),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#0f172a")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 1), (-1, -1), HexColor("#f8fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]))
            
            elements.append(KeepTogether([ct, Spacer(1, 10)]))

        elements.append(PageBreak())

        # ------------------- 4. EDA CHARTS -------------------
        elements.append(Paragraph("3. Exploratory Data Analysis", heading_style))
        elements.append(Spacer(1, 10))
        
        df_info = get_df_info(df)
        numeric_cols = df_info.get("numeric_columns", [])
        
        def add_chart(b64_str, title):
            if b64_str:
                try:
                    img_data = base64.b64decode(b64_str)
                    img = Image(io.BytesIO(img_data), width=5*inch, height=3.5*inch)
                    elements.append(KeepTogether([
                        Paragraph(title, subheading_style),
                        img,
                        Spacer(1, 15)
                    ]))
                except Exception as e:
                    logger.warning(f"Failed to add chart {title} to PDF: {e}")

        try:
            missing_b64 = generate_missing_heatmap(df)
            add_chart(missing_b64, "Missing Values Heatmap")
        except Exception:
            pass

        if len(numeric_cols) >= 2:
            try:
                corr_b64 = generate_correlation_heatmap(df)
                add_chart(corr_b64, "Correlation Heatmap")
            except Exception:
                pass

        for col in numeric_cols[:2]:
            try:
                hist_b64 = generate_histogram(df, col)
                add_chart(hist_b64, f"Distribution of {col}")
            except Exception:
                pass

        # ------------------- 5. CHAT HISTORY -------------------
        elements.append(PageBreak())
        elements.append(Paragraph("4. AI Analysis & Chat History", heading_style))
        elements.append(Spacer(1, 10))
        
        try:
            convs_ref = db.collection('users').document(current_user.uid).collection('conversations')
            convs = convs_ref.where('dataset_id', '==', request.dataset_id).order_by('updated_at', direction=firestore.Query.DESCENDING).limit(1).stream()
            
            conv_id = None
            for c in convs:
                conv_id = c.id
                break
                
            if conv_id:
                msgs_ref = db.collection('users').document(current_user.uid).collection('conversations').document(conv_id).collection('messages')
                msgs = msgs_ref.order_by('created_at', direction=firestore.Query.ASCENDING).stream()
                
                msg_count = 0
                for m in msgs:
                    msg_data = m.to_dict()
                    role = msg_data.get("role")
                    content = msg_data.get("content", "")
                    
                    # Clean up content for reportlab
                    clean_content = content.replace("**", "").replace("`", "")
                    clean_content = html.escape(clean_content).replace("\n", "<br/>")
                    
                    if role == "user":
                        elements.append(KeepTogether([
                            Paragraph(f"<b>User:</b> {clean_content}", chat_user_style)
                        ]))
                    elif role == "assistant":
                        block = [Paragraph(f"<b>AI Assistant:</b><br/>{clean_content}", chat_ai_style)]
                        
                        chart_path = msg_data.get("chart_path")
                        if chart_path and chart_path.startswith("data:image"):
                            b64_str = chart_path.split(",")[1]
                            try:
                                img_data = base64.b64decode(b64_str)
                                img = Image(io.BytesIO(img_data), width=4*inch, height=3*inch)
                                block.append(img)
                            except Exception:
                                pass
                        elements.append(KeepTogether(block))
                    msg_count += 1
                    
                if msg_count == 0:
                    elements.append(Paragraph("No chat history available for this dataset.", normal_style))
            else:
                elements.append(Paragraph("No conversations found for this dataset.", normal_style))
        except Exception as e:
            logger.error(f"Failed to append chat history to PDF: {e}")
            elements.append(Paragraph("Failed to load chat history.", normal_style))

        # Build PDF
        doc.build(elements)
        buf.seek(0)
        return buf.read()

    except Exception as e:
        logger.error(f"PDF generation error: {e}", exc_info=True)
        return b"%PDF-1.0\n% Error generating PDF report. Please check server logs."
