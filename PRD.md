# PRD-002: Registro de movimientos — App web para registrar ingresos/egresos clasificados por rubro y enviarlos por mail a los socios

## Contexto y Problema

Necesidad de carga de todos los movimientos de dinero de la empresa. Hoy hay 1 operador que carga estos movimientos en forma manual en un Excel desde diferentes comprobantes de papel. Se estima alrededor de 200 movimientos diarios. Hay un alto riesgo de error en la carga, ya que no está validado.

La aplicación puede tener más de un operador. Todos los usuarios autenticados ven y operan sobre el mismo conjunto de movimientos: no hay datos propios de cada usuario.

### Personas

- **Rocío:** persona que carga, modifica y marca como eliminados los movimientos. Ella quiere que la carga sea correcta y rápida.
- **José:** Socio que recibe la información por mail. Él quiere asegurarse que la información que le llega sea la correcta.

## Objetivos

Ingresar movimientos de egreso e ingreso de dinero clasificado por rubro. Poder modificarlos y marcarlos como baja. Evitar los posibles errores de carga manual en Excel.

- **Métrica de éxito:** los socios reciben el mail de movimientos el 100 % de los días hábiles.

## Requerimientos Funcionales

### Alta y validación de movimientos

- **RF-01:** El sistema debe permitir al operador dar de alta un movimiento con los campos descripción, tipo de movimiento, monto, clasificación y fecha.
- **RF-02:** El sistema debe exigir descripción, tipo de movimiento, monto y clasificación para guardar un movimiento.
- **RF-03:** El sistema debe proponer la fecha del día como valor por defecto del campo fecha.
- **RF-04:** El sistema debe ofrecer como tipo de movimiento solo Ingreso y Egreso.
- **RF-05:** El sistema debe guardar el monto con signo negativo cuando el tipo de movimiento es Egreso.
- **RF-06:** El sistema debe guardar el monto con signo positivo cuando el tipo de movimiento es Ingreso.
- **RF-07:** El sistema debe rechazar el movimiento si el monto ingresado no es un número mayor que 0 (se rechazan el 0, los negativos y los valores no numéricos), tanto en el alta como en la modificación.
- **RF-43:** Si el operador deja vacío el campo fecha, el sistema debe guardar el movimiento con la fecha del día de Argentina.
- **RF-44:** El sistema debe rechazar un movimiento cuya fecha no exista en el calendario (por ejemplo, 30/02).
- **RF-58:** El sistema debe rechazar un monto con decimales, tanto en el alta como en la modificación.
- **RF-64:** El sistema debe rechazar un monto escrito con separador de miles (por ejemplo, `1.200`); el monto se escribe solo con dígitos (`1200`).

> **Decisiones confirmadas:**
> - "La fecha del día" es la de Argentina (America/Argentina/Buenos_Aires), aunque el servidor esté en otra zona horaria (RF-03).
> - La fecha no es obligatoria: si el operador la deja vacía, se guarda la fecha del día. Una fecha inexistente (por ejemplo, 30/02) se rechaza (RF-43, RF-44).
> - El monto es un número entero, sin decimales, y no tiene monto máximo. Se escribe solo con dígitos, sin separador de miles (RF-07, RF-58, RF-64).

### Grilla, modificación y baja

- **RF-08:** El sistema debe mostrar una grilla con los movimientos no eliminados, con las columnas descripción, monto, tipo de movimiento, clasificación y fecha.
- **RF-09:** El sistema debe mostrar el formulario de alta cuando el operador presiona el botón "Agregar movimiento".
- **RF-10:** El sistema debe abrir el formulario de modificación de un movimiento cuando el operador hace doble click sobre su fila en la grilla.
- **RF-11:** El sistema debe permitir al operador marcar un movimiento como eliminado desde el formulario de modificación.
- **RF-12:** El sistema debe registrar la baja de un movimiento marcando el campo "eliminado", sin borrarlo físicamente de la base de datos.
- **RF-26:** El sistema debe guardar los cambios del formulario de modificación aplicando las mismas validaciones que en el alta.
- **RF-27:** El sistema debe permitir modificar todos los campos del movimiento, incluida la fecha.
- **RF-28:** El sistema debe pedir confirmación antes de marcar un movimiento como eliminado.
- **RF-45:** El sistema debe mostrar el monto sin signo (en positivo) en el formulario de modificación.
- **RF-46:** Cuando en la modificación el operador cambia el tipo de movimiento, el sistema debe vaciar la clasificación si no pertenece al tipo nuevo.
- **RF-47:** Cuando en la modificación el operador vuelve al tipo original, el sistema debe recuperar la clasificación guardada.
- **RF-59:** El sistema debe mostrar el monto en la grilla con punto como separador de miles, sin decimales y con signo menos en los egresos (por ejemplo, 1.200 y -1.200).
- **RF-60:** El sistema debe ordenar la grilla por fecha, de la más reciente a la más antigua.
- **RF-61:** El sistema debe mostrar la grilla en páginas de 30 movimientos.
- **RF-65:** Dentro de una misma fecha, el sistema debe ordenar la grilla del último movimiento cargado al primero.

