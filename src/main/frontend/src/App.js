import React, { useEffect, useMemo, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import { AlertTriangle, ArrowDownAZ, ArrowUpDown, Car, Crosshair, GraduationCap, Home, ShieldCheck, X } from "https://esm.sh/lucide-react@0.468.0?deps=react@18.3.1";

const h = React.createElement;

const SORTS = [
  ["school_proximity", "Proximity to school"],
  ["safety", "Safety"],
  ["price_asc", "Low to high price"],
  ["price_desc", "High to low price"],
  ["fee_asc", "Low to high condo fee"],
  ["fee_desc", "High to low condo fee"],
];

const PAGE_SIZES = [10, 25, 50, 100, "all"];
const DEFAULT_FILTERS = {
  allGreen: false,
  safety: "all",
  schoolDistance: "all",
  basement: "all",
  parking: "all",
  condoFee: "all",
  recommendation: "all",
  verification: "all",
  schoolBoard: "ocdsb,ocsb",
  community: "",
  maxPrice: "",
};

function money(value) {
  if (value === null || value === undefined) return "-";
  return Number(value).toLocaleString("en-CA", {
    style: "currency",
    currency: "CAD",
    maximumFractionDigits: 0,
  });
}

function badgeClass(value) {
  return String(value || "unknown").toLowerCase().replaceAll(" ", "-");
}

function feeTier(value, settings) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "unknown";
  if (amount <= Number(settings.green_max_fee)) return "low";
  if (amount <= Number(settings.amber_max_fee)) return "mid";
  return "high";
}

function feeClass(value, settings) {
  const tier = feeTier(value, settings);
  if (tier === "low") return "fee-low";
  if (tier === "mid") return "fee-mid";
  if (tier === "high") return "fee-high";
  return "fee-unknown";
}

function basementClass(value) {
  const text = String(value || "").toLowerCase();
  if (text.includes("finished") && !text.includes("unfinished") && !text.includes("part")) return "score-good";
  if (text.includes("semi") || text.includes("part")) return "score-mid";
  return "score-bad";
}

function parkingClass(value) {
  const text = String(value || "").toLowerCase();
  if (text.includes("no garage") || text.includes("no parking") || text.includes("none") || text.includes("pending")) return "score-bad";
  if (
    text.includes("garage")
    || text.includes("underground")
    || text.includes("covered")
    || text.includes("carport")
    || text.includes("indoor")
    || text.includes("inside")
    || text.includes("enclosed")
    || text.includes("inside entry")
    || text.includes("attached")
    || text.includes("detached")
  ) return "score-good";
  return "score-mid";
}

function recommendationClass(value) {
  const text = String(value || "").toLowerCase();
  if (text.includes("shortlist") || text.includes("recommend") || text.includes("good")) return "score-good";
  if (text.includes("maybe") || text.includes("consider")) return "score-mid";
  return "score-bad";
}

function scoreTier(className) {
  if (className === "score-good") return "good";
  if (className === "score-mid") return "mid";
  return "bad";
}

function formatKm(value) {
  return `${Number(value).toFixed(1)} km`;
}

function formatFee(value) {
  return `$${Math.round(Number(value))}`;
}

function TwoHandleSlider({ min, max, step, lower, upper, onLower, onUpper, format }) {
  const lowerNum = Number(lower);
  const upperNum = Number(upper);
  const stepNum = Number(step);
  const lowerPct = ((lowerNum - min) / (max - min)) * 100;
  const upperPct = ((upperNum - min) / (max - min)) * 100;
  return h(
    "div",
    { className: "dual-slider", style: { "--low": `${lowerPct}%`, "--high": `${upperPct}%` } },
    h(
      "div",
      { className: "slider-values" },
      h("span", { style: { left: `${lowerPct}%` } }, format(lowerNum)),
      h("span", { style: { left: `${upperPct}%` } }, format(upperNum)),
    ),
    h("div", { className: "slider-rail" }),
    h("input", {
      className: "slider-range",
      type: "range",
      min,
      max,
      step,
      value: lowerNum,
      onChange: (event) => onLower(String(Math.min(Number(event.target.value), upperNum - stepNum))),
    }),
    h("input", {
      className: "slider-range",
      type: "range",
      min,
      max,
      step,
      value: upperNum,
      onChange: (event) => onUpper(String(Math.max(Number(event.target.value), lowerNum + stepNum))),
    }),
  );
}

