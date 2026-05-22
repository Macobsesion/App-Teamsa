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
                    // Redirección uniforme: El sistema de permisos (checkboxes) 
                    // se encargará de mostrar o denegar acceso a los módulos.
                    window.location.href = '/ui/cronograma';
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
