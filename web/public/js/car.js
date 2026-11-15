/** Generated SVG placeholder for vehicle photos. */

const BODY_PATHS = {
  SUV: "M20 70 L32 46 Q36 40 46 40 L118 40 Q128 40 134 48 L150 62 L176 66 Q186 68 186 78 L186 86 L20 86 Z",
  Pickup: "M18 70 L30 46 Q34 40 44 40 L92 40 L100 58 L182 60 Q188 60 188 70 L188 86 L18 86 Z",
  Sedan: "M16 74 L40 56 Q48 50 60 48 L120 48 Q132 48 142 56 L164 66 L182 70 Q188 72 188 80 L188 86 L16 86 Z",
  Hatchback: "M20 74 L40 50 Q46 44 56 44 L120 44 Q130 44 136 52 L150 66 L178 70 Q186 72 186 80 L186 86 L20 86 Z",
};

const PALETTE = { white: "#e5e7eb", gray: "#9ca3af", silver: "#cbd5e1", black: "#374151", red: "#dc2626", blue: "#2563eb" };

export function carSvg(v, height = 160) {
  const fill = PALETTE[v.color] || "#94a3b8";
  const path = BODY_PATHS[v.body] || BODY_PATHS.SUV;
  return `<svg viewBox="0 0 204 110" height="${height}" role="img" aria-label="${v.brand} ${v.model}" class="w-full">
    <rect width="204" height="110" rx="10" fill="#f1f5f9"/>
    <path d="${path}" fill="${fill}" stroke="#1f2937" stroke-width="2"/>
    <circle cx="56" cy="86" r="12" fill="#1f2937"/><circle cx="56" cy="86" r="5" fill="#9ca3af"/>
    <circle cx="150" cy="86" r="12" fill="#1f2937"/><circle cx="150" cy="86" r="5" fill="#9ca3af"/>
    <text x="102" y="24" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#334155">${v.brand} ${v.model}</text>
  </svg>`;
}

/** Reference photo of the model, with the drawing as fallback when there is no photo. */
export function carPhoto(v, { eager = false } = {}) {
  const slug = `${v.brand}-${v.model}`.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-");
  const fallback = "data:image/svg+xml," + encodeURIComponent(carSvg(v).replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" '));
  const alt = `${v.brand} ${v.model}`.replace(/"/g, "");
  return `<img src="/img/cars/${slug}.jpg" alt="${alt}" width="1200" height="900" ${eager ? "" : 'loading="lazy"'}
    class="w-full aspect-[4/3] object-cover rounded-lg bg-base-200" onerror="this.onerror=null;this.src='${fallback}'">`;
}
