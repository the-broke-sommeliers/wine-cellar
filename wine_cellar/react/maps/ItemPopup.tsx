import React from 'react'
import django from 'django'
import { MapPopup } from './MapPopup'

const translations = {
  country: django.pgettext('Singular', 'Country'),
  image_alt: django.gettext('Picture of a wine bottle.'),
  vintage: django.gettext('Vintage'),
}

interface ItemPopupProps {
  feature: GeoJSON.Feature & {
    properties: {
      image: string
      url: string
      name: string
      country_icon: string
      country_name: string
      vintage?: string
    }
  }
}

/**
 * Renders a popup for an item feature on a map.
 *
 * @param {Object} props - The component props.
 * @param {Object} props.feature - The geojson feature.
 * @returns {JSX.Element} The JSX element representing the popup.
 */
export const ItemPopup = ({ feature }: ItemPopupProps) => {
  return (
    <MapPopup feature={feature}>
      <div className="popup-image">
        <img
          src={feature.properties.image}
          alt={translations.image_alt}
          height="100"
        />
      </div>
      <div className="popup-content">
        <a href={feature.properties.url} className="popup-title">
          {feature.properties.name}
        </a>
        <div className="popup-details">
          <div className="popup-detail">
            <span className="popup-label">{translations.country}:</span>
            <span className="country-info">
              {feature.properties.country_icon}{' '}
              {feature.properties.country_name}
            </span>
          </div>
          {feature.properties.vintage && (
            <div className="popup-detail">
              <span className="popup-label">{translations.vintage}:</span>
              <span>{feature.properties.vintage}</span>
            </div>
          )}
        </div>
      </div>
    </MapPopup>
  )
}
