// realtime_client/app/static/client.js

// Global variables to store WebRTC objects and local media stream
let peerConnection;
let dataChannel;
let localStream = null;
let recognition; // <-- Added global variable for speech recognition

const OPENAI_REALTIME_URL = "https://api.openai.com/v1/realtime";
const MODEL_ID = "gpt-4o-realtime-preview-2024-12-17";

// UI helper: Update the status div
function updateStatus(message) {
  const statusEl = document.getElementById("status");
  if (statusEl) {
    statusEl.textContent = "Status: " + message;
  }
}

// UI helper: Append text to a given element (used for transcript and message status)
function appendText(id, text) {
  const el = document.getElementById(id);
  if (el) {
    el.textContent += text + "\n";
    el.scrollTop = el.scrollHeight;
  }
}

// ===== New Helper Functions added near existing helper functions =====

function appendChatBubble(role, message) {
  // Prevent appending empty messages
  if (!message || !message.trim()) {
    return;
  }

  const transcriptEl = document.getElementById("transcript");
  if (!transcriptEl) return;

  const bubble = document.createElement("div");
  bubble.className = "chat-bubble " + role;

  const labelSpan = document.createElement("span");
  labelSpan.className = "chat-label";
  labelSpan.textContent = role === "assistant" ? "Assistant: " : "You: ";
  bubble.appendChild(labelSpan);

  const textSpan = document.createElement("span");
  textSpan.className = "chat-text";
  textSpan.textContent = message.trim();
  bubble.appendChild(textSpan);

  bubble.appendChild(document.createElement("br"));
  const timestampEl = document.createElement("small");
  timestampEl.className = "chat-timestamp";
  timestampEl.textContent = new Date().toLocaleTimeString();
  bubble.appendChild(timestampEl);

  transcriptEl.appendChild(bubble);
  transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

function appendMessageLog(data) {
  const messagesEl = document.getElementById("messageStatus");
  if (!messagesEl) return;

  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "Message: " + data.type;
  // Set the timestamp attribute to show the time when the message log was created.
  summary.setAttribute("data-timestamp", new Date().toLocaleTimeString());
  details.appendChild(summary);

  const pre = document.createElement("pre");
  pre.textContent = JSON.stringify(data, null, 2);
  details.appendChild(pre);

  messagesEl.appendChild(details);
  messagesEl.scrollTop = messagesEl.scrollHeight; // Ensure the last message is visible
}

// ===== New helper function for speech recognition =====
function startSpeechRecognition() {
  // If recognition is already running, do nothing
  if (recognition) return;

  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.log("Speech recognition not supported in this browser.");
    return;
  }
  recognition = new SpeechRecognition();
  recognition.interimResults = false;
  recognition.lang = "en-US";
  recognition.onresult = (event) => {
    const result = event.results[0][0].transcript;
    // Only append transcript if the microphone is enabled
    if (localStream && localStream.getAudioTracks()[0].enabled) {
      appendChatBubble("client", result);
    } else {
      console.log("Microphone is muted; transcript not appended.");
    }
  };
  recognition.onerror = (event) => {
    if (event.error === "no-speech") {
      console.debug("No speech detected, restarting recognition.");
      recognition.start();
    } else {
      console.error("Speech recognition error", event);
    }
  };
  recognition.onend = () => {
    // Only restart recognition if the mic is still enabled
    if (localStream && localStream.getAudioTracks()[0].enabled) {
      recognition.start();
    }
  };
  recognition.start();
}

// ===== Updated handleDataMessage function =====

