
interface FreeCells {
    [storageId: string]: {
        [rows: string]: number[]
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
        storageSelect.addEventListener('change', updateRows)
    }
    if (rowSelect) {
        rowSelect.addEventListener('change', updateColumns)
    }
    if (columnSelect) {
        columnSelect.addEventListener('change', updateSubmit)
    }

    function toggleFields(disable: boolean, submit: boolean = false) {
        rowSelect.disabled = disable
        columnSelect.disabled = disable
        if (disable) {
            rowSelect.tomselect?.disable()
            columnSelect.tomselect?.disable()
        } else {
            rowSelect.tomselect?.enable()
            columnSelect.tomselect?.enable()
        }
        submitButton.disabled = !submit
    }

    function populateSelect(select: HTMLSelectElement, options: number[]) {
        select.innerHTML = ''
        options.forEach(function (val) {
            const opt = document.createElement('option')
            opt.value = String(val)
            opt.textContent = String(val)
            select.appendChild(opt)
        })
        select.tomselect?.clear(true)
        select.tomselect?.clearOptions()
        options.forEach(function (val) {
            select.tomselect?.addOption({ value: val, text: val })
        })
        select.tomselect?.refreshOptions(false)
    }

    function updateSubmit() {
        submitButton.disabled = columnSelect.value === ''
    }   

    function updateColumns() {
        const storageId = storageSelect.value
        const rowId = rowSelect.value
        const columns = freeCells[storageId][rowId]
        if (columns.length > 0) {
            populateSelect(columnSelect, columns)
            hideWarning()
        } else {
            showWarning()
            populateSelect(columnSelect, [])
        }
        toggleFields(false, false)
    }

    function updateRows() {
        const storageId = storageSelect.value
        const rows = freeCells[storageId]
        const unlimitedShelf = Object.keys(rows).length === 0
        if (!unlimitedShelf) {
            const rowKeys = Object.keys(rows).map(Number)
            populateSelect(rowSelect, rowKeys)
            populateSelect(columnSelect, [])
            toggleFields(false, false)
        } else {
            populateSelect(rowSelect, [])
            populateSelect(columnSelect, [])
            toggleFields(true, true)
        }
    }
}


document.addEventListener('DOMContentLoaded', updateStorageCells)