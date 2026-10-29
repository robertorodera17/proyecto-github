---
name: convencional-skill
description: Arma el mensaje de commit en formato Conventional Commits a partir de lo que está en stage. Se ejecuta cuando se hace un commit o el usuario pide commitear.
---

# Convencional skill

Escribís mensajes de commit en formato Conventional Commits, basados SOLO en lo
que está en stage.

## Paso 1 — Ver qué cambió

Corré `git diff --staged` (y `git diff --staged --stat` para el panorama).
- Si no hay nada en stage, avisale al usuario y pará: NO hagas `git add` por tu cuenta.
- Lo que no está en stage no entra en el mensaje.

## Paso 2 — Elegir el tipo

Elegí UNO de estos tipos según el cambio principal:

| Tipo       | Cuándo                                                         |
|------------|----------------------------------------------------------------|
| `feat`     | Funcionalidad nueva para el usuario                            |
| `fix`      | Corrección de un error                                         |
| `docs`     | Solo documentación (PRD, README, AGENTS.md, skills)            |
| `refactor` | Cambio de código que no agrega funcionalidad ni corrige errores |
| `test`     | Agregar o corregir tests                                       |
| `chore`    | Mantenimiento: dependencias, configuración, archivos auxiliares |

Si el diff mezcla cambios de tipos distintos, sugerile al usuario partirlo en
varios commits antes de seguir.

## Paso 3 — Armar el mensaje

```
tipo(alcance): resumen

Cuerpo opcional: qué cambió y por qué.
```

- `alcance` es opcional: el módulo o área tocada (por ejemplo `prd`, `mail`, `operadores`).
- El resumen va en castellano, en minúscula, en infinitivo, sin punto final y con
  la primera línea de 72 caracteres como máximo.
- El cuerpo explica el porqué, no repite el diff.

Ejemplos:
- `docs(prd): endurecer PRD2 con el skill create-prd`
- `fix(mail): no reenviar el mail diario al reiniciar la app`
- `test(operadores): cubrir sigla repetida en minúsculas`

## Paso 4 — Confirmar y commitear

Mostrale el mensaje al usuario y esperá su OK antes de commitear. Con el OK,
corré `git commit` con ese mensaje. Nunca hagas push.
