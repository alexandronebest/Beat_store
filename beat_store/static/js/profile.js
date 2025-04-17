function scrollSongs(direction, containerId) {
    const container = document.getElementById(containerId);
    if (direction === 'left') {
        container.scrollLeft -= 200;
    } else if (direction === 'right') {
        container.scrollLeft += 200;
    }
}