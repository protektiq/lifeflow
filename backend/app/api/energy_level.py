"""Energy Level API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, Field
from app.database import supabase
from app.api.auth import get_current_user
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
security = HTTPBearer()


class EnergyLevelCreate(BaseModel):
    """Energy level creation model"""
    date: date
    energy_level: int = Field(..., ge=1, le=5, description="Energy level from 1 (low) to 5 (high)")


class EnergyLevelResponse(BaseModel):
    """Energy level response model"""
    id: str
    user_id: str
    date: date
    energy_level: int
    created_at: datetime
    updated_at: datetime


async def get_authenticated_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get authenticated user from JWT token"""
    try:
        user = get_current_user(credentials.credentials)
        return user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


@router.post("", response_model=EnergyLevelResponse, status_code=status.HTTP_201_CREATED)
async def create_energy_level(
    energy_level_data: EnergyLevelCreate,
    user = Depends(get_authenticated_user),
):
    """Store daily energy level"""
    try:
        # Check if entry already exists for this date
        existing = supabase.table("daily_energy_levels").select("*").eq(
            "user_id", user.id
        ).eq("date", energy_level_data.date.isoformat()).execute()
        
        if existing.data:
            # Update existing entry
            response = supabase.table("daily_energy_levels").update({
                "energy_level": energy_level_data.energy_level,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", existing.data[0]["id"]).execute()
            
            data = response.data[0]
        else:
            # Create new entry
            response = supabase.table("daily_energy_levels").insert({
                "user_id": user.id,
                "date": energy_level_data.date.isoformat(),
                "energy_level": energy_level_data.energy_level,
            }).execute()
            
            data = response.data[0]
        
        return EnergyLevelResponse(
            id=data["id"],
            user_id=data["user_id"],
            date=date.fromisoformat(data["date"]),
            energy_level=data["energy_level"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store energy level: {str(e)}",
        )


@router.get("", response_model=List[EnergyLevelResponse])
async def get_energy_levels(
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format YYYY-MM-DD)"),
    user = Depends(get_authenticated_user),
):
    """Retrieve energy levels for date range"""
    try:
        query = supabase.table("daily_energy_levels").select("*").eq(
            "user_id", user.id
        ).order("date", desc=False)
        
        if start_date:
            query = query.gte("date", start_date)
        
        if end_date:
            query = query.lte("date", end_date)
        
        response = query.execute()
        
        return [
            EnergyLevelResponse(
                id=item["id"],
                user_id=item["user_id"],
                date=date.fromisoformat(item["date"]),
                energy_level=item["energy_level"],
                created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00")),
            )
            for item in response.data
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch energy levels: {str(e)}",
        )


@router.get("/{target_date}", response_model=Optional[EnergyLevelResponse])
async def get_energy_level_for_date(
    target_date: str,
    user = Depends(get_authenticated_user),
):
    """Get energy level for a specific date"""
    try:
        response = supabase.table("daily_energy_levels").select("*").eq(
            "user_id", user.id
        ).eq("date", target_date).execute()
        
        if not response.data:
            return None
        
        data = response.data[0]
        return EnergyLevelResponse(
            id=data["id"],
            user_id=data["user_id"],
            date=date.fromisoformat(data["date"]),
            energy_level=data["energy_level"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch energy level: {str(e)}",
        )