function handleDataMessage(message) {
  let data;
  try {
    data = JSON.parse(message);
  } catch (e) {
    console.error("Invalid JSON message:", message);
    return;
  }

  // Log full JSON message in the messages section
  appendMessageLog(data);

  // Process and display dialog text in the transcript as chat bubbles
  if (
    data.type === "response.audio_transcript.delta" ||
    data.type === "response.text.delta"
  ) {
    // Determine sender: if a role property exists and is "user", show as client; else assistant.
    let sender = "assistant";
    if (data.role && data.role === "user") {
      sender = "client";
    }
    appendChatBubble(sender, data.text);
  } else if (data.type === "response.done") {
    if (
      data.response &&
      data.response.output &&
      data.response.output.length > 0
    ) {
      const output = data.response.output[0];
      // Determine sender based on output.role (default assistant)
      let sender = "assistant";
      if (output.role && output.role === "user") {
        sender = "client";
      }
      if (output.type === "function_call") {
        appendChatBubble(
          "assistant",
          "Function call detected: " +
            output.name +
            " with arguments: " +
            output.arguments
        );
      } else if (output.text) {
        appendChatBubble(sender, output.text);
      } else if (output.content && Array.isArray(output.content)) {
        // Extract transcript text from the content array if available
        let transcript = "";
        output.content.forEach((item) => {
          if (item.transcript) {
            transcript += item.transcript + " ";
          } else if (item.text) {
            transcript += item.text + " ";
          }
        });
        transcript = transcript.trim();
        if (transcript) {
          appendChatBubble(sender, transcript);
        }
      } else {
        appendChatBubble(
          "assistant",
          "Response: " + JSON.stringify(data.response)
        );
      }
    }
  } else if (
    data.type === "session.created" ||
    data.type === "session.updated"
  ) {
    updateStatus("Session event: " + data.type);
  } else if (data.type === "invalid_request_error" || data.type === "error") {
    updateStatus("Error: " + data.message);
  } else if (data.type === "message_status") {
    updateStatus("Message status: " + data.status);
  }
}

// Start the WebRTC connection to OpenAI Realtime API
async function startWebRTC() {
  updateStatus("Fetching ephemeral key...");
  // Fetch an ephemeral key by calling our server endpoint
  const tokenResponse = await fetch("/session");
  const tokenData = await tokenResponse.json();
  const EPHEMERAL_KEY = tokenData.client_secret.value; // Adjust based on your API response structure

  updateStatus("Initializing peer connection...");
  // Create the RTCPeerConnection with a basic STUN server
  peerConnection = new RTCPeerConnection({
    iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
  });

  // Set up the data channel for realtime events
  dataChannel = peerConnection.createDataChannel("oai-events");
  dataChannel.onmessage = async (event) => {
    let message = event.data;
    // If the data is a Blob, convert it to text
    if (message instanceof Blob) {
      message = await message.text();
    } else if (message instanceof ArrayBuffer) {
      message = new TextDecoder("utf-8").decode(new Uint8Array(message));
    }
    handleDataMessage(message);
  };

  // When remote tracks arrive, use the <audio> element to play audio
  const remoteAudio = document.getElementById("remoteAudio");
  peerConnection.ontrack = (event) => {
    if (remoteAudio) {
      remoteAudio.srcObject = event.streams[0];
    }
  };

  // Get local audio from the microphone
  try {
    localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    // Save for later use (e.g., to toggle mute)
    localStream.getTracks().forEach((track) => {
      peerConnection.addTrack(track, localStream);
    });
    // Start speech recognition to capture and display your spoken input locally
    startSpeechRecognition();
  } catch (err) {
    console.error("Error accessing microphone:", err);
    updateStatus("Error accessing microphone");
    return;
  }

  // Create an SDP offer
  updateStatus("Creating offer...");
  const offer = await peerConnection.createOffer();
  await peerConnection.setLocalDescription(offer);

  updateStatus("Sending offer to Realtime API...");
  // Log a client chat bubble when offering
  appendChatBubble("client", "Sent connection offer to Realtime API.");

  const sdpResponse = await fetch(`${OPENAI_REALTIME_URL}?model=${MODEL_ID}`, {
    method: "POST",
    body: offer.sdp,
    headers: {
      Authorization: `Bearer ${EPHEMERAL_KEY}`,
      "Content-Type": "application/sdp",
    },
  });

  const answerSdp = await sdpResponse.text();
  const answer = {
    type: "answer",
    sdp: answerSdp,
  };
  // Set the remote description from the answer SDP
  await peerConnection.setRemoteDescription(answer);

  // Set up connection state change logging
  peerConnection.onconnectionstatechange = () => {
    updateStatus(peerConnection.connectionState);
  };

  updateStatus("WebRTC connection established");
  // Enable/disable UI buttons
  document.getElementById("startBtn").disabled = true;
  document.getElementById("stopBtn").disabled = false;
}

