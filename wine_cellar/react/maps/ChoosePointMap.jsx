import React, { useRef } from 'react'
import AddMarkerControl from './AddMarkerControl'
import Map from './Map'

const ChoosePointMap = ({ BaseMap = Map, apiUrl, input, ...mapProps }) => {
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
