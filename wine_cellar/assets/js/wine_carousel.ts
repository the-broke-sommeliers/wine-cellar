type WineCarouselHandle = {
  setImages: (images: string[], fullImages?: string[]) => void
}

function initWineCarousel() {
  const wrapper = document.querySelector('.card__image-wrapper') as HTMLElement
  if (!wrapper) {
    return
  }

  const imgEl = document.getElementById('wine-image') as HTMLImageElement
  const anchor = wrapper.querySelector(
    '.image-fullscreen-anchor'
  ) as HTMLAnchorElement
  const controls = wrapper.querySelector('.image-controls') as HTMLElement
  const prevBtn = wrapper.querySelector('.wine-prev') as HTMLButtonElement
  const nextBtn = wrapper.querySelector('.wine-next') as HTMLButtonElement

  if (!imgEl || !prevBtn || !nextBtn) {
    console.error('Carousel elements not found')
    return
  }

  const state = { images: [] as string[], fullImages: [] as string[], index: 0 }

  function updateImage() {
    const src = state.images[state.index]
    if (!src) {
      return
    }
    imgEl.src = src
    // Prefer the server-provided full-size URL at this index; only fall
    // back to guessing one from the thumbnail filename if it's missing.
    anchor.href = state.fullImages[state.index] ?? src.replace('_thumb', '')
    prevBtn.disabled = state.index === 0
    nextBtn.disabled = state.index === state.images.length - 1
  }

  function setImages(images: string[], fullImages: string[] = []) {
    state.images = images
    state.fullImages = fullImages
    state.index = 0
    const multi = images.length > 1
    if (controls) {
      controls.hidden = !multi
    }
    updateImage()
  }

  prevBtn.addEventListener('click', () => {
    state.index = (state.index - 1 + state.images.length) % state.images.length
    updateImage()
  })

  nextBtn.addEventListener('click', () => {
    state.index = (state.index + 1) % state.images.length
    updateImage()
  })

  setImages(
    JSON.parse(wrapper.dataset.images || '[]'),
    JSON.parse(wrapper.dataset.imagesFull || '[]')
  )
  ;(window as unknown as { wineCarousel: WineCarouselHandle }).wineCarousel = {
    setImages,
  }
}

document.addEventListener('DOMContentLoaded', initWineCarousel)
