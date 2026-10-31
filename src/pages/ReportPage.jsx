import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ReportDocument, { printReport } from "../components/ReportDocument.jsx";
import { errorMessage, reportsApi } from "../services/api.js";

export default function ReportPage() {
  const { id } = useParams();
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    reportsApi.get(id).then(setReport).catch((e) => setError(errorMessage(e)));
  }, [id]);

  async function pdf() {
    setBusy(true);
    try { await reportsApi.downloadPdf(id); } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }

  return (
    <>
      <div className="row spread no-print page-head">
        <h1>Diagnostic report</h1>
        <div className="row">
          <Link className="btn" to="/reports">← All reports</Link>
          {report && <button className="btn" disabled={busy} onClick={pdf}>{busy ? "Preparing..." : "⬇ PDF"}</button>}
          {report && <button className="btn primary" onClick={() => printReport(report)}>🖨 Print / Preview</button>}
        </div>
      </div>
      {error && <div className="alert error">{error}</div>}
      {!report && !error && <div className="empty"><span className="spinner" /></div>}
      {report && <div className="card" style={{ padding: 0 }}><ReportDocument report={report} /></div>}
    </>
  );
}
