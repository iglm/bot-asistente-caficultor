/**
 * Gráficos para Mini App — Canvas puro, sin dependencias
 * Barras, Doughnut (torta), Línea temporal
 */
const charts = {
    /**
     * Gráfico de barras
     */
    drawBarChart(canvasId, labels, data, colors, title = '') {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const width = canvas.parentElement.clientWidth - 32 || 300;
        const height = 220;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        canvas.style.width = width + 'px';
        canvas.style.height = height + 'px';
        ctx.scale(dpr, dpr);

        ctx.clearRect(0, 0, width, height);
        if (!data || data.length === 0) {
            ctx.fillStyle = '#757575';
            ctx.font = '14px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Sin datos', width / 2, height / 2);
            return;
        }

        const padding = { top: title ? 30 : 15, bottom: 30, left: 10, right: 10 };
        const chartW = width - padding.left - padding.right;
        const chartH = height - padding.top - padding.bottom;
        const maxVal = Math.max(...data) || 1;
        const barW = Math.min(chartW / data.length * 0.7, 40);
        const gap = (chartW - barW * data.length) / (data.length + 1);

        // Título
        if (title) {
            ctx.fillStyle = '#424242';
            ctx.font = 'bold 12px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(title, width / 2, 18);
        }

        // Líneas de fondo
        ctx.strokeStyle = '#E8E8E8';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = padding.top + (chartH * i) / 4;
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(width - padding.right, y);
            ctx.stroke();
        }

        // Barras
        data.forEach((val, i) => {
            const barH = (val / maxVal) * chartH;
            const x = padding.left + gap + i * (barW + gap);
            const y = height - padding.bottom - barH;

            // Sombra
            ctx.fillStyle = 'rgba(0,0,0,0.05)';
            ctx.fillRect(x + 2, y + 2, barW, barH);

            // Barra
            ctx.fillStyle = colors[i % colors.length];
            ctx.beginPath();
            ctx.roundRect(x, y, barW, barH, [4, 4, 0, 0]);
            ctx.fill();

            // Valor encima
            ctx.fillStyle = '#212121';
            ctx.font = 'bold 10px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(formatValor(val), x + barW / 2, y - 6);
        });

        // Labels
        ctx.fillStyle = '#616161';
        ctx.font = '9px sans-serif';
        ctx.textAlign = 'center';
        labels.forEach((label, i) => {
            const x = padding.left + gap + i * (barW + gap) + barW / 2;
            ctx.fillText(truncar(label, 8), x, height - 8);
        });
    },

    /**
     * Gráfico de torta (doughnut)
     */
    drawDoughnutChart(canvasId, labels, data, colors) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const size = Math.min(canvas.parentElement.clientWidth - 32, 260);
        canvas.width = size * dpr;
        canvas.height = size * dpr;
        canvas.style.width = size + 'px';
        canvas.style.height = size + 'px';
        ctx.scale(dpr, dpr);

        ctx.clearRect(0, 0, size, size);
        if (!data || data.length === 0) {
            ctx.fillStyle = '#757575';
            ctx.font = '14px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Sin datos', size / 2, size / 2);
            return;
        }

        const cx = size / 2;
        const cy = size / 2;
        const radius = size * 0.38;
        const innerRadius = radius * 0.55;
        const total = data.reduce((a, b) => a + b, 0) || 1;

        let startAngle = -Math.PI / 2;
        data.forEach((val, i) => {
            const sliceAngle = (val / total) * Math.PI * 2;
            ctx.beginPath();
            ctx.arc(cx, cy, radius, startAngle, startAngle + sliceAngle);
            ctx.arc(cx, cy, innerRadius, startAngle + sliceAngle, startAngle, true);
            ctx.closePath();
            ctx.fillStyle = colors[i % colors.length];
            ctx.fill();

            // Label en medio del arco
            if (val / total > 0.05) {
                const midAngle = startAngle + sliceAngle / 2;
                const labelR = (radius + innerRadius) / 2;
                const lx = cx + Math.cos(midAngle) * labelR;
                const ly = cy + Math.sin(midAngle) * labelR;
                ctx.fillStyle = '#fff';
                ctx.font = 'bold 10px sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(Math.round(val / total * 100) + '%', lx, ly);
            }
            startAngle += sliceAngle;
        });

        // Centro
        ctx.beginPath();
        ctx.arc(cx, cy, innerRadius * 0.85, 0, Math.PI * 2);
        ctx.fillStyle = '#fff';
        ctx.fill();
        ctx.fillStyle = '#2E7D32';
        ctx.font = 'bold 16px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(formatValor(total), cx, cy);

        // Leyenda
        const legendY = size - 30;
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        labels.slice(0, 5).forEach((label, i) => {
            const x = 10 + i * (size / 5);
            ctx.fillStyle = colors[i % colors.length];
            ctx.fillRect(x, legendY - 4, 8, 8);
            ctx.fillStyle = '#424242';
            ctx.fillText(truncar(label, 10), x + 11, legendY);
        });
    },

    /**
     * Gráfico de línea (serie temporal)
     */
    drawLineChart(canvasId, labels, datasets, colors) {
        // datasets: [{label, data: [...]}]
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const width = canvas.parentElement.clientWidth - 32 || 300;
        const height = 220;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        canvas.style.width = width + 'px';
        canvas.style.height = height + 'px';
        ctx.scale(dpr, dpr);

        ctx.clearRect(0, 0, width, height);
        if (!datasets || datasets.length === 0 || !labels || labels.length === 0) {
            ctx.fillStyle = '#757575';
            ctx.font = '14px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Sin datos', width / 2, height / 2);
            return;
        }

        const padding = { top: 20, bottom: 25, left: 10, right: 10 };
        const chartW = width - padding.left - padding.right;
        const chartH = height - padding.top - padding.bottom;

        // Encontrar max valor
        let maxVal = 1;
        datasets.forEach(ds => {
            ds.data.forEach(v => { if (v > maxVal) maxVal = v; });
        });

        const stepX = chartW / Math.max(labels.length - 1, 1);

        // Grid
        ctx.strokeStyle = '#E8E8E8';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = padding.top + (chartH * i) / 4;
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(width - padding.right, y);
            ctx.stroke();
        }

        // Dibujar líneas
        datasets.forEach((ds, dsIdx) => {
            ctx.strokeStyle = colors[dsIdx % colors.length];
            ctx.lineWidth = 2.5;
            ctx.lineJoin = 'round';
            ctx.beginPath();

            ds.data.forEach((val, i) => {
                const x = padding.left + i * stepX;
                const y = height - padding.bottom - (val / maxVal) * chartH;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            });
            ctx.stroke();

            // Puntos
            ctx.fillStyle = colors[dsIdx % colors.length];
            ds.data.forEach((val, i) => {
                const x = padding.left + i * stepX;
                const y = height - padding.bottom - (val / maxVal) * chartH;
                ctx.beginPath();
                ctx.arc(x, y, 3, 0, Math.PI * 2);
                ctx.fill();
            });
        });

        // Labels X
        ctx.fillStyle = '#616161';
        ctx.font = '8px sans-serif';
        ctx.textAlign = 'center';
        const stepLabel = Math.max(1, Math.floor(labels.length / 8));
        labels.forEach((label, i) => {
            if (i % stepLabel === 0 || i === labels.length - 1) {
                const x = padding.left + i * stepX;
                ctx.fillText(label, x, height - 6);
            }
        });

        // Leyenda arriba
        if (datasets.length > 1) {
            ctx.font = '9px sans-serif';
            ctx.textAlign = 'left';
            let lx = 10;
            datasets.forEach((ds, i) => {
                ctx.fillStyle = colors[i % colors.length];
                ctx.fillRect(lx, 6, 10, 10);
                ctx.fillStyle = '#424242';
                ctx.fillText(ds.label || '', lx + 13, 16);
                lx += ctx.measureText(ds.label || '').width + 28;
            });
        }
    },

    /**
     * Barras horizontales (para comparación con FNC)
     */
    drawHorizontalBar(canvasId, label, valor, referencia, colorValor = '#2E7D32', colorRef = '#BDBDBD') {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const width = canvas.parentElement.clientWidth - 32 || 300;
        const height = 60;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        canvas.style.width = width + 'px';
        canvas.style.height = height + 'px';
        ctx.scale(dpr, dpr);

        ctx.clearRect(0, 0, width, height);
        const maxV = Math.max(valor, referencia) * 1.3 || 1;
        const barW = (v) => (v / maxV) * (width - 60);

        // Label
        ctx.fillStyle = '#424242';
        ctx.font = 'bold 11px sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText(label || '', 10, 16);

        // Barra referencia (FNC)
        ctx.fillStyle = colorRef;
        ctx.fillRect(10, 22, barW(referencia), 12);
        ctx.fillStyle = '#757575';
        ctx.font = '8px sans-serif';
        ctx.fillText('Ref: ' + formatValor(referencia), 12, 32);

        // Barra valor
        ctx.fillStyle = colorValor;
        ctx.fillRect(10, 38, barW(valor), 12);
        ctx.fillStyle = '#212121';
        ctx.font = '8px sans-serif';
        ctx.fillText('Tú: ' + formatValor(valor), 12, 48);

        // Valor al final
        ctx.fillStyle = '#212121';
        ctx.font = 'bold 10px sans-serif';
        ctx.textAlign = 'right';
        ctx.fillText(formatValor(valor), width - 10, 46);
    }
};

