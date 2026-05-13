import React, { ReactNode } from 'react'
import BaseMap from './Map'
import MarkerClusterLayer from './MarkerClusterLayer'
import GeoJsonMarker from './GeoJsonMarker'
import { ZoomToMarkers } from './ZoomToMarkers'
import { ItemPopup } from './ItemPopup'
import * as countries from './country.json'
import L from 'leaflet'

interface MapProps {
  id: string
  title?: string
  attribution?: string
  baseUrl: string
}

/**
 * Creates a Map component.
 *
 * @param {object} props - The properties for the Map component.
 * @param {string} props.id - The unique identifier for the Map component.
 * @param {string} props.title - The title for the Map component.
 * @returns {React.Element} - The rendered Map component.
 * @throws {Error} - If id is not defined.
 */
export const Map = React.forwardRef<L.Map, MapProps>(function Map({ id, title, ...props }, ref) {
  if (!id) {
    throw new Error('id must be defined when using Map')
  }

  return (
    <div id={id}>
      {title && <h2 className="title">{title}</h2>}
        <div>
          <BaseMap {...props} ref={ref} />
        </div>
    </div>
  )
})

interface Wine {
  location?: GeoJSON.Feature<GeoJSON.Point>
  country?: string
  image?: string
  url?: string
  name?: string
  country_icon?: string
  country_name?: string
  vintage?: string
  [key: string]: unknown
}

interface MapWithMarkersProps extends Omit<MapProps, 'children'> {
  wines: Wine[]
  withoutPopup?: boolean
  children?: ReactNode
}

/**
 * Represents a map component with markers.
 *
 * @param {object} props - The properties to pass to the Map component.
 * @param {Array<object>} points - The array of points to create markers from.
 * @param {boolean} withoutPopup - Indicates whether to exclude the popup for each marker.
 * @param {ReactNode} children - Any additional controls etc. to be added to the map
 * @returns {JSX.Element} - The rendered map component with markers.
 */
export const MapWithMarkers = ({ wines, withoutPopup, children, ...props }: MapWithMarkersProps) => {
  const latLngs: [number, number][] = []
  const markers = wines.map((wine, index) => {
    const feature = { ...(wine.location ?? (countries as any)[wine.country || '']) };
    if (!feature || !feature.geometry) {
        return null
    }
    latLngs.push([feature.geometry.coordinates[1], feature.geometry.coordinates[0]])
    feature.properties = Object.assign(wine, feature.properties)
    return (
      <GeoJsonMarker key={index} feature={feature as GeoJSON.Feature<GeoJSON.Point>}>
          {!withoutPopup && <ItemPopup feature={feature as any} />}
      </GeoJsonMarker>
    )
  })
  return (
    <Map {...props}>
      <ZoomToMarkers points={latLngs} />
      {markers.length > 1 ? (
        <MarkerClusterLayer>{markers}</MarkerClusterLayer>
      ) : (
        markers
      )}
      {children}
    </Map>
  )
}
