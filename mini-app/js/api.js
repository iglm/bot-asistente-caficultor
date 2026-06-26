/**
 * API Client completo — Mini App Asistente Caficultor ☕
 * Todos los endpoints del backend.
 */
const API_BASE = window.location.origin + '/api';

const api = {
    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const config = {
            headers: { 'Content-Type': 'application/json' },
            ...options
        };
        if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
            config.body = JSON.stringify(config.body);
        }
        try {
            const response = await fetch(url, config);
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || `Error ${response.status}`);
            }
            // Si es blob (descarga Excel)
            const ct = response.headers.get('content-type') || '';
            if (ct.includes('octet-stream') || ct.includes('spreadsheet')) {
                return response.blob();
            }
            return response.json();
        } catch (error) {
            if (error.message.includes('Failed to fetch')) {
                throw new Error('Error de conexión con el servidor');
            }
            throw error;
        }
    },

    // ─── CONFIG ───
    getConfig: () => api.request('/config'),
    healthCheck: () => api.request('/health'),

    // ─── USUARIOS ───
    getUsuario: (userId) => api.request(`/usuarios/${userId}`),
    aceptarTerminos: (userId) => api.request(`/usuarios/${userId}/aceptar-terminos`, { method: 'POST' }),
    registerUser: (userId, username) => api.request(`/auth/register?user_id=${userId}&username=${encodeURIComponent(username)}`, { method: 'POST' }),

    // ─── FINCAS ───
    getFincas: (userId) => api.request(`/fincas/user/${userId}`),
    getFinca: (fincaId) => api.request(`/fincas/${fincaId}`),
    createFinca: (data) => api.request('/fincas', { method: 'POST', body: data }),
    updateFinca: (fincaId, data) => {
        const params = new URLSearchParams(data).toString();
        return api.request(`/fincas/${fincaId}?${params}`, { method: 'PUT' });
    },
    deleteFinca: (fincaId) => api.request(`/fincas/${fincaId}`, { method: 'DELETE' }),

    // ─── LOTES ───
    getLotes: (fincaId) => api.request(`/lotes/${fincaId}`),
    getLote: (loteId) => api.request(`/lotes/detalle/${loteId}`),
    createLote: (data) => api.request('/lotes', { method: 'POST', body: data }),
    updateLote: (loteId, data) => {
        const params = new URLSearchParams(data).toString();
        return api.request(`/lotes/${loteId}?${params}`, { method: 'PUT' });
    },
    deleteLote: (loteId) => api.request(`/lotes/${loteId}`, { method: 'DELETE' }),

    // ─── TRANSACCIONES / INGRESOS ───
    getTransacciones: (fincaId, fechaInicio, fechaFin, categoria) => {
        const params = new URLSearchParams();
        if (fechaInicio) params.append('fecha_inicio', fechaInicio);
        if (fechaFin) params.append('fecha_fin', fechaFin);
        if (categoria) params.append('categoria', categoria);
        const qs = params.toString();
        return api.request(`/transacciones/${fincaId}${qs ? '?' + qs : ''}`);
    },
    createTransaccion: (data) => api.request('/transacciones', { method: 'POST', body: data }),
    deleteTransaccion: (txId) => api.request(`/transacciones/${txId}`, { method: 'DELETE' }),
    getTiposCafe: () => api.request('/ingresos/tipos'),

    // ─── COSTOS ───
    getCategoriasCostos: () => api.request('/costos/categorias'),
    getUnidadesCostos: () => api.request('/costos/unidades'),
    registrarCostoMO: (data) => api.request('/costos/mo', { method: 'POST', body: data }),
    registrarCostoInsumo: (data) => api.request('/costos/insumos', { method: 'POST', body: data }),

    // ─── RESUMEN ───
    getResumen: (fincaId) => api.request(`/resumen/${fincaId}`),
    getResumenPeriodo: (fincaId, fechaInicio, fechaFin) =>
        api.request(`/resumen/${fincaId}/periodo?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}`),
    getResumenSemanal: (fincaId, anio, semana) =>
        api.request(`/resumen/${fincaId}/semanal?anio=${anio}&semana=${semana}`),
    getResumenMensual: (fincaId, anio, mes) =>
        api.request(`/resumen/${fincaId}/mensual?anio=${anio}&mes=${mes}`),
    getResumenAnual: (fincaId, anio) =>
        api.request(`/resumen/${fincaId}/anual?anio=${anio}`),

    // ─── INDICADORES ───
    getIndicadores: (fincaId) => api.request(`/indicadores/${fincaId}`),
    getIndicadoresMO: (fincaId) => api.request(`/indicadores/${fincaId}/mo`),
    getIndicadoresInsumos: (fincaId) => api.request(`/indicadores/${fincaId}/insumos`),
    getIndicadoresFinanciero: (fincaId) => api.request(`/indicadores/${fincaId}/financiero`),
    getReferenciaFNC: () => api.request('/indicadores/referencia-fnc'),

    // ─── PRESUPUESTO ───
    getPresupuesto: (fincaId, anio) => {
        if (anio) return api.request(`/presupuesto/${fincaId}?anio=${anio}`);
        return api.request(`/presupuesto/${fincaId}`);
    },
    guardarPresupuesto: (fincaId, data) => api.request(`/presupuesto/${fincaId}`, { method: 'POST', body: data }),
    getEjecucionPresupuesto: (fincaId, anio) => api.request(`/presupuesto/${fincaId}/ejecucion/${anio}`),
    getPresupuestoSugerido: (fincaId) => api.request(`/presupuesto/${fincaId}/sugerido`),
    eliminarPresupuesto: (fincaId, anio) => api.request(`/presupuesto/${fincaId}?anio=${anio}`, { method: 'DELETE' }),

    // ─── ASESORÍA ───
    interpretarDatos: (fincaId) => api.request(`/asesoria/interpretar/${fincaId}`),
    getSugerencias: () => api.request('/asesoria/sugerencias'),
    getPlanAccion: () => api.request('/asesoria/plan'),
    getContactoAsesoria: () => api.request('/asesoria/contacto'),

    // ─── EXPORT / IMPORT ───
    exportarExcel: (fincaId) => {
        window.open(`${API_BASE}/excel/${fincaId}`, '_blank');
    },
    descargarPlantilla: () => {
        window.open(`${API_BASE}/excel/plantilla`, '_blank');
    },
    importarExcel: async (file, userId) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('user_id', userId);
        const response = await fetch(`${API_BASE}/excel/importar`, {
            method: 'POST',
            body: formData,
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'Error importando');
        }
        return response.json();
    },

    // ─── ALERTAS ───
    getAlertas: (fincaId) => api.request(`/alertas/${fincaId}`),

    // ─── ADMIN ───
    getUsuarios: () => api.request('/admin/usuarios'),
    aprobarUsuario: (userId) => api.request(`/admin/usuarios/aprobar/${userId}`, { method: 'POST' }),
    rechazarUsuario: (userId) => api.request(`/admin/usuarios/rechazar/${userId}`, { method: 'POST' }),
    revocarUsuario: (userId) => api.request(`/admin/usuarios/revocar/${userId}`, { method: 'POST' }),
    reactivarUsuario: (userId) => api.request(`/admin/usuarios/reactivar/${userId}`, { method: 'POST' }),
    borrarDatosUsuario: (userId) => api.request(`/admin/borrar-datos/${userId}`, { method: 'DELETE' }),
    getStats: () => api.request('/admin/stats'),
};
