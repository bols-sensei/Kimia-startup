/* Caisse — journal append-only. Le CEO consulte et audite ; seul le caissier écrit. */
import * as ui from "../../../utils/ui.js";
const { esc, pageHead, table, act, toast, fmtDate, fmtDateTime, formModal } = ui;

let tab = "moves";

const nf = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const money = (n, cur) => `${nf.format(Number(n) || 0)} ${cur || window.KIMIA_CURRENCY || ""}`.trim();

const CATEGORIES = ["Acompte", "Solde prestation", "Transport", "Matériel", "Location", "Salaire / prime", "Communication", "Autre"];
const AUDIT_LABELS = {
  "cash.transaction.created": "Mouvement enregistré",
  "cash.transaction.reversed": "Mouvement annulé",
  "cash.closed": "Caisse clôturée",
};

const empty = (title) => `<div class="state"><div class="state-title">${esc(title)}</div></div>`;

export default {
  title: "Caisse",
  events: ["cash.changed"],

  async fetch({ api }) {
    const me = await api.get("/api/access/me");
    const c = me.modules.cash;
    const [balance, txs, closings, audit, receivables] = await Promise.all([
      api.get("/api/cash/balance"),
      api.get("/api/cash/transactions", { limit: 200 }),
      api.get("/api/cash/closings", { limit: 60 }),
      c.audit ? api.get("/api/cash/audit", { limit: 100 }) : Promise.resolve([]),
      c.create ? api.get("/api/cash/receivables") : Promise.resolve([]),
    ]);
    return { c, balance, txs, closings, audit, receivables };
  },

  render({ c, balance, txs, closings, audit }) {
    const cur = balance.currency;
    const reversed = new Set(txs.filter((t) => t.reversal_of_id).map((t) => t.reversal_of_id));

    const actions = [
      c.create && !balance.today_closed ? `<button class="btn btn-primary btn-sm" id="cash-in">+ Entrée</button>` : "",
      c.create && !balance.today_closed ? `<button class="btn btn-secondary btn-sm" id="cash-out">− Sortie</button>` : "",
      c.close && !balance.today_closed ? `<button class="btn btn-secondary btn-sm" id="cash-close">Clôturer la journée</button>` : "",
      c.export ? `<button class="btn btn-secondary btn-sm" id="cash-export">Exporter CSV</button>` : "",
    ].join("");

    const notices = [
      !c.create ? `<div class="notice">Mode supervision : vous consultez la caisse et son historique, mais seule la personne chargée de la caisse peut saisir ou clôturer.</div>` : "",
      balance.today_closed ? `<div class="notice">La caisse est clôturée pour aujourd'hui. Les corrections se font demain par écriture inverse.</div>` : "",
    ].join("");

    const stats = `
      <div class="stats">
        <div class="stat"><div class="stat-label">Solde</div><div class="stat-value accent">${money(balance.balance, cur)}</div></div>
        <div class="stat"><div class="stat-label">Entrées</div><div class="stat-value success">${money(balance.total_in, cur)}</div></div>
        <div class="stat"><div class="stat-label">Sorties</div><div class="stat-value danger">${money(balance.total_out, cur)}</div></div>
        <div class="stat"><div class="stat-label">À clôturer</div><div class="stat-value">${balance.unclosed_count}</div></div>
      </div>`;

    const tabs = [["moves", "Mouvements"], ["closings", "Clôtures"], ...(c.audit ? [["audit", "Audit"]] : [])];
    const tabsHtml = `<div class="tabs">${tabs.map(([id, l]) =>
      `<button class="tab ${tab === id ? "active" : ""}" data-tab="${id}">${l}</button>`).join("")}</div>`;

    let body;
    if (tab === "moves") {
      body = txs.length ? table([
        { h: "Réf.", cell: (r) => `<span style="font-family:monospace">${esc(r.reference)}</span>` },
        { h: "Date", cell: (r) => fmtDate(r.entry_date) },
        { h: "Libellé", cell: (r) => `<span class="${reversed.has(r.id) ? "row-void" : ""}">${esc(r.label)}</span>` +
            (r.reversal_reason ? `<div class="field-hint">Motif : ${esc(r.reversal_reason)}</div>` : "") },
        { h: "Montant", cell: (r) => `<span class="${r.direction === "IN" ? "amount-in" : "amount-out"}">${r.direction === "IN" ? "+" : "−"} ${money(r.amount, r.currency)}</span>` },
        { h: "Statut", cell: (r) => `<span class="badge ${r.status === "CLOTUREE" ? "t-g" : "t-y"}">${r.status === "CLOTUREE" ? "Clôturée" : "Enregistrée"}</span>` +
            (reversed.has(r.id) ? ` <span class="badge t-m">Annulée</span>` : "") },
        { h: "Auteur", cell: (r) => esc(r.created_by_name || "—") },
        { h: "", cell: (r) => c.cancel && !balance.today_closed && !reversed.has(r.id) && !r.reversal_of_id
            ? `<button class="btn btn-secondary btn-sm" data-reverse="${r.id}">Annuler</button>` : "" },
      ], txs) : empty("Aucun mouvement");
    } else if (tab === "closings") {
      body = closings.length ? table([
        { h: "Date", cell: (r) => fmtDate(r.closing_date) },
        { h: "Ouverture", cell: (r) => money(r.opening_balance, cur) },
        { h: "Entrées", cell: (r) => `<span class="amount-in">${money(r.total_in, cur)}</span>` },
        { h: "Sorties", cell: (r) => `<span class="amount-out">${money(r.total_out, cur)}</span>` },
        { h: "Clôture", cell: (r) => money(r.closing_balance, cur) },
        { h: "Comptage", cell: (r) => (r.counted_balance == null ? "—" : money(r.counted_balance, cur)) },
        { h: "Écart", cell: (r) => r.difference == null ? "—" :
            `<span class="${Number(r.difference) === 0 ? "" : "amount-out"}">${money(r.difference, cur)}</span>` },
      ], closings) : empty("Aucune clôture");
    } else {
      body = audit.length ? table([
        { h: "Date", cell: (r) => fmtDateTime(r.created_at) },
        { h: "Action", cell: (r) => esc(AUDIT_LABELS[r.action] || r.action) },
        { h: "Objet", cell: (r) => esc(`${r.entity_type} #${r.entity_id}`) },
        { h: "Détail", cell: (r) => `<span class="field-hint">${esc(Object.entries(r.new_data || {}).map(([k, v]) => `${k}: ${v}`).join(" · "))}</span>` },
      ], audit) : empty("Aucune entrée d'audit");
    }

    return `${pageHead("Caisse", "Journal des entrées et sorties — non modifiable", actions)}${notices}${stats}${tabsHtml}${body}`;
  },

  bind(view, { balance, txs, receivables }, { api, reload }) {
    const cur = balance.currency;
    const $ = (s) => view.querySelector(s);

    view.querySelectorAll("[data-tab]").forEach((b) => (b.onclick = () => { tab = b.dataset.tab; reload(); }));

    const openEntry = (direction) => {
      const incoming = direction === "IN";
      formModal({
        title: incoming ? "Nouvelle entrée" : "Nouvelle sortie",
        fields: [
          { name: "label", label: "Libellé", required: true, full: true },
          { name: "amount", label: `Montant (${cur})`, type: "number", required: true },
          { name: "category", label: "Catégorie", type: "select", options: CATEGORIES.map((x) => ({ v: x, l: x })) },
          { name: "project_service_id", label: "Prestation concernée", type: "select", num: true, full: true,
            options: receivables.map((r) => ({ v: r.project_service_id, l: `${r.label} · reste ${money(r.remaining, r.currency)}` })),
            hint: incoming
              ? "Une entrée rattachée crée automatiquement le paiement du projet."
              : "Simple étiquette : aucune rémunération n'est créée." },
        ],
        submitLabel: "Enregistrer",
        onSubmit: async (v) => {
          const target = receivables.find((r) => r.project_service_id === v.project_service_id);
          await api.post("/api/cash/transactions", {
            direction,
            label: v.label,
            amount: String(v.amount),
            category: v.category,
            project_service_id: v.project_service_id,
            currency: target ? target.currency : undefined,
          });
          toast(incoming ? "Entrée enregistrée" : "Sortie enregistrée");
          reload();
        },
      });
    };
    $("#cash-in")?.addEventListener("click", () => openEntry("IN"));
    $("#cash-out")?.addEventListener("click", () => openEntry("OUT"));

    view.querySelectorAll("[data-reverse]").forEach((b) =>
      b.addEventListener("click", () => {
        const tx = txs.find((t) => t.id === +b.dataset.reverse);
        formModal({
          title: `Annuler ${tx.reference}`,
          fields: [{ name: "reason", label: "Motif de l'annulation", type: "textarea", required: true, full: true,
            hint: "Une écriture inverse est créée ; le mouvement d'origine est conservé." }],
          submitLabel: "Annuler le mouvement",
          onSubmit: async (v) => {
            await api.post(`/api/cash/transactions/${tx.id}/reverse`, { reason: v.reason });
            toast("Mouvement annulé");
            reload();
          },
        });
      })
    );

    $("#cash-close")?.addEventListener("click", () =>
      formModal({
        title: "Clôturer la caisse",
        fields: [
          { name: "counted_balance", label: `Solde compté (${cur})`, type: "number", full: true,
            hint: `Solde théorique : ${money(balance.balance, cur)}` },
          { name: "notes", label: "Notes", type: "textarea", full: true },
        ],
        extraHTML: `<div class="notice">Après la clôture, plus aucun mouvement ne peut être saisi ni annulé avant demain.</div>`,
        submitLabel: "Clôturer",
        onSubmit: async (v) => {
          await api.post("/api/cash/closings", {
            counted_balance: v.counted_balance == null ? null : String(v.counted_balance),
            notes: v.notes,
          });
          toast("Caisse clôturée");
          reload();
        },
      })
    );

    $("#cash-export")?.addEventListener("click", (e) =>
      act(e.currentTarget, () => api.download("/api/cash/transactions/export.csv", "caisse.csv"))
    );
  },
};
