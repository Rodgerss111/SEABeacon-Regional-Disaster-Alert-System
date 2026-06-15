import { useState, useEffect } from 'react'
import * as d3 from 'd3'

const WIDTH = 1100
const HEIGHT = 700

const LAYERS = [
  { url: '/gadm41_MMR_1.json', background: true },
  { url: '/gadm41_LAO_1.json', background: true },
  { url: '/gadm41_KHM_1.json', background: true },
  { url: '/gadm41_MYS_1.json', background: true },
  { url: '/gadm41_SGP_1.json', background: true },
  { url: '/gadm41_BRN_1.json', background: true },
  { url: '/gadm41_IDN_1.json', background: true },
  { url: '/gadm41_KHM_1.json', background: true },
  { url: '/gadm41_PHL_1.json', background: false },
  { url: '/gadm41_VNM_1.json', background: false },
  { url: '/gadm41_THA_1.json', background: false },
]

export default function App() {
  const [geoData, setGeoData] = useState(null)
  const [selected, setSelected] = useState(null)

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

  if (!geoData) return <p style={{ padding: 20 }}>Loading maps...</p>

  // Hard-code the projection to Southeast Asia
  // center: [longitude, latitude] of the middle of SEA
  // scale: zoom level — higher = more zoomed in
  const projection = d3.geoMercator()
    .center([113, 8])
    .scale(1600)
    .translate([WIDTH / 2, HEIGHT / 2])

  const pathGen = d3.geoPath().projection(projection)

  return (
    <div style={{ display: 'flex', height: '100vh', fontFamily: 'sans-serif', background: '#1a1a2e' }}>
      <svg width={WIDTH} height={HEIGHT} style={{ flexShrink: 0 }}>

        {/* Ocean */}
        <rect width={WIDTH} height={HEIGHT} fill="#a8c8e8" />

        {/* Background countries */}
        {geoData.features.filter(f => f.properties.isBackground).map((feature, i) => (
          <path
            key={`bg-${i}`}
            d={pathGen(feature)}
            fill="#b8c9a3"
            stroke="#8a9e7a"
            strokeWidth={0.8}
          />
        ))}

        {/* Clickable province countries */}
        {geoData.features.filter(f => !f.properties.isBackground).map((feature, i) => {
          const isSelected = selected?.GID_1 === feature.properties.GID_1
          return (
            <path
              key={`prov-${i}`}
              d={pathGen(feature)}
              fill={isSelected ? '#4a90d9' : '#8ab87a'}
              stroke="white"
              strokeWidth={0.5}
              style={{ cursor: 'pointer' }}
              onClick={() => setSelected(feature.properties)}
            />
          )
        })}

      </svg>

      {/* Info panel */}
      <div style={{ padding: 20, width: 240, color: '#eee', overflowY: 'auto' }}>
        {selected ? (
          <>
            <h2 style={{ marginBottom: 6, fontSize: 18 }}>{selected.NAME_1}</h2>
            <p style={{ color: '#aaa', fontSize: 13, marginBottom: 4 }}>{selected.COUNTRY}</p>
            <p style={{ color: '#aaa', fontSize: 13 }}>{selected.ENGTYPE_1}</p>
          </>
        ) : (
          <p style={{ color: '#666', fontSize: 13 }}>Click a province to inspect it</p>
        )}
      </div>
    </div>
  )
}