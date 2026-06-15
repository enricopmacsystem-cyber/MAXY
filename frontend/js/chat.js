import { authHeaders } from "./auth.js";

const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const questionEl = document.getElementById("question");
const sourceFileEl = document.getElementById("source-file");
const sendBtn = document.getElementById("send-btn");

let chatInitialized = false;

export function initChat({ authRequired = false, disabled = false } = {}) {
  if (chatInitialized) {
    sendBtn.disabled = disabled;
    return;
  }
  chatInitialized = true;
  sendBtn.disabled = disabled;
  if (authRequired && disabled) {
    appendMessage("Effettua il login con le credenziali EasyOne per usare l'assistente.", "error");
  }
}

function appendMessage(text, role, extraHtml = "") {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.innerHTML = `${escapeHtml(text)}${extraHtml}`;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderList(title, items, formatter) {
  if (!items || items.length === 0) {
    return `<div class="section-block"><h4>${title}</h4><p class="muted">Nessun elemento</p></div>`;
  }
  const list = items.map(formatter).join("");
  return `<div class="section-block"><h4>${title}</h4><ul>${list}</ul></div>`;
}

function availabilityClass(status) {
  if (status === "esaurito") return "badge-danger";
  if (status === "scorte_basse") return "badge-warning";
  return "badge-success";
}

function renderStructuredResponse(data) {
  const sections = [];

  sections.push(`<div class="section-block summary"><h4>Risposta operativa</h4><p>${escapeHtml(data.answer)}</p></div>`);

  if (data.article) {
    sections.push(`
      <div class="section-block">
        <h4>Articolo</h4>
        <p><strong>${escapeHtml(data.article.internal_code)}</strong> — ${escapeHtml(data.article.manufacturer)}</p>
        <p>Categoria: ${escapeHtml(data.article.category)} | Prezzo: ${escapeHtml(data.article.price)} EUR</p>
      </div>
    `);
  }

  if (data.availability) {
    sections.push(`
      <div class="section-block">
        <h4>Disponibilità</h4>
        <span class="badge ${availabilityClass(data.availability.status)}">${escapeHtml(data.availability.status_label)}</span>
      </div>
    `);
  }

  if (data.description) {
    sections.push(`
      <div class="section-block">
        <h4>Descrizione</h4>
        <p>${escapeHtml(data.description)}</p>
      </div>
    `);
  }

  const doc = data.documentation || {};
  let docHtml = `<div class="section-block"><h4>Documentazione</h4>`;
  if (doc.manual_url) {
    docHtml += `<p>Manuale: <a href="${escapeHtml(doc.manual_url)}" target="_blank" rel="noopener">${escapeHtml(doc.manual_url)}</a></p>`;
  }
  if (doc.datasheet_url) {
    docHtml += `<p>Scheda tecnica: <a href="${escapeHtml(doc.datasheet_url)}" target="_blank" rel="noopener">${escapeHtml(doc.datasheet_url)}</a></p>`;
  }
  if (doc.technical_summary) {
    docHtml += `<p><strong>Note tecniche (PDF):</strong> ${escapeHtml(doc.technical_summary)}</p>`;
  }
  if (doc.pdf_sources && doc.pdf_sources.length > 0) {
    docHtml += "<ul>";
    doc.pdf_sources.forEach((source) => {
      docHtml += `<li>${escapeHtml(source.pdf_name)} — Pag. ${source.page}, ${escapeHtml(source.section)}</li>`;
    });
    docHtml += "</ul>";
  }
  if (!doc.manual_url && !doc.datasheet_url && !doc.technical_summary && (!doc.pdf_sources || doc.pdf_sources.length === 0)) {
    docHtml += `<p class="muted">Nessuna documentazione disponibile</p>`;
  }
  docHtml += "</div>";
  sections.push(docHtml);

  const compat = data.compatibility;
  if (compat) {
    sections.push(renderList("Accessori compatibili", compat.accessories, (item) =>
      `<li>${escapeHtml(item.product.internal_code)} — ${escapeHtml(item.product.description)}</li>`
    ));
    sections.push(renderList("Alternative", compat.alternatives, (item) =>
      `<li>${escapeHtml(item.product.internal_code)} — ${escapeHtml(item.product.description)}</li>`
    ));
    sections.push(renderList("Ricambi", compat.spare_parts, (item) =>
      `<li>${escapeHtml(item.product.internal_code)} — ${escapeHtml(item.product.description)}</li>`
    ));
    sections.push(renderList("Complementari", compat.complementary, (item) =>
      `<li>${escapeHtml(item.product.internal_code)} — ${escapeHtml(item.product.description)}</li>`
    ));
  }

  sections.push(renderList("Suggerimenti commerciali", data.commercial_suggestions, (item) => {
    const pct = item.correlation_percent ? ` (${escapeHtml(item.correlation_percent)}%)` : "";
    return `<li><strong>${escapeHtml(item.internal_code)}</strong>${pct} — ${escapeHtml(item.reason)}</li>`;
  }));

  sections.push(`
    <div class="meta">
      Catalogo: ${data.catalog_matches} match | PDF: ${data.pdf_chunks_found} estratti
    </div>
  `);

  return `<div class="structured-response">${sections.join("")}</div>`;
}

formEl.addEventListener("submit", async (event) => {
  event.preventDefault();

  const question = questionEl.value.trim();
  if (!question) {
    return;
  }

  const sourceFile = sourceFileEl.value.trim();

  appendMessage(question, "user");
  questionEl.value = "";
  sendBtn.disabled = true;

  try {
    const payload = { question };
    if (sourceFile) {
      payload.source_file = sourceFile;
    }

    const response = await fetch("/api/chat/ask", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok) {
      const detail = data.detail || "Errore durante la richiesta.";
      appendMessage(detail, "error");
      return;
    }

    appendMessage("", "assistant", renderStructuredResponse(data));
  } catch (error) {
    appendMessage(
      "Impossibile contattare il server. Verifica che l'applicazione sia avviata.",
      "error"
    );
  } finally {
    sendBtn.disabled = false;
    questionEl.focus();
  }
});
