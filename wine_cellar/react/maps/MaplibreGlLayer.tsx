import L from 'leaflet'
import '@maplibre/maplibre-gl-leaflet'
import {
  createElementObject,
  createTileLayerComponent,
  type LeafletContextInterface,
  updateGridLayer,
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
  } as any)

  return createElementObject(instance, context)
}

const updateMaplibreGlLayer = (
  instance: any,
  props: MaplibreGlLayerProps,
  prevProps: MaplibreGlLayerProps
) => {
  updateGridLayer(instance, props, prevProps)

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
