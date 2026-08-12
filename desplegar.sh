#!/usr/bin/env bash
#
# Despliegue de ESPOL Academics v2 en AlwaysData.
#
# Ejecutalo en el servidor (SSH o la consola web https://ssh-jostin.alwaysdata.net):
#
#   curl -fsSL https://raw.githubusercontent.com/Jostin798M/EspolAcademicsManagev2/main/desplegar.sh -o ~/desplegar.sh
#   bash ~/desplegar.sh
#
# Hace: git clone -> entorno virtual -> dependencias -> .env -> migrate ->
#       datos de prueba -> comprobacion de la API -> superusuario.
#
# Se puede volver a ejecutar sin miedo: si algo ya existe, lo reutiliza.
# NO toca la configuracion del sitio en el panel: eso lo haces tu al final,
# con los datos que imprime.

set -euo pipefail

CUENTA="jostin"
PROYECTO="EspolAcademicsManagev2"
REPO_URL="https://github.com/Jostin798M/${PROYECTO}.git"
DESTINO="$HOME/www/$PROYECTO"
BACKEND="$DESTINO/backend"
VENV="$HOME/venv-espol"
DOMINIO="${CUENTA}.alwaysdata.net"

DB_NAME="${CUENTA}_espolacademics"
DB_USER="$CUENTA"
DB_HOST="mysql-${CUENTA}.alwaysdata.net"

# ── presentacion ─────────────────────────────────────────────────────────────
if [ -t 1 ]; then
    AZUL=$'\033[1;34m'; VERDE=$'\033[1;32m'; AMBAR=$'\033[1;33m'
    ROJO=$'\033[1;31m'; GRIS=$'\033[0;90m';  FIN=$'\033[0m'
else
    AZUL=""; VERDE=""; AMBAR=""; ROJO=""; GRIS=""; FIN=""
fi

paso()  { printf '\n%s──▶ %s%s\n' "$AZUL" "$1" "$FIN"; }
ok()    { printf '%s   ✔ %s%s\n' "$VERDE" "$1" "$FIN"; }
nota()  { printf '%s   · %s%s\n' "$GRIS"  "$1" "$FIN"; }
aviso() { printf '%s   ! %s%s\n' "$AMBAR" "$1" "$FIN"; }
morir() { printf '\n%s✘ %s%s\n\n' "$ROJO" "$1" "$FIN" >&2; exit 1; }

trap 'printf "\n%s✘ El script se detuvo en la linea %s.%s\n   Corrige el problema y vuelve a ejecutarlo: bash ~/desplegar.sh\n\n" "$ROJO" "$LINENO" "$FIN" >&2' ERR

printf '%s\n' "════════════════════════════════════════════════════════"
printf '%s\n' "  Despliegue de ESPOL Academics v2 en AlwaysData"
printf '%s\n' "  cuenta: $CUENTA   ·   destino: $DESTINO"
printf '%s\n' "════════════════════════════════════════════════════════"

# ── 0. comprobaciones previas ────────────────────────────────────────────────
paso "Comprobando el entorno"

command -v git >/dev/null || morir "git no esta disponible en este servidor."

PYBASE=""
for base in /usr/alwaysdata/python /usr/local/alwaysdata/python; do
    [ -d "$base" ] && { PYBASE="$base"; break; }
done
[ -n "$PYBASE" ] || morir "No encuentro los Python de AlwaysData. Revisa: ls /usr/alwaysdata/python/"
nota "Pythons disponibles en $PYBASE"

# Ojo con "set -e": una tuberia que no encuentra nada devuelve 1 y matarIa el
# script en la asignacion. Por eso todas llevan "|| true" y el valor se
# comprueba despues.
DISPONIBLES="$(ls "$PYBASE" 2>/dev/null \
    | grep -E '^3\.[0-9]+$' \
    | awk -F. '$2 >= 12' \
    | sort -V || true)"
[ -n "$DISPONIBLES" ] || morir "Este servidor no ofrece Python 3.12+. Django 6.0 lo necesita."
nota "Versiones utiles: $(printf '%s' "$DISPONIBLES" | tr '\n' ' ')"

hay_version() {
    printf '%s\n' "$DISPONIBLES" | grep -qx "$1"
}

# La version tiene que ser LA MISMA que la del sitio en el panel: uWSGI arranca
# con ese interprete y busca los paquetes en venv/lib/pythonX.Y/. Si no coincide,
# el log dice "ModuleNotFoundError: No module named 'django'" aunque el venv este
# perfecto. Se intenta averiguar por dos caminos antes de elegir a ciegas.

