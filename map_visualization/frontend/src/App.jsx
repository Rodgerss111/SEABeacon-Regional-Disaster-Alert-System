import { useState, useCallback, useEffect } from 'react'
import MapPanel from './MapPanel'
import SEABeacon from './SEABeacon'

// Small viewport detector. Stacks the two-pane layout on phones/tablets.
function useMediaQuery(query) {
  const [matches, setMatches] = useState(
    () => typeof window !== 'undefined' && window.matchMedia(query).matches
  )
  useEffect(() => {
    const mql = window.matchMedia(query)
    const onChange = (e) => setMatches(e.matches)
    setMatches(mql.matches)
    mql.addEventListener('change', onChange)
    return () => mql.removeEventListener('change', onChange)
  }, [query])
  return matches
}

export default function App() {
  const [selectedProvince, setSelectedProvince] = useState(null)
  const [alertsByProvince, setAlertsByProvince] = useState({})
  const [markers, setMarkers] = useState([])
  const [mapMode, setMapMode] = useState('alert')
  const isNarrow = useMediaQuery('(max-width: 900px)')

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
      // Desktop: two equal columns. Narrow: single column that stacks.
      gridTemplateColumns: isNarrow ? '1fr' : '50fr 50fr',
      height: isNarrow ? 'auto' : '100vh',
      minHeight: '100vh',
      width: '100%',
      overflow: isNarrow ? 'visible' : 'hidden',
      fontFamily: "'DM Sans', sans-serif",
      background: '#EEF3FA',
    }}>

    {/* Left — province map */}
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
      padding: 8,
      height: isNarrow ? 'auto' : '100vh',
      minWidth: 0, // allow the grid column to shrink instead of forcing overflow
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

      {/* Single map that switches mode. On narrow screens it gets a fixed
          height instead of filling the viewport so the panel below can flow. */}
      <div style={{
        flex: isNarrow ? 'none' : 1,
        height: isNarrow ? '52vh' : 'auto',
        minHeight: isNarrow ? 300 : 0,
        overflow: 'hidden',
      }}>
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
        borderLeft: isNarrow ? 'none' : '1px solid rgba(0,0,0,0.08)',
        borderTop: isNarrow ? '1px solid rgba(0,0,0,0.08)' : 'none',
        // Desktop: this pane scrolls on its own. Narrow: it flows into page scroll.
        overflowY: isNarrow ? 'visible' : 'auto',
        minWidth: 0, // critical: stops wide children from forcing the grid past the viewport
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
