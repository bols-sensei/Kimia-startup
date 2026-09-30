import * as ui from "../../../utils/ui.js";
const { esc, badge, label, fmtDate, pageHead, table, formModal, act, toast, byId } = ui;

const STATUSES = ["A_FAIRE", "EN_COURS", "TERMINEE", "BLOQUEE", "ANNULEE"];
const PRIORITIES = ["BASSE", "NORMALE", "HAUTE", "URGENTE"];

export default {
  title: "Activités",
  roles: null,
  events: ["activity.created", "activity.updated", "activity.completed", "activity.assigned"],
  fetch: ({ api, user }) => {
    const staff = ["CEO", "DA"].includes(user.role.name);
    return Promise.all([
      api.get("/api/activities", staff ? {} : { mine: true }),
      api.get("/api/projects"),
    ]).then(([activities, projects]) => ({ activities, projects, staff }));
  },

  render({ activities, projects, staff }) {
    const pj = byId(projects);
    const head = pageHead(
      "Activités",
      `${activities.length} activité${activities.length > 1 ? "s" : ""}`,
      staff ? `<button class="btn btn-primary" id="new">Nouvelle activité</button>` : ""
    );

    if (!activities.length) {
      return head + ui.stateHTML.empty("Aucune activité", "Les activités apparaissent ici.");
    }

    return head + table(
      [
        {
          h: "Activité",
          cls: "main-cell",
          cell: (a) => `
            <div>${esc(a.name)}</div>
            <span class="sub">${esc(pj[a.project_id]?.name || "")}</span>
          `,
        },
        { h: "Statut", cell: (a) => badge(a.status) },
        { h: "Priorité", cell: (a) => badge(a.priority) },
        { h: "Échéance", cell: (a) => fmtDate(a.end_at) },
        {
          h: "",
          cls: "r",
          cell: (a) => `<button class="btn btn-secondary btn-sm" data-edit="${a.id}">Ouvrir</button>`,
        },
      ],
      activities
    );
  },

  bind(view, { activities, projects, staff }, { api, reload }) {
    const openDetail = (activity) => {
      const canEdit = staff;
      ui.modal({
        title: activity.name,
        wide: true,
        body: `
          <div id="detail-body">
            <div class="state"><div class="spinner"></div></div>
          </div>
        `,
        onMount: async (el) => {
          try {
            const detail = await api.get(`/api/activities/${activity.id}`);
            el.querySelector("#detail-body").innerHTML = `
              <dl style="display:grid;grid-template-columns:140px 1fr;gap:8px 16px;margin-bottom:1.5rem">
                <dt style="color:var(--text-2);font-size:0.8125rem">Statut</dt>
                <dd style="margin:0">${badge(detail.status)}</dd>
                <dt style="color:var(--text-2);font-size:0.8125rem">Priorité</dt>
                <dd style="margin:0">${badge(detail.priority)}</dd>
                <dt style="color:var(--text-2);font-size:0.8125rem">Description</dt>
                <dd style="margin:0">${esc(detail.description || "—")}</dd>
                <dt style="color:var(--text-2);font-size:0.8125rem">Échéance</dt>
                <dd style="margin:0">${fmtDate(detail.end_at)}</dd>
              </dl>

              <h3 style="font-size:0.9375rem;font-weight:700;margin-bottom:0.75rem">Checklist</h3>
              <div style="display:grid;gap:6px;margin-bottom:1.5rem">
                ${(detail.checklist_items || []).length
                  ? detail.checklist_items
                      .map(
                        (c) => `
                        <label style="display:flex;align-items:center;gap:10px;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius-sm);cursor:pointer;${c.is_done ? "opacity:0.6" : ""}">
                          <input type="checkbox" data-check="${c.id}" ${c.is_done ? "checked" : ""} style="accent-color:var(--accent);width:16px;height:16px">
                          <span style="${c.is_done ? "text-decoration:line-through" : ""}">${esc(c.label)}</span>
                        </label>
                      `
                      )
                      .join("")
                  : `<p style="color:var(--text-2);font-size:0.8125rem">Aucun élément.</p>`}
              </div>

              ${canEdit ? `
                <h3 style="font-size:0.9375rem;font-weight:700;margin-bottom:0.75rem">Changer le statut</h3>
                <div style="display:flex;flex-wrap:wrap;gap:8px">
                  ${STATUSES.map((s) => `
                    <button class="btn btn-secondary btn-sm" data-status="${s}" ${s === detail.status ? "disabled" : ""}>
                      ${label(s)}
                    </button>
                  `).join("")}
                </div>
              ` : ""}
            `;

            el.querySelectorAll("[data-check]").forEach((cb) =>
              cb.addEventListener("change", async () => {
                await act(cb, () =>
                  api.patch(`/api/activities/${activity.id}/checklist/${cb.dataset.check}?is_done=${cb.checked}`)
                );
                toast("Checklist mise à jour");
              })
            );

            el.querySelectorAll("[data-status]").forEach((b) =>
              b.addEventListener("click", async () => {
                await act(b, () =>
                  api.patch(`/api/activities/${activity.id}`, { status: b.dataset.status }),
                  "Statut mis à jour"
                );
                reload();
              })
            );
          } catch (e) {
            el.querySelector("#detail-body").innerHTML = `<p style="color:var(--danger)">${esc(e.message)}</p>`;
          }
        },
      });
    };

    view.querySelector("#new")?.addEventListener("click", () => {
      formModal({
        title: "Nouvelle activité",
        fields: [
          { name: "project_id", label: "Projet", type: "select", required: true, options: projects.map((p) => ({ v: p.id, l: p.name })) },
          { name: "name", label: "Nom", required: true, full: true },
          { name: "description", label: "Description", type: "textarea", full: true },
          { name: "priority", label: "Priorité", type: "select", options: PRIORITIES.map((v) => ({ v, l: label(v) })) },
          { name: "start_at", label: "Début", type: "datetime-local" },
          { name: "end_at", label: "Fin", type: "datetime-local" },
        ],
        onSubmit: async (v) => {
          await api.post("/api/activities", v);
          toast("Activité créée");
          reload();
        },
      });
    });

    view.querySelectorAll("[data-edit]").forEach((b) =>
      b.addEventListener("click", () =>
        openDetail(activities.find((a) => a.id === +b.dataset.edit))
      )
    );
  },
};