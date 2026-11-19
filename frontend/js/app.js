// Handbook Assistant page: ask a question, show the answer with clickable citations, open sources.

const form = document.querySelector("#ask-form");
const input = document.querySelector("#question");
const askButton = document.querySelector("#ask-button");
const welcome = document.querySelector("#welcome");
const conversation = document.querySelector("#conversation");
const panel = document.querySelector("#source-panel");
const backdrop = document.querySelector("#backdrop");

const NOT_COVERED = "the handbook does not cover this";
const documentCache = new Map();

// --- Asking -----------------------------------------------------------------------

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (question) ask(question);
});

document.querySelectorAll(".example").forEach((button) =>
  button.addEventListener("click", () => ask(button.textContent))
);

async function ask(question) {
  welcome.hidden = true;
  input.value = "";
  setBusy(true);
  conversation.append(element("div", "question", escapeHtml(question)));
  const card = element("div", "answer-card", '<div class="loading"><span class="dots"><span></span><span></span><span></span></span>Searching the handbook…</div>');
  conversation.append(card);
  card.scrollIntoView({ behavior: "smooth", block: "end" });

  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(errorMessage(response.status, body));
    renderAnswer(card, body);
  } catch (error) {
    card.className = "answer-card error";
    card.textContent = error.message;
  } finally {
    setBusy(false);
    input.focus();
  }
}

function errorMessage(status, body) {
  if (status === 422) return "Please enter a question of up to 500 characters.";
  if (status === 503) return `The language model is unavailable right now: ${body.detail}`;
  return "Something went wrong. Please try again.";
}

function setBusy(busy) {
  askButton.disabled = busy;
  askButton.textContent = busy ? "…" : "Ask";
}

// --- Showing an answer --------------------------------------------------------------

function renderAnswer(card, { answer, citations }) {
  const byNumber = new Map(citations.map((citation) => [citation.number, citation]));
  card.className = answer.toLowerCase().startsWith(NOT_COVERED) ? "answer-card not-covered" : "answer-card";
  card.innerHTML = `<div class="answer-text">${formatAnswer(answer, byNumber)}</div>`;

  if (citations.length) {
    const sources = element("div", "sources", "<h3>Sources</h3>");
    citations.forEach((citation) => sources.append(sourceItem(citation)));
    card.append(sources);
  }
  card.querySelectorAll(".cite[data-number]").forEach((button) =>
    button.addEventListener("click", () => openSource(byNumber.get(Number(button.dataset.number))))
  );
}

// Escape first, then add bold, paragraphs and a button for every known citation [n].
function formatAnswer(text, byNumber) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\[(\d+)\]/g, (match, number) =>
      byNumber.has(Number(number)) ? citeButton(number) : match
    )
    .split(/\n+/)
    .map((paragraph) => `<p>${paragraph}</p>`)
    .join("");
}

function citeButton(number) {
  return `<button type="button" class="cite" data-number="${number}" aria-label="Open source ${number}">${number}</button>`;
}

function sourceItem(citation) {
  const item = element("button", "source-item");
  item.type = "button";
  item.innerHTML = `
    <span class="cite">${citation.number}</span>
    <span>
      <strong>${escapeHtml(citation.title)}</strong>
      <small>${escapeHtml(sectionPath(citation))} · effective ${citation.effective_date}</small>
      ${labelsHtml(citation.labels)}
    </span>`;
  item.addEventListener("click", () => openSource(citation));
  return item;
}

// "Travel Policy > 4. Limits > 4.2 Hotels" -> "4. Limits › 4.2 Hotels" (the title is shown above it)
function sectionPath(citation) {
  const parts = citation.section.split(" > ");
  return parts.length > 1 ? parts.slice(1).join(" › ") : "Whole document";
}

function labelsHtml(labels) {
  const badges = labels.map((label) => {
    const kind = label.startsWith("NOT YET IN EFFECT") ? "label warning" : "label";
    return `<span class="${kind}">${escapeHtml(label)}</span>`;
  });
  return `<span class="labels">${badges.join("")}</span>`;
}

// --- Source panel -------------------------------------------------------------------

async function openSource(citation) {
  const doc = await fetchDocument(citation.doc_id);
  const meta = doc.metadata;
  document.querySelector("#source-title").textContent = doc.title;
  document.querySelector("#source-meta").textContent =
    `${meta.category} · ${meta.owner} · effective ${meta.effective_date} · ${meta.status}`;
  document.querySelector("#source-labels").innerHTML = labelsHtml(citation.labels);
  document.querySelector("#source-file").href = `/api/documents/${encodeURIComponent(doc.doc_id)}/file`;

  const body = document.querySelector("#source-body");
  body.innerHTML = highlightPassage(doc.text, citation.text);
  panel.hidden = backdrop.hidden = false;
  body.querySelector(".passage")?.scrollIntoView({ block: "center" });
}

async function fetchDocument(docId) {
  if (!documentCache.has(docId)) {
    const response = await fetch(`/api/documents/${encodeURIComponent(docId)}`);
    documentCache.set(docId, await response.json());
  }
  return documentCache.get(docId);
}

// Render the document and wrap the cited passage. A passage split from a long section
// starts with a repeated heading line, so if the full text is not found we retry without it.
function highlightPassage(documentText, passage) {
  const candidates = [passage, passage.split("\n").slice(1).join("\n")];
  const found = candidates.find((candidate) => candidate && documentText.includes(candidate));
  if (!found) return renderDocument(documentText);
  const start = documentText.indexOf(found);
  return (
    renderDocument(documentText.slice(0, start)) +
    `<div class="passage">${renderDocument(found)}</div>` +
    renderDocument(documentText.slice(start + found.length))
  );
}

// Minimal Markdown: headings, bullet lines, bold, paragraphs.
function renderDocument(text) {
  return text
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => {
      const html = escapeHtml(line).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      if (/^#{1,6} /.test(line)) return `<h4>${html.replace(/^#+ /, "")}</h4>`;
      if (line.startsWith("- ")) return `<p class="bullet">${html.slice(2)}</p>`;
      return `<p>${html}</p>`;
    })
    .join("");
}

function closeSource() {
  panel.hidden = backdrop.hidden = true;
}

document.querySelector("#close-source").addEventListener("click", closeSource);
backdrop.addEventListener("click", closeSource);
document.addEventListener("keydown", (event) => event.key === "Escape" && closeSource());

// --- Helpers ---------------------------------------------------------------------------

function element(tag, className, html = "") {
  const node = document.createElement(tag);
  node.className = className;
  node.innerHTML = html;
  return node;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
