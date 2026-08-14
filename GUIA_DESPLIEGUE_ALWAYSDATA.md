# Guía paso a paso: subir ESPOL Academics a AlwaysData

Esta guía usa **solamente AlwaysData** (panel web + SSH). No hace falta GitHub,
Docker ni ningún otro servicio externo.

Al terminar tendrás funcionando en `https://jostin.alwaysdata.net`:

| Ruta | Qué es |
|---|---|
| `/` | Aplicación web para estudiantes, profesores y administradores |
| `/panel/` | Panel CRUD del Taller 3 (vistas genéricas de Django) |
| `/accounts/usuarios/` | CRUD de usuarios |
| `/cursos/…` | CRUD de facultades, cursos, fórmula, inscripciones, módulos, materiales, progreso |
| `/evaluaciones/…` | CRUD de tareas, entregas, quizzes, preguntas, respuestas |
| `/api/` | **API pública de consulta externa (JSON)** — ver *Paso 8 bis* |
| `/api/auth/…` | Login de otras aplicaciones: token de super administrador |
| `/admin/` | Panel de administración de Django |

> **Esta guía ya está personalizada** para la cuenta `jostin`
> (`https://jostin.alwaysdata.net`). Las contraseñas y la clave secreta **no**
> aparecen aquí a propósito: van solo en el archivo `.env` del servidor, que
> nunca se sube al repositorio.

---

## Paso 0. Crear la cuenta

1. Entra a `https://www.alwaysdata.com/` y crea una cuenta **gratuita (100 MB)**.
2. Durante el registro te pide un **nombre de cuenta**: ese es tu `jostin` y
   también tu dominio `jostin.alwaysdata.net`.
3. Confirma el correo e inicia sesión en `https://admin.alwaysdata.com/`.

---

## Paso 0 bis. Dónde ver tus datos de SSH

El acceso SSH **ya viene activado** al crear la cuenta, también en el plan
gratuito. Tus datos:

| Dato | Valor |
|---|---|
| Host SSH / SFTP | `ssh-jostin.alwaysdata.net` |
| Usuario | `jostin` |
| Sitio web | `jostin.alwaysdata.net` |
| Host MySQL | `mysql-jostin.alwaysdata.net` |
| WebDAV | `https://webdav-jostin.alwaysdata.net/` |
| Consola SSH por navegador | `https://ssh-jostin.alwaysdata.net` |

La contraseña del usuario SSH se define en **Entorno → Usuarios**
(*Environment → Users*); puede ser distinta de la del panel. El host exacto está
también en **Acceso remoto → SSH**.

**Comprueba antes de subir nada:**

```bash
ssh jostin@ssh-jostin.alwaysdata.net
```

> Si falla, no sigas al Paso 3: ve directamente al **Apéndice** del final.

---

## Paso 1. Crear la base de datos MySQL

1. En el panel izquierdo entra a **Bases de datos → MySQL**.
2. Pestaña **Usuarios** → botón **Añadir un usuario**:
   - Nombre: `jostin` (o `jostin_django`)
   - Contraseña: la que definas — **anótala**
   - Permisos: marca acceso completo
3. Pestaña **Bases de datos** → **Añadir una base de datos**:
   - Nombre: `jostin_espolacademics`
   - Juego de caracteres: `utf8mb4` (o `UTF-8 Unicode`)
   - Usuario asociado: el que acabas de crear, con permisos completos
4. Anota estos cuatro datos, los usarás en el Paso 5:

```
DB_NAME     = jostin_espolacademics
DB_USER     = jostin
DB_PASSWORD = la-contrasena-que-pusiste
DB_HOST     = mysql-jostin.alwaysdata.net
```

> El host exacto aparece en la misma pantalla del panel; cópialo de ahí.

---

## Paso 2. Preparar los archivos en tu computadora

Desde tu proyecto local (`/home/josmocobos/EspolAcademicsManagev2`), genera una
clave secreta nueva para producción:

```bash
cd /home/josmocobos/EspolAcademicsManagev2/backend
source venv/bin/activate
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copia el resultado (una cadena larga) — la usarás en el Paso 5.

**Qué se sube y qué NO se sube:**

| Se sube | NO se sube |
|---|---|
| `backend/` (código, sin `venv`) | `backend/venv/` |
| `css/`, `js/`, `pages/`, `index.html` | `__pycache__/`, `*.pyc` |
| `backend/requirements*.txt` | `backend/db.sqlite3` (usarás MySQL) |
| | `backend/staticfiles/` (se regenera en el servidor) |
| | `.git/` |

---

## Vía rápida: el script automático

Los Pasos 3 a 6 están automatizados en `desplegar.sh`. En el servidor (SSH o la
consola web `https://ssh-jostin.alwaysdata.net`), pega estas dos líneas:

```bash
curl -fsSL https://raw.githubusercontent.com/Jostin798M/EspolAcademicsManagev2/main/desplegar.sh -o ~/desplegar.sh
bash ~/desplegar.sh
```

El script hace, en este orden: `git clone` en `~/www` → entorno virtual →
dependencias → genera la clave secreta de Django **y la clave de la API** y te
**pide la contraseña de MySQL** para escribir el `.env` → `migrate` → datos de
prueba → comprueba que la API responde → te pide crear el **superusuario**. Al
terminar imprime los valores exactos para el Paso 7 **y la clave de la API** que
necesitarás para consultarla desde fuera (*Paso 8 bis*).

Se puede volver a ejecutar cuantas veces quieras: si algo ya existe, lo
reutiliza en vez de duplicarlo. **No** configura el sitio en el panel: los Pasos
7 y 8 los haces tú.

> El resto de esta guía explica lo mismo paso a paso, por si prefieres hacerlo a
> mano o necesitas entender qué falló.

---

## Paso 3. Subir el proyecto

Tienes tres formas. **Elige una.**

### Opción A — Desde la terminal (recomendada, más rápida)

Desde WSL/Linux/macOS, en la carpeta que **contiene** el proyecto:

```bash
cd /home/josmocobos

rsync -avz --progress \
  --exclude 'venv/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.git/' \
  --exclude 'staticfiles/' \
  --exclude 'db.sqlite3' \
  --exclude '*.bak-*' \
  EspolAcademicsManagev2 \
  jostin@ssh-jostin.alwaysdata.net:~/www/
```

Te pedirá la contraseña del usuario SSH (Paso 0 bis).

> **`Network is unreachable`** (típico en WSL2): tu máquina no tiene IPv6 y `ssh`
> intenta salir por ahí. Fuerza IPv4 una sola vez:
>
> ```bash
> mkdir -p ~/.ssh && chmod 700 ~/.ssh
> printf 'Host *.alwaysdata.net\n    AddressFamily inet\n' >> ~/.ssh/config
> chmod 600 ~/.ssh/config
> ```
>
> O añade `-e "ssh -4"` al `rsync`.

> **`Connection refused` en el puerto 22:** tu red bloquea el SSH saliente.
> Usa la **Opción C** de abajo y el **Apéndice** del final.

> Si `rsync` no está disponible, usa `scp -r` con las mismas exclusiones hechas
> a mano, o la Opción B.

### Opción C — Con git (la que funciona aunque tu red bloquee el puerto 22)

`git` viaja por HTTPS (puerto 443), así que no le afecta el bloqueo del 22. Es
además la forma más cómoda de actualizar después.

En tu computadora, una sola vez:

```bash
cd /home/josmocobos/EspolAcademicsManagev2
git init && git branch -M main
git remote add origin https://github.com/TU-USUARIO/TU-REPO.git
git add -A && git commit -m "Proyecto Taller 4"
git push -u origin main
```

En el servidor (por SSH, o en `https://ssh-jostin.alwaysdata.net` si el 22 está
bloqueado):

```bash
mkdir -p ~/www && cd ~/www
git clone https://github.com/TU-USUARIO/TU-REPO.git EspolAcademicsManagev2
```

> Si el repositorio es **privado**, el `git clone` pedirá usuario y un *personal
> access token* de GitHub (no tu contraseña). Si es público, no pide nada.

### Opción B — Con un cliente SFTP (FileZilla, WinSCP)

- Servidor: `ssh-jostin.alwaysdata.net`
- Protocolo: **SFTP**, puerto **22**
- Usuario: `jostin` — Contraseña: la de tu cuenta
- Sube la carpeta `EspolAcademicsManagev2` dentro de `/home/jostin/www/`
- **Excluye** `venv/`, `__pycache__/`, `.git/`, `staticfiles/`, `db.sqlite3`

Al final la ruta en el servidor debe ser:

```
/home/jostin/www/EspolAcademicsManagev2/backend/manage.py
```

---

## Paso 4. Conectarte por SSH y crear el entorno virtual

```bash
ssh jostin@ssh-jostin.alwaysdata.net
```

Ya dentro del servidor, mira qué versiones de Python hay disponibles:

```bash
ls /usr/alwaysdata/python/
```

Este proyecto usa **Django 6.0, que necesita Python 3.12 o superior**.

> ⚠️ **Apunta la versión que elijas aquí.** En el Paso 7 tendrás que poner
> *exactamente la misma* en el campo **Version de Python** del sitio. uWSGI
> arranca con el intérprete del panel y busca los paquetes en
> `~/venv-espol/lib/pythonX.Y/`: si el venv es `3.14` y el sitio es `3.13`, no
> encuentra nada y el log dice `ModuleNotFoundError: No module named 'django'`.
> **No elijas la más nueva por costumbre**; elige una que el panel ofrezca.

Créate el entorno (esta guía usa `3.13`):

```bash
cd ~/www/EspolAcademicsManagev2/backend

/usr/alwaysdata/python/3.13/bin/python3 -m venv ~/venv-espol
source ~/venv-espol/bin/activate

python --version          # debe decir 3.12.x o superior
pip install --upgrade pip
pip install --no-cache-dir -r requirements-produccion.txt
```

> `--no-cache-dir` evita que `~/.cache/pip` se coma la cuota de 100 MB.

> **Si `mysqlclient` falla al instalarse**, no es problema: instala solo lo demás
> y usa el driver alternativo en Python puro.
>
> ```bash
> pip install -r requirements.txt
> pip install PyMySQL==1.1.2
> ```
> Luego, en el Paso 5, agrega la línea `DB_DRIVER=pymysql` al archivo `.env`.
> El proyecto ya está preparado para funcionar con cualquiera de los dos drivers.

> **Si el servidor solo ofrece Python 3.11 o menor**, edita `requirements.txt`
> y cambia `Django==6.0.6` por `Django==5.2.11` antes de instalar. El código es
> compatible con ambas versiones.

---

## Paso 5. Crear el archivo de configuración `.env`

Sigue en la sesión SSH, dentro de `~/www/EspolAcademicsManagev2/backend`:

```bash
nano .env
```

Pega esto y **completa las dos líneas marcadas** con tus valores reales:

```
DJANGO_SECRET_KEY=<la clave larga que generaste en el Paso 2>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=jostin.alwaysdata.net
DJANGO_CSRF_TRUSTED_ORIGINS=https://jostin.alwaysdata.net
DJANGO_CORS_ALLOWED_ORIGINS=https://jostin.alwaysdata.net

DB_ENGINE=mysql
DB_NAME=jostin_espolacademics
DB_USER=jostin
DB_PASSWORD=<la contraseña de MySQL del Paso 1>
DB_HOST=mysql-jostin.alwaysdata.net
DB_PORT=3306

# Activar cuando el dominio ya responda por HTTPS
DJANGO_SECURE_SSL_REDIRECT=False

# API de consulta (/api/) — ver Paso 8 bis
API_MODO=privada
API_ROLES=SUPERADMIN
API_CLAVE=<una clave larga y aleatoria, distinta de la de Django>
API_ORIGENES=*
API_TAM_PAGINA=25
API_TAM_PAGINA_MAX=100
```