function IconLabel({ icon, text }) {
  return h("span", { className: "label" }, icon, text);
}

function schoolDisplayFor(listing, schoolBoardFilter) {
  const rows = listing.schools || [];
  const selectedBoard = schoolBoardFilter === "ocdsb" || schoolBoardFilter === "ocsb"
    ? schoolBoardFilter.toUpperCase()
    : null;
  const selectedRow = selectedBoard
    ? rows.find((school) => String(school.board || "").toUpperCase() === selectedBoard)
    : null;

  if (!selectedRow) {
    return {
      school: listing.school || "Manual enrichment needed",
      distance: listing.school_distance_km,
      distanceCategory: listing.school_distance_category,
      confidence: listing.confidence,
    };
  }

  return {
    school: `${selectedRow.board}: ${selectedRow.school || "Manual verification needed"}`,
    distance: selectedRow.distance_km,
    distanceCategory: selectedRow.distance_category,
    confidence: selectedRow.confidence || listing.confidence,
  };
}

function ListingCard({ listing, onDelete, feeSettings, schoolBoardFilter }) {
  const schoolDisplay = schoolDisplayFor(listing, schoolBoardFilter);
  const manual = (schoolDisplay.confidence || "").toLowerCase().includes("manual");
  return h(
    "article",
    { className: "listing-card" },
    h(
      "div",
      { className: "card-header" },
      h("a", { href: listing.url, target: "_blank", rel: "noreferrer" }, listing.address || "Unknown address"),
      h("span", null, money(listing.price)),
      h("button", { type: "button", className: "delete-card", title: "Delete entry", "aria-label": "Delete entry", onClick: () => onDelete(listing.url) }, h(X, { size: 16 })),
    ),
    h(
      "div",
      { className: "meta" },
      h("span", null, listing.community || "Community pending"),
      h("span", null, listing.property_type || "Type pending"),
      h("span", null, `${listing.beds ?? "-"} bd`),
      h("span", null, `${listing.baths ?? "-"} ba`),
    ),
    h(
      "div",
      { className: "facts" },
      h("div", null, h(IconLabel, { icon: h(GraduationCap, { size: 14 }), text: "School" }), h("strong", null, schoolDisplay.school)),
      h("div", null, h(IconLabel, { icon: h(ArrowUpDown, { size: 14 }), text: "Distance" }), h("strong", null, schoolDisplay.distance === null || schoolDisplay.distance === undefined ? "-" : `${schoolDisplay.distance} km`)),
      h("div", null, h("span", { className: `badge ${badgeClass(schoolDisplay.distanceCategory)}` }, `School proximity: ${schoolDisplay.distanceCategory || "Unclassified"}`)),
      h("div", null, h("span", { className: `badge ${badgeClass(listing.safety_category)}` }, `Safety ranking: ${listing.safety_category || "Safety pending"}`)),
    ),
    h(
      "div",
      { className: "footer-row" },
      h("span", { className: `score-pill ${parkingClass(listing.parking_type)}` }, h(Car, { size: 14 }), `Garage: ${listing.parking_type || "Parking pending"}`),
      h("span", { className: `score-pill ${basementClass(listing.basement)}` }, `Basement: ${listing.basement || "No information"}`),
      h("span", { className: `fee-pill ${feeClass(listing.maintenance_fee, feeSettings)}` }, `Condo fee: ${listing.maintenance_fee ? `${money(listing.maintenance_fee)}/mo` : "No fee info"}`),
      h("span", { className: `score-pill ${recommendationClass(listing.overall_verdict)}` }, `Recommendation: ${listing.overall_verdict || "Recommendation pending"}`),
    ),
    listing.safety_notes
      ? h("p", { className: "safety-source" }, `Safety source: ${listing.safety_notes}`)
      : null,
    manual
      ? h("p", { className: "confidence manual" }, h(AlertTriangle, { size: 14 }), schoolDisplay.confidence)
      : schoolDisplay.confidence
        ? h("p", { className: "confidence" }, schoolDisplay.confidence)
        : null,
  );
}

