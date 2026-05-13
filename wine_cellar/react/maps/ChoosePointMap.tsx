import React, { useRef } from 'react'
import AddMarkerControl from './AddMarkerControl'
import Map from './Map'

interface ChoosePointMapProps {
  BaseMap?: typeof Map
  apiUrl?: string
  input: HTMLInputElement
  point?: string
  polygon?: GeoJSON.FeatureCollection | GeoJSON.Feature
  attribution?: string
  baseUrl: string
  style?: React.CSSProperties
  id?: string
}

const ChoosePointMap = ({ BaseMap = Map, apiUrl, input, ...mapProps }: ChoosePointMapProps) => {
  const mapRef = useRef(null)
  const controlRef = useRef(null)

  return (
    <div className="wine-map">
      <BaseMap {...mapProps} ref={mapRef} id="choose-point">
        <AddMarkerControl
          point={mapProps.point}
          input={input}
          markerConstraints={mapProps.polygon}
          ref={controlRef}
        />
      </BaseMap>
    </div>
  )
}

export default ChoosePointMap
