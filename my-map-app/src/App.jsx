import { useState, useCallback } from 'react'
import MapPanel from './MapPanel'
import SEABeacon from './SEABeacon'

export default function App() {
  const [selectedProvince, setSelectedProvince] = useState(null)
  const [alertsByProvince, setAlertsByProvince] = useState({})
  const [markers, setMarkers] = useState([])

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
      gridTemplateColumns: '65fr 35fr',
      height: '100vh',
      width: '100vw',
      overflow: 'hidden',
      fontFamily: "'DM Sans', sans-serif",
      background: '#EEF3FA',
    }}>

      {/* Left — two maps side by side */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',   // two equal columns
        gap: 8,
        padding: 8,
        overflow: 'hidden',
        height: '100vh',
      }}>

        {/* Left map — Alert */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minHeight: 0, overflow: 'hidden' }}>
          <div style={{
            background: '#fff', borderRadius: 14,
            border: '0.5px solid rgba(0,0,0,0.08)',
            padding: '12px 18px', flexShrink: 0,
            display: 'flex', flexDirection: 'column', gap: 2,
          }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#0F1F35' }}>Province Alert Map</div>
            <div style={{ fontSize: 10, color: '#7A92AD' }}>
              Color = active alert tier · click to inspect
            </div>
            <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
              {[["Warning", "#C0282A"], ["Advisory", "#E8A020"], ["Watch", "#B87000"]].map(([label, color]) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: '#7A92AD' }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }}/>
                  {label}
                </div>
              ))}
            </div>
          </div>
          <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
            <MapPanel
              mode="alert"
              alertsByProvince={alertsByProvince}
              selectedProvince={selectedProvince}
              onProvinceClick={setSelectedProvince}
            />
          </div>
        </div>

        {/* Right map — Impact */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minHeight: 0, overflow: 'hidden' }}>
          <div style={{
            background: '#fff', borderRadius: 14,
            border: '0.5px solid rgba(0,0,0,0.08)',
            padding: '12px 18px', flexShrink: 0,
            display: 'flex', flexDirection: 'column', gap: 2,
          }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#0F1F35' }}>Province Impact Map</div>
            <div style={{ fontSize: 10, color: '#7A92AD' }}>
              Dot size = confidence · color = tier · live ranked overlay
            </div>
            <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
              {[["Warning", "#C0282A"], ["Advisory", "#E8A020"], ["Watch", "#B87000"]].map(([label, color]) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: '#7A92AD' }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }}/>
                  {label}
                </div>
              ))}
            </div>
          </div>
          <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
            <MapPanel
              mode="impact"
              alertsByProvince={alertsByProvince}
              selectedProvince={selectedProvince}
              onProvinceClick={setSelectedProvince}
              markers={markers}
            />
          </div>
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