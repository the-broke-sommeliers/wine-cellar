import {
  createElementObject,
  createLayerComponent,
  extendContext,
  type LeafletContextInterface,
} from '@react-leaflet/core'
import L from 'leaflet'

const PIN_IN_STOCK = '/static/images/map_pin.svg'
const PIN_OUT_OF_STOCK = '/static/images/map_pin_out_of_stock.svg'

export const makeIcon = (iconUrl?: string, inStock?: boolean) =>
  L.icon({
    iconUrl: iconUrl || (inStock ? PIN_IN_STOCK : PIN_OUT_OF_STOCK),
    iconSize: [30, 36],
    iconAnchor: [15, 36],
    shadowSize: [40, 54],
    shadowAnchor: [20, 54],
    popupAnchor: [0, -10],
  })

interface GeoJsonMarkerProps extends L.MarkerOptions {
  feature: GeoJSON.Feature<GeoJSON.Point>
  children?: React.ReactNode
}

/**
 * Creates a Leaflet marker from a GeoJSON. This is needed to
 * be able to add any Tooltip or Popup to the Markers using JSX.
 */
const iconFor = (
  feature: GeoJSON.Feature<GeoJSON.Point>,
  explicitIcon?: L.Icon
): L.Icon =>
  explicitIcon ||
  makeIcon(
    feature.properties?.category_icon,
    (feature.properties?.total_stock ?? 0) > 0
  )

const createGeoJsonMarker = (
  { feature, ...props }: GeoJsonMarkerProps,
  context: LeafletContextInterface
) => {
  const coords = [...feature.geometry.coordinates].reverse() as [number, number]
  const propsWithIcon = {
    ...props,
    icon: iconFor(feature, props.icon as L.Icon | undefined),
  }
  const instance = L.marker(coords, propsWithIcon)

  return createElementObject(
    instance,
    extendContext(context, { overlayContainer: instance })
  )
}

const updateGeoJsonMarker = (
  instance: L.Marker,
  { feature, ...props }: GeoJsonMarkerProps,
  _prevProps: GeoJsonMarkerProps
) => {
  const coords = [...feature.geometry.coordinates].reverse() as [number, number]
  instance.setIcon(iconFor(feature, props.icon as L.Icon | undefined))
  instance.setLatLng(coords)
}

const GeoJsonMarker = createLayerComponent(
  createGeoJsonMarker,
  updateGeoJsonMarker
)
export default GeoJsonMarker
