import { useState, useEffect } from 'react'
import * as d3 from 'd3'

const WIDTH = 800
const HEIGHT = 600

export default function App() {
  const [geoData, setGeoData] = useState(null)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    Promise.all([
      fetch('/gadm41_PHL_1.json').then(r => r.json()),
      fetch('/gadm41_VNM_1.json').then(r => r.json()),
      fetch('/gadm41_THA_1.json').then(r => r.json()),
    ]).then(([ph, vn, th]) => {
      setGeoData({
        type: 'FeatureCollection',
        features: [...ph.features, ...vn.features, ...th.features]
      })
    })
  }, [])

  if (!geoData) return <p>Loading...</p>

  const projection = d3.geoMercator().fitSize([WIDTH, HEIGHT], geoData)
  const pathGen = d3.geoPath().projection(projection)

  return (
    <div>
      <svg width={WIDTH} height={HEIGHT}>
        {geoData.features.map(feature => (
          <path
            key={feature.properties.GID_1}
            d={pathGen(feature)}
            fill={selected?.GID_1 === feature.properties.GID_1 ? 'steelblue' : '#ccc'}
            stroke="white"
            strokeWidth={0.5}
            onClick={() => setSelected(feature.properties)}
            style={{ cursor: 'pointer' }}
          />
        ))}
      </svg>

      {selected && (
        <div>
          <h2>{selected.NAME_1}</h2>
        </div>
      )}
    </div>
  )
}