# 1) la configuracion que genera el propio panel para el sitio
PYVER_SITIO="$(grep -hoE 'python3\.[0-9]+' "$HOME"/admin/config/uwsgi/*.conf 2>/dev/null \
    | head -1 | sed 's/^python//' || true)"

# 2) el entorno virtual que ya existe, si tiene Django funcionando: si el sitio
#    esta en linea ahora mismo, esa es la version buena y no hay que tocarla.
PYVER_VENV=""
if [ -x "$VENV/bin/python" ] && "$VENV/bin/python" -c 'import django' 2>/dev/null; then
    PYVER_VENV="$("$VENV/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])' || true)"
fi

if [ -n "$PYVER_SITIO" ] && hay_version "$PYVER_SITIO"; then
    PYVER="$PYVER_SITIO"
    ok "El sitio del panel usa Python $PYVER: usare esa misma version"
elif [ -n "$PYVER_VENV" ] && hay_version "$PYVER_VENV"; then
    PYVER="$PYVER_VENV"
    ok "El entorno actual ya funciona con Python $PYVER: lo conservo"
    aviso "Comprueba que el sitio del panel tambien diga $PYVER."
elif hay_version "3.13"; then
    # 3.13 es la version que documenta la guia; se prefiere antes que la mas
    # nueva para no adelantarse a lo que ofrece el panel.
    PYVER="3.13"
    nota "No pude averiguar la version del sitio; uso Python $PYVER (la de la guia)"
    aviso "En el panel, la Version de Python del sitio tiene que decir $PYVER."
else
    PYVER="$(printf '%s\n' "$DISPONIBLES" | tail -1)"
    nota "No pude averiguar la version del sitio; uso Python $PYVER"
    aviso "En el panel, la Version de Python del sitio tiene que decir $PYVER."
fi

PYBIN="$PYBASE/$PYVER/bin/python3"
[ -x "$PYBIN" ] || morir "No puedo ejecutar $PYBIN"
ok "Usare Python $PYVER  ($PYBIN)"

USADO="$(du -sm "$HOME" 2>/dev/null | cut -f1 || echo '?')"
nota "Espacio usado en la cuenta: ${USADO} MB de 100 MB"
if [ "$USADO" != "?" ] && [ "$USADO" -gt 75 ]; then
    aviso "Vas justo de cuota. Si algo falla por espacio, libera con:"
    aviso "  rm -rf ~/.cache/pip ~/www/EspolAcademicsManage"
fi

# ── 1. codigo ────────────────────────────────────────────────────────────────
paso "1/8  Descargando el proyecto"

mkdir -p "$HOME/www"
if [ -d "$DESTINO/.git" ]; then
    nota "Ya existe, actualizo con git pull"
    git -C "$DESTINO" pull --ff-only
    ok "Codigo actualizado"
elif [ -e "$DESTINO" ]; then
    morir "$DESTINO existe pero no es un repositorio git. Borralo o renombralo y reintenta."
else
    git clone "$REPO_URL" "$DESTINO"
    ok "Repositorio clonado en $DESTINO"
fi

[ -f "$BACKEND/manage.py" ] || morir "No encuentro $BACKEND/manage.py"

# ── 2. entorno virtual ───────────────────────────────────────────────────────
paso "2/8  Preparando el entorno virtual"

CREAR_VENV=1
if [ -x "$VENV/bin/python" ]; then
    ACTUAL="$("$VENV/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"

    if [ "$ACTUAL" = "$PYVER" ]; then
        nota "Reutilizo el entorno existente ($VENV, Python $ACTUAL)"
        CREAR_VENV=0
    else
        # Un venv de otra version es invisible para uWSGI: sus paquetes viven en
        # lib/python$ACTUAL/ y el sitio los busca en lib/python$PYVER/.
        aviso "El entorno existente usa Python $ACTUAL y el sitio arranca con $PYVER."
        aviso "Son incompatibles: lo rehago con $PYVER."
        rm -rf "$VENV"
    fi
fi

if [ "$CREAR_VENV" = "1" ]; then
    "$PYBIN" -m venv "$VENV"
    ok "Entorno creado en $VENV"
fi

PY="$VENV/bin/python"
PIP="$VENV/bin/pip"

# ── 3. dependencias ──────────────────────────────────────────────────────────
paso "3/8  Instalando dependencias"

# --no-cache-dir es importante: ~/.cache/pip llena la cuota de 100 MB, y un pip
# que se queda sin espacio a mitad de camino deja el venv sin Django.
PIP_OPCIONES=(--quiet --no-cache-dir)

