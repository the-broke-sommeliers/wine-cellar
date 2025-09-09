
interface FreeCells {
    [storageId: string]: {
        free_rows: number[]
        free_columns: number[]
    }
}


function showWarning() {
    const warning = document.getElementById('storage__error-full')
    warning?.classList.remove('hidden')
}

function hideWarning() {
    const warning = document.getElementById('storage__error-full')
    warning?.classList.add('hidden')
}

function updateStorageCells() {
    const storageSelect = document.getElementById('id_storage') as HTMLSelectElement
    const rowSelect = document.getElementById('id_row') as HTMLSelectElement
    const columnSelect = document.getElementById('id_column') as HTMLSelectElement
    const submitButton = document.getElementById('submit_button') as HTMLButtonElement

    const storageData = document.getElementById('storage-data')!
    const freeCells: FreeCells = JSON.parse(storageData.dataset.attributes || '{}')

    if (storageSelect) {
        storageSelect.addEventListener('change', updateRowAndColumn)
        updateRowAndColumn()
    }

    function toggleFields(disable: boolean, submit: boolean = false) {
        rowSelect.disabled = disable
        columnSelect.disabled = disable
        if (disable) {
            // @ts-ignore
            rowSelect.tomselect.disable()
            // @ts-ignore
            columnSelect.tomselect.disable()
            if (submit) {
                submitButton.disabled = true
            }
        } else {
            // @ts-ignore
            rowSelect.tomselect.enable()
            // @ts-ignore
            columnSelect.tomselect.enable()
            submitButton.disabled = false
        }
    }

    function populateSelect(select: HTMLSelectElement, options: number[]) {
        select.innerHTML = ''
        options.forEach(function (val) {
            const opt = document.createElement('option')
            opt.value = String(val)
            opt.textContent = String(val)
            select.appendChild(opt)
        })
        // @ts-ignore
        select.tomselect.clearOptions()
        options.forEach(function (val) {
            // @ts-ignore
            select.tomselect.addOption({ value: val, text: val })
        })
        // @ts-ignore
        select.tomselect.refreshOptions(false)
    }

    function updateRowAndColumn() {
        const storageId = storageSelect.value
        const cellInfo = freeCells[storageId]
        if (cellInfo) {
            const hasRows = Array.isArray(cellInfo.free_rows) && cellInfo.free_rows.length > 0
            const hasColumns = Array.isArray(cellInfo.free_columns) && cellInfo.free_columns.length > 0
            if (hasRows && hasColumns) {
                populateSelect(rowSelect, cellInfo.free_rows)
                populateSelect(columnSelect, cellInfo.free_columns)
                hideWarning()
                toggleFields(false)
            } else {
                const isFull = cellInfo.free_rows != null && cellInfo.free_columns != null
                populateSelect(rowSelect, [])
                populateSelect(columnSelect, [])
                toggleFields(true, isFull)
                if (isFull) {
                    showWarning()
                }
            }
        }
    }
}


document.addEventListener('DOMContentLoaded', updateStorageCells)