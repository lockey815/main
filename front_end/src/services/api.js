import axios from "axios";

const root = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");
const TOKEN_KEY = "leuknet_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export const http = axios.create({
  baseURL: `${root}/api`,
  timeout: 180000, // free CPU hosting can be slow on the first request (cold start + inference)
});

http.interceptors.request.use((config) => {
  const t = tokenStore.get();
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

// An expired/invalid token anywhere (except the login call itself) logs the user out.
http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401 && !err.config?.url?.includes("/auth/login")) {
      tokenStore.clear();
      window.dispatchEvent(new Event("leuknet:logout"));
    }
    return Promise.reject(err);
  }
);

/** Turn any axios/FastAPI error into a readable string. */
export function errorMessage(err) {
  const d = err?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => `${(x.loc || []).slice(1).join(".")}: ${x.msg}`).join("; ");
  if (err?.code === "ECONNABORTED") return "The server took too long to respond. Please try again.";
  if (err?.message === "Network Error")
    return "Cannot reach the LeukNet server. Check that the backend is running and VITE_API_URL / CORS are correct.";
  return err?.message || "Something went wrong";
}

export const healthApi = { get: () => http.get("/health").then((r) => r.data) };

export const authApi = {
  login: (email, password) => http.post("/auth/login", { email, password }).then((r) => r.data),
};

export const patientsApi = {
  list: (q) => http.get("/patients", { params: q ? { q } : {} }).then((r) => r.data),
  create: (body) => http.post("/patients", body).then((r) => r.data),
  update: (id, body) => http.put(`/patients/${id}`, body).then((r) => r.data),
  remove: (id) => http.delete(`/patients/${id}`),
};

export const predictApi = {
  /** Analyse one or more files and add them to a server-side session (created on the first call). */
  run: (files, sessionId, onProgress) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    if (sessionId) form.append("session_id", sessionId);
    return http
      .post("/predict", form, {
        onUploadProgress: (e) => onProgress && e.total && onProgress(Math.round((e.loaded / e.total) * 100)),
      })
      .then((r) => r.data);
  },
};

export const sessionsApi = {
  summarize: (id) => http.post(`/sessions/${id}/summarize`).then((r) => r.data),
  discard: (id) => http.delete(`/sessions/${id}`),
};

export const reportsApi = {
  list: (patientId) => http.get("/reports", { params: patientId ? { patient_id: patientId } : {} }).then((r) => r.data),
  get: (id) => http.get(`/reports/${id}`).then((r) => r.data),
  create: (patientId, sessionId) => http.post("/reports", { patient_id: patientId, session_id: sessionId }).then((r) => r.data),
  remove: (id) => http.delete(`/reports/${id}`),
  /** Server-generated PDF, downloaded through the browser. */
  downloadPdf: async (id) => {
    const res = await http.get(`/reports/${id}/pdf`, { responseType: "blob" });
    const name = /filename="?([^"]+)"?/.exec(res.headers["content-disposition"] || "")?.[1] || "LeukNet_Report.pdf";
    const url = URL.createObjectURL(res.data);
    const a = Object.assign(document.createElement("a"), { href: url, download: name });
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  },
};

export const verifyApi = { check: (token) => http.get(`/verify/${encodeURIComponent(token)}`).then((r) => r.data) };

export const settingsApi = {
  get: () => http.get("/settings").then((r) => r.data),
  update: (body) => http.put("/settings", body).then((r) => r.data),
};