function App() {
  const [urls, setUrls] = useState("");
  const [sort, setSort] = useState("school_proximity");
  const [listings, setListings] = useState([]);
  const [status, setStatus] = useState("Loading saved listings...");
  const [pageSize, setPageSize] = useState(25);
  const [page, setPage] = useState(1);
  const [showSchoolBoardFilterMenu, setShowSchoolBoardFilterMenu] = useState(false);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [draftFilters, setDraftFilters] = useState(DEFAULT_FILTERS);
  const [showFilters, setShowFilters] = useState(false);
  const [showDistanceSettings, setShowDistanceSettings] = useState(false);
  const [showFeeSettings, setShowFeeSettings] = useState(false);
  const [distanceSettings, setDistanceSettings] = useState({ preferred_max_km: "1.0", considerable_max_km: "1.5" });
  const [feeSettings, setFeeSettings] = useState({ green_max_fee: "400", amber_max_fee: "600" });
  const [distanceError, setDistanceError] = useState("");
  const [feeError, setFeeError] = useState("");

  async function loadListings(nextSort = sort) {
    const response = await fetch(`/api/listings?sort=${encodeURIComponent(nextSort)}`);
    const data = await response.json();
    setListings(data.listings || []);
    setPage(1);
  }

  useEffect(() => {
    fetch("/api/seed", { method: "POST" })
      .then(() => loadListings())
      .then(() => setStatus("Ready"))
      .catch(() => setStatus("Backend is not reachable"));
    fetch("/api/settings/distance")
      .then((response) => response.json())
      .then((data) => {
        setDistanceSettings({
          preferred_max_km: String(data.preferred_max_km ?? 1.0),
          considerable_max_km: String(data.considerable_max_km ?? 1.5),
        });
        if (!data.configured) setShowDistanceSettings(true);
      })
      .catch(() => {});
    fetch("/api/settings/fee")
      .then((response) => response.json())
      .then((data) => {
        setFeeSettings({
          green_max_fee: String(data.green_max_fee ?? 400),
          amber_max_fee: String(data.amber_max_fee ?? 600),
        });
      })
      .catch(() => {});
  }, []);

  async function importUrls(event) {
    event.preventDefault();
    setStatus("Queued import job...");
    const response = await fetch("/api/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ urls, school_board: "both" }),
    });
    const job = await response.json();
    if (!job.id) {
      setStatus("Import could not be queued");
      return;
    }
    pollJob(job.id);
  }

  async function pollJob(jobId) {
    const response = await fetch(`/api/jobs/${jobId}`);
    const job = await response.json();
    if (job.status === "failed") {
      setStatus(`Import failed: ${job.message || "Unknown error"}`);
      return;
    }
    if (job.status === "completed") {
      await loadListings();
      setStatus(`Imported ${job.imported} listing${job.imported === 1 ? "" : "s"} (${job.skipped} skipped).`);
      return;
    }
    setStatus(`${job.message || "Importing"} (${job.processed || 0}/${job.total || 0})`);
    window.setTimeout(() => pollJob(jobId), 1500);
  }

  async function deleteListing(url) {
    await fetch(`/api/listings/${encodeURIComponent(url)}`, { method: "DELETE" });
    await loadListings();
    setStatus("Deleted entry");
  }

  function changeSort(value) {
    setSort(value);
    loadListings(value);
  }

  function changePageSize(value) {
    setPageSize(value === "all" ? "all" : Number(value));
    setPage(1);
  }

  function changeDraftFilter(name, value) {
    setDraftFilters((current) => ({ ...current, [name]: value }));
  }

  function applyFilters() {
    setFilters(draftFilters);
    setPage(1);
    setShowFilters(false);
  }

  function clearFilters() {
    setFilters(DEFAULT_FILTERS);
    setDraftFilters(DEFAULT_FILTERS);
    setPage(1);
  }

  function applyQuickFilter(nextFilters) {
    const merged = { ...DEFAULT_FILTERS, ...nextFilters };
    setFilters(merged);
    setDraftFilters(merged);
    setShowFilters(false);
    setPage(1);
  }

  function toggleDraftSchoolBoard(board) {
    const current = new Set(String(draftFilters.schoolBoard || "").split(",").filter(Boolean));
    if (current.has(board)) current.delete(board);
    else current.add(board);
    if (current.size === 0) return;
    changeDraftFilter("schoolBoard", ["ocdsb", "ocsb"].filter((value) => current.has(value)).join(","));
  }

  async function saveDistanceSettings(event) {
    event.preventDefault();
    setDistanceError("");
    const response = await fetch("/api/settings/distance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        preferred_max_km: distanceSettings.preferred_max_km,
        considerable_max_km: distanceSettings.considerable_max_km,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      setDistanceError(data.error || "Could not save distance settings.");
      return;
    }
    setDistanceSettings({
      preferred_max_km: String(data.preferred_max_km),
      considerable_max_km: String(data.considerable_max_km),
    });
    setShowDistanceSettings(false);
    await loadListings();
    setStatus("School distance preferences saved");
  }

  async function saveFeeSettings(event) {
    event.preventDefault();
    setFeeError("");
    const response = await fetch("/api/settings/fee", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        green_max_fee: feeSettings.green_max_fee,
        amber_max_fee: feeSettings.amber_max_fee,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      setFeeError(data.error || "Could not save condo fee color settings.");
      return;
    }
    setFeeSettings({
      green_max_fee: String(data.green_max_fee),
      amber_max_fee: String(data.amber_max_fee),
    });
    setShowFeeSettings(false);
    setStatus("Condo fee color settings saved");
  }

  const activeFilterCount = useMemo(
    () => Object.entries(filters).filter(([key, value]) => value !== DEFAULT_FILTERS[key]).length,
    [filters],
  );

  const filteredListings = useMemo(
    () =>
      listings.filter((item) => {
        if (
          filters.allGreen
          && !(
            item.safety_category === "Very Safe"
            && item.school_distance_category === "Preferred"
            && scoreTier(basementClass(item.basement)) === "good"
            && scoreTier(parkingClass(item.parking_type)) === "good"
            && feeTier(item.maintenance_fee, feeSettings) === "low"
            && scoreTier(recommendationClass(item.overall_verdict)) === "good"
          )
        ) return false;
        if (filters.safety !== "all" && item.safety_category !== filters.safety) return false;
        if (filters.schoolDistance !== "all" && item.school_distance_category !== filters.schoolDistance) return false;
        if (filters.basement !== "all" && scoreTier(basementClass(item.basement)) !== filters.basement) return false;
        if (filters.parking !== "all" && scoreTier(parkingClass(item.parking_type)) !== filters.parking) return false;
        if (filters.condoFee !== "all" && feeTier(item.maintenance_fee, feeSettings) !== filters.condoFee) return false;
        if (filters.recommendation !== "all" && scoreTier(recommendationClass(item.overall_verdict)) !== filters.recommendation) return false;
        if (filters.verification === "manual" && !(item.confidence || "").toLowerCase().includes("manual")) return false;
        if (filters.verification === "verified" && (item.confidence || "").toLowerCase().includes("manual")) return false;
        const schoolBoards = new Set((item.schools || []).map((school) => String(school.board || "").toLowerCase()));
        const schoolBoardText = `${item.school || ""} ${item.confidence || ""}`.toLowerCase();
        const hasOcdsb = schoolBoards.has("ocdsb") || schoolBoardText.includes("ocdsb");
        const hasOcsb = schoolBoards.has("ocsb") || schoolBoardText.includes("ocsb");
        if (filters.schoolBoard === "ocdsb" && !hasOcdsb) return false;
        if (filters.schoolBoard === "ocsb" && !hasOcsb) return false;
        if (filters.community && !String(item.community || "").toLowerCase().includes(filters.community.toLowerCase())) return false;
        if (filters.maxPrice && Number(item.price) > Number(filters.maxPrice)) return false;
        return true;
      }),
    [listings, filters, feeSettings],
  );

  const counts = useMemo(
    () =>
      filteredListings.reduce(
        (acc, item) => {
          acc.total += 1;
          if (item.safety_category === "Very Safe") acc.safe += 1;
          if (item.school_distance_category === "Preferred") acc.preferred += 1;
          if ((item.confidence || "").toLowerCase().includes("manual")) acc.manual += 1;
          return acc;
        },
        { total: 0, safe: 0, preferred: 0, manual: 0 },
      ),
    [filteredListings],
  );

  const effectivePageSize = pageSize === "all" ? Math.max(1, filteredListings.length) : pageSize;
  const totalPages = Math.max(1, Math.ceil(filteredListings.length / effectivePageSize));
  const safePage = Math.min(page, totalPages);
  const pageStart = (safePage - 1) * effectivePageSize;
  const pageListings = filteredListings.slice(pageStart, pageStart + effectivePageSize);
  const visibleStart = filteredListings.length === 0 ? 0 : pageStart + 1;
  const visibleEnd = Math.min(pageStart + effectivePageSize, filteredListings.length);
  const draftSchoolBoards = new Set(String(draftFilters.schoolBoard || "").split(",").filter(Boolean));
  const schoolBoardFilterLabel = draftSchoolBoards.has("ocdsb") && draftSchoolBoards.has("ocsb")
    ? "OCDSB public + OCSB Catholic"
    : draftSchoolBoards.has("ocsb")
      ? "OCSB Catholic"
      : "OCDSB public";

  return h(
    "main",
    { className: "app" },
    h(
      "header",
      { className: "topbar" },
      h(
        "div",
        { className: "brand-block" },
        h(
          "div",
          { className: "brand-row" },
          h("div", { className: "logo-mark", "aria-hidden": "true" }, h(GraduationCap, { size: 20 }), h(Crosshair, { size: 16 }), h(Home, { size: 18 })),
          h("h1", null, "Ottawa Student's HomeHunter"),
        ),
        h("p", null, "Upload Realtor.ca URLs, and compare school proximity, safety, and price."),
      ),
      h(
        "div",
        { className: "header-actions" },
        h("div", { className: "status" }, h(ShieldCheck, { size: 16 }), status),
      ),
    ),
    showDistanceSettings
      ? h(
        "div",
        { className: "modal-backdrop" },
        h(
          "form",
          { className: "distance-modal", onSubmit: saveDistanceSettings },
          h("h2", null, "Proximity Slider"),
          h("p", null, "Choose where Preferred ends and Considerable ends. Anything after the second marker is Too Far."),
          h(TwoHandleSlider, {
            min: 0.1,
            max: Math.max(5, Number(distanceSettings.considerable_max_km) + 1),
            step: 0.1,
            lower: distanceSettings.preferred_max_km,
            upper: distanceSettings.considerable_max_km,
            format: formatKm,
            onLower: (value) => setDistanceSettings((current) => ({ ...current, preferred_max_km: value })),
            onUpper: (value) => setDistanceSettings((current) => ({ ...current, considerable_max_km: value })),
          }),
          h("div", { className: "slider-legend" }, h("span", null, "Preferred"), h("span", null, "Considerable"), h("span", null, "Too Far")),
          distanceError ? h("p", { className: "settings-error" }, distanceError) : null,
          h(
            "div",
            { className: "form-actions" },
            h("button", { type: "submit" }, "Save preferences"),
            h("button", { type: "button", className: "secondary", onClick: () => setShowDistanceSettings(false) }, "Cancel"),
          ),
        ),
      )
      : null,
    showFeeSettings
      ? h(
        "div",
        { className: "modal-backdrop" },
        h(
          "form",
          { className: "distance-modal", onSubmit: saveFeeSettings },
          h("h2", null, "Condo Fee Slider"),
          h("p", null, "Choose where green fees end and amber fees end. Anything after the second marker is red."),
          h(TwoHandleSlider, {
            min: 0,
            max: Math.max(1500, Number(feeSettings.amber_max_fee) + 200),
            step: 25,
            lower: feeSettings.green_max_fee,
            upper: feeSettings.amber_max_fee,
            format: formatFee,
            onLower: (value) => setFeeSettings((current) => ({ ...current, green_max_fee: value })),
            onUpper: (value) => setFeeSettings((current) => ({ ...current, amber_max_fee: value })),
          }),
          h("div", { className: "slider-legend" }, h("span", null, "Green"), h("span", null, "Amber"), h("span", null, "Red")),
          feeError ? h("p", { className: "settings-error" }, feeError) : null,
          h(
            "div",
            { className: "form-actions" },
            h("button", { type: "submit" }, "Save colors"),
            h("button", { type: "button", className: "secondary", onClick: () => setShowFeeSettings(false) }, "Cancel"),
          ),
        ),
      )
      : null,
    h(
      "section",
      { className: "workspace" },
      h(
        "form",
        { className: "import-panel", onSubmit: importUrls },
        h("label", { htmlFor: "urls" }, "Realtor.ca URLs"),
        h("textarea", {
          id: "urls",
          value: urls,
          onChange: (event) => setUrls(event.target.value),
          placeholder: "Paste one Realtor.ca listing URL per line",
        }),
        h(
          "div",
          { className: "form-actions" },
          h("button", { type: "submit" }, "Import listings"),
          h("button", { type: "button", className: "secondary", onClick: () => setUrls("") }, "Clear input"),
        ),
        h(
          "div",
          { className: "form-actions settings-actions" },
          h("button", { type: "button", className: "secondary", onClick: () => setShowDistanceSettings(true) }, "Proximity slider"),
          h("button", { type: "button", className: "secondary", onClick: () => setShowFeeSettings(true) }, "Condo fee slider"),
        ),
      ),
      h(
        "aside",
        { className: "summary" },
        h("button", { type: "button", className: "summary-tile", onClick: clearFilters }, h("strong", null, counts.total), h("span", null, "Listings")),
        h("button", { type: "button", className: "summary-tile", onClick: () => applyQuickFilter({ schoolDistance: "Preferred" }) }, h("strong", null, counts.preferred), h("span", null, "Preferred school distance")),
        h("button", { type: "button", className: "summary-tile", onClick: () => applyQuickFilter({ safety: "Very Safe" }) }, h("strong", null, counts.safe), h("span", null, "Very safe")),
        h("button", { type: "button", className: "summary-tile", onClick: () => applyQuickFilter({ verification: "manual" }) }, h("strong", null, counts.manual), h("span", null, "Need manual check")),
      ),
    ),
    h(
      "section",
      { className: "controls" },
      h("label", { htmlFor: "sort" }, h(ArrowDownAZ, { size: 16 }), "Sort by"),
      h("select", { id: "sort", value: sort, onChange: (event) => changeSort(event.target.value) }, ...SORTS.map(([value, label]) => h("option", { key: value, value }, label))),
      h("label", { htmlFor: "page-size" }, "Show"),
      h("select", { id: "page-size", value: pageSize, onChange: (event) => changePageSize(event.target.value) }, ...PAGE_SIZES.map((value) => h("option", { key: value, value }, value === "all" ? "All entries" : `${value} entries`))),
      h(
        "button",
        {
          type: "button",
          className: `filter-toggle ${showFilters ? "active" : "secondary"}`,
          onClick: () => {
            setDraftFilters(filters);
            setShowFilters((value) => !value);
          },
        },
        "Filter",
        activeFilterCount > 0 ? h("sup", null, activeFilterCount) : null,
      ),
      h("span", { className: "page-summary" }, `Showing ${visibleStart}-${visibleEnd} of ${filteredListings.length} filtered (${listings.length} total)`),
    ),
    showFilters ? h(
      "section",
      { className: "filters" },
      h(
        "label",
        { className: "all-green-filter" },
        h("input", {
          type: "checkbox",
          checked: draftFilters.allGreen,
          onChange: (event) => changeDraftFilter("allGreen", event.target.checked),
        }),
        "Show me all green",
      ),
      h("label", { htmlFor: "filter-safety" }, "Safety"),
      h("select", { id: "filter-safety", value: draftFilters.safety, onChange: (event) => changeDraftFilter("safety", event.target.value) },
        h("option", { value: "all" }, "All"),
        h("option", { value: "Very Safe" }, "Very Safe"),
        h("option", { value: "Moderate" }, "Moderate"),
        h("option", { value: "Risky" }, "Risky"),
      ),
      h("label", { htmlFor: "filter-school" }, "School distance"),
      h("select", { id: "filter-school", value: draftFilters.schoolDistance, onChange: (event) => changeDraftFilter("schoolDistance", event.target.value) },
        h("option", { value: "all" }, "All"),
        h("option", { value: "Preferred" }, "Preferred"),
        h("option", { value: "Considerable" }, "Considerable"),
        h("option", { value: "Too Far" }, "Too Far"),
      ),
      h("label", { htmlFor: "filter-basement" }, "Basement"),
      h("select", { id: "filter-basement", value: draftFilters.basement, onChange: (event) => changeDraftFilter("basement", event.target.value) },
        h("option", { value: "all" }, "All"),
        h("option", { value: "good" }, "Finished"),
        h("option", { value: "mid" }, "Semi/partly"),
        h("option", { value: "bad" }, "Unfinished/no info"),
      ),
      h("label", { htmlFor: "filter-parking" }, "Garage"),
      h("select", { id: "filter-parking", value: draftFilters.parking, onChange: (event) => changeDraftFilter("parking", event.target.value) },
        h("option", { value: "all" }, "All"),
        h("option", { value: "good" }, "Garage"),
        h("option", { value: "mid" }, "Parking, no garage"),
        h("option", { value: "bad" }, "No garage/no info"),
      ),
      h("label", { htmlFor: "filter-fee" }, "Condo fee"),
      h("select", { id: "filter-fee", value: draftFilters.condoFee, onChange: (event) => changeDraftFilter("condoFee", event.target.value) },
        h("option", { value: "all" }, "All"),
        h("option", { value: "low" }, `Green: <= $${feeSettings.green_max_fee}`),
        h("option", { value: "mid" }, `Amber: <= $${feeSettings.amber_max_fee}`),
        h("option", { value: "high" }, `Red: > $${feeSettings.amber_max_fee}`),
        h("option", { value: "unknown" }, "No info"),
      ),
      h("label", { htmlFor: "filter-recommendation" }, "Recommendation"),
      h("select", { id: "filter-recommendation", value: draftFilters.recommendation, onChange: (event) => changeDraftFilter("recommendation", event.target.value) },
        h("option", { value: "all" }, "All"),
        h("option", { value: "good" }, "Green"),
        h("option", { value: "mid" }, "Yellow"),
        h("option", { value: "bad" }, "Red"),
      ),
      h("label", { htmlFor: "filter-verification" }, "Verification"),
      h("select", { id: "filter-verification", value: draftFilters.verification, onChange: (event) => changeDraftFilter("verification", event.target.value) },
        h("option", { value: "all" }, "All"),
        h("option", { value: "verified" }, "No manual note"),
        h("option", { value: "manual" }, "Manual needed"),
      ),
      h(
        "div",
        { className: "filter-checkbox-dropdown" },
        h("label", { htmlFor: "filter-school-board" }, "School board"),
        h(
          "button",
          {
            type: "button",
            id: "filter-school-board",
            className: "checkbox-dropdown-toggle",
            "aria-expanded": showSchoolBoardFilterMenu,
            onClick: () => setShowSchoolBoardFilterMenu((value) => !value),
          },
          schoolBoardFilterLabel,
        ),
        showSchoolBoardFilterMenu
          ? h(
            "div",
            { className: "checkbox-dropdown-menu" },
            h(
              "label",
              null,
              h("input", {
                type: "checkbox",
                checked: draftSchoolBoards.has("ocdsb"),
                onChange: () => toggleDraftSchoolBoard("ocdsb"),
              }),
              "OCDSB public",
            ),
            h(
              "label",
              null,
              h("input", {
                type: "checkbox",
                checked: draftSchoolBoards.has("ocsb"),
                onChange: () => toggleDraftSchoolBoard("ocsb"),
              }),
              "OCSB Catholic",
            ),
          )
          : null,
      ),
      h("label", { htmlFor: "filter-community" }, "Community"),
      h("input", { id: "filter-community", value: draftFilters.community, onChange: (event) => changeDraftFilter("community", event.target.value), placeholder: "e.g. Kanata" }),
      h("label", { htmlFor: "filter-price" }, "Max price"),
      h("input", { id: "filter-price", type: "number", min: "0", step: "1000", value: draftFilters.maxPrice, onChange: (event) => changeDraftFilter("maxPrice", event.target.value), placeholder: "500000" }),
      h("div", { className: "filter-actions" },
        h("button", { type: "button", onClick: applyFilters }, "Apply"),
        h("button", { type: "button", className: "secondary", onClick: clearFilters }, "Reset"),
      ),
    ) : null,
    h("section", { className: "listing-grid" }, ...pageListings.map((listing) => h(ListingCard, { key: listing.url, listing, onDelete: deleteListing, feeSettings, schoolBoardFilter: filters.schoolBoard }))),
    h(
      "nav",
      { className: "pagination", "aria-label": "Pagination" },
      h("button", { type: "button", className: "secondary", disabled: safePage === 1, onClick: () => setPage(1) }, "First"),
      h("button", { type: "button", className: "secondary", disabled: safePage === 1, onClick: () => setPage((current) => Math.max(1, current - 1)) }, "Previous"),
      h("span", null, `Page ${safePage} of ${totalPages}`),
      h("button", { type: "button", className: "secondary", disabled: safePage === totalPages, onClick: () => setPage((current) => Math.min(totalPages, current + 1)) }, "Next"),
      h("button", { type: "button", className: "secondary", disabled: safePage === totalPages, onClick: () => setPage(totalPages) }, "Last"),
    ),
  );
}

createRoot(document.getElementById("root")).render(h(App));
