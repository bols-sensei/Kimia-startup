import * as ui from "../../../utils/ui.js";
const { esc, badge, pageHead, byId } = ui;

let cursor = new Date(new Date().getFullYear(), new Date().getMonth(), 1);

const hhmm = (d) => `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
const dayKey = (d) => `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;

export default {
  title: "Planning",
  roles: null,
  events: ["activity.created", "activity.updated", "activity.completed", "activity.assigned"],
  async fetch({ api }) {
    const [activities, projects] = await Promise.all([
      api.get("/api/activities"),
      api.get("/api/projects"),
    ]);
    return { activities, projects };
  },

  render({ activities, projects }) {
    const pj = byId(projects);
    const y = cursor.getFullYear();
    const m = cursor.getMonth();

    const items = activities
      .filter((a) => a.start_at || a.end_at)
      .map((a) => ({
        a,
        s: new Date(a.start_at || a.end_at),
        e: new Date(a.end_at || a.start_at),
      }))
      .filter((x) => x.s.getFullYear() === y && x.s.getMonth() === m && x.a.status !== "ANNULEE")
      .sort((p, q) => p.s - q.s);

    const days = new Map();
    items.forEach((x) => {
      const k = dayKey(x.s);
      if (!days.has(k)) days.set(k, []);
      days.get(k).push(x);
    });

    const today = dayKey(new Date());
    const monthName = new Intl.DateTimeFormat("fr-FR", { month: "long", year: "numeric" }).format(cursor);

    const actions = `
      <div style="display:flex;gap:8px;align-items:center">
        <button class="btn btn-secondary btn-sm" id="prev">‹</button>
        <h2 style="min-width:11ch;text-align:center;font-size:1rem;font-weight:700;text-transform:capitalize">${monthName}</h2>
        <button class="btn btn-secondary btn-sm" id="next">›</button>
      </div>
    `;

    const head = pageHead("Planning", "Activités datées du mois", actions);

    if (!days.size) {
      return head + ui.stateHTML.empty("Rien de planifié ce mois-ci", "Ajoutez des dates à vos activités pour les voir ici.");
    }

    return head + `
      <div class="card">
        ${[...days.entries()]
          .map(([k, list]) => {
            const d = list[0].s;
            return `
              <div style="display:grid;grid-template-columns:82px 1fr;gap:1rem;padding:14px 0;border-bottom:1px solid var(--border);${k === today ? "background:var(--accent-dim);margin:0 -20px;padding-left:20px;padding-right:20px;border-radius:8px" : ""}">
                <div>
                  <div style="font-size:1.75rem;font-weight:800;line-height:1;${k === today ? "color:var(--accent)" : ""}">${d.getDate()}</div>
                  <div style="font-size:0.75rem;color:var(--text-2);text-transform:capitalize">${new Intl.DateTimeFormat("fr-FR", { weekday: "long" }).format(d)}</div>
                </div>
                <div>
                  ${list
                    .map(
                      ({ a, s, e }) => `
                        <div style="display:flex;justify-content:space-between;gap:1rem;align-items:center;padding:10px 14px;margin-bottom:6px;border-radius:8px;background:var(--surface-2);border-left:3px solid var(--accent)">
                          <div>
                            <div style="font-weight:600;font-size:0.875rem">${esc(a.name)}</div>
                            <div style="font-size:0.75rem;color:var(--text-2)">
                              ${esc(pj[a.project_id]?.name || "")}
                              ${a.start_at ? ` · ${hhmm(s)}–${hhmm(e)}` : ""}
                            </div>
                          </div>
                          ${badge(a.status)}
                        </div>
                      `
                    )
                    .join("")}
                </div>
              </div>
            `;
          })
          .join("")}
      </div>
    `;
  },

  bind(view, _d, { reload }) {
    const move = (n) => {
      cursor = new Date(cursor.getFullYear(), cursor.getMonth() + n, 1);
      reload();
    };
    view.querySelector("#prev")?.addEventListener("click", () => move(-1));
    view.querySelector("#next")?.addEventListener("click", () => move(1));
  },
};