hay_driver_mysql() {
    "$PY" -c 'import MySQLdb' 2>/dev/null || "$PY" -c 'import pymysql' 2>/dev/null
}

if [ -d "$HOME/.cache/pip" ]; then
    rm -rf "$HOME/.cache/pip"
    nota "Borrada la cache de pip para no gastar cuota"
fi

USAR_PYMYSQL=0

if "$PY" -c 'import django, whitenoise' 2>/dev/null && hay_driver_mysql; then
    # Ya estaba todo instalado: no se reinstala. Reinstalar gasta cuota y, si
    # el disco se llena, rompe el venv que ahora mismo funciona.
    nota "Las dependencias ya estan instaladas, no las toco"
    "$PY" -c 'import MySQLdb' 2>/dev/null || USAR_PYMYSQL=1
else
    nota "Esto puede tardar un par de minutos..."
    "$PY" -m pip install "${PIP_OPCIONES[@]}" --upgrade pip

    if "$PIP" install "${PIP_OPCIONES[@]}" -r "$BACKEND/requirements-produccion.txt"; then
        ok "Dependencias instaladas (driver mysqlclient)"
    else
        aviso "mysqlclient no compilo en este servidor. Uso PyMySQL, que es Python puro."
        "$PIP" install "${PIP_OPCIONES[@]}" -r "$BACKEND/requirements.txt" \
            || morir "No se pudieron instalar las dependencias. Suele ser falta de espacio: mira 'du -sm ~' y libera con 'rm -rf ~/.cache/pip ~/www/EspolAcademicsManage'."
        "$PIP" install "${PIP_OPCIONES[@]}" "PyMySQL==1.1.2"
        USAR_PYMYSQL=1
        ok "Dependencias instaladas (driver PyMySQL)"
    fi
fi

# Comprobacion: si Django no se puede importar, el sitio arrancaria con
# "ModuleNotFoundError: No module named 'django'" en el log de uWSGI.
VERSION_DJANGO="$("$PY" -c 'import django; print(django.get_version())' 2>/dev/null || true)"
[ -n "$VERSION_DJANGO" ] || morir "Django no quedo instalado en $VENV. Reinstalalo con:
    $PIP install --no-cache-dir -r $BACKEND/requirements.txt
  Si falla por espacio, libera con: rm -rf ~/.cache/pip"
ok "Django $VERSION_DJANGO listo en el entorno virtual"

VER_VENV="$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"

# ── 4. archivo .env ──────────────────────────────────────────────────────────
paso "4/8  Configuracion (.env)"

if [ -f "$BACKEND/.env" ]; then
    aviso "Ya existe $BACKEND/.env"
    read -rp "   ¿Rehacerlo desde cero? Se pedira otra vez la contrasena [s/N]: " REHACER
    if [ "${REHACER,,}" != "s" ]; then
        nota "Conservo el .env actual"
        CREAR_ENV=0

        # el .env puede venir de una version anterior, sin la seccion de API
        if ! grep -q '^API_CLAVE=' "$BACKEND/.env"; then
            CLAVE_API="$("$PY" -c 'import secrets; print(secrets.token_urlsafe(32))')"
            {
                printf '%s\n' ""
                printf '%s\n' "# API de consulta (/api/). Se entra con la sesion de un usuario"
                printf '%s\n' "# SUPERADMIN o con esta clave (para programas externos)."
                printf '%s\n' "API_MODO=privada"
                printf '%s\n' "API_ROLES=SUPERADMIN"
                printf '%s\n' "API_CLAVE=$CLAVE_API"
                printf '%s\n' "API_ORIGENES=*"
                printf '%s\n' "API_TAM_PAGINA=25"
                printf '%s\n' "API_TAM_PAGINA_MAX=100"
            } >> "$BACKEND/.env"
            ok "Anadida la configuracion de la API al .env existente"
        fi
    else
        cp "$BACKEND/.env" "$BACKEND/.env.anterior"
        nota "Copia de seguridad en $BACKEND/.env.anterior"
        CREAR_ENV=1
    fi
else
    CREAR_ENV=1
fi

