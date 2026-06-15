import { useState, useEffect, useRef } from 'react'
import * as d3 from 'd3'

// ── Color tokens (must match SEABeacon.jsx) ───────────────────────────────────
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

const LAYERS = [
  // Level 1 background ASEAN countries — rendered flat, not clickable
  { url: '/gadm41_MMR_1.json', background: true },
  { url: '/gadm41_LAO_1.json', background: true },
  { url: '/gadm41_KHM_1.json', background: true },
  { url: '/gadm41_MYS_1.json', background: true },
  { url: '/gadm41_SGP_1.json', background: true },
  { url: '/gadm41_BRN_1.json', background: true },
  { url: '/gadm41_IDN_1.json', background: true },
  { url: '/gadm41_TLS_1.json', background: true },
  // Level 1 detailed countries — clickable provinces
  { url: '/gadm41_PHL_1.json', background: false },
  { url: '/gadm41_VNM_1.json', background: false },
  { url: '/gadm41_THA_1.json', background: false },
]

// alertsByProvince: { "Eastern Samar": "Warning", "Cebu": "Watch", ... }
// onProvinceClick: (provinceName) => void
export default function MapPanel({ alertsByProvince = {}, onProvinceClick, selectedProvince }) {
  const [geoData, setGeoData]   = useState(null)
  const [tooltip, setTooltip]   = useState(null) // { x, y, name, tier }
  const svgRef = useRef(null)

  // ── Responsive width ────────────────────────────────────────────────────────
  const [dims, setDims] = useState({ width: 700, height: 560 })
  useEffect(() => {
    const el = svgRef.current?.parentElement
    if (!el) return
    const ro = new ResizeObserver(([entry]) => {
      const w = entry.contentRect.width
      setDims({ width: w, height: Math.round(w * 0.75) })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // ── Fetch all GeoJSON layers ─────────────────────────────────────────────────
  useEffect(() => {
    Promise.all(
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
      setGeoData({ type: 'FeatureCollection', features: allFeatures })
    })
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

  // ── Projection — hard-coded to SEA, tuned to fit PH/VN/TH ─────────────────
  const projection = d3.geoMercator()
    .center([115, 10])
    .scale(1000 * (width / 700))   // scale proportionally to container width
    .translate([width / 2, height / 2])

  const pathGen = d3.geoPath().projection(projection)

  const bgFeatures   = geoData.features.filter(f =>  f.properties.isBackground)
  const provFeatures = geoData.features.filter(f => !f.properties.isBackground)

  return (
    <div style={{ position:'relative', width:'100%', height:'100%',
      background: C.surface, borderRadius: 14,
      border: `0.5px solid ${C.border}`, overflow:'hidden' }}>

      {/* Header */}
      <div style={{ padding:'14px 18px 10px', borderBottom:`0.5px solid ${C.border}`,
        display:'flex', justifyContent:'space-between', alignItems:'center' }}>
        <div>
          <div style={{ fontSize:13, fontWeight:700, color:C.text }}>Province Alert Map</div>
          <div style={{ fontSize:10, color:C.textDim, marginTop:2 }}>
            Click a province to filter reports · color = active alert tier
          </div>
        </div>
        {/* Legend */}
        <div style={{ display:'flex', gap:10 }}>
          {[["Warning", C.red], ["Advisory", C.amberLt], ["Watch", C.amber]].map(([label, color]) => (
            <div key={label} style={{ display:'flex', alignItems:'center', gap:4, fontSize:10, color:C.textDim }}>
              <div style={{ width:8, height:8, borderRadius:'50%', background:color }}/>
              {label}
            </div>
          ))}
        </div>
      </div>

      {/* SVG map */}
      <svg ref={svgRef} width={width} height={height} style={{ display:'block' }}>

        {/* Ocean */}
        <rect width={width} height={height} fill="#DCEBFB" />

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

        {/* Clickable province countries */}
        {provFeatures.map((feature, i) => {
          const name    = feature.properties.NAME_1
          const tier    = alertsByProvince[name] ?? null
          const fill    = tierFill(tier) ?? '#8ab87a'
          const isSelected = selectedProvince === name
          const d = pathGen(feature)
          if (!d) return null

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
                setTooltip({
                  x: e.clientX - rect.left + 10,
                  y: e.clientY - rect.top - 28,
                  name,
                  tier
                })
              }}
              onMouseLeave={() => setTooltip(null)}
            />
          )
        })}

        {/* Pulse ring on selected province centroid */}
        {selectedProvince && (() => {
          const f = provFeatures.find(f => f.properties.NAME_1 === selectedProvince)
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
          pointerEvents:'none', whiteSpace:'nowrap'
        }}>
          <span style={{ fontWeight:700 }}>{tooltip.name}</span>
          {tooltip.tier && (
            <span style={{ marginLeft:8, color: tierFill(tooltip.tier) }}>
              {tooltip.tier}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