> **Decisiones confirmadas:**
> - La grilla muestra todos los movimientos no eliminados, de cualquier fecha, ordenados por fecha descendente (y, dentro de una fecha, el último cargado arriba) y en páginas de 30 (RF-08, RF-60, RF-61, RF-65).
> - La baja se hace con el botón "Eliminar" del formulario de modificación, con confirmación; el formulario de alta no tiene ese botón (RF-11, RF-28).
> - En la modificación el monto se muestra en positivo: el signo lo define el tipo (RF-05/06, RF-45).
> - Si en la modificación el operador cambia el tipo, la clasificación queda vacía cuando no corresponde al tipo nuevo; si vuelve al tipo original, se recupera la clasificación guardada (RF-46, RF-47).

### Clasificación

- **RF-13:** El sistema debe ofrecer como clasificaciones de Ingreso solo SERVICIOS-PRESTADOS, ALQUILERES y FINANCIEROS.
- **RF-14:** El sistema debe ofrecer como clasificaciones de Egreso solo SUELDOS, IMPUESTOS-TASAS, VIATICOS, PAGO-PROVEEDORES y TURISMO.
- **RF-15:** Al crear un movimiento, el sistema debe proponer la clasificación según la palabra clave encontrada en la descripción, considerando solo las palabras clave del tipo de movimiento elegido (ver tabla y AC-01..08).
- **RF-16:** Si la descripción no coincide con ninguna palabra clave del tipo, o coincide con palabras clave de más de una clasificación, el sistema debe exigir que el operador elija la clasificación entre las del tipo.
- **RF-17:** El sistema debe rechazar un movimiento cuya clasificación no pertenezca a su tipo de movimiento, tanto en el alta como en la modificación (AC-09/10).
- **RF-42:** Al crear un movimiento, cada vez que el operador cambia la descripción, el sistema debe reemplazar la clasificación seleccionada por la que propone la descripción nueva, aunque el operador la haya elegido a mano.
- **RF-66:** Al crear un movimiento, si el operador cambia la descripción por una que no propone clasificación (RF-16), el sistema debe dejar vacía la clasificación, aunque el operador la haya elegido a mano.

Palabras clave. La comparación no distingue mayúsculas ni tildes, y la palabra clave debe estar al inicio de una palabra de la descripción.

| Tipo    | Palabra clave | Clasificación       |
|---------|---------------|---------------------|
| Egreso  | sue           | SUELDOS             |
| Egreso  | imp           | IMPUESTOS-TASAS     |
| Egreso  | via           | VIATICOS            |
| Egreso  | prov          | PAGO-PROVEEDORES    |
| Egreso  | tur           | TURISMO             |
| Ingreso | serv          | SERVICIOS-PRESTADOS |
| Ingreso | alq           | ALQUILERES          |
| Ingreso | fin           | FINANCIEROS         |

> **Decisiones confirmadas:**
> - Las palabras clave se comparan sin distinguir mayúsculas ni tildes y deben estar al inicio de una palabra; así "Factura" no coincide con "tur" (RF-15).
> - Si la descripción coincide con palabras clave de más de una clasificación, elige el operador. Si la misma palabra clave aparece varias veces, cuenta como una sola clasificación (RF-16).
> - La clasificación se propone solo al crear; al modificar, el operador la cambia a mano (RF-15).
> - La clasificación propuesta es un valor inicial: el operador puede cambiarla por otra del mismo tipo antes de guardar (RF-15).
> - Si el operador elige una clasificación a mano y después reescribe la descripción, la propuesta nueva reemplaza su elección (RF-42).
> - Si la descripción nueva no propone clasificación, la elegida a mano se borra y el operador tiene que volver a elegir (RF-66).

### Usuarios y acceso

- **RF-18:** El sistema debe guardar la sigla, el nombre y el mail de cada operador.
- **RF-41:** El sistema debe dar de alta a cada operador sin contraseña; la contraseña la define el propio operador en su primer ingreso (RF-19).
- **RF-29:** El sistema debe rechazar el alta de un operador cuya sigla ya exista, sin distinguir mayúsculas de minúsculas.
- **RF-30:** El sistema debe permitir dar de alta operadores por consola, con `python -m app.operadores alta SIGLA "Nombre" mail`.
- **RF-19:** Cuando un operador que todavía no tiene contraseña ingresa su sigla, el sistema debe pedirle que defina su contraseña.
- **RF-31:** El sistema debe exigir que la contraseña tenga al menos 8 caracteres.
- **RF-48:** El sistema debe aceptar contraseñas de hasta 72 bytes.
- **RF-62:** El sistema debe rechazar una contraseña de más de 72 bytes, mostrando un mensaje de error.
- **RF-69:** Al definir su contraseña en el primer ingreso, el sistema debe pedir que el operador la escriba dos veces y rechazarla si no coinciden.
- **RF-20:** El sistema debe permitir el ingreso solo cuando la sigla y la contraseña coinciden con las de la tabla de usuarios.
- **RF-33:** Cuando la sigla ingresada no existe, el sistema debe informar "No existe un operador con la sigla …" sin pedir contraseña.
- **RF-21:** El sistema debe impedir el acceso a cualquier pantalla o acción, salvo el login, a quien no haya iniciado sesión.
- **RF-22:** El sistema debe mostrar a todos los usuarios autenticados el mismo conjunto de movimientos.
- **RF-32:** El sistema debe permitir al operador cerrar su sesión con el botón "Cerrar sesión".
- **RF-34:** Cuando la sesión vence por inactividad, el sistema debe avisarlo en la pantalla de login.
- **RF-57:** El sistema debe negarse a arrancar si `SECRET_KEY` no está definida en `.env`.

