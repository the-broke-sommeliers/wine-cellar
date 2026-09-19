import L from 'leaflet'
import 'leaflet.markercluster'
import {
  createElementObject,
  createLayerComponent,
  extendContext,
  type LeafletContextInterface,
} from '@react-leaflet/core'

const createMarkerClusterLayer = (
  _props: Record<string, unknown>,
  context: LeafletContextInterface
) => {
  const instance = L.markerClusterGroup({ showCoverageOnHover: false })

  return createElementObject(
    instance,
    extendContext(context, { layerContainer: instance })
  )
}

const MarkerClusterLayer = createLayerComponent(createMarkerClusterLayer)
export default MarkerClusterLayer
