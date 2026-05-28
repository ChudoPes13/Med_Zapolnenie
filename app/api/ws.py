from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.api.deps import asr, processor
from app.db.session import engine
from app.services.vad import SileroVADDetector

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/visits/{visit_id}/audio")
async def audio_ws(websocket: WebSocket, visit_id: str) -> None:
    await websocket.accept()
    vad = SileroVADDetector()
    await websocket.send_json({"type": "ready", "visit_id": visit_id, "format": "pcm16-16000-mono"})

    try:
        while True:
            message = await websocket.receive()
            if text := message.get("text"):
                payload = json.loads(text)
                if payload.get("type") == "demo_text":
                    with Session(engine) as session:
                        state = await processor.process_text(
                            session,
                            visit_id,
                            str(payload.get("text", "")),
                            "demo",
                        )
                    await websocket.send_json({"type": "state", "state": state.model_dump(mode="json")})
                continue

            frame = message.get("bytes")
            if not frame:
                continue
            event = vad.accept_pcm16(frame)
            if event.speech_started:
                await websocket.send_json({"type": "speech_started"})
            if event.speech_ended:
                utterance = vad.pop_utterance()
                await websocket.send_json({"type": "transcribing"})
                text = asr.transcribe_pcm16(utterance)
                with Session(engine) as session:
                    state = await processor.process_text(session, visit_id, text, "asr")
                await websocket.send_json(
                    {
                        "type": "final_transcript",
                        "text": text,
                        "state": state.model_dump(mode="json"),
                    }
                )
    except WebSocketDisconnect:
        return