> **Decisiones confirmadas:**
> - "Primer ingreso" significa un operador dado de alta que todavía no tiene contraseña (RF-19).
> - La contraseña se define una sola vez desde el login: no se puede redefinir la de un operador que ya tiene una (RF-19).
> - Los operadores se dan de alta solo por consola; no hay pantalla de administración (RF-30, FA-04).
> - La sigla se guarda en mayúsculas y el login no distingue mayúsculas ("ro" es "RO") (RF-29).
> - La contraseña admite hasta 72 bytes, el límite que usa bcrypt; una más larga se rechaza con un mensaje (RF-48, RF-62).
> - La contraseña se escribe dos veces al definirla: como no se puede recuperar (FA-07), un error de tipeo dejaría al operador afuera para siempre (RF-69).

### Mail a los socios

- **RF-23:** El sistema debe rechazar el alta de un socio que no tenga mail.
- **RF-24:** El sistema debe enviar todos los días a las 17:00 (hora de Argentina, America/Argentina/Buenos_Aires) un mail a todos los socios con los movimientos no eliminados cuya fecha es la del día.
- **RF-25:** El mail debe incluir, para cada movimiento, descripción, monto, tipo de movimiento, clasificación y fecha.
- **RF-35:** El sistema debe permitir dar de alta socios por consola, con `python -m app.socios alta "Nombre" mail`.
- **RF-36:** El sistema debe mandar un mail separado a cada socio, con su dirección como único destinatario.
- **RF-37:** Si no hay movimientos en la fecha del mail, el sistema debe mandar igual el mail, informando "No hubo movimientos".
- **RF-38:** Si la aplicación arranca desde las 17:00 y antes de las 18:00 y el mail del día no se mandó, el sistema debe mandarlo al arrancar.
- **RF-39:** El sistema no debe mandar más de una vez el mail automático de un mismo día.
- **RF-40:** El sistema debe permitir mandar el mail de un día a mano, con `python -m app.mail enviar [--fecha AAAA-MM-DD]`.
- **RF-49:** El sistema debe rechazar el alta de un socio cuyo mail ya exista, sin distinguir mayúsculas de minúsculas.
- **RF-50:** El sistema debe poner como asunto del mail "Movimientos del DD/MM/AAAA", con la fecha del mail: la del día en el envío automático o la indicada con `--fecha` en el manual (RF-40).
- **RF-51:** El sistema debe informar en el mail la cantidad de movimientos de la fecha del mail.
- **RF-52:** Si la aplicación arranca a las 18:00 o después y el mail del día no se mandó, el sistema no debe mandarlo.
- **RF-53:** En el caso de RF-52, el sistema debe dejar en el log un aviso con el comando para mandar ese mail a mano.
- **RF-54:** El sistema no debe registrar como enviado el día de un envío manual (RF-40).
- **RF-55:** El sistema debe registrar en el log cada error de envío (servidor caído, dirección rechazada, configuración incompleta).
- **RF-56:** El sistema no debe reintentar automáticamente un envío que falló.
- **RF-63:** El sistema debe mostrar el monto en el mail con punto como separador de miles, sin decimales y con signo menos en los egresos (por ejemplo, 1.200 y -1.200).
- **RF-67:** El sistema debe enviar el mail en texto plano, sin HTML.
- **RF-68:** El sistema debe mostrar en el mail una línea por movimiento.

> **Decisiones confirmadas:**
> - El mail se envía todos los días, incluidos fines de semana, en hora de Argentina, e incluye solo movimientos no eliminados con fecha del día (RF-24).
> - Los socios no son usuarios del sistema: no tienen login, solo reciben el mail (RF-23).
> - Los socios se dan de alta solo por consola; no hay pantalla de administración (RF-35, FA-05). No se admiten dos socios con el mismo mail, sin distinguir mayúsculas (RF-49).
> - Un mail por socio: nadie ve las direcciones de los demás, y si una dirección falla, los demás lo reciben igual (RF-36).
> - El mail es texto plano: asunto "Movimientos del DD/MM/AAAA", la cantidad de movimientos y una línea por movimiento, con el monto en el mismo formato que la grilla (RF-25, RF-50, RF-51, RF-63, RF-67, RF-68).
> - Si la aplicación arranca a las 18:00 o después sin haber mandado el mail del día, no lo manda: lo deja registrado en el log con el comando para mandarlo a mano (RF-52, RF-53).
> - Cada día enviado queda registrado en la base antes de mandar; así, ni un reinicio ni una segunda copia de la aplicación lo repiten (RF-39). El envío manual no se registra: siempre manda (RF-54).
> - Los errores de envío (servidor caído, dirección rechazada, configuración incompleta) quedan en el log de la aplicación. No hay reintento automático: el día queda registrado y se reenvía a mano (RF-40, RF-55, RF-56).
> - La conexión SMTP se configura en `.env` (servidor, puerto, usuario, contraseña, remitente y seguridad `starttls`, `ssl` o `ninguna`) (RNF-04).

