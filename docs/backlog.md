# Modulo Actividades diarias

Estas son actividades que se requieren realizar todos los dias para garantizar una estabilidad en al modelo de negocio:

La idea es que puede ser una simple table que guarde las actividades a realizarse antes que el sistema sea ‘desbloqueado’ para su uso, estas actividades pueden ser realizadas por cualquiera de los trabajadores

Algo asi que esto aparezca al principio del dia, como actividades necesarias a realizarse antes de poder entrar al sistema.

| Modelo Daily Activity | Modelo DailyActivityHistory |
|-----------------------|-----------------------------|
| PK                    | Pk                          |
| Name: String          | Name: string                |
| Recurrence: Datetime  | Last completed: datetime    |
|                       | Completed by: PK User       |

## Ejemplos

- Apertura del dia:
  - Actualizar la tasa de cambio del dia(BCN)
  - Apertura de Caja y cuentas de Banco
  - Anotar gastos del dia anterior y guardar papeleria
  - Compras del dia anterior
  - Actualizar WR de IMG al sistema
  - Revision de paquetes para reportar del dia anterior
- Cierre del dia
  - Cierre de caja y cuentas de banco
  - Anotar gastos del dia y guardar papeleria
  - Compras del dia

---

# Modulo de reembolsos:

* Para con el cliente
* Para con el proveedor

---

# Modulo de Fuerza Laboral

* Llevar control sobre el horario de entrada y salida
  * Necesidad de comprar un lector de huella? 
* Llevar control sobre los dias ausentes
* Obtener toda la informacion que modifica los salarios base!
* Calculo automatico de Planilla con Frappe HR

---

# Flujo de Reporte Administrativo(Muy posible fuera del sistema)

* Facturas Pendientes
* Ordenes de Importacion Pendientes de Pago
* Cierres de Caja
* Charts - Por Verse
* Notificaciones transactionales via Telegram o Whatsapp:
  * Definir eventos que que activaran las notificaciones
