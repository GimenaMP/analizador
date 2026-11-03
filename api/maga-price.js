/**
 * Vercel Serverless Function: /api/maga-price
 * Scraper en tiempo real para obtener precios oficiales de granos básicos (Maíz blanco y amarillo)
 * Fuente directa oficial: https://precios.maga.gob.gt/diarios/diarios.html
 */

let cachedPrice = null;
let lastFetchTime = 0;
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutos de caché (reducido para mayor frescura)

const FALLBACK_DATA = {
  producto: "Maíz blanco, de primera",
  mercado: "La Terminal",
  medida: "Quintal",
  precio: 200.0,
  fecha: "30/10/2026",
  fuente: "MAGA Guatemala - Precios Diarios de Mercados Mayoristas (DIPLAN / SIMPA)",
  url_fuente: "https://precios.maga.gob.gt/diarios/diarios.html",
  estado: "fallback",
  hora_extraccion: new Date().toISOString(),
  variedades: [
    { producto: "Maíz blanco, de primera", mercado: "La Terminal", medida: "Quintal", precio: 200.0 },
    { producto: "Maíz blanco, de primera, otros orígenes", mercado: "La Terminal", medida: "Quintal", precio: 190.0 },
    { producto: "Maíz blanco, de segunda", mercado: "La Terminal", medida: "Quintal", precio: 185.0 },
    { producto: "Maíz amarillo, de primera", mercado: "La Terminal", medida: "Quintal", precio: 200.0 },
    { producto: "Maíz amarillo, de segunda", mercado: "La Terminal", medida: "Quintal", precio: 200.0 }
  ]
};

export async function getLiveMagaPrice(force = false) {
  const now = Date.now();
  if (!force && cachedPrice && (now - lastFetchTime < CACHE_TTL_MS)) {
    return cachedPrice;
  }

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6500);

    const response = await fetch("https://precios.maga.gob.gt/diarios/diarios.html", {
      signal: controller.signal,
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-GT,es;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache"
      }
    });
    clearTimeout(timeout);

    if (response.ok) {
      const html = await response.text();

      // 1. Extraer fecha oficial del boletín (ej. <h5>30/10/2026</h5>)
      const dateMatch = html.match(/<h5>\s*(\d{2}\/\d{2}\/\d{4})\s*<\/h5>/i);
      const fecha = dateMatch ? dateMatch[1] : new Date().toLocaleDateString('es-GT');

      // 2. Extraer todas las variedades de maíz presentes en la tabla
      const regex = /<tr>\s*<td>\s*(Ma[íi]z[^<]+)<\/td>\s*<td>\s*([^<]+)<\/td>\s*<td[^>]*>\s*([^<]+)<\/td>\s*<td[^>]*class=['"]precios['"][^>]*>\s*([\d\.]+)/gi;
      let match;
      const variedades = [];
      while ((match = regex.exec(html)) !== null) {
        variedades.push({
          producto: match[1].trim(),
          mercado: match[2].trim(),
          medida: match[3].trim(),
          precio: parseFloat(match[4])
        });
      }

      // 3. Seleccionar Maíz blanco, de primera en La Terminal
      let mainPrice = 200.0;
      const whiteFirst = variedades.find(v => 
        /blanco/i.test(v.producto) && 
        /primera/i.test(v.producto) && 
        !/otros/i.test(v.producto) && 
        /terminal/i.test(v.mercado)
      );

      if (whiteFirst) {
        mainPrice = whiteFirst.precio;
      } else if (variedades.length > 0) {
        const anyWhite = variedades.find(v => /blanco/i.test(v.producto));
        if (anyWhite) mainPrice = anyWhite.precio;
      }

      cachedPrice = {
        producto: "Maíz blanco, de primera",
        mercado: "La Terminal",
        medida: "Quintal",
        precio: mainPrice,
        fecha: fecha,
        fuente: "MAGA Guatemala - Precios Diarios de Mercados Mayoristas (DIPLAN / SIMPA)",
        url_fuente: "https://precios.maga.gob.gt/diarios/diarios.html",
        estado: "en_linea",
        hora_extraccion: new Date().toLocaleTimeString('es-GT', { hour12: false }),
        timestamp_ms: now,
        variedades: variedades
      };

      lastFetchTime = now;
      return cachedPrice;
    }
  } catch (err) {
    console.warn("[MAGA Scraper Error]", err.message);
  }

  const fallback = { ...FALLBACK_DATA };
  fallback.hora_extraccion = new Date().toLocaleTimeString('es-GT', { hour12: false });
  return fallback;
}

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,OPTIONS");
  res.setHeader("Cache-Control", "no-cache, no-store, must-revalidate");

  if (req.method === "OPTIONS") {
    res.status(200).end();
    return;
  }

  const force = req.query?.force === 'true' || req.query?.t !== undefined;
  const data = await getLiveMagaPrice(force);
  res.status(200).json(data);
}
