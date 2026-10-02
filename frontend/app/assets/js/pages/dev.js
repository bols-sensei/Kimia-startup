/* Espace développement : membres dev (accès limité) et devs internes (outils internes) */
import * as ui from "../../../utils/ui.js";
const { esc, pageHead, table, toast, formModal, confirmBox, fmtDate } = ui;

const LEVELS = { INTERNAL: "Développeur interne", MEMBER: "Membre dev" };

export default {
  title: "Développement",

  async fetch({ api }) {
    const me = await api.get("/api/access/me");
    const canManage = !!me.modules.dev.manage;
    const [members, team, tools] = await Promise.all([
      api.get("/api/dev/members"),
      canManage ? api.get("/api/users/team").catch(() => []) : Promise.resolve([]),
      me.dev_level === "INTERNAL" ? api.get("/api/dev/tools").catch(() => null) : Promise.resolve(null),
    ]);
    return { me, canManage, members, team, tools };
  },

  render({ me, canManage, members, tools }) {
    const internal = members.filter((m) => m.level === "INTERNAL").length;
    const stats = `
      <div class="stats">
        <div class="stat"><div class="stat-label">Membres dev</div><div class="stat-value">${members.length}</div></div>
        <div class="stat"><div class="stat-label">Devs internes</div><div class="stat-value accent">${internal}</div></div>
        <div class="stat"><div class="stat-label">Membres (accès limité)</div><div class="stat-value">${members.length - internal}</div></div>
      </div>`;

    const list = members.length ? table([
      { h: "Nom", cell: (r) => `<b>${esc(r.name)}</b><div class="field-hint">${esc(r.email)}</div>` },
      { h: "Niveau", cell: (r) => `<span class="badge ${r.level === "INTERNAL" ? "t-g" : "t-c"}">${LEVELS[r.level]}</span>` },
      { h: "Note", cell: (r) => esc(r.note || "—") },
      { h: "Depuis", cell: (r) => fmtDate(r.created_at) },
      { h: "", cell: (r) => canManage
          ? `<button class="btn btn-secondary btn-sm" data-edit="${r.user_id}">Modifier</button>
             <button class="btn btn-danger btn-sm" data-remove="${r.user_id}">Retirer</button>` : "" },
    ], members.map((m) => ({ ...m, id: m.user_id }))) : `<div class="state"><div class="state-title">Aucun membre dans l'équipe dev</div></div>`;

    const toolsHtml = tools
      ? `<h2 style="margin:var(--space-8) 0 var(--space-4)">Outils internes</h2>
         <div class="perm-grid">${tools.map((t) => `<div class="card"><div class="card-title">${esc(t.label)}</div><div class="field-hint">${esc(t.key)}</div></div>`).join("")}</div>`
      : me.dev_level === "MEMBER"
        ? `<div class="notice" style="margin-top:var(--space-6)">Les outils internes sont réservés aux développeurs internes. L'accès se décide au cas par cas.</div>` : "";

    return `${pageHead("Développement", "Équipe, niveaux d'accès et outils internes",
      canManage ? `<button class="btn btn-primary btn-sm" id="add-dev">+ Ajouter</button>` : "")}${stats}${list}${toolsHtml}`;
  },

  bind(view, { members, team, canManage }, { api, reload }) {
    if (!canManage) return;
    const levelField = { name: "level", label: "Niveau d'accès", type: "select", required: true,
      options: [{ v: "MEMBER", l: "Membre dev — accès limité" }, { v: "INTERNAL", l: "Dev interne — outils internes" }] };
    const noteField = { name: "note", label: "Note (projet, périmètre…)", full: true };
    const save = (userId) => async (v) => {
      await api.put(`/api/dev/members/${userId}`, { level: v.level, note: v.note });
      toast("Équipe dev mise à jour");
      reload();
    };

    view.querySelector("#add-dev")?.addEventListener("click", () => {
      const taken = new Set(members.map((m) => m.user_id));
      const candidates = team.filter((u) => u.is_active && !taken.has(u.id));
      if (!candidates.length) return toast("Tous les membres actifs sont déjà dans l'équipe dev", "err");
      formModal({
        title: "Ajouter à l'équipe dev",
        fields: [{ name: "user_id", label: "Membre", type: "select", required: true, num: true, full: true,
          options: candidates.map((u) => ({ v: u.id, l: `${u.name} (${u.role.name})` })) }, levelField, noteField],
        values: { level: "MEMBER" },
        onSubmit: (v) => save(v.user_id)(v),
      });
    });

    view.querySelectorAll("[data-edit]").forEach((b) =>
      b.addEventListener("click", () => {
        const m = members.find((x) => x.user_id === +b.dataset.edit);
        formModal({ title: `Modifier ${m.name}`, fields: [levelField, noteField], values: m, onSubmit: save(m.user_id) });
      })
    );

    view.querySelectorAll("[data-remove]").forEach((b) =>
      b.addEventListener("click", async () => {
        const m = members.find((x) => x.user_id === +b.dataset.remove);
        if (!(await confirmBox(`Retirer ${m.name} de l'équipe dev ?`, "Retirer"))) return;
        await ui.act(b, async () => { await api.del(`/api/dev/members/${m.user_id}`); reload(); }, "Membre retiré");
      })
    );
  },
};
