document.addEventListener("DOMContentLoaded", function () {
    const wrapper = document.getElementById("wine-image-wrapper");
    if (!wrapper) return;

    const images = JSON.parse(wrapper.dataset.images || '');
    let index = 0;

    const imgEl = document.getElementById("wine-image") as HTMLImageElement;
    const prevBtn = wrapper.querySelector(".wine-prev") as HTMLButtonElement;
    const nextBtn = wrapper.querySelector(".wine-next") as HTMLButtonElement;

    function updateImage() {
        imgEl.src = images[index];
    }

    prevBtn.addEventListener("click", () => {
        index = (index - 1 + images.length) % images.length;
        updateImage();
    });

    nextBtn.addEventListener("click", () => {
        index = (index + 1) % images.length;
        updateImage();
    });
});
