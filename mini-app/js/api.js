/**
 * API Client para Mini App
 */
const API_BASE = window.location.origin + '/api';

const api = {
    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const config = {
            headers: { 'Content-Type': 'application/json' },
            ...options
        };
        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }
        const response = await fetch(url, config);
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        return response.json();
    },

    // Endpoints
    getFincas: (userId) => api.request(`/fincas/${userId}`),
    getIndicadores: (fincaId) => api.request(`/indicadores/${fincaId}`),
    getTransacciones: (fincaId, inicio, fin) => {
        let params = '';
        if (inicio && fin) params = `?fecha_inicio=${inicio}&fecha_fin=${fin}`;
        return api.request(`/transacciones/${fincaId}${params}`);
    },
    createTransaccion: (data) => api.request('/transacciones', { method: 'POST', body: data }),
    getResumen: (fincaId) => api.request(`/resumen/${fincaId}`),
    getGastosPorRubro: (fincaId, inicio, fin) => {
        let params = '';
        if (inicio && fin) params = `?fecha_inicio=${inicio}&fecha_fin=${fin}`;
        return api.request(`/gastos-por-rubro/${fincaId}${params}`);
    },
    getPresupuesto: (fincaId) => api.request(`/presupuesto/${fincaId}`),
    // Endpoints de pagos
    getPlanes: () => api.request('/planes'),
    getConfig: () => api.request('/config')
};