## Requerimientos No Funcionales

- **RNF-01:** La clasificación propuesta debe mostrarse en menos de 2 s (p95), medido desde que se envía la descripción hasta que se muestra la clasificación en el formulario.
- **RNF-02:** Las contraseñas de los usuarios deben guardarse solo como hash bcrypt (costo ≥ 12), nunca en texto plano.
- **RNF-03:** La sesión debe expirar luego de 60 minutos de inactividad.
- **RNF-04:** El código y el repositorio deben tener 0 credenciales (contraseñas, API keys, credenciales SMTP, clave de sesión `SECRET_KEY`); van en `.env`, fuera del repositorio.

> **Decisiones confirmadas:**
> - El costo de bcrypt es ≥ 12 (RNF-02).
> - Sin `SECRET_KEY` en `.env` la aplicación no arranca (RNF-04, RF-57).
> - Cada acción del operador, incluidas las que hace el formulario sin recargar la página, renueva el plazo de 60 minutos. A los 60 minutos justos la sesión ya está vencida (RNF-03).

## Criterios de Aceptación

### Clasificación por palabra clave

- **AC-01 (RF-15):** Dado un movimiento nuevo de tipo Egreso, cuando la descripción es "Sueldo marzo", entonces el sistema propone SUELDOS.
- **AC-02 (RF-15):** Dado un movimiento nuevo de tipo Egreso, cuando la descripción es "Impuesto municipal", entonces el sistema propone IMPUESTOS-TASAS.
- **AC-03 (RF-15):** Dado un movimiento nuevo de tipo Egreso, cuando la descripción es "Viáticos Córdoba", entonces el sistema propone VIATICOS.
- **AC-04 (RF-15):** Dado un movimiento nuevo de tipo Egreso, cuando la descripción es "Proveedor de resmas", entonces el sistema propone PAGO-PROVEEDORES.
- **AC-05 (RF-15):** Dado un movimiento nuevo de tipo Egreso, cuando la descripción es "Turismo Bariloche", entonces el sistema propone TURISMO.
- **AC-06 (RF-15):** Dado un movimiento nuevo de tipo Ingreso, cuando la descripción es "Servicio de consultoría", entonces el sistema propone SERVICIOS-PRESTADOS.
- **AC-07 (RF-15):** Dado un movimiento nuevo de tipo Ingreso, cuando la descripción es "Alquiler local", entonces el sistema propone ALQUILERES.
- **AC-08 (RF-15):** Dado un movimiento nuevo de tipo Ingreso, cuando la descripción es "Financiación cliente", entonces el sistema propone FINANCIEROS.

### Clasificación válida para el tipo

- **AC-09 (RF-17):** Dado un movimiento de tipo Egreso, cuando se envía al servidor para guardarlo con clasificación ALQUILERES, entonces el sistema rechaza el guardado y muestra un error en el campo clasificación.
- **AC-10 (RF-17):** Dado un movimiento de tipo Ingreso, cuando se envía al servidor para guardarlo con clasificación SUELDOS, entonces el sistema rechaza el guardado y muestra un error en el campo clasificación.

### Grilla

- **AC-11 (RF-08):** Dado un movimiento guardado sin errores, cuando se muestra la grilla, entonces el movimiento aparece con su descripción, monto, tipo de movimiento, clasificación y fecha.
- **AC-99 (RF-08):** Dados un movimiento no eliminado con fecha de hoy y otro con fecha 01/01/2026, cuando se muestra la grilla, entonces aparecen los dos.
- **AC-83 (RF-59):** Dado un movimiento de tipo Ingreso con monto 1200, cuando se muestra la grilla, entonces su monto aparece como `1.200`.
- **AC-89 (RF-59):** Dado un movimiento de tipo Egreso con monto 1200, cuando se muestra la grilla, entonces su monto aparece como `-1.200`.
- **AC-84 (RF-60):** Dados tres movimientos con fechas 10/10/2026, 12/10/2026 y 11/10/2026, cuando se muestra la grilla, entonces aparecen en el orden 12/10/2026, 11/10/2026, 10/10/2026.
- **AC-85 (RF-61):** Dados 31 movimientos no eliminados, cuando se muestra la grilla, entonces la primera página tiene 30 movimientos y la segunda tiene 1.
- **AC-91 (RF-65):** Dados dos movimientos con fecha 21/10/2026, cargados primero "Alquiler local" y después "Sueldo marzo", cuando se muestra la grilla, entonces "Sueldo marzo" aparece arriba de "Alquiler local".

### Casos límite de la clasificación

