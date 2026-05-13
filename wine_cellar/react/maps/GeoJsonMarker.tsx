import L from 'leaflet'
import {
  createElementObject,
  createLayerComponent,
  extendContext,
  LeafletContextInterface
} from '@react-leaflet/core'

export const makeIcon = (iconUrl?: string) =>
  L.icon({
    iconUrl: iconUrl || '/static/images/map_pin.svg',
    iconSize: [30, 36],
    iconAnchor: [15, 36],
    shadowSize: [40, 54],
    shadowAnchor: [20, 54],
    popupAnchor: [0, -10]
  })

interface GeoJsonMarkerProps extends L.MarkerOptions {
  feature: GeoJSON.Feature<GeoJSON.Point>
  children?: React.ReactNode
}

/**
 * Creates a Leaflet marker from a GeoJSON. This is needed to
 * be able to add any Tooltip or Popup to the Markers using JSX.
 */
const createGeoJsonMarker = ({ feature, ...props }: GeoJsonMarkerProps, context: LeafletContextInterface) => {
  const coords = [...feature.geometry.coordinates].reverse() as [number, number]
  const icon = props.icon || makeIcon(feature.properties?.category_icon)
  const propsWithIcon = { ...props, icon }
  const instance = L.marker(coords, propsWithIcon)

  return createElementObject(instance, extendContext(context, { overlayContainer: instance }))
}

const updateGeoJsonMarker = (instance: L.Marker, { feature, ...props }: GeoJsonMarkerProps, prevProps: GeoJsonMarkerProps) => {
  const coords = [...feature.geometry.coordinates].reverse() as [number, number]
  if (props.icon !== prevProps.icon) {
    const icon = props.icon || makeIcon(feature.properties?.category_icon)
    instance.setIcon(icon)
  }
  instance.setLatLng(coords)
}

const GeoJsonMarker = createLayerComponent(createGeoJsonMarker, updateGeoJsonMarker)
export default GeoJsonMarker
