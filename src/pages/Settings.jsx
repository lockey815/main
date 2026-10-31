import { useEffect, useState } from "react";
import { useFacility } from "../context/SettingsContext.jsx";
import { errorMessage, settingsApi } from "../services/api.js";

/** Shrink the chosen logo in the browser so it stays small (<~150 KB). */
function fileToLogo(file, max = 300) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      const scale = Math.min(1, max / Math.max(img.width, img.height));
      const c = document.createElement("canvas");
      c.width = Math.round(img.width * scale);
      c.height = Math.round(img.height * scale);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      URL.revokeObjectURL(url);
      resolve(c.toDataURL("image/png"));
    };
    img.onerror = () => reject(new Error("Could not read that image."));
    img.src = url;
  });
}

export default function Settings() {
  const { settings, setSettings, loaded } = useFacility();
  const [form, setForm] = useState(settings);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (loaded) setForm(settings); }, [loaded, settings]);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function pickLogo(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const data = await fileToLogo(file);
      setForm((f) => ({ ...f, logo_data_url: data }));
    } catch (err) {
      setMsg({ type: "error", text: err.message });
    }
  }

  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      const saved = await settingsApi.update(form);
      setSettings(saved);
      setMsg({ type: "success", text: "Settings saved. New reports will use these details." });
    } catch (err) {
      setMsg({ type: "error", text: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <h1>Settings</h1>
        <p className="muted">These details appear in the sidebar and on every printed report.</p>
      </div>
      {msg && <div className={`alert ${msg.type}`}>{msg.text}</div>}
      <form className="card" onSubmit={save}>
        <div className="form-grid">
          <div><label>Facility / hospital name</label><input required value={form.facility_name} onChange={set("facility_name")} /></div>
          <div><label>Admin contact (phone)</label><input value={form.contact} onChange={set("contact")} /></div>
          <div><label>Email</label><input type="email" value={form.email} onChange={set("email")} /></div>
          <div style={{ gridColumn: "1 / -1" }}><label>Address</label><input value={form.address} onChange={set("address")} /></div>
          <div style={{ gridColumn: "1 / -1" }}>
            <label>Report footer / disclaimer</label>
            <textarea rows={2} value={form.report_footer} onChange={set("report_footer")} />
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <label>Logo</label>
            <div className="row">
              {form.logo_data_url ? <img src={form.logo_data_url} alt="logo preview" style={{ height: 64, border: "1px solid var(--line)", borderRadius: 8, padding: 4 }} /> : <span className="muted small">No logo yet</span>}
              <input type="file" accept="image/*" onChange={pickLogo} style={{ maxWidth: 300 }} />
              {form.logo_data_url && <button type="button" className="btn sm" onClick={() => setForm((f) => ({ ...f, logo_data_url: "" }))}>Remove</button>}
            </div>
          </div>
        </div>
        <div style={{ marginTop: "1rem" }}>
          <button className="btn primary" disabled={busy}>{busy ? "Saving..." : "Save Changes"}</button>
        </div>
      </form>
    </>
  );
}
