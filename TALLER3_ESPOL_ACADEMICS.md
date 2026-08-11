# Taller 3 — ESPOL Academics v2 (SOFG1006)

Aplicación del taller *"Django – VideoClub ESPOL"* al proyecto **ESPOL Academics**,
un sistema de gestión académica (facultades, cursos, contenidos y evaluaciones).

---

## 1. Aplicaciones Django (una APP = un módulo, no una tabla)

| Aplicación Django | Modelos que contiene |
|---|---|
| `accounts` | `Usuario` |
| `cursos` | `Facultad`, `Curso`, `FormulaComponente`, `Inscripcion`, `Modulo`, `Material`, `ProgresoModulo` |
| `evaluaciones` | `Tarea`, `Entrega`, `Quiz`, `Pregunta`, `RespuestaQuiz` |

Cada `apps.py` está configurado con `default_auto_field`, `name` y `verbose_name`.

---

## 2. Convenciones aplicadas en `models.py`

- Toda clave primaria es `models.BigAutoField(primary_key=True)` con nombre
  explícito (`id_usuario`, `id_curso`, `id_tarea`, …).
- `db_column` en **todos** los campos, para conservar los nombres físicos.
- `db_table`, `verbose_name`, `verbose_name_plural` y `ordering` en cada `Meta`.
- Todas las claves foráneas usan `on_delete=models.PROTECT` y `related_name`
  descriptivo.
- Los campos con valores limitados usan clases internas `models.TextChoices`.
- Campos opcionales con `null=True, blank=True`.
- Campos monetarios / de puntaje con `models.DecimalField(max_digits=10, decimal_places=2)`.
- Fechas con `DateField`, fechas y horas con `DateTimeField`.
- Método `__str__()` en todos los modelos.
- Restricciones estructurales con `models.UniqueConstraint` y `models.CheckConstraint`.
- Sin señales (`signals`) y sin `managed = False`: Django administra todas las tablas.

### Tablas físicas creadas

`usuario`, `facultad`, `curso`, `formula_componente`, `inscripcion`, `modulo`,
`material`, `progreso_modulo`, `tarea`, `entrega`, `quiz`, `pregunta`,
`respuesta_quiz`.

El script DDL completo para MySQL está en **`modelo_er_mysql.sql`**
(generado con `python manage.py sqlmigrate <app> 0001`).

---

## 3. Explicación breve de cada modelo

### App `accounts`

- **Usuario** — Persona registrada en el sistema. Es el modelo de autenticación
  (`AUTH_USER_MODEL`) y el acceso se hace con el **correo**. Guarda los datos
  personales exigidos (nombres, apellidos, identificación, teléfono, celular,
  correo, dirección, estado civil, estado, fecha de registro), la facultad a la
  que pertenece y el rol del sistema (`SUPERADMIN`, `ADMIN`, `USER`).

### App `cursos`

- **Facultad** — Unidad académica de ESPOL. Tiene código y nombre únicos y,
  opcionalmente, un usuario administrador responsable.
- **Curso** — Materia dictada dentro de una facultad por un profesor, con fechas
  de inicio y fin y estado (activo / archivado).
- **FormulaComponente** — Cada componente porcentual de la calificación de un
  curso (Tareas 40 %, Quizzes 30 %, …).
- **Inscripcion** — Vínculo entre un usuario y un curso, indicando si participa
  como `PROFESOR` o como `ESTUDIANTE`.
- **Modulo** — Unidad de contenido del curso, con un orden dentro del mismo.
- **Material** — Recurso de estudio de un módulo (video, PDF o enlace externo).
- **ProgresoModulo** — Avance de un estudiante sobre un módulo concreto.

### App `evaluaciones`

- **Tarea** — Trabajo asignado en un curso, con criterios, fecha límite y
  puntaje máximo.
- **Entrega** — Envío de un estudiante para una tarea, con su estado, contenido,
  nota y comentario del profesor.
