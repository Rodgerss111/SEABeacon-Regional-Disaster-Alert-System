import { useState, useCallback } from 'react'
import MapPanel from './MapPanel'
import SEABeacon from './SEABeacon'

export default function App() {
  const [selectedProvince, setSelectedProvince] = useState(null)
  const [alertsByProvince, setAlertsByProvince] = useState({})
  const [markers, setMarkers] = useState([])
  const [mapMode, setMapMode] = useState('alert')

  const handleRankedUpdate = useCallback((ranked) => {
    console.log('Ranked provinces from SEABeacon:', ranked.map(r => r.province))
    const map = {}
    ranked.forEach(r => {
      if (r.tier && !r.reviewed) map[r.province] = r.tier
    })
    setAlertsByProvince(map)
    setMarkers(ranked)
  }, [])

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '50fr 50fr',
      height: '100vh',
      width: '100vw',
      overflow: 'hidden',
      fontFamily: "'DM Sans', sans-serif",
      background: '#EEF3FA',
    }}>

    {/*// In the left div, replace the inner grid with:*/}
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
      padding: 8,
      height: '100vh',
      overflow: 'hidden',
    }}>
      {/* Toggle header */}
      <div style={{
        background: '#fff', borderRadius: 14,
        border: '0.5px solid rgba(0,0,0,0.08)',
        padding: '12px 18px', flexShrink: 0,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#0F1F35' }}>
          {mapMode === 'alert' ? 'Province Alert Map' : 'Province Impact Map'}
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {['alert', 'impact'].map(m => (
            <button key={m} onClick={() => setMapMode(m)} style={{
              padding: '4px 12px', borderRadius: 8, border: 'none',
              fontSize: 11, cursor: 'pointer',
              background: mapMode === m ? '#0F1F35' : '#EEF3FA',
              color: mapMode === m ? '#fff' : '#7A92AD',
            }}>
              {m === 'alert' ? 'Alert' : 'Impact'}
            </button>
          ))}
        </div>
      </div>

      {/* Single map that switches mode */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
        <MapPanel
          mode={mapMode}
          alertsByProvince={alertsByProvince}
          selectedProvince={selectedProvince}
          onProvinceClick={setSelectedProvince}
          markers={markers}
        />
      </div>
    </div>

      {/* Right — SEABeacon panel */}
      <div style={{
        borderLeft: '1px solid rgba(0,0,0,0.08)',
        overflowY: 'auto',
        background: '#FFFFFF',
      }}>
        <SEABeacon
          selectedProvince={selectedProvince}
          onRankedUpdate={handleRankedUpdate}
          hideImpactMap={true}
        />
      </div>

    </div>
  )
}