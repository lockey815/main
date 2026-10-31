import { useFacility } from "../context/SettingsContext.jsx";
import { formatDate, indicationLabel, resultTone } from "../utils.js";

/** The printable report (Quick View and /reports/:id). Layout follows the LeukNet report: facility header,
 *  patient block, SUMMARY table, results text, marked images, QR code. */
export default function ReportDocument({ report }) {
  const { settings: f } = useFacility();
  const p = report.patient;
  const tone = resultTone(report.result);
  const found =
    report.result === "blast_detected" ? `${report.total_blasts} blast cell region(s) found`
    : report.result === "normal" ? "No blast cells were found"
    : "Unknown - samples could not be analysed";

  return (
    <article className="report print-area">
      <header className="report-head">
        {f.logo_data_url && <img src={f.logo_data_url} alt="Facility logo" />}
        <div>
          <h2>{f.facility_name}</h2>
          <div className="small">{[f.address, f.contact, f.email].filter(Boolean).join("  |  ")}</div>
        </div>
      </header>

      <div className="report-title">LeukNet Blood Smear Screening Report</div>

      <div className="report-cols">
        <div><span>Patient name</span><strong>{p.name}</strong></div>
        <div><span>Patient address</span><strong>{p.address || "-"}</strong></div>
        <div><span>Patient contact</span><strong>{p.contact || "-"}</strong></div>
      </div>

      <h3>Summary</h3>
      <div className="kv">
        <div>Gender</div><div>{p.gender}</div>
        <div>Age</div><div>{p.age} years</div>
        <div>Test</div><div>{report.test_name}</div>
        <div>Samples analysed</div><div>{report.images_analyzed} of {report.sample_size}</div>
        <div>Total blast cells</div><div><span className={`dot ${tone === "danger" ? "bad" : tone === "ok" ? "ok" : ""}`} />{found}</div>
        <div>Foreign objects</div><div>{report.foreign_objects}</div>
        <div>Report date</div><div>{formatDate(report.created_at)}</div>
        <div>Report ID</div><div style={{ wordBreak: "break-all" }}>{report.id}</div>
      </div>

      <h3>Results report</h3>
      <div className={`report-result ${tone}`}>
        {report.result === "blast_detected" && indicationLabel(report.indication)
          ? indicationLabel(report.indication)
          : report.result === "normal" ? "Normal" : report.result === "unknown" ? "Unknown" : "Blast cells detected"}
      </div>
      <p style={{ marginTop: ".6rem" }}>{report.summary}</p>
      <p className="small muted">
        Counts are suspected blast regions flagged by the model per image tile, not a manual cell count. Foreign
        objects are a heuristic estimate of non-cellular material.
      </p>

      <h3>Analysed samples</h3>
      <div className="report-images">
        {report.findings.map((fd, i) => (
          <figure key={i}>
            {fd.annotated_image && <img src={fd.annotated_image} alt={fd.filename} />}
            <figcaption>
              {fd.filename} - {fd.status === "unknown" ? fd.note || "not analysable" : `${fd.blast_count} suspected blast region(s)`}
            </figcaption>
          </figure>
        ))}
      </div>

      <div className="report-foot">
        <img src={report.qr_code} alt="Verification QR code" />
        <div className="small">
          <strong>Verify this report</strong>
          <div>Scan the QR code or open:</div>
          <div style={{ wordBreak: "break-all" }}>{report.verify_url}</div>
        </div>
      </div>
      <p className="disclaimer">{f.report_footer}</p>
    </article>
  );
}

/** Opens the browser print dialog (also works as "Preview"). */
export function printReport(report) {
  const prev = document.title;
  const safe = report.patient.name.replace(/[^\w]+/g, "_");
  document.title = `LeukNet_Report_${safe}_${report.created_at.slice(0, 10)}`;
  const restore = () => {
    document.title = prev;
    window.removeEventListener("afterprint", restore);
  };
  window.addEventListener("afterprint", restore);
  window.print();
}
