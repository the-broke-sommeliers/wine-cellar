import TomSelect from 'tom-select'

import { RecursivePartial, TomCreateCallback, TomSettings } from 'tom-select/dist/types/types'

function initTomSelect (): void {
  document.querySelectorAll('select').forEach((el) => {
    const rawConfig : string | undefined = el.dataset.tom_config
    const clear : boolean = Boolean(JSON.parse(el.dataset.clear ?? "false"))
    const clearOpts : boolean = Boolean(JSON.parse(el.dataset.clearOpts ?? "false"))
    let config : RecursivePartial<TomSettings> = {
      create: false,
      closeAfterSelect: true,
      maxItems: 1,
      // disable search
      controlInput: '',
    }
    if (rawConfig) {
      config = JSON.parse(rawConfig)
      if (config.create) {
        config.create = function (input:string,create:TomCreateCallback) : boolean  {
          create({value: 'tom_new_opt' + input, text: input })
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
  })
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTomSelect)
} else {
  initTomSelect()
}
