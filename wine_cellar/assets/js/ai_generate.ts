interface AiGenerateStartResponse {
  poll_url?: string
  message?: string
}

interface AiGeneratePollResponse {
  status: 'pending' | 'done' | 'error'
  text?: string
  items?: string[]
  message?: string
}

const AI_GENERATE_POLL_INTERVAL_MS = 2000
const AI_GENERATE_MAX_POLL_ATTEMPTS = 60

function initAiGenerate(root: HTMLElement) {
  const button = root.querySelector<HTMLButtonElement>('[data-ai-generate]')
  const text = root.querySelector<HTMLElement>('[data-ai-text]')
  const status = root.querySelector<HTMLElement>('[data-ai-status]')
  const deleteForm = root.querySelector<HTMLFormElement>('[data-ai-delete]')
  const editLink = root.querySelector<HTMLAnchorElement>('[data-ai-edit]')
  const csrfToken =
    deleteForm?.querySelector<HTMLInputElement>(
      'input[name="csrfmiddlewaretoken"]'
    )?.value || ''
  if (!button) {
    return
  }

  // Saving the edit form would cancel the running job.
  editLink?.addEventListener('click', (event) => {
    if (root.classList.contains('ai-box--pending')) {
      event.preventDefault()
    }
  })

  function finish(message: string, isError = false) {
    button?.removeAttribute('disabled')
    root.classList.remove('ai-box--pending')
    editLink?.removeAttribute('aria-disabled')
    if (status) {
      status.textContent = message
      status.classList.toggle('ai-box__status--error', isError)
    }
  }

  function showResult(data: AiGeneratePollResponse) {
    if (text && text.dataset.aiList !== undefined) {
      text.replaceChildren(
        ...(data.items || []).map((item) => {
          const li = document.createElement('li')
          li.className = 'ai-box__item'
          li.textContent = item
          return li
        })
      )
    } else if (text) {
      text.textContent = data.text || ''
    }
    button?.remove()
    deleteForm?.classList.remove('hidden')
    finish(root.dataset.aiDoneMessage || '')
  }

  let attempts = 0

  async function poll(url: string) {
    attempts += 1
    try {
      const response = await fetch(url)
      const data: AiGeneratePollResponse = await response.json()
      if (data.status === 'done') {
        showResult(data)
        return
      }
      if (data.status === 'error') {
        finish(data.message || gettext('The AI request failed.'), true)
        return
      }
    } catch {
      // Transient network error - keep polling until AI_GENERATE_MAX_POLL_ATTEMPTS.
    }
    if (attempts >= AI_GENERATE_MAX_POLL_ATTEMPTS) {
      finish(
        gettext(
          'This is taking longer than expected. Please try again in a few minutes.'
        ),
        true
      )
      return
    }
    setTimeout(() => poll(url), AI_GENERATE_POLL_INTERVAL_MS)
  }

  button.addEventListener('click', () => {
    const url = button.dataset.aiGenerate
    if (!url) {
      return
    }
    button.setAttribute('disabled', '')
    root.classList.add('ai-box--pending')
    editLink?.setAttribute('aria-disabled', 'true')
    if (status) {
      status.textContent = gettext('Asking the AI… this can take a moment.')
      status.classList.remove('ai-box__status--error')
    }
    fetch(url, { method: 'POST', headers: { 'X-CSRFToken': csrfToken } })
      .then(async (response) => {
        const data: AiGenerateStartResponse = await response.json()
        if (response.ok && data.poll_url) {
          attempts = 0
          poll(data.poll_url)
          return
        }
        finish(data.message || gettext('Could not start the AI request.'), true)
      })
      .catch(() => {
        finish(gettext('Could not start the AI request.'), true)
      })
  })
}

function initAllAiGenerate() {
  document
    .querySelectorAll<HTMLElement>('[data-ai-box]')
    .forEach(initAiGenerate)
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAllAiGenerate)
} else {
  initAllAiGenerate()
}
