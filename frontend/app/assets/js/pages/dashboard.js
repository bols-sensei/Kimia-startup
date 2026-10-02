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
    // On récupère les données nécessaires
    const [projects, activities, publications, requests] = await Promise.all([
      api.get("/api/projects"),
      api.get("/api/activities"),
      api.get("/api/publications").catch(() => []),
      api.get("/api/requests").catch(() => []), // Ajout des demandes pour le dashboard
    ]);
    return { projects, activities, publications, requests, staff };
  },

  render({ projects, activities, publications, requests, staff }, { user }) {
    const now = Date.now();
    const week = now + 7 * 864e5;

    // --- Calculs des données ---
    const openActivities = activities.filter((a) => !DONE.includes(a.status));
    const late = openActivities.filter((a) => a.end_at && new Date(a.end_at) < now);
    const soon = openActivities
      .filter((a) => a.end_at && new Date(a.end_at) >= now && new Date(a.end_at) <= week)
      .sort((a, b) => new Date(a.end_at) - new Date(b.end_at));

    const activeProjects = projects.filter((p) =>
      ["EN_PREPARATION", "EN_COURS", "LIVRAISON"].includes(p.status)
    );

    // Demandes récentes (pour la carte "Activité récente")
    const recentRequests = requests.slice(0, 4);
    
    // Données pour le graphique (exemple basé sur les projets par catégorie ou statut)
    // Ici, on simule une répartition par statut de projet pour le graphique
    const projectStats = {
      "En cours": projects.filter(p => p.status === "EN_COURS").length,
      "Livraison": projects.filter(p => p.status === "LIVRAISON").length,
      "Terminé": projects.filter(p => p.status === "TERMINE").length,
      "En prépa": projects.filter(p => p.status === "EN_PREPARATION").length,
    };

    const first = user.name.split(" ")[0];

    // --- Composants UI ---

    // 1. Carte de statistique avec icône colorée (style image)
    const statCard = (label, value, iconSvg, colorClass = "") => `
      <div class="stat" style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
          <div class="stat-label">${esc(label)}</div>
          <div class="stat-value ${colorClass}">${value}</div>
        </div>
        <div style="width:40px; height:40px; border-radius:10px; background:var(--surface-2); display:grid; place-items:center; color:var(--text-2);">
          ${iconSvg}
        </div>
      </div>`;

    // 2. Graphique en barres simple (CSS pur)
    const chartBars = Object.entries(projectStats).map(([key, val]) => {
      const maxVal = Math.max(...Object.values(projectStats), 1);
      const height = (val / maxVal) * 100;
      return `
        <div style="flex:1; display:flex; flex-direction:column; align-items:center; gap:6px; height:100%; justify-content:flex-end;">
          <div style="width:100%; max-width:24px; height:${height}%; background:var(--grad-brand); border-radius:4px 4px 0 0; min-height:4px; transition:height 300ms;" title="${val}"></div>
          <span style="font-size:0.65rem; color:var(--text-3); text-align:center; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; width:100%;">${key}</span>
        </div>
      `;
    }).join("");

    // 3. Cercle de progression (CSS pur)
    const totalActivities = activities.length;
    const completedActivities = activities.filter(a => a.status === "TERMINEE").length;
    const completionRate = totalActivities > 0 ? Math.round((completedActivities / totalActivities) * 100) : 0;
    
    const progressRing = `
      <div style="position:relative; width:100px; height:100px; margin:0 auto;">
        <svg width="100" height="100" viewBox="0 0 100 100" style="transform:rotate(-90deg)">
          <circle cx="50" cy="50" r="40" stroke="var(--surface-2)" stroke-width="10" fill="none" />
          <circle cx="50" cy="50" r="40" stroke="var(--accent-text)" stroke-width="10" fill="none" 
                  stroke-dasharray="251.2" stroke-dashoffset="${251.2 - (251.2 * completionRate / 100)}" 
                  stroke-linecap="round" />
        </svg>
        <div style="position:absolute; top:50%; left:50%; transform:translate(-50%, -50%); font-weight:800; font-size:1.25rem;">
          ${completionRate}%
        </div>
      </div>
      <p style="text-align:center; font-size:0.75rem; color:var(--text-2); margin-top:8px;">Taux d'achèvement</p>
    `;

    // 4. Liste des activités récentes (style épuré)
    const actRow = (a) => `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:12px 0; border-bottom:1px solid var(--border);">
        <div style="display:flex; align-items:center; gap:12px;">
          <div style="width:8px; height:8px; border-radius:50%; background:${new Date(a.end_at) < now ? 'var(--danger)' : 'var(--accent-text)'};"></div>
          <div>
            <div style="font-weight:600; font-size:0.875rem;">${esc(a.name)}</div>
            <div style="font-size:0.75rem; color:var(--text-3);">${esc(byId(projects)[a.project_id]?.name || "Sans projet")}</div>
          </div>
        </div>
        <div style="font-size:0.75rem; color:${new Date(a.end_at) < now ? 'var(--danger)' : 'var(--text-2)'}; font-weight:500;">
          ${fmtDate(a.end_at)}
        </div>
      </div>`;

    // 5. Liste des demandes récentes
    const reqRow = (r) => `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:12px 0; border-bottom:1px solid var(--border);">
        <div>
          <div style="font-weight:600; font-size:0.875rem;">${esc(r.form_data?.["Nom complet"] || "Demande #" + r.id)}</div>
          <div style="font-size:0.75rem; color:var(--text-3);">${fmtDate(r.created_at)}</div>
        </div>
        <div>${ui.badge(r.status)}</div>
      </div>`;

    return `
      ${pageHead(
        `Bonjour ${first}`,
        new Intl.DateTimeFormat("fr-FR", { dateStyle: "full" }).format(new Date())
      )}

      <!-- Rangée 1 : Statistiques rapides (style cartes de l'image) -->
      <div class="stats" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
        ${statCard("Projets actifs", activeProjects.length, '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6.5A1.5 1.5 0 014.5 5h4l2 2.5h9A1.5 1.5 0 0121 9v9.5a1.5 1.5 0 01-1.5 1.5h-15A1.5 1.5 0 013 18.5z"/></svg>')}
        ${statCard("Activités ouvertes", openActivities.length, '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3.5" y="3.5" width="17" height="17" rx="3"/><path d="M8 12.5l3 3 5-6"/></svg>')}
        ${statCard("En retard", late.length, '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>', late.length > 0 ? "danger" : "")}
        ${statCard("Publications", publications.length, '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 10v4h3l7 4V6L7 10z"/><path d="M18 9.5a4 4 0 010 5"/></svg>')}
      </div>

      <!-- Rangée 2 : Graphiques et Progression -->
      <div style="display:grid; grid-template-columns: 2fr 1fr; gap:var(--space-4); margin-bottom:var(--space-4);">
        <!-- Graphique en barres -->
        <div class="card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
            <h2 class="card-title" style="margin:0;">Répartition des projets</h2>
            <span class="badge t-c">Par statut</span>
          </div>
          <div style="height:160px; display:flex; align-items:flex-end; gap:1rem; padding-top:1rem;">
            ${chartBars || '<p style="color:var(--text-3); font-size:0.875rem;">Aucune donnée</p>'}
          </div>
        </div>

        <!-- Cercle de progression -->
        <div class="card" style="display:flex; flex-direction:column; justify-content:center;">
          <h2 class="card-title" style="margin-bottom:1rem;">Progression globale</h2>
          ${progressRing}
        </div>
      </div>

      <!-- Rangée 3 : Listes détaillées -->
      <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap:var(--space-4);">
        <!-- Colonne Activités -->
        <div class="card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
            <h2 class="card-title" style="margin:0;">Activités récentes</h2>
            <a href="#/activities" style="font-size:0.75rem; color:var(--accent-text); font-weight:600;">Voir tout →</a>
          </div>
          ${openActivities.length
            ? openActivities.slice(0, 5).map(actRow).join("")
            : `<p style="color:var(--text-2); font-size:0.875rem;">Aucune activité en cours.</p>`}
        </div>

        <!-- Colonne Demandes -->
        <div class="card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
            <h2 class="card-title" style="margin:0;">Dernières demandes</h2>
            <a href="#/requests" style="font-size:0.75rem; color:var(--accent-text); font-weight:600;">Voir tout →</a>
          </div>
          ${recentRequests.length
            ? recentRequests.map(reqRow).join("")
            : `<p style="color:var(--text-2); font-size:0.875rem;">Aucune demande récente.</p>`}
        </div>
      </div>
    `;
  },
};