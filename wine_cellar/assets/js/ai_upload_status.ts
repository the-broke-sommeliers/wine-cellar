interface AiUploadPollResponse {
  status: 'pending' | 'done' | 'error'
  stage?: 'location' | 'country' | 'type' | 'sweetness' | null
  redirect?: string
  message?: string
}

const POLL_INTERVAL_MS = 2000
const MAX_ATTEMPTS = 60 // ~2 minutes at POLL_INTERVAL_MS

function initAiUploadStatus() {
  const container = document.getElementById('ai-upload-status')
  const pollUrl = container?.dataset.pollUrl
  if (!container || !pollUrl) {
    return
  }

  const pending = document.getElementById('ai-upload-pending')
  const pendingMessage = document.getElementById('ai-upload-pending-message')
  const errorList = document.getElementById('ai-upload-error')
  const errorMessage = document.getElementById('ai-upload-error-message')
  const retry = document.getElementById('ai-upload-retry')

  function showError(message: string) {
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
        showError(data.message || gettext('The AI request failed.'))
        return
      }
      if (data.status === 'pending') {
        showStage(data.stage)
      }
    } catch {
      // Transient network error - keep polling until MAX_ATTEMPTS.
    }
    if (attempts >= MAX_ATTEMPTS) {
      showError(
        gettext(
          'This is taking longer than expected. Please try again in a few minutes.'
        )
      )
      return
    }
    setTimeout(() => poll(url), POLL_INTERVAL_MS)
  }

  poll(pollUrl)
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAiUploadStatus)
} else {
  initAiUploadStatus()
}
