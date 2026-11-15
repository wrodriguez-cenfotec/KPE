/** Spanish labels for the codes stored in the database. */

const LABELS = {
  vehicleStatus: { available: "Disponible", reserved: "Reservado", sold: "Vendido" },
  quoteStatus: { open: "Abierta", expired: "Vencida", sold: "Vendida" },
  reservationStatus: { pending: "Pendiente", confirmed: "Confirmada", cancelled: "Cancelada" },
  actionStatus: { running: "En proceso", ok: "Completada", error: "Error" },
  fuel: { gasoline: "Gasolina", diesel: "Diésel", hybrid: "Híbrido" },
  transmission: { automatic: "Automático", manual: "Manual" },
  body: { SUV: "SUV", Pickup: "Pickup", Sedan: "Sedán", Hatchback: "Hatchback" },
  color: { white: "Blanco", gray: "Gris", silver: "Plateado", black: "Negro", red: "Rojo", blue: "Azul" },
  inspection: { excellent: "Excelente estado", acceptable: "Estado aceptable", needs_repairs: "Necesita reparaciones" },
  role: { visitor: "Visitante", customer: "Cliente", staff: "Personal" },
  origin: { web_chat: "Chat del sitio", mcp: "MCP", staff: "Gestión", web: "Sitio web" },
  auditEvent: {
    staff_login: "Inicio de sesión",
    reservations_viewed: "Consulta de reservas",
    inventory_viewed: "Consulta de inventario",
    reservation_confirmed: "Reserva confirmada",
  },
};

/** Returns the Spanish label for a code, or the code itself when there is no label. */
export function label(group, code) {
  return LABELS[group]?.[code] ?? code ?? "";
}
