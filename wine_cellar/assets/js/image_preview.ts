function initImagePreview() {
  document.querySelectorAll('input[type="file"]').forEach((inputEl) => {
    const input = inputEl as HTMLInputElement
    const preview = input
      .closest('.form-container')
      ?.querySelector('.image-preview') as HTMLImageElement | null
    const hasInitial = preview?.src !== ''
    console.log(hasInitial)
    const wrapper = preview?.parentElement
    const clearCheckbox = input
      .closest('.form-container')
      ?.querySelector('.image-clear-checkbox') as HTMLInputElement | null

    input.addEventListener('change', (e: Event) => {
      const file = input.files?.[0]
      if (!file || !file.type.startsWith('image/')) {
        if (wrapper && !wrapper.className.includes('hidden')) {
          wrapper.classList.add('hidden')
        }
        return
      }

      const reader = new FileReader()
      reader.onload = () => {
        if (preview && reader.result) {
          if (wrapper && wrapper.className.includes('hidden')) {
            wrapper.classList.remove('hidden')
          }
          preview.src = reader.result as string
          if (clearCheckbox && clearCheckbox.checked) {
            clearCheckbox.checked = false
          }
        }
      }
      reader.readAsDataURL(file)
    })

    if (clearCheckbox && preview) {
      const setClearControlLabels = (checked: boolean) => {
        const clearTitle = gettext('Clear Image')
        const restoreTitle = gettext('Restore image')
        const title = checked ? restoreTitle : clearTitle
        clearCheckbox.title = title
        clearCheckbox.setAttribute('aria-label', title)
        clearCheckbox.setAttribute('aria-pressed', checked ? 'true' : 'false')
      }

      setClearControlLabels(!!clearCheckbox.checked)

      clearCheckbox.addEventListener('change', () => {
        if (clearCheckbox.checked) {
          preview.dataset.originalSrc = preview.src || ''
          preview.src = ''
          if (!hasInitial) {
            if (wrapper && !wrapper.className.includes('hidden')) {
              wrapper.classList.add('hidden')
            }
          }
        } else {
          if (preview.dataset.originalSrc) {
            preview.src = preview.dataset.originalSrc
            delete preview.dataset.originalSrc
          }
        }
        setClearControlLabels(!!clearCheckbox.checked)
      })
      if (clearCheckbox.checked && hasInitial) {
        clearCheckbox.dispatchEvent(new Event('change', { bubbles: true }))
      }
    }
  })
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initImagePreview)
} else {
  initImagePreview()
}
