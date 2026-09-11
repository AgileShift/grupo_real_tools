# Payment Settlement

## Propósito

`Payment Settlement` cierra cobros que ya fueron registrados en ERPNext y que permanecen temporalmente en cuentas transitorias. El documento identifica los cobros incluidos, incorpora gastos o movimientos adicionales, calcula el destino residual y genera un `Journal Entry` con trazabilidad.

El módulo no cobra facturas ni reemplaza `Payment Entry`. Su responsabilidad comienza después de capturar el dinero:

```text
Cobros registrados
    → cuentas transitorias (clearing)
    → liquidación y componentes
    → cuentas de destino (settlement)
    → Journal Entry
```

Casos objetivo del MVP:

- liquidaciones de POS y tarjetas;
- cierres de cajas;
- liquidaciones de mensajeros y delivery;
- cierres con varias cuentas y monedas;
- fondos adicionales provenientes de banco, caja u otra cuenta manual;
- redondeos, diferencias cambiarias y write-offs controlados.

## Estado actual

El flujo **Manual** está implementado y fue probado de forma interactiva, incluyendo:

- referencias en USD y NIO;
- varias cuentas transitorias dentro de un solo cierre;
- componentes aplicados a una cuenta transitoria concreta;
- destinos bancarios y no bancarios;
- override manual del monto de liquidación;
- generación, confirmación y cancelación del `Journal Entry`;
- propagación de `Bank Account` y `User Remark` al asiento;
- bloqueo de referencias previamente liquidadas;
- bloqueo de submit cuando débito y crédito no cuadran.

`Percentage` y `Fixed Amount` aparecen en los DocTypes, pero su cálculo todavía no está implementado. En el MVP deben considerarse funcionales solamente las líneas `Manual`.

Los archivos de pruebas automatizadas todavía son esqueletos vacíos. Las verificaciones actuales han sido manuales y mediante transacciones con rollback.

## Modelo de documentos

### Payment Settlement Template

Define la receta reutilizable del cierre.

Contiene:

- `company`;
- una o varias filas de `Payment Settlement Template Account`;
- cero o varias filas de `Payment Settlement Template Component`.

Cada fila de cuenta representa un mapeo 1:1:

```text
Mode of Payment
    → Clearing Account
    → Settlement Account
```

Reglas actuales:

- `Clearing Account` se deriva del `Mode of Payment` para la compañía.
- Un `Mode of Payment` no debe repetirse dentro del mismo Template.
- `Bank Account` es opcional.
- Cuando existe `Bank Account`, su cuenta contable es el `Settlement Account`.
- Sin `Bank Account`, el destino puede ser una cuenta manual: caja, cuenta por cobrar, wallet u otra cuenta transitoria.
- Un componente no debe reutilizar una cuenta estructural de clearing o settlement.
- `Apply To`, cuando se usa, apunta a una `Clearing Account` del mismo Template.

### Payment Settlement Entry

Es el cierre transaccional real. Guarda una fotografía de la configuración utilizada; no depende dinámicamente del Template después de copiarlo.

Contiene:

- compañía, Template, fecha contable y rango de búsqueda;
- tabla de cuentas estructurales;
- tabla de referencias incluidas;
- tabla de componentes contables;
- totales en moneda de la compañía;
- diferencia calculada;
- enlace al `Journal Entry` generado.

### Payment Settlement Entry Reference

Representa un evento de cobro incluido en el cierre, no simplemente una factura.

Fuentes implementadas:

1. `Payment Entry` con `payment_type = Receive`.
2. Fila de `Sales Invoice Payment` perteneciente a un `Sales Invoice` confirmado y que no sea devolución.

Los candidatos se filtran por:

- compañía;
- rango de fechas;
- `Mode of Payment`;
- cuenta transitoria;
- `docstatus = 1`.

La identidad económica de una referencia es:

```text
(reference_doctype, reference_name, reference_row_name)
```

`reference_row_name` distingue filas de pago diferentes dentro de una misma factura. Para `Payment Entry` queda vacío.

Las filas son cargadas por el backend. El usuario no puede agregarlas manualmente, pero puede eliminar del Draft las que no pertenezcan al cierre.

### Payment Settlement Entry Component

Es la representación operativa y contable que finalmente alimenta `Journal Entry Account`.

Tipos actuales:

| Type | Origen | Comportamiento |
|---|---|---|
| `Clearing` | Generado desde el Template | Acredita los cobros agrupados por `Mode of Payment`. No es editable. |
| `Settlement` | Generado desde el Template | Recibe el residual del cierre. Puede ser debitado o acreditado. |
| `Component` | Copiado del Template | Gasto, retención u otro movimiento configurado. |
| `Manual` | Agregado por el usuario | Movimiento adicional no previsto en el Template. |
| `Adjustment` | Generado por `Make Difference Entry` | Balancea una diferencia contable sin alterar el residual operativo. |

## Cálculo

### 1. Clearing

Las referencias se agrupan por `Mode of Payment`.

Por cada fila estructural se calcula:

```text
reference_count       = cantidad de referencias
clearing_amount       = suma en moneda de la cuenta
clearing_base_amount  = suma en moneda de la compañía
```

La fila `Clearing` acredita ambos importes. Su tasa de cambio es un promedio derivado de los cobros incluidos:

```text
exchange_rate = clearing_base_amount / clearing_amount
```

No se sustituye esta tasa agregada por la tasa de la fecha del Settlement, porque la fila está descargando saldos capturados anteriormente con sus propias tasas.

### 2. Componentes y Apply To

Para una línea manual:

```text
adjustment = debit_in_account_currency - credit_in_account_currency
```

- Un débito consume parte del monto disponible para el Settlement.
- Un crédito aporta fondos y aumenta lo disponible para el Settlement.

