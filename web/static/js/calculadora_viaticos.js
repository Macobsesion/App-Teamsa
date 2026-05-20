/**
 * Lógica autónoma para la Calculadora de Viáticos
 * Emite eventos estándar para que cualquier módulo pueda suscribirse.
 */

class CalculadoraViaticos {
    
    static inicializar() {
        // Listener para recalcular totales automáticamente
        document.addEventListener('input', function (e) {
            if (e.target.classList.contains('viatico-calc') || e.target.id === 'viatico-personas') {
                CalculadoraViaticos.recalcular();
            }
        });
    }

    static recalcular() {
        const personas = parseInt(document.getElementById('viatico-personas').value) || 1;
        const dias = parseInt(document.getElementById('viatico-dias').value) || 1;
        
        const desayuno = parseFloat(document.getElementById('viatico-desayuno').value) || 0;
        const comida = parseFloat(document.getElementById('viatico-comida').value) || 0;
        const cena = parseFloat(document.getElementById('viatico-cena').value) || 0;
        
        // Calcular subtotal de alimentos: (D+C+C) * personas * dias
        const totalAlimentos = (desayuno + comida + cena) * personas * dias;
        document.getElementById('viatico-alimentos').value = totalAlimentos.toFixed(2);
        document.getElementById('viatico-alimentos-label').textContent = '$' + totalAlimentos.toFixed(2);

        const transporte = parseFloat(document.getElementById('viatico-transporte').value) || 0;
        const alojamiento = parseFloat(document.getElementById('viatico-alojamiento').value) || 0;
        const peajes = parseFloat(document.getElementById('viatico-peajes').value) || 0;
        const estacionamiento = parseFloat(document.getElementById('viatico-estacionamiento').value) || 0;
        const otros = parseFloat(document.getElementById('viatico-otros').value) || 0;

        const total = transporte + alojamiento + totalAlimentos + peajes + estacionamiento + otros;
        document.getElementById('viatico-total-suma').textContent = total.toFixed(2);
    }

