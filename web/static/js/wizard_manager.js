/**
 * TeamSAWizard
 *
 * Gestor genérico para formularios por pasos (Wizards) de TEAMSA.
 * Abstrae la manipulación del DOM, paginación, botones e indicadores, 
 * delegando la regla de negocio y validación al controlador que lo instancia.
 */
class TeamSAWizard {
    /**
     * @param {Object} config Configuración inicial del Wizard
     * @param {number} config.totalSteps Cantidad total de pasos (default 3)
     * @param {Function} config.onValidateStep Función (step) => bool. Retorna false para evitar avance.
     * @param {Function} config.onStepChange Función (step) => void. Callback disparado tras cambiar de paso exitosamente.
     * @param {Function} config.onSubmit Función llamada cuando se da click a Confirmar / Enviar en el último paso.
     */
    constructor(config) {
        this.currentStep = 1;
        this.totalSteps = config.totalSteps || 3;
        
        this.onValidateStep = config.onValidateStep || function(step) { return true; };
        this.onStepChange = config.onStepChange || function(step) { };
        this.onSubmit = config.onSubmit || function() { };

        this.initDOM();
        this.actualizarVista();
    }

    initDOM() {
        // Enlazar eventos a los botones estándar del wizard
        const btnNext = document.getElementById('btn-next');
        const btnPrev = document.getElementById('btn-prev');
        const btnSubmit = document.getElementById('btn-submit');

        // Para evitar múltiples listeners si se re-instancia accidentalmente
        if (btnNext) {
            const nuevoNext = btnNext.cloneNode(true);
            btnNext.parentNode.replaceChild(nuevoNext, btnNext);
            nuevoNext.addEventListener('click', () => this.nextStep());
        }

        if (btnPrev) {
            const nuevoPrev = btnPrev.cloneNode(true);
            btnPrev.parentNode.replaceChild(nuevoPrev, btnPrev);
            nuevoPrev.addEventListener('click', () => this.prevStep());
        }

        if (btnSubmit) {
            // El submit general sí podría estar re-bindeado por el HTML, 
            // no lo clonamos para evitar romper `onclick` directos 
            // a menos que dependamos 100% de este manager. 
            // Para mantener retro-compatibilidad por ahora:
            btnSubmit.addEventListener('click', (e) => {
                // Prevenimos comportamiento default de HTML y delegamos
                if(!btnSubmit.hasAttribute("onclick")) {
                    e.preventDefault();
                    this.submit();
                }
            });
        }
    }

    nextStep() {
        if (!this.onValidateStep(this.currentStep)) {
            return; // Se detiene el avance si la validación falla
        }
        
        if (this.currentStep < this.totalSteps) {
            this.currentStep++;
            this.actualizarVista();
            this.onStepChange(this.currentStep);
        }
    }

    prevStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.actualizarVista();
            this.onStepChange(this.currentStep);
        }
    }

    submit() {
        if (!this.onValidateStep(this.currentStep)) {
            return;
        }
        this.onSubmit();
    }

    actualizarVista() {
        // Ocultar todos los div de contenido del wizard
        document.querySelectorAll('.wizard-content').forEach(el => {
            el.classList.add('d-none');
        });

        // Mostrar el contenido del paso actual
        const stepEl = document.getElementById(`step-${this.currentStep}`);
        if (stepEl) {
            stepEl.classList.remove('d-none');
        }

        // Actualizar indicadores visuales de pasos (bolitas superiores)
        document.querySelectorAll('.wizard-step').forEach((el, idx) => {
            el.classList.remove('active', 'completed');
            if (idx + 1 === this.currentStep) {
                el.classList.add('active');
            } else if (idx + 1 < this.currentStep) {
                el.classList.add('completed');
            }
        });

        // Actualizar visibilidad y estados de los controles inferiores
        const btnPrev = document.getElementById('btn-prev');
        const btnNext = document.getElementById('btn-next');
        const btnSubmit = document.getElementById('btn-submit');

        if (btnPrev) {
            btnPrev.disabled = (this.currentStep === 1);
        }

        if (this.currentStep === this.totalSteps) {
            if (btnNext) btnNext.classList.add('d-none');
            if (btnSubmit) btnSubmit.classList.remove('d-none');
        } else {
            if (btnNext) btnNext.classList.remove('d-none');
            if (btnSubmit) btnSubmit.classList.add('d-none');
        }
    }
    
    // Getter útil para módulos locales
    get step() {
        return this.currentStep;
    }
}
