import { useState, useEffect, useCallback, useRef } from "react";

// ══ TOKENS ═══════════════════════════════════════════════════════════════════
const C = {
  bg:"#FFFFFF", surface:"#F7F9FC", surfaceHi:"#EEF3FA", surfaceMd:"rgba(0,0,0,0.06)",
  border:"rgba(0,0,0,0.08)", borderMd:"rgba(0,0,0,0.14)",
  text:"#0F1F35", textMid:"#3A5272", textDim:"#7A92AD",
  blue:"#1A65C0", blueLt:"#2D7DD2", teal:"#0A8C65", tealLt:"#0E9E75",
  purple:"#5A52C4", purpleLt:"#7A6FD8", amber:"#B87000", amberLt:"#E8A020",
  red:"#C0282A", redLt:"#D94040", green:"#1E8A3C", greenLt:"#3DAA5C",
};

const EXPIRY_MS = 6 * 60 * 60 * 1000; // 6 hours

// ══ HELPERS ══════════════════════════════════════════════════════════════════
const fmt2 = v => v.toFixed(2);
const clamp = (v,lo,hi) => Math.min(hi, Math.max(lo, v));
const ts = () => new Date().toLocaleTimeString("en-PH",{hour:"2-digit",minute:"2-digit",second:"2-digit"});
const tsDate = () => new Date().toLocaleString("en-PH",{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit",second:"2-digit"});
let _id = 1;
const nextId = () => `RPT-${String(_id++).padStart(4,"0")}`;

function getTier(s){ if(s<0.50)return null; if(s<0.65)return"Watch"; if(s<0.80)return"Advisory"; return"Warning"; }
function tierColor(t){ if(t==="Watch")return C.amber; if(t==="Advisory")return C.amberLt; if(t==="Warning")return C.red; return C.textDim; }
function tierBg(t){ if(t==="Watch")return"rgba(232,160,32,0.10)"; if(t==="Advisory")return"rgba(245,197,90,0.08)"; if(t==="Warning")return"rgba(192,40,42,0.08)"; return"transparent"; }

// ── Province lists ────────────────────────────────────────────────────────────
const PROVINCES = {
  PH: ["Eastern Samar","Western Samar","Northern Samar","Leyte","Southern Leyte","Cebu","Bohol","Davao del Norte","Davao del Sur","Cagayan","Isabela","Aurora","Quezon","Albay","Sorsogon","Masbate"],
  VT: ["Hanoi","Ho Chi Minh City","Da Nang","Hai Phong","Can Tho","An Giang","Ben Tre","Ca Mau","Khanh Hoa","Nghe An","Quang Binh","Quang Nam","Thua Thien Hue"],
  TH: ["Bangkok","Chiang Mai","Chiang Rai","Nakhon Ratchasima","Khon Kaen","Udon Thani","Surat Thani","Phuket","Songkhla","Nakhon Si Thammarat","Phetchaburi","Rayong","Chonburi"],
};
// ══ SIMULATION SCRIPT ════════════════════════════════════════════════════════
// Scripted typhoon track scenario — provinces are fixed, scores randomised
// within a realistic band that escalates over waves.
// wave index loops: 0 → 1 → 2 → 3 → back to 0
const SIM_STORM = "Typhoon Pepito";
const SIM_SCRIPT = [
  // Wave 1 — broad initial detection, low-confidence social chatter
  {
    label: "Initial Detection",
    flood:   { provinces:["Eastern Samar","Northern Samar","Leyte"],          scoreRange:[0.52,0.64], ctx:{ basinName:"Gandara Basin", discharge:"900",  threshold:"1800", floodHorizon:"48", severityLabel:"WATCH"    }},
    typhoon: { provinces:["Eastern Samar","Northern Samar","Western Samar","Leyte"], scoreRange:[0.55,0.68], ctx:{ stormName:SIM_STORM, windKmh:"120", typhoonHorizon:"48", cteKm:"180" }},
    social:  { provinces:["Eastern Samar","Northern Samar","Leyte","Cebu"],   scoreRange:[0.50,0.62], ctx:{ stormName:SIM_STORM, postCount:"14",  domLabel:"watch",    highLang:true }},
  },
  // Wave 2 — track narrows, confidence rising
  {
    label: "Track Narrowing",
    flood:   { provinces:["Eastern Samar","Northern Samar"],                  scoreRange:[0.65,0.76], ctx:{ basinName:"Gandara Basin", discharge:"1400", threshold:"1800", floodHorizon:"36", severityLabel:"ADVISORY" }},
    typhoon: { provinces:["Eastern Samar","Northern Samar","Western Samar"],  scoreRange:[0.68,0.79], ctx:{ stormName:SIM_STORM, windKmh:"155", typhoonHorizon:"30", cteKm:"110" }},
    social:  { provinces:["Eastern Samar","Northern Samar","Western Samar"],  scoreRange:[0.63,0.75], ctx:{ stormName:SIM_STORM, postCount:"38",  domLabel:"advisory", highLang:true }},
  },
  // Wave 3 — landfall imminent, all AIs converge
  {
    label: "Landfall Imminent",
    flood:   { provinces:["Eastern Samar","Northern Samar"],                  scoreRange:[0.80,0.91], ctx:{ basinName:"Gandara Basin", discharge:"1750", threshold:"1800", floodHorizon:"18", severityLabel:"WARNING"  }},
    typhoon: { provinces:["Eastern Samar","Northern Samar"],                  scoreRange:[0.82,0.94], ctx:{ stormName:SIM_STORM, windKmh:"195", typhoonHorizon:"18", cteKm:"55"  }},
    social:  { provinces:["Eastern Samar","Northern Samar"],                  scoreRange:[0.80,0.92], ctx:{ stormName:SIM_STORM, postCount:"89",  domLabel:"warning",  highLang:true }},
  },
  // Wave 4 — landfall, peak intensity, tight convergence
  {
    label: "Landfall",
    flood:   { provinces:["Eastern Samar"],                                   scoreRange:[0.88,0.97], ctx:{ basinName:"Gandara Basin", discharge:"1800", threshold:"1800", floodHorizon:"6",  severityLabel:"WARNING"  }},
    typhoon: { provinces:["Eastern Samar","Northern Samar"],                  scoreRange:[0.90,0.98], ctx:{ stormName:SIM_STORM, windKmh:"220", typhoonHorizon:"6",  cteKm:"20"  }},
    social:  { provinces:["Eastern Samar","Northern Samar"],                  scoreRange:[0.88,0.97], ctx:{ stormName:SIM_STORM, postCount:"147", domLabel:"warning",  highLang:true }},
  },
];

function simScore([lo, hi]) {
  return Math.round((lo + Math.random() * (hi - lo)) * 100) / 100;
}



// ── Province coordinates + place IDs (PH) ────────────────────────────────────
const PROVINCE_COORDS = {
  "Eastern Samar":  { lat:11.5001, lng:125.4999, placeId:"ChIJj4Q9ER_kCDMRj6g0QpiH7ZU" },
  "Northern Samar": { lat:12.3613, lng:124.7741, placeId:"ChIJEY0Gn6b1CTMRMKeOYBPNTgo" },
  "Western Samar":  { lat:11.5795, lng:124.9748, placeId:"ChIJFzMfDUpICDMR1zI106TV0GA" },
  "Leyte":          { lat:11.0891, lng:124.8923, placeId:"ChIJ4TnilcbtBzMR0_L6-A-Cr48" },
  "Southern Leyte": { lat:10.3346, lng:125.1709, placeId:"ChIJ9SlbfZEXBzMRs9Ip9es_Xmg" },
  "Cebu":           { lat:10.6079, lng:123.8858, placeId:"ChIJvSXsc5dzqTMRYI7-mlFhFEI" },
  "Bohol":          { lat: 9.8500, lng:124.1435, placeId:"ChIJ31ShG94XqjMRINAYIQS_yGs" },
  "Cagayan":        { lat:18.2490, lng:121.8788, placeId:"ChIJLTqLxz_5hTMRYMCccmvVRIU" },
  "Isabela":        { lat:16.9754, lng:121.8107, placeId:"ChIJN47LhvtGhTMRut0YP5jYJwY" },
  "Aurora":         { lat:16.0774, lng:121.7693, placeId:"ChIJG_hoej0NmjMRS0CfUrl4ya4" },
  "Quezon":         { lat:13.9347, lng:121.9473, placeId:"ChIJWziNTeafojMRH7SZ84zudoE" },
  "Albay":          { lat:13.1775, lng:123.5280, placeId:"ChIJE95VZ05UoDMRvW_dg_3qyMk" },
  "Sorsogon":       { lat:12.7600, lng:123.9304, placeId:"ChIJ67Npv9reoDMRsX2Jarf72Sg" },
  "Masbate":        { lat:12.3060, lng:123.5589, placeId:"ChIJH82sLsfHpjMRCsV7ngRlsaU" },
  "Davao del Norte":{ lat: 7.5618, lng:125.6533, placeId:"ChIJHSqPedBL-TIRi2ija0Q5qj0" },
  "Davao del Sur":  { lat: 6.7663, lng:125.3284, placeId:"ChIJ40AP8j5s9zIRqd8MaWdSFxo" },

  // Vietnam
  "Hanoi":          { lat:21.0285, lng:105.8542 },
  "Ho Chi Minh City": { lat:10.8231, lng:106.6297 },
  "Da Nang":        { lat:16.0544, lng:108.2022 },
  "Hai Phong":      { lat:20.8449, lng:106.6881 },
  "Can Tho":        { lat:10.0452, lng:105.7469 },
  "An Giang":       { lat:10.5216, lng:105.1259 },
  "Ben Tre":        { lat:10.2433, lng:106.3756 },
  "Ca Mau":         { lat: 9.1769, lng:105.1524 },
  "Khanh Hoa":      { lat:12.2388, lng:109.1967 },
  "Nghe An":        { lat:18.6796, lng:105.6813 },
  "Quang Binh":     { lat:17.4684, lng:106.6222 },
  "Quang Nam":      { lat:15.5736, lng:108.4740 },
  "Thua Thien Hue": { lat:16.4637, lng:107.5909 },

  // Thailand
  "Bangkok":        { lat:13.7563, lng:100.5018 },
  "Chiang Mai":     { lat:18.7883, lng: 98.9853 },
  "Chiang Rai":     { lat:19.9105, lng: 99.8406 },
  "Nakhon Ratchasima": { lat:14.9799, lng:102.0978 },
  "Khon Kaen":      { lat:16.4419, lng:102.8360 },
  "Udon Thani":     { lat:17.4138, lng:102.7870 },
  "Surat Thani":    { lat: 9.1382, lng: 99.3215 },
  "Phuket":         { lat: 7.8804, lng: 98.3923 },
  "Songkhla":       { lat: 7.1898, lng:100.5950 },
  "Nakhon Si Thammarat": { lat: 8.4304, lng: 99.9631 },
  "Phetchaburi":    { lat:13.1119, lng: 99.9457 },
  "Rayong":         { lat:12.6814, lng:101.2816 },
  "Chonburi":       { lat:13.3611, lng:100.9847 },
};

// ── AI type metadata ──────────────────────────────────────────────────────────
const AI_META = {
  flood:   { label:"AI-1 · Flood LSTM",       icon:"💧", color:C.blue,   colorLt:C.blueLt,   kind:"physical" },
  typhoon: { label:"AI-2 · Typhoon XGBoost",  icon:"🌀", color:C.teal,   colorLt:C.tealLt,   kind:"physical" },
  social:  { label:"AI-3 · BERT NLP",         icon:"📡", color:C.purple, colorLt:C.purpleLt, kind:"social"   },
};

// ══ FUSION ENGINE ════════════════════════════════════════════════════════════
// Each report is a single-province row (fan-out happens at submit time).
// Physical types weighted 0.65, social 0.35 (or 0.20 low-resource).
// Cross-AI diversity bonus: +0.04 per additional unique AI type beyond the first.
function fuseReports(reports, now = Date.now(), reviewedAt = new Map()) {
  // Exclude expired AND reports submitted before their province was reviewed
  // reviewedAt: Map of provinceKey -> timestamp when reviewed
  // Reports submitted AFTER the review timestamp are fresh and not excluded
  const live = reports.filter(r => {
    if (now - r.submittedAt >= EXPIRY_MS) return false;
    const rt = reviewedAt.get(`${r.country}::${r.province}`);
    return !rt || r.submittedAt > rt; // fresh if submitted after review
  });

  const byProvince = {};
  for (const r of live) {
    const key = `${r.country}::${r.province}`;
    if (!byProvince[key]) byProvince[key] = { country:r.country, province:r.province, entries:[] };
    byProvince[key].entries.push(r);
  }

  const results = Object.entries(byProvince).map(([key, { country, province, entries }]) => {
    const physEntries = entries.filter(r => AI_META[r.aiType].kind === "physical");
    const socEntries  = entries.filter(r => AI_META[r.aiType].kind === "social");
    const physAvg = physEntries.length ? physEntries.reduce((s,r)=>s+r.score,0)/physEntries.length : 0;
    const socAvg  = socEntries.length  ? socEntries.reduce((s,r)=>s+r.score,0)/socEntries.length   : 0;
    const nlpW    = socEntries.some(r=>r.highLang===false) ? 0.20 : 0.35;
    const uniqueTypes = new Set(entries.map(r=>r.aiType)).size;
    const diversityBonus = Math.max(0, uniqueTypes - 1) * 0.04;
    const isOverride = physAvg >= 0.90;
    const base = isOverride ? physAvg : physAvg * 0.65 + socAvg * nlpW;
    const fusion = clamp(base + diversityBonus, 0.01, 0.99);
    return { country, province, key, fusion, physAvg, socAvg, uniqueTypes,
      reportCount: entries.length, isOverride, reports: entries,
      tier: getTier(fusion), reviewed: false };
  });

  const active = results.sort((a,b) => b.fusion - a.fusion);
  const activeKeys = new Set(active.map(a => a.key));

  // Append reviewed provinces at the bottom for display only — zero weight.
  // Skip any province that already has a fresh active entry (Wave 2+ case).
  const reviewedExpired = reports.filter(r => {
    if (now - r.submittedAt >= EXPIRY_MS) return false;
    const key = `${r.country}::${r.province}`;
    if (activeKeys.has(key)) return false;
    const rt = reviewedAt.get(key);
    return rt && r.submittedAt <= rt;
  });
  const reviewedByProvince = {};
  for (const r of reviewedExpired) {
    const key = `${r.country}::${r.province}`;
    if (!reviewedByProvince[key]) reviewedByProvince[key] = { country:r.country, province:r.province, key, entries:[] };
    reviewedByProvince[key].entries.push(r);
  }
  const reviewedResults = Object.values(reviewedByProvince).map(({ country, province, key, entries }) => ({
    country, province, key, fusion: 0, physAvg: 0, socAvg: 0,
    uniqueTypes: new Set(entries.map(r=>r.aiType)).size,
    reportCount: entries.length, isOverride: false, reports: entries,
    tier: null, reviewed: true,
  }));

  return [...active, ...reviewedResults];
}

// ══ PRIMITIVES ════════════════════════════════════════════════════════════════
function SectionLabel({children}){
  return(
    <div style={{fontSize:10,fontWeight:700,letterSpacing:"0.12em",color:C.textDim,textTransform:"uppercase",marginBottom:10,display:"flex",alignItems:"center",gap:8}}>
      <div style={{flex:1,height:"0.5px",background:C.border}}/>{children}<div style={{flex:1,height:"0.5px",background:C.border}}/>
    </div>
  );
}
function Tag({label,color}){return(<span style={{display:"inline-block",fontSize:10,fontWeight:700,letterSpacing:"0.07em",padding:"2px 8px",borderRadius:20,background:`${color}14`,color,border:`0.5px solid ${color}44`}}>{label}</span>);}
function Pill({label,color}){return(<span style={{display:"inline-block",fontSize:10,fontWeight:600,color,background:`${color}18`,border:`0.5px solid ${color}44`,borderRadius:20,padding:"2px 8px",marginTop:6,letterSpacing:"0.03em"}}>{label}</span>);}
function Arrow(){return(<div style={{display:"flex",justifyContent:"center",padding:"6px 0",color:C.textDim}}><svg width="16" height="22" viewBox="0 0 16 22" fill="none"><line x1="8" y1="0" x2="8" y2="16" stroke="currentColor" strokeWidth="1" strokeDasharray="3 2"/><polyline points="3,12 8,18 13,12" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinejoin="round"/></svg></div>);}
function AnimatedBar({pct,color,label,value}){return(<div style={{marginBottom:10}}><div style={{display:"flex",justifyContent:"space-between",fontSize:10,color:C.textDim,marginBottom:4}}><span>{label}</span><span style={{color:C.textMid,fontFamily:"monospace"}}>{value}</span></div><div style={{height:5,background:"rgba(0,0,0,0.08)",borderRadius:3,overflow:"hidden"}}><div style={{height:"100%",width:`${pct}%`,background:color,borderRadius:3,transition:"width 0.45s cubic-bezier(0.4,0,0.2,1)"}}/></div></div>);}

// ── Score Slider ──────────────────────────────────────────────────────────────
function ScoreSlider({ value, onChange, color, label }) {
  const pct = Math.round(value * 100);
  return (
    <div style={{ marginTop:12, paddingTop:12, borderTop:`0.5px solid ${C.border}` }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-end", marginBottom:6 }}>
        <div>
          <div style={{ fontSize:30, fontWeight:800, color, fontFamily:"monospace", lineHeight:1 }}>{fmt2(value)}</div>
          <div style={{ fontSize:10, color:C.textDim, marginTop:2 }}>{label}</div>
        </div>
        <Tag label={getTier(value)?.toUpperCase() ?? "BELOW THRESHOLD"} color={getTier(value) ? tierColor(getTier(value)) : C.textDim}/>
      </div>
      <div style={{ display:"flex", alignItems:"center", gap:10 }}>
        <input type="range" min={1} max={99} step={1} value={pct}
          onChange={e => onChange(clamp(parseInt(e.target.value)/100, 0.01, 0.99))}
          style={{ flex:1, accentColor:color, cursor:"pointer" }}/>
        <span style={{ fontSize:10, fontFamily:"monospace", color:C.textDim, minWidth:28 }}>{pct}%</span>
      </div>
    </div>
  );
}

// ── Field input ───────────────────────────────────────────────────────────────
function FieldInput({ fieldName, value, onChange, type="text", options=null, accent, unit="", note }) {
  return (
    <div style={{ marginBottom:8 }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"baseline", marginBottom:2 }}>
        <label style={{ fontSize:10, fontWeight:700, color:C.textDim, letterSpacing:"0.04em", fontFamily:"'IBM Plex Mono',monospace" }}>{fieldName}</label>
        {note && <span style={{ fontSize:9, color:C.textDim, fontStyle:"italic" }}>{note}</span>}
      </div>
      {options ? (
        <select value={value} onChange={e=>onChange(e.target.value)}
          style={{ width:"100%", padding:"5px 8px", borderRadius:6, border:`1px solid ${accent}44`,
            background:C.bg, color:C.text, fontSize:12, fontFamily:"inherit", outline:"none", cursor:"pointer", fontWeight:600 }}>
          {options.map(o=><option key={o} value={o}>{o}</option>)}
        </select>
      ) : (
        <div style={{ position:"relative" }}>
          <input type={type==="number"?"number":"text"} value={value} onChange={e=>onChange(e.target.value)}
            style={{ width:"100%", padding:`5px ${unit?"28px":"8px"} 5px 8px`, borderRadius:6,
              border:`1px solid ${accent}44`, background:C.bg, color:C.text,
              fontSize:12, fontFamily:"'IBM Plex Mono',monospace", outline:"none", boxSizing:"border-box" }}/>
          {unit && <span style={{ position:"absolute", right:8, top:"50%", transform:"translateY(-50%)", fontSize:10, color:C.textDim, pointerEvents:"none" }}>{unit}</span>}
        </div>
      )}
    </div>
  );
}

// ── Province multi-select checklist ──────────────────────────────────────────
function ProvinceChecklist({ country, selected, onChange, accentColor }) {
  const list = PROVINCES[country] ?? [];
  const allSelected = selected.length === list.length;

  function toggle(p) {
    onChange(selected.includes(p) ? selected.filter(x => x !== p) : [...selected, p]);
  }
  function toggleAll() {
    onChange(allSelected ? [] : [...list]);
  }

  return (
    <div style={{ marginBottom:10 }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"baseline", marginBottom:4 }}>
        <label style={{ fontSize:10, fontWeight:700, color:C.textDim, letterSpacing:"0.04em", fontFamily:"'IBM Plex Mono',monospace" }}>
          provinces <span style={{ color:accentColor, fontWeight:800 }}>{selected.length > 0 ? `(${selected.length} selected)` : "(none)"}</span>
        </label>
        <button onClick={toggleAll}
          style={{ fontSize:9, color:accentColor, background:"transparent", border:"none", cursor:"pointer", textDecoration:"underline", padding:0 }}>
          {allSelected ? "deselect all" : "select all"}
        </button>
      </div>
      <div style={{ maxHeight:140, overflowY:"auto", border:`1px solid ${accentColor}33`,
        borderRadius:8, background:C.bg }}>
        {list.map((p, i) => {
          const checked = selected.includes(p);
          return (
            <div key={p} onClick={() => toggle(p)}
              style={{ display:"flex", alignItems:"center", gap:8, padding:"5px 10px",
                cursor:"pointer", background: checked ? `${accentColor}0d` : "transparent",
                borderBottom: i < list.length-1 ? `0.5px solid ${C.border}` : "none",
                transition:"background 0.15s" }}>
              <div style={{ width:14, height:14, borderRadius:3, flexShrink:0,
                border:`1.5px solid ${checked ? accentColor : C.borderMd}`,
                background: checked ? accentColor : "transparent",
                display:"flex", alignItems:"center", justifyContent:"center" }}>
                {checked && <span style={{ color:"white", fontSize:9, lineHeight:1, fontWeight:800 }}>✓</span>}
              </div>
              <span style={{ fontSize:11, color: checked ? C.text : C.textMid, fontWeight: checked ? 600 : 400 }}>{p}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ══ AI INPUT PANEL ════════════════════════════════════════════════════════════
function AIInputPanel({ aiType, onSubmit }) {
  const meta = AI_META[aiType];
  const [country,    setCountry]   = useState("PH");
  const [provinces,  setProvinces] = useState([PROVINCES["PH"][0]]);
  useEffect(() => setProvinces([PROVINCES[country][0]]), [country]);

  const [stormName,     setStormName]     = useState("Kalmaegi");
  const [score,         setScore]         = useState(aiType === "flood" ? 0.72 : aiType === "typhoon" ? 0.84 : 0.68);
  const [basinName,     setBasinName]     = useState("Gandara Basin");
  const [discharge,     setDischarge]     = useState("1800");
  const [threshold,     setThreshold]     = useState("1800");
  const [floodHorizon,  setFloodHorizon]  = useState("36");
  const [severityLabel, setSeverityLabel] = useState("ADVISORY");
  const [windKmh,       setWindKmh]       = useState("185");
  const [typhoonHorizon,setTyphoonHorizon]= useState("18");
  const [cteKm,         setCteKm]         = useState("94");
  const [postCount,     setPostCount]     = useState("47");
  const [domLabel,      setDomLabel]      = useState("warning");
  const [highLang,      setHighLang]      = useState(true);
  const [flash,         setFlash]         = useState(false);

  function handleSubmit() {
    if (provinces.length === 0) return;
    const ctx = aiType === "flood"
      ? { basinName, discharge, threshold, floodHorizon, severityLabel }
      : aiType === "typhoon"
      ? { stormName, windKmh, typhoonHorizon, cteKm }
      : { stormName, postCount, domLabel, highLang };

    // Fan out: one independent row per selected province
    const now = Date.now();
    const display = tsDate();
    provinces.forEach(prov => {
      onSubmit({
        id: nextId(),
        aiType,
        country,
        province: prov,
        score,
        submittedAt: now,
        displayTime: display,
        highLang: aiType === "social" ? highLang : true,
        ctx,
      });
    });
    setFlash(true);
    setTimeout(() => setFlash(false), 1400);
  }

  return (
    <div style={{ background:C.surface, border:`0.5px solid ${C.border}`, borderRadius:14,
      padding:"16px 18px 14px", borderTop:`2px solid ${meta.color}`,
      boxShadow: flash ? `0 0 0 3px ${meta.color}44` : "none",
      transition:"box-shadow 0.4s ease" }}>

      {/* Header */}
      <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:14 }}>
        <div style={{ width:32, height:32, borderRadius:8, background:`${meta.color}14`,
          border:`1px solid ${meta.color}33`, display:"flex", alignItems:"center",
          justifyContent:"center", fontSize:16, flexShrink:0 }}>{meta.icon}</div>
        <div>
          <div style={{ fontSize:12, fontWeight:700, color:C.text }}>{meta.label}</div>
          <div style={{ fontSize:10, color:C.textDim, marginTop:1 }}>Independent report · multi-province</div>
        </div>
      </div>

      {/* Country selector */}
      <div style={{ marginBottom:10 }}>
        <div style={{ fontSize:10, fontWeight:700, color:C.textDim, fontFamily:"'IBM Plex Mono',monospace", marginBottom:2 }}>country</div>
        <select value={country} onChange={e=>setCountry(e.target.value)}
          style={{ padding:"5px 8px", borderRadius:6, border:`1px solid ${meta.color}44`,
            background:C.bg, color:C.text, fontSize:12, fontFamily:"'IBM Plex Mono',monospace",
            outline:"none", fontWeight:600 }}>
          {["PH","VT","TH"].map(c=><option key={c}>{c}</option>)}
        </select>
      </div>

      {/* Province checklist */}
      <ProvinceChecklist country={country} selected={provinces} onChange={setProvinces} accentColor={meta.color}/>

      {/* AI-specific context fields */}
      {aiType === "flood" && <>
        <FieldInput fieldName="basin_name" value={basinName} onChange={setBasinName} accent={meta.color} note="context"/>
        <FieldInput fieldName="discharge_cms" value={discharge} onChange={setDischarge} type="number" accent={meta.color} unit="cms"/>
        <FieldInput fieldName="threshold_cms" value={threshold} onChange={setThreshold} type="number" accent={meta.color} unit="cms"/>
        <FieldInput fieldName="forecast_hrs" value={floodHorizon} onChange={setFloodHorizon} type="number" accent={meta.color} unit="hrs"/>
        <FieldInput fieldName="severity_label" value={severityLabel} onChange={setSeverityLabel}
          options={["WATCH","ADVISORY","WARNING"]} accent={meta.color}/>
      </>}

      {aiType === "typhoon" && <>
        <FieldInput fieldName="storm_name" value={stormName} onChange={setStormName} accent={meta.color} note="context"/>
        <FieldInput fieldName="wind_speed_kmh" value={windKmh} onChange={setWindKmh} type="number" accent={meta.color} unit="km/h"/>
        <FieldInput fieldName="forecast_hrs" value={typhoonHorizon} onChange={setTyphoonHorizon} type="number" accent={meta.color} unit="hrs"/>
        <FieldInput fieldName="cross_track_err" value={cteKm} onChange={setCteKm} type="number" accent={meta.color} unit="km"/>
        <div style={{padding:"5px 8px",borderRadius:6,background:`${C.teal}10`,border:`0.5px solid ${C.teal}33`,marginBottom:8,fontSize:10}}>
          <span style={{color:C.textDim}}>Category: </span>
          <span style={{fontWeight:700,color:C.teal}}>
            {parseFloat(windKmh)<63?"TD":parseFloat(windKmh)<89?"TS":parseFloat(windKmh)<119?"Cat 1":parseFloat(windKmh)<153?"Cat 2":parseFloat(windKmh)<178?"Cat 3":parseFloat(windKmh)<209?"Cat 4":"Cat 5"}
          </span>
        </div>
      </>}

      {aiType === "social" && <>
        <FieldInput fieldName="storm_name" value={stormName} onChange={setStormName} accent={meta.color} note="context"/>
        <FieldInput fieldName="post_count" value={postCount} onChange={setPostCount} type="number" accent={meta.color}/>
        <FieldInput fieldName="dominant_label" value={domLabel} onChange={setDomLabel}
          options={["watch","advisory","warning"]} accent={meta.color}/>
        <div style={{marginBottom:8}}>
          <div style={{fontSize:10,fontWeight:700,color:C.textDim,fontFamily:"'IBM Plex Mono',monospace",marginBottom:4}}>language_resource</div>
          <div style={{display:"flex",gap:6}}>
            {[["High",true],["Low",false]].map(([lbl,val])=>(
              <button key={lbl} onClick={()=>setHighLang(val)}
                style={{flex:1,fontSize:10,fontWeight:600,padding:"4px 0",borderRadius:6,
                  border:`1px solid ${highLang===val?meta.color:C.border}`,
                  background:highLang===val?`${meta.color}14`:"transparent",
                  color:highLang===val?meta.color:C.textDim,cursor:"pointer"}}>
                {lbl} ({val?"35%":"20%"})
              </button>
            ))}
          </div>
        </div>
      </>}

      {/* Score slider */}
      <ScoreSlider value={score} onChange={setScore} color={meta.colorLt} label="score_value (independent)"/>

      {/* Submit */}
      <button onClick={handleSubmit} disabled={provinces.length === 0}
        style={{ marginTop:14, width:"100%", padding:"9px 0", borderRadius:8,
          border:`1px solid ${provinces.length ? meta.color+"88" : C.border}`,
          background: provinces.length ? `${meta.color}18` : C.surfaceHi,
          color: provinces.length ? meta.color : C.textDim,
          fontWeight:700, fontSize:12,
          cursor: provinces.length ? "pointer" : "not-allowed",
          letterSpacing:"0.04em", transition:"all 0.2s" }}>
        {flash
          ? `✓ Filed — ${provinces.length} province${provinces.length!==1?"s":""}`
          : provinces.length === 0
          ? "Select at least one province"
          : `↑ Submit Report (${provinces.length} province${provinces.length!==1?"s":""})`}
      </button>
    </div>
  );
}

// ══ REPORTS TABLE ════════════════════════════════════════════════════════════
function ExpiryBar({ submittedAt, now }) {
  const age = now - submittedAt;
  const pct = Math.max(0, 100 - (age / EXPIRY_MS) * 100);
  const color = pct > 60 ? C.green : pct > 25 ? C.amber : C.red;
  const remaining = EXPIRY_MS - age;
  const h = Math.floor(remaining / 3600000);
  const m = Math.floor((remaining % 3600000) / 60000);
  return (
    <div style={{ display:"flex", alignItems:"center", gap:6 }}>
      <div style={{ flex:1, height:3, background:"rgba(0,0,0,0.08)", borderRadius:2, overflow:"hidden" }}>
        <div style={{ height:"100%", width:`${pct}%`, background:color, borderRadius:2, transition:"width 60s linear" }}/>
      </div>
      <span style={{ fontSize:9, fontFamily:"monospace", color:C.textDim, minWidth:36 }}>
        {h > 0 ? `${h}h ${m}m` : `${m}m`}
      </span>
    </div>
  );
}

function ReportsTable({ reports, now, onClear, reviewedKeys }) {
  const [showReviewed, setShowReviewed] = useState(false);

  // A report is "used" if it was submitted before its province was reviewed
  const isUsed = r => {
    const rt = reviewedKeys.get(`${r.country}::${r.province}`);
    return rt && r.submittedAt <= rt;
  };

  const activeReports   = reports.filter(r => !isUsed(r));
  const reviewedReports = reports.filter(r =>  isUsed(r));

  // Sort + shade each group independently
  function buildRows(rpts) {
    const sorted = [...rpts].sort((a,b) => {
      const pk = r => `${r.country}::${r.province}`;
      if (pk(a) !== pk(b)) return pk(a).localeCompare(pk(b));
      return b.submittedAt - a.submittedAt;
    });
    let lastProv = null; let shade = false;
    return sorted.map(r => {
      const provKey = `${r.country}::${r.province}`;
      if (provKey !== lastProv) { shade = !shade; lastProv = provKey; }
      return { ...r, shade };
    });
  }

  const activeRows   = buildRows(activeReports);
  const reviewedRows = buildRows(reviewedReports);

  function ctxSummary(r) {
    if (!r.ctx) return "—";
    const c = r.ctx;
    if (r.aiType === "flood")   return [c.basinName, c.discharge && `${c.discharge}cms`, c.severityLabel].filter(Boolean).join(" · ");
    if (r.aiType === "typhoon") return [c.stormName, c.windKmh && `${c.windKmh}km/h`, c.typhoonHorizon && `ETA ${c.typhoonHorizon}h`].filter(Boolean).join(" · ");
    if (r.aiType === "social")  return [c.stormName, c.postCount && `${c.postCount} posts`, c.domLabel].filter(Boolean).join(" · ");
    return "—";
  }
  function ctxFull(r) {
    if (!r.ctx) return "No context";
    return Object.entries(r.ctx).map(([k,v]) => `${k}: ${v}`).join("\n");
  }

  function ReportRow({ r, used }) {
    const meta = AI_META[r.aiType];
    const tier = getTier(r.score);
    const summary = ctxSummary(r);
    const [hover, setHover] = useState(false);
    return (
      <div style={{ display:"grid", gridTemplateColumns:"80px 160px 110px 1fr 90px 100px",
        padding:"9px 18px", alignItems:"center", gap:0,
        opacity: used ? 0.38 : 1,
        background: used ? "rgba(0,0,0,0.02)" : r.shade ? C.surfaceHi+"66" : "transparent",
        borderBottom:`0.5px solid ${C.border}`,
        filter: used ? "grayscale(0.6)" : "none",
        transition:"all 0.3s" }}>
        {/* AI source */}
        <div style={{ display:"flex", alignItems:"center", gap:5 }}>
          <span style={{ fontSize:12 }}>{meta.icon}</span>
          <span style={{ fontSize:10, fontWeight:600, color: used ? C.textDim : meta.color }}>{r.aiType}</span>
        </div>
        {/* Province */}
        <div>
          <div style={{ display:"flex", alignItems:"center", gap:6 }}>
            <span style={{ fontSize:12, fontWeight:600, color: used ? C.textDim : C.text,
              textDecoration: used ? "line-through" : "none" }}>{r.province}</span>
            {used && <Tag label="used in advisory" color={C.textDim}/>}
          </div>
          <div style={{ fontSize:9, color:C.textDim }}>{r.country} · {r.displayTime}</div>
        </div>
        {/* Score bar */}
        <div>
          <div style={{ display:"flex", alignItems:"center", gap:6 }}>
            <div style={{ flex:1, height:4, background:"rgba(0,0,0,0.06)", borderRadius:2, overflow:"hidden" }}>
              <div style={{ height:"100%", width:`${Math.round(r.score*100)}%`,
                background: used ? C.textDim : (tier ? tierColor(tier) : C.textDim), borderRadius:2 }}/>
            </div>
            <span style={{ fontSize:10, fontFamily:"monospace", fontWeight:700,
              color: used ? C.textDim : (tier ? tierColor(tier) : C.textDim), minWidth:28 }}>{fmt2(r.score)}</span>
          </div>
          {tier && !used && <div style={{ marginTop:2 }}><Tag label={tier} color={tierColor(tier)}/></div>}
        </div>
        {/* Context — truncated with tooltip */}
        <div style={{ position:"relative", minWidth:0 }}
          onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}>
          <div style={{ fontSize:10, color:C.textDim, whiteSpace:"nowrap", overflow:"hidden",
            textOverflow:"ellipsis", fontFamily:"'IBM Plex Mono',monospace", cursor:"default",
            paddingRight:4 }}>{summary}</div>
          {hover && summary !== "—" && (
            <div style={{ position:"absolute", top:"100%", left:0, zIndex:50,
              background:C.text, color:"white", fontSize:10, borderRadius:8,
              padding:"8px 12px", whiteSpace:"pre", lineHeight:1.7,
              boxShadow:"0 4px 16px rgba(0,0,0,0.18)", marginTop:4,
              fontFamily:"'IBM Plex Mono',monospace", pointerEvents:"none",
              maxWidth:260 }}>
              {ctxFull(r)}
            </div>
          )}
        </div>
        {/* ID */}
        <span style={{ fontSize:10, color:C.textDim, fontFamily:"monospace" }}>{r.id}</span>
        {/* Expiry */}
        <ExpiryBar submittedAt={r.submittedAt} now={now}/>
      </div>
    );
  }

  const ColHeaders = () => (
    <div style={{ display:"grid", gridTemplateColumns:"80px 160px 110px 1fr 90px 100px", gap:0,
      padding:"6px 18px", background:C.surfaceHi, borderBottom:`0.5px solid ${C.border}`,
      fontSize:9, fontWeight:700, color:C.textDim, letterSpacing:"0.08em", textTransform:"uppercase" }}>
      <span>AI Source</span><span>Province</span><span>Score</span><span>Context</span><span>Report ID</span><span>Expires</span>
    </div>
  );

  return (
    <div style={{ background:C.surface, border:`0.5px solid ${C.borderMd}`, borderRadius:14, overflow:"hidden", marginBottom:8 }}>
      {/* Header */}
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", padding:"14px 18px", borderBottom:`0.5px solid ${C.border}` }}>
        <div>
          <div style={{ fontSize:13, fontWeight:700, color:C.text }}>Report Database</div>
          <div style={{ fontSize:10, color:C.textDim, marginTop:2 }}>
            <span style={{ color:C.green, fontWeight:600 }}>{activeReports.length} active</span>
            {reviewedReports.length > 0 && <span> · <span style={{ color:C.textDim }}>{reviewedReports.length} used in advisory</span></span>}
            <span style={{ color:C.textDim }}> · expires 6h after submission</span>
          </div>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:8 }}>
          {reviewedReports.length > 0 && (
            <button onClick={() => setShowReviewed(s => !s)}
              style={{ fontSize:10, fontWeight:600, color: showReviewed ? C.blue : C.textDim,
                background: showReviewed ? `${C.blue}12` : C.surfaceHi,
                border:`0.5px solid ${showReviewed ? C.blue+"44" : C.border}`,
                borderRadius:6, padding:"4px 10px", cursor:"pointer", transition:"all 0.2s" }}>
              {showReviewed ? "▾ hide reviewed" : `▸ show ${reviewedReports.length} reviewed`}
            </button>
          )}
          {reports.length > 0 && (
            <button onClick={onClear}
              style={{ fontSize:10, color:C.red, background:"transparent",
                border:`0.5px solid ${C.red}44`, borderRadius:6, padding:"4px 10px", cursor:"pointer" }}>
              Clear all
            </button>
          )}
        </div>
      </div>

      {reports.length === 0 ? (
        <div style={{ textAlign:"center", padding:"32px", color:C.textDim, fontSize:12 }}>
          No reports yet. Submit from any AI panel above to populate the database.
        </div>
      ) : (
        <>
          {/* Active rows — max 20, scrollable */}
          {activeRows.length > 0 ? (
            <>
              <ColHeaders/>
              <div style={{ maxHeight: 20 * 52, overflowY:"auto" }}>
                {activeRows.slice(0, 20).map(r => <ReportRow key={r.id} r={r} used={false}/>)}
                {activeRows.length > 20 && (
                  <div style={{ padding:"8px 18px", fontSize:10, color:C.textDim, textAlign:"center",
                    borderTop:`0.5px solid ${C.border}`, background:C.surfaceHi }}>
                    Showing 20 of {activeRows.length} — older rows hidden. Clear to reset.
                  </div>
                )}
              </div>
            </>
          ) : (
            <div style={{ padding:"18px", textAlign:"center", color:C.textDim, fontSize:12,
              background:C.surfaceHi, borderBottom:`0.5px solid ${C.border}` }}>
              All reports have been used in advisories.
            </div>
          )}

          {/* Reviewed rows — toggled */}
          {showReviewed && reviewedRows.length > 0 && (
            <>
              <div style={{ padding:"6px 18px", background:`${C.textDim}10`,
                borderTop:`0.5px solid ${C.border}`, borderBottom:`0.5px solid ${C.border}`,
                fontSize:9, fontWeight:700, color:C.textDim, letterSpacing:"0.08em", textTransform:"uppercase",
                display:"flex", alignItems:"center", gap:8 }}>
                <span>─</span><span>used in advisory ({reviewedRows.length})</span><span style={{flex:1,height:"0.5px",background:C.border}}/>
              </div>
              <div style={{ maxHeight: 10 * 52, overflowY:"auto" }}>
                {reviewedRows.map(r => <ReportRow key={r.id} r={r} used={true}/>)}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

// ══ PROVINCE RANKINGS ════════════════════════════════════════════════════════
function ProvinceRankings({ ranked, topProvince }) {
  if (ranked.length === 0) return (
    <div style={{ textAlign:"center", padding:"28px", color:C.textDim, fontSize:12,
      background:C.surfaceHi, borderRadius:14, border:`0.5px solid ${C.border}`, marginBottom:8 }}>
      No reports filed yet. Submit reports from the AI panels to begin pattern detection.
    </div>
  );

  return (
    <div style={{ background:C.surface, border:`0.5px solid ${C.borderMd}`, borderRadius:14, overflow:"hidden", marginBottom:8 }}>
      <div style={{ padding:"14px 18px 10px", borderBottom:`0.5px solid ${C.border}` }}>
        <div style={{ fontSize:13, fontWeight:700, color:C.text }}>Province Pattern Detection</div>
        <div style={{ fontSize:10, color:C.textDim, marginTop:2 }}>
          Ranked by fused confidence · cross-AI agreement earns +0.04 diversity bonus per additional source type
        </div>
      </div>

      {ranked.map((prov, idx) => {
        const isTop = idx === 0 && !prov.reviewed;
        const tier = prov.tier;
        const tColor = tier ? tierColor(tier) : C.textDim;
        const aiTypes = [...new Set(prov.reports.map(r=>r.aiType))];
        const hasPattern = prov.uniqueTypes >= 2;

        return (
          <div key={`${prov.country}::${prov.province}`}
            style={{ padding:"14px 18px", borderBottom:`0.5px solid ${C.border}`,
              background: isTop && tier ? tierBg(tier) : "transparent",
              borderLeft: isTop ? `4px solid ${tColor}` : `4px solid transparent`,
              opacity: prov.reviewed ? 0.4 : 1,
              filter: prov.reviewed ? "grayscale(0.7)" : "none",
              transition: "opacity 0.3s, filter 0.3s",
              position:"relative" }}>

            {isTop && tier && (
              <div style={{ position:"absolute", top:10, right:14 }}>
                <Tag label="▲ TOP TARGET" color={tColor}/>
              </div>
            )}

            <div style={{ display:"flex", alignItems:"flex-start", gap:14 }}>
              {/* Rank */}
              <div style={{ fontSize:20, fontWeight:800, fontFamily:"monospace",
                color: isTop ? tColor : C.textDim, minWidth:28, lineHeight:1, paddingTop:2 }}>
                #{idx+1}
              </div>

              {/* Main info */}
              <div style={{ flex:1 }}>
                <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:6 }}>
                  <span style={{ fontSize:14, fontWeight:800, color:C.text }}>{prov.province}</span>
                  <span style={{ fontSize:10, color:C.textDim }}>{prov.country}</span>
                  {tier && <Tag label={tier.toUpperCase()} color={tColor}/>}
                  {hasPattern && <Tag label={`${prov.uniqueTypes} AI TYPES`} color={C.teal}/>}
                  {prov.reviewed && <Tag label="REVIEWED" color={C.textDim}/>}
                </div>

                {/* Confidence bar */}
                <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:8 }}>
                  <div style={{ flex:1, height:8, background:"rgba(0,0,0,0.06)", borderRadius:4, overflow:"hidden" }}>
                    <div style={{ height:"100%", width:`${Math.round(prov.fusion*100)}%`,
                      background: isTop ? tColor : C.textDim,
                      borderRadius:4, transition:"width 0.5s cubic-bezier(0.4,0,0.2,1)" }}/>
                  </div>
                  <span style={{ fontSize:16, fontWeight:800, fontFamily:"monospace",
                    color: isTop ? tColor : C.text, minWidth:36 }}>{fmt2(prov.fusion)}</span>
                </div>

                {/* Stats row */}
                <div style={{ display:"flex", gap:16, flexWrap:"wrap" }}>
                  <div style={{ fontSize:10, color:C.textDim }}>
                    Reports: <span style={{ color:C.textMid, fontWeight:600 }}>{prov.reportCount}</span>
                  </div>
                  <div style={{ fontSize:10, color:C.textDim }}>
                    Phys avg: <span style={{ color:C.blue, fontWeight:600 }}>{prov.physAvg > 0 ? fmt2(prov.physAvg) : "—"}</span>
                  </div>
                  <div style={{ fontSize:10, color:C.textDim }}>
                    Social avg: <span style={{ color:C.purple, fontWeight:600 }}>{prov.socAvg > 0 ? fmt2(prov.socAvg) : "—"}</span>
                  </div>
                  {prov.isOverride && <Tag label="OVERRIDE" color={C.red}/>}
                </div>

                {/* AI type chips */}
                <div style={{ display:"flex", gap:5, marginTop:8, flexWrap:"wrap" }}>
                  {["flood","typhoon","social"].map(type => {
                    const active = aiTypes.includes(type);
                    const m = AI_META[type];
                    return (
                      <span key={type} style={{ fontSize:10, padding:"2px 8px", borderRadius:20,
                        background: active ? `${m.color}18` : C.surfaceHi,
                        color: active ? m.color : C.textDim,
                        border:`0.5px solid ${active ? m.color+"44" : C.border}`,
                        fontWeight: active ? 700 : 400 }}>
                        {m.icon} {type}
                      </span>
                    );
                  })}
                  {hasPattern && (
                    <span style={{ fontSize:10, padding:"2px 8px", borderRadius:20,
                      background:`${C.teal}18`, color:C.teal, border:`0.5px solid ${C.teal}44`, fontWeight:700 }}>
                      ✦ cross-AI pattern
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ══ TIER CARD ════════════════════════════════════════════════════════════════
function TierCard({tier,active}){
  const color=tierColor(tier);
  return(<div style={{border:`1px solid ${active?color:C.border}`,borderRadius:12,padding:"14px 14px 12px",background:active?tierBg(tier):"transparent",opacity:active?1:0.35,transition:"all 0.35s ease",position:"relative",overflow:"hidden"}}>{active&&<div style={{position:"absolute",top:0,left:0,right:0,height:2,background:color}}/>}<div style={{display:"flex",alignItems:"center",gap:6,marginBottom:5}}><span style={{fontSize:15}}>{tier==="Watch"?"👁":tier==="Advisory"?"🟠":"🔴"}</span><span style={{fontSize:12,fontWeight:700,color:active?color:C.textDim,letterSpacing:"0.04em"}}>{tier.toUpperCase()}</span></div><div style={{fontSize:10,color:C.textDim,fontFamily:"monospace",marginBottom:6}}>{tier==="Watch"?"0.50 – 0.64":tier==="Advisory"?"0.65 – 0.79":"≥ 0.80"}</div><div style={{fontSize:11,color:active?C.textMid:C.textDim,lineHeight:1.5}}>{tier==="Watch"&&"Monitor and prepare."}{tier==="Advisory"&&"Precautionary action."}{tier==="Warning"&&"Immediate action. Human gate active."}</div></div>);
}

// ══ CHANNEL CARD ════════════════════════════════════════════════════════════
function ChannelCard({icon,platform,lang,message}){return(<div style={{background:C.surface,border:`0.5px solid ${C.border}`,borderRadius:10,padding:"12px 14px",display:"flex",gap:10}}><span style={{fontSize:20,flexShrink:0,paddingTop:1}}>{icon}</span><div style={{flex:1,minWidth:0}}><div style={{fontSize:10,fontWeight:600,color:C.textDim,marginBottom:4}}>{platform} · {lang}</div><div style={{fontSize:11.5,color:C.textMid,lineHeight:1.6,whiteSpace:"pre-wrap",wordBreak:"break-word"}}>{message}</div></div></div>);}

// ══ REVIEW QUEUE ════════════════════════════════════════════════════════════
const OPERATORS = ["Maria Santos","Nguyen Van A","Somchai P."];
function ReviewQueue({tier,alertText,fusion,onApprove,onModify,onReject,reviewState}){
  const[sec,setSec]=useState(300);
  const[operator,setOperator]=useState(OPERATORS[0]);
  const[editText,setEditText]=useState(alertText);
  const[editing,setEditing]=useState(false);
  useEffect(()=>{setEditText(alertText);},[alertText]);
  useEffect(()=>{if(tier!=="Warning"||reviewState!=="pending"||sec<=0)return;const t=setInterval(()=>setSec(s=>Math.max(0,s-1)),1000);return()=>clearInterval(t);},[tier,reviewState,sec]);
  if(tier!=="Warning")return null;
  const m=Math.floor(sec/60),s=sec%60,urgent=sec<60&&sec>0,expired=sec===0&&reviewState==="pending";
  const sC={pending:C.amber,approved:C.green,modified:C.teal,rejected:C.red};
  const sL={pending:"AWAITING REVIEW",approved:"APPROVED — DISPATCHED",modified:"MODIFIED — DISPATCHED",rejected:"REJECTED — SUPPRESSED"};
  return(<div style={{background:C.surface,border:`1px solid ${sC[reviewState]}44`,borderRadius:14,padding:"20px 22px",marginBottom:8,borderTop:`2px solid ${sC[reviewState]}`}}><div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:16}}><div><div style={{fontSize:13,fontWeight:700,color:C.text}}>Human Review Gate</div><div style={{fontSize:10,color:C.textDim,marginTop:2}}>Warning-tier alert queued</div></div><div style={{textAlign:"right"}}><div style={{fontSize:10,fontWeight:700,color:sC[reviewState],letterSpacing:"0.08em"}}>{sL[reviewState]}</div>{reviewState==="pending"&&<div style={{fontSize:22,fontWeight:800,fontFamily:"monospace",color:expired?C.red:urgent?C.amberLt:C.text,marginTop:2}}>{expired?"EXPIRED":`${m}:${String(s).padStart(2,"0")}`}</div>}</div></div>{reviewState==="pending"&&<><div style={{display:"flex",alignItems:"center",gap:10,marginBottom:14,padding:"10px 14px",background:C.surfaceHi,borderRadius:10,border:`0.5px solid ${C.border}`}}><div style={{width:32,height:32,borderRadius:"50%",background:`${C.blue}22`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:13,fontWeight:700,color:C.blue}}>{operator.split(" ").map(w=>w[0]).join("")}</div><div style={{flex:1}}><div style={{fontSize:10,color:C.textDim,marginBottom:3}}>reviewing operator</div><select value={operator} onChange={e=>setOperator(e.target.value)} style={{background:"transparent",border:"none",color:C.text,fontSize:12,fontWeight:600,cursor:"pointer",outline:"none",width:"100%"}}>{OPERATORS.map(o=><option key={o}>{o}</option>)}</select></div><div style={{fontSize:10,color:C.textDim}}>Confidence: <span style={{color:C.text,fontWeight:600}}>{Math.round(fusion*100)}%</span></div></div><div style={{marginBottom:14}}><div style={{fontSize:10,color:C.textDim,marginBottom:6,display:"flex",justifyContent:"space-between"}}><span>alert preview</span><button onClick={()=>setEditing(e=>!e)} style={{fontSize:10,color:C.blue,background:"transparent",border:"none",cursor:"pointer",textDecoration:"underline",padding:0}}>{editing?"collapse":"edit"}</button></div>{editing?<textarea value={editText} onChange={e=>setEditText(e.target.value)} style={{width:"100%",minHeight:100,background:C.surface,border:`0.5px solid ${C.borderMd}`,borderRadius:8,color:C.text,fontSize:12,padding:"10px 12px",lineHeight:1.6,fontFamily:"monospace",resize:"vertical",outline:"none",boxSizing:"border-box"}}/>:<div style={{background:C.surface,border:`0.5px solid ${C.border}`,borderRadius:8,padding:"10px 12px",fontSize:12,color:C.textMid,lineHeight:1.6,whiteSpace:"pre-wrap",fontFamily:"monospace",maxHeight:120,overflowY:"auto"}}>{editText}</div>}</div><div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:8}}>{[{label:"✓ Approve",color:C.green,fn:()=>onApprove(operator)},{label:"✎ Modify",color:C.teal,fn:()=>{setEditing(true);onModify(operator);}},{label:"✕ Reject",color:C.red,fn:()=>onReject(operator)}].map(btn=><button key={btn.label} onClick={btn.fn} style={{padding:"9px 0",borderRadius:8,border:`1px solid ${btn.color}66`,background:`${btn.color}14`,color:btn.color,fontWeight:700,fontSize:12,cursor:"pointer"}}>{btn.label}</button>)}</div>{expired&&<div style={{marginTop:10,fontSize:11,color:C.red,textAlign:"center"}}>Review window expired — auto-suppressed.</div>}</>}{reviewState!=="pending"&&<div style={{padding:"14px",background:C.surface,borderRadius:10,textAlign:"center"}}><div style={{fontSize:13,fontWeight:700,color:sC[reviewState]}}>{reviewState==="approved"&&"✓ Dispatched"}{reviewState==="modified"&&"✎ Modified and dispatched"}{reviewState==="rejected"&&"✕ Rejected — no broadcast"}</div></div>}</div>);
}

// ══ SIMULATION BAR ══════════════════════════════════════════════════════════
function SimulationBar({ running, paused, waveIdx, simLog, speed, onSpeedChange,
                         pauseOnAlert, onPauseToggle, onStart, onStop }) {
  const wave     = SIM_SCRIPT[waveIdx % SIM_SCRIPT.length];
  const nextWave = SIM_SCRIPT[(waveIdx + 1) % SIM_SCRIPT.length];
  const dotColor = paused ? C.amber : running ? C.teal : C.textDim;
  const statusLabel = paused ? "Paused — advisory active" : running ? "Simulation Running" : "Simulation";

  return (
    <div style={{ background: paused ? `${C.amber}0a` : running ? `${C.teal}0d` : C.surfaceHi,
      border:`1px solid ${paused ? C.amber+"44" : running ? C.teal+"44" : C.border}`,
      borderRadius:14, padding:"16px 20px", marginBottom:16, transition:"all 0.3s" }}>

      {/* Header row */}
      <div style={{ display:"flex", alignItems:"center", gap:12, flexWrap:"wrap", rowGap:8 }}>
        {/* Status dot + label */}
        <div style={{ display:"flex", alignItems:"center", gap:8 }}>
          <div style={{ width:8, height:8, borderRadius:"50%", background:dotColor,
            boxShadow: running && !paused ? `0 0 0 3px ${C.teal}33` : "none",
            animation: running && !paused ? "pulse 1.5s infinite" : "none" }}/>
          <span style={{ fontSize:13, fontWeight:700, color:dotColor }}>{statusLabel}</span>
        </div>

        {/* Wave badge */}
        {running && (
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <Tag label={`WAVE ${(waveIdx % SIM_SCRIPT.length) + 1} — ${wave.label.toUpperCase()}`}
              color={paused ? C.amber : C.teal}/>
            {!paused && <span style={{ fontSize:10, color:C.textDim }}>→ next: {nextWave.label}</span>}
            {paused && <span style={{ fontSize:10, color:C.amber }}>⏸ waiting for review decision</span>}
          </div>
        )}

        <div style={{ flex:1 }}/>

        {/* Speed selector — always visible */}
        <div style={{ display:"flex", alignItems:"center", gap:6 }}>
          <span style={{ fontSize:10, color:C.textDim, fontWeight:600 }}>Speed</span>
          {[1, 10, 100].map(s => (
            <button key={s} onClick={() => onSpeedChange(s)} disabled={running}
              style={{ fontSize:10, fontWeight:700, padding:"4px 10px", borderRadius:6,
                border:`1px solid ${speed===s ? C.blue+"66" : C.border}`,
                background: speed===s ? `${C.blue}14` : "transparent",
                color: speed===s ? C.blue : C.textDim,
                cursor: running ? "not-allowed" : "pointer",
                opacity: running ? 0.5 : 1 }}>
              {s === 1 ? "1×" : s === 10 ? "10×" : "100×"}
            </button>
          ))}
        </div>

        {/* Pause on alert toggle */}
        <div style={{ display:"flex", alignItems:"center", gap:6 }}>
          <span style={{ fontSize:10, color:C.textDim }}>Pause on alert</span>
          <div onClick={() => onPauseToggle(!pauseOnAlert)}
            style={{ width:32, height:18, borderRadius:9, cursor:"pointer", position:"relative",
              background: pauseOnAlert ? C.teal : C.borderMd, transition:"background 0.2s" }}>
            <div style={{ position:"absolute", top:2, left: pauseOnAlert ? 16 : 2,
              width:14, height:14, borderRadius:"50%", background:"white",
              transition:"left 0.2s", boxShadow:"0 1px 3px rgba(0,0,0,0.2)" }}/>
          </div>
        </div>

        {/* Start / Stop */}
        <button onClick={running ? onStop : onStart}
          style={{ padding:"8px 20px", borderRadius:8, fontWeight:700, fontSize:12,
            cursor:"pointer", letterSpacing:"0.04em",
            background: running ? `${C.red}18` : C.teal,
            color: running ? C.red : "white",
            border: running ? `1px solid ${C.red}44` : "none",
            transition:"all 0.2s" }}>
          {running ? "⏹ Stop" : "▶ Start Simulation"}
        </button>
      </div>

      {/* Speed legend when stopped */}
      {!running && (
        <div style={{ display:"flex", gap:16, marginTop:10, fontSize:10, color:C.textDim }}>
          <span>💧🌀 every <b style={{color:C.text}}>{Math.round(360/speed)}s</b> (6 min ÷ {speed}×)</span>
          <span>📡 every <b style={{color:C.text}}>{Math.round(60/speed)}s</b> (1 min ÷ {speed}×)</span>
        </div>
      )}

      {/* Live log */}
      {running && simLog.length > 0 && (
        <div style={{ borderTop:`0.5px solid ${paused ? C.amber+"44" : C.teal+"33"}`, paddingTop:12, marginTop:12 }}>
          <div style={{ fontSize:9, fontWeight:700, color:C.textDim, letterSpacing:"0.1em",
            textTransform:"uppercase", marginBottom:8 }}>Live Dispatch Log</div>
          <div style={{ display:"flex", flexDirection:"column", gap:6, maxHeight:140, overflowY:"auto" }}>
            {simLog.map((entry, i) => (
              <div key={i} style={{ background:C.bg, borderRadius:8, padding:"8px 12px",
                border:`0.5px solid ${C.border}`, opacity: Math.max(0.2, 1 - i * 0.12) }}>
                <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:4 }}>
                  <Tag label={`Wave ${entry.wave}`} color={C.teal}/>
                  <span style={{ fontSize:10, fontWeight:600, color:C.textMid }}>{entry.label}</span>
                  <span style={{ fontSize:9, color:C.textDim, marginLeft:"auto", fontFamily:"monospace" }}>{entry.time}</span>
                </div>
                <div style={{ display:"flex", flexWrap:"wrap", gap:4 }}>
                  {entry.entries.map((e, j) => (
                    <span key={j} style={{ fontSize:9, padding:"1px 7px", borderRadius:10,
                      background:C.surfaceHi, color:C.textMid, border:`0.5px solid ${C.border}`,
                      fontFamily:"monospace" }}>{e}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ══ PROVINCE MAP ════════════════════════════════════════════════════════════
const SEA_BOUNDS = [[5, 95], [23, 128]]; // covers Philippines, Vietnam, Thailand

function ProvinceMap({ ranked }) {
  const active = ranked.filter(p => !p.reviewed && p.fusion > 0);

  // Scale fusion to marker radius (px)
  const markerSize = (fusion) => Math.round(8 + fusion * 18);

  // Build markers for all active provinces that have coords
  const markers = active
    .map(p => ({ ...p, coords: PROVINCE_COORDS[p.province] }))
    .filter(p => p.coords);

  const mapElRef = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);
  const [leafletReady, setLeafletReady] = useState(typeof window !== "undefined" && !!window.L);

  // Load Leaflet (CSS + JS) from CDN once
  useEffect(() => {
    if (window.L) { setLeafletReady(true); return; }
    if (!document.getElementById("leaflet-css")) {
      const link = document.createElement("link");
      link.id = "leaflet-css";
      link.rel = "stylesheet";
      link.href = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css";
      document.head.appendChild(link);
    }
    let script = document.getElementById("leaflet-js");
    if (!script) {
      script = document.createElement("script");
      script.id = "leaflet-js";
      script.src = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js";
      script.async = true;
      document.body.appendChild(script);
    }
    const handleLoad = () => setLeafletReady(true);
    if (window.L) setLeafletReady(true);
    else script.addEventListener("load", handleLoad);
    return () => script.removeEventListener("load", handleLoad);
  }, []);

  // Initialize the map once Leaflet is ready
  useEffect(() => {
    if (!leafletReady || !mapElRef.current || mapRef.current) return;
    const L = window.L;
    const map = L.map(mapElRef.current, { scrollWheelZoom: false });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 18,
    }).addTo(map);
    map.fitBounds(SEA_BOUNDS);
    layerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
  }, [leafletReady]);

  // Update markers whenever the ranked list changes
  useEffect(() => {
    if (!mapRef.current || !layerRef.current || !window.L) return;
    const L = window.L;
    const layer = layerRef.current;
    layer.clearLayers();
    markers.forEach((m, i) => {
      const color = m.tier ? tierColor(m.tier) : C.textDim;
      const r = markerSize(m.fusion);
      const isTop = i === 0;
      if (isTop) {
        L.circleMarker([m.coords.lat, m.coords.lng], {
          radius: r + 10, color: "transparent", fillColor: color, fillOpacity: 0.18,
        }).addTo(layer);
      }
      L.circleMarker([m.coords.lat, m.coords.lng], {
        radius: r, color: "#fff", weight: 2, fillColor: color, fillOpacity: 0.85,
      }).bindTooltip(
        `${m.province} (${m.country}) — conf ${fmt2(m.fusion)}${m.tier ? " · " + m.tier : ""}`,
        { direction: "top", offset: [0, -r] }
      ).addTo(layer);
    });
  }, [markers]);

  return (
    <div style={{ background:C.surface, border:`0.5px solid ${C.borderMd}`, borderRadius:14,
      overflow:"hidden", marginBottom:8 }}>
      {/* Header */}
      <div style={{ padding:"14px 18px 10px", borderBottom:`0.5px solid ${C.border}`,
        display:"flex", justifyContent:"space-between", alignItems:"center" }}>
        <div>
          <div style={{ fontSize:13, fontWeight:700, color:C.text }}>Province Impact Map</div>
          <div style={{ fontSize:10, color:C.textDim, marginTop:2 }}>
            Active provinces ranked by confidence · size = intensity · live OpenStreetMap
          </div>
        </div>
        <div style={{ display:"flex", gap:8 }}>
          {[["Warning","red",C.red],["Advisory","orange",C.amberLt],["Watch","yellow",C.amber]].map(([label,,,color]) => (
            <div key={label} style={{ display:"flex", alignItems:"center", gap:4, fontSize:10, color:C.textDim }}>
              <div style={{ width:8, height:8, borderRadius:"50%",
                background: label==="Warning"?C.red:label==="Advisory"?C.amberLt:C.amber }}/>
              {label}
            </div>
          ))}
        </div>
      </div>

      {/* Map + sidebar */}
      <div style={{ display:"grid", gridTemplateColumns: markers.length ? "1fr 220px" : "1fr" }}>
        {/* Live map */}
        <div style={{ height:340, position:"relative", background:"#DCEBFB" }}>
          <div ref={mapElRef} style={{ position:"absolute", top:0, left:0, width:"100%", height:"100%" }}/>
          {!leafletReady && (
            <div style={{ position:"absolute", inset:0, display:"flex", alignItems:"center",
              justifyContent:"center", fontSize:12, color:C.textDim }}>
              Loading map…
            </div>
          )}
          {leafletReady && markers.length === 0 && (
            <div style={{ position:"absolute", left:10, bottom:10, fontSize:11, color:C.textDim,
              background:"rgba(255,255,255,0.85)", borderRadius:8, padding:"6px 10px",
              border:`0.5px solid ${C.border}` }}>
              No active province reports — showing PH / Vietnam / Thailand overview.
            </div>
          )}
        </div>

        {/* Ranked sidebar */}
        {markers.length > 0 && (
        <div style={{ borderLeft:`0.5px solid ${C.border}`, overflowY:"auto", maxHeight:340 }}>
          {markers.map((m, i) => {
            const tColor = m.tier ? tierColor(m.tier) : C.textDim;
            const isTop = i === 0;
            return (
              <div key={m.province}
                style={{ padding:"10px 14px", borderBottom:`0.5px solid ${C.border}`,
                  background: isTop ? tierBg(m.tier) : "transparent" }}>
                <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:4 }}>
                  <div style={{ width:10, height:10, borderRadius:"50%", flexShrink:0,
                    background: tColor,
                    boxShadow: isTop ? `0 0 0 3px ${tColor}33` : "none" }}/>
                  <span style={{ fontSize:11, fontWeight:700, color:C.text }}>{m.province}</span>
                  {isTop && <Tag label="#1" color={tColor}/>}
                </div>
                {/* Confidence bar */}
                <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:4 }}>
                  <div style={{ flex:1, height:4, background:"rgba(0,0,0,0.06)", borderRadius:2, overflow:"hidden" }}>
                    <div style={{ height:"100%", width:`${Math.round(m.fusion*100)}%`,
                      background:tColor, borderRadius:2, transition:"width 0.4s ease" }}/>
                  </div>
                  <span style={{ fontSize:10, fontFamily:"monospace", fontWeight:700,
                    color:tColor, minWidth:28 }}>{fmt2(m.fusion)}</span>
                </div>
                <div style={{ display:"flex", gap:5, flexWrap:"wrap" }}>
                  {m.tier && <Tag label={m.tier} color={tColor}/>}
                  <span style={{ fontSize:9, color:C.textDim }}>{m.reportCount} report{m.reportCount!==1?"s":""} · {m.uniqueTypes} AI type{m.uniqueTypes!==1?"s":""}</span>
                </div>
              </div>
            );
          })}
        </div>
        )}
      </div>
    </div>
  );
}

// ══ ENGINE VIEW ══════════════════════════════════════════════════════════════
export default function SEABeacon({ selectedProvince, onRankedUpdate, hideImpactMap = false }) {
  const [reports, setReports] = useState([]);
  const [showPanels, setShowPanels] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [reviewedKeys, setReviewedKeys] = useState(new Map()); // provinceKey -> reviewedAt timestamp
  const [reviewStates, setReviewStates] = useState({}); // key -> "pending"|"approved"|"modified"|"rejected"
  const [approved, setApproved] = useState(false);
  const alertIdRef = useRef(1);
  const [logEntries, setLogEntries] = useState([]);

  // Tick every 30s to update expiry bars and purge expired records
  useEffect(() => {
    const t = setInterval(() => {
      setNow(Date.now());
      setReports(rs => rs.filter(r => Date.now() - r.submittedAt < EXPIRY_MS));
    }, 30000);
    return () => clearInterval(t);
  }, []);

  const handleSubmit = useCallback((report) => {
    setReports(rs => [...rs, report]);
  }, []);

  // ranked/tier must be declared before simulation effects that reference tier
  const ranked = fuseReports(reports, now, reviewedKeys)
  useEffect(() => { onRankedUpdate?.(ranked) }, [JSON.stringify(ranked)])
  const top = ranked.find(p => !p.reviewed) ?? null;
  const fusion = top ? top.fusion : 0;
  const tier = top ? top.tier : null;
  const topKey = top ? top.key : null;

  // ── Simulation state ──────────────────────────────────────────────────────
  const [simRunning,    setSimRunning]   = useState(false);
  const [simWaveIdx,    setSimWaveIdx]   = useState(0);
  const [simLog,        setSimLog]       = useState([]);
  const [simSpeed,      setSimSpeed]     = useState(1);    // 1 | 10 | 100
  const [simPauseAlert, setSimPauseAlert]= useState(true); // pause when advisory generated
  const [simPaused,     setSimPaused]    = useState(false);// currently paused by alert
  const simPhysRef   = useRef(null);
  const simSocRef    = useRef(null);
  const simWaveRef   = useRef(0);
  const simSpeedRef  = useRef(1);   // ref mirror for use inside intervals
  const simPauseRef  = useRef(true);// ref mirror
  const simPausedRef = useRef(false);
  const prevTierRef  = useRef(null);

  function fireSimReports(types) {
    const waveIdx = simWaveRef.current % SIM_SCRIPT.length;
    const wave    = SIM_SCRIPT[waveIdx];
    const now     = Date.now();
    const display = tsDate();
    const fired   = [];

    types.forEach(type => {
      const spec = wave[type];
      spec.provinces.forEach(prov => {
        const score = simScore(spec.scoreRange);
        // Build rich context so the report table and advisory text have real data
        const ctx = { ...spec.ctx };
        if (type === "flood") {
          // Slightly vary discharge per province for realism
          const base = parseInt(ctx.discharge) + Math.round((Math.random()-0.5)*200);
          ctx.discharge = String(Math.max(200, base));
        }
        if (type === "typhoon") {
          // Vary wind speed slightly
          const base = parseInt(ctx.windKmh) + Math.round((Math.random()-0.5)*20);
          ctx.windKmh = String(Math.max(60, base));
        }
        if (type === "social") {
          // Vary post count slightly
          const base = parseInt(ctx.postCount) + Math.round(Math.random()*10);
          ctx.postCount = String(base);
        }
        handleSubmit({
          id: nextId(),
          aiType:      type,
          country:     "PH",
          province:    prov,
          score,
          submittedAt: now,
          displayTime: display,
          highLang:    type === "social" ? spec.ctx.highLang : true,
          ctx,
          simulated:   true,
        });
        fired.push(`${type} → ${prov} (${score.toFixed(2)})`);
      });
    });

    setSimLog(prev => [{
      time: display,
      wave: waveIdx + 1,
      label: wave.label,
      entries: fired,
    }, ...prev].slice(0, 20));

    // Advance wave only when physical AIs fire (every 6 min)
    if (types.includes("flood")) {
      simWaveRef.current = simWaveRef.current + 1;
      setSimWaveIdx(w => w + 1);
    }
  }

  // Keep speed + pause refs in sync
  useEffect(() => { simSpeedRef.current  = simSpeed;      }, [simSpeed]);
  useEffect(() => { simPauseRef.current  = simPauseAlert; }, [simPauseAlert]);

  // Watch tier changes — pause when alert generated, resume when cleared
  useEffect(() => {
    if (!simRunning) return;
    if (!simPauseRef.current) return;
    const currentTier = tier;
    const prev = prevTierRef.current;
    // New advisory appeared → pause only on Warning
    if (currentTier === "Warning" && prev !== "Warning") {
      simPausedRef.current = true;
      setSimPaused(true);
      clearInterval(simSocRef.current);
      clearTimeout(simPhysRef.current);
      clearInterval(simPhysRef.current);
    }
    // Warning cleared (reviewed down) → resume
    if (prev === "Warning" && currentTier !== "Warning" && simPausedRef.current) {
      simPausedRef.current = false;
      setSimPaused(false);
      scheduleSim();
    }
    prevTierRef.current = currentTier;
  }, [tier, simRunning]);

  function socMs()  { return 60000  / simSpeedRef.current; }
  function physMs() { return 360000 / simSpeedRef.current; }

  function scheduleSim() {
    // AI-3 every 1 min (speed-adjusted)
    simSocRef.current = setInterval(() => {
      if (!simPausedRef.current) fireSimReports(["social"]);
    }, socMs());
    // AI-1 + AI-2 every 6 min (speed-adjusted)
    simPhysRef.current = setTimeout(() => {
      if (!simPausedRef.current) fireSimReports(["flood", "typhoon", "social"]);
      simPhysRef.current = setInterval(() => {
        if (!simPausedRef.current) fireSimReports(["flood", "typhoon", "social"]);
      }, physMs());
    }, physMs());
  }

  function startSim() {
    setSimRunning(true);
    setSimPaused(false);
    simPausedRef.current = false;
    simWaveRef.current = 0;
    setSimWaveIdx(0);
    setSimLog([]);
    prevTierRef.current = null;
    // AI-3 fires immediately
    fireSimReports(["social"]);
    scheduleSim();
  }

  function stopSim() {
    setSimRunning(false);
    setSimPaused(false);
    simPausedRef.current = false;
    clearInterval(simSocRef.current);
    clearTimeout(simPhysRef.current);
    clearInterval(simPhysRef.current);
  }

  useEffect(() => () => { stopSim(); }, []);

  // reviewState resets to "pending" when new reports arrive after the last review.
  // This fixes the Wave 2 bug: same province resubmitted after rejection/approval.
  const reviewState = (() => {
    if (!topKey) return "pending";
    const lastReviewTime = reviewedKeys.get(topKey);
    if (!lastReviewTime) return "pending";
    const hasNewerReports = top && top.reports.some(r => r.submittedAt > lastReviewTime);
    if (hasNewerReports) return "pending";
    return reviewStates[topKey] ?? "pending";
  })();

  // Build alert text from top province
  const alertText = (() => {
    if (!tier || !top) return "";
    const loc = `${top.province}, ${top.country}`;
    const conf = Math.round(fusion * 100);
    const stormCtx = top.reports.find(r => r.ctx?.stormName)?.ctx?.stormName ?? "Unknown Storm";
    const etaCtx = top.reports.find(r => r.ctx?.typhoonHorizon)?.ctx?.typhoonHorizon ?? "?";
    if (tier === "Warning")  return `⚠ SEABEACON WARNING\nImpact zone: ${loc}\nConf: ${conf}% · ${top.reportCount} reports from ${top.uniqueTypes} AI type(s)\nStorm: ${stormCtx} · ETA: ${etaCtx}h\n\nFollow evacuation orders from your local DRRM office. Early aggregated advisory — NOT an official evacuation order.`;
    if (tier === "Advisory") return `🟠 SEABEACON ADVISORY\nMonitor: ${loc} · Conf: ${conf}%\n${top.reportCount} reports · ${top.uniqueTypes} AI type(s) converging\n\nPrepare supplies. Follow PAGASA/NDRRMC. Early advisory.`;
    return `👁 SEABEACON WATCH\nMonitoring: ${loc} · Conf: ${conf}%\n${top.reportCount} reports filed\n\nNo action required yet. Monitor official channels.`;
  })();

  function markReviewed(key, action) {
    const reviewedAt = Date.now();
    // Always overwrite the timestamp so new post-review reports are correctly detected
    setReviewedKeys(prev => new Map([...prev, [key, reviewedAt]]));
    // Store the decision; reviewState derivation above will override with "pending"
    // if newer reports arrive after this timestamp
    setReviewStates(prev => ({ ...prev, [key]: action }));
  }

  function addLog(action, operator) {
    const id = `SB-${String(alertIdRef.current++).padStart(4,"0")}`;
    setLogEntries(p => [...p, { id, action, operator, tier, confidence: Math.round(fusion*100), time: ts(), province: top?.province }]);
  }

  return (
    <div style={{ background:C.bg, minHeight:"100vh", fontFamily:"'DM Sans','Segoe UI',sans-serif", color:C.text }}>
      {/* Nav */}
      <div style={{ borderBottom:`1px solid ${C.border}`, background:C.bg, position:"sticky", top:0, zIndex:100 }}>
        <div style={{ maxWidth:1100, margin:"0 auto", padding:"0 24px", display:"flex", alignItems:"center" }}>
          <div style={{ display:"flex", alignItems:"center", gap:8, padding:"14px 0", marginRight:24 }}>
            <div style={{ width:8, height:8, borderRadius:"50%", background:C.teal }}/>
            <span style={{ fontSize:13, fontWeight:800, color:C.text }}>SEABeacon</span>
            <span style={{ fontSize:10, color:C.textDim }}>CardinalMu ASEAN</span>
          </div>
          <div style={{ flex:1 }}/>
          <div style={{ display:"flex", gap:8 }}>
            <Tag label="Multi-Report Engine" color={C.teal}/>
            {reports.length > 0 && <Tag label={`${reports.length} live report${reports.length!==1?"s":""}`} color={C.green}/>}
          </div>
        </div>
      </div>

      <div style={{ maxWidth:1100, margin:"0 auto", padding:"28px 24px 56px" }}>
        <div style={{ marginBottom:20 }}>
          <h2 style={{ fontSize:20, fontWeight:800, color:C.text, margin:"0 0 4px" }}>Live Multi-Report Engine</h2>
          <p style={{ fontSize:12, color:C.textDim, margin:0 }}>
            Each AI panel submits independently to a shared report database. The confidence engine detects patterns when multiple AIs converge on the same province.
          </p>
        </div>

        {/* Simulation Bar */}
        <SimulationBar
          running={simRunning}
          paused={simPaused}
          waveIdx={simWaveIdx}
          simLog={simLog}
          speed={simSpeed}
          onSpeedChange={s => { simSpeedRef.current = s; setSimSpeed(s); }}
          pauseOnAlert={simPauseAlert}
          onPauseToggle={v => { simPauseRef.current = v; setSimPauseAlert(v); }}
          onStart={startSim}
          onStop={stopSim}
        />

        {/* AI Input Panels — collapsible */}
        <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom: showPanels ? 10 : 8 }}>
          <div style={{ fontSize:10, fontWeight:700, letterSpacing:"0.12em", color:C.textDim, textTransform:"uppercase", display:"flex", alignItems:"center", gap:8 }}>
            <div style={{ flex:"0 0 auto", height:"0.5px", width:40, background:C.border }}/>
            AI report submission
            <div style={{ height:"0.5px", width:40, background:C.border }}/>
          </div>
          <button onClick={() => setShowPanels(s => !s)}
            style={{ fontSize:10, fontWeight:600, padding:"4px 12px", borderRadius:6,
              border:`0.5px solid ${C.border}`, background: showPanels ? C.surfaceHi : C.bg,
              color: showPanels ? C.textMid : C.textDim, cursor:"pointer" }}>
            {showPanels ? "▾ hide manual inputs" : "▸ show manual inputs"}
          </button>
        </div>
        {showPanels && (
          <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:12, marginBottom:8 }}>
            <AIInputPanel aiType="flood"   onSubmit={handleSubmit}/>
            <AIInputPanel aiType="typhoon" onSubmit={handleSubmit}/>
            <AIInputPanel aiType="social"  onSubmit={handleSubmit}/>
          </div>
        )}

        <Arrow/>

        {/* Report Database Table */}
        <SectionLabel>Report database — live records</SectionLabel>
        <ReportsTable reports={reports} now={now} onClear={() => setReports([])} reviewedKeys={reviewedKeys}/>

        <Arrow/>

        {/* Province Rankings / Pattern Detection */}
        <SectionLabel>Pattern detection — province rankings</SectionLabel>
        <ProvinceRankings ranked={ranked} topProvince={top?.province}/>

        {/* Province Impact Map */}
        {!hideImpactMap && <ProvinceImpactMap markers={markers} ranked={ranked} />}
        <Arrow/>

        {/* Confidence Engine */}
        <SectionLabel>Confidence scoring engine — top province</SectionLabel>
        {top ? (
          <div style={{ background:C.surface, border:`0.5px solid ${C.borderMd}`, borderRadius:14, padding:"20px 22px", marginBottom:8, borderTop:`2px solid ${C.teal}` }}>
            <div style={{ display:"flex", gap:24, alignItems:"flex-start" }}>
              <div style={{ flexShrink:0, textAlign:"center", minWidth:110 }}>
                <div style={{ fontSize:52, fontWeight:800, fontFamily:"monospace", color:tier?tierColor(tier):C.textDim, lineHeight:1, letterSpacing:"-0.03em", transition:"color 0.4s" }}>{fmt2(fusion)}</div>
                <div style={{ fontSize:11, color:C.textDim, marginTop:4 }}>combined score</div>
                <div style={{ marginTop:6, fontSize:12, fontWeight:700, color:C.text }}>{top.province}</div>
                <div style={{ marginTop:8, display:"inline-block", fontSize:11, fontWeight:700, padding:"3px 12px", borderRadius:20, background:tier?`${tierColor(tier)}14`:C.surfaceHi, color:tier?tierColor(tier):C.textDim, border:`1px solid ${tier?tierColor(tier)+"44":C.border}` }}>
                  {tier?tier.toUpperCase():"BELOW THRESHOLD"}
                </div>
              </div>
              <div style={{ flex:1 }}>
                <AnimatedBar pct={Math.round(top.physAvg*100)} color={C.blue} label={`physical avg (${top.reports.filter(r=>AI_META[r.aiType].kind==="physical").length} physical reports)`} value={fmt2(top.physAvg||0)}/>
                <AnimatedBar pct={Math.round(top.socAvg*100)} color={C.purple} label={`social avg (${top.reports.filter(r=>AI_META[r.aiType].kind==="social").length} social reports)`} value={fmt2(top.socAvg||0)}/>
                <AnimatedBar pct={Math.round(fusion*100)} color={tier?tierColor(tier):C.teal} label="fused confidence (with diversity bonus)" value={fmt2(fusion)}/>
                <div style={{ fontSize:10, color:C.textDim, fontFamily:"monospace", marginTop:10, paddingTop:10, borderTop:`0.5px solid ${C.border}`, lineHeight:1.8 }}>
                  {top.uniqueTypes} unique AI type{top.uniqueTypes!==1?"s":""} · diversity bonus: +{fmt2(Math.max(0,top.uniqueTypes-1)*0.04)}
                  {top.isOverride && " · PHYSICAL OVERRIDE ACTIVE"}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div style={{ textAlign:"center", padding:"28px", color:C.textDim, fontSize:12, background:C.surfaceHi, borderRadius:14, border:`0.5px solid ${C.border}`, marginBottom:8 }}>
            No reports in database. Submit reports above to activate the confidence engine.
          </div>
        )}

        <Arrow/>

        {/* Tier protocol */}
        <SectionLabel>Three-tier alert protocol</SectionLabel>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:10, marginBottom:8 }}>
          <TierCard tier="Watch" active={tier==="Watch"}/>
          <TierCard tier="Advisory" active={tier==="Advisory"}/>
          <TierCard tier="Warning" active={tier==="Warning"}/>
        </div>
        {!tier && <div style={{ textAlign:"center", padding:"14px", color:C.textDim, fontSize:12, background:C.surfaceHi, borderRadius:10, border:`0.5px solid ${C.border}`, marginBottom:8 }}>Confidence below 0.50 — no advisory generated.</div>}

        <Arrow/>

        {/* Advisory output */}
        <SectionLabel>Aggregated advisory output</SectionLabel>
        {tier && top ? (
          <div style={{ background:C.surface, border:`0.5px solid ${C.borderMd}`, borderRadius:14, padding:"18px 20px", marginBottom:8, borderTop:`2px solid ${tierColor(tier)}` }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:14 }}>
              <div>
                <div style={{ fontSize:13, fontWeight:700, color:C.text }}>SEABeacon Aggregated Advisory</div>
                <div style={{ fontSize:10, color:C.textDim, marginTop:2 }}>
                  {top.province}, {top.country} · {top.reportCount} reports · {top.uniqueTypes} AI source type(s) · Auto-generated
                </div>
              </div>
              <Tag label={tier.toUpperCase()} color={tierColor(tier)}/>
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8 }}>
              <ChannelCard icon="💬" platform="Messenger / Telegram" lang="Filipino · English" message={alertText}/>
              <ChannelCard icon="💚" platform="LINE" lang="Thai · English" message={alertText}/>
              <ChannelCard icon="🟦" platform="Zalo" lang="Vietnamese · English" message={alertText}/>
              <div style={{ background:C.surface, border:`0.5px solid ${C.border}`, borderRadius:10, padding:"12px 14px", display:"flex", gap:10 }}>
                <span style={{ fontSize:20 }}>📱</span>
                <div>
                  <div style={{ fontSize:10, fontWeight:600, color:C.textDim, marginBottom:4 }}>SMS · 160-char</div>
                  <div style={{ fontSize:11, color:C.textMid, fontFamily:"monospace", lineHeight:1.6 }}>
                    {`[SEABEACON ${tier.toUpperCase()}] ${top.province}. Conf ${Math.round(fusion*100)}%. ${top.reportCount} AI reports. Follow DRRM orders. Early advisory only.`}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div style={{ textAlign:"center", padding:"28px", color:C.textDim, fontSize:13, background:C.surfaceHi, borderRadius:14, border:`0.5px solid ${C.border}`, marginBottom:8 }}>
            No advisory to generate. Confidence below threshold.
          </div>
        )}

        <Arrow/>

        {/* Review gate */}
        <SectionLabel>Human review gate</SectionLabel>
        {tier === "Warning" ? (
          <ReviewQueue key={topKey} tier={tier} alertText={alertText} fusion={fusion} reviewState={reviewState}
            onApprove={(op)=>{markReviewed(topKey,"approved");setApproved(true);addLog("approved",op);}}
            onModify={(op)=>{markReviewed(topKey,"modified");setApproved(true);addLog("modified",op);}}
            onReject={(op)=>{markReviewed(topKey,"rejected");setApproved(false);addLog("rejected",op);}}/>
        ) : (
          <div style={{ textAlign:"center", padding:"18px", color:C.textDim, fontSize:12, background:C.surfaceHi, borderRadius:14, border:`0.5px solid ${C.border}`, marginBottom:8 }}>
            {tier ? `${tier}-tier alerts broadcast automatically — human gate only at Warning.` : "No active alert — human gate idle."}
          </div>
        )}

        <Arrow/>

        {/* Dispatch Log */}
        <SectionLabel>Audit dispatch log</SectionLabel>
        <div style={{ background:C.surface, border:`0.5px solid ${C.borderMd}`, borderRadius:14, padding:"18px 20px" }}>
          <div style={{ fontSize:13, fontWeight:700, color:C.text, marginBottom:10 }}>Audit Log</div>
          {logEntries.length === 0 ? (
            <div style={{ textAlign:"center", padding:"20px", color:C.textDim, fontSize:12, background:C.surfaceHi, borderRadius:10 }}>
              No entries yet.
            </div>
          ) : (
            <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
              {[...logEntries].reverse().map((e,i) => (
                <div key={i} style={{ padding:"10px 14px", borderRadius:10, background:C.surfaceHi, border:`0.5px solid ${C.border}`, borderLeft:`3px solid ${e.action==="approved"?C.green:e.action==="modified"?C.teal:C.red}` }}>
                  <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4 }}>
                    <div style={{ display:"flex", gap:6 }}>
                      <Tag label={e.action.toUpperCase()} color={e.action==="approved"?C.green:e.action==="modified"?C.teal:C.red}/>
                      {e.tier && <Tag label={e.tier} color={tierColor(e.tier)}/>}
                    </div>
                    <span style={{ fontSize:10, color:C.textDim, fontFamily:"monospace" }}>{e.time}</span>
                  </div>
                  <div style={{ fontSize:11, color:C.textDim }}>
                    {e.operator} · {e.province} · {e.id} · Conf {e.confidence}%
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div style={{ borderTop:`1px solid ${C.border}`, padding:"16px 24px", textAlign:"center", fontSize:10, color:C.textDim, letterSpacing:"0.06em" }}>
        SEABEACON · CARDINALMU ASEAN · FOR DEMO PURPOSES
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700;800&family=IBM+Plex+Mono:wght@400;600;700&display=swap');
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        *{box-sizing:border-box;} button{font-family:inherit;} textarea{font-family:monospace;}
        select option{background:#F7F9FC;color:#0F1F35;}
        input[type=number]{-moz-appearance:textfield;}
        input[type=number]::-webkit-outer-spin-button,input[type=number]::-webkit-inner-spin-button{-webkit-appearance:none;margin:0;}
        input[type=range]{width:100%;}
      `}</style>
    </div>
  );
}
