import React, { useState, useEffect, useRef, useMemo, useCallback, memo } from 'react'
import * as d3 from 'd3'

const C = {
  surface: "#F7F9FC",
  border:  "rgba(0,0,0,0.08)",
  text:    "#0F1F35",
  textDim: "#7A92AD",
  amber:   "#B87000",
  amberLt: "#E8A020",
  red:     "#C0282A",
}

function tierFill(tier) {
  if (tier === "Warning")  return "#C0282A"
  if (tier === "Advisory") return "#E8A020"
  if (tier === "Watch")    return "#B87000"
  return null
}

// ── Legend row swatch + label ────────────────────────────────────────────────
function LegendRow({ color, label, shape = 'box' }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, margin: '2px 0' }}>
      <span style={{
        width: shape === 'dot' ? 10 : 12,
        height: shape === 'dot' ? 10 : 12,
        borderRadius: shape === 'dot' ? '50%' : 3,
        background: color,
        opacity: shape === 'dot' ? 0.6 : 1,
        border: `1px solid ${color}`,
        flexShrink: 0,
      }} />
      <span>{label}</span>
    </div>
  )
}

function norm(s) {
  return s?.toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/\s+/g, "")
    .replace(/[^a-z0-9]/g, "") ?? ""
}

const LAYERS = [
  { url: '/gadm41_MMR_1.json', background: true },
  { url: '/gadm41_LAO_1.json', background: true },
  { url: '/gadm41_KHM_1.json', background: true },
  { url: '/gadm41_MYS_1.json', background: true },
  { url: '/gadm41_SGP_1.json', background: true },
  { url: '/gadm41_BRN_1.json', background: true },
  { url: '/gadm41_IDN_1.json', background: true },
  { url: '/gadm41_PHL_1.json', background: false },
  { url: '/gadm41_VNM_1.json', background: false },
  { url: '/gadm41_THA_1.json', background: false },
  { url: '/gadm41_CHN_1.json', background: false },
  { url: '/gadm41_JPN_1.json', background: false },
  { url: '/gadm41_TWN_1.json', background: false },
]

// Non-ASEAN countries that are display-only (no interaction)
const NON_ASEAN = new Set(['China', 'Japan', 'Taiwan'])

let _geoCache = null
let _geoPromise = null

function loadGeoData() {
  if (_geoCache) return Promise.resolve(_geoCache)
  if (_geoPromise) return _geoPromise
  _geoPromise = Promise.all(
    LAYERS.map(layer =>
      fetch(layer.url)
        .then(r => {
          const contentType = r.headers.get('content-type') || ''
          if (!r.ok || !contentType.includes('json')) {
            throw new Error(`Bad response for ${layer.url}: ${r.status} ${contentType || '(no content-type)'}`)
          }
          return r.json()
        })
        // Tag isNonASEAN at load time so the render loop never has to check it
        .then(json => ({
          background: layer.background,
          features: json.features.map(f => ({
            ...f,
            properties: {
              ...f.properties,
              isNonASEAN: NON_ASEAN.has(f.properties.COUNTRY),
            }
          }))
        }))
        .catch(err => {
          console.error(err.message)
          return { background: layer.background, features: [] }
        })
    )
  ).then(results => {
    const allFeatures = results.flatMap(r =>
      r.features.map(f => ({
        ...f,
        properties: { ...f.properties, isBackground: r.background }
      }))
    )
    _geoCache = { type: 'FeatureCollection', features: allFeatures }
    return _geoCache
  })
  return _geoPromise
}

// ── Tooltip — updates via direct DOM mutation, zero React re-renders ──────────
// The ref is passed down from MapPanel. Mouse handlers write to it directly
// instead of calling setState, so hovering never triggers a React render cycle.
const ProvinceTooltip = memo(function ProvinceTooltip({ tooltipRef }) {
  return (
    <div
      ref={tooltipRef}
      style={{
        display: 'none',          // shown/hidden by imperative toggle
        position: 'absolute',
        background: 'rgba(15,31,53,0.9)', color: 'white',
        padding: '5px 10px', borderRadius: 6, fontSize: 11,
        pointerEvents: 'none', whiteSpace: 'nowrap', zIndex: 10,
        left: 0, top: 0,
      }}
    />
  )
})