if [ "$CREAR_ENV" = "1" ]; then
    # clave secreta generada por el propio Django
    SECRETO="$("$PY" -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"
    [ -n "$SECRETO" ] || morir "No pude generar la clave secreta de Django."
    ok "Clave secreta generada automaticamente (50 caracteres)"

    # clave de la API publica (/api/)
    CLAVE_API="$("$PY" -c 'import secrets; print(secrets.token_urlsafe(32))')"
    [ -n "$CLAVE_API" ] || morir "No pude generar la clave de la API."
    ok "Clave de la API generada automaticamente"

    printf '\n   Contrasena del usuario MySQL "%s"\n' "$DB_USER"
    printf '   %s(la definiste en el panel: Bases de datos → MySQL → Usuarios)%s\n' "$GRIS" "$FIN"
    CLAVE_BD=""
    while [ -z "$CLAVE_BD" ]; do
        read -rsp "   Contrasena: " CLAVE_BD; echo
        [ -n "$CLAVE_BD" ] || aviso "No puede quedar vacia."
    done

    {
        printf '%s\n' "# Generado por desplegar.sh — NO subir este archivo al repositorio."
        printf '%s\n' ""
        printf '%s\n' "DJANGO_SECRET_KEY=$SECRETO"
        printf '%s\n' "DJANGO_DEBUG=False"
        printf '%s\n' "DJANGO_ALLOWED_HOSTS=$DOMINIO"
        printf '%s\n' "DJANGO_CSRF_TRUSTED_ORIGINS=https://$DOMINIO"
        printf '%s\n' ""
        printf '%s\n' "DB_ENGINE=mysql"
        printf '%s\n' "DB_NAME=$DB_NAME"
        printf '%s\n' "DB_USER=$DB_USER"
        printf '%s\n' "DB_PASSWORD=$CLAVE_BD"
        printf '%s\n' "DB_HOST=$DB_HOST"
        printf '%s\n' "DB_PORT=3306"
        [ "$USAR_PYMYSQL" = "1" ] && printf '%s\n' "DB_DRIVER=pymysql"
        printf '%s\n' ""
        printf '%s\n' "# Activar cuando el dominio ya responda por HTTPS"
        printf '%s\n' "DJANGO_SECURE_SSL_REDIRECT=False"
        printf '%s\n' "DJANGO_SECURE_HSTS_SECONDS=0"
        printf '%s\n' ""
        printf '%s\n' "# API de consulta (/api/). Se entra con la sesion de un usuario"
        printf '%s\n' "# SUPERADMIN o con esta clave (para programas externos)."
        printf '%s\n' "API_MODO=privada"
        printf '%s\n' "API_ROLES=SUPERADMIN"
        printf '%s\n' "API_CLAVE=$CLAVE_API"
        printf '%s\n' "API_ORIGENES=*"
        printf '%s\n' "API_TAM_PAGINA=25"
        printf '%s\n' "API_TAM_PAGINA_MAX=100"
    } > "$BACKEND/.env"

    chmod 600 "$BACKEND/.env"
    unset CLAVE_BD
    ok "Escrito $BACKEND/.env (permisos 600, solo tu puedes leerlo)"
fi

# ── 5. conexion con la base de datos ─────────────────────────────────────────
paso "5/8  Verificando la conexion con MySQL"

cd "$BACKEND"
if ! "$PY" manage.py check --database default; then
    printf '\n'
    aviso "Django no pudo conectarse. Lo mas probable:"
    aviso "  · Access denied      -> contrasena o usuario incorrectos"
    aviso "  · Unknown database   -> falta crear $DB_NAME en el panel"
    aviso "  · Unknown server host-> el host $DB_HOST no es el tuyo"
    aviso "Revisa $BACKEND/.env y vuelve a ejecutar: bash ~/desplegar.sh"
    exit 1
fi
ok "Conexion con MySQL correcta"

# ── 6. tablas y datos de prueba ──────────────────────────────────────────────
paso "6/8  Creando tablas y datos de prueba"

"$PY" manage.py migrate
ok "Migraciones aplicadas"

"$PY" manage.py collectstatic --noinput >/dev/null
ok "Archivos estaticos recolectados"

printf '\n'
nota "Los datos de prueba (facultades, cursos, modulos, tareas, quizzes)"
nota "BORRAN y recrean todo el contenido de la base."
read -rp "   ¿Cargar los datos de prueba? [S/n]: " SEMBRAR
if [ "${SEMBRAR,,}" != "n" ]; then
    "$PY" manage.py seed
    ok "Datos de prueba cargados"
else
    nota "Omitido"
fi

# ── 7. API publica ───────────────────────────────────────────────────────────
paso "7/8  Comprobando el arranque del sitio y la API"

