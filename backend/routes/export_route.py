from io import BytesIO
from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse
from auth.jwt_handler import CurrentUser, require_ceo_or_finance
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False
    
import openpyxl

router = APIRouter(prefix="/api/export", tags=["Export"])

@router.get("/pdf/overview")
async def export_pdf_overview(user: CurrentUser = Depends(require_ceo_or_finance)):
    if not WEASYPRINT_AVAILABLE:
        from fastapi import HTTPException
        raise HTTPException(status_code=501, detail="PDF generation is unavailable due to missing system dependencies.")
        
    # Basic PDF generation using WeasyPrint
    html_content = """
    <html>
        <head>
            <style>
                body { font-family: sans-serif; }
                h1 { color: #1e3a8a; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
                th { background-color: #f3f4f6; }
            </style>
        </head>
        <body>
            <h1>Aarogya Hospital CEO Dashboard</h1>
            <p>Confidential Business Intelligence Report</p>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Annual Revenue</td><td>₹120M</td></tr>
                <tr><td>Net Profit</td><td>₹25M</td></tr>
                <tr><td>Total Patients</td><td>15,420</td></tr>
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
async def export_excel_overview(user: CurrentUser = Depends(require_ceo_or_finance)):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Overview Report"
    
    headers = ["Metric", "Value", "Status"]
    ws.append(headers)
    ws.append(["Annual Revenue", "120M", "Healthy"])
    ws.append(["Net Profit", "25M", "Healthy"])
    ws.append(["Bed Occupancy", "78%", "Warning"])
    
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="hospital_overview.xlsx"'}
    )
