type CellState = 'free' | 'occupied' | 'current'

interface GridCell {
  row: number
  column: number
  state: CellState
}

interface UnlimitedStorage {
  unlimited: true
}

interface GridStorage {
  unlimited: false
  rows: number
  columns: number
  swap_axes: boolean
  row_labels: Record<string, string>
  column_labels: Record<string, string>
  cells: GridCell[]
}

type StoragePayload = UnlimitedStorage | GridStorage

interface StorageCellsData {
  [storageId: string]: StoragePayload
}

function cellKey(row: number, column: number) {
  return `${row},${column}`
}

function initStockPicker() {
  const storageSelect = document.getElementById(
    'id_storage'
  ) as HTMLSelectElement | null
  const quantityInput = document.getElementById(
    'id_quantity'
  ) as HTMLInputElement | null
  const slotsInput = document.getElementById(
    'id_slots'
  ) as HTMLInputElement | null
  const submitButton = document.getElementById(
    'submit_button'
  ) as HTMLButtonElement | null
  const picker = document.getElementById('grid-picker')
  const table = document.getElementById(
    'grid-picker__table'
  ) as HTMLTableElement | null
  const autofillButton = document.getElementById(
    'grid-picker__autofill'
  ) as HTMLButtonElement | null
  const counter = document.getElementById('grid-picker__count')
  const capacityWarning = document.getElementById('grid-picker__error-full')
  const storageData = document.getElementById('storage-data')

  if (!storageSelect || !slotsInput || !submitButton || !picker || !table) {
    console.error('stock picker: required elements not found')
    return
  }
  if (!storageData) {
    console.error('storage-data element not found')
    return
  }

  const mode: 'single' | 'multi' =
    picker.dataset.mode === 'single' ? 'single' : 'multi'
  const payload: StorageCellsData = JSON.parse(
    storageData.dataset.attributes || '{}'
  )
  const selected = new Set<string>()

  function updateSlotsInput() {
    if (!slotsInput) {
      return
    }
    slotsInput.value = JSON.stringify(
      Array.from(selected, (key) => key.split(',').map(Number))
    )
  }

  function updateCounter() {
    if (!counter) {
      return
    }
    const count = selected.size
    counter.textContent = interpolate(
      ngettext('%s bottle selected', '%s bottles selected', count),
      [count]
    )
  }

  function updateSubmit(isGrid: boolean) {
    if (!submitButton) {
      return
    }
    submitButton.disabled = isGrid && selected.size === 0
  }

  function deselectAll() {
    selected.forEach((key) => {
      table
        ?.querySelector(`[data-key="${key}"]`)
        ?.classList.remove('grid-picker__cell--selected')
    })
    selected.clear()
  }

  function selectCell(button: HTMLButtonElement, row: number, column: number) {
    const key = cellKey(row, column)
    if (mode === 'multi') {
      if (selected.has(key)) {
        selected.delete(key)
        button.classList.remove('grid-picker__cell--selected')
      } else {
        selected.add(key)
        button.classList.add('grid-picker__cell--selected')
      }
    } else {
      if (selected.has(key)) {
        return
      }
      deselectAll()
      selected.add(key)
      button.classList.add('grid-picker__cell--selected')
    }
    updateSlotsInput()
    updateCounter()
    updateSubmit(true)
  }

  function renderGrid(storage: GridStorage) {
    selected.clear()
    if (!table) {
      return
    }
    table.innerHTML = ''

    const rows = new Map<number, GridCell[]>()
    storage.cells.forEach((cell) => {
      const rowCells = rows.get(cell.row) ?? []
      rowCells.push(cell)
      rows.set(cell.row, rowCells)
    })

    const thead = table.createTHead()
    const headRow = thead.insertRow()
    headRow.insertCell()
    for (let column = 1; column <= storage.columns; column++) {
      const th = document.createElement('th')
      const label = storage.column_labels[String(column)]
      th.textContent = label ? `${column} (${label})` : String(column)
      headRow.appendChild(th)
    }

    const tbody = table.createTBody()
    for (let row = 1; row <= storage.rows; row++) {
      const tr = tbody.insertRow()
      const rowHeader = document.createElement('th')
      const rowLabel = storage.row_labels[String(row)]
      rowHeader.textContent = rowLabel ? `${row} (${rowLabel})` : String(row)
      tr.appendChild(rowHeader)

      const cellsInRow = (rows.get(row) ?? []).sort(
        (a, b) => a.column - b.column
      )
      cellsInRow.forEach((cell) => {
        const td = tr.insertCell()
        const button = document.createElement('button')
        button.type = 'button'
        button.dataset.key = cellKey(cell.row, cell.column)
        button.classList.add('grid-picker__cell')
        if (cell.state === 'occupied') {
          button.classList.add('grid-picker__cell--occupied')
          button.disabled = true
        } else {
          button.addEventListener('click', () =>
            selectCell(button, cell.row, cell.column)
          )
        }
        td.appendChild(button)
        if (cell.state === 'current') {
          selectCell(button, cell.row, cell.column)
        }
      })
    }

    if (quantityInput) {
      const freeCount = storage.cells.filter(
        (cell) => cell.state !== 'occupied'
      ).length
      quantityInput.max = String(freeCount)
    }
    updateSlotsInput()
    updateCounter()
    updateSubmit(true)
  }

  function showPicker(show: boolean) {
    picker?.classList.toggle('hidden', !show)
  }

  function hideCapacityWarning() {
    capacityWarning?.classList.add('hidden')
  }

  const render = () => {
    const storage = payload[storageSelect.value]
    slotsInput.value = '[]'
    selected.clear()
    hideCapacityWarning()
    if (!storage || storage.unlimited) {
      showPicker(false)
      updateSubmit(false)
      return
    }
    showPicker(true)
    renderGrid(storage)
  }

  autofillButton?.addEventListener('click', () => {
    const storage = payload[storageSelect.value]
    if (!storage || storage.unlimited) {
      return
    }
    deselectAll()
    const requested = Number(quantityInput?.value) || 1
    const freeCells = storage.cells.filter((cell) => cell.state !== 'occupied')
    freeCells.slice(0, requested).forEach((cell) => {
      const key = cellKey(cell.row, cell.column)
      const button = table.querySelector(
        `[data-key="${key}"]`
      ) as HTMLButtonElement | null
      if (button) {
        selected.add(key)
        button.classList.add('grid-picker__cell--selected')
      }
    })
    capacityWarning?.classList.toggle('hidden', requested <= freeCells.length)
    updateSlotsInput()
    updateCounter()
    updateSubmit(true)
  })

  storageSelect.addEventListener('change', render)
  render()
}

document.addEventListener('DOMContentLoaded', initStockPicker)
