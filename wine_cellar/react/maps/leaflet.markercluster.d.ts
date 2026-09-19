import * as L from 'leaflet'

declare module 'leaflet' {
  interface MarkerClusterGroupOptions extends L.FeatureGroupOptions {
    showCoverageOnHover?: boolean
  }

  class MarkerClusterGroup extends L.FeatureGroup {
    constructor(options?: MarkerClusterGroupOptions)
  }

  function markerClusterGroup(
    options?: MarkerClusterGroupOptions
  ): MarkerClusterGroup
}
