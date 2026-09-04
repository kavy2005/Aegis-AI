from fastapi import APIRouter, Depends

from app.models.models import User
from app.schemas.schemas import CopilotChatRequest, CopilotChatResponse
from app.security import get_current_user
from app.ai.copilot import get_copilot_reply

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/chat", response_model=CopilotChatResponse)
def copilot_chat(
    payload: CopilotChatRequest,
    current_user: User = Depends(get_current_user),
):
    context_dict = payload.report_context.model_dump() if payload.report_context else None
    history = [turn.model_dump() for turn in payload.history] if payload.history else None

    result = get_copilot_reply(payload.message, context_dict, history)

    return CopilotChatResponse(reply=result["reply"], source=result["source"])
