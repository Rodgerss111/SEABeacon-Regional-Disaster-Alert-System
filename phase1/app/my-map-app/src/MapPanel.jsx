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

// ── Single province path, memoized ───────────────────────────────────────────
const ProvincePath = memo(function ProvincePath({
  d, fill, isSelected, name, tier, onClick, onHoverEnter, onHoverLeave,
}) {
  return (
    <path
      d={d}
      fill={fill}
      stroke={isSelected ? '#0F1F35' : 'white'}
      strokeWidth={isSelected ? 1.5 : 0.5}
      // No pointer cursor or events when onClick is absent (non-ASEAN countries)
      style={{ cursor: onClick ? 'pointer' : 'default' }}
      onClick={onClick}
      onMouseEnter={onHoverEnter}
      onMouseLeave={onHoverLeave}
    />
  )
}, (prev, next) => (
  prev.d === next.d &&
  prev.fill === next.fill &&
  prev.isSelected === next.isSelected &&
  prev.name === next.name &&
  prev.tier === next.tier
))

export default React.memo(function MapPanel({
  alertsByProvince = {},
  onProvinceClick,
  selectedProvince,
  markers = [],
  mode = 'alert',
}) {
  const [geoData, setGeoData] = useState(_geoCache)
  const [hoverState, setHoverState] = useState({ index: null, position: null })
  const svgRef = useRef(null)
  const [dims, setDims] = useState({ width: 700, height: 560 })
  const handleHoverEnter = useCallback((index, event) => {
    const rect = svgRef.current?.getBoundingClientRect()
    if (!rect) return
    setHoverState({
      index,
      position: { x: event.clientX - rect.left + 10, y: event.clientY - rect.top - 28 }
    })
  }, []);
  const handleHoverLeave = useCallback(() => {
    setHoverState({ index: null, position: null })
  }, [])

  useEffect(() => {
    const el = svgRef.current?.parentElement
    if (!el) return
    const ro = new ResizeObserver(([entry]) => {
      const w = entry.contentRect.width
      const h = entry.contentRect.height
      setDims({ width: w, height: h })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    if (_geoCache) { setGeoData(_geoCache); return }
    loadGeoData().then(setGeoData)
  }, [])

  const { width, height } = dims

  const projection = useMemo(() => (
    d3.geoMercator()
      .center([115, 10])
      .scale(1000 * (width / 700))
      .translate([width / 2, height / 2])
  ), [width, height])

  const pathGen = useMemo(() => d3.geoPath().projection(projection), [projection])

  const bgFeatures = useMemo(
    () => (geoData ? geoData.features.filter(f => f.properties.isBackground) : []),
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

  const normalizedMarkers = useMemo(() => {
    return markers.map(m => ({ ...m, province: normToGadm[norm(m.province)] ?? m.province }))
  }, [markers, normToGadm])

  const normalizedSelected = normToGadm[norm(selectedProvince)] ?? selectedProvince

  const { pathStrings, centroids } = useMemo(() => {
    const paths = {}
    const cents = {}
    provFeatures.forEach((f, i) => {
      paths[i] = pathGen(f)
      cents[i] = pathGen.centroid(f)
    })
    return { pathStrings: paths, centroids: cents }
  }, [provFeatures, pathGen])

  const provinceNameToIndex = useMemo(() => {
    const map = new Map()
    provFeatures.forEach((f, i) => {
      map.set(f.properties.NAME_1, i)
    })
    return map
  }, [provFeatures])

  const provinceNameToFeature = useMemo(() => {
    const map = new Map()
    provFeatures.forEach(f => {
      map.set(f.properties.NAME_1, f)
    })
    return map
  }, [provFeatures])

  const markerProvinceToMarker = useMemo(() => {
    const map = new Map()
    normalizedMarkers.forEach(m => {
      map.set(m.province, m)
    })
    return map
  }, [normalizedMarkers])

  const tooltipData = useMemo(() => {
    if (hoverState.index === null) return null
    const feature = provFeatures[hoverState.index]
    const name = feature.properties.NAME_1
    const tier = normalizedAlerts[name] ?? null
    return { name, tier, x: hoverState.position?.x, y: hoverState.position?.y }
  }, [hoverState, provFeatures, normalizedAlerts])

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

        {/* Clickable province paths */}
        {provFeatures.map((feature, i) => {
          const name = feature.properties.NAME_1
          const tier = normalizedAlerts[name] ?? null
          const isSelected = normalizedSelected === name

          // China, Japan, Taiwan are display-only — no interaction
          const isNonASEAN = ['China', 'Japan', 'Taiwan'].includes(feature.properties.COUNTRY)
          const nonASEANFill = '#d5d6d2'

          const fill = mode === 'alert'
            ? (tierFill(tier) ?? (isSelected ? '#4a90d9' : (isNonASEAN ? nonASEANFill : '#8ab87a')))
            : (isSelected ? '#4a90d9' : (isNonASEAN ? nonASEANFill : '#a8c8a0'))

          const d = pathStrings[i]
          if (!d) return null

          return (
            <ProvincePath
              key={`prov-${i}`}
              d={d}
              fill={fill}
              isSelected={isSelected}
              name={name}
              tier={tier}
              // Non-ASEAN countries get no handlers — unselectable, no tooltip, default cursor
              onClick={isNonASEAN ? undefined : () => onProvinceClick?.(name)}
              onHoverEnter={isNonASEAN ? undefined : (e) => handleHoverEnter(i, e)}
              onHoverLeave={isNonASEAN ? undefined : handleHoverLeave}
            />
          )
        })}

        {/* Impact mode — confidence dots */}
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
      {tooltipData && (
        <div style={{
          position:'absolute', left: tooltipData.x, top: tooltipData.y,
          background:'rgba(15,31,53,0.9)', color:'white',
          padding:'5px 10px', borderRadius:6, fontSize:11,
          pointerEvents:'none', whiteSpace:'nowrap', zIndex:10
        }}>
          <span style={{ fontWeight:700 }}>{tooltipData.name}</span>
          {tooltipData.tier && (
            <span style={{ marginLeft:8, color: tierFill(tooltipData.tier) }}>
              {tooltipData.tier}
            </span>
          )}
          {mode === 'impact' && (() => {
            const m = normalizedMarkers.find(x => x.province === tooltipData.name)
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
})