    static abrir(data = null) {
        if (data) {
            // Llenar campos del modal
            document.getElementById('viatico-proyecto').value = data.proyecto || '';
            document.getElementById('viatico-id').value = data.id || '';
            document.getElementById('viatico-folio').value = data.folio || '';
            document.getElementById('viatico-origen').value = data.origen || '';
            document.getElementById('viatico-destino').value = data.destino || '';
            document.getElementById('viatico-personas').value = data.personas || 1;
            document.getElementById('viatico-transporte').value = data.costo_transporte || 0;
            document.getElementById('viatico-alojamiento').value = data.costo_alojamiento || 0;
            document.getElementById('viatico-peajes').value = data.costo_peajes || 0;
            document.getElementById('viatico-estacionamiento').value = data.costo_estacionamiento || 0;
            document.getElementById('viatico-otros').value = data.costo_otros || 0;
            document.getElementById('viatico-transporte-tipo').value = data.tipo_transporte || 'Vehículo Empresa';

            document.getElementById('viatico-dias').value = data.dias || 1;
            document.getElementById('viatico-desayuno').value = data.desayuno || 0;
            document.getElementById('viatico-comida').value = data.comida || (data.costo_alimentos / (data.personas || 1) / (data.dias || 1)).toFixed(2) || 0;
            document.getElementById('viatico-cena').value = data.cena || 0;

            document.querySelector('#modalCalculadoraViaticos .modal-title').innerHTML = '✏️ Editando Viático';
        } else {
            CalculadoraViaticos.limpiar();
            document.querySelector('#modalCalculadoraViaticos .modal-title').innerHTML = '✈️ Gestión de Viáticos';
        }

        // Forzar recalculo
        CalculadoraViaticos.recalcular();

        const modalEl = document.getElementById('modalCalculadoraViaticos');
        if (!modalEl) return console.error("Modal de calculadora no encontrado en el DOM");
        
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) modal = new bootstrap.Modal(modalEl);
        modal.show();
    }

    static guardar() {
        const proyecto = document.getElementById('viatico-proyecto').value;
        const origen = document.getElementById('viatico-origen').value;
        const destino = document.getElementById('viatico-destino').value;
        const tipoTransporte = document.getElementById('viatico-transporte-tipo').value;
        const personas = parseInt(document.getElementById('viatico-personas').value) || 1;
        const dias = parseInt(document.getElementById('viatico-dias').value) || 1;
        const transporte = parseFloat(document.getElementById('viatico-transporte').value) || 0;
        const alojamiento = parseFloat(document.getElementById('viatico-alojamiento').value) || 0;
        const alimentos = parseFloat(document.getElementById('viatico-alimentos').value) || 0;
        const peajes = parseFloat(document.getElementById('viatico-peajes').value) || 0;
        const estacionamiento = parseFloat(document.getElementById('viatico-estacionamiento').value) || 0;
        const otros = parseFloat(document.getElementById('viatico-otros').value) || 0;
        
        const desayuno = parseFloat(document.getElementById('viatico-desayuno').value) || 0;
        const comida = parseFloat(document.getElementById('viatico-comida').value) || 0;
        const cena = parseFloat(document.getElementById('viatico-cena').value) || 0;

        const total = parseFloat((transporte + alojamiento + alimentos + peajes + estacionamiento + otros).toFixed(2));

        if (!proyecto || !origen || !destino || total <= 0) {
            alert('Por favor completa Proyecto, Origen, Destino y asegúrate de que el total sea mayor a 0.');
            return;
        }

        const viaticoId = document.getElementById('viatico-id').value;
        const viaticoData = {
            id: viaticoId ? parseInt(viaticoId) : null,
            proyecto, origen, destino, personas, dias,
            folio_referencia: document.getElementById('viatico-folio').value,
            desayuno, comida, cena,
            costo_transporte: transporte,
            costo_alojamiento: alojamiento,
            costo_alimentos: alimentos,
            costo_peajes: peajes,
            costo_estacionamiento: estacionamiento,
            costo_otros: otros,
            tipo_transporte: tipoTransporte,
            total
        };

        // Emitir CustomEvent para que el padre lo capture
        const evento = new CustomEvent('CalculadoraViaticos:Guardar', { detail: viaticoData });
        document.dispatchEvent(evento);

        const modalEl = document.getElementById('modalCalculadoraViaticos');
        const modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();

        CalculadoraViaticos.limpiar();
    }

    static limpiar() {
        document.getElementById('viatico-proyecto').value = '';
        document.getElementById('viatico-id').value = '';
        document.getElementById('viatico-folio').value = '';
        document.getElementById('viatico-origen').value = '';
        document.getElementById('viatico-destino').value = '';
        document.getElementById('viatico-transporte-tipo').value = 'Vehículo Empresa';
        document.getElementById('viatico-personas').value = '1';
        document.getElementById('viatico-dias').value = '1';
        document.getElementById('viatico-desayuno').value = '0.00';
        document.getElementById('viatico-comida').value = '0.00';
        document.getElementById('viatico-cena').value = '0.00';
        document.getElementById('viatico-transporte').value = '0.00';
        document.getElementById('viatico-alojamiento').value = '0.00';
        document.getElementById('viatico-peajes').value = '0.00';
        document.getElementById('viatico-estacionamiento').value = '0.00';
        document.getElementById('viatico-otros').value = '0.00';
        document.getElementById('viatico-total-suma').textContent = '0.00';
        document.getElementById('viatico-alimentos-label').textContent = '$0.00';
        document.querySelector('#modalCalculadoraViaticos .modal-title').innerHTML = '✈️ Gestión de Viáticos';
    }

    static async cargarDesdeBiblioteca(id) {
        if (!id) return;
        try {
            const resp = await fetch(`/api/viaticos/${id}`);
            if (!resp.ok) throw new Error("No se pudo cargar el viático");
            const data = await resp.json();
            
            // Abrir en modo "Nueva" (clonando)
            this.abrir(data);
            
            // IMPORTANTE: Al cargar de biblioteca para una NUEVA cotización o item, 
            // queremos que sea un CLON, no que edite el original.
            document.getElementById('viatico-id').value = '';
            
            // Cambiar a la pestaña de "Nueva Calculadora" para que el usuario vea los datos
            const tabEl = document.getElementById('nueva-tab');
            if (tabEl) bootstrap.Tab.getOrCreateInstance(tabEl).show();
            
            mostrarFlash("Datos importados de la biblioteca. Puedes editarlos antes de inyectar.");
        } catch (e) {
            console.error(e);
            alert("Error al importar viático: " + e.message);
        }
    }

    static async vistaPreviaBiblioteca(id) {

        const preview = document.getElementById('viatico-preview-modal');
        if (!preview) return;
        
        if (!id || id === "") {
            preview.classList.add('d-none');
            return;
        }

        try {
            // Mostrar el contenedor de inmediato para dar feedback (aunque esté vacío o cargando)
            preview.classList.remove('d-none');
            const totalEl = document.getElementById('v-prev-total');
            if (totalEl) totalEl.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

            const resp = await fetch(`/api/viaticos/${id}`);
            if (!resp.ok) throw new Error("Error al consultar el viático");
            const v = await resp.json();
            

            
            const folioEl = document.getElementById('v-prev-folio');
            const proyectoEl = document.getElementById('v-prev-proyecto');

            if (folioEl) folioEl.textContent = v.folio || 'S/F';
            if (proyectoEl) proyectoEl.textContent = v.proyecto || 'Sin proyecto';
            
            if (totalEl) {
                const totalVal = parseFloat(v.total || 0);
                totalEl.textContent = '$' + totalVal.toLocaleString('es-MX', { 
                    minimumFractionDigits: 2, 
                    maximumFractionDigits: 2 
                });
            }
        } catch (e) {
            console.error("Calculadora: Error en vista previa:", e);
            preview.classList.add('d-none');
        }
    }
}

// Inicializar listener estático
CalculadoraViaticos.inicializar();

// Exportar globalmente para que el Wizard pueda acceder
window.CalculadoraViaticos = CalculadoraViaticos;
