/**
 * TEAMSA Common JS Utilities
 * Funciones compartidas para el frontend de la aplicación.
 */

window.TEAMSA = {
    /**
     * Gestión de Notas Privadas (Modales Genéricos)
     */
    Notas: {
        CONFIG: {
            'cotizaciones': { endpoint: '/api/cotizaciones', label: 'Cotización' },
            'ordenes-compra': { endpoint: '/api/ordenes-compra', label: 'Orden de Compra' },
            'ordenes_trabajo': { endpoint: '/api/ordenes-trabajo', label: 'Orden de Trabajo' },
            'servicios': { endpoint: '/api/servicios', label: 'Servicio' }
        },

        iniciar: function() {
            // Delegación de eventos para capturar clics en botones incluso tras recargas HTMX
            document.addEventListener('click', (e) => {
                const btn = e.target.closest('.btn-notas-privadas-generico');
                if (btn) {
                    e.preventDefault();
                    console.log("TEAMSA: Abriendo notas para", btn.dataset.modulo);
                    this.abrir(
                        btn.dataset.modulo, 
                        btn.dataset.id, 
                        btn.dataset.folio, 
                        btn.dataset.notas
                    );
                }
            });
        },

        abrir: function(modulo, id, folio, notasActuales) {
            const config = this.CONFIG[modulo];
            if (!config) {
                console.error("Módulo no configurado para notas:", modulo);
                return;
            }

            // Llenar campos del modal
            document.getElementById('notasPrivadasModulo').value = modulo;
            document.getElementById('notasPrivadasId').value = id;
            document.getElementById('notasPrivadasTexto').value = notasActuales || '';
            document.getElementById('notasPrivadasTitulo').textContent = `Notas Internas: ${config.label} ${folio}`;

            // Mostrar modal
            const modalElement = document.getElementById('modalNotasPrivadas');
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
        },

        guardar: async function() {
            const btn = document.querySelector('#modalNotasPrivadas .btn-teamsa-primary');
            const originalText = btn.innerHTML;
            
            const modulo = document.getElementById('notasPrivadasModulo').value;
            const id = document.getElementById('notasPrivadasId').value;
            const notas = document.getElementById('notasPrivadasTexto').value;

            const config = this.CONFIG[modulo];
            if (!config) return;

            const url = `${config.endpoint}/${id}/notas-privadas`;

            try {
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';

                const response = await fetch(url, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ notas_privadas: notas })
                });

                if (response.ok) {
                    const modalElement = document.getElementById('modalNotasPrivadas');
                    const modal = bootstrap.Modal.getInstance(modalElement);
                    modal.hide();

                    // Notificación
                    this.notificar('✅ Notas privadas guardadas', 'success');

                    // Actualización de UI (HTMX o DOM Directo)
                    this.actualizarUI(id, notas);
                } else {
                    const err = await response.json();
                    alert('❌ Error: ' + (err.detail || 'No se pudo guardar'));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('❌ Error de red al guardar las notas');
            } finally {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        },

        actualizarUI: function(id, notas) {
            // 1. Recargar tabla si es HTMX
            const tbody = document.getElementById('tbody-lista');
            if (tbody) {
                if (typeof htmx !== 'undefined') htmx.trigger(tbody, 'load');
            }

            // 2. Actualizar atributo de botones en la vista
            const buttons = document.querySelectorAll(`.btn-notas-privadas-generico[data-id="${id}"]`);
            buttons.forEach(btn => btn.setAttribute('data-notas', notas));

            // 3. Actualizar contenedor de notas si existe (Detalle)
            const notasDiv = document.getElementById('container-notas-privadas');
            if (notasDiv) {
                notasDiv.textContent = notas || 'Sin notas registradas.';
                if (!notas) notasDiv.classList.add('text-muted', 'fst-italic');
                else notasDiv.classList.remove('text-muted', 'fst-italic');
            }
        },

        notificar: function(texto, tipo) {
            if (window.mostrarFlash) {
                mostrarFlash(texto, tipo);
            } else {
                document.body.dispatchEvent(new CustomEvent('flash', {
                    detail: { texto: texto, tipo: tipo }
                }));
            }
        }
    }
};

// Auto-inicialización segura
(function() {
    const init = () => {
        if (window.TEAMSA && window.TEAMSA.Notas) {
            window.TEAMSA.Notas.iniciar();
        }
    };
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
