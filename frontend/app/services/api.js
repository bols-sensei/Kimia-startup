/* Client API centralisé — jeton Bearer, redirection sur 401 */

const TOKEN_KEY = "kimia_token";
const USER_KEY = "kimia_user";

export const session = {
  get token() { return localStorage.getItem(TOKEN_KEY); },
  get user() {
    try { return JSON.parse(localStorage.getItem(USER_KEY)); }
    catch { return null; }
  },
  save(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  saveUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
};

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

const base = () => window.KIMIA_API || "";

function detailText(d) {
  if (!d) return "";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d.map((x) => (x.loc ? x.loc.slice(1).join(".") + " : " : "") + (x.msg || "")).join(" ; ");
  }
  return JSON.stringify(d);
}

function qs(params) {
  const p = new URLSearchParams();
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") p.set(k, v);
  });
  const s = p.toString();
  return s ? "?" + s : "";
}

async function request(path, { method = "GET", body, form, raw } = {}) {
  const headers = {};
  if (session.token) headers.Authorization = "Bearer " + session.token;

  let payload;
  if (form) payload = form;
  else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(base() + path, { method, headers, body: payload });
  } catch {
    throw new ApiError("Serveur injoignable. Vérifiez votre connexion.", 0);
  }

  if (res.status === 401 && !path.startsWith("/api/auth/login")) {
    session.clear();
    location.replace("login.html");
    throw new ApiError("Session expirée", 401);
  }

  if (!res.ok) {
    let d;
    try { d = (await res.json()).detail; } catch {}
    throw new ApiError(detailText(d) || `Erreur ${res.status}`, res.status);
  }

  if (raw) return res;
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get: (path, params) => request(path + qs(params)),
  post: (path, body, params) => request(path + qs(params), { method: "POST", body }),
  patch: (path, body, params) => request(path + qs(params), { method: "PATCH", body }),
  put: (path, body) => request(path, { method: "PUT", body }),
  del: (path) => request(path, { method: "DELETE" }),
  upload: (path, params, file) => {
    const form = new FormData();
    form.append("file", file);
    return request(path + qs(params), { method: "POST", form });
  },
  async download(path, filename) {
    const res = await request(path, { raw: true });
    const url = URL.createObjectURL(await res.blob());
    const a = Object.assign(document.createElement("a"), { href: url, download: filename });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  },
  login: (email, password) => request("/api/auth/login", {
    method: "POST",
    body: { email, password },
  }),
};