> `API_CLAVE` es **opcional**: sirve para que programas externos consulten la
> API. Si solo la vas a mirar tú desde el navegador, déjala vacía y entra con tu
> sesión de super administrador.

> Para generar `API_CLAVE` sin inventarla a mano:
>
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(32))"
> ```
>
> Si dejas `API_CLAVE` vacía, los recursos públicos de la API quedan **abiertos
> a cualquiera** y los que exponen datos personales (`/api/usuarios/`,
> `/api/cursos/<código>/estudiantes/`) quedan **deshabilitados**.

> La clave secreta y la contraseña de MySQL **no se escriben en esta guía** ni en
> `.env.ejemplo`: ambos archivos van al repositorio. Viven solo en el `.env` del
> servidor, que está en `.gitignore`.

Guarda con `Ctrl+O`, `Enter`, y sal con `Ctrl+X`.

**Comprueba que no quedó ningún marcador sin reemplazar:**

```bash
grep -nE 'jostin|<la |<una |pega-aqui' .env
```

Si imprime algo, esa línea sigue con el texto de la plantilla. Un marcador
olvidado aquí produce en el Paso 6 el error
`Unknown server host 'mysql-tucuenta.alwaysdata.net'`.

Protege el archivo (contiene contraseñas):

```bash
chmod 600 .env
```

> Hay una plantilla lista en `backend/.env.ejemplo` por si prefieres copiarla:
> `cp .env.ejemplo .env && nano .env`

---

## Paso 6. Crear las tablas y los datos iniciales

Siempre desde `~/www/EspolAcademicsManagev2/backend` con el entorno activado
(`source ~/venv-espol/bin/activate`):

```bash
# 1. Revisión previa: debe decir "no issues"
python manage.py check

# 2. Crear todas las tablas en MySQL
python manage.py migrate

# 3. Confirmar que las migraciones quedaron aplicadas
python manage.py showmigrations accounts cursos evaluaciones

# 4. Recolectar los archivos estáticos (admin de Django y DRF)
python manage.py collectstatic --noinput

# 5. Crear tu usuario administrador
python manage.py createsuperuser
```

En `createsuperuser` te pedirá: **correo**, nombres, apellidos, identificación,
celular y contraseña (el correo es el usuario de acceso, no un "username").

**Opcional pero recomendado para la entrega:** cargar los datos de prueba
(facultades, cursos, módulos, tareas y quizzes de ejemplo):

```bash
python manage.py seed
```

> ⚠️ `seed` **borra y vuelve a crear** todos los datos, incluido el superusuario
> que acabas de hacer. Si lo vas a usar, ejecútalo **antes** de
> `createsuperuser`, o usa el usuario que crea el propio seed:
> `carlos.mendoza@espol.edu.ec` / `admin123`.

Puedes verificar las tablas creadas desde **Bases de datos → MySQL → phpMyAdmin**
en el panel de AlwaysData; deben aparecer:
`usuario`, `facultad`, `curso`, `formula_componente`, `inscripcion`, `modulo`,
`material`, `progreso_modulo`, `tarea`, `entrega`, `quiz`, `pregunta`,
`respuesta_quiz`.

---

## Paso 7. Crear el sitio web en el panel de AlwaysData

1. En el panel entra a **Web → Sitios** → botón **Añadir un sitio**.
2. Completa así:

| Campo | Valor |
|---|---|
| **Direcciones** | `jostin.alwaysdata.net` |
| **Tipo** | `Python WSGI` |
| **Ruta de la aplicación** (Application) | `$HOME/www/EspolAcademicsManagev2/backend/config/wsgi.py` |
| **Directorio de trabajo** (Working directory) | `$HOME/www/EspolAcademicsManagev2/backend` |
| **Entorno virtual** (Virtualenv directory) | `$HOME/venv-espol` |
| **Versión de Python** | la misma que elegiste en el Paso 4 |

3. Guarda con **Enviar / Submit**.

> Si el formulario pide el nombre de la variable WSGI, es `application`
> (algunos formularios lo escriben junto: `config/wsgi.py:application`).

---

## Paso 8. Reiniciar y probar

En el panel: **Web → Sitios → ⚙️ → Reiniciar**
(o por SSH, si tu plan lo permite, con el botón de reinicio del panel).

Abre en el navegador y verifica una por una:

| URL | Qué debe verse |
|---|---|
| `https://jostin.alwaysdata.net/` | Pantalla de login de ESPOL Academics |
| `https://jostin.alwaysdata.net/admin/` | Login del administrador de Django, **con estilos** |
| `https://jostin.alwaysdata.net/panel/` | Panel académico con el conteo de cada módulo |
| `https://jostin.alwaysdata.net/accounts/usuarios/` | Listado de usuarios con botones Detalle / Editar / Eliminar |
| `https://jostin.alwaysdata.net/cursos/cursos/` | Listado de cursos |
| `https://jostin.alwaysdata.net/evaluaciones/tareas/` | Listado de tareas |
| `https://jostin.alwaysdata.net/api/` | Índice de la API en JSON (ver *Paso 8 bis*) |

> `/panel/` y todo el CRUD piden inicio de sesión. Si te redirige al login,
> entra con tu superusuario y vuelve a la dirección.

Comprueba además las dos funciones de interfaz:

- **Modo oscuro** — el botón de la luna en la barra superior alterna claro/oscuro.
  La elección se guarda y se mantiene al navegar entre el panel y la aplicación.
  Si nunca lo tocas, el sitio sigue el tema del sistema operativo.
- **Tablas adaptables** — reduce el ancho del navegador por debajo de 768 px (o
  ábrelo en el teléfono): cada tabla se convierte en tarjetas, una por registro,
  con sus etiquetas y sus botones.

Prueba también el ciclo completo en cualquier módulo:
**Registrar → Guardar → Detalle → Editar → Eliminar**, y confirma que al
intentar eliminar una facultad que tiene cursos aparece el mensaje rojo
*"No se puede eliminar la facultad porque tiene cursos relacionados"*.

