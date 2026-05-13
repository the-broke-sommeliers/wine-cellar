import React, { useImperativeHandle, ReactNode } from 'react'
import { MapContainer, MapContainerProps, useMap } from 'react-leaflet'
import MaplibreGlLayer from './MaplibreGlLayer'
import L from 'leaflet'

interface MapProps extends Omit<MapContainerProps, 'children'> {
  attribution?: string
  baseUrl: string
  polygon?: GeoJSON.FeatureCollection | GeoJSON.Feature
  omtToken?: string
  children?: ReactNode
}

const Map = React.forwardRef<L.Map, MapProps>(function Map(
  { attribution, baseUrl, polygon, omtToken, children, ...rest },
  ref
) {
  const MapLayers = () => {
    const map = useMap()
    useImperativeHandle(ref, () => map)
    return (
      <>
        <MaplibreGlLayer attribution={attribution} baseUrl={baseUrl} />
      </>
    )
  }

  return (
    <MapContainer
      style={{ minHeight: "60vh" }}
      zoom={2}
      maxZoom={18}
      {...rest}
      center={[52.520008, 13.404954]}
    >
      <MapLayers />
      {children}
    </MapContainer>
  )
})

export default Map
