# realtime_client/app/main.py
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
import httpx

# Load environment variables
load_dotenv()

app = FastAPI()

# Configure CORS (allow all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (HTML, JS, CSS)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# Serve the main client HTML
@app.get("/", response_class=FileResponse)
async def get_index():
    return "app/static/client.html"


# New endpoint to mint an ephemeral API key for WebRTC connection
@app.get("/session")
async def get_ephemeral_key():
    # Endpoint for creating an ephemeral token from OpenAI’s REST API
    url = "https://api.openai.com/v1/realtime/sessions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json",
    }
    # The payload can be adjusted as needed. Here we use the current preview model and a sample voice.
    payload = {"model": "gpt-4o-realtime-preview-2024-12-17", "voice": "coral"}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)

    # Return the JSON response (which should include the ephemeral key)
    return JSONResponse(content=response.json())


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9090)
