/** Backend timestamps are UTC; SQLite may drop the offset, so add it when missing. */
export function parseDate(s) {
  if (!s) return null;
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? s : s + "Z");
}

export function formatDate(s, withTime = true) {
  const d = parseDate(s);
  if (!d || isNaN(d)) return "-";
  return d.toLocaleString(undefined, withTime
    ? { dateStyle: "medium", timeStyle: "short" }
    : { dateStyle: "medium" });
}

export function resultLabel(result, blasts) {
  if (result === "blast_detected") return `Blast cells detected (${blasts})`;
  if (result === "normal") return "Normal - no blast cells found";
  return "Unknown - image could not be analysed";
}

export const resultTone = (result) =>
  result === "blast_detected" ? "danger" : result === "normal" ? "ok" : "warn";

export const indicationLabel = (i) =>
  i === "acute" ? "Acute lymphoblastic leukemia indicated" : i === "chronic" ? "Chronic leukemia indicated" : "";

/** CSV download from an array of objects (client side). */
export function downloadCsv(filename, rows) {
  if (!rows.length) return;
  const cols = Object.keys(rows[0]);
  const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const csv = [cols.join(","), ...rows.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
