"""
python_client.py

A Python client that establishes a WebRTC connection to the OpenAI Realtime API,
captures microphone audio, and prints chat messages received over the data channel.
It mimics the functionality of the OpenAI Realtime AI simple client.
"""

import asyncio
import json
import logging
import aiohttp
import pyaudio
import numpy as np

from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
    RTCIceServer,
)
from aiortc.contrib.media import MediaPlayer

# Configuration
MODEL_ID = "gpt-4o-realtime-preview-2024-12-17"
OPENAI_REALTIME_URL = f"https://api.openai.com/v1/realtime?model={MODEL_ID}"
# Adjust the session endpoint if your local server is running elsewhere.
SESSION_ENDPOINT = "http://localhost:9090/session"


class PyAudioPlayer:
    def __init__(self, channels, rate, frames_per_buffer=1024):
        self.p = pyaudio.PyAudio()
        self.channels = channels
        self.rate = rate
        # Assume audio is 16-bit PCM.
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=rate,
            output=True,
            frames_per_buffer=frames_per_buffer,
        )

    def play_frame(self, frame):
        # Convert the AudioFrame to a numpy array of int16
        audio_data = frame.to_ndarray().astype(np.int16)
        self.stream.write(audio_data.tobytes())

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()


async def run():
    # Create the RTCPeerConnection with a basic STUN server
    pc = RTCPeerConnection(
        configuration=RTCConfiguration(
            iceServers=[RTCIceServer(urls="stun:stun.l.google.com:19302")]
        )
    )
    print("Initialized peer connection.")

    # Capture the microphone audio.
    # On Linux you might use format="pulse". On macOS, an alternative is "avfoundation", on Windows "dshow".
    player = MediaPlayer("none:0", format="avfoundation")
    if player.audio:
        pc.addTrack(player.audio)
        print("Added local audio track from microphone.")
    else:
        logging.warning("No audio input track available from your system device.")

    # Create a data channel for receiving realtime messages.
    channel = pc.createDataChannel("oai-events")
    channel.on("message", lambda message: handle_data_message(message))
    print("Created data channel 'oai-events'.")

    # Log connection state changes.
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print(f"Connection state changed to: {pc.connectionState}")
        if pc.connectionState == "failed":
            await pc.close()

    # Set up reception of remote audio.
    recorder = None

    @pc.on("track")
    async def on_track(track):
        if track.kind == "audio":
            print("Received remote audio track.")
            # Wait for the first frame to get audio parameters.
            frame = await track.recv()
            # Use the frame's layout to determine channel count.
            player = PyAudioPlayer(
                channels=len(frame.layout.channels), rate=frame.sample_rate
            )
            # Play the first frame.
            player.play_frame(frame)
            try:
                while True:
                    frame = await track.recv()
                    player.play_frame(frame)
            except Exception as e:
                print("Audio track ended:", e)
            finally:
                player.close()

    # Create an SDP offer for the connection.
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    print("Created and set local SDP offer.")

    # Request an ephemeral key from our local session server.
    async with aiohttp.ClientSession() as session:
        async with session.get(SESSION_ENDPOINT) as resp:
            token_data = await resp.json()
    # Adjust extraction depending on your session endpoint response.
    ephemeral_key = token_data["client_secret"]["value"]
    print("Obtained ephemeral key from session endpoint.")

    # Send the SDP offer to the OpenAI Realtime API.
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {ephemeral_key}",
            "Content-Type": "application/sdp",
        }
        async with session.post(
            OPENAI_REALTIME_URL, data=pc.localDescription.sdp, headers=headers
        ) as resp:
            answer_sdp = await resp.text()
    print("Received answer SDP from OpenAI Realtime API.")

    # Set the remote SDP (answer) to finalize the connection.
    answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
    await pc.setRemoteDescription(answer)
    print("WebRTC connection established with remote SDP set.\n")
    print("Listening for realtime messages (press Ctrl+C to exit)...\n")

    # Run indefinitely until interrupted.
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting...")
    finally:
        if recorder:
            await recorder.stop()
        await pc.close()


def handle_data_message(message):
    """
    Process JSON messages received on the data channel.
    The function prints the content in a chat-like format.
    """
    try:
        data = json.loads(message)
    except Exception:
        print("Received non-JSON message:", message)
        return

    # Similar to the JS client, process different message types.
    if data.get("type") in ["response.audio_transcript.delta", "response.text.delta"]:
        sender = "Assistant" if data.get("role") != "user" else "Client"
        text = data.get("text", "").strip()
        if text:
            print(f"{sender}: {text}")
    elif data.get("type") == "input.audio_transcript.delta":
        # Handle transcript of input audio
        text = data.get("text", "").strip()
        if text:
            print("Client:", text)
    elif data.get("type") == "response.done":
        response = data.get("response", {})
        if response.get("output"):
            output = response["output"][0]
            sender = "Assistant" if output.get("role") != "user" else "Client"
            if output.get("type") == "function_call":
                print(
                    f"{sender}: Function call detected: {output.get('name')} with arguments: {output.get('arguments')}"
                )
            elif output.get("text"):
                print(f"{sender}: {output.get('text')}")
            elif output.get("content") and isinstance(output["content"], list):
                transcript = " ".join(
                    [
                        item.get("transcript") or item.get("text", "")
                        for item in output["content"]
                    ]
                )
                if transcript.strip():
                    print(f"\n{sender}: {transcript.strip()}")
            else:
                print(f"{sender}: Response received: {json.dumps(response)}")
    elif data.get("type") in ["session.created", "session.updated"]:
        print("Status:", data.get("type"))
    elif data.get("type") in ["invalid_request_error", "error"]:
        print("Error:", data.get("message"))
    elif data.get("type") == "message_status":
        print("Message status:", data.get("status"))
    else:
        print("Unhandled message:", data)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
