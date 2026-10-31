import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function Welcome() {
  const { isAuthed } = useAuth();
  const nav = useNavigate();
  return (
    <div className="hero">
      <div>
        <div style={{ fontSize: "3.4rem" }}>🩸</div>
        <h1>LeukNet <span style={{ color: "var(--ok)" }}>✔</span></h1>
        <p className="tag">A platform for AI-assisted blood smear analysis: register patients, screen smear images for blast cells, and issue verifiable reports.</p>
        <div className="row" style={{ justifyContent: "center" }}>
          <button className="btn primary" onClick={() => nav(isAuthed ? "/dashboard" : "/login")}>Get Started</button>
          <Link className="btn" to="/about">About</Link>
        </div>
        <p className="small muted" style={{ marginTop: "2rem" }}>LeukNet is a screening aid and does not replace a pathologist.</p>
      </div>
    </div>
  );
}
