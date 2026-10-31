import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Pager, TableControls, Th, useTable } from "../components/DataTable.jsx";
import Modal from "../components/Modal.jsx";
import ReportDocument, { printReport } from "../components/ReportDocument.jsx";
import ResultBadge from "../components/ResultBadge.jsx";
import { errorMessage, reportsApi } from "../services/api.js";
import { downloadCsv, formatDate, resultLabel } from "../utils.js";

const KEYS = ["patient_name", "result", "dateText"];

export default function ReportsManager() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quick, setQuick] = useState(null);
  const [opening, setOpening] = useState(null);
  const [pdfBusy, setPdfBusy] = useState(false);

  const rows = reports.map((r) => ({ ...r, dateText: formatDate(r.created_at) }));
  const t = useTable(rows, { searchKeys: KEYS, initialSort: { key: "created_at", dir: "desc" } });

  const load = useCallback(async () => {
    try {
      setReports(await reportsApi.list());
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function openQuick(id) {
    setOpening(id);
    try {
      setQuick(await reportsApi.get(id));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setOpening(null);
    }
  }

  async function pdf(id) {
    setPdfBusy(true);
    try {
      await reportsApi.downloadPdf(id);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setPdfBusy(false);
    }
  }

  async function remove(r) {
    if (!window.confirm(`Delete the report for ${r.patient_name}? This cannot be undone.`)) return;
    try {
      await reportsApi.remove(r.id);
      setReports((cur) => cur.filter((x) => x.id !== r.id));
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  const exportCsv = () =>
    downloadCsv("leuknet_reports.csv", t.pageRows.length === 0 ? [] : rows.map((r) => ({
      report_id: r.id, date: r.created_at, patient: r.patient_name, result: resultLabel(r.result, r.total_blasts),
      indication: r.indication, blast_regions: r.total_blasts, foreign_objects: r.foreign_objects, samples_analysed: r.images_analyzed,
    })));

  return (
    <>
      <div className="row spread page-head">
        <div>
          <h1>Reports Manager</h1>
          <p className="muted" style={{ margin: 0 }}>View, print and export saved diagnostic reports. New reports are created from the LeukNet Assistant.</p>
        </div>
        <button className="btn" onClick={exportCsv} disabled={reports.length === 0}>⬇ Export CSV</button>
      </div>
      {error && <div className="alert error">{error}</div>}

      <div className="card">
        <TableControls t={t} placeholder="Search reports..." />
        {loading ? (
          <div className="empty"><span className="spinner" /></div>
        ) : t.allTotal === 0 ? (
          <div className="empty">No reports yet. Analyse a sample in the <Link to="/assistant">LeukNet Assistant</Link> and save the results.</div>
        ) : (
          <>
            <div className="table-wrap">
              <table>
                <thead><tr><th>#</th><Th t={t} k="created_at">Date</Th><Th t={t} k="patient_name">Name</Th><Th t={t} k="result">Result</Th><th>Report</th><th>Manage</th></tr></thead>
                <tbody>
                  {t.pageRows.map((r, i) => (
                    <tr key={r.id}>
                      <td className="muted">{t.from + i}</td>
                      <td className="small">{r.dateText}</td>
                      <td><strong>{r.patient_name}</strong><div className="muted small" title={r.id}>{r.id.slice(0, 8)}…</div></td>
                      <td><ResultBadge result={r.result} blasts={r.total_blasts} /></td>
                      <td><button className="btn sm primary" disabled={opening === r.id} onClick={() => openQuick(r.id)}>{opening === r.id ? "Opening..." : "👁 Quick View"}</button></td>
                      <td><button className="btn sm danger" onClick={() => remove(r)}>🗑 Delete</button></td>
                    </tr>
                  ))}
                  {t.total === 0 && <tr><td colSpan={6} className="empty">No matching reports.</td></tr>}
                </tbody>
              </table>
            </div>
            <Pager t={t} />
          </>
        )}
      </div>

      {quick && (
        <Modal
          title={`Report - ${quick.patient.name}`}
          onClose={() => setQuick(null)}
          actions={
            <>
              <Link className="btn" to={`/reports/${quick.id}`}>Full page</Link>
              <button className="btn" disabled={pdfBusy} onClick={() => pdf(quick.id)}>{pdfBusy ? "Preparing..." : "⬇ PDF"}</button>
              <button className="btn primary" onClick={() => printReport(quick)}>🖨 Print / Preview</button>
            </>
          }
        >
          <ReportDocument report={quick} />
        </Modal>
      )}
    </>
  );
}
