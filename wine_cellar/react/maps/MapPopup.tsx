import type { ReactNode } from 'react'
import { Popup, type PopupProps } from 'react-leaflet'

interface MapPopupProps extends Omit<PopupProps, 'children'> {
  feature: GeoJSON.Feature
  className?: string
  children: ReactNode
}

export const MapPopup = ({
  feature,
  className,
  children,
  ...rest
}: MapPopupProps) => {
  const _className = `maps-popups ${className ?? ''}`
  return (
    <Popup {...rest} className={_className}>
      <div className="maps-popups-popup-text-content">{children}</div>
    </Popup>
  )
}
