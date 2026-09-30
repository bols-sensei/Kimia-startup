/* Client API public — aucune authentification */

const base = () => window.KIMIA_API || "";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function detailText(d) {
  if (!d) return "";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d.map(x => (x.loc ? x.loc.slice(1).join(".") + " : " : "") + (x.msg || "")).join(" ; ");
  }
  return JSON.stringify(d);
}

async function request(path, { method = "GET", body } = {}) {
  const headers = {};
  let payload;

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(base() + path, { method, headers, body: payload });
  } catch {
    throw new ApiError("Serveur injoignable. Vérifiez votre connexion.", 0);
  }

  if (!res.ok) {
    let d;
    try { d = (await res.json()).detail; } catch {}
    throw new ApiError(detailText(d) || `Erreur ${res.status}`, res.status);
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  getCategories: () => request("/api/public/categories"),
  getEventTypes: () => request("/api/public/event-types"),
  getServices: (categoryId) => request(
    "/api/public/services" + (categoryId ? `?category_id=${categoryId}` : "")
  ),
  getPortfolio: () => request("/api/public/portfolio"),
  submitRequest: (payload) => request("/api/public/requests", {
    method: "POST",
    body: payload,
  }),
};