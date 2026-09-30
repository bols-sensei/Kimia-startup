import * as ui from "../../../utils/ui.js";
const { esc, badge, label, fmtDateTime, pageHead, formModal, act, toast, byId } = ui;

const LANES = ["BROUILLON", "A_VALIDER", "A_MODIFIER", "VALIDE"];
const FORMATS = ["IMAGE", "CAROUSEL", "REEL", "STORY", "VIDEO", "TEXT", "LINK"];

const isStaff = (u) => ["CEO", "DA"].includes(u.role.name);

export default {
  title: "Publications",
  roles: null,
  events: ["publication.created", "publication.updated", "publication.validated"],
  async fetch({ api }) {
    const [pubs, platforms, projects] = await Promise.all([
      api.get("/api/publications"),
      api.get("/api/publications/platforms"),
      api.get("/api/projects").catch(() => []),
    ]);
    return { pubs, platforms, projects };
  },

  render({ pubs, platforms, projects }, { user }) {
    const staff = isStaff(user);
    const pf = byId(platforms);
    const pj = byId(projects);

    const card = (p) => {
      const actions = [];
      if (!staff && ["BROUILLON", "A_MODIFIER"].includes(p.status)) {
        actions.push(`<button class="btn btn-primary btn-sm" data-set="${p.id}:A_VALIDER">Soumettre</button>`);
      }
      if (staff && p.status === "A_VALIDER") {
        actions.push(`<button class="btn btn-primary btn-sm" data-set="${p.id}:VALIDE">Valider</button>`);
        actions.push(`<button class="btn btn-danger btn-sm" data-set="${p.id}:A_MODIFIER">Modifier</button>`);
      }

      return `
        <article style="background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius);padding:14px;margin-bottom:10px;display:grid;gap:8px">
          <b style="font-weight:700">${esc(p.title)}</b>
          <small style="color:var(--text-2);font-size:0.75rem">
            ${esc(pj[p.project_id]?.name || "Sans projet")}
            ${p.scheduled_at ? " · " + fmtDateTime(p.scheduled_at) : ""}
          </small>
          <div style="display:flex;flex-wrap:wrap;gap:4px">
            ${p.format ? `<span class="tag">${esc(label(p.format))}</span>` : ""}
            ${p.platform_ids.map((id) => `<span class="tag">${esc(pf[id]?.name || "")}</span>`).join("")}
          </div>
          ${p.status === "A_MODIFIER" && p.notes ? `<small style="color:var(--danger)">Retour : ${esc(p.notes)}</small>` : ""}
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            <button class="btn btn-secondary btn-sm" data-edit="${p.id}">Modifier</button>
            ${actions.join("")}
          </div>
        </article>
      `;
    };

    return pageHead(
      "Calendrier éditorial",
      `${pubs.length} publication${pubs.length > 1 ? "s" : ""}`,
      `<button class="btn btn-primary" id="new">Nouvelle publication</button>`
    ) + `
      <div style="display:grid;grid-template-columns:repeat(4,minmax(240px,1fr));gap:1rem;overflow-x:auto;padding-bottom:8px">
        ${LANES.map((s) => {
          const list = pubs
            .filter((p) => p.status === s)
            .sort((a, b) => (a.scheduled_at || "9").localeCompare(b.scheduled_at || "9"));
          return `
            <section style="background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius-lg);padding:14px;min-height:220px">
              <h2 style="font-size:0.875rem;display:flex;justify-content:space-between;padding:4px 6px 12px;font-weight:700">
                ${label(s)} <span style="color:var(--text-3);font-weight:500">${list.length}</span>
              </h2>
              ${list.map(card).join("") || `<p style="color:var(--text-3);font-size:0.8125rem;padding:6px">Vide</p>`}
            </section>
          `;
        }).join("")}
      </div>
    `;
  },

  bind(view, { pubs, platforms, projects }, { api, reload }) {
    const fields = [
      { name: "title", label: "Titre", required: true, full: true },
      { name: "project_id", label: "Projet", type: "select", options: projects.map((p) => ({ v: p.id, l: p.name })) },
      { name: "format", label: "Format", type: "select", options: FORMATS.map((v) => ({ v, l: label(v) })) },
      { name: "scheduled_at", label: "Publication prévue", type: "datetime-local", full: true },
      { name: "content", label: "Contenu", type: "textarea", full: true },
    ];

    const open = (pub) =>
      formModal({
        title: pub ? "Modifier la publication" : "Nouvelle publication",
        fields,
        values: pub || {},
        wide: true,
        onSubmit: async (v) => {
          if (pub) await api.patch(`/api/publications/${pub.id}`, v);
          else await api.post("/api/publications", v);
          toast(pub ? "Publication modifiée" : "Publication créée");
          reload();
        },
      });

    view.querySelector("#new")?.addEventListener("click", () => open());
    view.querySelectorAll("[data-edit]").forEach((b) =>
      b.addEventListener("click", () => open(pubs.find((p) => p.id === +b.dataset.edit)))
    );

    view.querySelectorAll("[data-set]").forEach((b) =>
      b.addEventListener("click", () => {
        const [id, status] = b.dataset.set.split(":");
        const send = (extra = {}) =>
          api.patch(`/api/publications/${id}`, { status, ...extra });

        if (status === "A_MODIFIER") {
          formModal({
            title: "Demander une modification",
            submitLabel: "Envoyer",
            fields: [
              { name: "notes", label: "Ce qu'il faut changer", type: "textarea", required: true, full: true },
            ],
            onSubmit: async (v) => {
              await send({ notes: v.notes });
              toast("Modification demandée");
              reload();
            },
          });
        } else {
          act(b, send, status === "VALIDE" ? "Publication validée" : "Publication soumise").then(() => reload());
        }
      })
    );
  },
};