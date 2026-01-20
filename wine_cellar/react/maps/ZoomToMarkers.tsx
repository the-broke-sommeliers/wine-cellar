import { useEffect } from 'react'
import { useMap } from 'react-leaflet'
import L, { LatLngExpression } from 'leaflet'

interface ZoomToMarkersProps {
  points: LatLngExpression[]
}

export const ZoomToMarkers: React.FC<ZoomToMarkersProps> = ({ points }) => {
  const map = useMap()

  useEffect(() => {
    if (!points || points.length === 0) return

    if (points.length === 1) {
      map.setView(points[0], 8)
    } else {
      map.fitBounds(L.latLngBounds(points), {
        padding: [40, 40],
        maxZoom: 8,
      })
    }
  }, [points, map])

  return null
}
