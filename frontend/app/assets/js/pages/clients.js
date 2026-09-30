import * as ui from "../../../utils/ui.js";
const { esc, fmtDate, pageHead, table, formModal, toast } = ui;

const FIELDS = [
  { name: "name", label: "Nom", required: true, full: true },
  { name: "phone", label: "Téléphone", type: "tel" },
  { name: "email", label: "Email", type: "email" },
  { name: "address", label: "Adresse", full: true },
  { name: "notes", label: "Notes", type: "textarea", full: true },
];

export default {
  title: "Clients",
  roles: ["CEO", "DA"],
  events: ["request.created"],
  fetch: ({ api }) => api.get("/api/clients"),

  render(clients) {
    const head = pageHead(
      "Clients",
      `${clients.length} client${clients.length > 1 ? "s" : ""}`,
      `<button class="btn btn-primary" id="new">Nouveau client</button>`
    );

    if (!clients.length) {
      return head + ui.stateHTML.empty(
        "Aucun client",
        "Les clients sont créés automatiquement à la réception d'une demande."
      );
    }

    return head + table([
      { h: "Nom", cls: "main-cell", cell: (c) => esc(c.name) },
      { h: "Téléphone", cell: (c) => esc(c.phone || "—") },
      { h: "Email", cell: (c) => esc(c.email || "—") },
      { h: "Ajouté le", cell: (c) => fmtDate(c.created_at) },
      { h: "", cls: "r", cell: (c) => `<button class="btn btn-secondary btn-sm" data-edit="${c.id}">Modifier</button>` },
    ], clients);
  },

  bind(view, clients, { api, reload }) {
    const open = (client) => formModal({
      title: client ? "Modifier le client" : "Nouveau client",
      fields: FIELDS,
      values: client || {},
      onSubmit: async (v) => {
        if (client) await api.patch(`/api/clients/${client.id}`, v);
        else await api.post("/api/clients", v);
        toast(client ? "Client modifié" : "Client créé");
        reload();
      },
    });

    view.querySelector("#new")?.addEventListener("click", () => open());
    view.querySelectorAll("[data-edit]").forEach((b) =>
      b.addEventListener("click", () => open(clients.find((c) => c.id === +b.dataset.edit)))
    );
  },
};