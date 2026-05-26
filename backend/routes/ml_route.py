from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from auth.jwt_handler import CurrentUser, require_any_staff
from database import get_db
from models.sql_models import Patient, Department
from ml.bed_forecast import forecast_bed_demand
from ml.readmission_risk import score_readmission_risk

router = APIRouter(prefix="/api/ml", tags=["Machine Learning"])

@router.get("/bed-forecast/{dept}")
async def get_bed_forecast(dept: str, periods: int = 30, user: CurrentUser = Depends(require_any_staff)):
    """Prophet-based bed demand forecasting."""
    forecast = forecast_bed_demand(dept, periods=periods)
    return forecast

@router.get("/readmission/{patient_id}")
async def get_readmission_risk(patient_id: int, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(require_any_staff)):
    """Logistic regression model for patient readmission risk scoring."""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
        
    dept_result = await db.execute(select(Department).where(Department.id == patient.department_id))
    department = dept_result.scalar_one_or_none()
    dept_name = department.name if department else "Unknown"
    
    # Calculate approximate LOS
    los_days = 0
    if patient.admission_date and patient.discharge_date:
        los_days = (patient.discharge_date - patient.admission_date).days
    elif patient.admission_date:
        from datetime import date
        los_days = (date.today() - patient.admission_date).days
    
    # Using encrypted fields would normally require decryption here.
    # For now, we estimate or use placeholders for icd_code
    icd_code = "Z" # Default/Placeholder
    
    risk = score_readmission_risk(
        patient_id=patient_id,
        age=patient.age or 45,
        los_days=los_days or 1,
        department=dept_name,
        prev_admissions=0,
        icd_code=icd_code,
        is_emergency=(patient.patient_type == "emergency"),
    )
    return risk
