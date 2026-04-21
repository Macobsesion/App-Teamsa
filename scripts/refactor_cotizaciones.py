import re

file_path = '/home/teamsa/htdocs/teamsa.com.mx/teamsa-app-dev/web/templates/ui/cotizaciones/wizard.html'
with open(file_path, 'r') as f:
    text = f.read()

# 1. Update DOMContentLoaded
init_block = """
    let wizManager;
    document.addEventListener('DOMContentLoaded', () => {
        // Detectar modo edición/versión
        const urlParams = new URLSearchParams(window.location.search);
        cotizacionId = urlParams.get('id');
        const versionDe = urlParams.get('version_de');

        modoEdicion = cotizacionId !== null;
        modoVersion = versionDe !== null;

        if (modoVersion) {
            cotizacionId = parseInt(versionDe);
            document.getElementById('wizard-titulo').textContent = '📂 Nueva Versión de Cotización';
            document.getElementById('btn-submit-text').textContent = '✨ Crear Nueva Versión';
        } else if (modoEdicion) {
            document.getElementById('wizard-titulo').textContent = '✏️ Modificar Cotización';
            document.getElementById('btn-submit-text').textContent = '💾 Guardar Cambios';
        }

        cargarClientes();
        cargarServicios();
        cargarViaticosParaWizard();

        document.getElementById('modalCalculadoraViaticos')?.addEventListener('shown.bs.modal', function () {
            cargarViaticosParaWizard();
        });

        if (modoEdicion || modoVersion) {
            setTimeout(() => cargarCotizacionParaEditar(cotizacionId), 500);
        }
        
        wizManager = new TeamSAWizard({
            totalSteps: 3,
            onValidateStep: (step) => {
                if (step === 1) {
                    const clienteId = document.getElementById('cliente-select').value;
                    if (!clienteId) {
                        mostrarError('Por favor selecciona un cliente');
                        return false;
                    }
                    wizardState.cliente_id = parseInt(clienteId);
                    wizardState.metodo_pago = document.getElementById('metodo-pago').value;
                    wizardState.forma_pago = document.getElementById('forma-pago').value;
                    wizardState.notas = document.getElementById('notas').value;
                    return true;
                }
                if (step === 2) {
                    if (wizardState.servicios.length === 0) {
                        mostrarError('Agrega al menos un servicio o ítem');
                        return false;
                    }
                    return true;
                }
                return true;
            },
            onStepChange: (step) => {
                if (step === 3) {
                    actualizarResumen();
                }
            }
        });
    });
"""

old_init_pattern = r"document\.addEventListener\('DOMContentLoaded', \(\) => \{.*?setTimeout\(\(\) => cargarCotizacionParaEditar\(cotizacionId\), 500\);\n        \}\n    \}\);"
text = re.sub(old_init_pattern, init_block.strip() + "\n", text, flags=re.DOTALL)

# 2. Remove nextStep, prevStep, actualizarVista
pattern_funcs = r"function nextStep\(\) \{.*?function actualizarVista\(\) \{.*?\}\n"
text = re.sub(pattern_funcs, "", text, flags=re.DOTALL)

# 3. Clean up onclick native calls
text = text.replace('onclick="prevStep()"', '')
text = text.replace('onclick="nextStep()"', '')

with open(file_path, 'w') as f:
    f.write(text)

print("Wizard refactor success for Cotizaciones")
