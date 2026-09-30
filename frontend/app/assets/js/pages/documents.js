import * as ui from "../../../utils/ui.js";
const { esc, fmtDate, pageHead, table, act, confirmBox, toast } = ui;

const MAX_MB = window.KIMIA_MAX_MB || 20;
const size = (n) => (n > 1048576 ? (n / 1048576).toFixed(1) + " Mo" : Math.max(1, Math.round(n / 1024)) + " Ko");

let selected = "";

export default {
  title: "Documents",
  roles: null,
  events: ["document.created"],
  async fetch({ api, query }) {
    const projects = await api.get("/api/projects");
    selected =
      query.project ||
      (projects.some((p) => String(p.id) === String(selected)) ? selected : projects[0]?.id ?? "");
    const documents = selected ? await api.get("/api/documents", { project_id: selected }) : [];
    return { projects, documents };
  },

  render({ projects, documents }, { user }) {
    if (!projects.length) {
      return pageHead("Documents") + ui.stateHTML.empty("Aucun projet", "Les documents sont rattachés à un projet.");
    }

    const staff = ["CEO", "DA"].includes(user.role.name);
    const head =
      pageHead(
        "Documents",
        `Limite ${MAX_MB} Mo par fichier`,
        `<label class="btn btn-primary" style="cursor:pointer">Ajouter<input id="file" type="file" hidden></label>`
      ) +
      `<div style="margin-bottom:1rem">
        <select id="proj" style="padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--bg-2);color:var(--text);font-size:0.875rem">
          ${projects.map((p) => `<option value="${p.id}"${String(p.id) === String(selected) ? " selected" : ""}>${esc(p.name)}</option>`).join("")}
        </select>
      </div>`;

    if (!documents.length) {
      return head + ui.stateHTML.empty("Aucun document pour ce projet", "Ajoutez un brief, un devis ou un livrable.");
    }

    return head + table(
      [
        { h: "Nom", cls: "main-cell", cell: (d) => esc(d.name) },
        { h: "Type", cell: (d) => `<span class="tag">${esc(d.mime_type)}</span>` },
        { h: "Taille", cls: "num", cell: (d) => size(d.size) },
        { h: "Ajouté le", cell: (d) => fmtDate(d.created_at) },
        {
          h: "",
          cls: "r",
          cell: (d) => `
            <div style="display:flex;gap:6px;justify-content:flex-end">
              <button class="btn btn-secondary btn-sm" data-dl="${d.id}">Télécharger</button>
              ${staff ? `<button class="btn btn-danger btn-sm" data-rm="${d.id}">Supprimer</button>` : ""}
            </div>`,
        },
      ],
      documents
    );
  },

  bind(view, { documents }, { api, reload, navigate }) {
    view.querySelector("#proj")?.addEventListener("change", (e) => {
      selected = e.target.value;
      navigate(`#/documents?project=${selected}`);
      reload();
    });

    view.querySelector("#file")?.addEventListener("change", async (e) => {
      const f = e.target.files[0];
      if (!f) return;
      if (f.size > MAX_MB * 1048576) {
        toast(`Ce fichier dépasse ${MAX_MB} Mo.`, "err");
        e.target.value = "";
        return;
      }
      await act(null, () => api.upload("/api/documents", { project_id: selected }, f), "Document ajouté");
      reload();
    });

    view.querySelectorAll("[data-dl]").forEach((b) =>
      b.addEventListener("click", () => {
        const d = documents.find((x) => x.id === +b.dataset.dl);
        act(b, () => api.download(`/api/documents/${d.id}/download`, d.name));
      })
    );

    view.querySelectorAll("[data-rm]").forEach((b) =>
      b.addEventListener("click", async () => {
        const d = documents.find((x) => x.id === +b.dataset.rm);
        if (!(await confirmBox(`Supprimer « ${d.name} » ? Cette action est définitive.`, "Supprimer"))) return;
        await act(b, () => api.del(`/api/documents/${d.id}`), "Document supprimé");
        reload();
      })
    );
  },
};