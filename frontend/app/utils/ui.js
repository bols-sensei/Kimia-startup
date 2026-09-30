/* Composants UI réutilisables */

export const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));

/* Labels métier */
export const LABELS = {
  NOUVELLE: "Nouvelle", A_CONTACTER: "À contacter", EN_DISCUSSION: "En discussion",
  CONFIRMEE: "Confirmée", REFUSEE: "Refusée", ANNULEE: "Annulée",
  A_PREPARER: "À préparer", EN_PREPARATION: "En préparation", EN_COURS: "En cours",
  LIVRAISON: "Livraison", TERMINE: "Terminé", ANNULE: "Annulé",
  A_FAIRE: "À faire", TERMINEE: "Terminée", BLOQUEE: "Bloquée",
  BASSE: "Basse", NORMALE: "Normale", HAUTE: "Haute", URGENTE: "Urgente",
  BROUILLON: "Brouillon", A_VALIDER: "À valider", VALIDE: "Validé", A_MODIFIER: "À modifier",
  CLIENT: "Client", INTERNE: "Interne",
  PHOTOGRAPHIE: "Photographie", VIDEO: "Vidéo", GRAPHISME: "Graphisme",
  DEVELOPPEMENT_WEB: "Développement web", COMMUNICATION: "Communication", AUTRE: "Autre",
  IMAGE: "Image", CAROUSEL: "Carrousel", REEL: "Reel", STORY: "Story",
  TEXT: "Texte", LINK: "Lien",
  COFOUNDER: "Cofondateur", COLLABORATOR: "Collaborateur",
  RESPONSABLE: "Responsable", PARTICIPANT: "Participant",
};

const TONES = {
  NOUVELLE: "m", A_CONTACTER: "y", EN_DISCUSSION: "c", CONFIRMEE: "g",
  REFUSEE: "n", ANNULEE: "n", A_PREPARER: "n", EN_PREPARATION: "y",
  EN_COURS: "c", LIVRAISON: "m", TERMINE: "g", ANNULE: "n",
  A_FAIRE: "n", TERMINEE: "g", BLOQUEE: "m",
  BASSE: "n", NORMALE: "c", HAUTE: "y", URGENTE: "m",
  BROUILLON: "n", A_VALIDER: "y", VALIDE: "g", A_MODIFIER: "m",
};

export const label = (v) => LABELS[v] || v || "—";

export const badge = (v) => {
  const tone = TONES[v] || "n";
  return `<span class="badge t-${tone}">${esc(label(v))}</span>`;
};

/* Dates */
const MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];

export function fmtDate(v) {
  if (!v) return "—";
  const d = new Date(v.length === 10 ? v + "T00:00:00" : v);
  if (isNaN(d)) return "—";
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}