- **Quiz** — Evaluación en línea de un curso, con tiempo y fecha límite.
- **Pregunta** — Pregunta de un quiz. Soporta 15 tipos distintos; las opciones y
  la respuesta correcta se guardan en `JSONField`. La propiedad
  `es_auto_corregible` indica si el sistema puede calificarla automáticamente.
- **RespuestaQuiz** — Intento resuelto por un estudiante, con la nota automática
  y la nota manual asignada por el profesor.

---

## 4. Relaciones implementadas

| Origen | Destino | Cardinalidad | `related_name` |
|---|---|---|---|
| `Usuario.facultad` | `Facultad` | 0..1 → N | `usuarios` |
| `Facultad.admin` | `Usuario` | 0..1 → N | `facultades_administradas` |
| `Curso.facultad` | `Facultad` | 1 → N | `cursos` |
| `Curso.profesor` | `Usuario` | 1 → N | `cursos_como_profesor` |
| `FormulaComponente.curso` | `Curso` | 1 → N | `formula` |
| `Inscripcion.usuario` | `Usuario` | 1 → N | `inscripciones` |
| `Inscripcion.curso` | `Curso` | 1 → N | `inscripciones` |
| `Modulo.curso` | `Curso` | 1 → N | `modulos` |
| `Material.modulo` | `Modulo` | 1 → N | `materiales` |
| `ProgresoModulo.usuario` | `Usuario` | 1 → N | `progresos` |
| `ProgresoModulo.modulo` | `Modulo` | 1 → N | `progresos` |
| `Tarea.curso` | `Curso` | 1 → N | `tareas` |
| `Entrega.tarea` | `Tarea` | 1 → N | `entregas` |
| `Entrega.usuario` | `Usuario` | 1 → N | `entregas` |
| `Quiz.curso` | `Curso` | 1 → N | `quizzes` |
| `Pregunta.quiz` | `Quiz` | 1 → N | `preguntas` |
| `RespuestaQuiz.quiz` | `Quiz` | 1 → N | `respuestas` |
| `RespuestaQuiz.usuario` | `Usuario` | 1 → N | `respuestas_quiz` |

Todas con `on_delete=models.PROTECT`: un registro referenciado no puede
borrarse, y la interfaz muestra un mensaje explicando el motivo.

### Restricciones declaradas

| Tipo | Restricción |
|---|---|
| `UniqueConstraint` | `formula_componente(curso, componente)` |
| `UniqueConstraint` | `inscripcion(usuario, curso)` |
| `UniqueConstraint` | `modulo(curso, orden)` |
| `UniqueConstraint` | `progreso_modulo(usuario, modulo)` |
| `UniqueConstraint` | `tarea(curso, titulo)`, `quiz(curso, titulo)` |
| `UniqueConstraint` | `entrega(tarea, usuario)`, `respuesta_quiz(quiz, usuario)` |
| `CheckConstraint` | `curso.fecha_fin >= curso.fecha_inicio` |
| `CheckConstraint` | `formula_componente.porcentaje` entre 1 y 100 |
| `CheckConstraint` | `modulo.orden >= 1` |
| `CheckConstraint` | Puntajes y notas nunca negativos (tarea, entrega, pregunta, respuesta_quiz) |

---

## 5. Estructura de archivos por aplicación

```
<app>/
├── apps.py            AppConfig con verbose_name
├── models.py          modelos del módulo
├── admin.py           registro extendido (list_display, search_fields, list_filter, ordering)
├── forms.py           un ModelForm por modelo (labels, widgets, error_messages, clean_*)
├── views.py           CRUD con ListView / DetailView / CreateView / UpdateView / DeleteView
├── urls.py            rutas del módulo con app_name
└── templates/<app>/   <modelo>_list / _form / _detail / _confirm_delete .html
```

