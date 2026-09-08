import django from 'django'
import type L from 'leaflet'
import React, { type ReactNode, useEffect, useState } from 'react'
import * as countries from './country.json'
import GeoJsonMarker from './GeoJsonMarker'
import { ItemPopup } from './ItemPopup'
import BaseMap from './Map'
import MarkerClusterLayer from './MarkerClusterLayer'
import { useMapFilters } from './useMapFilters'
import { ZoomToMarkers } from './ZoomToMarkers'

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
export const Map = React.forwardRef<L.Map, MapProps>(function Map(
  { id, title, ...props },
  ref
) {
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
  total_stock?: number
  [key: string]: unknown
}

interface MapWithMarkersProps extends Omit<MapProps, 'children'> {
  wines?: Wine[]
  dataUrl?: string
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
export const MapWithMarkers = ({
  wines: staticWines,
  dataUrl,
  withoutPopup,
  children,
  ...props
}: MapWithMarkersProps) => {
  const search = useMapFilters()
  const [fetchedWines, setFetchedWines] = useState<Wine[]>([])
  const [loading, setLoading] = useState(Boolean(dataUrl))
  const [error, setError] = useState(false)
  const [hasFetchedOnce, setHasFetchedOnce] = useState(false)

  useEffect(() => {
    if (!dataUrl) {
      return
    }
    const controller = new AbortController()
    setLoading(true)
    setError(false)
    fetch(`${dataUrl}${search}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Unexpected response: ${response.status}`)
        }
        return response.json() as Promise<{ wines: Wine[] }>
      })
      .then((data) => {
        setFetchedWines(data.wines)
        setLoading(false)
        setHasFetchedOnce(true)
      })
      .catch((_err: unknown) => {
        if (controller.signal.aborted) {
          return
        }
        setError(true)
        setLoading(false)
        setHasFetchedOnce(true)
      })
    return () => controller.abort()
  }, [dataUrl, search])

  const wines = dataUrl ? fetchedWines : (staticWines ?? [])

  const latLngs: [number, number][] = []
  const markers = wines.map((wine, index) => {
    const feature = {
      ...(wine.location ?? (countries as any)[wine.country || '']),
    }
    if (!feature?.geometry) {
      return null
    }
    latLngs.push([
      feature.geometry.coordinates[1],
      feature.geometry.coordinates[0],
    ])
    feature.properties = Object.assign(wine, feature.properties)
    return (
      <GeoJsonMarker
        key={index}
        feature={feature as GeoJSON.Feature<GeoJSON.Point>}
      >
        {!withoutPopup && <ItemPopup feature={feature as any} />}
      </GeoJsonMarker>
    )
  })

  const isInitialLoad = dataUrl && loading && !hasFetchedOnce
  const isRefetching = dataUrl && loading && hasFetchedOnce
  const isEmpty =
    dataUrl && !loading && !error && hasFetchedOnce && wines.length === 0

  return (
    <div className="map-with-markers">
      <Map {...props}>
        <ZoomToMarkers points={latLngs} />
        {markers.length > 1 ? (
          <MarkerClusterLayer>{markers}</MarkerClusterLayer>
        ) : (
          markers
        )}
        {children}
      </Map>

      {isInitialLoad && (
        <div className="map-loading-overlay">
          <span className="map-spinner" />
          <span>{django.gettext('Loading your wines…')}</span>
        </div>
      )}

      {isRefetching && (
        <div className="map-refetch-pill">
          <span className="map-spinner map-spinner--small" />
          {django.gettext('Updating…')}
        </div>
      )}

      {error && (
        <div className="map-error-banner">
          <i
            className="fa-solid fa-triangle-exclamation"
            aria-hidden="true"
          ></i>
          {django.gettext("Couldn't load your wines. Please try again.")}
        </div>
      )}

      {isEmpty && (
        <div className="map-empty-overlay">
          <i className="fa-solid fa-wine-bottle" aria-hidden="true"></i>
          <p className="map-empty-overlay__title">
            {django.gettext('No wines match your filters')}
          </p>
        </div>
      )}
    </div>
  )
}