# Esto es exactamente lo que hace uWSGI al levantar el sitio. Si falla aqui,
# en el panel veras "Connection to upstream failed" y en el log el traceback.
ERROR_WSGI="$(mktemp)"
if "$PY" -c 'from config.wsgi import application' 2>"$ERROR_WSGI"; then
    rm -f "$ERROR_WSGI"
    ok "config/wsgi.py carga correctamente (Python $VER_VENV)"
    nota "Django cargado desde: $("$PY" -c 'import django, os; print(os.path.dirname(django.__file__))')"

    if [ -n "$PYVER_SITIO" ] && [ "$PYVER_SITIO" != "$VER_VENV" ]; then
        aviso "OJO: el sitio del panel arranca con Python $PYVER_SITIO y este"
        aviso "entorno virtual es $VER_VENV. Cambia la Version de Python del"
        aviso "sitio a $VER_VENV o seguiras viendo 'No module named django'."
    fi
else
    printf '\n'
    sed 's/^/   /' "$ERROR_WSGI" >&2
    rm -f "$ERROR_WSGI"
    printf '\n'
    morir "El sitio no puede arrancar. Ese traceback es el que veras en ~/admin/logs/uwsgi/*.log"
fi

CLAVE_API="$(grep -m1 '^API_CLAVE=' "$BACKEND/.env" | cut -d= -f2- || true)"

if "$PY" - "$DOMINIO" <<'PYEOF'
import json
import os
import sys

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.test import Client

cliente = Client()
cabeceras = {}
if settings.API_CLAVE:
    cabeceras['x-api-key'] = settings.API_CLAVE

respuesta = cliente.get('/api/estado/', headers=cabeceras, HTTP_HOST=sys.argv[1])

if respuesta.status_code != 200:
    print(f'   La API respondio {respuesta.status_code}')
    sys.exit(1)

datos = json.loads(respuesta.content)['datos']
totales = datos.get('totales') or {}
print('   base de datos: {}  ·  cursos: {}  ·  modulos: {}'.format(
    datos['base_de_datos'], totales.get('cursos', 0), totales.get('modulos', 0),
))
PYEOF
then
    ok "La API responde correctamente"
else
    aviso "La API no respondio como se esperaba. Revisa backend/.env (API_CLAVE)."
fi

# ── 8. superusuario ──────────────────────────────────────────────────────────
paso "8/8  Creando tu usuario administrador"

printf '\n'
nota "Te pedira: correo, nombres, apellidos, identificacion, celular y contrasena."
nota "El correo es el usuario de acceso (este proyecto no usa 'username')."
printf '\n'
"$PY" manage.py createsuperuser

# ── resumen ──────────────────────────────────────────────────────────────────
printf '\n%s' "$VERDE"
printf '%s\n' "════════════════════════════════════════════════════════"
printf '%s\n' "  Parte del servidor terminada."
printf '%s\n' "════════════════════════════════════════════════════════"
printf '%s' "$FIN"

cat <<RESUMEN

Ahora, en el panel: Web → Sitios → Añadir un sitio (o editar el existente)

  Direcciones .............. $DOMINIO
  Tipo ..................... Python WSGI
  Ruta de la aplicacion .... \$HOME/www/$PROYECTO/backend/config/wsgi.py
  Directorio de trabajo .... \$HOME/www/$PROYECTO/backend
  Entorno virtual .......... \$HOME/venv-espol
  Version de Python ........ $VER_VENV      <-- tiene que coincidir

  Esa version es la del entorno virtual ($VENV). Si en el panel eliges otra,
  uWSGI arranca con un Python que no ve los paquetes y el log dira:
  "ModuleNotFoundError: No module named 'django'".

Guarda, pulsa Reiniciar, y abre:

  https://$DOMINIO/
  https://$DOMINIO/admin/
  https://$DOMINIO/api/          <-- indice de la API (JSON)

API de consulta (/api/)

  Desde el navegador, sin claves: inicia sesion en https://$DOMINIO/admin/
  con tu usuario SUPERADMIN y abre https://$DOMINIO/api/cursos/

  Desde un programa externo (no tiene sesion), con la clave:

    curl -H "X-API-Key: $CLAVE_API" https://$DOMINIO/api/estado/
    curl -H "X-API-Key: $CLAVE_API" https://$DOMINIO/api/cursos/

  Clave (X-API-Key) ........ $CLAVE_API
  Guardala: esta tambien en $BACKEND/.env. Si solo la vas a consultar
  desde el navegador, puedes dejar API_CLAVE vacia y borrarla.

Si sale "Connection to upstream failed", el detalle esta en:

  tail -50 ~/admin/logs/sites/*

La causa numero uno es que la Version de Python del sitio no sea $VER_VENV.

RESUMEN
