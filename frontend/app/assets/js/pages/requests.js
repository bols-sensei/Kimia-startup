import * as ui from "../../../utils/ui.js";
const { esc, badge, fmtDate, fmtDateTime, pageHead, table, modal, formModal, act, toast } = ui;

const TRANSITIONS = {
  NOUVELLE: ["A_CONTACTER", "REFUSEE", "ANNULEE"],
  A_CONTACTER: ["EN_DISCUSSION", "REFUSEE", "ANNULEE"],
  EN_DISCUSSION: ["CONFIRMEE", "REFUSEE", "ANNULEE"],
  CONFIRMEE: ["ANNULEE"],
  REFUSEE: [],
  ANNULEE: [],
};

const isConfirmed = (status) => {
  const s = String(status).toUpperCase();
  return s === "CONFIRMEE" || s.endsWith(".CONFIRMEE");
};

export default {
  title: "Demandes",
  roles: ["CEO", "DA"],
  events: ["request.created", "request.updated"],
  fetch: ({ api }) => api.get("/api/requests"),

  render(requests) {
    const head = pageHead(
      "Demandes",
      `${requests.length} demande${requests.length > 1 ? "s" : ""}`
    );

    if (!requests.length) {
      return head + ui.stateHTML.empty(
        "Aucune demande",
        "Les demandes arrivent depuis le site public."
      );
    }

    return head + table(
      [
        {
          h: "Client",
          cls: "main-cell",
          cell: (r) => esc(r.form_data?.["Nom complet"] || "Demande #" + r.id),
        },
        { h: "Statut", cell: (r) => badge(r.status) },
        { h: "Reçue le", cell: (r) => fmtDate(r.created_at) },
        {
          h: "",
          cls: "r",
          cell: (r) => `
            <div style="display:flex;gap:6px;justify-content:flex-end">
              ${isConfirmed(r.status) ? `<button class="btn btn-primary btn-sm" data-create-project="${r.id}">Créer le projet</button>` : ""}
              <button class="btn btn-secondary btn-sm" data-open="${r.id}">Détails</button>
            </div>`,
        },
      ],
      requests
    );
  },

  bind(view, requests, { api, reload }) {
    /* ---------------- Ouvrir les détails ---------------- */
    const openDetail = (req) => {
      const m = modal({
        title: `Demande #${req.id}`,
        wide: true,
        body: `
          <dl style="display:grid;grid-template-columns:140px 1fr;gap:8px 16px;margin-bottom:1.5rem">
            <dt style="color:var(--text-2);font-size:0.8125rem">Statut</dt>
            <dd style="margin:0">${badge(req.status)}</dd>
            <dt style="color:var(--text-2);font-size:0.8125rem">Reçue le</dt>
            <dd style="margin:0">${fmtDateTime(req.created_at)}</dd>
            <dt style="color:var(--text-2);font-size:0.8125rem">Formulaire</dt>
            <dd style="margin:0">
              ${Object.entries(req.form_data || {}).map(([k, v]) => `
                <div style="margin-bottom:6px">
                  <b style="font-size:0.8125rem">${esc(k)}</b><br>
                  <span style="color:var(--text-2);font-size:0.8125rem">${esc(v)}</span>
                </div>
              `).join("")}
            </dd>
            ${req.notes ? `
              <dt style="color:var(--text-2);font-size:0.8125rem">Notes internes</dt>
              <dd style="margin:0">${esc(req.notes)}</dd>
            ` : ""}
          </dl>

          <h3 style="font-size:0.9375rem;font-weight:700;margin-bottom:0.75rem">Historique</h3>
          <div id="history"><div class="state"><div class="spinner"></div></div></div>

          <h3 style="font-size:0.9375rem;font-weight:700;margin:1.5rem 0 0.75rem">Actions</h3>
          <div style="display:flex;flex-wrap:wrap;gap:8px">
            ${(TRANSITIONS[req.status] || []).map((s) => `
              <button class="btn btn-secondary btn-sm" data-transition="${s}">
                → ${ui.label(s)}
              </button>
            `).join("") || `<span style="color:var(--text-2);font-size:0.8125rem">Aucune transition possible.</span>`}
            ${isConfirmed(req.status) ? `
              <button class="btn btn-primary btn-sm" data-create-project="${req.id}">
                Créer le projet
              </button>
            ` : ""}
          </div>
        `,
        onMount: async (el) => {
          try {
            const hist = await api.get(`/api/requests/${req.id}/history`);
            el.querySelector("#history").innerHTML = hist.length
              ? `<ul style="list-style:none;padding:0;border-left:2px solid var(--border)">${hist
                  .map(
                    (h) => `
                    <li style="padding:0 0 10px 14px;position:relative">
                      <div style="position:absolute;left:-6px;top:6px;width:10px;height:10px;border-radius:50%;background:var(--accent)"></div>
                      <b style="font-size:0.8125rem">${ui.label(h.new_status)}</b>
                      <div style="color:var(--text-3);font-size:0.75rem">${fmtDateTime(h.created_at)}</div>
                      ${h.reason ? `<div style="color:var(--text-2);font-size:0.8125rem">${esc(h.reason)}</div>` : ""}
                    </li>
                  `
                  )
                  .join("")}</ul>`
              : `<p style="color:var(--text-2);font-size:0.8125rem">Aucun historique.</p>`;
          } catch (e) {
            el.querySelector("#history").innerHTML = `<p style="color:var(--danger);font-size:0.8125rem">${esc(e.message)}</p>`;
          }

          /* Transitions */
          el.querySelectorAll("[data-transition]").forEach((b) =>
            b.addEventListener("click", async () => {
              const target = b.dataset.transition;
              const needsReason = ["REFUSEE", "ANNULEE"].includes(target);

              if (needsReason) {
                const reason = prompt("Motif (obligatoire) :");
                if (!reason) return;
                await act(b, () =>
                  api.patch(`/api/requests/${req.id}/status`, { new_status: target, reason }),
                  "Statut mis à jour"
                );
              } else {
                await act(b, () =>
                  api.patch(`/api/requests/${req.id}/status`, { new_status: target }),
                  "Statut mis à jour"
                );
              }
              m.close();
              reload();
            })
          );

          /* Bouton créer projet dans la modale */
          el.querySelectorAll("[data-create-project]").forEach((b) =>
            b.addEventListener("click", () => {
              m.close();
              openCreateProject(req);
            })
          );
        },
      });
    };

    /* ---------------- Créer un projet ---------------- */
    const openCreateProject = async (req) => {
      // Ouvre la modale immédiatement avec un loader
      modal({
        title: `Créer un projet depuis la demande #${req.id}`,
        wide: true,
        body: `
          <div id="project-modal-content">
            <div class="state">
              <div class="spinner"></div>
              <p style="color:var(--text-2);font-size:0.8125rem;margin-top:0.5rem">Chargement des données…</p>
            </div>
          </div>
        `,
        onMount: async (bodyEl, close) => {
          // Charger services + équipe
          let services = [];
          let team = [];

          try {
            const [servicesRes, teamRes] = await Promise.all([
              fetch("/api/services", {
                headers: { Authorization: "Bearer " + localStorage.getItem("kimia_token") },
              }),
              fetch("/api/users/team", {
                headers: { Authorization: "Bearer " + localStorage.getItem("kimia_token") },
              }),
            ]);

            if (!servicesRes.ok) throw new Error(`Services : erreur ${servicesRes.status}`);
            if (!teamRes.ok) throw new Error(`Équipe : erreur ${teamRes.status}`);

            services = await servicesRes.json();
            team = await teamRes.json();
          } catch (err) {
            console.error("Erreur chargement:", err);
            bodyEl.querySelector("#project-modal-content").innerHTML = `
              <div class="state err">
                <h3 class="state-title" style="color:var(--danger)">Erreur de chargement</h3>
                <p class="state-text">${esc(err.message)}</p>
                <p class="state-text" style="font-size:0.75rem;margin-top:0.5rem">Vérifiez la console (F12).</p>
              </div>
            `;
            return;
          }

          // Grouper par catégorie
          const byCat = {};
          services.forEach((s) => {
            if (!byCat[s.category_id]) byCat[s.category_id] = [];
            byCat[s.category_id].push(s);
          });

          const suggestedServiceId = req.service_id;

          // Construire le contenu
          bodyEl.querySelector("#project-modal-content").innerHTML = `
            <form id="project-form" class="form" novalidate>
              <div class="form-row">
                <div class="field field-full">
                  <label>Nom du projet <span class="required">*</span></label>
                  <input type="text" name="name" required value="Projet ${esc(req.form_data?.["Nom complet"] || "#" + req.id)}">
                </div>

                <div class="field field-full">
                  <label>Description</label>
                  <textarea name="description">${esc(req.form_data?.["Détails du projet"] || "")}</textarea>
                </div>

                <div class="field">
                  <label>Catégorie <span class="required">*</span></label>
                  <select name="category" required>
                    <option value="PHOTOGRAPHIE">Photographie</option>
                    <option value="VIDEO">Vidéo</option>
                    <option value="GRAPHISME">Graphisme</option>
                    <option value="DEVELOPPEMENT_WEB">Développement web</option>
                    <option value="COMMUNICATION">Communication</option>
                    <option value="AUTRE">Autre</option>
                  </select>
                </div>

                <div class="field">
                  <label>Responsable</label>
                  <select name="responsible_id">
                    <option value="">—</option>
                    ${team.map((u) => `<option value="${u.id}">${esc(u.name)} (${esc(u.role.name)})</option>`).join("")}
                  </select>
                </div>

                <div class="field">
                  <label>Date de l'événement</label>
                  <input type="date" name="event_date">
                </div>

                <div class="field">
                  <label>Lieu de l'événement</label>
                  <input type="text" name="event_location">
                </div>

                <div class="field field-full">
                  <label>Prestations vendues <span class="required">*</span></label>
                  <p class="field-hint" style="margin-bottom:0.75rem">
                    Sélectionnez les prestations et indiquez les montants convenus.
                  </p>
                  <div id="services-list" style="display:grid;gap:8px"></div>
                  <button type="button" class="btn btn-secondary btn-sm" id="add-service" style="margin-top:8px;align-self:flex-start">
                    + Ajouter une prestation
                  </button>
                </div>
              </div>

              <div class="modal-footer" style="border:none;padding:0;margin-top:1rem;justify-content:flex-end">
                <button type="button" class="btn btn-secondary" data-cancel>Annuler</button>
                <button type="submit" class="btn btn-primary">Créer le projet</button>
              </div>
            </form>
          `;

          const form = bodyEl.querySelector("#project-form");
          const list = form.querySelector("#services-list");

          const renderServiceRow = (serviceId = "", amount = "") => {
            const row = document.createElement("div");
            row.style.cssText = "display:grid;grid-template-columns:2fr 1fr auto;gap:8px;align-items:start";
            row.innerHTML = `
              <select class="svc-select" style="padding:10px 14px;border:1px solid var(--border);border-radius:8px;background:var(--bg-2);color:var(--text);font-size:0.875rem">
                <option value="">— Choisir une prestation —</option>
                ${Object.entries(byCat).map(([catId, svcs]) => `
                  <optgroup label="Catégorie ${catId}">
                    ${svcs.map((s) => `<option value="${s.id}" ${s.id === serviceId ? "selected" : ""}>${esc(s.name)}</option>`).join("")}
                  </optgroup>
                `).join("")}
              </select>
              <input type="number" class="svc-amount" placeholder="Montant" value="${amount}" style="padding:10px 14px;border:1px solid var(--border);border-radius:8px;background:var(--bg-2);color:var(--text);font-size:0.875rem">
              <button type="button" class="btn btn-danger btn-sm remove-svc">×</button>
            `;
            row.querySelector(".remove-svc").onclick = () => row.remove();
            list.appendChild(row);
          };

          if (suggestedServiceId) {
            const svc = services.find((s) => s.id === suggestedServiceId);
            renderServiceRow(suggestedServiceId, svc?.base_price || "");
          } else {
            renderServiceRow();
          }

          form.querySelector("#add-service").onclick = () => renderServiceRow();
          form.querySelector("[data-cancel]").onclick = close;

          // Soumission
          form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const btn = form.querySelector("[type=submit]");

            const name = form.elements["name"].value.trim();
            if (!name) {
              toast("Le nom du projet est obligatoire", "err");
              return;
            }

            const rows = form.querySelectorAll("#services-list > div");
            const svcPayload = [];
            rows.forEach((row) => {
              const svcId = row.querySelector(".svc-select").value;
              const amount = row.querySelector(".svc-amount").value;
              if (!svcId || !amount) return;
              svcPayload.push({
                service_id: Number(svcId),
                agreed_amount: Number(amount),
                currency: "XOF",
              });
            });

            if (!svcPayload.length) {
              toast("Ajoutez au moins une prestation avec un montant", "err");
              return;
            }

            btn.disabled = true;
            btn.textContent = "Création…";

            try {
              await api.post(`/api/requests/${req.id}/create-project`, {
                name,
                description: form.elements["description"].value || null,
                project_type: "CLIENT",
                category: form.elements["category"].value,
                responsible_id: form.elements["responsible_id"].value
                  ? Number(form.elements["responsible_id"].value)
                  : null,
                event_date: form.elements["event_date"].value || null,
                event_location: form.elements["event_location"].value || null,
                services: svcPayload,
              });

              toast("Projet créé avec succès !");
              close();
              reload();
            } catch (err) {
              toast(err.message || "Erreur lors de la création", "err");
              btn.disabled = false;
              btn.textContent = "Créer le projet";
            }
          });
        },
      });
    };

    /* ---------------- Événements ---------------- */
    view.querySelectorAll("[data-open]").forEach((b) =>
      b.addEventListener("click", () =>
        openDetail(requests.find((r) => r.id === +b.dataset.open))
      )
    );

    view.querySelectorAll("[data-create-project]").forEach((b) =>
      b.addEventListener("click", () =>
        openCreateProject(requests.find((r) => r.id === +b.dataset.createProject))
      )
    );
  },
};