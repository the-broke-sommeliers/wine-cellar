import TomSelect from 'tom-select'
import { TomSettings } from 'tom-select/dist/esm/types/settings.js';
import { RecursivePartial, TomCreateCallback, TomOption } from 'tom-select/dist/esm/types/core.js';


function initTomSelect(): void {
  document.querySelectorAll('select').forEach((el) => {
    const rawConfig: string | undefined = el.dataset.tom_config
    const clear: boolean = Boolean(JSON.parse(el.dataset.clear ?? "false"))
    const clearOpts: boolean = Boolean(JSON.parse(el.dataset.clearOpts ?? "false"))
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
        config.create = function (input: string, create: TomCreateCallback): boolean {
          create({ value: 'tom_new_opt' + input, text: input })
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

    if (!config.create) return

    const itemsArray = Array.isArray(config.items) ? config.items : []

    itemsArray.forEach((value) => {
      const isInteger = Number.isInteger(value)
      const strValue = String(value)

      let optionObj: TomOption | undefined
      if (isInteger) {
        optionObj = Object.values(ts.options).find(
          (opt: any) => opt.value === value || opt.text === strValue
        )
      } else {
        optionObj = Object.values(ts.options).find(
          (opt: any) => opt.text === strValue
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
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTomSelect)
} else {
  initTomSelect()
}
