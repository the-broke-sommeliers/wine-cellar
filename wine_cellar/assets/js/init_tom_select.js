import TomSelect from 'tom-select/dist/js/tom-select.base.js'

function initTomSelect() {
  document.querySelectorAll('select').forEach((el) => {
    const rawConfig = el.dataset.tom_config
    const clear = el.dataset.clear
    let config = {
      create: false,
      maxItems: 1,
      // disable search
      controlInput: null
    }
    if (rawConfig) {
      config = JSON.parse(rawConfig)
    }
    // eslint-disable-next-line
    const ts = new TomSelect(el, config)
    if (clear) {
      ts.clear()
    }
  })
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTomSelect)
} else {
  initTomSelect()
}