---

## Paso 8 bis. La API pública (`/api/`)

El módulo `backend/api/` publica los datos del sistema en **JSON** para que
otras aplicaciones (una app móvil, otra página web, Postman, un script de
Python) puedan consultarlos desde fuera del servidor.

Características:

- **Solo lectura.** Los datos únicamente se consultan con `GET`; ninguna ruta
  de la API modifica el contenido académico de la base. Las dos únicas rutas
  `POST` son las de identificarse (`/api/auth/login/` y `/api/auth/logout/`).
- **Sin dependencias nuevas.** Está hecha con Django puro (`JsonResponse`), no
  con Django REST Framework, para no consumir la cuota de 100 MB de la cuenta.
- **CORS habilitado**, así que se puede llamar desde el navegador de otro sitio.
- **Tres formas de entrar**, y basta con una: tu **sesión de super
  administrador** (nada que escribir), un **token** que otra aplicación pide
  con las credenciales de un super administrador, o una **clave** fija del
  sitio para tus propios scripts.
- **Pensada para que la consuman otras apps.** La aplicación de un tercero, con
  su propio sistema de login, cambia el correo y la contraseña de su usuario por
  un token; si esa cuenta es **SUPERADMIN** en esta base de datos obtiene acceso
  completo, y si no, recibe siempre el mismo aviso:
  `No se ha autorizado que sea un super admin.`

### Cómo se autentica

El módulo `backend/api/seguridad.py` decide quién entra. Hay tres vías y basta
con cumplir una:

| Vía | Para qué sirve | Cómo |
|---|---|---|
| **Sesión** | Mirar la API tú, desde el navegador | Inicia sesión en `/admin/` con un usuario de rol **SUPERADMIN** y abre la API en la misma ventana. No hay claves de por medio. |
| **Token** | **Otras aplicaciones** con su propio login | `POST /api/auth/login/` con el correo y la contraseña de un **SUPERADMIN** de esta base; luego `Authorization: Bearer <token>` en cada petición |
| **Clave** | Tus propios scripts, sin usuario detrás | Encabezado `X-API-Key: <clave>` (o `?clave=<clave>`) |

La diferencia entre el token y la clave: el **token pertenece a una persona**
(se sabe quién consulta, se revoca solo a esa aplicación y deja de servir en el
momento en que esa cuenta deja de ser super administrador), mientras que la
**clave es única para todo el sitio** y no distingue quién la usa.

Un superusuario de Django entra siempre, tenga el rol que tenga. Puedes ampliar
los roles con `API_ROLES=SUPERADMIN,ADMIN` en el `.env`.

**Si solo la vas a consultar desde el navegador, puedes dejar `API_CLAVE` vacía
y borrarla del `.env`.** La sesión basta.

`API_MODO` decide qué pasa con quien **no** se identifica de ninguna de las dos
formas:

| | `/api/` y `/api/estado/` | Catálogo (facultades, cursos, módulos, tareas, quizzes, reportes) | Datos personales (`usuarios`, `estudiantes`) |
|---|---|---|---|
| `API_MODO=privada` *(por defecto)* | Abiertos | Sesión o clave | Sesión o clave |
| `API_MODO=publica` | Abiertos | Abiertos a cualquiera | Sesión o clave |

`/api/auth/login/` tampoco pide nada: es justamente la puerta por la que se
entra. `/api/` y `/api/estado/` nunca piden nada: el índice no devuelve datos del
sistema y el estado sirve para monitorear el servicio (sus totales sí se ocultan
a quien no se identifica). Al abrir `https://jostin.alwaysdata.net/api/` en el
navegador ves la lista de recursos y **si tu sesión actual está autorizada**:

```json
"acceso_actual": { "autorizado": true, "via": "sesion", "usuario": "tu@espol.edu.ec" }
```

#### Un solo login para todo

La pantalla de `index.html` **ya no valida contra los datos de prueba del
navegador**: llama a `POST /api/auth/login/` con `"sesion": true`, que comprueba
el correo y la contraseña contra MySQL y abre la **cookie de sesión de Django**.
Con un único usuario y una única contraseña entras a:

| | |
|---|---|
| `https://jostin.alwaysdata.net/` | el sitio (panel de superadmin, profesor o estudiante) |
| `/admin/` y `/panel/` | la administración de Django, ya identificado |
| `/api/…` | la API, sin escribir ninguna clave |

Por eso **el `desplegar.sh` solo crea un usuario**: el `createsuperuser` de
Django nace con rol `SUPERADMIN`, así que esa misma cuenta es la del `index.html`.
No hay que darla de alta dos veces.

En el **dashboard del superadmin** hay una tarjeta con el estado de la sesión y
dos botones directos: **Panel de Django** (`/admin/`) y **Lista de endpoints de
la API** (`/api/`).

Detalles que conviene saber:

- Quien **no** es superadmin (profesor, estudiante, admin de facultad) entra
  igual a su panel; simplemente la respuesta trae `"autorizado": false` y el
  aviso, y la API le sigue respondiendo `401`.
- El sitio pide `"token": false`: le basta la cookie, así que **no se guarda
  ningún token en el navegador** ni se crea una fila por cada vez que alguien
  entra. Los tokens son solo para aplicaciones de terceros.
- El botón **Salir** llama a `POST /api/auth/logout/`, que cierra la sesión de
  Django además de la del navegador.
- Si abres `index.html` **suelto** (con `file://`, sin Django levantado), el
  login cae en el modo demo de siempre con los usuarios de `mockdata.js`, y el
  dashboard lo avisa con una etiqueta *Modo demo*.

#### Desde el navegador (lo más cómodo)

1. Entra a `https://jostin.alwaysdata.net/admin/` con tu superusuario.
2. En esa misma ventana abre `https://jostin.alwaysdata.net/api/cursos/`.

Ya está: la cookie de sesión viaja sola. Si cierras sesión, vuelve el `401`.

#### Desde un programa

Un script no tiene sesión, así que usa la clave:

