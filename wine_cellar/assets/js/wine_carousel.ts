function initWineCarousel() {
  const wrapper = document.querySelector(
    '.wine-detail__image-wrapper'
  ) as HTMLElement
  if (!wrapper) {
    return
  }

  const images = JSON.parse(wrapper.dataset.images || '')

  if (!Array.isArray(images) || images.length < 2) {
    return
  }

  let index = 0

  const imgEl = document.getElementById('wine-image') as HTMLImageElement
  const anchor = wrapper.querySelector(
    '.image-fullscreen-anchor'
  ) as HTMLAnchorElement
  const prevBtn = wrapper.querySelector('.wine-prev') as HTMLButtonElement
  const nextBtn = wrapper.querySelector('.wine-next') as HTMLButtonElement

  if (!imgEl || !prevBtn || !nextBtn) {
    console.error('Carousel elements not found')
    return
  }

  function updateImage() {
    imgEl.src = images[index]
    anchor.href = images[index].replace('_thumb', '')
    prevBtn.disabled = index === 0
    nextBtn.disabled = index === images.length - 1
  }

  prevBtn.addEventListener('click', () => {
    index = (index - 1 + images.length) % images.length
    updateImage()
  })

  nextBtn.addEventListener('click', () => {
    index = (index + 1) % images.length
    updateImage()
  })
}

document.addEventListener('DOMContentLoaded', initWineCarousel)
