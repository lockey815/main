import { useEffect, useMemo, useState } from "react";

/** Client-side search + sort + paging, mirroring the "entries per page / Search / Showing x to y" tables of LeukNet. */
export function useTable(rows, { searchKeys, initialSort }) {
  const [query, setQuery] = useState("");
  const [pageSize, setPageSize] = useState(10);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState(initialSort || { key: null, dir: "asc" });

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => searchKeys.some((k) => String(r[k] ?? "").toLowerCase().includes(q)));
  }, [rows, query, searchKeys]);

  const sorted = useMemo(() => {
    if (!sort.key) return filtered;
    const mul = sort.dir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const x = a[sort.key], y = b[sort.key];
      if (typeof x === "number" && typeof y === "number") return (x - y) * mul;
      return String(x ?? "").localeCompare(String(y ?? ""), undefined, { numeric: true, sensitivity: "base" }) * mul;
    });
  }, [filtered, sort]);

  const pages = Math.max(1, Math.ceil(sorted.length / pageSize));
  useEffect(() => { if (page > pages) setPage(pages); }, [page, pages]);
  useEffect(() => { setPage(1); }, [query, pageSize]);

  const start = (page - 1) * pageSize;
  return {
    pageRows: sorted.slice(start, start + pageSize),
    total: sorted.length, allTotal: rows.length, page, pages, setPage, pageSize, setPageSize,
    query, setQuery, sort,
    toggleSort: (key) => setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "asc" })),
    from: sorted.length ? start + 1 : 0,
    to: Math.min(start + pageSize, sorted.length),
  };
}

export function TableControls({ t, placeholder = "Search..." }) {
  return (
    <div className="row spread" style={{ marginBottom: ".8rem" }}>
      <label className="row small" style={{ margin: 0, fontWeight: 500 }}>
        <select style={{ width: "auto" }} value={t.pageSize} onChange={(e) => t.setPageSize(Number(e.target.value))}>
          {[10, 25, 50, 100].map((n) => <option key={n}>{n}</option>)}
        </select>
        entries per page
      </label>
      <input style={{ maxWidth: 260 }} placeholder={placeholder} value={t.query} onChange={(e) => t.setQuery(e.target.value)} />
    </div>
  );
}

/** Sortable header cell */
export function Th({ t, k, children }) {
  const active = t.sort.key === k;
  return (
    <th style={{ cursor: "pointer", userSelect: "none" }} onClick={() => t.toggleSort(k)} aria-sort={active ? (t.sort.dir === "asc" ? "ascending" : "descending") : "none"}>
      {children} <span style={{ opacity: active ? 1 : 0.3 }}>{active && t.sort.dir === "desc" ? "▼" : "▲"}</span>
    </th>
  );
}

export function Pager({ t }) {
  return (
    <div className="row spread small muted" style={{ marginTop: ".8rem" }}>
      <span>Showing {t.from} to {t.to} of {t.total} entries{t.total !== t.allTotal ? ` (filtered from ${t.allTotal})` : ""}</span>
      <div className="row">
        <button className="btn sm" disabled={t.page <= 1} onClick={() => t.setPage(t.page - 1)}>Previous</button>
        <span>Page {t.page} / {t.pages}</span>
        <button className="btn sm" disabled={t.page >= t.pages} onClick={() => t.setPage(t.page + 1)}>Next</button>
      </div>
    </div>
  );
}
