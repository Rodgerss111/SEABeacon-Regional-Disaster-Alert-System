import { useState, useEffect, useRef } from 'react'
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

// Normalize province names for matching — strips spaces, punctuation, lowercases
// "Northern Samar" → "northernsamar", "AgusandelNorte" → "agusandelnorte"
// Same concept as CAN ID normalization before arbitration comparison
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
  { url: '/gadm41_TLS_1.json', background: true },
  { url: '/gadm41_PHL_1.json', background: false },
  { url: '/gadm41_VNM_1.json', background: false },
  { url: '/gadm41_THA_1.json', background: false },
  { url: '/gadm41_CHN_1.json', background: false },
  { url: '/gadm41_JPN_1.json', background: false },
  { url: '/gadm41_TWN_1.json', background: false },
]

// Module-level shared cache — both MapPanel instances share one fetch
let _geoCache = null
let _geoPromise = null

function loadGeoData() {
  if (_geoCache) return Promise.resolve(_geoCache)
  if (_geoPromise) return _geoPromise
  _geoPromise = Promise.all(
    LAYERS.map(layer =>
      fetch(layer.url)
        .then(r => {
          if (!r.ok) throw new Error(`404: ${layer.url}`)
          return r.json()
        })
        .then(json => ({ background: layer.background, features: json.features }))
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

export default function MapPanel({
  alertsByProvince = {},
  onProvinceClick,
  selectedProvince,
  markers = [],
  mode = 'alert',
}) {
  const [geoData, setGeoData] = useState(_geoCache)
  const [tooltip, setTooltip]  = useState(null)
  const svgRef = useRef(null)
  const [dims, setDims] = useState({ width: 700, height: 560 })

  // Responsive resize observer
  useEffect(() => {
    const el = svgRef.current?.parentElement
    if (!el) return
    const ro = new ResizeObserver(([entry]) => {
      const w = entry.contentRect.width
      const h = entry.contentRect.height
      setDims({ width: w, height: h })   // use full height, not 80% of width
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // Load GeoJSON — uses shared cache
  useEffect(() => {
    if (_geoCache) { setGeoData(_geoCache); return }
    loadGeoData().then(setGeoData)
  }, [])

  if (!geoData) {
    return (
      <div style={{ display:'flex', alignItems:'center', justifyContent:'center',
        height:'100%', color: C.textDim, fontSize: 13 }}>
        Loading map…
      </div>
    )
  }

  const { width, height } = dims

  const projection = d3.geoMercator()
    .center([115, 10])
    .scale(1000 * (width / 700))
    .translate([width / 2, height / 2])

  const pathGen    = d3.geoPath().projection(projection)
  const bgFeatures   = geoData.features.filter(f =>  f.properties.isBackground)
  const provFeatures = geoData.features.filter(f => !f.properties.isBackground)

  // Build normalized lookup table: norm(gadmName) → gadmName
  // Lets us match "Northern Samar" (SEABeacon) → "NorthernSamar" (GADM)
  const normToGadm = {}
  provFeatures.forEach(f => {
    normToGadm[norm(f.properties.NAME_1)] = f.properties.NAME_1
  })

  // Remap alertsByProvince keys to GADM names
  const normalizedAlerts = {}
  Object.entries(alertsByProvince).forEach(([province, tier]) => {
    const gadmName = normToGadm[norm(province)]
    if (gadmName) normalizedAlerts[gadmName] = tier
  })

  // Remap marker province names to GADM names
  const normalizedMarkers = markers.map(m => ({
    ...m,
    province: normToGadm[norm(m.province)] ?? m.province
  }))

  // Also normalize selectedProvince for centroid/selection lookup
  const normalizedSelected = normToGadm[norm(selectedProvince)] ?? selectedProvince

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

        {/* Clickable province paths */}
        {provFeatures.map((feature, i) => {
          const name       = feature.properties.NAME_1
          const tier       = normalizedAlerts[name] ?? null
          const isSelected = normalizedSelected === name
          const d          = pathGen(feature)
          if (!d) return null

          // Define colors for non-ASEAN countries (China, Japan, Taiwan)
          const isNonASEAN = ['China', 'Japan', 'Taiwan'].includes(feature.properties.COUNTRY);
          const nonASEANFill = '#6b8e23'; // OliveDrab color for non-ASEAN countries

          const fill = mode === 'alert'
            ? (tierFill(tier) ?? (isSelected ? '#4a90d9' : (isNonASEAN ? nonASEANFill : '#8ab87a')))
            : (isSelected ? '#4a90d9' : (isNonASEAN ? nonASEANFill : '#a8c8a0'))

          return (
            <path
              key={`prov-${i}`}
              d={d}
              fill={fill}
              stroke={isSelected ? '#0F1F35' : 'white'}
              strokeWidth={isSelected ? 1.5 : 0.5}
              style={{ cursor:'pointer', transition:'fill 0.3s' }}
              onClick={() => onProvinceClick?.(name)}
              onMouseEnter={e => {
                const rect = svgRef.current.getBoundingClientRect()
                setTooltip({ x: e.clientX - rect.left + 10, y: e.clientY - rect.top - 28, name, tier })
              }}
              onMouseLeave={() => setTooltip(null)}
            />
          )
        })}

        {/* Impact mode — confidence dots scaled by m.confidence (0→1 maps to r 4→16px) */}
        {mode === 'impact' && normalizedMarkers.filter(m => m.tier).map((m, i) => {
          const feature = provFeatures.find(f => f.properties.NAME_1 === m.province)
          if (!feature) return null
          const c = pathGen.centroid(feature)
          if (!c || isNaN(c[0])) return null
          const color = tierFill(m.tier) ?? C.amber
          const r = Math.max(4, Math.min(16, (m.confidence ?? 0.5) * 16))
          return (
            <g key={`dot-${i}`} style={{ pointerEvents:'none' }}>
              <circle cx={c[0]} cy={c[1]} r={r + 4} fill={color} fillOpacity={0.15} />
              <circle cx={c[0]} cy={c[1]} r={r}     fill={color} fillOpacity={0.6}
                stroke={color} strokeWidth={1} />
            </g>
          )
        })}

        {/* Alert mode — selection ring at province centroid */}
        {mode === 'alert' && normalizedSelected && (() => {
          const f = provFeatures.find(f => f.properties.NAME_1 === normalizedSelected)
          if (!f) return null
          const c = pathGen.centroid(f)
          if (!c || isNaN(c[0])) return null
          return (
            <circle cx={c[0]} cy={c[1]} r={10}
              fill="none" stroke="#0F1F35" strokeWidth={1.5}
              opacity={0.6} style={{ pointerEvents:'none' }}/>
          )
        })()}

      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div style={{
          position:'absolute', left: tooltip.x, top: tooltip.y,
          background:'rgba(15,31,53,0.9)', color:'white',
          padding:'5px 10px', borderRadius:6, fontSize:11,
          pointerEvents:'none', whiteSpace:'nowrap', zIndex:10
        }}>
          <span style={{ fontWeight:700 }}>{tooltip.name}</span>
          {tooltip.tier && (
            <span style={{ marginLeft:8, color: tierFill(tooltip.tier) }}>
              {tooltip.tier}
            </span>
          )}
          {mode === 'impact' && (() => {
            const m = normalizedMarkers.find(x => x.province === tooltip.name)
            return m?.confidence != null
              ? <span style={{ marginLeft:8, color:'#aaa' }}>
                  {Math.round(m.confidence * 100)}% confidence
                </span>
              : null
          })()}
        </div>
      )}
    </div>
  )
}