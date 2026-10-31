import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Pager, TableControls, Th, useTable } from "../components/DataTable.jsx";
import Modal from "../components/Modal.jsx";
import { errorMessage, patientsApi } from "../services/api.js";

const EMPTY = { name: "", gender: "Female", age: "", contact: "", address: "" };
const KEYS = ["name", "gender", "age", "address", "contact"];

export default function PatientRegister() {
  const nav = useNavigate();
  const [patients, setPatients] = useState([]);
  const [form, setForm] = useState(null); // null = closed; otherwise the form values
  const [editingId, setEditingId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null); // page-level {type, text}
  const [formError, setFormError] = useState(null);
  const t = useTable(patients, { searchKeys: KEYS, initialSort: { key: "name", dir: "asc" } });

  const load = useCallback(async () => {
    try {
      setPatients(await patientsApi.list());
    } catch (e) {
      setMsg({ type: "error", text: errorMessage(e) });
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const openNew = () => { setEditingId(null); setForm(EMPTY); setFormError(null); };
  const openEdit = (p) => {
    setEditingId(p.id);
    setForm({ name: p.name, gender: p.gender, age: String(p.age), contact: p.contact, address: p.address });
    setFormError(null);
  };

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setFormError(null);
    try {
      const body = { ...form, age: Number(form.age) };
      if (editingId) await patientsApi.update(editingId, body);
      else await patientsApi.create(body);
      setForm(null);
      setMsg({ type: "success", text: editingId ? "Patient updated." : "Patient saved." });
      load();
    } catch (err) {
      setFormError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove(p) {
    if (!window.confirm(`Delete ${p.name}? Their reports will be deleted as well.`)) return;
    try {
      await patientsApi.remove(p.id);
      load();
    } catch (err) {
      setMsg({ type: "error", text: errorMessage(err) });
    }
  }

  return (
    <>
      <div className="row spread page-head">
        <div>
          <h1>Patient Register</h1>
          <p className="muted" style={{ margin: 0 }}>Capture and manage patient biodata, then analyse their blood smear in the LeukNet Assistant.</p>
        </div>
        <button className="btn primary" onClick={openNew}>＋ Add Patient</button>
      </div>

      {msg && <div className={`alert ${msg.type}`}>{msg.text}</div>}

      <div className="card">
        <TableControls t={t} placeholder="Search patients..." />
        {t.allTotal === 0 ? (
          <div className="empty">No patients yet. Click “Add Patient” to register the first one.</div>
        ) : (
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>#</th><Th t={t} k="name">Name</Th><Th t={t} k="gender">Gender</Th><Th t={t} k="age">Age</Th>
                    <Th t={t} k="address">Address</Th><Th t={t} k="contact">Contact</Th><th>Manage</th>
                  </tr>
                </thead>
                <tbody>
                  {t.pageRows.map((p, i) => (
                    <tr key={p.id}>
                      <td className="muted">{t.from + i}</td>
                      <td><strong>{p.name}</strong></td><td>{p.gender}</td><td>{p.age} yrs</td>
                      <td>{p.address || "-"}</td><td>{p.contact || "-"}</td>
                      <td>
                        <div className="row">
                          <button className="btn sm primary" onClick={() => nav(`/assistant?patient=${p.id}`)}>Analyse</button>
                          <button className="btn sm" onClick={() => openEdit(p)}>Edit</button>
                          <button className="btn sm danger" onClick={() => remove(p)}>Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {t.total === 0 && <tr><td colSpan={7} className="empty">No matching patients.</td></tr>}
                </tbody>
              </table>
            </div>
            <Pager t={t} />
          </>
        )}
      </div>

      {form && (
        <Modal title={editingId ? "Edit patient" : "Add patient"} onClose={() => setForm(null)}>
          <form onSubmit={submit}>
            {formError && <div className="alert error">{formError}</div>}
            <div className="form-grid">
              <div><label>Full name *</label><input required autoFocus value={form.name} onChange={set("name")} /></div>
              <div>
                <label>Gender *</label>
                <select value={form.gender} onChange={set("gender")}><option>Female</option><option>Male</option><option>Other</option></select>
              </div>
              <div><label>Age (years) *</label><input required type="number" min="0" max="130" value={form.age} onChange={set("age")} /></div>
              <div><label>Contact</label><input value={form.contact} onChange={set("contact")} placeholder="Phone number" /></div>
              <div style={{ gridColumn: "1 / -1" }}><label>Address</label><input value={form.address} onChange={set("address")} /></div>
            </div>
            <div className="row" style={{ marginTop: "1rem" }}>
              <button className="btn primary" disabled={busy}>{busy ? "Saving..." : "Save Details"}</button>
              <button type="button" className="btn" onClick={() => setForm(null)}>Cancel</button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