export function fmtDateTime(v) {
  if (!v) return "—";
  const d = new Date(v);
  if (isNaN(d)) return "—";
  return `${fmtDate(v)} · ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export const fmtMoney = (n, cur) =>
  new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(Number(n) || 0) +
  " " + (cur || window.KIMIA_CURRENCY || "XOF");

export const initials = (name) =>
  (name || "?").split(/\s+/).slice(0, 2).map((p) => p[0]).join("").toUpperCase();

export const byId = (list) => Object.fromEntries((list || []).map((x) => [x.id, x]));

/* Toasts */
export function toast(msg, kind = "ok") {
  let root = document.getElementById("toasts");
  if (!root) {
    root = document.createElement("div");
    root.id = "toasts";
    root.setAttribute("aria-live", "polite");
    document.body.append(root);
  }
  const t = document.createElement("div");
  t.className = "toast " + kind;
  t.textContent = msg;
  root.append(t);
  setTimeout(() => {
    t.classList.add("out");
    setTimeout(() => t.remove(), 300);
  }, kind === "err" ? 5000 : 2800);
}

/* Action avec bouton désactivé */
export async function act(btn, fn, okMsg) {
  if (btn) btn.disabled = true;
  try {
    const r = await fn();
    if (okMsg) toast(okMsg);
    return r;
  } catch (e) {
    toast(e.message || "Une erreur est survenue", "err");
    return undefined;
  } finally {
    if (btn && btn.isConnected) btn.disabled = false;
  }
}

/* États */
export const stateHTML = {
  loading: () => `
    <div class="state">
      <div class="spinner" role="status" aria-label="Chargement"></div>
    </div>`,
  empty: (title, hint = "") => `
    <div class="state">
      <div class="state-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5"/>
        </svg>
      </div>
      <h3 class="state-title">${esc(title)}</h3>
      ${hint ? `<p class="state-text">${esc(hint)}</p>` : ""}
    </div>`,
  error: (msg) => `
    <div class="state err">
      <h3 class="state-title">Impossible de charger</h3>
      <p class="state-text">${esc(msg)}</p>
      <button class="btn btn-secondary" data-retry>Réessayer</button>
    </div>`,
  denied: () => `
    <div class="state">
      <h3 class="state-title">Accès non autorisé</h3>
      <p class="state-text">Votre rôle ne donne pas accès à cette page.</p>
    </div>`,
};

/* Page head */
export const pageHead = (title, sub = "", actions = "") => `
  <div class="page-header">
    <div>
      <h1 class="page-title">${esc(title)}</h1>
      ${sub ? `<p class="page-subtitle">${esc(sub)}</p>` : ""}
    </div>
    ${actions ? `<div class="page-actions">${actions}</div>` : ""}
  </div>`;

/* Tableau */
export function table(cols, rows) {
  if (!rows.length) return "";
  return `
    <div class="table-wrapper">
      <table class="table">
        <thead>
          <tr>${cols.map((c) => `<th class="${c.cls || ""}">${esc(c.h)}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${rows.map((r) => `
            <tr data-id="${r.id}">
              ${cols.map((c) => `<td data-label="${esc(c.h)}" class="${c.cls || ""}">${c.cell(r)}</td>`).join("")}
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>`;
}

export function modal({ title, body, wide, onMount }) {
  const d = document.createElement("dialog");
  d.className = "modal" + (wide ? " wide" : "");

  // Forcer le style en inline (indépendant du CSS)
  d.style.cssText = `
    position: fixed !important;
    top: 50% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    border-radius: 20px !important;
    width: ${wide ? "min(820px, calc(100vw - 2rem))" : "min(560px, calc(100vw - 2rem))"} !important;
    max-height: calc(100vh - 2rem) !important;
    background: var(--surface, #151515) !important;
    color: var(--text, #fff) !important;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5) !important;
    overflow: hidden !important;
  `;

  d.innerHTML = `
    <div class="modal-header" style="display:flex;align-items:center;justify-content:space-between;padding:1.25rem;border-bottom:1px solid var(--border);flex-shrink:0">
      <h2 class="modal-title" style="font-size:1.125rem;font-weight:700">${esc(title)}</h2>
      <button type="button" class="modal-close" aria-label="Fermer" style="width:32px;height:32px;border-radius:8px;display:grid;place-items:center;color:var(--text-2);background:none;border:none;cursor:pointer">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6L6 18M6 6l12 12"/>
        </svg>
      </button>
    </div>
    <div class="modal-body" style="padding:1.25rem;overflow-y:auto;flex:1">${body}</div>`;

  document.body.append(d);

  // Ouvre la modale
  d.showModal();

  // ⚠️ CRUCIAL : forcer display:flex APRÈS showModal
  requestAnimationFrame(() => {
    d.style.setProperty("display", "flex", "important");
    d.style.setProperty("flex-direction", "column", "important");
  });

  // Bloquer le scroll du body
  document.body.style.overflow = "hidden";

  const close = () => {
    d.close();
    d.remove();
    document.body.style.overflow = "";
  };

  d.querySelector(".modal-close").onclick = close;
  d.addEventListener("cancel", (e) => { e.preventDefault(); close(); });
  d.addEventListener("mousedown", (e) => { if (e.target === d) close(); });

  const bodyEl = d.querySelector(".modal-body");
  if (onMount) onMount(bodyEl, close);
  return { el: bodyEl, close };
}

/* Confirmation */
export function confirmBox(message, okLabel = "Confirmer") {
  return new Promise((resolve) => {
    let done = false;
    const m = modal({
      title: "Confirmation",
      body: `
        <p style="margin-bottom:1.5rem;color:var(--text-2)">${esc(message)}</p>
        <div class="modal-footer" style="border:none;padding:0;">
          <button class="btn btn-secondary" data-no>Annuler</button>
          <button class="btn btn-danger" data-ok>${esc(okLabel)}</button>
        </div>`,
      onMount: (el, close) => {
        el.querySelector("[data-no]").onclick = () => { done = true; close(); resolve(false); };
        el.querySelector("[data-ok]").onclick = () => { done = true; close(); resolve(true); };
      },
    });
    m.el.closest("dialog").addEventListener("close", () => { if (!done) resolve(false); });
  });
}

/* Champs de formulaire */
function fieldHTML(f, values) {
  const v = values[f.name] ?? f.value ?? "";
  const req = f.required ? " required" : "";
  const id = "f_" + f.name;
  const full = f.full ? " field-full" : "";

  let control;
  if (f.type === "textarea") {
    control = `<textarea id="${id}" name="${f.name}"${req} placeholder="${esc(f.placeholder || "")}">${esc(v)}</textarea>`;
  } else if (f.type === "select") {
    control = `<select id="${id}" name="${f.name}"${req}>
      ${f.required ? "" : `<option value="">—</option>`}
      ${(f.options || []).map((o) =>
        `<option value="${esc(o.v)}"${String(o.v) === String(v) ? " selected" : ""}>${esc(o.l)}</option>`
      ).join("")}
    </select>`;
  } else {
    control = `<input id="${id}" name="${f.name}" type="${f.type || "text"}" value="${esc(v)}"${req}${f.type === "number" ? ' step="any" min="0"' : ""} placeholder="${esc(f.placeholder || "")}">`;
  }

  return `
    <div class="field${full}">
      <label for="${id}">${esc(f.label)}${f.required ? ' <span class="required">*</span>' : ""}</label>
      ${control}
      ${f.hint ? `<div class="field-hint">${esc(f.hint)}</div>` : ""}
    </div>`;
}

function collect(form, fields) {
  const out = {};
  for (const f of fields) {
    let v = form.elements[f.name].value.trim();
    if (v === "") { out[f.name] = null; continue; }
    if (f.type === "number" || f.num) v = Number(v);
    else if (f.type === "datetime-local") v = new Date(v).toISOString();
    out[f.name] = v;
  }
  return out;
}

export function formModal({ title, fields, values = {}, submitLabel = "Enregistrer", onSubmit, wide, extraHTML = "", onMount }) {
  return modal({
    title, wide,
    body: `
      <form class="form" novalidate>
        <div class="form-row">
          ${fields.map((f) => fieldHTML(f, values)).join("")}
        </div>
        ${extraHTML}
        <div class="modal-footer" style="border:none;padding:0;margin-top:1rem;">
          <button type="button" class="btn btn-secondary" data-cancel>Annuler</button>
          <button type="submit" class="btn btn-primary">${esc(submitLabel)}</button>
        </div>
      </form>`,
    onMount: (el, close) => {
      const form = el.querySelector("form");
      el.querySelector("[data-cancel]").onclick = close;

      // ✅ Appeler le onMount utilisateur
      if (onMount) onMount(el, close);

      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = form.querySelector("[type=submit]");
        btn.disabled = true;
        try {
          const result = await onSubmit(collect(form, fields), form);
          if (result !== false) close();
        } catch (ex) {
          toast(ex.message || "Une erreur est survenue", "err");
          btn.disabled = false;
        }
      });
    },
  });
}