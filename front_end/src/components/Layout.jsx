import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { useFacility } from "../context/SettingsContext.jsx";
import { healthApi } from "../services/api.js";

const NAV = [
  ["/dashboard", "🏠", "Dashboard"],
  ["/patients", "🧑‍⚕️", "Patient Register"],
  ["/assistant", "🔬", "LeukNet Assistant"],
  ["/reports", "📄", "Reports Manager"],
  ["/settings", "⚙️", "Settings"],
];

export default function Layout() {
  const { settings } = useFacility();
  const { email, logout } = useAuth();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const [health, setHealth] = useState(null);
  const loc = useLocation();

  useEffect(() => setOpen(false), [loc.pathname]);
  useEffect(() => {
    healthApi.get().then(setHealth).catch(() => setHealth({ model_loaded: false, error: "Server unreachable" }));
  }, []);

  return (
    <div className="shell">
      <aside className={`sidebar no-print ${open ? "open" : ""}`}>
        <div className="brand">
          {settings.logo_data_url ? <img src={settings.logo_data_url} alt="logo" /> : <div className="logo-fallback">🩸</div>}
          <div>
            <strong>LeukNet</strong>
            <span>{settings.facility_name}</span>
          </div>
        </div>
        <nav className="nav">
          {NAV.map(([to, icon, label]) => (
            <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "active" : "")}>
              <span>{icon}</span> {label}
            </NavLink>
          ))}
        </nav>
        <div className="status-pill" title={health?.error || ""}>
          <span className={`dot ${health ? (health.model_loaded ? "ok" : "bad") : ""}`} />
          {health ? (health.model_loaded ? "Model ready" : "Model not loaded") : "Connecting..."}
        </div>
        <div className="status-pill" style={{ marginTop: 0 }}>
          <div style={{ overflow: "hidden", textOverflow: "ellipsis" }} title={email}>{email}</div>
          <button className="btn sm" style={{ marginTop: ".5rem", width: "100%", justifyContent: "center" }}
            onClick={() => { logout(); nav("/"); }}>Sign out</button>
        </div>
      </aside>
      <main className="main">
        <button className="btn menu-btn no-print" onClick={() => setOpen((o) => !o)}>☰ Menu</button>
        <Outlet context={{ health }} />
      </main>
    </div>
  );
}