// ─── Helpers ───

function formatValor(value) {
    if (!value || value === 0) return '$0';
    if (value >= 1000000) return '$' + (value / 1000000).toFixed(1) + 'M';
    if (value >= 1000) return '$' + (value / 1000).toFixed(1) + 'K';
    return '$' + Math.round(value);
}

function truncar(str, max) {
    if (!str) return '';
    return str.length > max ? str.substring(0, max) + '..' : str;
}

// Polyfill roundRect si no existe
if (!CanvasRenderingContext2D.prototype.roundRect) {
    CanvasRenderingContext2D.prototype.roundRect = function (x, y, w, h, radii) {
        const r = Array.isArray(radii) ? radii : [radii, radii, radii, radii];
        const [tl, tr, br, bl] = r.map(v => Math.min(v || 0, Math.min(w, h) / 2));
        this.moveTo(x + tl, y);
        this.lineTo(x + w - tr, y);
        this.quadraticCurveTo(x + w, y, x + w, y + tr);
        this.lineTo(x + w, y + h - br);
        this.quadraticCurveTo(x + w, y + h, x + w - br, y + h);
        this.lineTo(x + bl, y + h);
        this.quadraticCurveTo(x, y + h, x, y + h - bl);
        this.lineTo(x, y + tl);
        this.quadraticCurveTo(x, y, x + tl, y);
        this.closePath();
    };
}
