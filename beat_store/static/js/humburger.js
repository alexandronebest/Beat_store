document.addEventListener('DOMContentLoaded', function () {
    const navbarToggler = document.querySelector('.navbar-toggler');
    const offcanvas = document.querySelector('#offcanvasNavbar');
    if (!navbarToggler || !offcanvas) {
        console.error('Navbar toggler or offcanvas element not found');
        return;
    }
    const offcanvasInstance = bootstrap.Offcanvas.getOrCreateInstance(offcanvas);
    const navLinks = offcanvas.querySelectorAll('.nav-link, .auth-btn');

    navbarToggler.addEventListener('click', function () {
        offcanvasInstance.toggle();
    });

    navLinks.forEach(link => {
        link.addEventListener('click', function () {
            offcanvasInstance.hide();
        });
    });
});