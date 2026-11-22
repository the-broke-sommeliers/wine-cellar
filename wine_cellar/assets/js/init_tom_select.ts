import TomSelect from 'tom-select'
import type {
  RecursivePartial,
  TomCreateCallback,
  TomOption,
} from 'tom-select/dist/esm/types/core.js'
import type { TomSettings } from 'tom-select/dist/esm/types/settings.js'

// Debounce function to delay form submission
function debounce(callback: () => void, delay: number): () => void {
  let timeoutId: number | null = null
  return () => {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
    timeoutId = setTimeout(callback, delay)
  }
}

function submitForm(form: HTMLFormElement): void {
  if (form.requestSubmit) {
    form.requestSubmit()
  } else {
    form.submit()
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
    // Only offer a clear button where clearing leaves a valid value:
    // multi-selects (deselecting all is fine) or selects that already
    // render a blank option (so there's something to clear to). Required
    // single-selects with no blank option (e.g. wine_type, country) are
    // left alone.
    const hasEmptyOption = Array.from(el.options).some((o) => o.value === '')
    if (el.multiple || hasEmptyOption) {
      config.plugins = ['clear_button']
    }

    const ts = new TomSelect(el, config)
    if (clear) {
      ts.clear()
    }
    if (clearOpts) {
      ts.clearOptions()
    }

    // Auto-submit filter form on dropdown change
    const filterForm = el.closest('.filter-form') as HTMLFormElement | null
    if (filterForm) {
      ts.on('change', () => submitForm(filterForm))
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
  document
    .querySelectorAll('.filter-form input[type="text"]')
    .forEach((element) => {
      const input = element as HTMLInputElement
      const filterForm = input.closest('.filter-form') as HTMLFormElement | null
      if (filterForm) {
        const debouncedSubmit = debounce(() => submitForm(filterForm), 700)

        input.addEventListener('input', debouncedSubmit)
      }
    })
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTomSelect)
} else {
  initTomSelect()
}
