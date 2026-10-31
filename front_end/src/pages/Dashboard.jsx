import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { patientsApi, reportsApi } from "../services/api.js";
import { useFacility } from "../context/SettingsContext.jsx";

const MODULES = [
  { to: "/patients", icon: "🧑‍⚕️", title: "Patient Register", text: "Save new patient biodata and manage existing records." },
  { to: "/assistant", icon: "🔬", title: "LeukNet Assistant", text: "Upload blood smear images and classify them with the LeukNet model." },
  { to: "/reports", icon: "📄", title: "Reports Manager", text: "View, print and verify saved diagnostic reports." },
  { to: "/settings", icon: "⚙️", title: "Settings", text: "Customise reports with your facility name, address and logo." },
];

export default function Dashboard() {
  const { settings } = useFacility();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    Promise.all([patientsApi.list(), reportsApi.list()])
      .then(([patients, reports]) =>
        setStats({
          patients: patients.length,
          reports: reports.length,
          flagged: reports.filter((r) => r.result === "blast_detected").length,
        })
      )
      .catch(() => setStats(null));
  }, []);

  return (
    <>
      <div className="page-head">
        <h1>Welcome to LeukNet</h1>
        <p className="muted">{settings.facility_name} - AI-assisted blood smear screening for acute lymphoblastic leukemia.</p>
      </div>

      <div className="grid cols-3" style={{ marginBottom: "1.2rem" }}>
        <div className="card stat"><span className="muted small">Registered patients</span><b>{stats?.patients ?? "-"}</b></div>
        <div className="card stat"><span className="muted small">Reports generated</span><b>{stats?.reports ?? "-"}</b></div>
        <div className="card stat"><span className="muted small">Reports with blasts flagged</span><b>{stats?.flagged ?? "-"}</b></div>
      </div>

      <div className="grid cols-4">
        {MODULES.map((m) => (
          <Link key={m.to} to={m.to} className="card module">
            <div className="icon">{m.icon}</div>
            <h3>{m.title}</h3>
            <p className="muted small" style={{ margin: 0 }}>{m.text}</p>
          </Link>
        ))}
      </div>

      <p className="muted small" style={{ marginTop: "1.5rem" }}>
        LeukNet is a screening aid. Every result must be reviewed by a qualified pathologist or hematologist.
      </p>
    </>
  );
}
