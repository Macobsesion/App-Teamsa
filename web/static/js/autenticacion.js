// Autenticación con HTMX para enviar formulario de login
document.addEventListener('DOMContentLoaded', function () {
    const formLogin = document.getElementById('formLogin');

    if (formLogin) {
        formLogin.addEventListener('submit', async function (e) {
            e.preventDefault();

            const formData = new FormData(formLogin);

            try {
                const response = await fetch('/auth/validaUsuario', {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    const data = await response.json();
                    // Redirigir según el rol del usuario.
                    if (data.rol && data.rol.toLowerCase() === 'tecnico') {
                        window.location.href = '/ordenes';
                    } else {
                        // Comportamiento por defecto
                        window.location.href = '/usuarios';
                    }
                } else {
                    const error = await response.json();
                    alert(error.detail || 'Error al iniciar sesión');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error de conexión');
            }
        });
    }
});
