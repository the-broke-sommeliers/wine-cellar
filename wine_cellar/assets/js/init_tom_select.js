import TomSelect from 'tom-select/dist/js/tom-select.base.js'

function initTomSelect() {
  document.querySelectorAll('select').forEach((el) => {
    const rawConfig = el.dataset.tom_config
    const clear = el.dataset.clear
    const clearOpts = el.dataset.clearOpts
    let config = {
      create: false,
      maxItems: 1,
      // disable search
      controlInput: null
    }
    if (rawConfig) {
      config = JSON.parse(rawConfig)
      if (config.create) {
        config.create = function(input) {
          return { value: 'tom_new_opt' + input, text: input }
        }
      }
    }
    // eslint-disable-next-line
    const ts = new TomSelect(el, config)
    console.log(clear)
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
