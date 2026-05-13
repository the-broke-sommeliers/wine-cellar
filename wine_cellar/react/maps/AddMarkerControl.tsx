import L from 'leaflet'
import { createControlComponent } from '@react-leaflet/core'
import { point, booleanPointInPolygon } from '@turf/turf'
import { makeIcon } from './GeoJsonMarker'

export function checkPointInsidePolygon (marker: L.LatLng, polygons: L.GeoJSON | null) {
  if (!polygons) {
    return true
  }
  const pointGeoJSON = point([marker.lng, marker.lat])
  let isInPolygon = false

  polygons.eachLayer((layer: L.Layer) => {
    const polygonGeoJSON = (layer as any).toGeoJSON()
    if (booleanPointInPolygon(pointGeoJSON, polygonGeoJSON as any)) {
      isInPolygon = true
    }
  })

  return isInPolygon
}

const markerProps = { icon: makeIcon(), draggable: true }

interface AddMarkerControlProps {
  input: HTMLInputElement
  point?: string
  markerConstraints?: GeoJSON.FeatureCollection | GeoJSON.Feature
  onDragEnd?: (isInsideConstraints: boolean) => void
}

export class AddMarkerControlClass extends L.Control {
  marker: L.Marker | null
  oldCoords: L.LatLngExpression | null
  map: L.Map | null
  input: HTMLInputElement
  markerConstraints: L.GeoJSON | null
  onDragEndHandler?: (isInsideConstraints: boolean) => void
  boundClickHandler?: (e: L.LeafletMouseEvent) => void

  constructor ({ input, point, markerConstraints, onDragEnd }: AddMarkerControlProps) {
    super()
    this.marker = null
    this.oldCoords = null
    this.map = null
    this.input = input
    this.markerConstraints = null
    this.onDragEndHandler = onDragEnd

    if (markerConstraints) {
      this.markerConstraints = L.geoJSON(markerConstraints)
    }

    if (point) {
      const pointObj = JSON.parse(point)
      const latlng = pointObj.geometry.coordinates.reverse()
      this.marker = L.marker(latlng, markerProps)
      this.oldCoords = latlng
    }
  }

  updateMarker (latlng: L.LatLng) {
    const isInsideConstraints = checkPointInsidePolygon(latlng, this.markerConstraints)
    if (isInsideConstraints) {
      this.oldCoords = latlng
      if (this.marker) {
        this.marker.setLatLng(latlng)
      } else {
        this.marker = L.marker(latlng, markerProps).addTo(this.map!)
        this.marker.on('dragend', this.onDragend.bind(this))
      }
      this.input.value = JSON.stringify(this.marker.toGeoJSON())
    }

    return isInsideConstraints
  }

  onDragend (e: L.LeafletEvent) {
    const targetPosition = (e.target as L.Marker).getLatLng()
    const isInsideConstraints = checkPointInsidePolygon(targetPosition, this.markerConstraints)
    if (!isInsideConstraints) {
      (e.target as L.Marker).setLatLng(this.oldCoords!)
    } else {
      this.updateMarker(targetPosition)
    }
    this.onDragEndHandler?.(isInsideConstraints)
  }

  addTo (map: L.Map) {
    this.map = map
    this.boundClickHandler = (e: L.LeafletMouseEvent) => this.updateMarker(e.latlng)
    map.on('click', this.boundClickHandler)

    if (this.marker) {
      this.marker.addTo(this.map)
      this.marker.on('dragend', this.onDragend.bind(this))
    }
    return this
  }

  onRemove (map: L.Map) {
    if (this.boundClickHandler) {
      map.off('click', this.boundClickHandler)
    }
    if (this.marker) {
      this.marker.off('dragend', this.onDragend)
      this.marker.remove()
      this.marker = null
    }
  }
}
const createControl = (props: any) => new AddMarkerControlClass(props)

const AddMarkerControl = createControlComponent(createControl)
export default AddMarkerControl
