"""
client.py

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
import time
import speech_recognition as sr  # NEW: For speech recognition functionality
import threading  # NEW: To run recognition in a background thread

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
    def __init__(self, channels, rate, frames_per_buffer=512):
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


# NEW helper function for speech recognition
def start_speech_recognition():
    """
    Starts speech recognition in a background thread.
    Recognized speech is printed to the console.
    """
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    # Adjust for ambient noise to set a suitable energy threshold
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
    print("Speech Recognition: Calibrated for ambient noise. Ready to listen.")

    def recognition_loop():
        with mic as source:
            while True:
                try:
                    print("Listening for speech...")
                    # Listen for a phrase (with a 5-second limit per phrase)
                    audio = recognizer.listen(source, phrase_time_limit=5)
                    # Recognize using Google's API (change if needed)
                    transcript = recognizer.recognize_google(audio)
                    print(f"\n[{time.time():.3f}] Client: {transcript}\n")
                except sr.UnknownValueError:
                    print("Speech Recognition: Could not understand audio.")
                except sr.RequestError as e:
                    print(f"Speech Recognition Request error: {e}")
                except Exception as e:
                    print(f"Speech Recognition error: {e}")

    threading.Thread(target=recognition_loop, daemon=True).start()


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
    player = MediaPlayer("none:default", format="avfoundation")
    if player.audio:
        pc.addTrack(player.audio)
        print("Added local audio track from microphone.")
    else:
        logging.warning("No audio input track available from your system device.")

    # Create a data channel for receiving realtime messages.
    channel = pc.createDataChannel("oai-events")

    @channel.on("message")
    async def on_message(message):
        # If the received message is bytes, decode it using UTF-8.
        if isinstance(message, bytes):
            message = message.decode("utf-8")
        handle_data_message(message)

    print("Created data channel 'oai-events'.")

    # Log connection state changes.
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print(f"Connection state changed to: {pc.connectionState}")
        if pc.connectionState == "failed":
            await pc.close()

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

    # NEW: Start speech recognition in a background thread
    start_speech_recognition()

    print("Listening for realtime messages (press Ctrl+C to exit)...\n")

    # Run indefinitely until interrupted.
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting...")
    finally:
        await pc.close()


def handle_data_message(message):
    """
    Process JSON messages received on the data channel.
    The function prints the content in a chat-like format.
    """
    now = time.time()  # Timestamp for latency monitoring
    try:
        data = json.loads(message)
    except Exception:
        print(f"[{now:.3f}] Received non-JSON message:", message)
        return

    event_type = data.get("type")
    if event_type in ["response.audio_transcript.delta", "response.text.delta"]:
        sender = "Assistant" if data.get("role") != "user" else "Client"
        text = data.get("text", "").strip()
        if text:
            print(f"[{now:.3f}] {sender}: {text}")
    elif event_type == "input.audio_transcript.delta":
        # Handle transcript of input audio
        text = data.get("text", "").strip()
        if text:
            print(f"[{now:.3f}] Client: {text}")
    elif event_type == "response.done":
        response = data.get("response", {})
        if response.get("output"):
            output = response["output"][0]
            sender = "Assistant" if output.get("role") != "user" else "Client"
            if output.get("type") == "function_call":
                print(
                    f"[{now:.3f}] {sender}: Function call detected: {output.get('name')} with arguments: {output.get('arguments')}"
                )
            elif output.get("text"):
                print(f"[{now:.3f}] {sender}: {output.get('text')}")
            elif output.get("content") and isinstance(output["content"], list):
                transcript = " ".join(
                    [
                        item.get("transcript") or item.get("text", "")
                        for item in output["content"]
                    ]
                )
                if transcript.strip():
                    print(f"\n[{now:.3f}] {sender}: {transcript.strip()}\n")
            else:
                print(
                    f"[{now:.3f}] {sender}: Response received: {json.dumps(response)}"
                )
    elif event_type in ["session.created", "session.updated"]:
        print(f"[{now:.3f}] Status: {event_type}")
    elif event_type in ["invalid_request_error", "error"]:
        print(f"[{now:.3f}] Error: {data.get('message')}")
    elif event_type == "message_status":
        print(f"[{now:.3f}] Message status: {data.get('status')}")
    # --- New event handling for additional realtime events ---
    elif event_type == "input_audio_buffer.speech_started":
        print(f"[{now:.3f}] Speech started detected.")
    elif event_type == "input_audio_buffer.speech_stopped":
        print(f"[{now:.3f}] Speech stopped detected.")
    elif event_type == "response.audio.delta":
        # For large audio chunks, printing only the first 50 characters
        delta = data.get("delta", "")
        print(f"[{now:.3f}] Audio delta received (base64 snippet): {delta[:50]}...")
    elif event_type == "response.function_call_arguments.delta":
        print(f"[{now:.3f}] Function call arguments delta: {data.get('arguments', '')}")
    else:
        print(f"[{now:.3f}] Unhandled message: {event_type}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
