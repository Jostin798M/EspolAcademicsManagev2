"""
Paquete de configuracion del proyecto.

Driver de MySQL:
  - Por defecto se usa mysqlclient (el driver recomendado por Django).
  - Si el servidor no puede compilarlo, se usa PyMySQL como reemplazo.
  - Con DB_DRIVER=pymysql se fuerza el uso de PyMySQL.
"""
import os


def _usar_pymysql():
    import pymysql

    pymysql.install_as_MySQLdb()

    # Django exige mysqlclient >= 2.2.1; PyMySQL implementa la misma
    # interfaz pero se identifica con su propia numeracion.
    import MySQLdb

    MySQLdb.version_info = (2, 2, 1, 'final', 0)
    MySQLdb.__version__ = '2.2.1'


if os.environ.get('DB_DRIVER', '').strip().lower() == 'pymysql':
    try:
        _usar_pymysql()
    except ImportError:
        pass
else:
    try:
        import MySQLdb  # noqa: F401
    except ImportError:
        try:
            _usar_pymysql()
        except ImportError:
            pass
