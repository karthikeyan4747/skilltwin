// AI Mentor: grounded chat, one-frame screen share (on click, previewed, confirmed), Twin interviews.
import { api } from "../api.js";
import { twinCard } from "../mentor/twin-panel.js";
import {
  agentTrace,
  announce,
  badge,
  button,
  card,
  el,
  pageHead,
  toast,
  withLoading,
} from "../ui.js";
const MAX_SIDE = 1024;

export async function render(root) {
  root.append(
    pageHead(
      "AI Mentor",
      "Guidance grounded in your skill graph, roadmap and recent evidence. It can re-prioritise your roadmap.",
    ),
  );
  root.append(el("div", { class: "stack" }, chatCard(), twinCard()));
}

async function captureFrame() {
  const stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
  try {
    const video = el("video", { muted: true, playsInline: true });
    video.srcObject = stream;
    await video.play();
    const scale = Math.min(1, MAX_SIDE / Math.max(video.videoWidth, video.videoHeight));
    const canvas = el("canvas", {
      width: Math.round(video.videoWidth * scale),
      height: Math.round(video.videoHeight * scale),
    });
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.8);
  } finally {
    stream.getTracks().forEach((t) => t.stop());
  }
}

function chatCard() {
  const log = el("ol", { class: "chat-log", "aria-label": "Conversation", "aria-live": "polite" });
  const message = el("textarea", {
    id: "mentor-msg",
    maxlength: "2000",
    rows: "3",
    required: true,
  });
  const preview = el("div", { class: "stack" });
  let shot = null;
  const send = button("Send", { type: "submit" });
  const share = button("Share screen (one frame)", { variant: "secondary" });
  const clearShot = () => {
    shot = null;
    preview.replaceChildren();
  };
  share.addEventListener("click", async () => {
    if (!navigator.mediaDevices?.getDisplayMedia)
      return toast("Screen sharing is not supported in this browser.", "error");
    try {
      shot = await captureFrame();
      preview.replaceChildren(
        el("img", {
          src: shot,
          alt: "Preview of the captured screen frame",
          class: "screenshot-preview",
        }),
        el("p", {
          class: "small muted",
          text: "Only this single frame is sent with your next message, and it is never stored.",
        }),
        button("Remove screenshot", { variant: "ghost", onClick: clearShot }),
      );
      return announce("Screen frame captured. It will be sent with your next message.");
    } catch {
      return toast("Screen capture was cancelled.", "info");
    }
  });
  const form = el(
    "form",
    { class: "stack" },
    el(
      "div",
      { class: "field" },
      el("label", { for: "mentor-msg", text: "Ask your mentor" }),
      message,
    ),
    preview,
    el("div", { class: "row" }, send, share),
  );
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const text = message.value.trim();
    if (!text) return toast("Type a message first.", "error");
    const body = { message: text, screenshot_b64: shot ? shot.split(",")[1] : null };
    return withLoading(send, async () => {
      try {
        const res = await api.post("/mentor/chat", body);
        log.append(
          el(
            "li",
            { class: "chat-msg from-user" },
            el("span", { class: "visually-hidden", text: "You: " }),
            text,
            shot ? " (with screenshot)" : "",
          ),
        );
        log.append(
          el(
            "li",
            { class: "chat-msg" },
            el("strong", { text: "Mentor: " }),
            res.reply,
            res.applied_focus.length
              ? el(
                  "p",
                  { class: "small" },
                  badge("Roadmap updated", "accent"),
                  ` Moved to the front: ${res.applied_focus_names.join(", ")}`,
                )
              : null,
            agentTrace(res.agent_trace),
          ),
        );
        message.value = "";
        clearShot();
      } catch (error) {
        toast(error.message, "error");
      }
    });
  });
  return card("Chat", log, form);
}
