
import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { errorMessage } from "../services/api.js";

export default function Register() {
  const { isAuthed, register } = useAuth();
  const nav = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  if (isAuthed) return <Navigate to="/dashboard" replace />;

  async function submit(e) {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Password must contain at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setBusy(true);

    try {
      await register(email.trim().toLowerCase(), password);
      nav("/dashboard", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="hero">
      <form
        className="card login-card"
        onSubmit={submit}
        style={{ textAlign: "left" }}
      >
        <div style={{ textAlign: "center", fontSize: "2.4rem" }}>🩸</div>

        <h1 style={{ textAlign: "center" }}>Create LeukNet Account</h1>

        {error && <div className="alert error">{error}</div>}

        <div style={{ marginBottom: ".8rem" }}>
          <label>Email</label>
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <div style={{ marginBottom: ".8rem" }}>
          <label>Password</label>
          <input
            type="password"
            autoComplete="new-password"
            minLength={8}
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        <div style={{ marginBottom: "1rem" }}>
          <label>Confirm Password</label>
          <input
            type="password"
            autoComplete="new-password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
        </div>

        <button
          className="btn primary"
          style={{ width: "100%", justifyContent: "center" }}
          disabled={busy}
        >
          {busy ? "Creating account..." : "Create account"}
        </button>

        <p className="small" style={{ textAlign: "center", marginTop: "1rem" }}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
