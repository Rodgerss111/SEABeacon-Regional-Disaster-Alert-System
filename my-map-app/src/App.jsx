import { useState, useCallback } from 'react'
import MapPanel from './MapPanel'
import SEABeacon from './SEABeacon'   // rename your uploaded file to SEABeacon.jsx

// SEABeacon exposes its fused province alert data upward via this prop.
// App owns the bridge state between the map and the alert engine.

export default function App() {
  // The province the user clicked on the map
  const [selectedProvince, setSelectedProvince] = useState(null)

  // alertsByProvince is built from SEABeacon's fused ranked list.
  // Shape: { "Eastern Samar": "Warning", "Leyte": "Watch", ... }
  const [alertsByProvince, setAlertsByProvince] = useState({})

  // SEABeacon calls this whenever its ranked list changes
  const handleRankedUpdate = useCallback((ranked) => {
    const map = {}
    ranked.forEach(r => {
      if (r.tier && !r.reviewed) map[r.province] = r.tier
    })
    setAlertsByProvince(map)
  }, [])

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 380px',  // map takes remaining space, panel fixed
      height: '100vh',
      overflow: 'hidden',
      fontFamily: "'DM Sans', sans-serif",
      background: '#EEF3FA',
    }}>

      {/* Left — D3 SVG map */}
      <div style={{ padding: 8, overflow: 'hidden' }}>
        <MapPanel
          alertsByProvince={alertsByProvince}
          selectedProvince={selectedProvince}
          onProvinceClick={setSelectedProvince}
        />
      </div>

      {/* Right — SEABeacon alert engine */}
      <div style={{
        borderLeft: '1px solid rgba(0,0,0,0.08)',
        overflowY: 'auto',
        background: '#FFFFFF',
      }}>
        <SEABeacon
          selectedProvince={selectedProvince}
          onRankedUpdate={handleRankedUpdate}
        />
      </div>

    </div>
  )
}
