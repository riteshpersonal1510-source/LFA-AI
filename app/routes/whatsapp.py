from typing import Optional
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.whatsapp.campaign_engine import campaign_engine
from app.services.whatsapp.queue import campaign_queue

router = APIRouter()

class GenerateRequest(BaseModel):
    leadIds: list[str]
    campaignId: Optional[str] = None

@router.post("/whatsapp/generate")
async def generate(request: GenerateRequest):
    campaign_id = request.campaignId or uuid.uuid4().hex[:12]
    try:
        result = await campaign_engine.generate_campaign(campaign_id, request.leadIds)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/whatsapp/campaign/{campaign_id}")
async def get_campaign_status(campaign_id: str):
    return campaign_queue.get_status(campaign_id)