Cuando hay múltiples destinos, `Apply To` determina qué mapeo clearing → settlement recibe el efecto. El valor de `Apply To` siempre es la cuenta transitoria, no la cuenta de destino.

Si existe un solo destino, una línea sin `Apply To` puede aplicarse automáticamente a ese destino. Con varios destinos, una línea activa sin `Apply To` produce un error.

Si el componente y el destino tienen la misma moneda, el movimiento se aplica directamente en esa moneda. Si tienen monedas diferentes, se convierte desde el monto base usando la tasa de la cuenta de destino.

### 3. Settlement

Cada fila `Settlement` recibe el saldo residual correspondiente:

```text
saldo inicial de clearing
- débitos aplicados
+ créditos aplicados
= settlement residual
```

- Residual positivo → débito al `Settlement Account`.
- Residual negativo → crédito al `Settlement Account`; la cuenta de destino aportó el faltante.

Ejemplo:

```text
Clearing recibido:       C$1,000  (crédito)
Delivery y CargoTrans:   C$1,100  (débito)
Fuente manual:             C$300  (crédito)
Settlement residual:       C$200  (débito)
```

La opción `Override` permite escribir manualmente el monto final de una fila `Settlement`. Solo una fila puede hacer override de una misma cuenta de destino.

### 4. Totales y diferencia

Los totales se calculan en moneda de la compañía:

```text
total_debit  = suma de component.debit
total_credit = suma de component.credit
difference   = total_debit - total_credit
```

No se permite confirmar el Settlement mientras `difference` sea distinto de cero.

`Make Difference Entry` permite crear una fila `Adjustment` usando una de las cuentas configuradas en `Company`:

- `Round Off`;
- `Exchange Gain Or Loss`;
- `Write Off`.

El usuario debe escoger el significado real de la diferencia; no todas las diferencias son redondeo.

## Flujo operativo

1. Crear o seleccionar un `Payment Settlement Template`.
2. Configurar su compañía, cuentas estructurales y componentes.
3. Crear un `Payment Settlement Entry`.
4. Seleccionar Template, fecha contable y rango de fechas.
5. El backend copia las cuentas y componentes del Template.
6. El backend carga las referencias elegibles.
7. El usuario elimina referencias que no pertenecen al cierre.
8. El usuario introduce los importes de los componentes manuales.
9. El backend recalcula clearing, tasas, settlement, totales y diferencia.
10. Si corresponde, el usuario aplica override o crea un ajuste identificado.
11. Confirmar solamente cuando la diferencia sea cero y los movimientos coincidan con la realidad.
12. Al confirmar, se crea y confirma el `Journal Entry` y se guarda su enlace.
13. Al cancelar el Settlement, también se cancela el `Journal Entry` vinculado.

## Journal Entry generado

Solo se copian componentes con débito o crédito distinto de cero.

Por cada fila se transfieren:

- cuenta contable;
- `Bank Account`;
- tasa de cambio;
- débito y crédito en moneda de la cuenta;
- `User Remark`.

Antes de confirmar el asiento, el módulo compara los montos base recalculados por ERPNext contra los del Settlement. Si ERPNext obtiene un importe diferente por tasa o precisión, se detiene el proceso.

El `Bank Account` viaja por esta ruta:

```text
Template Account
→ Entry Account
→ Settlement Component
→ Journal Entry Account
```

Las filas no bancarias normalmente permanecen sin `Bank Account`.

## Validaciones y responsabilidades

El backend es responsable de:

- buscar referencias;
- calcular importes y tasas;
- recalcular el documento durante `validate`;
- impedir referencias duplicadas en Settlements confirmados;
- exigir diferencia cero antes de submit;
- generar y confirmar el `Journal Entry`;
- cancelar el asiento vinculado.

El JavaScript se limita a experiencia de usuario:

- filtros de campos;
- copia solicitada al backend;
- recarga de referencias al cambiar el rango;
- botón para buscar referencias;
- diálogo para crear diferencias;
- recálculo al eliminar referencias.

## Limitaciones conocidas del MVP

- Solo `Manual` tiene comportamiento de cálculo implementado.
- No existe todavía motor para `Percentage` ni `Fixed Amount`.
- No se consulta directamente `POS Invoice`.
- No se usan `Journal Entry`, transacciones bancarias ni otras fuentes como referencias.
- No hay conciliación automática contra `Bank Transaction`.
- No hay pruebas automatizadas implementadas.
- No hay workflow de aprobación adicional al submit estándar de Frappe.

## Pruebas mínimas antes de desplegar cambios

Probar siempre, preferiblemente dentro de una transacción con rollback:

1. Una moneda y un destino no bancario.
2. USD + NIO dentro del mismo Settlement.
3. Múltiples clearing accounts hacia un mismo banco.
4. Múltiples destinos con `Apply To`.
5. Gastos mayores que los cobros y Settlement residual en crédito.
6. Fuente manual en crédito que convierte el residual en débito.
7. Override de Settlement.
8. Round Off, Exchange Gain Or Loss y Write Off.
9. Referencia ya usada en otro Settlement confirmado.
10. Documento fuente cancelado antes de guardar o confirmar.
11. Submit con diferencia distinta de cero.
12. Propagación de `Bank Account` y `User Remark` al Journal Entry.
13. Cancelación del Settlement y del Journal Entry vinculado.

## Archivos principales

```text
payment_settlement/
├── README.md
├── AGENTS.md
└── doctype/
    ├── payment_settlement_template/
    │   ├── payment_settlement_template.py
    │   └── payment_settlement_template.js
    ├── payment_settlement_entry/
    │   ├── payment_settlement_entry.py
    │   └── payment_settlement_entry.js
    └── child DocTypes...
```

