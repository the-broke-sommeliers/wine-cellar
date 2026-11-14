import TomSelect from 'tom-select'
import type {
  RecursivePartial,
  TomCreateCallback,
  TomOption,
} from 'tom-select/dist/esm/types/core.js'
import type { TomSettings } from 'tom-select/dist/esm/types/settings.js'

// Debounce function to delay form submission
function debounce(callback: () => void, delay: number): ((...args: any[]) => void) {
  let timeoutId: number | null = null
  return () => {
    if (timeoutId) clearTimeout(timeoutId)
    timeoutId = setTimeout(callback, delay)
  }
}

function initTomSelect(): void {
  document.querySelectorAll('select').forEach((el) => {
    const rawConfig: string | undefined = el.dataset.tom_config
    const clear: boolean = Boolean(JSON.parse(el.dataset.clear ?? 'false'))
    const clearOpts: boolean = Boolean(
      JSON.parse(el.dataset.clearOpts ?? 'false')
    )
    let config: RecursivePartial<TomSettings> = {
      create: false,
      closeAfterSelect: true,
      maxItems: 1,
      // disable search
      controlInput: '',
    }
    if (rawConfig) {
      config = JSON.parse(rawConfig)
      if (config.create) {
        config.create = (input: string, create: TomCreateCallback): boolean => {
          create({ value: `tom_new_opt${input}`, text: input })
          return true
        }
      }
    }
    const ts = new TomSelect(el, config)
    if (clear) {
      ts.clear()
    }
    if (clearOpts) {
      ts.clearOptions()
    }

    // Add clear button to the TomSelect control
    const controlEl = ts.control
    if (controlEl) {
      const clearBtn = document.createElement('button')
      clearBtn.type = 'button'
      clearBtn.className = 'ts-clear'
      clearBtn.innerHTML = '×'
      clearBtn.style.cssText = 'position: absolute; right: 8px; top: 50%; transform: translateY(-50%); background: none; border: none; font-size: 20px; cursor: pointer; padding: 0; color: #999; display: none;'
      
      clearBtn.addEventListener('click', (e) => {
        e.preventDefault()
        e.stopPropagation()
        ts.clear()
      })
      controlEl.style.position = 'relative'
      controlEl.appendChild(clearBtn)

      // Show clear button only if there's any value selected
      const toggleClearBtn = () => {
        const value = ts.getValue()
        // For multi-select, getValue() returns array; for single-select, returns string/number
        const hasValue = Array.isArray(value) ? value.length > 0 : Boolean(value && value !== '')
        clearBtn.style.display = hasValue ? 'block' : 'none'
      }
      toggleClearBtn()
      ts.on('change', toggleClearBtn)
    }

    // Auto-submit filter form on dropdown change
    const filterForm = el.closest('.filter-form') as HTMLFormElement | null
    if (filterForm) {
      ts.on('change', () => {
        filterForm.requestSubmit?.() ?? filterForm.submit()
      })
    }

    if (!config.create) {
      return
    }

    const itemsArray = Array.isArray(config.items) ? config.items : []

    itemsArray.forEach((value) => {
      const isInteger = Number.isInteger(value)
      const strValue = String(value)

      let optionObj: TomOption | undefined
      if (isInteger) {
        optionObj = Object.values(ts.options).find(
          (opt: TomOption) => opt.value === value || opt.text === strValue
        )
      } else {
        optionObj = Object.values(ts.options).find(
          (opt: TomOption) => opt.text === strValue
        )
      }

      const itemExists = ts.getItem(optionObj?.value ?? strValue) !== null

      if (optionObj) {
        if (!itemExists) {
          ts.addItem(optionObj.value)
        }
      } else if (!optionObj && !itemExists && config.create) {
        ts.createItem(strValue)
      }
    })
  })

  // Auto-submit filter form on text input change with debounce
  document.querySelectorAll('.filter-form input[type="text"]').forEach((element) => {
    const input = element as HTMLInputElement
    const filterForm = input.closest('.filter-form') as HTMLFormElement | null
    if (filterForm) {
      const debouncedSubmit = debounce(() => {
        filterForm.requestSubmit?.() ?? filterForm.submit()
      }, 700)
      
      input.addEventListener('input', debouncedSubmit)
    }
  })
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTomSelect)
} else {
  initTomSelect()
}
