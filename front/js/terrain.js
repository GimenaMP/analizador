/**
 * MODELADO GEOMÉTRICO DEL TERRENO EN TIEMPO REAL (RF-05)
 * Renderizado interactivo sobre HTML5 Canvas a escala proporcional con cotas y orientación Norte.
 * Estilo visual limpio y moderno (Tema Claro / Agritech Cropler).
 */

class TerrainVisualizer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    this.shapeType = 'rectangulo';
    this.sides = [100, 70, 100, 70];
    this.vertices = [[0, 0], [100, 0], [100, 70], [0, 70]];
    this.areaM2 = 7000;
    this.manzanas = 1.0;
    
    this.resizeObserver = new ResizeObserver(() => this.render());
    this.resizeObserver.observe(this.canvas.parentElement);
  }

  setDimensions(widthM, lengthM) {
    const w = Math.max(1, parseFloat(widthM) || 100);
    const l = Math.max(1, parseFloat(lengthM) || 70);
    this.shapeType = 'rectangulo';
    this.sides = [w, l, w, l];
    this.vertices = [[0, 0], [w, 0], [w, l], [0, l]];
    this.areaM2 = w * l;
    this.manzanas = this.areaM2 / 7000;
    this.render();
  }

  setPolygon(shapeType, sides, areaM2, manzanas, customVertices = null) {
    this.shapeType = shapeType || 'cuadrilatero';
    this.sides = sides || [100, 70, 100, 70];
    this.areaM2 = areaM2 || 7000;
    this.manzanas = manzanas || (this.areaM2 / 7000);

    if (customVertices && customVertices.length >= 3) {
      this.vertices = customVertices;
    } else {
      this.vertices = this._computeVertices(this.shapeType, this.sides);
    }
    this.render();
  }

  _computeVertices(shapeType, sides) {
    if (shapeType === 'triangulo') {
      const a = sides[0] || 80;
      const b = sides[1] || 75;
      const c = sides[2] || 90;
      let cosA = (a*a + b*b - c*c) / (2 * a * b);
      cosA = Math.max(-1, Math.min(1, cosA));
      const xc = b * cosA;
      const yc = b * Math.sqrt(Math.max(0, 1 - cosA * cosA));
      return [[0, 0], [a, 0], [xc, yc]];
    } else if (shapeType === 'cuadrilatero') {
      const a = sides[0] || 100;
      const b = sides[1] || 70;
      const c = sides[2] || 90;
      const d = sides[3] || 65;
      const hRight = b * 0.95;
      const hLeft = d * 0.95;
      const offsetC = Math.max(0, (a - c) / 2);
      return [[0, 0], [a, 0], [a - offsetC, hRight], [offsetC, hLeft]];
    } else {
      const w = sides[0] || 100;
      const l = sides[1] || 70;
      return [[0, 0], [w, 0], [w, l], [0, l]];
    }
  }

  render() {
    if (!this.canvas || !this.ctx) return;
    const rect = this.canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    const ctx = this.ctx;

    // Fondo limpio estilo Cropler
    ctx.fillStyle = '#F8FAFC';
    ctx.fillRect(0, 0, w, h);

    // 1. Cuadrícula sutil
    ctx.strokeStyle = '#E2E8F0';
    ctx.lineWidth = 1;
    const gridSize = 24;
    for (let x = 0; x < w; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = 0; y < h; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    if (!this.vertices || this.vertices.length < 3) return;

    // 2. Escala proporcional y centrado del polígono
    const xs = this.vertices.map(p => p[0]);
    const ys = this.vertices.map(p => p[1]);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);

    const polyW = Math.max(1, maxX - minX);
    const polyH = Math.max(1, maxY - minY);

    const margin = 50;
    const availW = w - margin * 2;
    const availH = h - margin * 2;

    const scale = Math.min(availW / polyW, availH / polyH);

    // Transformación para centrar e invertir eje Y (para coordenadas cartesianas normales)
    const scaledPoints = this.vertices.map(p => [
      margin + (availW - polyW * scale) / 2 + (p[0] - minX) * scale,
      h - margin - (availH - polyH * scale) / 2 - (p[1] - minY) * scale
    ]);

    // 3. Trazado del Polígono
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(scaledPoints[0][0], scaledPoints[0][1]);
    for (let i = 1; i < scaledPoints.length; i++) {
      ctx.lineTo(scaledPoints[i][0], scaledPoints[i][1]);
    }
    ctx.closePath();

    // Relleno verde cultivo limpio
    ctx.fillStyle = 'rgba(22, 163, 74, 0.12)';
    ctx.fill();

    // Borde verde esmeralda
    ctx.strokeStyle = '#16A34A';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // 4. Surcos esquemáticos (recortados dentro de la parcela)
    ctx.clip();
    ctx.strokeStyle = 'rgba(22, 163, 74, 0.28)';
    ctx.lineWidth = 1.2;
    ctx.setLineDash([5, 4]);

    const furrowStep = 18;
    for (let curY = 0; curY < h; curY += furrowStep) {
      ctx.beginPath();
      ctx.moveTo(0, curY);
      ctx.lineTo(w, curY);
      ctx.stroke();
    }
    ctx.restore();

    // 5. Vértices y Cotas de Medida en cada lado
    const n = scaledPoints.length;
    for (let i = 0; i < n; i++) {
      const p1 = scaledPoints[i];
      const p2 = scaledPoints[(i + 1) % n];

      // Punto de vértice
      ctx.beginPath();
      ctx.arc(p1[0], p1[1], 4.5, 0, Math.PI * 2);
      ctx.fillStyle = '#D97706';
      ctx.fill();
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Etiqueta de longitud del lado
      const mx = (p1[0] + p2[0]) / 2;
      const my = (p1[1] + p2[1]) / 2;
      const sideVal = this.sides[i] !== undefined ? this.sides[i] : Math.hypot(this.vertices[(i+1)%n][0] - this.vertices[i][0], this.vertices[(i+1)%n][1] - this.vertices[i][1]);

      ctx.font = '600 11px Inter, sans-serif';
      const labelText = `L${i+1}: ${parseFloat(sideVal).toFixed(1)}m`;
      const textWidth = ctx.measureText(labelText).width;

      // Badge blanco limpio para la cota
      ctx.fillStyle = '#FFFFFF';
      ctx.shadowColor = 'rgba(0, 0, 0, 0.08)';
      ctx.shadowBlur = 4;
      ctx.fillRect(mx - textWidth / 2 - 5, my - 9, textWidth + 10, 18);
      ctx.shadowBlur = 0;
      ctx.strokeStyle = '#CBD5E1';
      ctx.lineWidth = 1;
      ctx.strokeRect(mx - textWidth / 2 - 5, my - 9, textWidth + 10, 18);

      ctx.fillStyle = '#1E293B';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(labelText, mx, my);
    }

    // 6. Flecha Norte
    const northX = w - 36;
    const northY = 38;
    ctx.beginPath();
    ctx.moveTo(northX, northY - 14);
    ctx.lineTo(northX + 6, northY + 9);
    ctx.lineTo(northX, northY + 4);
    ctx.lineTo(northX - 6, northY + 9);
    ctx.closePath();
    ctx.fillStyle = '#DC2626';
    ctx.fill();

    ctx.font = '700 10px Inter, sans-serif';
    ctx.fillStyle = '#DC2626';
    ctx.textAlign = 'center';
    ctx.fillText('N', northX, northY - 17);

    // 7. Etiqueta central de Superficie (Badge blanco limpio con borde verde)
    const cx = scaledPoints.reduce((acc, p) => acc + p[0], 0) / n;
    const cy = scaledPoints.reduce((acc, p) => acc + p[1], 0) / n;

    ctx.fillStyle = '#FFFFFF';
    const boxW = 164;
    const boxH = 46;
    ctx.shadowColor = 'rgba(0, 0, 0, 0.08)';
    ctx.shadowBlur = 8;
    ctx.fillRect(cx - boxW / 2, cy - boxH / 2, boxW, boxH);
    ctx.shadowBlur = 0;

    ctx.strokeStyle = '#16A34A';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(cx - boxW / 2, cy - boxH / 2, boxW, boxH);

    ctx.fillStyle = '#0F172A';
    ctx.font = '700 11.5px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'alphabetic';
    ctx.fillText(this.shapeType.toUpperCase(), cx, cy - 4);

    ctx.font = '600 11.5px JetBrains Mono, monospace';
    ctx.fillStyle = '#15803D';
    ctx.fillText(`${Math.round(this.areaM2).toLocaleString()} m² • ${parseFloat(this.manzanas).toFixed(2)} mz`, cx, cy + 14);
  }
}

window.TerrainVisualizer = TerrainVisualizer;
