# (C) Datadog, Inc.2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

app = FastAPI(title="KrakenD Test API", version="1.0.0")


@app.get("/valid/")
async def valid_endpoint() -> Dict[str, Any]:
    """Returns a valid response with a dummy message."""
    return {"message": "This is a valid response", "status": "success"}


@app.get("/invalid/")
async def invalid_endpoint():
    """Always fails with a 500 error."""
    raise HTTPException(status_code=500, detail="This endpoint always fails")


@app.get("/timeout/")
async def timeout_endpoint() -> Dict[str, Any]:
    """Takes more than 2 seconds to respond, causing a timeout."""
    await asyncio.sleep(2)
    return {"message": "This response took too long", "status": "timeout"}


@app.get("/cancelled/")
async def cancelled_endpoint(request: Request):
    """Simulates a cancelled request by checking for client disconnection."""
    for _ in range(50):
        if await request.is_disconnected():
            # Client disconnected - this should trigger KrakenD's cancellation detection
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.1)

    # If we get here, no disconnection occurred
    return {"message": "Request completed without cancellation", "status": "completed"}


@app.get("/no-content-length/")
async def no_content_length_endpoint() -> Response:
    """Returns a response without Content-Length header."""

    async def chunked_data_generator():
        """
        This async generator yields response chunks one by one.
        The server doesn't know the total size in advance.
        """
        yield '{"message":'
        await asyncio.sleep(0.1)
        yield ' "Hello, '
        await asyncio.sleep(0.1)
        yield 'Streaming World!"}'

    # Return response without Content-Length header
    return StreamingResponse(chunked_data_generator(), media_type="application/json")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
