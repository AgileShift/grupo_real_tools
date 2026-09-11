# Payment Settlement Maintenance Guide

Estas instrucciones aplican a todo el árbol `grupo_real_tools/payment_settlement/`.

## Forma de trabajar con el propietario

- No modificar código sin autorización explícita.
- Antes de editar, explicar el problema y mostrar el cambio exacto propuesto.
- Trabajar en incrementos pequeños; no convertir un ajuste puntual en un refactor general.
- Después de una edición autorizada, mostrar el diff y verificar el comportamiento afectado.
- No tocar ni revertir cambios no relacionados del worktree.
- No usar datos reales de producción para pruebas destructivas.
- No confirmar documentos contables reales sin autorización explícita del usuario.

## Regla absoluta para DocTypes

- **Nunca editar manualmente archivos JSON de DocType.**
- Los cambios de campos, propiedades, orden, dependencias y permisos se realizan desde la UI de Frappe.
- Tampoco editar manualmente el bloque de tipos delimitado por `begin: auto-generated types` y `end: auto-generated types`.
- Después de guardar desde la UI, revisar el JSON y el bloque generado solamente para confirmar el resultado.
- El código controlador fuera del bloque generado puede editarse únicamente después de aprobación.

## Intención del módulo

Este módulo no paga facturas. Liquida eventos de cobro que ya entraron a cuentas transitorias y genera un `Journal Entry` justificable y auditable.

Leer `README.md` antes de proponer cambios. No asumir que todos los componentes son impuestos ni que una retención es recuperable. El significado contable proviene principalmente de la cuenta seleccionada.

## Invariantes que deben preservarse

1. El Template es una receta; el Entry es una fotografía transaccional.
2. Un Template puede incluir varios `Mode of Payment`, pero no debe repetir el mismo en más de una fila.
3. `Clearing Account` se deriva del `Mode of Payment` y la compañía.
4. Cada fila estructural mapea una clearing account a una settlement account.
5. `Bank Account` es opcional y solo debe propagarse a la fila `Settlement` correspondiente.
6. Las referencias representan cobros, no facturas completas.
7. La clave de duplicidad es `(reference_doctype, reference_name, reference_row_name)`.
8. `Apply To` apunta a una clearing account del Entry.
9. Clearing y Settlement son filas estructurales; no deben ser editables salvo el `Override` controlado de Settlement.
10. Los componentes manuales usan débito y crédito en moneda de la cuenta.
11. Los totales y `difference` se expresan en moneda de la compañía.
12. Submit requiere `difference == 0`.
13. El `Journal Entry` debe producir exactamente los mismos montos base que el Settlement.
14. Cancelar el Settlement debe cancelar el Journal Entry vinculado.
15. La lógica contable y las validaciones definitivas pertenecen al backend; JavaScript solo orquesta la UI.

## Semántica de tipos de componente

- `Clearing`: generado, automático, normalmente crédito.
- `Settlement`: generado, residual automático o override explícito.
- `Component`: copiado desde el Template.
- `Manual`: agregado por el usuario y aplicado al cierre.
- `Adjustment`: creado para cuadrar una diferencia ya identificada; no recalcula el residual operativo.

No cambiar los signos sin recorrer un caso contable completo. En el cálculo actual:

```text
component adjustment = debit - credit
settlement residual  -= component adjustment
```

Por tanto, un débito reduce lo disponible para el destino y un crédito lo aumenta.

## Monedas

- La clearing row usa la tasa agregada real de sus referencias: `base_amount / amount`.
- Una fila en moneda de la compañía usa tasa 1.
- Las demás filas obtienen la tasa de la fecha contable si todavía no tienen una.
- Cuando componente y destino comparten moneda, aplicar el monto directamente en esa moneda.
- Cuando difieren, convertir mediante montos base y la tasa del destino.
- No esconder diferencias cambiarias alterando silenciosamente el efectivo residual.

## Fuentes implementadas

No afirmar soporte para una fuente sin encontrar su query en el controlador.

Actualmente existen:

- `Payment Entry` de tipo `Receive`;
- `Sales Invoice Payment` enlazado a `Sales Invoice` confirmado y no devuelto.

No existe query directa para `POS Invoice`, `Journal Entry` ni `Bank Transaction`.

## Ruta de Bank Account

Debe permanecer completa:

```text
Payment Settlement Template Account.bank_account
→ Payment Settlement Entry Account.bank_account
→ Payment Settlement Entry Component.bank_account (Type = Settlement)
→ Journal Entry Account.bank_account
```

La creación server-side del Journal Entry no ejecuta el evento de cliente que normalmente deriva `Bank Account`; por eso debe enviarse explícitamente.

## Dónde realizar cambios

- Metadatos y comportamiento declarativo de campos: UI de DocType.
- Cálculos, consultas, submit y cancelación: `payment_settlement_entry.py`.
- Configuración server-side del Template: `payment_settlement_template.py`.
- Filtros, botones y llamadas de formulario: archivos `.js` correspondientes.
- Textos visibles de Python: envolver en `_()`.
- Textos visibles de JavaScript: envolver en `__()`.
- Traducciones: actualizar `.po` mediante las herramientas de traducción; no introducir mensajes duplicados si ya existe uno nativo adecuado.

## Limitaciones que no deben confundirse con bugs

- `Percentage` y `Fixed Amount` existen como opciones, pero no tienen motor de cálculo implementado.
- El alcance funcional actual es `Manual`.
- Los archivos de integration tests están vacíos.
- La conciliación bancaria automática no forma parte del MVP.

## Verificación requerida

Para cambios de Python:

- verificar sintaxis sin escribir bytecode dentro del repositorio;
- ejecutar `git diff --check`;
- probar el caso afectado con rollback cuando cree asientos;
- confirmar que ERPNext recalcula los mismos débitos y créditos base;
- verificar submit y cancelación juntos.

Para cambios de JavaScript:

- probar el evento real en Desk;
- comprobar tanto selección como limpieza del campo;
- verificar que un cambio de Template o rango no deje referencias o componentes obsoletos.

Para cambios contables o de monedas, incluir al menos:

- una cuenta en moneda de la compañía;
- una cuenta en moneda extranjera;
- un componente en la misma moneda del destino;
- un componente en moneda diferente;
- residual positivo y residual negativo;
- diferencia de precisión.

## Prioridades recomendadas

1. Agregar pruebas automatizadas para el flujo Manual ya estable.
2. Probar operativamente POS, cajas y mensajeros con cierres reales controlados.
3. Implementar `Percentage` y `Fixed Amount` solo cuando el comportamiento Manual esté estable.
4. Agregar nuevas fuentes de referencias solamente por necesidad comprobada.
5. Considerar conciliación bancaria después de estabilizar la generación de Journal Entries.
