import React from 'react'
import { createRoot } from 'react-dom/client'
// @ts-ignore
import { MapWithMarkers, Map } from './WineMaps'

function init() {
  const container = document.getElementById('wine_map')
  if (container) {
    const props = JSON.parse(container.getAttribute('data-attributes') ?? "")
    const root = createRoot(container)
    root.render(
      <React.StrictMode>
        <MapWithMarkers
          {...props.map}
          wines={props.wines}
          id="display-point"
        />
      </React.StrictMode>
    )
  }
}

document.addEventListener('DOMContentLoaded', init, false)
