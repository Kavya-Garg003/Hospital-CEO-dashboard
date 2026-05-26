from io import BytesIO
from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from auth.jwt_handler import CurrentUser, require_ceo_or_finance
from database import get_db
from routes.ai_concierge import _get_live_context

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False
    
import openpyxl

router = APIRouter(prefix="/api/export", tags=["Export"])

@router.get("/pdf/overview")
async def export_pdf_overview(
    user: CurrentUser = Depends(require_ceo_or_finance),
    db: AsyncSession = Depends(get_db)
):
    if not WEASYPRINT_AVAILABLE:
        from fastapi import HTTPException
        raise HTTPException(status_code=501, detail="PDF generation is unavailable due to missing system dependencies.")
        
    context = await _get_live_context(db)
    
    # Basic PDF generation using WeasyPrint with real DB data
    html_content = f"""
    <html>
        <head>
            <style>
                body {{ font-family: sans-serif; }}
                h1 {{ color: #1e3a8a; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
                th {{ background-color: #f3f4f6; }}
            </style>
        </head>
        <body>
            <h1>Aarogya Hospital CEO Dashboard</h1>
            <p>Confidential Business Intelligence Report</p>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Annual Revenue (Cr)</td><td>₹{context.get('revenue_cr', 'N/A')} Cr</td></tr>
                <tr><td>Net Profit (Cr)</td><td>₹{context.get('profit_cr', 'N/A')} Cr</td></tr>
                <tr><td>Profit Margin</td><td>{context.get('margin', 'N/A')}%</td></tr>
                <tr><td>Total Patients</td><td>{context.get('total_patients', 'N/A')}</td></tr>
                <tr><td>Total Staff</td><td>{context.get('total_staff', 'N/A')}</td></tr>
                <tr><td>Bed Occupancy</td><td>{context.get('bor', 'N/A')}%</td></tr>
                <tr><td>Insurance Claims</td><td>{context.get('total_claims', 'N/A')} ({context.get('pending_claims', 'N/A')} pending)</td></tr>
                <tr><td>OT Utilization</td><td>{context.get('ot_util', 'N/A')}%</td></tr>
            </table>
            <p>Generated securely by Aarogya BI.</p>
        </body>
    </html>
    """
    pdf_bytes = HTML(string=html_content).write_pdf()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="hospital_overview.pdf"'}
    )

@router.get("/excel/overview")
async def export_excel_overview(
    user: CurrentUser = Depends(require_ceo_or_finance),
    db: AsyncSession = Depends(get_db)
):
    context = await _get_live_context(db)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Overview Report"
    
    headers = ["Metric", "Value"]
    ws.append(headers)
    ws.append(["Annual Revenue (Cr)", f"₹{context.get('revenue_cr', 'N/A')} Cr"])
    ws.append(["Net Profit (Cr)", f"₹{context.get('profit_cr', 'N/A')} Cr"])
    ws.append(["Profit Margin", f"{context.get('margin', 'N/A')}%"])
    ws.append(["Total Patients", context.get('total_patients', 'N/A')])
    ws.append(["Total Staff", context.get('total_staff', 'N/A')])
    ws.append(["Bed Occupancy", f"{context.get('bor', 'N/A')}%"])
    ws.append(["Total Claims", context.get('total_claims', 'N/A')])
    ws.append(["Pending Claims", context.get('pending_claims', 'N/A')])
    ws.append(["OT Utilization", f"{context.get('ot_util', 'N/A')}%"])
    
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="hospital_overview.xlsx"'}
    )
