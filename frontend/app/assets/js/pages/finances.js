import * as ui from "../../../utils/ui.js";
const { esc, fmtDate, fmtMoney, pageHead, table, formModal, act, toast, byId } = ui;

/* Cache local */
let selectedProjectId = null;
let selectedServiceId = null;

export default {
  title: "Finances",
  roles: ["CEO"],
  events: ["project.created", "project.updated"],

  async fetch({ api, query }) {
    const projects = await api.get("/api/projects");

    // Sélection : query → cache → premier projet
    const fromQuery = query.project ? Number(query.project) : null;
    const fromCache = selectedProjectId && projects.some((p) => p.id === selectedProjectId)
      ? selectedProjectId
      : null;
    selectedProjectId = fromQuery || fromCache || projects[0]?.id || null;

    // Charger le détail du projet sélectionné
    let projectDetail = null;
    if (selectedProjectId) {
      try {
        projectDetail = await api.get(`/api/projects/${selectedProjectId}`);
      } catch {
        projectDetail = null;
      }
    }

    // Sélection de la prestation : première du projet par défaut
    const services = projectDetail?.project_services || [];
    const validService = services.some((s) => s.id === selectedServiceId);
    selectedServiceId = validService ? selectedServiceId : services[0]?.id || null;

    // Charger le détail financier de la prestation sélectionnée
    let finance = null;
    if (selectedServiceId) {
      try {
        finance = await api.get(`/api/finance/project-services/${selectedServiceId}/detail`);
      } catch {
        finance = null;
      }
    }

    const me = await api.get("/api/access/me");
    const canManage = !!me.modules.finance.manage;
    return { projects, projectDetail, services, finance, canManage };
  },

  render({ projects, projectDetail, services, finance, canManage }) {
    /* Aucun projet */
    if (!projects.length) {
      return pageHead("Finances") + ui.stateHTML.empty(
        "Aucun projet",
        "Créez un projet pour suivre ses finances."
      );
    }

    /* Sélecteur de projet */
    const projectSelect = `
      <div style="margin-bottom:1rem">
        <label style="display:block;font-size:0.75rem;font-weight:700;color:var(--text-3);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px">
          Projet
        </label>
        <select id="project-select" style="width:100%;max-width:400px;padding:10px 14px;border-radius:8px;border:1px solid var(--border);background:var(--bg-2);color:var(--text);font-size:0.875rem">
          ${projects.map((p) => `
            <option value="${p.id}"${p.id === selectedProjectId ? " selected" : ""}>
              ${esc(p.name)}
            </option>
          `).join("")}
        </select>
      </div>
    `;

    /* Aucune prestation */
    if (!services.length) {
      return pageHead("Finances", "Suivi des revenus et rémunérations") + projectSelect + ui.stateHTML.empty(
        "Aucune prestation vendue",
        "Ajoutez une prestation à ce projet pour suivre ses finances."
      );
    }

    /* Sélecteur de prestation */
    const serviceSelect = `
      <div style="margin-bottom:1.5rem">
        <label style="display:block;font-size:0.75rem;font-weight:700;color:var(--text-3);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px">
          Prestation
        </label>
        <div style="display:flex;flex-wrap:wrap;gap:8px">
          ${services.map((s) => `
            <button class="btn ${s.id === selectedServiceId ? "btn-primary" : "btn-secondary"} btn-sm" data-service="${s.id}">
              ${esc(s.service_id ? "Prestation #" + s.service_id : "Prestation #" + s.id)}
              · ${fmtMoney(s.agreed_amount, s.currency)}
            </button>
          `).join("")}
        </div>
      </div>
    `;

    /* Chargement finance */
    if (!finance) {
      return pageHead("Finances", "Suivi des revenus et rémunérations") + projectSelect + serviceSelect + `
        <div class="state"><div class="spinner"></div></div>
      `;
    }

    /* Statistiques */
    const stats = `
      <div class="stats">
        <div class="stat">
          <div class="stat-label">Montant dû</div>
          <div class="stat-value">${fmtMoney(finance.agreed_amount)}</div>
        </div>
        <div class="stat">
          <div class="stat-label">Encaissé</div>
          <div class="stat-value success">${fmtMoney(finance.total_paid)}</div>
        </div>
        <div class="stat">
          <div class="stat-label">Restant à payer</div>
          <div class="stat-value ${Number(finance.remaining) > 0 ? "danger" : ""}">
            ${fmtMoney(finance.remaining)}
          </div>
        </div>
        <div class="stat">
          <div class="stat-label">Rémunérations</div>
          <div class="stat-value accent">${fmtMoney(finance.total_remunerated)}</div>
        </div>
      </div>
    `;

    /* Barre de progression */
    const pct = Number(finance.agreed_amount) > 0
      ? Math.min(100, (Number(finance.total_paid) / Number(finance.agreed_amount)) * 100)
      : 0;

    const progress = `
      <div class="card" style="margin-bottom:1.5rem">
        <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px">
          <h2 class="card-title" style="margin:0">Progression du paiement</h2>
          <span style="font-size:0.8125rem;color:var(--text-2);font-weight:600">${pct.toFixed(0)} %</span>
        </div>
        <div style="height:10px;border-radius:99px;background:var(--surface-2);overflow:hidden">
          <div style="height:100%;width:${pct}%;background:linear-gradient(90deg, var(--accent), var(--success));transition:width 300ms"></div>
        </div>
      </div>
    `;

    /* Boutons d'action */
    const actions = `
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:1.5rem">
        ${canManage ? `<button class="btn btn-primary btn-sm" id="add-revenue">+ Revenu</button>
        <button class="btn btn-secondary btn-sm" id="add-payment" ${!finance.revenues.length ? "disabled" : ""}>+ Paiement</button>
        <button class="btn btn-secondary btn-sm" id="add-remuneration">+ Rémunération</button>` : `<span class="field-hint">Lecture seule : la saisie est réservée au rôle comptable.</span>`}
      </div>
    `;

    /* Tableau des revenus */
    const revenuesTable = finance.revenues.length
      ? table(
          [
            { h: "Montant", cls: "num", cell: (r) => `<b>${fmtMoney(r.amount, r.currency)}</b>` },
            { h: "Créé le", cell: (r) => fmtDate(r.created_at) },
            {
              h: "Payé",
              cls: "num",
              cell: (r) => {
                const total = (r.payments || []).reduce((s, p) => s + Number(p.amount), 0);
                return fmtMoney(total, r.currency);
              },
            },
            {
              h: "Reste",
              cls: "num",
              cell: (r) => {
                const total = (r.payments || []).reduce((s, p) => s + Number(p.amount), 0);
                return fmtMoney(Number(r.amount) - total, r.currency);
              },
            },
          ],
          finance.revenues
        )
      : `<p style="color:var(--text-2);font-size:0.875rem">Aucun revenu enregistré.</p>`;

    /* Tableau des rémunérations */
    const remsTable = finance.remunerations.length
      ? table(
          [
            { h: "Bénéficiaire", cell: (r) => `Utilisateur #${r.user_id}` },
            { h: "Montant", cls: "num", cell: (r) => `<b>${fmtMoney(r.amount, r.currency)}</b>` },
            { h: "Statut", cell: (r) => r.status || "—" },
            { h: "Créée le", cell: (r) => fmtDate(r.created_at) },
          ],
          finance.remunerations
        )
      : `<p style="color:var(--text-2);font-size:0.875rem">Aucune rémunération enregistrée.</p>`;

    return (
      pageHead("Finances", "Suivi des revenus et rémunérations") +
      projectSelect +
      serviceSelect +
      stats +
      progress +
      actions +
      `
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:1rem;margin-bottom:1.5rem">
        <div class="card">
          <h2 class="card-title">Revenus</h2>
          ${revenuesTable}
        </div>
        <div class="card">
          <h2 class="card-title">Rémunérations</h2>
          ${remsTable}
        </div>
      </div>
      `
    );
  },

  bind(view, { projects, services, finance }, { api, reload, navigate }) {
    /* Changement de projet */
    view.querySelector("#project-select")?.addEventListener("change", (e) => {
      selectedProjectId = Number(e.target.value);
      selectedServiceId = null;
      navigate(`#/finances?project=${selectedProjectId}`);
      reload();
    });

    /* Changement de prestation */
    view.querySelectorAll("[data-service]").forEach((b) =>
      b.addEventListener("click", () => {
        selectedServiceId = Number(b.dataset.service);
        reload();
      })
    );

    /* Ajouter un revenu */
    view.querySelector("#add-revenue")?.addEventListener("click", () => {
      formModal({
        title: "Nouveau revenu",
        fields: [
          {
            name: "amount",
            label: "Montant",
            type: "number",
            required: true,
            full: true,
            placeholder: "Ex: 150000",
          },
          {
            name: "currency",
            label: "Devise",
            type: "select",
            options: [
              { v: "XOF", l: "XOF (FCFA)" },
              { v: "EUR", l: "EUR (€)" },
              { v: "USD", l: "USD ($)" },
            ],
          },
        ],
        values: { currency: "XOF" },
        submitLabel: "Enregistrer",
        onSubmit: async (v) => {
          await api.post("/api/finance/revenues", {
            project_service_id: selectedServiceId,
            amount: Number(v.amount),
            currency: v.currency,
          });
          toast("Revenu enregistré");
          reload();
        },
      });
    });

    /* Ajouter un paiement */
    view.querySelector("#add-payment")?.addEventListener("click", () => {
      if (!finance.revenues.length) return;

      formModal({
        title: "Nouveau paiement",
        fields: [
          {
            name: "revenue_id",
            label: "Revenu concerné",
            type: "select",
            required: true,
            full: true,
            options: finance.revenues.map((r) => ({
              v: r.id,
              l: `${fmtMoney(r.amount, r.currency)} — ${fmtDate(r.created_at)}`,
            })),
          },
          {
            name: "amount",
            label: "Montant du paiement",
            type: "number",
            required: true,
            full: true,
          },
          {
            name: "paid_at",
            label: "Date du paiement",
            type: "datetime-local",
            required: true,
            full: true,
          },
          {
            name: "method",
            label: "Moyen de paiement",
            type: "select",
            options: [
              { v: "", l: "—" },
              { v: "ESPECES", l: "Espèces" },
              { v: "MOBILE_MONEY", l: "Mobile Money" },
              { v: "VIREMENT", l: "Virement bancaire" },
              { v: "CHEQUE", l: "Chèque" },
              { v: "AUTRE", l: "Autre" },
            ],
          },
          {
            name: "notes",
            label: "Notes",
            type: "textarea",
            full: true,
          },
        ],
        values: {
          revenue_id: finance.revenues[0].id,
          paid_at: new Date().toISOString().slice(0, 16),
        },
        submitLabel: "Enregistrer",
        onSubmit: async (v) => {
          const payload = {
            revenue_id: Number(v.revenue_id),
            amount: Number(v.amount),
            paid_at: new Date(v.paid_at).toISOString(),
            method: v.method || null,
            notes: v.notes || null,
          };
          await api.post("/api/finance/payments", payload);
          toast("Paiement enregistré");
          reload();
        },
      });
    });

    /* Ajouter une rémunération */
    view.querySelector("#add-remuneration")?.addEventListener("click", async () => {
      // Charger la liste des utilisateurs pour le select
      let users = [];
      try {
        users = await api.get("/api/users/team");
      } catch {
        toast("Impossible de charger l'équipe", "err");
        return;
      }

      formModal({
        title: "Nouvelle rémunération",
        fields: [
          {
            name: "user_id",
            label: "Bénéficiaire",
            type: "select",
            required: true,
            full: true,
            options: users.map((u) => ({
              v: u.id,
              l: `${u.name} (${u.role.name})`,
            })),
          },
          {
            name: "amount",
            label: "Montant",
            type: "number",
            required: true,
            full: true,
          },
          {
            name: "currency",
            label: "Devise",
            type: "select",
            options: [
              { v: "XOF", l: "XOF (FCFA)" },
              { v: "EUR", l: "EUR (€)" },
              { v: "USD", l: "USD ($)" },
            ],
          },
          {
            name: "status",
            label: "Statut",
            type: "select",
            options: [
              { v: "PENDING", l: "En attente" },
              { v: "PAID", l: "Payée" },
            ],
          },
        ],
        values: { currency: "XOF", status: "PENDING" },
        submitLabel: "Enregistrer",
        onSubmit: async (v) => {
          await api.post("/api/finance/remunerations", {
            project_service_id: selectedServiceId,
            user_id: Number(v.user_id),
            amount: Number(v.amount),
            currency: v.currency,
            status: v.status,
          });
          toast("Rémunération enregistrée");
          reload();
        },
      });
    });
  },
};