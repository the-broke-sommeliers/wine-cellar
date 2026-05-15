import L, { type LatLngExpression } from 'leaflet'
import { useEffect } from 'react'
import { useMap } from 'react-leaflet'

interface ZoomToMarkersProps {
  points: LatLngExpression[]
}

export const ZoomToMarkers: React.FC<ZoomToMarkersProps> = ({ points }) => {
  const map = useMap()

  useEffect(() => {
    if (!points || points.length === 0) {
      return
    }

    const firstPoint = points[0]
    if (points.length === 1 && firstPoint) {
      map.setView(firstPoint, 8)
    } else {
      map.fitBounds(L.latLngBounds(points), {
        padding: [40, 40],
        maxZoom: 8,
      })
    }
  }, [points, map])

  return null
}