El `base.html` común está en `backend/templates/base.html` y la página de
inicio del panel en `backend/templates/panel_inicio.html`. Los estilos propios
del panel viven en `css/panel.css` y reutilizan los tokens de `css/main.css`,
por lo que el panel hereda el **modo oscuro** y la identidad visual del resto
de la aplicación.

### Tablas adaptables y modo oscuro

Cada listado se renderiza dos veces: como `.mobile-cards` (tarjetas) y como
`.table-container` (tabla). El CSS de `components.css` muestra las tarjetas y
oculta la tabla por debajo de 768 px, de modo que en el teléfono cada registro
se lee como una tarjeta con su título, sus etiquetas y sus acciones.

El botón de la barra superior alterna entre claro y oscuro, guarda la elección
en `localStorage["tema"]` — la misma clave que usa el frontend — y, si el
usuario no ha elegido nada, sigue la preferencia del sistema operativo.

Las vistas CRUD comparten dos mixins declarados en cada `views.py`:

- `MensajeFormularioMixin` — muestra un mensaje al registrar o actualizar.
- `EliminacionProtegidaMixin` — captura `ProtectedError` al eliminar y muestra
  un mensaje en lugar de un error del servidor.

Todas las vistas del panel exigen sesión iniciada (`LoginRequiredMixin`); el
login es el del administrador de Django (`/admin/login/`).

---

## 6. Inventario de rutas del panel CRUD

```
/panel/                              Panel académico (resumen por módulo)

/accounts/usuarios/                  /accounts/usuarios/nuevo/
/accounts/usuarios/1/                /accounts/usuarios/1/editar/       /accounts/usuarios/1/eliminar/

/cursos/facultades/                  /cursos/facultades/nuevo/          /cursos/facultades/1/…
/cursos/cursos/                      /cursos/cursos/nuevo/              /cursos/cursos/1/…
/cursos/formula/                     /cursos/formula/nuevo/             /cursos/formula/1/…
/cursos/inscripciones/               /cursos/inscripciones/nuevo/       /cursos/inscripciones/1/…
/cursos/modulos/                     /cursos/modulos/nuevo/             /cursos/modulos/1/…
/cursos/materiales/                  /cursos/materiales/nuevo/          /cursos/materiales/1/…
/cursos/progresos/                   /cursos/progresos/nuevo/           /cursos/progresos/1/…

/evaluaciones/tareas/                /evaluaciones/tareas/nuevo/        /evaluaciones/tareas/1/…
/evaluaciones/entregas/              /evaluaciones/entregas/nuevo/      /evaluaciones/entregas/1/…
/evaluaciones/quizzes/               /evaluaciones/quizzes/nuevo/       /evaluaciones/quizzes/1/…
/evaluaciones/preguntas/             /evaluaciones/preguntas/nuevo/     /evaluaciones/preguntas/1/…
/evaluaciones/respuestas/            /evaluaciones/respuestas/nuevo/    /evaluaciones/respuestas/1/…
```

Cada bloque `…` incluye `/1/` (detalle), `/1/editar/` y `/1/eliminar/`.

---

## 7. Comandos de verificación (orden del taller)

```bash
cd backend
source venv/bin/activate

python manage.py check                                   # 0 errores
python manage.py makemigrations accounts cursos evaluaciones
python manage.py sqlmigrate cursos 0001                  # revisión del SQL (opcional)
python manage.py migrate                                 # crea las tablas
python manage.py showmigrations accounts cursos evaluaciones
python manage.py createsuperuser
python manage.py seed                                    # datos de prueba
python manage.py runserver
```

Luego revisar `http://127.0.0.1:8000/panel/` y `http://127.0.0.1:8000/admin/`.

---

## 8. Despliegue

El paso a paso para publicarlo en AlwaysData está en
**[`GUIA_DESPLIEGUE_ALWAYSDATA.md`](GUIA_DESPLIEGUE_ALWAYSDATA.md)**.
