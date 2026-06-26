/**
 * Gráficos para Mini App (Canvas puro, sin dependencias)
 */
const charts = {
    drawBarChart(canvasId, labels, data, colors) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const width = canvas.width = canvas.parentElement.clientWidth - 32;
        const height = canvas.height = 200;
        const maxVal = Math.max(...data) || 1;
        const barWidth = (width - 40) / data.length;
        const padding = 30;

        ctx.clearRect(0, 0, width, height);

        // Líneas de fondo
        ctx.strokeStyle = '#E0E0E0';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 5; i++) {
            const y = padding + (height - 2 * padding) * i / 5;
            ctx.beginPath();
            ctx.moveTo(20, y);
            ctx.lineTo(width - 20, y);
            ctx.stroke();
        }

        // Barras
        data.forEach((val, i) => {
            const barHeight = (val / maxVal) * (height - 2 * padding);
            const x = 20 + i * barWidth + barWidth * 0.1;
            const y = height - padding - barHeight;
            const w = barWidth * 0.8;

            ctx.fillStyle = colors[i % colors.length];
            ctx.fillRect(x, y, w, barHeight);

            // Valor
            ctx.fillStyle = '#212121';
            ctx.font = '10px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(formatValue(val), x + w/2, y - 5);
        });

        // Labels
        ctx.fillStyle = '#757575';
        ctx.font = '9px sans-serif';
        labels.forEach((label, i) => {
            const x = 20 + i * barWidth + barWidth / 2;
            ctx.fillText(label, x, height - 10);
        });
    }
};

function formatValue(value) {
    if (value >= 1000000) return '$' + (value / 1000000).toFixed(1) + 'M';
    if (value >= 1000) return '$' + (value / 1000).toFixed(0) + 'K';
    return '$' + (value || 0).toFixed(0);
}
