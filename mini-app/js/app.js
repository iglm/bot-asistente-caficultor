/**
 * Lógica principal de la Mini App
 */
let currentUser = null;
let currentFincaId = null;

document.addEventListener('DOMContentLoaded', async () => {
    // Inicializar Telegram WebApp
    if (window.Telegram && window.Telegram.WebApp) {
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        currentUser = tg.initDataUnsafe?.user;
    }

    // Setup navegación
    setupNavigation();

    // Cargar datos iniciales
    await loadDashboard();
});

function setupNavigation() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(btn.dataset.tab).classList.add('active');
        });
    });
}

async function loadDashboard() {
    try {
        // Obtener finca del usuario (por defecto ID 1 para demo)
        const fincas = await api.getFincas(1);
        if (fincas.fincas && fincas.fincas.length > 0) {
            currentFincaId = fincas.fincas[0].id;
        } else {
            currentFincaId = 1; // Demo
        }

        // Cargar indicadores
        const ind = await api.getIndicadores(currentFincaId);
        document.getElementById('ingresos').textContent = formatMoney(ind.ingresos_totales || 0);
        document.getElementById('costos').textContent = formatMoney(ind.costos_total || 0);
        document.getElementById('margen').textContent = formatMoney((ind.ingresos_totales || 0) - (ind.costos_total || 0));
        document.getElementById('productividad').textContent = (ind.productividad || 0).toFixed(1) + ' kg/ha';

        // Cargar indicadores detallados
        document.getElementById('indProductividad').textContent = (ind.productividad || 0).toFixed(1) + ' kg/ha';
        document.getElementById('indRendimiento').textContent = (ind.rendimiento || 0).toFixed(1) + ' kg/ha';
        document.getElementById('indCostoHa').textContent = formatMoney(ind.costo_total_por_ha || 0);
        document.getElementById('indPrecioVenta').textContent = formatMoney(ind.precio_venta_promedio || 0);
        document.getElementById('indMargenHa').textContent = formatMoney(ind.margen_por_ha || 0);
        document.getElementById('indJornales').textContent = (ind.jornales_por_ha || 0).toFixed(1);

        // Cargar gastos por rubro
        const gastos = await api.getGastosPorRubro(currentFincaId);
        if (gastos.gastos && gastos.gastos.length > 0) {
            const labels = gastos.gastos.map(g => g.categoria.substring(0, 8));
            const data = gastos.gastos.map(g => g.total);
            const colors = ['#2E7D32', '#4CAF50', '#FF8F00', '#1976D2', '#7B1FA2', '#D32F2F'];
            setTimeout(() => charts.drawBarChart('chartGastos', labels, data, colors), 100);
        }

        // Cargar transacciones
        const tx = await api.getTransacciones(currentFincaId);
        renderTransacciones(tx.transacciones || []);

    } catch (error) {
        console.error('Error cargando dashboard:', error);
    }
}

function renderTransacciones(transacciones) {
    const container = document.getElementById('listaTransacciones');
    if (!transacciones.length) {
        container.innerHTML = '<p class="empty-state">No hay transacciones registradas.</p>';
        return;
    }
    container.innerHTML = transacciones.slice(0, 20).map(t => `
        <div class="tx-item">
            <span class="tx-fecha">${t.fecha}</span>
            <span class="tx-categoria">${t.categoria}</span>
            <span class="tx-valor">${formatMoney(t.valor_total)}</span>
        </div>
    `).join('');
}

function formatMoney(value) {
    if (value >= 1000000) return '$' + (value / 1000000).toFixed(1) + 'M';
    if (value >= 1000) return '$' + (value / 1000).toFixed(0) + 'K';
    return '$' + (value || 0).toFixed(0);
}

// Formulario de nueva transacción
document.getElementById('formTransaccion')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
        finca_id: currentFincaId,
        categoria: document.getElementById('tipo').value,
        fecha: document.getElementById('fecha').value,
        labor: document.getElementById('labor').value,
        producto: document.getElementById('producto').value,
        cantidad: parseFloat(document.getElementById('cantidad').value) || 0,
        unidad: document.getElementById('unidad').value,
        valor_unitario: parseFloat(document.getElementById('valorUnitario').value) || 0,
        valor_total: parseFloat(document.getElementById('valorTotal').value) || 0
    };
    try {
        await api.createTransaccion(data);
        alert('✅ Transacción guardada');
        e.target.reset();
        await loadDashboard();
    } catch (error) {
        alert('❌ Error: ' + error.message);
    }
});

// Exportar Excel
async function exportarExcel() {
    alert('📊 Exportando Excel...\n\nEsta función se conectará con el endpoint /api/export del backend.');
}

// Importar Excel
async function importarExcel(event) {
    const file = event.target.files[0];
    if (!file) return;
    alert('📥 Importando...\n\nEsta función se conectará con el endpoint /api/import del backend.');
}

// ═══════════════════════════════════════════
// PLANES Y PAGOS
// ═══════════════════════════════════════════

async function loadPlanes() {
    try {
        const data = await api.getPlanes();
        const grid = document.getElementById('planesGrid');
        grid.innerHTML = data.planes.map(plan => `
            <div class="plan-card ${plan.precio === 0 ? 'plan-free' : 'plan-premium'}">
                <h4>${plan.nombre}</h4>
                <div class="plan-precio">
                    ${plan.precio === 0 ? 'GRATIS' : '$' + plan.precio.toLocaleString() + ' COP'}
                </div>
                <ul class="plan-features">
                    ${plan.caracteristicas.map(c => `<li>✅ ${c}</li>`).join('')}
                </ul>
                <button class="btn-primary" onclick="seleccionarPlan('${plan.id}')">
                    ${plan.precio === 0 ? 'Plan actual' : 'Elegir plan'}
                </button>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error cargando planes:', error);
    }
}

function seleccionarPlan(planId) {
    alert(`Plan seleccionado: ${planId}\n\nIntegración de pagos próximamente.\nContacto: mateotabares7@gmail.com`);
}