- **AC-12 (RF-16):** Dado un movimiento nuevo de tipo Egreso, cuando la descripción es "Compra de café", entonces el sistema no propone clasificación y no permite guardar hasta que el operador elija una de las 5 clasificaciones de Egreso.
- **AC-13 (RF-16):** Dado un movimiento nuevo de tipo Egreso, cuando la descripción es "Impuesto sobre sueldos", entonces el sistema no propone clasificación y no permite guardar hasta que el operador elija una de las 5 clasificaciones de Egreso.
- **AC-14 (RF-15):** Dado un movimiento nuevo de tipo Egreso, cuando la descripción es "VIATICO cordoba", entonces el sistema propone VIATICOS.
- **AC-15 (RF-15):** Dado un movimiento nuevo de tipo Egreso, cuando la descripción es "Factura de luz", entonces el sistema no propone ninguna clasificación y no permite guardar hasta que el operador elija una de las 5 clasificaciones de Egreso.
- **AC-16 (RF-15):** Dado un movimiento nuevo de tipo Egreso, cuando la descripción es "Alquiler oficina", entonces el sistema no propone ninguna clasificación y no permite guardar hasta que el operador elija una de las 5 clasificaciones de Egreso.
- **AC-17 (RF-13):** Dado el formulario de alta con tipo Ingreso, cuando el operador abre el selector de clasificación, entonces ve exactamente SERVICIOS-PRESTADOS, ALQUILERES y FINANCIEROS.
- **AC-18 (RF-14):** Dado el formulario de alta con tipo Egreso, cuando el operador abre el selector de clasificación, entonces ve exactamente SUELDOS, IMPUESTOS-TASAS, VIATICOS, PAGO-PROVEEDORES y TURISMO.
- **AC-81 (RF-16):** Dado un movimiento nuevo de tipo Egreso, cuando la descripción es "Sueldo marzo y sueldo abril", entonces el sistema propone SUELDOS.
- **AC-67 (RF-42):** Dado un movimiento nuevo de tipo Egreso con descripción "Compra de café" y clasificación VIATICOS elegida a mano, cuando el operador cambia la descripción a "Sueldo marzo", entonces la clasificación seleccionada pasa a ser SUELDOS.
- **AC-92 (RF-66):** Dado un movimiento nuevo de tipo Egreso con descripción "Sueldo marzo" y clasificación VIATICOS elegida a mano, cuando el operador cambia la descripción a "Compra de café", entonces el campo clasificación queda vacío y el sistema no permite guardar hasta que el operador elija una.

### Alta y validación

- **AC-68 (RF-01):** Dado el formulario de alta, cuando el operador carga descripción "Sueldo marzo", tipo Egreso, monto 1000, clasificación SUELDOS y fecha 20/10/2026 y guarda, entonces el movimiento queda registrado con descripción "Sueldo marzo", tipo Egreso, monto -1000, clasificación SUELDOS y fecha 20/10/2026.
- **AC-19 (RF-02):** Dado el formulario de alta, para cada uno de los cuatro campos descripción, tipo, monto y clasificación, cuando el operador intenta guardar con ese campo vacío y los demás válidos, entonces el sistema rechaza el guardado y marca ese campo.
- **AC-20 (RF-03):** Dado que el operador abre el formulario de alta, cuando se muestra, entonces el campo fecha tiene la fecha del día.
- **AC-97 (RF-03):** Dado el servidor en UTC, cuando el operador abre el formulario de alta a las 22:30 del 20/10/2026 de Argentina (01:30 del 21/10/2026 en UTC), entonces el campo fecha muestra 20/10/2026.
- **AC-21 (RF-04):** Dado el formulario de alta, cuando el operador abre el selector de tipo, entonces ve exactamente Ingreso y Egreso.
- **AC-22 (RF-05):** Dado un movimiento de tipo Egreso con monto 500, cuando se guarda, entonces queda registrado con monto -500.
- **AC-23 (RF-06):** Dado un movimiento de tipo Ingreso con monto 500, cuando se guarda, entonces queda registrado con monto 500.
- **AC-24 (RF-07):** Dado el formulario de alta, cuando el monto es `0`, entonces el sistema rechaza el guardado y muestra un error en el campo monto.
- **AC-25 (RF-07):** Dado el formulario de alta, cuando el monto es `-500`, entonces el sistema rechaza el guardado y muestra un error en el campo monto.
- **AC-26 (RF-07):** Dado el formulario de alta, cuando el monto es `12abc`, entonces el sistema rechaza el guardado y muestra un error en el campo monto.
- **AC-46 (RF-43):** Dado el formulario de alta con datos válidos, cuando el operador borra la fecha y guarda, entonces el movimiento queda registrado con la fecha del día de Argentina.
- **AC-47 (RF-44):** Dado el formulario de alta, cuando la fecha es 30/02/2026 y el operador guarda, entonces el sistema rechaza el guardado y muestra un error en el campo fecha.
- **AC-82 (RF-58):** Dado el formulario de alta, cuando el monto es `12,5`, entonces el sistema rechaza el guardado y muestra un error en el campo monto.
- **AC-88 (RF-64):** Dado el formulario de alta, cuando el monto es `1.200`, entonces el sistema rechaza el guardado y muestra un error en el campo monto.

### Modificación y baja

