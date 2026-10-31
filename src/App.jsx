import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import { useAuth } from "./context/AuthContext.jsx";
import About from "./pages/About.jsx";
import Assistant from "./pages/Assistant.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Login from "./pages/Login.jsx";
import PatientRegister from "./pages/PatientRegister.jsx";
import ReportPage from "./pages/ReportPage.jsx";
import ReportsManager from "./pages/ReportsManager.jsx";
import Settings from "./pages/Settings.jsx";
import Verify from "./pages/Verify.jsx";
import Welcome from "./pages/Welcome.jsx";

function RequireAuth() {
  const { isAuthed } = useAuth();
  const loc = useLocation();
  return isAuthed ? <Outlet /> : <Navigate to="/login" replace state={{ from: loc.pathname }} />;
}

export default function App() {
  return (
    <Routes>
      {/* Public pages */}
      <Route path="/" element={<Welcome />} />
      <Route path="/about" element={<About />} />
      <Route path="/login" element={<Login />} />
      {/* Opened by scanning the QR code on a printed report */}
      <Route path="/verify/:token" element={<Verify />} />

      {/* Signed-in area */}
      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/patients" element={<PatientRegister />} />
          <Route path="/assistant" element={<Assistant />} />
          <Route path="/reports" element={<ReportsManager />} />
          <Route path="/reports/:id" element={<ReportPage />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