```bash
curl -H "X-API-Key: TU_CLAVE" https://jostin.alwaysdata.net/api/cursos/
```

Un navegador no puede enviar encabezados al escribir una dirección; si no
quieres iniciar sesión, añade `?clave=` a la URL:

```
https://jostin.alwaysdata.net/api/cursos/?clave=TU_CLAVE
```

> Ten en cuenta que así la clave queda en el historial y en los registros del
> servidor. Con la sesión no pasa eso, por eso es la vía recomendada para mirarla
> tú mismo.

Si no recuerdas la clave, está en el servidor:

```bash
grep API_CLAVE ~/www/EspolAcademicsManagev2/backend/.env
```

#### Desde otra aplicación con su propio login (la vía recomendada)

Este es el caso de una app de terceros: tiene sus propios usuarios, y quiere
saber si el que acaba de entrar es super administrador **en esta base de datos**
para darle acceso a la API completa.

**Paso 1 — pedir el token.** La otra aplicación envía el correo y la contraseña
que su usuario tiene en ESPOL Academics:

```bash
curl -X POST https://jostin.alwaysdata.net/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"correo": "tu@espol.edu.ec", "password": "TU_CONTRASENA",
       "aplicacion": "Nombre de la app", "dias": 30}'
```

Si la cuenta es **SUPERADMIN**, la respuesta trae el token (`200`):

```json
{
  "ok": true,
  "datos": {
    "autorizado": true,
    "token": "Ijh9SD5-3gkSu61mFRy1wJpzfImhMsMSZ7vXbVA45xzM0dGF",
    "tipo": "Bearer",
    "expira": "2026-09-12T02:53:52+00:00",
    "usuario": { "correo": "tu@espol.edu.ec", "rol": "SUPERADMIN", "es_superadmin": true },
    "acceso": "completo"
  }
}
```

Y si **no** lo es, aunque el correo y la contraseña sean correctos (`403`):

```json
{
  "ok": false,
  "error": "No se ha autorizado que sea un super admin.",
  "codigo": 403,
  "autorizado": false,
  "motivo": "no_superadmin",
  "detalle": "La cuenta ana.paredes@espol.edu.ec tiene rol USER; la API solo la usan los roles SUPERADMIN.",
  "usuario": { "correo": "ana.paredes@espol.edu.ec", "rol": "USER", "es_superadmin": false }
}
```

> El texto del token **solo se muestra una vez**. Guárdalo en el servidor de la
> otra aplicación (nunca en el navegador ni en el código fuente). En la base de
> datos de ESPOL Academics no se guarda el token, sino su huella SHA-256, así
> que nadie puede recuperarlo mirando la tabla `token_api`.
>
> El campo `dias` es opcional (por defecto `API_TOKEN_DIAS=30`, máximo
> `API_TOKEN_DIAS_MAX`). Tras diez intentos fallidos con el mismo correo desde
> la misma IP el login responde `429` durante unos minutos.

**Paso 2 — usar el token en cada petición:**

```bash
curl -H "Authorization: Bearer TU_TOKEN" https://jostin.alwaysdata.net/api/usuarios/
```

Si algún servidor intermedio se come el encabezado `Authorization`, sirve
igual `X-API-Token: TU_TOKEN`.

**Paso 3 — preguntar en cualquier momento si sigue autorizado.** Es la ruta que
la otra aplicación consulta para decidir si le enseña o no la sección de
administración a su usuario:

```bash
curl -H "Authorization: Bearer TU_TOKEN" https://jostin.alwaysdata.net/api/auth/verificar/
```

```json
{
  "ok": true,
  "datos": {
    "autorizado": true,
    "via": "token",
    "mensaje": "Sesion de super administrador confirmada.",
    "usuario": { "correo": "tu@espol.edu.ec", "rol": "SUPERADMIN", "es_superadmin": true },
    "acceso": "completo",
    "token": { "prefijo": "Ijh9SD5-3gkS", "aplicacion": "Nombre de la app", "expira": "..." }
  }
}
```

Sin token, con un token caducado o con una cuenta que ya no es super
administrador, responde `401`/`403` con **el mismo mensaje de siempre** y un
`motivo` que la aplicación puede leer sin interpretar el texto:

```json
{ "ok": false, "error": "No se ha autorizado que sea un super admin.",
  "autorizado": false, "motivo": "sin_credenciales", "como_autorizarse": { "...": "..." } }
```

| `motivo` | Qué hacer en la otra aplicación |
|---|---|
| `sin_credenciales` | No mandaste token: pide el login |
| `credenciales_invalidas` | Correo o contraseña mal escritos |
| `no_superadmin` | La cuenta existe pero no es SUPERADMIN: muéstrale el aviso |
| `cuenta_inactiva` | La cuenta está desactivada en ESPOL Academics |
| `token_invalido` / `token_revocado` / `token_caducado` | Vuelve a pedir un token en `/api/auth/login/` |
| `demasiados_intentos` | Espera unos minutos antes de reintentar |

**Paso 4 — cerrar sesión.** Cuando el usuario sale de la otra aplicación, esta
devuelve el token para que no siga sirviendo:

```bash
curl -X POST -H "Authorization: Bearer TU_TOKEN" \
  https://jostin.alwaysdata.net/api/auth/logout/
```

Con `-d '{"todos": true}'` (y `Content-Type: application/json`) revoca **todos**
los tokens de esa cuenta, que es lo que hay que hacer si uno se filtró. También
puedes revocarlos a mano desde `/admin/` → **Tokens de API**, donde se ve qué
aplicación tiene acceso y cuándo lo usó por última vez.

**El rol se comprueba en cada petición.** Si le quitas el rol SUPERADMIN a una
cuenta (o la marcas como inactiva), sus tokens dejan de funcionar en ese mismo
instante, sin esperar a que caduquen.

### Recursos disponibles

