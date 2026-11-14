// Learn in Public: editable LinkedIn draft and downloadable learning-log.md from real evidence.
import { api } from "../api.js";
import { agentTrace, button, card, el, emptyState, pageHead, toast, withLoading } from "../ui.js";

export async function render(root) {
  const out = el("div", { class: "stack" });
  const generate = button("Generate draft from my evidence");
  generate.addEventListener("click", () => withLoading(generate, async () => {
    try {
      draw(out, await api.post("/publish/draft"));
    } catch (error) {
      toast(error.message, "error");
    }
  }));
  root.append(pageHead("Learn in Public", "Share verified progress. Drafts use only your real evidence — nothing is posted without you."), card(null, generate), out);
  out.append(emptyState("No draft yet", "Generate a draft to edit, copy or download it."));
}

function draw(out, res) {
  const post = el("textarea", { id: "post", rows: "8", value: res.linkedin_post });
  const copy = button("Copy post", { variant: "secondary", onClick: async () => {
    try {
      await navigator.clipboard.writeText(post.value);
      toast("Post copied to clipboard.", "success");
    } catch {
      toast("Copy failed. Select the text and copy it manually.", "error");
    }
  } });
  const share = el("a", { class: "btn btn-primary", target: "_blank", rel: "noopener noreferrer", text: "Open LinkedIn to post" });
  const syncShare = () => (share.href = `https://www.linkedin.com/feed/?shareActive=true&text=${encodeURIComponent(post.value)}`);
  post.addEventListener("input", syncShare);
  syncShare();
  const log = el("pre", { text: res.learning_log_md });
  const download = button("Download learning-log.md", { variant: "secondary", onClick: () => {
    const url = URL.createObjectURL(new Blob([res.learning_log_md], { type: "text/markdown" }));
    const link = el("a", { href: url, download: "learning-log.md" });
    link.click();
    URL.revokeObjectURL(url);
  } });
  out.replaceChildren(
    card("LinkedIn draft", el("div", { class: "field" }, el("label", { for: "post", text: "Edit before posting" }), post), el("div", { class: "row" }, share, copy), el("p", { class: "small muted", text: "No LinkedIn login or token is used — the link only opens LinkedIn with your text." })),
    card("Learning log", log, download),
    agentTrace(res.agent_trace),
  );
}
