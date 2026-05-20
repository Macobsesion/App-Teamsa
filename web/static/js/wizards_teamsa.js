/**
 * TeamSADocumentWizard
 * 
 * Extensión de la lógica de negocio para Wizards de documentos complejos 
 * (Cotizaciones y Órdenes de Compra) en TEAMSA.
 */
class TeamSADocumentWizard {
    constructor(config) {
        this.state = config.initialState || { items: [] };
        this.config = {
            selectors: config.selectors || {},
            endpoints: config.endpoints || {},
            templates: config.templates || {},
            callbacks: config.callbacks || {}
        };
        
        this.init();
    }

    init() {

    }

    /**
     * Carga datos para un selector desde un endpoint
     */
    async cargarSelector(key, formatFn) {
        const endpoint = this.config.endpoints[key];
        const selectorId = this.config.selectors[key];
        if (!endpoint || !selectorId) return;

        try {
            const resp = await fetch(endpoint);
            if (!resp.ok) throw new Error(`Error al cargar ${key}`);
            const data = await resp.json();
            
            const sel = document.getElementById(selectorId);
            if (!sel) return;

            // Conservar primera opción (placeholder)
            const firstOpt = sel.options[0];
            sel.innerHTML = '';
            if (firstOpt) sel.appendChild(firstOpt);

            data.forEach(item => {
                const opt = document.createElement('option');
                const formatted = formatFn ? formatFn(item) : { val: item.id, text: item.nombre };
                opt.value = formatted.val;
                opt.textContent = formatted.text;
                sel.appendChild(opt);
            });
            
            return data;
        } catch (e) {
            console.error(e);
            return [];
        }
    }

    /**
     * Gestión de Items/Partidas
     */
    agregarItem(item) {
        this.state.items.push(item);
        if (this.config.callbacks.onItemsChange) {
            this.config.callbacks.onItemsChange(this.state.items);
        }
    }

    eliminarItem(index) {
        this.state.items.splice(index, 1);
        if (this.config.callbacks.onItemsChange) {
            this.config.callbacks.onItemsChange(this.state.items);
        }
    }

    actualizarItem(index, campo, valor, isNumeric = false) {
        let finalValue = valor;
        if (isNumeric) {
            finalValue = parseFloat(valor);
            if (isNaN(finalValue) || finalValue < 0) return;
            // Validaciones de negocio mínimas
            if (campo === 'cantidad' && finalValue < 1) return;
            if (campo === 'descuento_porcentaje' && finalValue > 100) return;
        }
        
        this.state.items[index][campo] = finalValue;
        
        if (this.config.callbacks.onItemsChange) {
            this.config.callbacks.onItemsChange(this.state.items);
        }
    }

    /**
     * Cálculos Financieros
     */
    calcularTotales() {
        let subtotal = 0;
        let descuentoTotal = 0;

        this.state.items.forEach(item => {
            const importeRecurso = item.cantidad * item.precio_unitario;
            const descFila = importeRecurso * ((item.descuento_porcentaje || 0) / 100);
            subtotal += importeRecurso;
            descuentoTotal += descFila;
        });

        const baseIva = subtotal - descuentoTotal;
        const iva = baseIva * 0.16;
        const total = baseIva + iva;

        return { subtotal, descuentoTotal, baseIva, iva, total };
    }

    /**
     * Sincroniza los totales calculados con los elementos del DOM si existen
     */
    refreshUI() {
        const totals = this.calcularTotales();
        
        // Buscar y actualizar elementos comunes de totales
        const ids = {
            'resumen-subtotal': totals.subtotal,
            'resumen-descuento': totals.descuentoTotal,
            'resumen-iva': totals.iva,
            'resumen-total': totals.total,
            'total-step-2': totals.subtotal
        };

        for (const [id, value] of Object.entries(ids)) {
            const el = document.getElementById(id);
            if (el) {
                // Si el ID es total-step-2 usamos formato moneda con $, sino solo el número
                el.textContent = id === 'total-step-2' ? `$${value.toFixed(2)}` : value.toFixed(2);
            }
        }
    }

    /**
     * Guardado genérico
     */
    async guardar(url, method = 'POST') {
        try {
            const resp = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.state)
            });

            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.detail || 'Error al procesar la solicitud');
            }

            return await resp.json();
        } catch (e) {
            throw e;
        }
    }
}

// Exportar al namespace global de la app
window.TEAMSA.DocumentWizard = TeamSADocumentWizard;
