import * as ui from "../../../utils/ui.js";
const { esc, pageHead, fmtDate, byId } = ui;

const DONE = ["TERMINEE", "ANNULEE"];

export default {
  title: "Tableau de bord",
  roles: null,
  events: [
    "request.created", "request.updated",
    "project.created", "project.updated",
    "activity.created", "activity.updated", "activity.completed", "activity.assigned",
    "publication.created", "publication.updated", "publication.validated",
  ],

  async fetch({ api, user }) {
    const staff = ["CEO", "DA"].includes(user.role.name);
    const [projects, activities, publications] = await Promise.all([
      api.get("/api/projects"),
      api.get("/api/activities"),
      api.get("/api/publications").catch(() => []),
    ]);
    return { projects, activities, publications, staff };
  },

  render({ projects, activities, publications, staff }, { user }) {
    const now = Date.now();
    const week = now + 7 * 864e5;

    const openActivities = activities.filter((a) => !DONE.includes(a.status));
    const late = openActivities.filter((a) => a.end_at && new Date(a.end_at) < now);
    const soon = openActivities
      .filter((a) => a.end_at && new Date(a.end_at) >= now && new Date(a.end_at) <= week)
      .sort((a, b) => new Date(a.end_at) - new Date(b.end_at));

    const activeProjects = projects.filter((p) =>
      ["EN_PREPARATION", "EN_COURS", "LIVRAISON"].includes(p.status)
    );

    const pj = byId(projects);
    const first = user.name.split(" ")[0];

    const stat = (label, value, tone = "") => `
      <div class="stat">
        <div class="stat-label">${esc(label)}</div>
        <div class="stat-value ${tone}">${value}</div>
      </div>`;

    const actRow = (a) => `
      <div style="display:flex;justify-content:space-between;gap:1rem;align-items:center;padding:10px 0;border-bottom:1px solid var(--border);">
        <div>
          <div style="font-weight:600;">${esc(a.name)}</div>
          <div style="font-size:0.8125rem;color:var(--text-2);">${esc(pj[a.project_id]?.name || "")}</div>
        </div>
        <span style="font-size:0.8125rem;color:${new Date(a.end_at) < now ? "var(--danger)" : "var(--text-2)"};font-weight:500;">
          ${fmtDate(a.end_at)}
        </span>
      </div>`;

    return `
      ${pageHead(
        `Bonjour ${first}`,
        new Intl.DateTimeFormat("fr-FR", { dateStyle: "full" }).format(new Date())
      )}

      <div class="stats">
        ${stat("Projets actifs", activeProjects.length)}
        ${stat("Activités ouvertes", openActivities.length)}
        ${stat("En retard", late.length, late.length > 0 ? "danger" : "")}
        ${stat("Publications", publications.length)}
      </div>

      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:var(--space-4);">
        <div class="card">
          <h2 class="card-title">En retard</h2>
          ${late.length
            ? late.slice(0, 6).map(actRow).join("")
            : `<p style="color:var(--text-2);font-size:0.875rem;">Rien en retard. Bon rythme.</p>`}
        </div>

        <div class="card">
          <h2 class="card-title">Cette semaine</h2>
          ${soon.length
            ? soon.slice(0, 6).map(actRow).join("")
            : `<p style="color:var(--text-2);font-size:0.875rem;">Aucune échéance dans les 7 prochains jours.</p>`}
        </div>
      </div>
    `;
  },
};