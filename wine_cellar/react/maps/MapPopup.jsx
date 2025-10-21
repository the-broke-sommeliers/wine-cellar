import React from 'react'
import { Popup } from 'react-leaflet'

export const MapPopup = ({ feature, className, children, ...rest }) => {
  const _className = 'maps-popups ' + (className ?? '')
  return (
    <Popup {...rest} className={_className}>
      <div className="maps-popups-popup-text-content">
        {children}
      </div>
    </Popup>
  )
}
