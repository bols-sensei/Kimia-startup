/* Mes accès (tous) + Rôles & permissions (permission roles.manage) */
import * as ui from "../../../utils/ui.js";
const { esc, pageHead, toast, formModal, confirmBox } = ui;

let tab = "mine";

const MODULES = {
  cash: { label: "Caisse", actions: { view: "Voir les mouvements", create: "Saisir entrées et sorties", cancel: "Annuler un mouvement", close: "Clôturer la journée", audit: "Consulter l'audit", export: "Exporter" } },
  finance: { label: "Finance", actions: { view: "Voir revenus et paiements", manage: "Saisir revenus, paiements, rémunérations" } },
  team: { label: "Équipe", actions: { view: "Voir les membres", manage: "Gérer les membres", skills: "Gérer les compétences" } },
  dev: { label: "Développement", actions: { view: "Voir l'équipe dev", manage: "Gérer l'équipe dev", "tools.use": "Utiliser les outils internes" } },
};
const GROUP_LABELS = {
  cash: "Caisse", finance: "Finance", team: "Équipe", roles: "Rôles", dev: "Développement", security: "Sécurité", chat: "Chat",
  projects: "Projets", clients: "Clients", requests: "Demandes", activities: "Activités", planning: "Planning",
  publications: "Publications", portfolio: "Réalisations", services: "Services", documents: "Documents",
  dashboard: "Tableau de bord", notifications: "Notifications",
};
const dev = { INTERNAL: "Développeur interne", MEMBER: "Membre dev" };

const item = (on, text) =>
  `<div class="perm-item ${on ? "on" : ""}"><span class="perm-dot">${on ? "✓" : ""}</span><span>${esc(text)}</span></div>`;

function mineHTML(me) {
  const cards = Object.entries(MODULES).map(([key, m]) => `
    <div class="card">
      <div class="card-title">${m.label}</div>
      ${Object.entries(m.actions).map(([a, text]) => item(!!me.modules[key]?.[a], text)).join("")}
    </div>`).join("");
  const note = me.modules.cash && !me.modules.cash.create && me.modules.cash.view
    ? `<div class="notice">Vous supervisez la caisse : consultation et audit uniquement. La saisie est réservée à la personne chargée de la caisse.</div>` : "";
  return `
    <div class="stats">
      <div class="stat"><div class="stat-label">Rôle</div><div class="stat-value">${esc(me.role)}</div></div>
      <div class="stat"><div class="stat-label">Statut</div><div class="stat-value">${esc(({ ACTIVE: "Actif", ABSENT: "Absent", LEAVE: "Congé", SUSPENDED: "Suspendu", LEFT: "Parti" })[me.employment_status] || me.employment_status)}</div></div>
      <div class="stat"><div class="stat-label">Espace dev</div><div class="stat-value">${me.dev_level ? esc(dev[me.dev_level]) : "—"}</div></div>
    </div>
    ${note}
    <p class="page-subtitle" style="margin-bottom:var(--space-4)">Ces accès sont définis par votre rôle. Ils expliquent ce que vous pouvez faire ; vous ne pouvez pas les modifier ici.</p>
    <div class="perm-grid">${cards}</div>`;
}

function groupOf(code) { return code.split(".")[0]; }

function rolesHTML(roles, catalog) {
  const groups = {};
  catalog.forEach((p) => (groups[groupOf(p.code)] ||= []).push(p));
  return roles.map((r) => {
    const locked = r.permission_codes.includes("*");
    const granted = new Set(r.permission_codes);
    return `
      <div class="card" style="margin-bottom:var(--space-4)" data-role="${r.id}">
        <div style="display:flex;justify-content:space-between;gap:1rem;align-items:center;flex-wrap:wrap">
          <div>
            <div class="card-title" style="margin:0">${esc(r.name)}</div>
            <div class="field-hint">${r.users_count} membre(s) · ${locked ? "accès complet (protégé)" : `${r.permission_codes.length} permission(s)`}</div>
          </div>
          ${locked ? `<span class="badge t-g">Protégé</span>` : `<button class="btn btn-primary btn-sm" data-save="${r.id}">Enregistrer</button>`}
        </div>
        ${locked ? `<div class="notice" style="margin-top:var(--space-4)">Le rôle CEO voit tout mais n'écrit ni en caisse ni en finance : ces écritures se donnent à un rôle dédié.</div>` : `
        <div class="perm-grid" style="margin-top:var(--space-4)">
          ${Object.entries(groups).map(([g, perms]) => `
            <div>
              <div class="stat-label" style="margin-bottom:.25rem">${esc(GROUP_LABELS[g] || g)}</div>
              ${perms.map((p) => `
                <label class="perm-item" style="cursor:pointer">
                  <input type="checkbox" data-perm="${esc(p.code)}" ${granted.has(p.code) ? "checked" : ""} style="accent-color:var(--brand-green)">
                  <span title="${esc(p.code)}">${esc(p.description || p.code)}</span>
                </label>`).join("")}
            </div>`).join("")}
        </div>`}
      </div>`;
  }).join("");
}

export default {
  title: "Mes accès",

  async fetch({ api }) {
    const me = await api.get("/api/access/me");
    const canRoles = me.permissions.includes("roles.manage");
    const [roles, catalog] = canRoles
      ? await Promise.all([api.get("/api/access/roles"), api.get("/api/access/permissions")])
      : [[], []];
    return { me, canRoles, roles, catalog };
  },

  render({ me, canRoles, roles, catalog }) {
    const tabs = canRoles
      ? `<div class="tabs">
           <button class="tab ${tab === "mine" ? "active" : ""}" data-tab="mine">Mes accès</button>
           <button class="tab ${tab === "roles" ? "active" : ""}" data-tab="roles">Rôles &amp; permissions</button>
         </div>` : "";
    const actions = canRoles && tab === "roles" ? `<button class="btn btn-primary btn-sm" id="new-role">+ Nouveau rôle</button>` : "";
    return `${pageHead(tab === "roles" && canRoles ? "Rôles & permissions" : "Mes accès", "", actions)}${tabs}
      ${tab === "roles" && canRoles ? rolesHTML(roles, catalog) : mineHTML(me)}`;
  },

  bind(view, { roles, catalog }, { api, reload }) {
    view.querySelectorAll("[data-tab]").forEach((b) => (b.onclick = () => { tab = b.dataset.tab; reload(); }));

    view.querySelectorAll("[data-save]").forEach((b) =>
      b.addEventListener("click", async () => {
        const card = view.querySelector(`[data-role="${b.dataset.save}"]`);
        const codes = [...card.querySelectorAll("[data-perm]:checked")].map((i) => i.dataset.perm);
        await ui.act(b, async () => {
          await api.put(`/api/access/roles/${b.dataset.save}/permissions`, { permission_codes: codes });
          reload();
        }, "Permissions enregistrées");
      })
    );

    view.querySelector("#new-role")?.addEventListener("click", () =>
      formModal({
        title: "Nouveau rôle",
        fields: [
          { name: "name", label: "Nom du rôle", required: true, full: true, placeholder: "Chef de projet" },
          { name: "description", label: "Description", type: "textarea", full: true },
        ],
        submitLabel: "Créer",
        onSubmit: async (v) => {
          await api.post("/api/access/roles", { name: v.name, description: v.description, permission_codes: [] });
          toast("Rôle créé : cochez ses permissions puis enregistrez");
          reload();
        },
      })
    );
  },
};
