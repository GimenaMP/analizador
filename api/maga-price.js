/**
 * Vercel Serverless Function: /api/maga-price
 * Scraper en tiempo real para obtener el precio oficial de Maíz blanco, de primera en La Terminal.
 * Fuente: https://precios.maga.gob.gt/diarios/diarios.html
 */

let cachedPrice = null;
let lastFetchTime = 0;
const CACHE_TTL_MS = 10 * 60 * 1000; // 10 minutos de caché

const FALLBACK_DATA = {
  producto: "Maíz blanco, de primera",
  mercado: "La Terminal",
  medida: "Quintal",
  precio: 235.0,
  fecha: "09/10/2026",
  fuente: "MAGA Guatemala - Precios Diarios de Mercados Mayoristas",
  estado: "fallback"
};

export async function getLiveMagaPrice() {
  const now = Date.now();
  if (cachedPrice && now - lastFetchTime < CACHE_TTL_MS) {
    return cachedPrice;
  }

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4500);

    const response = await fetch("https://precios.maga.gob.gt/diarios/diarios.html", {
      signal: controller.signal,
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
      }
    });
    clearTimeout(timeout);

    if (response.ok) {
      const html = await response.text();

      // Extraer fecha (<h5>09/10/2026</h5>)
      const dateMatch = html.match(/<h5>\s*(\d{2}\/\d{2}\/\d{4})\s*<\/h5>/i);
      const fecha = dateMatch ? dateMatch[1] : "09/10/2026";

      // Extraer precio de Maíz blanco, de primera
      const priceMatch = html.match(/<td>\s*Maíz blanco, de primera\s*<\/td>\s*<td>\s*La Terminal\s*<\/td>\s*<td[^>]*>\s*Quintal\s*<\/td>\s*<td[^>]*class=['"]precios['"][^>]*>\s*([\d\.]+)/i);

      if (priceMatch) {
        const precio = parseFloat(priceMatch[1]);
        cachedPrice = {
          producto: "Maíz blanco, de primera",
          mercado: "La Terminal",
          medida: "Quintal",
          precio: precio,
          fecha: fecha,
          fuente: "MAGA Guatemala - Precios Diarios de Mercados Mayoristas",
          estado: "en_linea"
        };
        lastFetchTime = now;
        return cachedPrice;
      }
    }
  } catch (err) {
    console.warn("[MAGA Scraper Error]", err.message);
  }

  return FALLBACK_DATA;
}

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,OPTIONS");
  res.setHeader("Cache-Control", "public, s-maxage=600, stale-while-revalidate=1200");

  if (req.method === "OPTIONS") {
    res.status(200).end();
    return;
  }

  const data = await getLiveMagaPrice();
  res.status(200).json(data);
}
