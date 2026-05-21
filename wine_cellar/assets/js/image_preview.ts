function initImagePreview() {
  document.querySelectorAll('input[type="file"]').forEach((inputEl) => {
    const input = inputEl as HTMLInputElement
    const container = input.closest('.form-container')
    const preview = container?.querySelector(
      '.image-preview'
    ) as HTMLImageElement | null
    const hasInitial = preview?.src !== ''
    const wrapper = preview?.parentElement
    const clearCheckbox = container?.querySelector(
      '.image-clear-checkbox'
    ) as HTMLInputElement | null
    const clearBtn = container?.querySelector(
      '.image-clear-btn'
    ) as HTMLButtonElement | null

    if (clearBtn && clearCheckbox) {
      clearBtn.addEventListener('click', () => {
        clearCheckbox.checked = !clearCheckbox.checked
        clearCheckbox.dispatchEvent(new Event('change', { bubbles: true }))
      })
    }

    input.addEventListener('change', (_e: Event) => {
      const file = input.files?.[0]
      if (!file?.type.startsWith('image/')) {
        if (wrapper && !wrapper.className.includes('hidden')) {
          wrapper.classList.add('hidden')
        }
        return
      }

      const reader = new FileReader()
      reader.onload = () => {
        if (preview && reader.result) {
          if (wrapper?.className.includes('hidden')) {
            wrapper.classList.remove('hidden')
          }
          preview.src = reader.result as string
          if (clearCheckbox?.checked) {
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
        if (clearBtn) {
          clearBtn.title = title
          clearBtn.setAttribute('aria-label', title)
        }
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