// Stop the WebRTC connection and clean up resources
function stopWebRTC() {
  if (peerConnection) {
    peerConnection.close();
    peerConnection = null;
    dataChannel = null;
  }
  if (localStream) {
    localStream.getTracks().forEach((track) => track.stop());
    localStream = null;
  }
  updateStatus("Connection closed");
  document.getElementById("startBtn").disabled = false;
  document.getElementById("stopBtn").disabled = true;
}

// Function to initialize the microphone (audio only)
function initMic() {
  navigator.mediaDevices
    .getUserMedia({ audio: true })
    .then((stream) => {
      localStream = stream;
      console.log("Microphone initialized");
      // If you need to attach the stream to a peer connection or audio element, do it here.
    })
    .catch((err) => {
      console.error("Failed to initialize microphone:", err);
    });
}

/**
 * Function: toggleMic()
 * Toggles the "active" state of the mic button.
 * When active (i.e., class "active" is added), it disables all audio tracks from the stream (muting the mic);
 * when inactive, it re-enables the mic.
 * It also updates the icon to display either "mic" or "mic_off".
 */
function toggleMic() {
  const micButton = document.getElementById("toggleMicPlayer");
  const iconEl = micButton.querySelector(".material-icons");

  // Toggle the active class; if active, the mic is muted
  const isMuted = micButton.classList.toggle("active");
  iconEl.textContent = isMuted ? "mic_off" : "mic";

  // If there's a valid localStream, disable or enable its audio tracks accordingly
  if (localStream && localStream.getAudioTracks().length > 0) {
    localStream.getAudioTracks().forEach((track) => {
      track.enabled = !isMuted;
    });
  }

  console.log(isMuted ? "Microphone muted" : "Microphone unmuted");
}

// Initialize the mic when the DOM content is fully loaded
document.addEventListener("DOMContentLoaded", initMic);

// New function: Toggle (mute/unmute) the output audio (remote playback)
function toggleOutputAudio() {
  const remoteAudio = document.getElementById("remoteAudio");
  if (remoteAudio) {
    remoteAudio.muted = !remoteAudio.muted;
    updateStatus("Output Audio " + (remoteAudio.muted ? "Muted" : "Unmuted"));
  }
}

// Toggle visibility of a given element
function toggleVisibility(id) {
  const el = document.getElementById(id);
  if (el) {
    // Toggle the element's visibility by setting inline display style.
    // Removing the inline style (setting it to "") allows the element to use its original display setting from CSS.
    if (window.getComputedStyle(el).display === "none") {
      el.style.display = "";
    } else {
      el.style.display = "none";
    }
  }
}

// Attach UI event listeners once the DOM loads
document.addEventListener("DOMContentLoaded", function () {
  // Buttons for starting/stopping connection and toggling UI panels
  document.getElementById("startBtn").addEventListener("click", startWebRTC);
  document.getElementById("stopBtn").addEventListener("click", stopWebRTC);
  document
    .getElementById("toggleTranscriptBtn")
    .addEventListener("click", () => toggleVisibility("transcript"));
  document
    .getElementById("toggleMessageStatusBtn")
    .addEventListener("click", () => toggleVisibility("messageStatus"));
  document
    .getElementById("toggleOutputAudioBtn")
    .addEventListener("click", toggleOutputAudio);
  // Attach new microphone toggle button listener
  document
    .getElementById("toggleMicPlayer")
    .addEventListener("click", toggleMic);
});
