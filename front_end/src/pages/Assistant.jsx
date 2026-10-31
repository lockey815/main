import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useOutletContext, useSearchParams } from "react-router-dom";
import { errorMessage, patientsApi, predictApi, reportsApi, sessionsApi } from "../services/api.js";
import { resultTone } from "../utils.js";

const MAX_FILES = 8;
const ACCEPT = ["image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff", "application/pdf"];

function FindingBadge({ f }) {
  if (f.status === "unknown") return <span className="badge warn">Unknown</span>;
  if (f.status === "normal") return <span className="badge ok">Normal</span>;
  return <span className="badge danger">{f.blast_count} Blast {f.blast_count === 1 ? "Cell" : "Cells"}</span>;
}

export default function Assistant() {
  const { health } = useOutletContext() || {};
  const [params] = useSearchParams();
  const [tab, setTab] = useState("upload"); // upload | tools
  const [patients, setPatients] = useState([]);
  const [patientId, setPatientId] = useState(params.get("patient") || "");
  const [files, setFiles] = useState([]);
  const [drag, setDrag] = useState(false);
  const [items, setItems] = useState([]); // per-file processing state
  const [running, setRunning] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [agg, setAgg] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(null);
  const [error, setError] = useState(null);
  const input = useRef(null);

  useEffect(() => {
    patientsApi.list().then(setPatients).catch((e) => setError(errorMessage(e)));
  }, []);

  const previews = useMemo(
    () => files.map((f) => ({ f, url: f.type.startsWith("image/") ? URL.createObjectURL(f) : null })),
    [files]
  );
  useEffect(() => () => previews.forEach((p) => p.url && URL.revokeObjectURL(p.url)), [previews]);

  const patient = patients.find((p) => p.id === patientId);
  const modelDown = health && !health.model_loaded;

  function addFiles(list) {
    setError(null);
    const incoming = Array.from(list);
    const valid = incoming.filter((f) => ACCEPT.includes(f.type));
    let msg = valid.length < incoming.length ? "Some files were skipped - only JPEG, PNG, WEBP, BMP, TIFF or PDF are supported." : null;
    setFiles((cur) => {
      const merged = [...cur, ...valid];
      if (merged.length > MAX_FILES) msg = `A maximum of ${MAX_FILES} files can be analysed in one session.`;
      return merged.slice(0, MAX_FILES);
    });
    if (msg) setError(msg);
  }

  const patchItem = (i, patch) => setItems((cur) => cur.map((it, j) => (j === i ? { ...it, ...patch } : it)));

  async function process() {
    setError(null);
    setSaved(null);
    setAgg(null);
    setSessionId(null);
    const queue = files.map((f) => ({ name: f.name, state: "pending", findings: [], error: null }));
    setItems(queue);
    setTab("tools");
    setRunning(true);

    let sid = null;
    for (let i = 0; i < files.length; i++) {
      patchItem(i, { state: "processing" });
      try {
        const res = await predictApi.run([files[i]], sid); // one sample at a time -> "Processed k / N"
        sid = res.session_id;
        patchItem(i, { state: "done", findings: res.findings });
      } catch (e) {
        patchItem(i, { state: "error", error: errorMessage(e) });
        if (!e?.response || e.response.status === 503) {
          setError(errorMessage(e));
          break; // server unreachable / model not loaded: stop instead of failing every file
        }
      }
    }
    setSessionId(sid);
    if (sid) {
      try {
        setAgg(await sessionsApi.summarize(sid));
      } catch (e) {
        setError(errorMessage(e));
      }
    }
    setRunning(false);
  }

  async function newSession() {
    if (sessionId) sessionsApi.discard(sessionId).catch(() => {});
    setFiles([]); setItems([]); setAgg(null); setSessionId(null); setSaved(null); setError(null); setTab("upload");
  }

  async function saveResults() {
    setSaving(true);
    setError(null);
    try {
      setSaved(await reportsApi.create(patientId, sessionId));
      setSessionId(null);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  const done = items.filter((it) => it.state === "done" || it.state === "error").length;

  return (
    <>
      <div className="page-head">
        <h1>LeukNet Assistant</h1>
        <p className="muted">Select a patient, drop their blood smear images, then review the results before saving.</p>
      </div>

      {modelDown && <div className="alert error">The model is not loaded on the server: {health.error}</div>}
      {error && <div className="alert error">{error}</div>}

      <div className="tabs">
        <button className={`tab ${tab === "upload" ? "active" : ""}`} onClick={() => setTab("upload")}>File uploader</button>
        <button className={`tab ${tab === "tools" ? "active" : ""}`} onClick={() => setTab("tools")} disabled={items.length === 0}>LeukNet Tools</button>
      </div>

      {tab === "upload" && (
        <div className="card">
          <label>Choose patient *</label>
          <select value={patientId} onChange={(e) => setPatientId(e.target.value)}>
            <option value="">- Select a registered patient -</option>
            {patients.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.gender}, {p.age})</option>)}
          </select>
          {patients.length === 0 && <p className="small muted" style={{ marginTop: ".5rem" }}>No patients yet - <Link to="/patients">register one first</Link>.</p>}
          {!patientId && patients.length > 0 && <p className="small muted" style={{ marginTop: ".5rem" }}>A patient profile must be selected before you can analyse images.</p>}

          <div
            className={`dropzone ${drag ? "drag" : ""}`}
            style={{ marginTop: "1rem" }}
            onClick={() => input.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); addFiles(e.dataTransfer.files); }}
            role="button" tabIndex={0}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
          >
            <div className="big">🩸</div>
            <strong>Click or drag &amp; drop blood smear images here</strong>
            <div className="muted small">JPEG, PNG, WEBP, BMP, TIFF or PDF - up to {MAX_FILES} files</div>
            <input ref={input} type="file" multiple accept={ACCEPT.join(",")} hidden onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }} />
          </div>

          {previews.length > 0 && (
            <div className="thumbs">
              {previews.map(({ f, url }, i) => (
                <div className="thumb" key={`${f.name}-${i}`}>
                  {url ? <img src={url} alt={f.name} /> : <div style={{ height: 96, display: "grid", placeItems: "center", fontSize: "2rem" }}>📄</div>}
                  <div className="name" title={f.name}>{f.name}</div>
                  <button aria-label={`Remove ${f.name}`} onClick={() => setFiles((c) => c.filter((_, j) => j !== i))}>×</button>
                </div>
              ))}
            </div>
          )}

          <div className="row" style={{ marginTop: "1rem" }}>
            <button className="btn primary" disabled={running || !patientId || files.length === 0 || modelDown} onClick={process}>
              Process {files.length || ""} {files.length === 1 ? "sample" : "samples"}
            </button>
            {files.length > 0 && <button className="btn" onClick={() => setFiles([])}>Clear</button>}
          </div>
        </div>
      )}

      {tab === "tools" && (
        <>
          <div className="card" style={{ marginBottom: "1rem" }}>
            <div className="row spread">
              <div><strong>{patient?.name || "Patient"}</strong> <span className="muted small">{patient ? `${patient.gender}, ${patient.age} yrs` : ""}</span></div>
              {running
                ? <span><span className="spinner" /> Processed {done} / {items.length} samples...</span>
                : <span className="muted small">Processed {done} / {items.length} samples</span>}
            </div>
            {running && <div className="progress" style={{ marginTop: ".6rem" }}><div style={{ width: `${(done / items.length) * 100}%` }} /></div>}
            {running && <p className="small muted" style={{ margin: ".5rem 0 0" }}>The first run on free hosting can take a minute while the server wakes up.</p>}
          </div>

          <div className="grid cols-2">
            {items.map((it, i) =>
              it.state === "done" ? (
                it.findings.map((f, k) => (
                  <div className="card finding" key={`${i}-${k}`}>
                    <div className="row spread" style={{ marginBottom: ".5rem" }}>
                      <strong style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{f.filename}</strong>
                      <FindingBadge f={f} />
                    </div>
                    <div className="compare">
                      <figure><img src={f.original_image || f.annotated_image} alt="Original" /><figcaption>Original</figcaption></figure>
                      <figure><img src={f.annotated_image} alt="Analysed" /><figcaption>Analysed{f.blast_count ? " (blast regions marked in red)" : ""}</figcaption></figure>
                    </div>
                    <p className="small muted" style={{ margin: ".5rem 0 0" }}>
                      {f.status === "unknown" ? f.note
                        : `${f.tiles_analyzed} tile(s) analysed - peak blast probability ${(f.max_blast_probability * 100).toFixed(1)}%`}
                      {f.foreign_objects > 0 && ` - ${f.foreign_objects} foreign object region(s) (amber)`}
                    </p>
                  </div>
                ))
              ) : (
                <div className="card" key={i}>
                  <strong>{it.name}</strong>
                  <div style={{ padding: "1.4rem 0", textAlign: "center" }} className="muted">
                    {it.state === "processing" && <><span className="spinner" /><div className="small">Analysing...</div></>}
                    {it.state === "pending" && <div className="small">Waiting...</div>}
                    {it.state === "error" && <div className="alert error" style={{ margin: 0, textAlign: "left" }}>{it.error}</div>}
                  </div>
                </div>
              )
            )}
          </div>

          {agg && (
            <div className="card" style={{ marginTop: "1rem" }}>
              <h2>Results:</h2>
              <div className="results-table">
                <div><strong>Uploaded Sample Size</strong><span>{agg.sample_size}</span></div>
                <div><strong>Total Blast Cells</strong><span>{agg.total_blasts}</span></div>
                <div><strong>Foreign Objects</strong><span>{agg.foreign_objects}</span></div>
              </div>
              <div className={`results-report ${resultTone(agg.result)}`}>
                <strong>Results Report</strong>
                <div>{agg.summary}</div>
                <div className="small muted" style={{ marginTop: ".4rem" }}>
                  {agg.summary_source === "mistral" ? "Summary written by Mistral AI from the numbers above." : "Automated summary."}
                  {" "}Counts are suspected blast regions, not an exact cell count.
                </div>
              </div>

              {saved ? (
                <div className="alert success" style={{ marginBottom: 0 }}>
                  <div className="row spread">
                    <span>Results saved. Report <code>{saved.id.slice(0, 8)}</code> was created for {saved.patient.name}.</span>
                    <span className="row"><Link className="btn sm primary" to={`/reports/${saved.id}`}>Open report</Link>
                      <button className="btn sm" onClick={newSession}>New Session</button></span>
                  </div>
                </div>
              ) : (
                <div className="row spread">
                  <button className="btn" onClick={newSession} disabled={running}>↻ New Session</button>
                  <button className="btn primary" onClick={saveResults} disabled={running || saving || !sessionId || !patientId}>
                    {saving ? "Saving..." : "💾 Save Results"}
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </>
  );
}
