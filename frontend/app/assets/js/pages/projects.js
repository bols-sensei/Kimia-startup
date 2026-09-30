import * as ui from "../../../utils/ui.js";
const { esc, badge, fmtDate, label, pageHead, table, formModal, act, toast, byId } = ui;

const STATUSES = ["A_PREPARER", "EN_PREPARATION", "EN_COURS", "LIVRAISON", "TERMINE", "ANNULE"];
const CATEGORIES = ["PHOTOGRAPHIE", "VIDEO", "GRAPHISME", "DEVELOPPEMENT_WEB", "COMMUNICATION", "AUTRE"];
const TYPES = ["CLIENT", "INTERNE"];

const FIELDS = [
  { name: "name", label: "Nom du projet", required: true, full: true },
  { name: "description", label: "Description", type: "textarea", full: true },
  {
    name: "project_type",
    label: "Type",
    type: "select",
    required: true,
    options: TYPES.map((v) => ({ v, l: label(v) })),
  },
  {
    name: "category",
    label: "Catégorie",
    type: "select",
    required: true,
    options: CATEGORIES.map((v) => ({ v, l: label(v) })),
  },
  { name: "start_date", label: "Début prévu", type: "date" },
  { name: "planned_end_date", label: "Fin prévue", type: "date" },
];

export default {
  title: "Projets",
  roles: null,
  events: ["project.created", "project.updated"],
  fetch: ({ api }) => api.get("/api/projects"),

  render(projects) {
    const head = pageHead(
      "Projets",
      `${projects.length} projet${projects.length > 1 ? "s" : ""}`,
      `<button class="btn btn-primary" id="new">Nouveau projet</button>`
    );

    if (!projects.length) {
      return head + ui.stateHTML.empty("Aucun projet", "Créez un projet pour démarrer.");
    }

    return head + table(
      [
        { h: "Nom", cls: "main-cell", cell: (p) => esc(p.name) },
        { h: "Type", cell: (p) => `<span class="tag">${esc(label(p.project_type))}</span>` },
        { h: "Catégorie", cell: (p) => esc(label(p.category)) },
        { h: "Statut", cell: (p) => badge(p.status) },
        { h: "Fin prévue", cell: (p) => fmtDate(p.planned_end_date) },
        {
          h: "",
          cls: "r",
          cell: (p) => `<button class="btn btn-secondary btn-sm" data-edit="${p.id}">Modifier</button>`,
        },
      ],
      projects
    );
  },

  bind(view, projects, { api, reload }) {
    const open = (project) => {
      if (!project) {
        // Création simple
        formModal({
          title: "Nouveau projet",
          fields: FIELDS,
          submitLabel: "Créer",
          onSubmit: async (v) => {
            await api.post("/api/projects", { ...v, services: [] });
            toast("Projet créé");
            reload();
          },
        });
        return;
      }

      // Modification : nom, description, statut
      formModal({
        title: `Modifier « ${project.name} »`,
        fields: [
          { name: "name", label: "Nom du projet", required: true, full: true },
          { name: "description", label: "Description", type: "textarea", full: true },
          {
            name: "status",
            label: "Statut",
            type: "select",
            options: STATUSES.map((v) => ({ v, l: label(v) })),
          },
          { name: "planned_end_date", label: "Fin prévue", type: "date" },
          { name: "actual_end_date", label: "Fin réelle", type: "date" },
        ],
        values: {
          ...project,
          planned_end_date: project.planned_end_date || "",
          actual_end_date: project.actual_end_date || "",
        },
        onSubmit: async (v) => {
          await api.patch(`/api/projects/${project.id}`, v);
          toast("Projet modifié");
          reload();
        },
      });
    };

    view.querySelector("#new")?.addEventListener("click", () => open());
    view.querySelectorAll("[data-edit]").forEach((b) =>
      b.addEventListener("click", () => open(projects.find((p) => p.id === +b.dataset.edit)))
    );
  },
};