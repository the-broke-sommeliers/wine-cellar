type VintageTabsWineCarouselHandle = {
  setImages: (images: string[], fullImages?: string[]) => void
}

function initVintageTabs() {
  const tabs = Array.prototype.slice.call(
    document.querySelectorAll('[data-vintage-tab]')
  ) as HTMLButtonElement[]
  if (!tabs.length) {
    return
  }

  const panels = document.querySelectorAll('[data-vintage-panel]')
  const stockRows = document.querySelectorAll('[data-vintage-row]')
  const stockAddBtn = document.getElementById('stock-add-btn')
  const imgEl = document.getElementById('wine-image') as HTMLImageElement
  const anchor = document.getElementById(
    'wine-image-anchor'
  ) as HTMLAnchorElement
  const actions = document.getElementById('vintage-actions')
  const editBtn = actions?.querySelector(
    '.card__action-btn:not(.card__action-btn--delete)'
  ) as HTMLAnchorElement | null
  const deleteBtn = actions?.querySelector(
    '.card__action-btn--delete'
  ) as HTMLAnchorElement | null

  function activateTab(tab: HTMLButtonElement, focus: boolean) {
    const id = tab.dataset.vintageTab

    tabs.forEach((t) => {
      const active = t === tab
      t.classList.toggle('vintage-tabs__tab--active', active)
      t.setAttribute('aria-selected', active ? 'true' : 'false')
      t.setAttribute('tabindex', active ? '0' : '-1')
    })
    panels.forEach((panel) => {
      const el = panel as HTMLElement
      el.hidden = el.dataset.vintagePanel !== id
    })
    stockRows.forEach((row) => {
      row.classList.toggle(
        'stock-item--other-vintage',
        (row as HTMLElement).dataset.vintageRow !== id
      )
    })
    if (imgEl) {
      imgEl.src = tab.dataset.thumbnail || ''
    }
    if (anchor) {
      anchor.href = tab.dataset.image || ''
    }
    const wineCarousel = (
      window as unknown as { wineCarousel?: VintageTabsWineCarouselHandle }
    ).wineCarousel
    if (wineCarousel) {
      wineCarousel.setImages(
        JSON.parse(tab.dataset.images || '[]'),
        JSON.parse(tab.dataset.imagesFull || '[]')
      )
    }
    if (stockAddBtn && tab.dataset.stockAddUrl) {
      stockAddBtn.setAttribute('href', tab.dataset.stockAddUrl)
    }
    if (editBtn && tab.dataset.editUrl) {
      editBtn.setAttribute('href', tab.dataset.editUrl)
    }
    if (deleteBtn && tab.dataset.deleteUrl) {
      deleteBtn.setAttribute('href', tab.dataset.deleteUrl)
    }
    if (focus) {
      tab.focus()
    }
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => activateTab(tab, false))
    tab.addEventListener('keydown', (event) => {
      let targetIndex: number
      if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
        targetIndex = (index + 1) % tabs.length
      } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
        targetIndex = (index - 1 + tabs.length) % tabs.length
      } else if (event.key === 'Home') {
        targetIndex = 0
      } else if (event.key === 'End') {
        targetIndex = tabs.length - 1
      } else {
        return
      }
      const targetTab = tabs[targetIndex]
      if (!targetTab) {
        return
      }
      event.preventDefault()
      activateTab(targetTab, true)
    })
  })

  // Honor a `?vintage=<pk>` link (e.g. from a barcode scan matching a
  // specific vintage) by pre-selecting that tab instead of the default
  // (newest) one the server rendered as active.
  const requestedVintage = new URLSearchParams(window.location.search).get(
    'vintage'
  )
  if (requestedVintage) {
    const requestedTab = tabs.find(
      (t) => t.dataset.vintageTab === requestedVintage
    )
    if (requestedTab) {
      activateTab(requestedTab, false)
    }
  }
}

document.addEventListener('DOMContentLoaded', initVintageTabs)