- **AC-27 (RF-09):** Dada la grilla, cuando el operador presiona "Agregar movimiento", entonces se muestra el formulario de alta vacío, con la fecha del día.
- **AC-28 (RF-10):** Dado un movimiento en la grilla, cuando el operador hace doble click sobre su fila, entonces se abre el formulario de modificación con los datos de ese movimiento.
- **AC-29 (RF-26):** Dado el formulario de modificación de un movimiento, cuando el operador cambia la descripción y guarda, entonces la grilla muestra la descripción nueva.
- **AC-48 (RF-27):** Dado el formulario de modificación de un movimiento con fecha 17/10/2026, cuando el operador cambia la fecha a 10/10/2026 y guarda, entonces la grilla muestra el movimiento con fecha 10/10/2026.
- **AC-93 (RF-27):** Dado un movimiento de tipo Egreso con monto 500 y clasificación SUELDOS en modificación, cuando el operador cambia el tipo a Ingreso, elige ALQUILERES y guarda, entonces queda registrado con tipo Ingreso, clasificación ALQUILERES y monto 500.
- **AC-94 (RF-27):** Dado un movimiento de tipo Egreso con monto 500 en modificación, cuando el operador cambia el monto a 800 y guarda, entonces queda registrado con monto -800.
- **AC-30 (RF-17):** Dado un movimiento existente de tipo Egreso con clasificación SUELDOS, cuando se envía al servidor su modificación con tipo Ingreso y clasificación SUELDOS, entonces el sistema rechaza el guardado y muestra un error en el campo clasificación.
- **AC-31 (RF-07):** Dado el formulario de modificación de un movimiento, cuando el operador cambia el monto a `0` y guarda, entonces el sistema rechaza el guardado y muestra un error en el campo monto.
- **AC-100 (RF-58):** Dado el formulario de modificación de un movimiento, cuando el operador cambia el monto a `12,5` y guarda, entonces el sistema rechaza el guardado y muestra un error en el campo monto.
- **AC-32 (RF-11, RF-28):** Dado el formulario de modificación de un movimiento, cuando el operador presiona "Eliminar" y confirma, entonces el movimiento deja de aparecer en la grilla.
- **AC-49 (RF-28):** Dado el formulario de modificación de un movimiento, cuando el operador presiona "Eliminar" y cancela la confirmación, entonces el movimiento sigue en la grilla sin cambios.
- **AC-33 (RF-12):** Dado un movimiento marcado como eliminado, cuando se consulta la base de datos, entonces el registro sigue existiendo con el campo eliminado en verdadero.
- **AC-69 (RF-45):** Dado un movimiento de tipo Egreso guardado con monto -500, cuando el operador abre su formulario de modificación, entonces el campo monto muestra 500.
- **AC-70 (RF-46):** Dado un movimiento de tipo Egreso con clasificación SUELDOS en modificación, cuando el operador cambia el tipo a Ingreso, entonces el campo clasificación queda vacío.
- **AC-71 (RF-47):** Dado un movimiento de tipo Egreso con clasificación SUELDOS en modificación, cuando el operador cambia el tipo a Ingreso y después vuelve a Egreso, entonces el campo clasificación muestra SUELDOS.

### Usuarios y acceso

- **AC-34 (RF-29):** Dado un operador existente con sigla "RO", cuando se intenta registrar otro operador con sigla "RO", entonces el sistema rechaza el registro.
- **AC-50 (RF-29):** Dado un operador existente con sigla "RO", cuando se intenta registrar otro operador con sigla "ro", entonces el sistema rechaza el registro.
- **AC-51 (RF-30, RF-41):** Dada la consola, cuando se ejecuta `python -m app.operadores alta JP "Juan" juan@empresa.com`, entonces el operador JP queda creado sin contraseña.
- **AC-96 (RF-18):** Dada la consola, cuando se ejecuta `python -m app.operadores alta JP "Juan" juan@empresa.com`, entonces la tabla de usuarios tiene un operador con sigla JP, nombre Juan y mail juan@empresa.com.
- **AC-35 (RF-19):** Dado un operador sin contraseña, cuando ingresa su sigla en el login, entonces el sistema le pide definir su contraseña antes de dejarlo entrar.
- **AC-52 (RF-19):** Dado un operador con contraseña definida, cuando se intenta definirle una contraseña nueva desde el login, entonces el sistema lo rechaza y la contraseña guardada no cambia.
- **AC-53 (RF-31):** Dado un operador sin contraseña, cuando define una contraseña de 7 caracteres, entonces el sistema la rechaza y no lo deja entrar.
- **AC-98 (RF-31):** Dado un operador sin contraseña, cuando define una contraseña de 8 caracteres, entonces el sistema la acepta y lo deja entrar.
- **AC-72 (RF-48):** Dado un operador sin contraseña, cuando define una contraseña de 72 caracteres sin tildes (72 bytes), entonces el sistema la acepta y, al ingresar después con esa contraseña, accede a la grilla.
- **AC-86 (RF-62):** Dado un operador sin contraseña, cuando define una contraseña de 73 caracteres sin tildes (73 bytes), entonces el sistema la rechaza, muestra un mensaje de error y no lo deja entrar.
- **AC-103 (RF-69):** Dado un operador sin contraseña, cuando escribe "secreta123" y la repite como "secreta124", entonces el sistema la rechaza, muestra "Las contraseñas no coinciden" y no lo deja entrar.
- **AC-54 (RF-33):** Dado que no existe el operador "XX", cuando se ingresa la sigla "XX" en el login, entonces el sistema muestra "No existe un operador con la sigla XX" y no pide contraseña.
- **AC-36 (RF-20):** Dado un operador con contraseña definida, cuando ingresa su sigla y su contraseña correcta, entonces accede a la grilla.
- **AC-37 (RF-20):** Dado un operador con contraseña definida, cuando ingresa su sigla y una contraseña incorrecta, entonces el sistema rechaza el acceso y no muestra movimientos.
- **AC-38 (RF-21):** Dado un visitante sin sesión, cuando accede a la URL de la grilla o de cualquier acción de alta, modificación o baja, entonces el sistema lo redirige al login y no muestra movimientos.
- **AC-39 (RF-22):** Dado un movimiento cargado por el operador A, cuando el operador B inicia sesión, entonces ve ese movimiento en la grilla.
- **AC-40 (RNF-03):** Dada una sesión sin actividad durante 60 minutos, cuando el usuario realiza una acción, entonces el sistema lo redirige al login.
- **AC-55 (RNF-03):** Dada una sesión sin actividad durante 59 minutos, cuando el usuario realiza una acción, entonces el sistema la ejecuta sin pedir login.
- **AC-56 (RF-34):** Dada una sesión vencida por inactividad, cuando el usuario realiza una acción, entonces la pantalla de login muestra "Tu sesión venció por inactividad".
- **AC-73 (RF-57):** Dado un `.env` sin `SECRET_KEY`, cuando se intenta arrancar la aplicación, entonces la aplicación no arranca y no atiende pedidos.
- **AC-57 (RF-32):** Dado un operador con sesión iniciada, cuando presiona "Cerrar sesión", entonces el sistema lo lleva al login y, al volver a la URL de la grilla, lo redirige al login.

