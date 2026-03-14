import Electrobun, { Electroview } from "electrobun/view";

type SessionPayload = {
  schema_version: number;
  state: "stopped" | "idle" | "recording" | "transcribing" | "error";
  started_at: number | null;
  last_completed_at: number | null;
  last_transcript: {
    schema_version: number;
    transcript: string;
    normalized_transcript?: string;
    device?: string;
    metadata?: Record<string, unknown>;
  } | null;
  last_error: string | null;
  config: Record<string, unknown>;
  stderr_tail: string[];
};

type BridgeViewState = {
  bridgeUrl: string;
  bridgeStartCommand: string;
  hotkey: string;
  connected: boolean;
  session: SessionPayload;
};

type DesktopRPC = {
  bun: {
    requests: {
      getBridgeState: { params: {}; response: BridgeViewState };
      startRecording: { params: {}; response: BridgeViewState };
      stopRecording: { params: {}; response: BridgeViewState };
      toggleRecording: { params: {}; response: BridgeViewState };
      showWindow: { params: {}; response: { success: true } };
    };
    messages: {
      bridgeStateUpdated: { params: BridgeViewState };
      bridgeError: { params: { message: string } };
    };
  };
  webview: {
    requests: {};
    messages: {};
  };
};

const rpc = Electroview.defineRPC<DesktopRPC>({
  maxRequestTime: 30000,
  handlers: {
    requests: {},
    messages: {},
  },
});

const electrobun = new Electrobun.Electroview({ rpc });

const statusBadge = document.getElementById("statusBadge") as HTMLDivElement;
const hotkeyValue = document.getElementById("hotkeyValue") as HTMLDivElement;
const toggleButton = document.getElementById("toggleButton") as HTMLButtonElement;
const statusLine = document.getElementById("statusLine") as HTMLParagraphElement;
const bridgeUrl = document.getElementById("bridgeUrl") as HTMLDivElement;
const bridgeCommand = document.getElementById("bridgeCommand") as HTMLPreElement;
const transcriptMeta = document.getElementById("transcriptMeta") as HTMLDivElement;
const transcriptText = document.getElementById("transcriptText") as HTMLPreElement;
const errorBox = document.getElementById("errorBox") as HTMLPreElement;
const refreshButton = document.getElementById("refreshButton") as HTMLButtonElement;

function formatTimestamp(timestamp: number | null): string {
  if (!timestamp) return "—";
  return new Date(timestamp * 1000).toLocaleTimeString();
}

function setBusy(busy: boolean) {
  toggleButton.disabled = busy;
  refreshButton.disabled = busy;
}

function renderState(viewState: BridgeViewState) {
  const sessionState = viewState.connected ? viewState.session.state : "offline";
  statusBadge.textContent = viewState.connected ? viewState.session.state : "Disconnected";
  statusBadge.className = `badge ${sessionState}`;

  hotkeyValue.textContent = viewState.hotkey;
  bridgeUrl.textContent = viewState.bridgeUrl;
  bridgeCommand.textContent = viewState.bridgeStartCommand;

  const transcript = viewState.session.last_transcript;
  if (transcript) {
    transcriptText.textContent = transcript.transcript;
    transcriptText.classList.remove("empty");
    transcriptMeta.textContent = [
      transcript.device ? `device: ${transcript.device}` : null,
      `completed: ${formatTimestamp(viewState.session.last_completed_at)}`,
    ]
      .filter(Boolean)
      .join(" • ");
  } else {
    transcriptText.textContent = "No transcript yet.";
    transcriptText.classList.add("empty");
    transcriptMeta.textContent = "No transcript yet.";
  }

  if (!viewState.connected) {
    toggleButton.textContent = "Bridge offline";
    statusLine.textContent = "Start the WSL bridge command below, then use the button or hotkey.";
  } else if (viewState.session.state === "recording") {
    toggleButton.textContent = "Stop recording";
    statusLine.textContent = `Recording in progress since ${formatTimestamp(viewState.session.started_at)}.`;
  } else if (viewState.session.state === "transcribing") {
    toggleButton.textContent = "Transcribing…";
    statusLine.textContent = "Audio captured. Waiting for transcript…";
  } else if (viewState.session.state === "error") {
    toggleButton.textContent = "Try again";
    statusLine.textContent = "Bridge reachable but the backend reported an error.";
  } else {
    toggleButton.textContent = "Start recording";
    statusLine.textContent = "Ready. Press the button or the global hotkey to begin.";
  }

  const errorLines = [];
  if (viewState.session.last_error) errorLines.push(viewState.session.last_error);
  if (viewState.session.stderr_tail.length) errorLines.push(...viewState.session.stderr_tail.slice(-8));
  errorBox.textContent = errorLines.length ? errorLines.join("\n") : "No bridge errors.";
}

async function refreshState() {
  setBusy(true);
  try {
    const state = await electrobun.rpc!.request.getBridgeState({});
    renderState(state);
  } finally {
    setBusy(false);
  }
}

async function toggleRecording() {
  setBusy(true);
  try {
    const current = await electrobun.rpc!.request.getBridgeState({});
    const next = current.connected && current.session.state === "recording"
      ? await electrobun.rpc!.request.stopRecording({})
      : await electrobun.rpc!.request.startRecording({});
    renderState(next);
  } catch (error) {
    errorBox.textContent = error instanceof Error ? error.message : String(error);
  } finally {
    setBusy(false);
  }
}

toggleButton.addEventListener("click", () => {
  void toggleRecording();
});
refreshButton.addEventListener("click", () => {
  void refreshState();
});

(electrobun.rpc as any)?.addMessageListener("bridgeStateUpdated", (state: BridgeViewState) => {
  renderState(state);
});

(electrobun.rpc as any)?.addMessageListener("bridgeError", (payload: { message: string }) => {
  errorBox.textContent = payload.message;
});

void refreshState();
