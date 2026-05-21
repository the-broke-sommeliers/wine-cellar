function initStockDrag() {
  const table = document.querySelector(
    '.card__table'
  ) as HTMLTableElement | null
  if (!table) {
    return
  }

  const swapUrl = table.dataset.swapUrl
  if (!swapUrl) {
    return
  }

  let draggedRow: HTMLTableRowElement | null = null

  function getDropTarget(target: HTMLElement): HTMLTableRowElement | null {
    const row = target.closest('tr') as HTMLTableRowElement | null
    if (!row) {
      return null
    }
    // Accept draggable rows (items) or empty slot rows
    if (
      row.hasAttribute('data-item-id') ||
      row.classList.contains('card__table-empty')
    ) {
      return row
    }
    return null
  }

  table.addEventListener('dragstart', (e: DragEvent) => {
    const row = (e.target as HTMLElement).closest(
      'tr[draggable="true"]'
    ) as HTMLTableRowElement | null
    if (!row) {
      e.preventDefault()
      return
    }
    draggedRow = row
    row.classList.add('dragging')
    const dt = e.dataTransfer
    if (dt) {
      dt.effectAllowed = 'move'
    }
  })

  table.addEventListener('dragend', () => {
    if (draggedRow) {
      draggedRow.classList.remove('dragging')
    }
    for (const r of table.querySelectorAll('tr.drag-over')) {
      r.classList.remove('drag-over')
    }
    draggedRow = null
  })

  table.addEventListener('dragover', (e: DragEvent) => {
    e.preventDefault()
    const dt = e.dataTransfer
    if (dt) {
      dt.dropEffect = 'move'
    }
    const row = getDropTarget(e.target as HTMLElement)
    if (row && row !== draggedRow) {
      for (const r of table.querySelectorAll('tr.drag-over')) {
        r.classList.remove('drag-over')
      }
      row.classList.add('drag-over')
    }
  })

  table.addEventListener('drop', (e: DragEvent) => {
    e.preventDefault()
    const targetRow = getDropTarget(e.target as HTMLElement)
    const sourceRow = draggedRow
    if (!targetRow || !sourceRow || targetRow === sourceRow) {
      return
    }

    const item1 = sourceRow.dataset.itemId
    if (!item1) {
      return
    }

    // Check same-storage: compare the source's storage info against target
    // For item rows, the item is in the same storage (single storage view)
    // For empty slots, the storage id is on the row

    const formData = new FormData()
    formData.append('item1', item1)

    if (targetRow.classList.contains('card__table-empty')) {
      // Dropping on an empty slot
      const slotStorage = table.dataset.storage
      const slotRow = targetRow.dataset.row
      const slotCol = targetRow.dataset.column
      if (!slotStorage || !slotRow || !slotCol) {
        return
      }
      formData.append('storage', slotStorage)
      formData.append('row', slotRow)
      formData.append('column', slotCol)
    } else {
      // Dropping on another item (insert and shift)
      const item2 = targetRow.dataset.itemId
      if (!item2) {
        return
      }
      formData.append('item2', item2)
    }

    fetch(swapUrl, {
      method: 'POST',
      body: formData,
      headers: { 'X-CSRFToken': getCsrfToken() },
    })
      .then((res) => {
        if (res.ok) {
          window.location.reload()
        }
      })
      .catch(() => undefined)
  })

  function getCsrfToken(): string {
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/)
    return match?.[1] ?? ''
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initStockDrag)
} else {
  initStockDrag()
}