| Método y ruta | Qué devuelve |
|---|---|
| `GET /api/` | Índice: lista todos los recursos, filtros y opciones de paginación |
| `GET /api/estado/` | Salud del servicio: versión, conexión a la base y totales |
| `POST /api/auth/login/` | Cambia correo + contraseña de un SUPERADMIN por un token. Con `"sesion": true` es además el login del sitio |
| `GET /api/auth/verificar/` | ¿Quien pregunta está identificado como super administrador? |
| `POST /api/auth/logout/` | Revoca el token con el que se llama y cierra la sesión de Django |
| `GET /api/facultades/` | Listado de facultades con su número de cursos |
| `GET /api/facultades/<código>/` | Una facultad y sus cursos (ej. `FIEC`) |
| `GET /api/cursos/` | Catálogo de cursos (paginado) |
| `GET /api/cursos/<código>/` | Curso completo: fórmula, módulos, materiales, tareas y quizzes |
| `GET /api/cursos/<código>/modulos/` | Módulos del curso con sus materiales |
| `GET /api/cursos/<código>/tareas/` | Tareas del curso |
| `GET /api/cursos/<código>/quizzes/` | Quizzes del curso |
| `GET /api/quizzes/<id>/` | Quiz con sus preguntas (**sin** las respuestas correctas) |
| `GET /api/reportes/resumen/` | Indicadores del tablero: totales, promedios y estado de entregas |
| `GET /api/usuarios/` | 🔒 Usuarios registrados (datos personales) |
| `GET /api/cursos/<código>/estudiantes/` | 🔒 Estudiantes inscritos en un curso |

Los cursos y las facultades se buscan por su **código** (`DAWM-2026A`, `FIEC`),
no por su `id`, y no distingue mayúsculas de minúsculas.

### Filtros y paginación

| Recurso | Parámetros |
|---|---|
| `/api/cursos/` | `facultad`, `estado` (`activo`/`archivado`), `profesor` (id o correo), `buscar` |
| `/api/usuarios/` | `rol`, `estado`, `facultad`, `buscar` |
| `/api/reportes/resumen/` | `facultad`, `estado` |
| Todos los listados | `pagina` (por defecto 1), `tam` (por defecto 25, máximo 100) |

```bash
# cursos activos de la FIEC, de 10 en 10, segunda página
curl -H "X-API-Key: TU_CLAVE" \
  "https://jostin.alwaysdata.net/api/cursos/?facultad=FIEC&estado=activo&tam=10&pagina=2"
```

### Forma de las respuestas

Todo viene envuelto igual, de modo que el cliente siempre revisa `ok` primero:

```json
{
  "ok": true,
  "datos": [
    {
      "id_curso": 4,
      "codigo": "DAWM-2026A",
      "nombre": "Desarrollo de Aplicaciones Web y Moviles",
      "estado": "activo",
      "fecha_inicio": "2026-03-01",
      "fecha_fin": "2026-07-31",
      "facultad": { "id_facultad": 5, "codigo": "FIEC", "nombre": "..." },
      "profesor": { "id_usuario": 8, "nombre_completo": "Roberto Llerena Castillo" }
    }
  ],
  "paginacion": {
    "pagina": 1, "paginas": 3, "tam": 1, "total": 3,
    "siguiente": 2, "anterior": null
  }
}
```

Y los errores, también en JSON (nunca una página HTML de Django):

```json
{
  "ok": false,
  "error": "No se ha autorizado que sea un super admin.",
  "codigo": 401,
  "autorizado": false,
  "motivo": "sin_credenciales",
  "detalle": "No se recibio ninguna credencial valida (sesion, token o clave).",
  "como_autorizarse": { "token": { "paso_1": "POST /api/auth/login/ ...", "paso_2": "..." } }
}
```

| Código | Significado |
|---|---|
| `200` | Todo bien |
| `400` | Un parámetro mal escrito (por ejemplo `estado=inventado`) o faltan credenciales en el login |
| `401` | No te identificaste: ni sesión de SUPERADMIN, ni token válido, ni clave |
| `403` | Te identificaste bien, pero esa cuenta **no es super administrador** |
| `404` | El curso, la facultad o la ruta no existen |
| `405` | Se usó `PUT`/`DELETE`, o `POST` en una ruta que no es de `/api/auth/` |
| `429` | Demasiados intentos fallidos de login con ese correo |

### Ejemplo de consumo desde otra aplicación

```javascript
// Aplicación de terceros: primero cambia las credenciales por un token
// (esto va en TU servidor, no en el navegador del usuario).
const API = "https://jostin.alwaysdata.net/api";

const entrada = await fetch(`${API}/auth/login/`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ correo, password, aplicacion: "Mi App" }),
});

const sesion = await entrada.json();

if (!sesion.ok) {
  // "No se ha autorizado que sea un super admin."
  mostrarAviso(sesion.error, sesion.motivo);
} else {
  const token = sesion.datos.token;   // guárdalo, no se vuelve a mostrar

  const respuesta = await fetch(`${API}/cursos/?estado=activo`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  const { ok, datos } = await respuesta.json();
  if (ok) datos.forEach(curso => console.log(curso.codigo, curso.nombre));
}
```

```javascript
// Desde una página del mismo dominio, con la sesión ya iniciada,
// basta con credentials: "include" y ningún token.
const RESPUESTA = await fetch(
  "https://jostin.alwaysdata.net/api/cursos/?estado=activo",
  { credentials: "include" },
);
```

```python
import requests

API = "https://jostin.alwaysdata.net/api"

sesion = requests.post(
    f"{API}/auth/login/",
    json={"correo": "tu@espol.edu.ec", "password": "TU_CONTRASENA",
          "aplicacion": "Script de reportes"},
    timeout=10,
).json()

if not sesion["ok"]:
    raise SystemExit(sesion["error"])   # No se ha autorizado que sea un super admin.

cabeceras = {"Authorization": "Bearer " + sesion["datos"]["token"]}

r = requests.get(
    f"{API}/cursos/",
    headers=cabeceras,
    params={"facultad": "FIEC"},
    timeout=10,
)
for curso in r.json()["datos"]:
    print(curso["codigo"], curso["nombre"])
```

