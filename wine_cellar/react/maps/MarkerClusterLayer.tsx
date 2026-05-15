import L from 'leaflet'
import 'leaflet.markercluster'
import {
  createElementObject,
  createLayerComponent,
  extendContext,
  type LeafletContextInterface,
  updateGridLayer,
} from '@react-leaflet/core'

const createMarkerClusterLayer = (
  _props: Record<string, unknown>,
  context: LeafletContextInterface
) => {
  const instance = (L as any).markerClusterGroup({ showCoverageOnHover: false })

  return createElementObject(
    instance,
    extendContext(context, { layerContainer: instance })
  )
}

const updateMarkerClusterLayer = (
  instance: any,
  props: Record<string, unknown>,
  prevProps: Record<string, unknown>
) => {
  updateGridLayer(instance, props, prevProps)
}

const MarkerClusterLayer = createLayerComponent(
  createMarkerClusterLayer,
  updateMarkerClusterLayer
)
export default MarkerClusterLayer
