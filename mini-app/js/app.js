/**
 * app.js — Lógica principal de la Mini App Asistente Caficultor ☕
 * 100% funcionalidad del bot en interfaz web.
 */
const app = {
    currentUser: null,
    currentFinca: null,
    userId: 0,
    username: '',
    // Estado de los flujos
    costoState: { fincaId: null, loteIds: [], modo: 'todos', categoria: null, tipo: null },
    presupuestoAnio: null,

    // ─── INIT ───
    async init() {
        // Inicializar Telegram WebApp
        if (window.Telegram && window.Telegram.WebApp) {
            const tg = window.Telegram.WebApp;
            tg.ready();
            tg.expand();
            this.currentUser = tg.initDataUnsafe?.user;
            if (this.currentUser) {
                this.userId = this.currentUser.id;
                this.username = this.currentUser.username || this.currentUser.first_name || '';
            }
        }

        // Fallback: user_id vía URL o localStorage
        if (!this.userId) {
            const params = new URLSearchParams(window.location.search);
            this.userId = parseInt(params.get('user_id')) || parseInt(localStorage.getItem('userId')) || 1;
            this.username = params.get('username') || localStorage.getItem('username') || 'usuario';
        }
        localStorage.setItem('userId', this.userId);
        localStorage.setItem('username', this.username);

        // Setup navegación
        this.setupNavigation();

        // Verificar usuario y términos
        await this.verificarAcceso();
    },

    setupNavigation() {
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.dataset.tab;
                this.cambiarTab(tab);
            });
        });
    },

    cambiarTab(tabId) {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        const btn = document.querySelector(`.nav-btn[data-tab="${tabId}"]`);
        if (btn) btn.classList.add('active');
        const section = document.getElementById(tabId);
        if (section) section.classList.add('active');

        // Cargar datos según tab
        switch (tabId) {
            case 'dashboard': this.cargarDashboard(); break;
            case 'fincas': this.cargarFincas(); break;
            case 'lotes': this.cargarSelectorFincaLotes(); break;
            case 'ingresos': this.cargarSelectorFincaIngresos(); break;
            case 'costos': this.cargarSelectorFincaCostos(); break;
            case 'presupuesto': this.cargarSelectorFincaPresupuesto(); break;
            case 'indicadores': this.cargarSelectorFincaIndicadores(); break;
            case 'asesoria': this.cargarAsesoria(); break;
            case 'exportar': this.cargarSelectorFincaExport(); break;
        }
    },

    // ═══════════════════════════════════════════
    // AUTENTICACIÓN
    // ═══════════════════════════════════════════

    async verificarAcceso() {
        try {
            const user = await api.getUsuario(this.userId);
            this.usuario = user;

            // Si no ha aceptado términos, mostrar aviso legal
            if (!user.acepto_terminos) {
                document.getElementById('loginLoading').classList.add('hidden');
                const aviso = document.getElementById('avisoLegal');
                aviso.classList.remove('hidden');
                document.getElementById('avisoTexto').innerHTML = user.aviso_legal || 'Cargando aviso legal...';

                // Si no tenemos el texto, cargarlo de config
                if (!user.aviso_legal) {
                    const config = await api.getConfig();
                    document.getElementById('avisoTexto').innerHTML = config.aviso_legal || 'Términos y condiciones';
                }
            } else {
                // Usuario aceptó términos, mostrar app
                document.getElementById('loginScreen').classList.remove('active');
                document.getElementById('dashboard').classList.add('active');
                document.querySelector('.nav-btn[data-tab="dashboard"]').classList.add('active');
                await this.cargarDashboard();
            }
        } catch (e) {
            console.error('Error verificando acceso:', e);
            // Fallback: mostrar app directamente
            document.getElementById('loginScreen').classList.remove('active');
            document.getElementById('dashboard').classList.add('active');
            document.querySelector('.nav-btn[data-tab="dashboard"]').classList.add('active');
            await this.cargarDashboard();
        }
    },

    async aceptarTerminos() {
        try {
            await api.aceptarTerminos(this.userId);
            document.getElementById('avisoLegal').classList.add('hidden');
            document.getElementById('loginScreen').classList.remove('active');
            document.getElementById('dashboard').classList.add('active');
            document.querySelector('.nav-btn[data-tab="dashboard"]').classList.add('active');
            await this.cargarDashboard();
        } catch (e) {
            this.mostrarModal('Error', 'No se pudo procesar tu solicitud. Intentalo de nuevo.');
        }
    },

    rechazarTerminos() {
        this.mostrarModal(
            'Términos no aceptados',
            'Lamentamos que no aceptes los términos. Sin aceptarlos no podés usar el asistente. ' +
            'Si cambiás de opinión, recargá la página.'
        );
    },

    // ═══════════════════════════════════════════
    // DASHBOARD / MENÚ PRINCIPAL
    // ═══════════════════════════════════════════

    async cargarDashboard() {
        try {
            document.getElementById('menuScreen').classList.remove('hidden');

            // Obtener fincas
            const fincasData = await api.getFincas(this.userId);
            const fincas = fincasData.fincas || [];
            if (fincas.length === 0) {
                document.getElementById('dashIngresos').textContent = '$0';
                document.getElementById('dashCostos').textContent = '$0';
                document.getElementById('dashMargen').textContent = '$0';
                document.getElementById('dashCostoHa').textContent = '$0';
                document.getElementById('alertasContainer').innerHTML =
                    '<div class="alerta alerta-info"><span class="icon">💡</span><div class="content"><strong>¡Bienvenido!</strong>Comenzá creando una finca en la sección Fincas.</div></div>';
                return;
            }

            // Usar primera finca
            const fincaId = fincas[0].id;
            this.currentFinca = fincas[0];

            try {
                const resumen = await api.getResumen(fincaId);
                document.getElementById('dashIngresos').textContent = this.formatearDinero(resumen.ingresos || 0);
                document.getElementById('dashCostos').textContent = this.formatearDinero(resumen.egresos || 0);
                const margen = (resumen.margen || 0);
                document.getElementById('dashMargen').textContent = this.formatearDinero(margen);
                document.getElementById('dashMargen').className = 'card-value ' + (margen >= 0 ? 'text-success' : 'text-danger');
                document.getElementById('dashCostoHa').textContent = this.formatearDinero(resumen.costo_por_hectarea || 0);

                // Gráfico de gastos por categoría
                const cats = resumen.egresos_por_categoria || {};
                const labels = Object.keys(cats);
                const data = Object.values(cats);
                const colors = ['#2E7D32', '#4CAF50', '#FF8F00', '#1976D2', '#7B1FA2', '#D32F2F', '#009688', '#795548', '#607D8B'];
                charts.drawBarChart('chartGastos', labels, data, colors);

                // Mostrar resumen rápido
                this.mostrarMenuRapido('resumen');
            } catch (e) {
                console.error('Dashboard error:', e);
            }

            // Cargar alertas
            await this.cargarAlertas(fincaId);

        } catch (e) {
            console.error('Error cargando dashboard:', e);
        }
    },

    async cargarAlertas(fincaId) {
        try {
            const data = await api.getAlertas(fincaId);
            const container = document.getElementById('alertasContainer');
            if (data.alertas && data.alertas.length > 0) {
                container.innerHTML = '<h3 class="section-title">🔔 Alertas</h3>' +
                    data.alertas.map(a => `
                        <div class="alerta alerta-${a.tipo}">
                            <span class="icon">${a.tipo === 'danger' ? '🔴' : a.tipo === 'warning' ? '🟡' : '🟢'}</span>
                            <div class="content">
                                <strong>${a.titulo}</strong>
                                ${a.mensaje}
                            </div>
                        </div>
                    `).join('');
            } else {
                container.innerHTML = '';
            }
        } catch (e) { console.error(e); }
    },

    mostrarMenuRapido(tipo) {
        ['resumen', 'indicadores', 'periodo'].forEach(t => {
            document.getElementById(`rapid${t.charAt(0).toUpperCase() + t.slice(1)}Btn`).classList.toggle('active', t === tipo);
        });

        const container = document.getElementById('rapidContent');
        const fincaId = this.currentFinca?.id;

        if (tipo === 'resumen' && fincaId) {
            api.getResumen(fincaId).then(r => {
                container.innerHTML = `
                    <div class="cards" style="margin-bottom:0;">
                        <div class="card"><span class="card-label">Total ingresos</span><span class="card-value">${this.formatearDinero(r.ingresos)}</span></div>
                        <div class="card"><span class="card-label">Total costos</span><span class="card-value">${this.formatearDinero(r.egresos)}</span></div>
                        <div class="card"><span class="card-label">Margen neto</span><span class="card-value ${r.margen >= 0 ? 'text-success' : 'text-danger'}">${this.formatearDinero(r.margen)}</span></div>
                        <div class="card"><span class="card-label">Costo/ha</span><span class="card-value">${this.formatearDinero(r.costo_por_hectarea)}</span></div>
                    </div>`;
            }).catch(() => { container.innerHTML = '<p class="empty-state">Sin datos</p>'; });
        } else if (tipo === 'indicadores' && fincaId) {
            api.getIndicadores(fincaId).then(ind => {
                container.innerHTML = `
                    <div class="indicadores-grid" style="margin-bottom:0;">
                        <div class="indicador-item"><span class="indicador-label">Productividad</span><span class="indicador-value">${(ind.productividad||0).toFixed(1)} kg/ha</span></div>
                        <div class="indicador-item"><span class="indicador-label">Costo/kg</span><span class="indicador-value">${this.formatearDinero(ind.costo_por_kilo)}</span></div>
                        <div class="indicador-item"><span class="indicador-label">Precio venta</span><span class="indicador-value">${this.formatearDinero(ind.precio_venta_promedio)}</span></div>
                        <div class="indicador-item"><span class="indicador-label">Eficiencia MO</span><span class="indicador-value">${(ind.eficiencia_mo||0).toFixed(1)} kg/jornal</span></div>
                    </div>`;
            }).catch(() => {});
        } else if (tipo === 'periodo' && fincaId) {
            container.innerHTML = `
                <div class="form-row">
                    <div class="form-group"><label>Desde</label><input type="date" id="rapidPeriodoInicio"></div>
                    <div class="form-group"><label>Hasta</label><input type="date" id="rapidPeriodoFin"></div>
                </div>
                <button class="btn btn-primary btn-sm" onclick="app.filtrarPeriodoRapido()">🔍 Analizar período</button>
                <div id="rapidPeriodoResult" class="mt-1"></div>`;
        } else {
            container.innerHTML = '<p class="empty-state">Seleccioná una finca primero</p>';
        }
    },

    async filtrarPeriodoRapido() {
        const inicio = document.getElementById('rapidPeriodoInicio').value;
        const fin = document.getElementById('rapidPeriodoFin').value;
        if (!inicio || !fin) { return; }
        const fincaId = this.currentFinca?.id;
        if (!fincaId) return;

        try {
            const r = await api.getResumenPeriodo(fincaId, inicio, fin);
            document.getElementById('rapidPeriodoResult').innerHTML = `
                <div class="cards" style="margin:8px 0 0;">
                    <div class="card"><span class="card-label">Ingresos</span><span class="card-value">${this.formatearDinero(r.ingresos)}</span></div>
                    <div class="card"><span class="card-label">Costos</span><span class="card-value">${this.formatearDinero(r.egresos)}</span></div>
                    <div class="card"><span class="card-label">Margen</span><span class="card-value ${(r.margen||0) >= 0 ? 'text-success' : 'text-danger'}">${this.formatearDinero(r.margen)}</span></div>
                </div>`;
        } catch (e) { console.error(e); }
    },

    // ─── Navegación rápida ───
    irAFincas() { this.cambiarTab('fincas'); },
    irALotes() { this.cargarSelectorFincaLotes(); this.cambiarTab('lotes'); },
    irAIngresos() { this.cargarSelectorFincaIngresos(); this.cambiarTab('ingresos'); },
    irACostos() { this.cargarSelectorFincaCostos(); this.cambiarTab('costos'); },
    irAPresupuesto() { this.cargarSelectorFincaPresupuesto(); this.cambiarTab('presupuesto'); },
    irAExportar() { this.cargarSelectorFincaExport(); this.cambiarTab('exportar'); },
    irAAsesoria() { this.cargarAsesoria(); this.cambiarTab('asesoria'); },

    // ═══════════════════════════════════════════
    // FINCAS — CRUD
    // ═══════════════════════════════════════════

    async cargarFincas() {
        const container = document.getElementById('fincasList');
        try {
            const data = await api.getFincas(this.userId);
            const fincas = data.fincas || [];
            if (fincas.length === 0) {
                container.innerHTML = '<p class="empty-state"><span class="icon">🗺️</span>Aún no tenés fincas registradas. ¡Creá la primera!</p>';
                return;
            }
            container.innerHTML = fincas.map(f => `
                <div class="list-item">
                    <div class="item-main">
                        <div class="item-title">${f.nombre}</div>
                        <div class="item-sub">${f.region || 'Sin región'} ${f.departamento ? '- ' + f.departamento : ''}</div>
                    </div>
                    <div class="item-actions">
                        <button class="btn btn-sm btn-outline" onclick="app.editarFinca(${f.id},'${f.nombre}','${f.region||''}','${f.departamento||''}')">✏️</button>
                        <button class="btn btn-sm btn-danger" onclick="app.eliminarFinca(${f.id},'${f.nombre}')">🗑️</button>
                    </div>
                </div>
            `).join('');
        } catch (e) {
            container.innerHTML = '<p class="empty-state">Error cargando fincas</p>';
        }
    },

    mostrarFormFinca() {
        document.getElementById('formFinca').classList.remove('hidden');
        document.getElementById('fincaNombre').value = '';
        document.getElementById('fincaRegion').value = '';
        document.getElementById('fincaDepto').value = '';
        document.getElementById('fincaNombre').focus();
    },

    ocultarFormFinca() {
        document.getElementById('formFinca').classList.add('hidden');
    },

    async guardarFinca() {
        const nombre = document.getElementById('fincaNombre').value.trim();
        if (!nombre) {
            this.mostrarModal('Error', 'El nombre de la finca es obligatorio.');
            return;
        }
        try {
            await api.createFinca({
                user_id: this.userId,
                nombre,
                region: document.getElementById('fincaRegion').value.trim(),
                departamento: document.getElementById('fincaDepto').value.trim(),
            });
            this.ocultarFormFinca();
            await this.cargarFincas();
            this.mostrarModal('✅ Listo', `Finca "${nombre}" creada exitosamente.`);
        } catch (e) {
            this.mostrarModal('Error', 'No se pudo crear la finca: ' + e.message);
        }
    },

    editarFinca(id, nombre, region, depto) {
        const nuevoNombre = prompt('Nuevo nombre:', nombre);
        if (!nuevoNombre) return;
        api.updateFinca(id, { nombre: nuevoNombre }).then(() => this.cargarFincas()).catch(e => alert('Error: ' + e.message));
    },

    async eliminarFinca(id, nombre) {
        if (!confirm(`¿Eliminar la finca "${nombre}" y TODOS sus datos?\n\nEsta acción no se puede deshacer.`)) return;
        if (!confirm(`⚠️ CONFIRMACIÓN FINAL\n\n¿Estás SEGURO de eliminar "${nombre}"?`)) return;
        try {
            await api.deleteFinca(id);
            await this.cargarFincas();
            this.mostrarModal('🗑️ Eliminado', `Finca "${nombre}" y todos sus datos fueron eliminados.`);
        } catch (e) {
            this.mostrarModal('Error', e.message);
        }
    },

    // ═══════════════════════════════════════════
    // LOTES — CRUD
    // ═══════════════════════════════════════════

    async cargarSelectorFincaLotes() {
        const select = document.getElementById('lotesFincaSelect');
        try {
            const data = await api.getFincas(this.userId);
            const fincas = data.fincas || [];
            select.innerHTML = fincas.map(f => `<option value="${f.id}">${f.nombre}</option>`).join('');
            if (fincas.length > 0) {
                await this.cargarLotes();
            } else {
                document.getElementById('lotesList').innerHTML = '<p class="empty-state"><span class="icon">🗺️</span>Creá una finca primero.</p>';
            }
        } catch (e) { console.error(e); }
    },

    async cargarLotes() {
        const fincaId = parseInt(document.getElementById('lotesFincaSelect').value);
        if (!fincaId) return;
        const container = document.getElementById('lotesList');
        try {
            const data = await api.getLotes(fincaId);
            const lotes = data.lotes || [];
            if (lotes.length === 0) {
                container.innerHTML = '<p class="empty-state"><span class="icon">🌱</span>No hay lotes en esta finca. ¡Creá el primero!</p>';
                return;
            }
            container.innerHTML = lotes.map(l => `
                <div class="list-item">
                    <div class="item-main">
                        <div class="item-title">${l.nombre}</div>
                        <div class="item-sub">${l.area_hectareas || 0} ha | ${l.num_arboles || 0} árboles | ${l.variedad || 'Sin variedad'} ${l.fecha_siembra ? '| Sembrado: ' + l.fecha_siembra : ''}</div>
                    </div>
                    <div class="item-actions">
                        <button class="btn btn-sm btn-danger" onclick="app.eliminarLote(${l.id},'${l.nombre}')">🗑️</button>
                    </div>
                </div>
            `).join('');
        } catch (e) {
            container.innerHTML = '<p class="empty-state">Error cargando lotes</p>';
        }
    },

    mostrarFormLote() {
        document.getElementById('formLote').classList.remove('hidden');
        const fincaId = parseInt(document.getElementById('lotesFincaSelect').value);
        document.getElementById('loteNombre').value = '';
        document.getElementById('loteArea').value = '';
        document.getElementById('loteArboles').value = '';
        document.getElementById('loteVariedad').value = '';
        document.getElementById('loteFechaSiembra').value = '';
        document.getElementById('loteNombre').focus();
    },

    ocultarFormLote() {
        document.getElementById('formLote').classList.add('hidden');
    },

    async guardarLote() {
        const nombre = document.getElementById('loteNombre').value.trim();
        if (!nombre) { this.mostrarModal('Error', 'El nombre del lote es obligatorio.'); return; }
        const fincaId = parseInt(document.getElementById('lotesFincaSelect').value);
        try {
            await api.createLote({
                finca_id: fincaId,
                nombre,
                area_hectareas: parseFloat(document.getElementById('loteArea').value) || 0,
                num_arboles: parseInt(document.getElementById('loteArboles').value) || 0,
                variedad: document.getElementById('loteVariedad').value.trim(),
                fecha_siembra: document.getElementById('loteFechaSiembra').value,
            });
            this.ocultarFormLote();
            await this.cargarLotes();
            this.mostrarModal('✅ Listo', `Lote "${nombre}" creado.`);
        } catch (e) {
            this.mostrarModal('Error', e.message);
        }
    },

    async eliminarLote(id, nombre) {
        if (!confirm(`¿Eliminar el lote "${nombre}" y sus transacciones?`)) return;
        try {
            await api.deleteLote(id);
            await this.cargarLotes();
            this.mostrarModal('🗑️ Eliminado', `Lote "${nombre}" eliminado.`);
        } catch (e) { this.mostrarModal('Error', e.message); }
    },

    // ═══════════════════════════════════════════
    // INGRESOS
    // ═══════════════════════════════════════════

    async cargarSelectorFincaIngresos() {
        const select = document.getElementById('ingresosFincaSelect');
        const lotesSelect = document.getElementById('ingresoLote');
        try {
            const data = await api.getFincas(this.userId);
            const fincas = data.fincas || [];
            if (fincas.length === 0) return;
            document.getElementById('ingresosSelectorFinca').classList.remove('hidden');
            select.innerHTML = fincas.map(f => `<option value="${f.id}">${f.nombre}</option>`).join('');
            await this.cargarIngresos();
        } catch (e) { console.error(e); }
    },

    async cargarIngresos() {
        const fincaId = parseInt(document.getElementById('ingresosFincaSelect').value);
        if (!fincaId) return;

        // Cargar lotes para el selector
        try {
            const lotesData = await api.getLotes(fincaId);
            const lotesSelect = document.getElementById('ingresoLote');
            lotesSelect.innerHTML = '<option value="0">General (sin lote específico)</option>' +
                (lotesData.lotes || []).map(l => `<option value="${l.id}">${l.nombre}</option>`).join('');
        } catch (e) {}

        // Cargar historial
        try {
            const data = await api.getTransacciones(fincaId);
            const ingresos = (data.transacciones || []).filter(t => t.categoria.startsWith('ingreso_'));
            const container = document.getElementById('ingresosList');
            if (ingresos.length === 0) {
                container.innerHTML = '<p class="empty-state">No hay ingresos registrados.</p>';
                document.getElementById('ingresosResumen').innerHTML = '';
                return;
            }

            const total = ingresos.reduce((s, t) => s + (t.valor_total || 0), 0);
            const totalKg = ingresos.reduce((s, t) => s + (t.cantidad || 0), 0);

            document.getElementById('ingresosResumen').innerHTML = `
                <div class="cards" style="margin-bottom:0;">
                    <div class="card"><span class="card-label">Total ingresos</span><span class="card-value">${this.formatearDinero(total)}</span></div>
                    <div class="card"><span class="card-label">Total kg</span><span class="card-value">${totalKg.toFixed(1)} kg</span></div>
                    <div class="card"><span class="card-label">Precio prom.</span><span class="card-value">${totalKg > 0 ? this.formatearDinero(total / totalKg) : '$0'}/kg</span></div>
                </div>`;

            container.innerHTML = ingresos.slice(-30).reverse().map(t => `
                <div class="list-item">
                    <div class="item-main">
                        <div class="item-title">${t.categoria === 'ingreso_cps' ? 'CPS' : 'Pasilla'} — ${t.fecha}</div>
                        <div class="item-sub">${t.cantidad || 0} kg × $${(t.valor_unitario||0).toLocaleString()}</div>
                    </div>
                    <div class="item-value">${this.formatearDinero(t.valor_total)}</div>
                </div>
            `).join('');
        } catch (e) { console.error(e); }
    },

    async guardarIngreso() {
        const fincaId = parseInt(document.getElementById('ingresosFincaSelect').value);
        const fecha = document.getElementById('ingresoFecha').value;
        const tipo = document.getElementById('ingresoTipo').value;
        const kg = parseFloat(document.getElementById('ingresoKg').value);
        const vt = parseFloat(document.getElementById('ingresoValorTotal').value);
        const loteId = parseInt(document.getElementById('ingresoLote').value);

        if (!fecha || !kg || !vt) {
            this.mostrarModal('Error', 'Completá fecha, cantidad y valor total.');
            return;
        }

        try {
            const vu = vt / kg;
            await api.createTransaccion({
                finca_id: fincaId,
                lote_id: loteId,
                categoria: tipo,
                fecha,
                labor: document.getElementById('ingresoLabor').value.trim() || 'Venta cosecha',
                producto: tipo === 'ingreso_cps' ? 'CPS' : 'Pasilla',
                cantidad: kg,
                unidad: 'kg',
                valor_unitario: Math.round(vu),
                valor_total: vt,
            });
            // Reset form
            document.getElementById('ingresoFecha').value = '';
            document.getElementById('ingresoKg').value = '';
            document.getElementById('ingresoValorTotal').value = '';
            document.getElementById('ingresoLabor').value = '';
            await this.cargarIngresos();
            this.mostrarModal('✅ Ingreso guardado', `$${vt.toLocaleString()} COP por ${kg} kg registrados.`);
        } catch (e) {
            this.mostrarModal('Error', e.message);
        }
    },

    // ═══════════════════════════════════════════
    // COSTOS — Flujo completo (multi-step)
    // ═══════════════════════════════════════════

    async cargarSelectorFincaCostos() {
        try {
            const data = await api.getFincas(this.userId);
            const fincas = data.fincas || [];
            document.getElementById('costosFincaSelect').innerHTML =
                fincas.map(f => `<option value="${f.id}">${f.nombre}</option>`).join('');
            if (fincas.length > 0) {
                this.costoState.fincaId = fincas[0].id;
                this.costoState.loteIds = [];
                this.costoState.modo = 'todos';
                await this.costosSeleccionarFinca();
            }
            // Cargar últimos costos
            await this.cargarListaCostos(fincas[0]?.id);
        } catch (e) { console.error(e); }
    },

    async costosSeleccionarFinca() {
        const fincaId = parseInt(document.getElementById('costosFincaSelect').value);
        this.costoState.fincaId = fincaId;
        this.costoState.loteIds = [];
        this.costoState.modo = 'todos';

        // Mostrar step 2
        document.getElementById('costosStep2').classList.remove('hidden');
        document.getElementById('costosStep3').classList.add('hidden');
        document.getElementById('costosStep4').classList.add('hidden');
        document.getElementById('costosStep5').classList.add('hidden');
        document.getElementById('costosStep6').classList.add('hidden');

        // Cargar lotes
        try {
            const data = await api.getLotes(fincaId);
            const lotes = data.lotes || [];
            const container = document.getElementById('costosLoteOptions');
            if (lotes.length === 0) {
                container.innerHTML = '<p class="hint">No hay lotes en esta finca. Los costos se asignarán a la finca completa.</p>';
                this.costoState.modo = 'todos';
                return;
            }
            // Mostrar lotes para selección (modo checkboxes)
            container.innerHTML = lotes.map(l => `
                <label class="lote-checkbox" onclick="this.classList.toggle('selected')">
                    <input type="checkbox" value="${l.id}" ${this.costoState.modo === 'todos' ? 'checked' : ''}>
                    <div class="lote-info">
                        <div class="name">${l.nombre}</div>
                        <div class="detail">${l.area_hectareas || 0} ha | ${l.num_arboles || 0} árboles</div>
                    </div>
                </label>
            `).join('');
        } catch (e) { console.error(e); }
    },

    costosModoLote(modo) {
        this.costoState.modo = modo;
        document.querySelectorAll('#costosStep2 .toggle-btn').forEach(b => b.classList.remove('active'));
        document.getElementById(`costosModo${modo.charAt(0).toUpperCase() + modo.slice(1)}`).classList.add('active');

        const checkboxes = document.querySelectorAll('#costosLoteOptions input[type="checkbox"]');
        checkboxes.forEach(cb => {
            cb.checked = (modo === 'todos');
            cb.closest('.lote-checkbox')?.classList.toggle('selected', cb.checked);
        });

        if (modo === 'especifico') {
            checkboxes.forEach((cb, i) => { cb.checked = (i === 0); });
        }
    },

    costosSiguienteCategoria() {
        // Recolectar lote IDs
        const checkboxes = document.querySelectorAll('#costosLoteOptions input[type="checkbox"]:checked');
        this.costoState.loteIds = Array.from(checkboxes).map(cb => parseInt(cb.value));

        if (this.costoState.modo !== 'todos' && this.costoState.loteIds.length === 0) {
            this.mostrarModal('Atención', 'Seleccioná al menos un lote o elegí "Toda la finca".');
            return;
        }

        // Mostrar step 3 (categorías)
        document.getElementById('costosStep3').classList.remove('hidden');
        document.getElementById('costosStep2').classList.add('hidden');

        // Cargar categorías
        api.getCategoriasCostos().then(cats => {
            const grid = document.getElementById('costosCategoriasGrid');
            const todas = { ...cats.categorias_padre, ...cats.categorias_simple };
            grid.innerHTML = Object.entries(todas).map(([key, nombre]) => `
                <button class="menu-item" onclick="app.costosSeleccionarCategoria('${key}')">
                    <span class="menu-icon">${key.startsWith('instalacion') ? '🌱' : key.startsWith('arvenses') ? '🌿' : key.startsWith('fertilizacion') ? '🧪' : key.startsWith('fitosanitario') ? '🛡️' : key.startsWith('sombrio') ? '🌳' : key.startsWith('otras') ? '🔧' : key.startsWith('recoleccion') ? '☕' : key.startsWith('beneficio') ? '🏭' : key.startsWith('administrativo') ? '📋' : '📌'}</span>
                    <span class="menu-label">${nombre}</span>
                </button>
            `).join('');
        }).catch(e => console.error(e));
    },

    costosSeleccionarCategoria(catKey) {
        this.costoState.categoria = catKey;

        // Determinar si es compuesta (MO+Insumos) o simple
        const categoriasCompuestas = ['instalacion', 'arvenses', 'fertilizacion', 'fitosanitario', 'sombrio', 'otras_labores'];
        const categoriasSimples = ['recoleccion', 'beneficio', 'administrativo'];

        if (categoriasCompuestas.includes(catKey)) {
            // MO + Insumos: preguntar tipo
            document.getElementById('costosStep4').classList.remove('hidden');
            document.getElementById('costosStep3').classList.add('hidden');
            const btns = document.getElementById('costosTipoBtns');
            btns.innerHTML = `
                <button class="btn btn-primary" onclick="app.costosIniciarMO()">👷 Solo MO</button>
                <button class="btn btn-info" onclick="app.costosIniciarInsumos()">🧪 Solo Insumos</button>
                <button class="btn btn-success" onclick="app.costosIniciarAmbos()">👷‍♂️🧪 Ambos</button>
            `;
        } else {
            // Simple: solo MO, ir directo
            this.costoState.tipo = 'mo';
            document.getElementById('costosStep3').classList.add('hidden');
            this.mostrarFormularioMO();
        }
    },

    costosIniciarMO() {
        this.costoState.tipo = 'mo';
        document.getElementById('costosStep4').classList.add('hidden');
        this.mostrarFormularioMO();
    },

    costosIniciarInsumos() {
        this.costoState.tipo = 'insumos';
        document.getElementById('costosStep4').classList.add('hidden');
        this.mostrarFormularioInsumos();
    },

    costosIniciarAmbos() {
        this.costoState.tipo = 'ambos';
        document.getElementById('costosStep4').classList.add('hidden');
        this.mostrarFormularioMO();
    },

    mostrarFormularioMO() {
        document.getElementById('costosStep5').classList.remove('hidden');
        document.getElementById('costoMOFecha').value = new Date().toISOString().split('T')[0];
        document.getElementById('costoMOLabor').value = '';
        document.getElementById('costoMOCantidad').value = '';
        document.getElementById('costoMOVU').value = '';
        document.getElementById('costoMOVT').value = '';
        document.getElementById('costoMOHint').textContent = '';
    },

    mostrarFormularioInsumos() {
        document.getElementById('costosStep6').classList.remove('hidden');
        document.getElementById('costoInsumoFecha').value = new Date().toISOString().split('T')[0];
        document.getElementById('costoInsumoProducto').value = '';
        document.getElementById('costoInsumoCantidad').value = '';
        document.getElementById('costoInsumoVU').value = '';
        document.getElementById('costoInsumoVT').value = '';
    },

    costosAtras() {
        // Volver al paso anterior
        if (!document.getElementById('costosStep6').classList.contains('hidden')) {
            document.getElementById('costosStep6').classList.add('hidden');
            if (this.costoState.tipo === 'ambos') {
                document.getElementById('costosStep5').classList.remove('hidden');
            } else {
                document.getElementById('costosStep4').classList.remove('hidden');
            }
        } else if (!document.getElementById('costosStep5').classList.contains('hidden')) {
            document.getElementById('costosStep5').classList.add('hidden');
            document.getElementById('costosStep4').classList.remove('hidden');
        } else if (!document.getElementById('costosStep4').classList.contains('hidden')) {
            document.getElementById('costosStep4').classList.add('hidden');
            document.getElementById('costosStep3').classList.remove('hidden');
        } else if (!document.getElementById('costosStep3').classList.contains('hidden')) {
            document.getElementById('costosStep3').classList.add('hidden');
            document.getElementById('costosStep2').classList.remove('hidden');
        }
    },

    async guardarCostoMO() {
        const fecha = document.getElementById('costoMOFecha').value;
        const labor = document.getElementById('costoMOLabor').value.trim();
        const cantidad = parseFloat(document.getElementById('costoMOCantidad').value);
        const vu = parseFloat(document.getElementById('costoMOVU').value);
        let vt = parseFloat(document.getElementById('costoMOVT').value);

        if (!fecha || !labor || !cantidad || !vu) {
            this.mostrarModal('Error', 'Completá todos los campos de MO.');
            return;
        }
        if (!vt) vt = cantidad * vu;

        const cat = this.costoState.categoria;
        const catMO = ['instalacion','arvenses','fertilizacion','fitosanitario','sombrio','otras_labores'].includes(cat)
            ? `${cat}_mo` : cat;

        try {
            for (const loteId of (this.costoState.modo === 'todos' ? [0] : this.costoState.loteIds)) {
                await api.registrarCostoMO({
                    finca_id: this.costoState.fincaId,
                    lote_id: loteId,
                    categoria: catMO,
                    fecha,
                    labor,
                    cantidad,
                    valor_unitario: vu,
                    valor_total: vt,
                });
            }

            this.mostrarModal('✅ MO guardada', `${labor} — ${cantidad} jornales por $${vt.toLocaleString()}`);

            // Si es modo "ambos", pasar a insumos
            if (this.costoState.tipo === 'ambos') {
                document.getElementById('costosStep5').classList.add('hidden');
                this.mostrarFormularioInsumos();
            } else {
                // Resetear
                this.costosReiniciarFlujo();
                await this.cargarListaCostos(this.costoState.fincaId);
            }
        } catch (e) {
            this.mostrarModal('Error', e.message);
        }
    },

    async guardarCostoInsumo() {
        await this._guardarInsumo(false);
    },

    async guardarCostoInsumoYOtro() {
        await this._guardarInsumo(true);
    },

    async _guardarInsumo(otro) {
        const fecha = document.getElementById('costoInsumoFecha').value;
        const producto = document.getElementById('costoInsumoProducto').value.trim();
        const cantidad = parseFloat(document.getElementById('costoInsumoCantidad').value);
        const unidad = document.getElementById('costoInsumoUnidad').value;
        const vu = parseFloat(document.getElementById('costoInsumoVU').value);
        let vt = parseFloat(document.getElementById('costoInsumoVT').value);

        if (!fecha || !producto || !cantidad || !vu) {
            this.mostrarModal('Error', 'Completá todos los campos del insumo.');
            return;
        }
        if (!vt) vt = cantidad * vu;

        const cat = `${this.costoState.categoria}_insumos`;

        try {
            for (const loteId of (this.costoState.modo === 'todos' ? [0] : this.costoState.loteIds)) {
                await api.registrarCostoInsumo({
                    finca_id: this.costoState.fincaId,
                    lote_id: loteId,
                    categoria: cat,
                    fecha,
                    producto,
                    cantidad,
                    unidad,
                    valor_unitario: vu,
                    valor_total: vt,
                });
            }

            if (otro) {
                // Limpiar y seguir
                document.getElementById('costoInsumoProducto').value = '';
                document.getElementById('costoInsumoCantidad').value = '';
                document.getElementById('costoInsumoVU').value = '';
                document.getElementById('costoInsumoVT').value = '';
                document.getElementById('costoInsumoProducto').focus();
                this.mostrarModal('✅ Insumo guardado', 'Podés seguir agregando más insumos.');
            } else {
                if (this.costoState.tipo === 'ambos') {
                    this.costosReiniciarFlujo();
                } else {
                    this.costosReiniciarFlujo();
                }
                await this.cargarListaCostos(this.costoState.fincaId);
                this.mostrarModal('✅ Insumo guardado', `${producto} — ${cantidad} ${unidad} por $${vt.toLocaleString()}`);
            }
        } catch (e) {
            this.mostrarModal('Error', e.message);
        }
    },

    costosReiniciarFlujo() {
        document.getElementById('costosStep6').classList.add('hidden');
        document.getElementById('costosStep5').classList.add('hidden');
        document.getElementById('costosStep4').classList.add('hidden');
        document.getElementById('costosStep3').classList.add('hidden');
        document.getElementById('costosStep2').classList.remove('hidden');
        this.costoState.categoria = null;
        this.costoState.tipo = null;
    },

    async cargarListaCostos(fincaId) {
        if (!fincaId) return;
        try {
            const data = await api.getTransacciones(fincaId);
            const costos = (data.transacciones || []).filter(t => !t.categoria.startsWith('ingreso_'));
            const container = document.getElementById('costosList');
            if (costos.length === 0) {
                container.innerHTML = '<p class="empty-state">No hay costos registrados.</p>';
                return;
            }
            container.innerHTML = costos.slice(-20).reverse().map(t => `
                <div class="list-item">
                    <div class="item-main">
                        <div class="item-title">${t.categoria} — ${t.fecha}</div>
                        <div class="item-sub">${t.labor || t.producto || ''} ${t.cantidad ? '| ' + t.cantidad + ' ' + (t.unidad||'') : ''}</div>
                    </div>
                    <div class="item-value">${this.formatearDinero(t.valor_total)}</div>
                </div>
            `).join('');
        } catch (e) { console.error(e); }
    },

    async filtrarCostos() {
        const fincaId = this.costoState.fincaId;
        const inicio = document.getElementById('costosFiltroInicio').value;
        const fin = document.getElementById('costosFiltroFin').value;
        if (!fincaId || !inicio || !fin) return;

        try {
            const data = await api.getTransacciones(fincaId, inicio, fin);
            const costos = (data.transacciones || []).filter(t => !t.categoria.startsWith('ingreso_'));
            const container = document.getElementById('costosList');
            if (costos.length === 0) {
                container.innerHTML = '<p class="empty-state">No hay costos en este período.</p>';
                return;
            }
            const total = costos.reduce((s, t) => s + (t.valor_total || 0), 0);
            container.innerHTML = `<p class="hint mb-1">Mostrando ${costos.length} costos — Total: ${this.formatearDinero(total)}</p>` +
                costos.slice(-30).reverse().map(t => `
                    <div class="list-item">
                        <div class="item-main">
                            <div class="item-title">${t.categoria} — ${t.fecha}</div>
                            <div class="item-sub">${t.labor || t.producto || ''}</div>
                        </div>
                        <div class="item-value">${this.formatearDinero(t.valor_total)}</div>
                    </div>
                `).join('');
        } catch (e) { console.error(e); }
    },

    limpiarFiltroCostos() {
        document.getElementById('costosFiltroInicio').value = '';
        document.getElementById('costosFiltroFin').value = '';
        this.cargarListaCostos(this.costoState.fincaId);
    },

    // ═══════════════════════════════════════════
    // PRESUPUESTO
    // ═══════════════════════════════════════════

    async cargarSelectorFincaPresupuesto() {
        try {
            const data = await api.getFincas(this.userId);
            const fincas = data.fincas || [];
            document.getElementById('presupFincaSelect').innerHTML =
                fincas.map(f => `<option value="${f.id}">${f.nombre}</option>`).join('');
            if (fincas.length > 0) await this.cargarPresupuestoMenu();
        } catch (e) { console.error(e); }
    },

    async cargarPresupuestoMenu() {
        const fincaId = parseInt(document.getElementById('presupFincaSelect').value);
        if (!fincaId) return;

        // Cargar años
        const anioSelect = document.getElementById('presupAnio');
        const anioActual = new Date().getFullYear();
        anioSelect.innerHTML = '';
        for (let a = anioActual - 1; a <= anioActual + 2; a++) {
            anioSelect.innerHTML += `<option value="${a}" ${a === anioActual ? 'selected' : ''}>${a}</option>`;
        }

        this.presupuestoAnio = anioActual;
        this.presupMostrar('crear');
    },

    presupMostrar(tab) {
        ['crear', 'consultar', 'ejecucion'].forEach(t => {
            document.getElementById(`presup${t.charAt(0).toUpperCase() + t.slice(1)}`).classList.toggle('active', t === tab);
            document.getElementById(`presup${t.charAt(0).toUpperCase() + t.slice(1)}Btn`).classList.toggle('active', t === tab);
        });
        const fincaId = parseInt(document.getElementById('presupFincaSelect').value);
        if (tab === 'consultar') this.cargarPresupuestoConsultar(fincaId);
        if (tab === 'ejecucion') this.cargarPresupuestoEjecucion(fincaId);
    },

    async cargarPresupuestoSugerido() {
        const fincaId = parseInt(document.getElementById('presupFincaSelect').value);
        const anio = parseInt(document.getElementById('presupAnio').value);
        if (!fincaId) return;

        try {
            const data = await api.getPresupuestoSugerido(fincaId);
            const sugerido = data.sugerido || {};

            // También cargar presupuesto existente si hay
            let existente = {};
            try {
                const presData = await api.getPresupuesto(fincaId, anio);
                if (presData.presupuesto) {
                    presData.presupuesto.forEach(p => { existente[p.categoria] = p.monto_planificado; });
                }
            } catch (e) {}

            const container = document.getElementById('presupCategorias');
            container.innerHTML = `<p class="hint mb-1">Área: ${data.area?.toFixed(1) || '?'} ha — Costo ref: ${this.formatearDinero(data.costo_total_referencia)}</p>`;

            const todasCategorias = { ...PRESUPUESTO_PORCENTAJES };
            for (const [rubro, pct] of Object.entries(todasCategorias)) {
                const valorSugerido = sugerido[rubro] || 0;
                const valorActual = existente[rubro] || valorSugerido;
                container.innerHTML += `
                    <div class="presupuesto-categoria">
                        <span class="cat-name">${this.nombreRubro(rubro)}</span>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <input type="number" id="presup_${rubro}" value="${Math.round(valorActual)}" style="width:130px;padding:6px 8px;border:1px solid var(--border);border-radius:6px;text-align:right;" step="10000">
                            <span class="cat-pct" style="color:var(--text-light);font-size:0.75em;">${(pct*100).toFixed(0)}%</span>
                        </div>
                    </div>
                `;
            }

            // Total
            container.innerHTML += `
                <div class="flex-between mt-1" style="padding:8px 12px;background:var(--primary-bg);border-radius:8px;">
                    <strong>Total planificado</strong>
                    <strong id="presupTotal">${this.formatearDinero(Object.values(existente).reduce((s,v) => s+v, 0) || Object.values(sugerido).reduce((s,v) => s+v, 0))}</strong>
                </div>
            `;
        } catch (e) {
            console.error(e);
            this.mostrarModal('Error', 'No se pudieron calcular montos sugeridos.');
        }
    },

    async guardarPresupuesto() {
        const fincaId = parseInt(document.getElementById('presupFincaSelect').value);
        const anio = parseInt(document.getElementById('presupAnio').value);

        const datos = {};
        const rubros = Object.keys(PRESUPUESTO_PORCENTAJES);
        rubros.forEach(r => {
            const input = document.getElementById(`presup_${r}`);
            if (input) datos[r] = parseFloat(input.value) || 0;
        });

        try {
            await api.guardarPresupuesto(fincaId, { finca_id: fincaId, anio, datos });
            this.mostrarModal('✅ Presupuesto guardado', `Presupuesto ${anio} guardado exitosamente. Total: ${this.formatearDinero(Object.values(datos).reduce((s,v) => s+v, 0))}`);
        } catch (e) {
            this.mostrarModal('Error', e.message);
        }
    },

    async cargarPresupuestoConsultar(fincaId) {
        const container = document.getElementById('presupConsultarContent');
        const anioSelect = document.getElementById('presupAnio');
        const anio = parseInt(anioSelect?.value) || new Date().getFullYear();

        try {
            const data = await api.getPresupuesto(fincaId, anio);
            if (!data.presupuesto || data.presupuesto.length === 0) {
                container.innerHTML = '<p class="empty-state"><span class="icon">📋</span>No hay presupuesto para este año. Creá uno en la pestaña "Crear".</p>';
                return;
            }
            const total = data.presupuesto.reduce((s, p) => s + (p.monto_planificado || 0), 0);
            container.innerHTML = `<p class="hint mb-1">Presupuesto ${anio} — Total: <strong>${this.formatearDinero(total)}</strong></p>` +
                data.presupuesto.map(p => `
                    <div class="presupuesto-categoria">
                        <span class="cat-name">${this.nombreRubro(p.categoria)}</span>
                        <span class="cat-plan">${this.formatearDinero(p.monto_planificado)}</span>
                    </div>
                `).join('');
        } catch (e) {
            container.innerHTML = '<p class="empty-state">Error cargando presupuesto.</p>';
        }
    },

    async cargarPresupuestoEjecucion(fincaId) {
        const container = document.getElementById('presupEjecucionContent');
        const anioSelect = document.getElementById('presupAnio');
        const anio = parseInt(anioSelect?.value) || new Date().getFullYear();

        try {
            const ejec = await api.getEjecucionPresupuesto(fincaId, anio);
            if (!ejec.categorias || ejec.categorias.length === 0) {
                container.innerHTML = '<p class="empty-state"><span class="icon">📊</span>No hay datos de ejecución para este año.</p>';
                return;
            }

            container.innerHTML = `
                <div class="cards" style="margin-bottom:12px;">
                    <div class="card"><span class="card-label">Planificado</span><span class="card-value">${this.formatearDinero(ejec.total_planificado)}</span></div>
                    <div class="card"><span class="card-label">Ejecutado</span><span class="card-value">${this.formatearDinero(ejec.total_ejecutado)}</span></div>
                    <div class="card"><span class="card-label">Diferencia</span><span class="card-value ${(ejec.total_diferencia||0) <= 0 ? 'text-success' : 'text-danger'}">${this.formatearDinero(ejec.total_diferencia)}</span></div>
                </div>
                <div class="list-section"><h3>Detalle por categoría</h3>
            `;

            ejec.categorias.forEach(cat => {
                const pct = cat.pct_ejecucion || 0;
                const clase = pct <= 70 ? 'fill-green' : pct <= 90 ? 'fill-yellow' : 'fill-red';
                const semaforo = pct <= 70 ? 'semaforo-verde' : pct <= 90 ? 'semaforo-amarillo' : 'semaforo-rojo';
                container.innerHTML += `
                    <div class="presupuesto-categoria" style="flex-direction:column;align-items:stretch;">
                        <div class="flex-between" style="margin-bottom:4px;">
                            <span class="cat-name">${this.nombreRubro(cat.categoria)}</span>
                            <span class="${semaforo}" style="font-weight:700;">${pct.toFixed(0)}%</span>
                        </div>
                        <div class="flex-between" style="font-size:0.78em;color:var(--text-secondary);">
                            <span>Plan: ${this.formatearDinero(cat.monto_planificado)}</span>
                            <span>Real: ${this.formatearDinero(cat.monto_ejecutado)}</span>
                        </div>
                        <div class="progress-bar">
                            <div class="fill ${clase}" style="width:${Math.min(pct, 100)}%"></div>
                        </div>
                    </div>
                `;
            });

            container.innerHTML += '</div>';
        } catch (e) {
            container.innerHTML = '<p class="empty-state">Error cargando ejecución.</p>';
        }
    },

    // ═══════════════════════════════════════════
    // INDICADORES
    // ═══════════════════════════════════════════

    async cargarSelectorFincaIndicadores() {
        try {
            const data = await api.getFincas(this.userId);
            const fincas = data.fincas || [];
            document.getElementById('indicFincaSelect').innerHTML =
                fincas.map(f => `<option value="${f.id}">${f.nombre}</option>`).join('');
            if (fincas.length > 0) await this.cargarTodosIndicadores();
        } catch (e) { console.error(e); }
    },

    async cargarTodosIndicadores() {
        const fincaId = parseInt(document.getElementById('indicFincaSelect').value);
        if (!fincaId) return;

        try {
            const ind = await api.getIndicadores(fincaId);

            // General
            const generalGrid = document.getElementById('indicGeneralGrid');
            generalGrid.innerHTML = `
                <div class="indicador-item"><span class="indicador-label">Área total</span><span class="indicador-value">${(ind.area_total||0).toFixed(1)} ha</span></div>
                <div class="indicador-item"><span class="indicador-label">Productividad</span><span class="indicador-value">${(ind.productividad||0).toFixed(1)} kg/ha</span><span class="indicador-ref">Ref: ${(ind.fnc_productividad_ha||0).toLocaleString()} kg/ha</span></div>
                <div class="indicador-item"><span class="indicador-label">Rendimiento</span><span class="indicador-value">${(ind.rendimiento||0).toFixed(1)} kg/ha</span><span class="indicador-ref">Ref: ${(ind.fnc_rendimiento_ha||0).toLocaleString()} kg/ha</span></div>
                <div class="indicador-item"><span class="indicador-label">Costo total/ha</span><span class="indicador-value">${this.formatearDinero(ind.costo_total_por_ha)}</span><span class="indicador-ref">Ref: ${this.formatearDinero(ind.fnc_costo_ha)}</span></div>
                <div class="indicador-item"><span class="indicador-label">Costo/kg CPS</span><span class="indicador-value">${this.formatearDinero(ind.costo_por_kilo)}</span><span class="indicador-ref">Ref: ${this.formatearDinero(ind.fnc_costo_produccion_kilo)}</span></div>
                <div class="indicador-item"><span class="indicador-label">Precio venta prom.</span><span class="indicador-value">${this.formatearDinero(ind.precio_venta_promedio)}</span><span class="indicador-ref">Ref: ${this.formatearDinero(ind.fnc_precio_venta_promedio)}</span></div>
                <div class="indicador-item"><span class="indicador-label">Margen/ha</span><span class="indicador-value ${(ind.margen_por_ha||0) >= 0 ? 'text-success' : 'text-danger'}">${this.formatearDinero(ind.margen_por_ha)}</span><span class="indicador-ref">Ref: ${this.formatearDinero(ind.fnc_margen_ha)}</span></div>
                <div class="indicador-item"><span class="indicador-label">Jornales/ha</span><span class="indicador-value">${(ind.jornales_por_ha||0).toFixed(1)}</span></div>
                <div class="indicador-item"><span class="indicador-label">Eficiencia MO</span><span class="indicador-value">${(ind.eficiencia_mo||0).toFixed(1)} kg/jornal</span></div>
                <div class="indicador-item"><span class="indicador-label">Insumos total</span><span class="indicador-value">${(ind.insumos_total_kg||0).toFixed(1)} kg</span></div>
            `;

            // Charts comparativa
            const prod = ind.productividad || 0;
            const refProd = ind.fnc_productividad_ha || 1669;
            const costo = ind.costo_total_por_ha || 0;
            const refCosto = ind.fnc_costo_ha || 16340000;

            setTimeout(() => {
                charts.drawHorizontalBar('chartIndicComparativa', 'Productividad (kg/ha)',
                    prod, refProd, prod >= refProd ? '#2E7D32' : '#FF8F00', '#BDBDBD');
            }, 100);

            // MO
            const moGrid = document.getElementById('indicMOGrid');
            moGrid.innerHTML = `
                <div class="indicador-item"><span class="indicador-label">Total Jornales</span><span class="indicador-value">${(ind.total_jornales||0).toFixed(1)}</span></div>
                <div class="indicador-item"><span class="indicador-label">Costo MO total</span><span class="indicador-value">${this.formatearDinero(ind.costos_mo)}</span></div>
                <div class="indicador-item"><span class="indicador-label">Costo MO/ha</span><span class="indicador-value">${this.formatearDinero(ind.costo_mo_por_ha)}</span></div>
                <div class="indicador-item"><span class="indicador-label">Costo MO/kg</span><span class="indicador-value">${this.formatearDinero(ind.costo_mo_por_kg_cps)}</span></div>
                <div class="indicador-item"><span class="indicador-label">Jornales/ha</span><span class="indicador-value">${(ind.jornales_por_ha||0).toFixed(1)}</span></div>
                <div class="indicador-item"><span class="indicador-label">Eficiencia MO</span><span class="indicador-value">${(ind.eficiencia_mo||0).toFixed(1)} kg/jornal</span></div>
            `;

            // Insumos
            const insGrid = document.getElementById('indicInsumosGrid');
            insGrid.innerHTML = `
                <div class="indicador-item"><span class="indicador-label">Costo insumos total</span><span class="indicador-value">${this.formatearDinero(ind.costos_insumos)}</span></div>
                <div class="indicador-item"><span class="indicador-label">Costo insumos/ha</span><span class="indicador-value">${this.formatearDinero(ind.costo_insumos_por_ha)}</span></div>
                <div class="indicador-item"><span class="indicador-label">Costo insumos/kg</span><span class="indicador-value">${this.formatearDinero(ind.costo_insumos_por_kg_cps)}</span></div>
                <div class="indicador-item"><span class="indicador-label">Insumos total (kg eq.)</span><span class="indicador-value">${(ind.insumos_total_kg||0).toFixed(1)} kg</span></div>
                <div class="indicador-item"><span class="indicador-label">Insumos/ha</span><span class="indicador-value">${(ind.insumos_por_ha||0).toFixed(1)} kg/ha</span></div>
                <div class="indicador-item"><span class="indicador-label">Eficiencia insumos</span><span class="indicador-value">${(ind.eficiencia_insumos||0).toFixed(2)} kg/kg</span></div>
            `;

            // Financiero
            const finGrid = document.getElementById('indicFinancieroGrid');
            finGrid.innerHTML = `
                <div class="indicador-item"><span class="indicador-label">Ingresos totales</span><span class="indicador-value">${this.formatearDinero(ind.ingresos_totales)}</span></div>
                <div class="indicador-item"><span class="indicador-label">Costos totales</span><span class="indicador-value">${this.formatearDinero(ind.costos_total)}</span></div>
                <div class="indicador-item"><span class="indicador-label">Margen neto</span><span class="indicador-value ${((ind.ingresos_totales||0)-(ind.costos_total||0)) >= 0 ? 'text-success' : 'text-danger'}">${this.formatearDinero((ind.ingresos_totales||0)-(ind.costos_total||0))}</span></div>
                <div class="indicador-item"><span class="indicador-label">Kg producidos</span><span class="indicador-value">${(ind.kg_producidos||0).toFixed(1)} kg</span></div>
                <div class="indicador-item"><span class="indicador-label">Precio venta prom.</span><span class="indicador-value">${this.formatearDinero(ind.precio_venta_promedio)}/kg</span></div>
                <div class="indicador-item"><span class="indicador-label">Costo producción</span><span class="indicador-value">${this.formatearDinero(ind.costo_por_kilo)}/kg</span></div>
            `;

            setTimeout(() => {
                charts.drawDoughnutChart('chartIngresosVsCostos',
                    ['Ingresos', 'Costos'],
                    [ind.ingresos_totales || 0, ind.costos_total || 0],
                    ['#2E7D32', '#F44336']);
            }, 100);

        } catch (e) {
            console.error(e);
            document.getElementById('indicGeneralGrid').innerHTML = '<p class="empty-state">Error cargando indicadores</p>';
        }
    },

    indicMostrar(tab) {
        ['general', 'mo', 'insumos', 'financiero'].forEach(t => {
            const el = document.getElementById(`indic${t.charAt(0).toUpperCase() + t.slice(1)}`);
            if (el) el.classList.toggle('hidden', t !== tab);
            const btn = document.getElementById(`indic${t.charAt(0).toUpperCase() + t.slice(1)}Btn`);
            if (btn) btn.classList.toggle('active', t === tab);
        });
    },

    // ═══════════════════════════════════════════
    // ASESORÍA
    // ═══════════════════════════════════════════

    async cargarAsesoria() {
        try {
            const data = await api.getFincas(this.userId);
            const fincas = data.fincas || [];
            document.getElementById('asesoriaFincaSelect').innerHTML =
                '<option value="">Seleccionar finca...</option>' +
                fincas.map(f => `<option value="${f.id}">${f.nombre}</option>`).join('');
        } catch (e) {}

        // Cargar sugerencias y plan por defecto
        this.cargarSugerencias();
        this.cargarPlan();
        this.cargarContacto();
    },

    asesoriaMostrar(tab) {
        ['interpretar', 'sugerencias', 'plan', 'contacto'].forEach(t => {
            const el = document.getElementById(`asesoria${t.charAt(0).toUpperCase() + t.slice(1)}`);
            if (el) el.classList.toggle('hidden', t !== tab);
            const btn = document.getElementById(`asesoria${t.charAt(0).toUpperCase() + t.slice(1)}Btn`);
            if (btn) btn.classList.toggle('active', t === tab);
        });
    },

    async interpretarDatos() {
        const fincaId = parseInt(document.getElementById('asesoriaFincaSelect').value);
        const container = document.getElementById('asesoriaInterpretarContent');
        if (!fincaId) {
            container.innerHTML = '<p class="empty-state">Seleccioná una finca para interpretar sus datos.</p>';
            return;
        }

        try {
            const data = await api.interpretarDatos(fincaId);
            container.innerHTML = (data.analisis || []).map(a => `
                <div class="alerta alerta-${a.tipo === 'danger' ? 'danger' : a.tipo === 'warning' ? 'warning' : 'success'}">
                    <span class="icon">${a.tipo === 'danger' ? '🔴' : a.tipo === 'warning' ? '🟡' : '🟢'}</span>
                    <div class="content">
                        <strong>${a.indicador}</strong>
                        <div style="font-size:0.85em;color:var(--text-secondary);margin:2px 0;">
                            Tu valor: ${a.valor} | Referencia: ${a.referencia}
                        </div>
                        ${a.mensaje}
                    </div>
                </div>
            `).join('') || '<p class="empty-state">No hay suficientes datos para interpretar.</p>';
        } catch (e) {
            container.innerHTML = '<p class="empty-state">Error al interpretar datos.</p>';
        }
    },

    async cargarSugerencias() {
        try {
            const data = await api.getSugerencias();
            document.getElementById('asesoriaSugerenciasContent').innerHTML =
                (data.sugerencias || []).map(s => `
                    <div class="alerta alerta-info">
                        <span class="icon">${s.icono || '💡'}</span>
                        <div class="content">
                            <strong>${s.titulo}</strong>
                            ${s.descripcion}
                        </div>
                    </div>
                `).join('');
        } catch (e) { console.error(e); }
    },

    async cargarPlan() {
        try {
            const data = await api.getPlanAccion();
            const plan = data.plan || {};
            document.getElementById('asesoriaPlanContent').innerHTML = `
                <div class="form-section">
                    <h3>⏰ Corto Plazo</h3>
                    ${(plan.corto_plazo || []).map(p => `<p style="padding:4px 0;font-size:0.9em;">${p}</p>`).join('')}
                </div>
                <div class="form-section">
                    <h3>📅 Mediano Plazo</h3>
                    ${(plan.mediano_plazo || []).map(p => `<p style="padding:4px 0;font-size:0.9em;">${p}</p>`).join('')}
                </div>
                <div class="form-section">
                    <h3>🎯 Largo Plazo</h3>
                    ${(plan.largo_plazo || []).map(p => `<p style="padding:4px 0;font-size:0.9em;">${p}</p>`).join('')}
                </div>
            `;
        } catch (e) { console.error(e); }
    },

    async cargarContacto() {
        try {
            const data = await api.getContactoAsesoria();
            document.getElementById('asesoriaContactoContent').innerHTML = `
                <div class="form-section" style="text-align:center;">
                    <p style="font-size:2em;margin-bottom:8px;">👨‍🏫</p>
                    <h3>${data.nombre || 'Lucas Mateo Tabares Franco'}</h3>
                    <p style="color:var(--text-secondary);margin-bottom:4px;">Asesor: ${data.asesor || 'Ing. Jhoan Sebastian Bustamante Montes'}</p>
                    <p style="color:var(--primary);font-weight:600;">📧 ${data.email || 'mateotabares7@gmail.com'}</p>
                    <p class="hint mt-2">${data.mensaje || 'Contactanos para recibir asesoría personalizada gratuita.'}</p>
                </div>
            `;
        } catch (e) { console.error(e); }
    },

    // ═══════════════════════════════════════════
    // EXPORT / IMPORT
    // ═══════════════════════════════════════════

    async cargarSelectorFincaExport() {
        try {
            const data = await api.getFincas(this.userId);
            const fincas = data.fincas || [];
            document.getElementById('exportFincaSelect').innerHTML =
                fincas.map(f => `<option value="${f.id}">${f.nombre}</option>`).join('');
        } catch (e) { console.error(e); }
    },

    exportarExcel() {
        const fincaId = parseInt(document.getElementById('exportFincaSelect').value);
        if (!fincaId) { this.mostrarModal('Atención', 'Seleccioná una finca primero.'); return; }
        api.exportarExcel(fincaId);
        this.mostrarModal('📥 Descargando', 'El archivo Excel se está descargando.');
    },

    descargarPlantilla() {
        api.descargarPlantilla();
        this.mostrarModal('📋 Plantilla', 'Descargando plantilla vacía para importar datos.');
    },

    async importarExcel(event) {
        const file = event.target.files[0];
        if (!file) return;
        const container = document.getElementById('importResult');
        container.innerHTML = '<div class="loading"><div class="spinner"></div><p>Procesando archivo...</p></div>';

        try {
            const result = await api.importarExcel(file, this.userId);
            const r = result.resultado || {};
            const totalOk = (r.importados || []).length;
            const errores = (r.errores || []).length;
            container.innerHTML = `
                <div class="alerta alerta-success">
                    <span class="icon">✅</span>
                    <div class="content">
                        <strong>Importación completada</strong>
                        ${totalOk} registros importados (${r.fincas_creadas || 0} fincas)
                        ${errores > 0 ? `<br>${errores} errores` : ''}
                    </div>
                </div>
                ${errores > 0 ? '<div class="alerta alerta-warning"><span class="icon">⚠️</span><div class="content"><strong>Errores:</strong>' +
                    r.errores.map(e => `<br>${e.finca || e.lote || ''}: ${e.error}`).join('') + '</div></div>' : ''}
            `;
            // Recargar datos
            await this.cargarFincas();
        } catch (e) {
            container.innerHTML = `<div class="alerta alerta-danger"><span class="icon">❌</span><div class="content"><strong>Error</strong>${e.message}</div></div>`;
        }
    },

    // ═══════════════════════════════════════════
    // MODAL
    // ═══════════════════════════════════════════

    mostrarModal(titulo, contenido) {
        const overlay = document.getElementById('modalOverlay');
        const content = document.getElementById('modalContent');
        content.innerHTML = `
            <h2>${titulo}</h2>
            <p>${contenido}</p>
            <button class="btn btn-primary btn-block" onclick="app.cerrarModal()">Cerrar</button>
        `;
        overlay.classList.remove('hidden');
    },

    cerrarModal() {
        document.getElementById('modalOverlay').classList.add('hidden');
    },

    // ═══════════════════════════════════════════
    // HELPERS
    // ═══════════════════════════════════════════

    formatearDinero(value) {
        if (!value || value === 0) return '$0';
        if (value >= 1000000) return '$' + (value / 1000000).toFixed(1) + 'M';
        if (value >= 1000) return '$' + Math.round(value / 1000) + 'K';
        return '$' + Math.round(value);
    },

    nombreRubro(rubro) {
        const nombres = {
            'recoleccion': '☕ Recolección',
            'fertilizacion': '🧪 Fertilización',
            'administrativo': '📋 Gastos Admin',
            'arvenses': '🌿 Arvenses',
            'beneficio': '🏭 Beneficio',
            'fitosanitario': '🛡️ Fitosanitario',
            'renovacion': '🌱 Renovación',
            'otras_labores': '🔧 Otras Labores',
            'instalacion': '🌱 Instalación',
            'sombrio': '🌳 Sombrío',
        };
        return nombres[rubro] || rubro;
    },
};

// ═══════════════════════════════════════════
// CONSTANTES (compartidas con backend)
// ═══════════════════════════════════════════

const PRESUPUESTO_PORCENTAJES = {
    recoleccion: 0.54, fertilizacion: 0.19, administrativo: 0.07,
    arvenses: 0.06, beneficio: 0.06, fitosanitario: 0.02,
    renovacion: 0.05, otras_labores: 0.01,
};

// ─── INIT ───
document.addEventListener('DOMContentLoaded', () => app.init());