> **Control de acceso:** no hay un AC de "un usuario no ve los datos de otro" porque todos los operadores comparten el mismo conjunto de movimientos (RF-22, AC-39). El control de acceso se verifica con AC-38 (visitante sin sesión), AC-40 (sesión vencida) y AC-57 (sesión cerrada).

### Mail a los socios

- **AC-41 (RF-23):** Dado un socio sin mail, cuando se intenta dar de alta por consola, entonces el sistema rechaza el alta.
- **AC-42 (RF-24):** Dados un movimiento de hoy no eliminado, un movimiento de hoy eliminado y un movimiento de ayer, cuando son las 17:00, entonces cada socio recibe un mail que contiene solo el movimiento de hoy no eliminado.
- **AC-43 (RF-25):** Dado el mail de las 17:00, cuando un socio lo abre, entonces cada movimiento muestra descripción, monto, tipo de movimiento, clasificación y fecha.
- **AC-58 (RF-35):** Dada la consola, cuando se ejecuta `python -m app.socios alta "José" jose@empresa.com`, entonces el socio queda creado.
- **AC-59 (RF-49):** Dado un socio con mail jose@empresa.com, cuando se intenta dar de alta otro socio con JOSE@empresa.com, entonces el sistema rechaza el alta.
- **AC-60 (RF-36):** Dados dos socios, cuando son las 17:00, entonces se mandan dos mails y cada uno tiene como destinatario solo a su socio.
- **AC-61 (RF-36):** Dados dos socios y la dirección del primero rechazada por el servidor de correo, cuando son las 17:00, entonces el segundo socio recibe el mail y el rechazo queda en el log.
- **AC-62 (RF-37):** Dado un día sin movimientos, cuando son las 17:00, entonces cada socio recibe un mail que dice "No hubo movimientos" con la fecha del día.
- **AC-63 (RF-38):** Dado que la aplicación estuvo apagada a las 17:00 y el mail del día no se mandó, cuando arranca a las 17:30, entonces manda el mail.
- **AC-64 (RF-52):** Dado que la aplicación estuvo apagada a las 17:00 y el mail del día no se mandó, cuando arranca a las 18:00, entonces no manda el mail y deja un aviso en el log.
- **AC-65 (RF-39):** Dado que el mail del día ya se mandó a las 17:00, cuando la aplicación se reinicia a las 17:30, entonces no se manda de nuevo.
- **AC-66 (RF-40):** Dada la consola, cuando se ejecuta `python -m app.mail enviar --fecha 2026-10-10`, entonces cada socio recibe el mail con asunto "Movimientos del 10/10/2026" y los movimientos de ese día.
- **AC-74 (RF-50):** Dado el 21/10/2026, cuando se manda el mail de las 17:00, entonces su asunto es "Movimientos del 21/10/2026".
- **AC-75 (RF-51):** Dados 3 movimientos no eliminados con fecha de hoy, cuando se manda el mail de las 17:00, entonces el mail informa que hubo 3 movimientos.
- **AC-87 (RF-63):** Dado un movimiento de hoy de tipo Ingreso con monto 1200, cuando se manda el mail de las 17:00, entonces su monto aparece como `1.200`.
- **AC-90 (RF-63):** Dado un movimiento de hoy de tipo Egreso con monto 1200, cuando se manda el mail de las 17:00, entonces su monto aparece como `-1.200`.
- **AC-101 (RF-67):** Dado el mail de las 17:00, cuando se inspecciona su contenido, entonces tiene una sola parte de tipo `text/plain` y ninguna parte HTML.
- **AC-102 (RF-68):** Dados 3 movimientos no eliminados con fecha de hoy, cuando se manda el mail de las 17:00, entonces el cuerpo tiene exactamente 3 líneas de movimiento, una por cada uno.
- **AC-76 (RF-53):** Dado que la aplicación estuvo apagada a las 17:00 del 21/10/2026 y el mail no se mandó, cuando arranca a las 18:00, entonces el log contiene el comando `python -m app.mail enviar --fecha 2026-10-21`.
- **AC-77 (RF-54):** Dado que el mail de hoy no se mandó, cuando a las 16:00 se ejecuta `python -m app.mail enviar`, entonces a las 17:00 el sistema manda igual el mail automático.
- **AC-78 (RF-55):** Dado el servidor de correo caído, cuando son las 17:00, entonces el error de conexión queda en el log.
- **AC-79 (RF-56):** Dado que el envío de las 17:00 falló por el servidor de correo caído, cuando la aplicación sigue corriendo hasta las 18:00 y también cuando se reinicia a las 17:30, entonces en ninguno de los dos casos vuelve a intentar el envío de ese día.