### Limitar quién puede llamarla desde el navegador

Por defecto `API_ORIGENES=*` acepta peticiones de cualquier página. Para
restringirla, escribe los dominios separados por coma en el `.env` y reinicia:

```
API_ORIGENES=https://mi-otra-app.com,https://jostin.alwaysdata.net
```

### Probarla antes de subirla

En tu computadora, con el entorno virtual activado y dentro de `backend/`:

```bash
python manage.py test api        # 65 pruebas del módulo
python manage.py runserver       # luego abre http://127.0.0.1:8000/api/
```

---

## Paso 9. Actualizar el proyecto más adelante

**Si usaste git (Opción C), que es lo más cómodo:**

```bash
# en tu computadora
git add -A && git commit -m "descripcion del cambio" && git push

# en el servidor
cd ~/www/EspolAcademicsManagev2 && git pull
source ~/venv-espol/bin/activate
cd backend
python manage.py migrate && python manage.py collectstatic --noinput
```

Después reinicia el sitio en **Web → Sitios → ⚙️ → Reiniciar**.

**Si usaste rsync:**

Cada vez que cambies el código en tu computadora:

```bash
# 1. Subir los cambios
cd /home/josmocobos
rsync -avz --exclude 'venv/' --exclude '__pycache__/' --exclude '.git/' \
  --exclude 'staticfiles/' --exclude 'db.sqlite3' --exclude '*.bak-*' \
  EspolAcademicsManagev2 jostin@ssh-jostin.alwaysdata.net:~/www/

# 2. Aplicar cambios en el servidor
ssh jostin@ssh-jostin.alwaysdata.net
source ~/venv-espol/bin/activate
cd ~/www/EspolAcademicsManagev2/backend
python manage.py migrate
python manage.py collectstatic --noinput
```

3. Reinicia el sitio desde **Web → Sitios → ⚙️ → Reiniciar**.

> El archivo `.env` vive solo en el servidor y `rsync` no lo borra, porque no
> existe en tu copia local (está en `.gitignore`).

---

## Paso 10. Solución de problemas

