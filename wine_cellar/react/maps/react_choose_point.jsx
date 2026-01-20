import React from 'react'
import { createRoot } from 'react-dom/client'
import { Map } from './WineMaps'
import ChoosePointMap
  from './ChoosePointMap'

function init() {
  const container = document.getElementById('map_select_point')
  if (container) {
    const props = JSON.parse(container.getAttribute('data-attributes') ?? "")
    const root = createRoot(container)
    root.render(
      <React.StrictMode>
        <ChoosePointMap
          BaseMap={Map}
          input={container.nextElementSibling}
          {...props.map}
          style={{ height: '50vh' }}
        />
      </React.StrictMode>
    )
  }
}

document.addEventListener('DOMContentLoaded', init, false)