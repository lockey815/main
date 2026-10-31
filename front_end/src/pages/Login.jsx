import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { errorMessage } from "../services/api.js";

export default function Login() {
  const { isAuthed, login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  if (isAuthed) return <Navigate to={loc.state?.from || "/dashboard"} replace />;

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      nav(loc.state?.from || "/dashboard", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="hero">
      <form className="card login-card" onSubmit={submit} style={{ textAlign: "left" }}>
        <div style={{ textAlign: "center", fontSize: "2.4rem" }}>🩸</div>
        <h1 style={{ textAlign: "center" }}>Sign in to LeukNet</h1>
        {error && <div className="alert error">{error}</div>}
        <div style={{ marginBottom: ".8rem" }}><label>Email</label><input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} /></div>
        <div style={{ marginBottom: "1rem" }}><label>Password</label><input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></div>
        <button className="btn primary" style={{ width: "100%", justifyContent: "center" }} disabled={busy}>{busy ? "Signing in..." : "Sign in"}</button>
        <p className="small" style={{ textAlign: "center", marginTop: "1rem" }}><Link to="/">← Back</Link> · <Link to="/about">About</Link></p>
      </form>
    </div>
  );
}
