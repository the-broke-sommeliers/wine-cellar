import L from 'leaflet'
import '@maplibre/maplibre-gl-leaflet'
import {
  createElementObject,
  createTileLayerComponent,
  type LeafletContextInterface,
} from '@react-leaflet/core'

interface MaplibreGlLayerProps {
  attribution?: string
  baseUrl: string
}

const createMaplibreGlLayer = (
  props: MaplibreGlLayerProps,
  context: LeafletContextInterface
) => {
  const instance = L.maplibreGL({
    style: props.baseUrl,
    ...(props.attribution && { attribution: props.attribution }),
  })

  return createElementObject(instance, context)
}

const updateMaplibreGlLayer = (
  instance: L.MaplibreGL,
  props: MaplibreGlLayerProps,
  prevProps: MaplibreGlLayerProps
) => {
  const { baseUrl, attribution } = props
  if (baseUrl != null && baseUrl !== prevProps.baseUrl) {
    instance.getMaplibreMap().setStyle(baseUrl)
  }

  if (attribution != null && attribution !== prevProps.attribution) {
    instance.options.attribution = attribution
  }
}

const MaplibreGlLayer = createTileLayerComponent(
  createMaplibreGlLayer,
  updateMaplibreGlLayer
)
export default MaplibreGlLayer
