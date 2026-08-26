document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.password-toggle').forEach(function (input) {
        if (!input || input.dataset.passwordEyeBound) {
            return;
        }

        input.dataset.passwordEyeBound = 'true';
        const wrapper = input.parentElement;
        if (!wrapper) {
            return;
        }

        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'password-toggle-btn';
        button.innerHTML = '<i class="fa-solid fa-eye"></i>';
        button.setAttribute('aria-label', 'Mostrar u ocultar contraseña');

        button.addEventListener('click', function () {
            const isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';
            button.innerHTML = isPassword
                ? '<i class="fa-solid fa-eye-slash"></i>'
                : '<i class="fa-solid fa-eye"></i>';
        });

        wrapper.appendChild(button);
    });
});
