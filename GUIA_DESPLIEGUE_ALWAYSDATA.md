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
dependencias → genera la clave secreta de Django y te **pide la contraseña de
MySQL** para escribir el `.env` → `migrate` → datos de prueba → te pide crear el
**superusuario**. Al terminar imprime los valores exactos para el Paso 7.

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
Elige la versión más alta que aparezca (por ejemplo `3.13`) y créate el entorno:

```bash
cd ~/www/EspolAcademicsManagev2/backend

/usr/alwaysdata/python/3.13/bin/python3 -m venv ~/venv-espol
source ~/venv-espol/bin/activate

python --version          # debe decir 3.12.x o superior
pip install --upgrade pip
pip install -r requirements-produccion.txt
```

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
```

> La clave secreta y la contraseña de MySQL **no se escriben en esta guía** ni en
> `.env.ejemplo`: ambos archivos van al repositorio. Viven solo en el `.env` del
> servidor, que está en `.gitignore`.

Guarda con `Ctrl+O`, `Enter`, y sal con `Ctrl+X`.

**Comprueba que no quedó ningún marcador sin reemplazar:**

```bash
grep -nE 'jostin|<la |pega-aqui' .env
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
| **`ModuleNotFoundError: No module named 'config'`** | El *Working directory* del sitio no apunta a `.../EspolAcademicsManagev2/backend`. Corrígelo en el Paso 7. |
| **`SyntaxError` o `Django requires Python 3.12`** | El entorno virtual se creó con una versión vieja de Python. Bórralo (`rm -rf ~/venv-espol`) y repite el Paso 4 con una versión más alta, o baja a `Django==5.2.11`. |
| **La página queda en blanco tras un cambio** | Falta reiniciar el sitio en el panel. |

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
```

Después: crear el sitio (Paso 7) y **reiniciarlo** (Paso 8).

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
