import TomSelect from 'tom-select/dist/js/tom-select.base.js'

function initTomSelect() {
  document.querySelectorAll('select').forEach((el) => {
    const rawConfig = el.dataset.tom_config
    let config = {
      create: false,
      maxItems: null
    }
    if (rawConfig) {
      config = JSON.parse(rawConfig)
    }
    // eslint-disable-next-line
    new TomSelect(el, config)
  })
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTomSelect)
} else {
  initTomSelect()
}
