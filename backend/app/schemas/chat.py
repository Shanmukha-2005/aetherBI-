from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class ChatPromptRequest(BaseModel):
    dataset_id: int
    prompt: str
    api_key: Optional[str] = None

class ChatMessageOut(BaseModel):
    id: int
    dataset_id: int
    role: str
    content: str
    generated_sql: Optional[str] = None
    explanation: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChatHistoryResponse(BaseModel):
    dataset_id: int
    messages: List[ChatMessageOut]