// ── Single province path, memoized ───────────────────────────────────────────
// Callbacks are stable Map entries (see provinceCallbacks below), so the memo
// comparator can safely skip them — identity never changes between renders.
const ProvincePath = memo(function ProvincePath({
  d, fill, isSelected, onClick, onHoverEnter, onHoverLeave,
}) {
  return (
    <path
      d={d}
      fill={fill}
      stroke={isSelected ? '#0F1F35' : 'white'}
      strokeWidth={isSelected ? 1.5 : 0.5}
      style={{ cursor: onClick ? 'pointer' : 'default' }}
      onClick={onClick}
      onMouseEnter={onHoverEnter}
      onMouseLeave={onHoverLeave}
    />
  )
}, (prev, next) => (
  prev.d     === next.d     &&
  prev.fill  === next.fill  &&
  prev.isSelected === next.isSelected
  // onClick/onHoverEnter/onHoverLeave excluded: they're stable per-index
  // entries from provinceCallbacks and never change identity after mount.
))

export default React.memo(function MapPanel({
  alertsByProvince = {},
  onProvinceClick,
  selectedProvince,
  markers = [],
  mode = 'alert',
}) {
  const [geoData, setGeoData]   = useState(_geoCache)
  const [dims, setDims]         = useState({ width: 700, height: 560 })
  const svgRef                  = useRef(null)
  const tooltipRef              = useRef(null)
  // Stable ref to latest normalizedAlerts/markers so tooltip handlers can read
  // them without being recreated when those values change.
  const alertsRef               = useRef({})
  const markersRef              = useRef([])
  const modeRef                 = useRef(mode)

  useEffect(() => { modeRef.current = mode }, [mode])

  // Responsive resize observer
  useEffect(() => {
    const el = svgRef.current?.parentElement
    if (!el) return
    const ro = new ResizeObserver(([entry]) => {
      setDims({ width: entry.contentRect.width, height: entry.contentRect.height })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // Load GeoJSON — uses shared module-level cache
  useEffect(() => {
    if (_geoCache) { setGeoData(_geoCache); return }
    loadGeoData().then(setGeoData)
  }, [])

  // All hooks must run unconditionally before any early return (see comment in
  // prior version). useMemo falls back to empty/null when geoData isn't ready.

  const { width, height } = dims

  const projection = useMemo(() => (
    d3.geoMercator()
      .center([115, 10])
      .scale(1000 * (width / 700))
      .translate([width / 2, height / 2])
  ), [width, height])

  const pathGen = useMemo(() => d3.geoPath().projection(projection), [projection])

  const bgFeatures = useMemo(
    () => (geoData ? geoData.features.filter(f =>  f.properties.isBackground) : []),
    [geoData]
  )
  const provFeatures = useMemo(
    () => (geoData ? geoData.features.filter(f => !f.properties.isBackground) : []),
    [geoData]
  )

  const normToGadm = useMemo(() => {
    const map = {}
    provFeatures.forEach(f => { map[norm(f.properties.NAME_1)] = f.properties.NAME_1 })
    return map
  }, [provFeatures])

  const normalizedAlerts = useMemo(() => {
    const map = {}
    Object.entries(alertsByProvince).forEach(([province, tier]) => {
      const gadmName = normToGadm[norm(province)]
      if (gadmName) map[gadmName] = tier
    })
    return map
  }, [alertsByProvince, normToGadm])

  // Keep alertsRef in sync so tooltip handlers always see latest value
  useEffect(() => { alertsRef.current = normalizedAlerts }, [normalizedAlerts])

  const normalizedMarkers = useMemo(() => (
    markers.map(m => ({ ...m, province: normToGadm[norm(m.province)] ?? m.province }))
  ), [markers, normToGadm])

  // Keep markersRef in sync
  useEffect(() => { markersRef.current = normalizedMarkers }, [normalizedMarkers])

  const normalizedSelected = normToGadm[norm(selectedProvince)] ?? selectedProvince

  // Memoize path strings and centroids together — one pass over provFeatures
  const { pathStrings, centroids } = useMemo(() => {
    const paths = {}
    const cents = {}
    provFeatures.forEach((f, i) => {
      paths[i] = pathGen(f)
      cents[i] = pathGen.centroid(f)
    })
    return { pathStrings: paths, centroids: cents }
  }, [provFeatures, pathGen])

  // O(1) name → feature lookup (replaces provFeatures.find() in selection ring)
  const provinceNameToFeature = useMemo(() => {
    const map = new Map()
    provFeatures.forEach(f => map.set(f.properties.NAME_1, f))
    return map
  }, [provFeatures])

  // ── Stable per-province callbacks ────────────────────────────────────────
  // Built once per provFeatures change (i.e. on initial load only).
  // Tooltip updates go directly to the DOM via tooltipRef — no setState at all.
  // onProvinceClick is read through a ref so we don't recreate the Map when it changes.
  const onProvinceClickRef = useRef(onProvinceClick)
  useEffect(() => { onProvinceClickRef.current = onProvinceClick }, [onProvinceClick])

  const provinceCallbacks = useMemo(() => {
    const map = new Map() // index → { onClick, onHoverEnter, onHoverLeave }
    provFeatures.forEach((f, i) => {
      const name        = f.properties.NAME_1
      const isNonASEAN  = f.properties.isNonASEAN

      if (isNonASEAN) {
        map.set(i, { onClick: undefined, onHoverEnter: undefined, onHoverLeave: undefined })
        return
      }

      const onClick = () => onProvinceClickRef.current?.(name)

      const onHoverEnter = (e) => {
        const tip = tooltipRef.current
        if (!tip) return
        const rect = svgRef.current?.getBoundingClientRect()
        if (!rect) return

        // Build tooltip HTML imperatively — no React setState
        const tier = alertsRef.current[name] ?? null
        const tierColor = tierFill(tier)
        let html = `<span style="font-weight:700">${name}</span>`
        if (tier) {
          html += `<span style="margin-left:8px;color:${tierColor}">${tier}</span>`
        }
        if (modeRef.current === 'impact') {
          const m = markersRef.current.find(x => x.province === name)
          if (m?.confidence != null) {
            html += `<span style="margin-left:8px;color:#aaa">${Math.round(m.confidence * 100)}% confidence</span>`
          }
        }

        tip.innerHTML = html
        tip.style.left    = `${e.clientX - rect.left + 10}px`
        tip.style.top     = `${e.clientY - rect.top  - 28}px`
        tip.style.display = 'block'
      }

      const onHoverLeave = () => {
        if (tooltipRef.current) tooltipRef.current.style.display = 'none'
      }

      map.set(i, { onClick, onHoverEnter, onHoverLeave })
    })
    return map
  }, [provFeatures]) // tooltipRef/svgRef/alertsRef/markersRef/modeRef are stable refs

  // Selection ring centroid — O(1) map lookup instead of O(n) find
  const selectedCentroid = useMemo(() => {
    if (!normalizedSelected) return null
    const f = provinceNameToFeature.get(normalizedSelected)
    if (!f) return null
    const c = pathGen.centroid(f)
    return (!c || isNaN(c[0])) ? null : c
  }, [normalizedSelected, provinceNameToFeature, pathGen])

  // Impact mode dot centroids — also O(1)
  const impactDots = useMemo(() => {
    if (mode !== 'impact') return []
    return normalizedMarkers
      .filter(m => m.tier)
      .map(m => {
        const f = provinceNameToFeature.get(m.province)
        if (!f) return null
        const c = pathGen.centroid(f)
        if (!c || isNaN(c[0])) return null
        return { ...m, cx: c[0], cy: c[1] }
      })
      .filter(Boolean)
  }, [mode, normalizedMarkers, provinceNameToFeature, pathGen])

  // ── Early return AFTER all hooks ─────────────────────────────────────────
  if (!geoData) {
    return (
      <div style={{ display:'flex', alignItems:'center', justifyContent:'center',
        height:'100%', color: C.textDim, fontSize: 13 }}>
        Loading map…
      </div>
    )
  }

  return (
    <div style={{ position:'relative', width:'100%', height:'100%',
      background: C.surface, borderRadius: 14,
      border: `0.5px solid ${C.border}`, overflow:'hidden' }}>

      <svg ref={svgRef} width="100%" height="100%"
        viewBox={`0 0 ${width} ${height}`}
        style={{ display:'block' }}>

        {/* Ocean */}
        <rect x={-500} y={-500} width={width + 1000} height={height + 1000} fill="#DCEBFB" />

        {/* Background ASEAN countries */}
        {bgFeatures.map((feature, i) => (
          <path
            key={`bg-${i}`}
            d={pathGen(feature) || ''}
            fill="#C8D8B0"
            stroke="#A0B888"
            strokeWidth={0.6}
          />
        ))}

        {/* Province paths — callbacks are stable; only fill/isSelected change */}
        {provFeatures.map((feature, i) => {
          const name       = feature.properties.NAME_1
          const isNonASEAN = feature.properties.isNonASEAN
          const tier       = normalizedAlerts[name] ?? null
          const isSelected = normalizedSelected === name
          const fill       = mode === 'alert'
            ? (tierFill(tier) ?? (isSelected ? '#4a90d9' : (isNonASEAN ? '#c2c7b6' : '#8ab87a')))
            : (isSelected ? '#4a90d9' : (isNonASEAN ? '#d0d3cc' : '#a8c8a0'))
          const d = pathStrings[i]
          if (!d) return null

          const cbs = provinceCallbacks.get(i)

          return (
            <ProvincePath
              key={`prov-${i}`}
              d={d}
              fill={fill}
              isSelected={isSelected}
              onClick={cbs?.onClick}
              onHoverEnter={cbs?.onHoverEnter}
              onHoverLeave={cbs?.onHoverLeave}
            />
          )
        })}

        {/* Impact mode — confidence dots (O(1) centroid lookup) */}
        {impactDots.map((m, i) => {
          const color = tierFill(m.tier) ?? C.amber
          const r     = Math.max(4, Math.min(16, (m.confidence ?? 0.5) * 16))
          return (
            <g key={`dot-${i}`} style={{ pointerEvents:'none' }}>
              <circle cx={m.cx} cy={m.cy} r={r + 4} fill={color} fillOpacity={0.15} />
              <circle cx={m.cx} cy={m.cy} r={r}     fill={color} fillOpacity={0.6}
                stroke={color} strokeWidth={1} />
            </g>
          )
        })}

        {/* Alert mode — selection ring (O(1) centroid lookup) */}
        {mode === 'alert' && selectedCentroid && (
          <circle cx={selectedCentroid[0]} cy={selectedCentroid[1]} r={10}
            fill="none" stroke="#0F1F35" strokeWidth={1.5}
            opacity={0.6} style={{ pointerEvents:'none' }}/>
        )}

      </svg>

      {/* Legend — mode-aware overlay, top-right corner (over ocean) */}
      <div style={{
        position: 'absolute', right: 12, top: 12, zIndex: 10,
        background: 'rgba(255,255,255,0.92)', border: `0.5px solid ${C.border}`,
        borderRadius: 8, padding: '8px 11px', fontSize: 10.5, color: C.text,
        lineHeight: 1.45, fontFamily: 'system-ui, sans-serif', maxWidth: 168,
        boxShadow: '0 1px 5px rgba(15,31,53,0.10)', pointerEvents: 'none',
      }}>
        <div style={{
          fontWeight: 700, fontSize: 9, letterSpacing: '0.06em',
          color: C.textDim, textTransform: 'uppercase', marginBottom: 5,
        }}>
          {mode === 'impact' ? 'Impact confidence' : 'Alert tier'}
        </div>

        <LegendRow color="#C0282A" label="Warning (≥0.80)"      shape={mode === 'impact' ? 'dot' : 'box'} />
        <LegendRow color="#E8A020" label="Advisory (0.65–0.79)" shape={mode === 'impact' ? 'dot' : 'box'} />
        <LegendRow color="#B87000" label="Watch (0.50–0.64)"    shape={mode === 'impact' ? 'dot' : 'box'} />

        <div style={{ height: 1, background: C.border, margin: '6px 0' }} />

        <LegendRow color={mode === 'impact' ? '#a8c8a0' : '#8ab87a'} label="Monitored · PH·VN·TH" />
        <LegendRow color={mode === 'impact' ? '#d0d3cc' : '#c2c7b6'} label="Context / non-ASEAN" />

        {mode === 'impact'
          ? <div style={{ marginTop: 6, color: C.textDim, fontSize: 9.5 }}>● dot size = confidence</div>
          : <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 12, height: 12, borderRadius: 3, background: '#4a90d9', flexShrink: 0 }} />
              <span>Selected</span>
            </div>}
      </div>

      {/* Tooltip — mounted once, updated imperatively via tooltipRef */}
      <ProvinceTooltip tooltipRef={tooltipRef} />

    </div>
  )
})