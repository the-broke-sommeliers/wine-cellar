interface AiUploadPollResponse {
  status: 'pending' | 'done' | 'error'
  stage?: 'location' | 'country' | 'type' | 'sweetness' | null
  redirect?: string
  message?: string
}

interface AiUploadStartResponse {
  poll_url?: string
  errors?: Record<string, Array<{ message: string; code?: string }>>
}

const POLL_INTERVAL_MS = 2000
const MAX_ATTEMPTS = 60 // ~2 minutes at POLL_INTERVAL_MS

function initWineUploadAi() {
  const root = document.getElementById('ai-upload')
  const form = document.getElementById(
    'ai-upload-form'
  ) as HTMLFormElement | null
  if (!root || !form) {
    return
  }

  const formSection = document.getElementById('ai-upload-form-section')
  const formErrors = document.getElementById('ai-upload-form-errors')
  const statusSection = document.getElementById('ai-upload-status-section')
  const pending = document.getElementById('ai-upload-pending')
  const pendingMessage = document.getElementById('ai-upload-pending-message')
  const errorList = document.getElementById('ai-upload-error')
  const errorMessage = document.getElementById('ai-upload-error-message')
  const retry = document.getElementById('ai-upload-retry')
  const retryButton = document.getElementById('ai-upload-retry-button')

  const UPLOADING_MESSAGE = gettext('Uploading your photos…')
  const ANALYZING_MESSAGE = gettext(
    'Analyzing your label with AI… this can take up to a minute.'
  )

  function showFormSection() {
    formSection?.classList.remove('hidden')
    statusSection?.classList.add('hidden')
  }

  function showPending(message: string) {
    formSection?.classList.add('hidden')
    statusSection?.classList.remove('hidden')
    pending?.classList.remove('hidden')
    errorList?.classList.add('hidden')
    retry?.classList.add('hidden')
    if (pendingMessage) {
      pendingMessage.textContent = message
    }
  }

  function showFormErrors(messages: string[]) {
    if (!formErrors) {
      return
    }
    formErrors.innerHTML = ''
    messages.forEach((message) => {
      const li = document.createElement('li')
      li.textContent = message
      formErrors.appendChild(li)
    })
    formErrors.classList.toggle('hidden', messages.length === 0)
  }

  function flattenErrors(errors: AiUploadStartResponse['errors']): string[] {
    if (!errors) {
      return []
    }
    return Object.values(errors).flatMap((fieldErrors) =>
      fieldErrors.map((error) => error.message)
    )
  }

  function showStatusError(message: string) {
    pending?.classList.add('hidden')
    if (errorMessage) {
      errorMessage.textContent = message
    }
    errorList?.classList.remove('hidden')
    retry?.classList.remove('hidden')
  }

  const STAGE_MESSAGES: Record<string, string> = {
    location: gettext('Wine identified — now refining its location…'),
    country: gettext('Wine identified — now confirming its country of origin…'),
    type: gettext('Wine identified — now confirming its type…'),
    sweetness: gettext('Wine identified — now confirming its sweetness…'),
  }

  let shownStage: string | null = null

  function showStage(stage: string | null | undefined) {
    if (!stage || stage === shownStage) {
      return
    }
    const message = STAGE_MESSAGES[stage]
    if (message && pendingMessage) {
      pendingMessage.textContent = message
      shownStage = stage
    }
  }

  let attempts = 0

  async function poll(url: string) {
    attempts += 1
    try {
      const response = await fetch(url)
      const data: AiUploadPollResponse = await response.json()
      if (data.status === 'done' && data.redirect) {
        window.location.href = data.redirect
        return
      }
      if (data.status === 'error') {
        showStatusError(data.message || gettext('The AI request failed.'))
        return
      }
      if (data.status === 'pending') {
        showStage(data.stage)
      }
    } catch {
      // Transient network error - keep polling until MAX_ATTEMPTS.
    }
    if (attempts >= MAX_ATTEMPTS) {
      showStatusError(
        gettext(
          'This is taking longer than expected. Please try again in a few minutes.'
        )
      )
      return
    }
    setTimeout(() => poll(url), POLL_INTERVAL_MS)
  }

  function startPolling(pollUrl: string) {
    attempts = 0
    shownStage = null
    showPending(ANALYZING_MESSAGE)
    poll(pollUrl)
  }

  retryButton?.addEventListener('click', showFormSection)

  form.addEventListener('submit', (event) => {
    event.preventDefault()
    showFormErrors([])
    showPending(UPLOADING_MESSAGE)

    fetch(form.action || window.location.href, {
      method: 'POST',
      body: new FormData(form),
    })
      .then(async (response) => {
        const data: AiUploadStartResponse = await response.json()
        if (response.status === 200 && data.poll_url) {
          startPolling(data.poll_url)
          return
        }
        const messages = flattenErrors(data.errors)
        showFormSection()
        showFormErrors(
          messages.length
            ? messages
            : [gettext('Could not upload the images. Please try again.')]
        )
      })
      .catch(() => {
        showFormSection()
        showFormErrors([
          gettext('Could not upload the images. Please try again.'),
        ])
      })
  })
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initWineUploadAi)
} else {
  initWineUploadAi()
}
