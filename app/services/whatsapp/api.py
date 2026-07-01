"""FastAPI routes for WhatsApp automation."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...core.exception_handlers import ValidationException
from ..whatsapp.engine import whatsapp_engine
from ..whatsapp.logs import whatsapp_logger
from ..whatsapp.session import session_manager
from ..whatsapp.template_service import template_service
from ..whatsapp.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


class SendWhatsAppRequest(BaseModel):
    leadIds: list[str] = Field(
        ..., min_length=1, max_length=1000, description="Array of MongoDB lead ObjectIds"
    )


class SendWhatsAppResponse(BaseModel):
    status: str = Field(..., description="Session status")
    currentLead: str = Field(default="", description="Current lead being processed")
    totalLeads: int = Field(default=0, description="Total leads in session")
    completed: int = Field(default=0, description="Successfully processed leads")
    failed: int = Field(default=0, description="Failed leads")
    logs: list = Field(default_factory=list, description="Processing logs")
    sessionId: str = Field(default="", description="Unique session identifier")


class CampaignResponse(BaseModel):
    sessionId: str = Field(..., description="Unique session identifier")
    status: str = Field(..., description="Campaign status")
    totalLeads: int = Field(default=0, description="Total leads in campaign")
    completed: int = Field(default=0, description="Successfully sent leads")
    failed: int = Field(default=0, description="Failed leads")
    currentLead: str = Field(default="", description="Current lead being sent")


class GenerateMessagesRequest(BaseModel):
    leadIds: list[str] = Field(
        ..., min_length=1, max_length=1000, description="Array of MongoDB lead ObjectIds"
    )
    campaignId: Optional[str] = Field(
        None, description="Optional campaign ID; auto-generated if not provided"
    )


class LeadStatusResponse(BaseModel):
    leadId: str
    companyName: str
    phone: Optional[str] = None
    website: str = ""
    city: str = ""
    messageType: str = ""
    queuePosition: int = 0
    status: str
    error: Optional[str] = None
    attempts: int = 0
    durationMs: float = 0.0
    browserState: str = ""
    updatedAt: float = 0
    completedAt: Optional[float] = None


class DetailedSessionResponse(BaseModel):
    sessionId: str
    status: str
    totalLeads: int
    completed: int
    failed: int
    currentLead: Optional[str] = None
    currentLeadIndex: int = 0
    currentStep: str = ""
    error: Optional[str] = None
    eta: Optional[float] = None
    elapsedSeconds: float = 0.0
    processed: int = 0
    remaining: int = 0
    leads: list[LeadStatusResponse] = []
    createdAt: float
    completedAt: Optional[float] = None


@router.post(
    "/whatsapp/generate",
    summary="Generate WhatsApp messages for selected leads using Python template engine",
    description=(
        "Loads leads from MongoDB, auto-selects Website/No-Website template based on "
        "hasWebsite flag, generates personalized messages using the Python message_builder, "
        "stores preparedMessage / campaignId / preparedAt in each lead's whatsappOutreach "
        "subdocument in MongoDB, and returns prepared messages with web.whatsapp.com URLs. "
        "All business logic runs in Python — Node only forwards, frontend only displays."
    ),
)
async def generate_messages(request: GenerateMessagesRequest):
    import uuid
    from datetime import datetime, timezone
    from urllib.parse import quote

    from .database import get_db
    from .lead_loader import lead_loader
    from .message_builder import message_builder
    from .phone_utils import validate_phone
    from .template_service import template_service

    campaign_id = request.campaignId or uuid.uuid4().hex[:12]
    db = get_db()

    logger.info("[GENERATE] Campaign %s: %d leads", campaign_id, len(request.leadIds))
    logger.info("[GENERATE] Template Source = MongoDB")

    try:
        await template_service.load_templates()
        logger.info("[GENERATE] Loaded Website Template")
        logger.info("[GENERATE] Loaded No Website Template")

        leads = await lead_loader.load_by_ids_batched(request.leadIds)
    except Exception as e:
        logger.exception("[GENERATE] Failed to load leads or templates")
        raise HTTPException(status_code=500, detail=f"Failed to load leads or templates: {str(e)}")

    prepared = []
    skipped = []

    for lead in leads:
        normalized_lead = lead_loader.normalize_lead(lead)
        lead_id = normalized_lead["id"]
        company = normalized_lead["companyName"]
        phone = normalized_lead["phone"]

        valid, result = validate_phone(phone)
        if not valid:
            skipped.append({"leadId": lead_id, "companyName": company, "reason": result})
            continue

        normalized_phone = result
        has_website = normalized_lead["hasWebsite"]
        website = normalized_lead.get("website", "")
        city = normalized_lead.get("city", "")

        message = await message_builder.build(normalized_lead)
        template_type = "website" if has_website else "no-website"

        if not isinstance(message, str):
            message = str(message) if message is not None else ""
        encoded = quote(message)
        whatsapp_url = f"https://web.whatsapp.com/send?phone={normalized_phone}&text={encoded}"

        entry = {
            "leadId": lead_id,
            "companyName": company,
            "phone": phone,
            "normalizedPhone": f"+{normalized_phone}",
            "message": message,
            "templateType": template_type,
            "hasWebsite": has_website,
            "whatsappUrl": whatsapp_url,
            "skipReason": None,
        }
        prepared.append(entry)

        if db is not None:
            try:
                from bson.objectid import ObjectId
                await db["leads"].update_one(
                    {"_id": ObjectId(lead_id)},
                    {"$set": {
                        "whatsappOutreach.status": "prepared",
                        "whatsappOutreach.templateType": template_type,
                        "whatsappOutreach.campaignId": campaign_id,
                        "whatsappOutreach.preparedMessage": message,
                        "whatsappOutreach.preparedAt": datetime.now(timezone.utc).isoformat(),
                        "whatsappOutreach.lastError": None,
                    }}
                )
            except Exception as e:
                logger.warning("[GENERATE] Failed to update lead %s: %s", lead_id, e)

    logger.info(
        "[GENERATE] Campaign %s: %d prepared, %d skipped",
        campaign_id, len(prepared), len(skipped),
    )

    return {
        "success": True,
        "data": prepared,
        "skipped": skipped,
        "total": len(prepared),
        "skippedCount": len(skipped),
        "campaignId": campaign_id,
    }


@router.post(
    "/whatsapp/send",
    response_model=SendWhatsAppResponse,
    summary="Prepare WhatsApp messages for selected leads",
    description=(
        "Loads selected leads from MongoDB, generates WhatsApp message templates "
        "based on each lead's hasWebsite flag, queues them, and returns progress. "
        "Does NOT send actual WhatsApp messages — only prepares automation data."
    ),
)
async def send_whatsapp(
    request: SendWhatsAppRequest,
):
    if not request.leadIds:
        raise ValidationException("leadIds must contain at least one ID")

    try:
        result = await whatsapp_engine.prepare_automation(request.leadIds)
    except Exception as e:
        logger.exception("WhatsApp automation preparation failed")
        raise HTTPException(status_code=500, detail=f"Automation failed: {str(e)}")

    return SendWhatsAppResponse(
        status=result.get("status", "failed"),
        currentLead=result.get("currentLead", ""),
        totalLeads=result.get("totalLeads", 0),
        completed=result.get("completed", 0),
        failed=result.get("failed", 0),
        logs=result.get("logs", []),
        sessionId=result.get("sessionId", ""),
    )


@router.post(
    "/whatsapp/start-campaign",
    response_model=CampaignResponse,
    summary="Start WhatsApp campaign — prepare + send messages via WhatsApp Web",
    description=(
        "Loads leads, generates templates, then opens WhatsApp Web for each lead, "
        "clicks Send, and closes the tab. Returns immediately; poll "
        "/api/v1/whatsapp/sessions/{sessionId}/status for per-lead progress "
        "with ETA, message type, and full dashboard data."
    ),
)
async def start_campaign(
    request: SendWhatsAppRequest,
):
    if not request.leadIds:
        logger.warn("[API] start-campaign called with empty leadIds")
        raise ValidationException("leadIds must contain at least one ID")

    lead_count = len(request.leadIds)
    logger.info("[API] ====== START CAMPAIGN RECEIVED =====")
    logger.info("[API] Lead count: %d", lead_count)
    logger.info("[API] First 3 IDs: %s", request.leadIds[:3])
    logger.info("[API] Database already connected via lifespan, invoking engine...")

    try:
        result = await whatsapp_engine.start_campaign(request.leadIds)
        
        if result.get("status") == "failed":
            error_msg = result.get("error") or "Campaign failed during preparation"
            logger.error("[API] Campaign preparation failed: %s", error_msg)
            from ...core.exception_handlers import WhatsAppException
            raise WhatsAppException(
                error_msg,
                "CAMPAIGN_PREPARATION_FAILED",
                400
            )
    except Exception as e:
        from ...core.exception_handlers import WhatsAppException
        if isinstance(e, WhatsAppException):
            logger.error("[API] WhatsApp error: %s (code: %s)", e.message, e.error_code)
            raise
        logger.exception("[API] Unexpected error in start_campaign")
        raise WhatsAppException(
            f"Campaign failed: {str(e)}", 
            "CAMPAIGN_START_FAILED",
            500
        )

    logger.info("[API] Engine returned: sessionId=%s status=%s totalLeads=%d",
                result.get("sessionId"), result.get("status"), result.get("totalLeads"))
    logger.info("[API] ====== START CAMPAIGN RESPONDING =====")

    return CampaignResponse(
        sessionId=result.get("sessionId", ""),
        status=result.get("status", "failed"),
        totalLeads=result.get("totalLeads", 0),
        completed=result.get("completed", 0),
        failed=result.get("failed", 0),
        currentLead=result.get("currentLead") or "",
    )


@router.post(
    "/whatsapp/sessions/{session_id}/stop",
    summary="Stop a running WhatsApp campaign",
)
async def stop_campaign(session_id: str):
    success = await whatsapp_engine.stop_campaign(session_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Session not found or not running",
        )
    return {"sessionId": session_id, "status": "stopped"}


@router.get(
    "/whatsapp/sessions/{session_id}",
    summary="Get WhatsApp session progress (aggregate)",
)
async def get_session_progress(session_id: str):
    progress = session_manager.get_progress(session_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return progress


@router.get(
    "/whatsapp/sessions/{session_id}/status",
    response_model=DetailedSessionResponse,
    summary="Get detailed session progress with per-lead statuses, ETA, message types",
    description=(
        "Returns every lead's current status (prepared, opening, waiting, "
        "sending, sent, failed, retrying) with company name, phone, website, "
        "message type (Website / No Website), duration, browser state, "
        "remaining leads, processed count, and ETA for real-time dashboard."
    ),
)
async def get_detailed_session_status(session_id: str):
    logger.info("[API] get_detailed_session_status session_id=%s", session_id)
    progress = session_manager.get_detailed_progress(session_id)
    if progress is None:
        logger.warning("[API] Session %s not found", session_id)
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        return DetailedSessionResponse(**progress)
    except Exception as e:
        logger.error("[API] Failed to build DetailedSessionResponse: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/whatsapp/logs/{session_id}",
    summary="Get logs for a WhatsApp session",
)
async def get_session_logs(
    session_id: str,
    limit: int = Query(default=200, le=1000),
    offset: int = Query(default=0, ge=0),
):
    db = get_db()
    if db is not None:
        whatsapp_logger.set_database(db)
    logs = await whatsapp_logger.get_session_logs(session_id, limit=limit, offset=offset)
    return {"sessionId": session_id, "total": len(logs), "logs": logs}


class TemplateRefreshResponse(BaseModel):
    success: bool
    message: str


@router.post(
    "/whatsapp/templates/refresh",
    summary="Invalidate AI service template cache — forces reload from MongoDB on next campaign",
)
async def refresh_templates():
    template_service.refresh_cache()
    logger.info("[Templates] Cache invalidated — next campaign will reload from MongoDB")
    return TemplateRefreshResponse(
        success=True,
        message="Template cache invalidated. Next campaign will reload from MongoDB.",
    )


class PreviewRequest(BaseModel):
    type: str = Field(..., description="Template type: 'website' or 'no_website'")
    message: str = Field(..., description="Template text to preview")


class PreviewResponse(BaseModel):
    rendered: str


@router.post(
    "/whatsapp/templates/preview",
    summary="Preview a template with sample data — uses the exact same rendering engine as automation",
)
async def preview_template(request: PreviewRequest):
    if request.type not in ("website", "no_website"):
        raise HTTPException(status_code=400, detail="type must be 'website' or 'no_website'")

    rendered = await template_service.render_preview(request.type, request.message)
    return PreviewResponse(rendered=rendered)
