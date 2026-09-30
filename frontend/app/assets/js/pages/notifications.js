import * as ui from "../../../utils/ui.js";
import { store } from "../../../state/store.js";
const { esc, fmtDateTime, pageHead, act } = ui;

export default {
  title: "Notifications",
  roles: null,
  events: ["notification.created"],
  fetch: ({ api }) => api.get("/api/notifications"),

  render(list) {
    const unread = list.filter((n) => !n.is_read).length;
    const head = pageHead(
      "Notifications",
      unread ? `${unread} non lue${unread > 1 ? "s" : ""}` : "Tout est lu",
      unread ? `<button class="btn btn-secondary" id="all">Tout marquer comme lu</button>` : ""
    );

    if (!list.length) {
      return head + ui.stateHTML.empty("Aucune notification", "Vous serez prévenu ici quand une activité vous est assignée.");
    }

    return head + `
      <div class="card">
        ${[...list]
          .sort((a, b) => b.id - a.id)
          .map(
            (n) => `
            <div style="display:flex;justify-content:space-between;gap:1rem;align-items:center;padding:14px 0;border-bottom:1px solid var(--border);${n.is_read ? "opacity:0.6" : ""}">
              <div>
                <div style="font-weight:600">${esc(n.title)}</div>
                <div style="font-size:0.8125rem;color:var(--text-2)">
                  ${esc(n.message)} · ${fmtDateTime(n.created_at)}
                </div>
              </div>
              <div style="display:flex;gap:6px">
                ${n.activity_id || n.project_id ? `<button class="btn btn-secondary btn-sm" data-go="${n.id}">Ouvrir</button>` : ""}
                ${!n.is_read ? `<button class="btn btn-primary btn-sm" data-read="${n.id}">Marquer lu</button>` : ""}
              </div>
            </div>
          `
          )
          .join("")}
      </div>
    `;
  },

  bind(view, list, { api, reload, navigate }) {
    const markRead = (id) => api.patch(`/api/notifications/${id}/read`);
    const sync = () =>
      api
        .get("/api/notifications", { unread_only: true })
        .then((l) => store.set({ unread: l.length }))
        .catch(() => {});

    view.querySelectorAll("[data-read]").forEach((b) =>
      b.addEventListener("click", async () => {
        await act(b, () => markRead(+b.dataset.read));
        await sync();
        reload();
      })
    );

    view.querySelectorAll("[data-go]").forEach((b) =>
      b.addEventListener("click", async () => {
        const n = list.find((x) => x.id === +b.dataset.go);
        if (!n.is_read) {
          await markRead(n.id).catch(() => {});
          sync();
        }
        navigate(n.project_id ? `#/activities?project=${n.project_id}` : "#/activities");
      })
    );

    view.querySelector("#all")?.addEventListener("click", async (e) => {
      await act(
        e.currentTarget,
        () => Promise.all(list.filter((n) => !n.is_read).map((n) => markRead(n.id))),
        "Tout est marqué comme lu"
      );
      await sync();
      reload();
    });
  },
};