| Síntoma | Causa y solución |
|---|---|
| **`DisallowedHost` / "Invalid HTTP_HOST"** | Falta tu dominio en `DJANGO_ALLOWED_HOSTS` del `.env`. Agrégalo y reinicia el sitio. |
| **Error 500 sin detalle** | Revisa el log: **Web → Sitios → ⚙️ → Registros (Logs)**, o `tail -50 ~/admin/logs/http/error.log` por SSH. |
| **El `/admin/` se ve sin estilos** | Faltó `python manage.py collectstatic --noinput`. Ejecútalo y reinicia. |
| **"CSRF verification failed" al guardar un formulario** | Falta `DJANGO_CSRF_TRUSTED_ORIGINS=https://jostin.alwaysdata.net` en el `.env`. |
| **`ssh: Network is unreachable`** | Tu red no tiene IPv6 y `ssh` prueba esa dirección primero. `AddressFamily inet` en `~/.ssh/config`, o `-e "ssh -4"`. |
| **`ssh: Connection refused` (puerto 22)** | Tu red bloquea el SSH saliente; compruébalo con `ssh git@github.com`, que falla igual. Ve al **Apéndice**. |
| **`Unknown server host 'mysql-tucuenta...'`** | Quedó un marcador sin reemplazar en el `.env`. Verifícalo con el `grep` del Paso 5. |
| **`Connection to upstream failed`** | La aplicación no arrancó. Mira `tail -50 ~/admin/logs/sites/*` y reproduce el arranque con `python -c "from config.wsgi import application"`. Causas típicas: versión de Python del sitio distinta a la del venv, rutas mal en el Paso 7, o cuota de disco llena. |
| **`Access denied for user`** | Usuario, contraseña o host de MySQL mal escritos en el `.env`. Verifícalos en **Bases de datos → MySQL**. |
| **`mysqlclient ... is required`** | Instalaste PyMySQL sin activarlo. Agrega `DB_DRIVER=pymysql` al `.env` y reinicia. |
| **`error: command 'gcc' failed` al instalar mysqlclient** | Usa el driver alternativo: `pip install PyMySQL==1.1.2` y `DB_DRIVER=pymysql` en el `.env`. |
| **`ModuleNotFoundError: No module named 'django'`** en `~/admin/logs/uwsgi/*.log` | **Causa nº 1:** la *Version de Python* del sitio no es la del entorno virtual. uWSGI arranca con el intérprete del panel y busca los paquetes en `venv-espol/lib/pythonX.Y/`; si el venv se creó con otra versión, no ve nada, aunque esté todo bien instalado. Compara `ls ~/venv-espol/lib/` con la versión que dice el log (`Python version: 3.13.x`) y con la del panel: **las tres deben coincidir**. Si no, [rehaz el venv](#si-el-venv-quedó-con-otra-versión-de-python). **Causa nº 2:** `pip` se quedó sin espacio y dejó el venv a medias; verifícalo con `~/venv-espol/bin/python -c "import django"`. |
| **`ModuleNotFoundError: No module named 'config'`** | El *Working directory* del sitio no apunta a `.../EspolAcademicsManagev2/backend`. Corrígelo en el Paso 7. |
| **`SyntaxError` o `Django requires Python 3.12`** | El entorno virtual se creó con una versión vieja de Python. Bórralo (`rm -rf ~/venv-espol`) y repite el Paso 4 con una versión más alta, o baja a `Django==5.2.11`. |
| **La página queda en blanco tras un cambio** | Falta reiniciar el sitio en el panel. |
| **`401` al abrir la API en el navegador** | No has iniciado sesión, o el usuario con el que entraste no es `SUPERADMIN`. Entra en `/admin/` y vuelve a la dirección; comprueba tu rol en `/api/` (`acceso_actual`). También sirve añadir `?clave=TU_CLAVE`. |
| **`401` con la clave puesta** | No coincide con `API_CLAVE` del `.env`, o el `.env` cambió y falta reiniciar el sitio. Compruébala con `grep API_CLAVE ~/www/EspolAcademicsManagev2/backend/.env`. |
| **`/api/usuarios/` responde `503`** | `API_CLAVE` está vacía en el `.env`. Ponle un valor y reinicia el sitio. |
| **`403` con `"motivo": "no_superadmin"` al hacer login** | El correo y la contraseña son correctos, pero esa cuenta no tiene rol `SUPERADMIN`. Cámbiaselo en `/admin/` → *Usuarios*, o amplía `API_ROLES` en el `.env`. |
| **`401` con `"motivo": "token_caducado"` o `"token_revocado"`** | El token venció (`API_TOKEN_DIAS`) o alguien lo revocó desde `/admin/` → *Tokens de API*. La aplicación tiene que volver a `POST /api/auth/login/`. |
| **El token deja de servir de golpe** | A esa cuenta le quitaron el rol `SUPERADMIN` o la marcaron inactiva: el rol se comprueba en cada petición. Compruébalo en `/api/auth/verificar/` (`detalle`). |
| **`429` al iniciar sesión** | Diez intentos fallidos con ese correo desde la misma IP. Espera `API_LOGIN_BLOQUEO_MIN` minutos. |
| **`/api/` devuelve HTML en vez de JSON** | La ruta `path('api/', include('api.urls'))` quedó **después** del `re_path` que sirve el frontend en `config/urls.py`, o falta `'api'` en `INSTALLED_APPS`. |
| **El navegador bloquea la llamada por CORS** | Tu dominio no está en `API_ORIGENES`. Ponlo en el `.env` (o déjalo en `*`) y reinicia. Ojo: para usar la **sesión** desde otro dominio hay que listarlo explícitamente — con `*` el navegador no envía cookies, y ahí solo funciona la clave. |

---

## Resumen de comandos (para copiar rápido)

```bash
# En tu computadora
rsync -avz --exclude 'venv/' --exclude '__pycache__/' --exclude '.git/' \
  --exclude 'staticfiles/' --exclude 'db.sqlite3' --exclude '*.bak-*' \
  ~/EspolAcademicsManagev2 jostin@ssh-jostin.alwaysdata.net:~/www/

# En el servidor
ssh jostin@ssh-jostin.alwaysdata.net
/usr/alwaysdata/python/3.13/bin/python3 -m venv ~/venv-espol
source ~/venv-espol/bin/activate
cd ~/www/EspolAcademicsManagev2/backend
pip install -r requirements-produccion.txt
nano .env                       # configuración del Paso 5
chmod 600 .env
python manage.py check
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed           # datos de prueba (opcional)
python manage.py createsuperuser

# Comprobar la API una vez que el sitio esté en línea
curl -H "X-API-Key: TU_CLAVE" https://jostin.alwaysdata.net/api/estado/
```

Después: crear el sitio (Paso 7) y **reiniciarlo** (Paso 8).

---

### Si el venv quedó con otra versión de Python

Es el fallo más común y se arregla rehaciendo el entorno con la versión exacta
que usa el sitio (la que aparece en el log como `Python version: 3.13.x`):

```bash
ls ~/venv-espol/lib/          # ¿python3.13? ¿python3.14?

rm -rf ~/venv-espol
/usr/alwaysdata/python/3.13/bin/python3 -m venv ~/venv-espol
~/venv-espol/bin/pip install --no-cache-dir \
  -r ~/www/EspolAcademicsManagev2/backend/requirements-produccion.txt

# comprobación: esto es exactamente lo que hace uWSGI al arrancar
cd ~/www/EspolAcademicsManagev2/backend
~/venv-espol/bin/python -c "from config.wsgi import application; print('ok')"
```

Si imprime `ok`, reinicia el sitio en el panel y listo. Cambia `3.13` por la
versión que muestre tu log si es otra.

---

## Apéndice. Si tu red bloquea el puerto 22

**Síntoma:** `ssh: connect to host ... port 22: Connection refused`.

**Diagnóstico** — si esto falla contra GitHub, el bloqueo es de tu red, no de
AlwaysData:

```bash
timeout 6 bash -c 'exec 3<>/dev/tcp/github.com/22' && echo "22 OK" || echo "22 BLOQUEADO"
timeout 6 bash -c 'exec 3<>/dev/tcp/alwaysdata.com/443' && echo "443 OK" || echo "443 BLOQUEADO"
```

**Solución 1 (la mejor): otra red.** Hotspot del celular. Las redes móviles no
suelen bloquear el 22 y con eso la guía funciona tal cual.

**Solución 2: todo por HTTPS (puerto 443).** Nada de esto usa el puerto 22:

| Para | Usa |
|---|---|
| Subir el código (Paso 3) | **git** — Opción C del Paso 3 |
| Ejecutar comandos en el servidor (Pasos 4 a 6) | `https://ssh-jostin.alwaysdata.net` — consola SSH del navegador |
| Subir archivos sueltos | `https://webdav-jostin.alwaysdata.net/` |

La consola web es una terminal real de tu servidor servida por HTTPS. La propia
documentación de AlwaysData avisa de que es lenta y poco fiable, así que úsala
solo si no puedes cambiar de red — pero para los comandos de los Pasos 4 a 6
sirve perfectamente.

Los Pasos 7 y 8 son en el panel web y no se ven afectados.

*Alternativa a git para subir archivos, si la prefieres:*

```bash
sudo apt install -y davfs2
mkdir -p ~/alwaysdata
sudo mount -t davfs https://webdav-jostin.alwaysdata.net/ ~/alwaysdata
rsync -av --no-perms --no-owner --no-group \
  --exclude 'venv/' --exclude '__pycache__/' --exclude 'staticfiles/' \
  --exclude 'db.sqlite3' ~/EspolAcademicsManagev2 ~/alwaysdata/www/
sudo umount ~/alwaysdata
```

> `--no-perms --no-owner --no-group` son obligatorios: WebDAV no maneja permisos
> Unix y sin ellos `rsync` aborta.