### Rendimiento

- **AC-80 (RNF-01):** Dadas 100 descripciones distintas cargadas en el formulario de alta, cuando se mide el tiempo desde que se envía cada descripción hasta que se muestra la clasificación, entonces al menos 95 se muestran en menos de 2 s.

### Seguridad

- **AC-44 (RNF-02):** Dado un operador con contraseña definida, cuando se consulta la tabla de usuarios, entonces la contraseña está guardada como hash bcrypt y no en texto plano.
- **AC-95 (RNF-02):** Dado un operador con contraseña definida, cuando se lee su hash en la tabla de usuarios, entonces el costo de bcrypt indicado en el hash es 12 o mayor (por ejemplo, empieza con `$2b$12$`).
- **AC-45 (RNF-04):** Dado el repositorio, cuando se busca en el código y en los archivos versionados, entonces no hay contraseñas, API keys ni credenciales SMTP, y `.env` no está versionado.

## Fuera de Alcance

- **FA-01:** Los movimientos no emiten comprobantes.
- **FA-02:** La aplicación no se conecta a bancos.
- **FA-03:** La aplicación no se conecta a billeteras virtuales.
- **FA-04:** No hay pantalla de administración de operadores: el alta es solo por consola (RF-30).
- **FA-05:** No hay pantalla de administración de socios: el alta es solo por consola (RF-35).
- **FA-06:** El sistema no valida el formato del mail de operadores y socios ni el formato de la sigla (largo o caracteres permitidos).
- **FA-07:** No se puede cambiar ni recuperar una contraseña olvidada.
- **FA-08:** No se pueden dar de baja ni modificar operadores ni socios.
- **FA-09:** No se puede restaurar un movimiento eliminado.
- **FA-10:** No se guarda historial de quién creó, modificó o eliminó cada movimiento.
- **FA-11:** La grilla no tiene búsqueda, filtros ni exportación.
- **FA-12:** No se manejan varias monedas.
- **FA-13:** No hay roles ni permisos distintos entre operadores: todos pueden hacer lo mismo.

## Riesgos y Dependencias

- **Riesgo:** Clasificación inconsistente de los movimientos → Se permite volver a clasificar modificando el movimiento (RF-10, RF-17).
- **Riesgo:** Quien conozca la sigla de un operador recién dado de alta puede definir su contraseña antes que él (RF-19) → Cada operador debe ingresar apenas se lo da de alta.
- **Dependencia:** SQLite.
- **Dependencia:** Servidor SMTP para el envío del mail de las 17:00 (RF-24). Con Gmail hace falta una contraseña de aplicación, que exige tener activada la verificación en dos pasos.
- **Riesgo:** Si el envío de las 17:00 falla (servidor de correo caído, credenciales vencidas), los socios no reciben el mail de ese día hasta que alguien lo reenvíe a mano (RF-40) → Revisar el log de la aplicación.
- **Riesgo:** El mail sale de la aplicación mientras está corriendo; si está apagada entre las 17:00 y las 18:00, el mail de ese día no sale solo (RF-38) → Al arrancar, el log avisa con el comando para mandarlo a mano (RF-53, RF-40).
- **Riesgo:** Un operador que olvida su contraseña no puede volver a entrar (FA-07, FA-08) → Riesgo aceptado, sin mitigación.
- **Riesgo:** El mensaje "No existe un operador con la sigla …" permite averiguar qué siglas existen (RF-33) → Aceptado: es una decisión confirmada.
- **Riesgo:** La grilla acumula unos 200 movimientos por día, unos 50.000 por año (RF-08) → Se pagina de a 30 (RF-61). Sin búsqueda ni filtros (FA-11), encontrar un movimiento viejo exige recorrer páginas.
