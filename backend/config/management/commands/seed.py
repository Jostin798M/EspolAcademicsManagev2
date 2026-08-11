"""
python manage.py seed

Carga en la base de datos los mismos registros de prueba que usa el
frontend en js/data/mockdata.js.
"""
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from accounts.models import Usuario
from cursos.models import (
    Curso,
    Facultad,
    FormulaComponente,
    Inscripcion,
    Material,
    Modulo,
    ProgresoModulo,
)
from evaluaciones.models import Entrega, Pregunta, Quiz, RespuestaQuiz, Tarea


class Command(BaseCommand):
    help = 'Poblar la base de datos con los datos de prueba del frontend'

    def add_arguments(self, parser):
        parser.add_argument(
            '--if-empty',
            action='store_true',
            help='Solo sembrar si no existen usuarios (no borra datos existentes).',
        )

    def handle(self, *args, **options):
        if options.get('if_empty') and Usuario.objects.exists():
            self.stdout.write('La base de datos ya tiene datos; se omite el sembrado.')
            return

        self.stdout.write('Limpiando datos anteriores...')
        # El orden respeta las claves foraneas configuradas con PROTECT
        RespuestaQuiz.objects.all().delete()
        Pregunta.objects.all().delete()
        Quiz.objects.all().delete()
        Entrega.objects.all().delete()
        Tarea.objects.all().delete()
        ProgresoModulo.objects.all().delete()
        Material.objects.all().delete()
        Modulo.objects.all().delete()
        Inscripcion.objects.all().delete()
        FormulaComponente.objects.all().delete()
        Curso.objects.all().delete()
        Usuario.objects.all().update(facultad=None)
        Facultad.objects.all().update(admin=None)
        Facultad.objects.all().delete()
        Usuario.objects.all().delete()

        # ── USUARIOS ──────────────────────────────────────────
        self.stdout.write('Creando usuarios...')
        carlos = Usuario.objects.create_user(
            correo='carlos.mendoza@espol.edu.ec', password='admin123',
            nombres='Carlos Alberto', apellidos='Mendoza Rios',
            identificacion='0912345678', telefono='042123456', celular='0991234567',
            direccion='Cdla. Kennedy Norte',
            estado_civil=Usuario.EstadoCivil.CASADO, rol=Usuario.Rol.SUPERADMIN,
        )
        maria = Usuario.objects.create_user(
            correo='maria.torres@espol.edu.ec', password='admin123',
            nombres='Maria Elena', apellidos='Torres Vega',
            identificacion='0923456789', celular='0987654321',
            estado_civil=Usuario.EstadoCivil.SOLTERO, rol=Usuario.Rol.ADMIN,
        )
        roberto = Usuario.objects.create_user(
            correo='roberto.llerena@espol.edu.ec', password='user123',
            nombres='Roberto', apellidos='Llerena Castillo',
            identificacion='0934567890', telefono='042987654', celular='0976543210',
            direccion='Urdesa Central',
            estado_civil=Usuario.EstadoCivil.DIVORCIADO, rol=Usuario.Rol.USER,
        )
        ana = Usuario.objects.create_user(
            correo='ana.paredes@espol.edu.ec', password='user123',
            nombres='Ana Lucia', apellidos='Paredes Suarez',
            identificacion='0945678901', celular='0965432109',
            estado_civil=Usuario.EstadoCivil.SOLTERO, rol=Usuario.Rol.USER,
        )
        diego = Usuario.objects.create_user(
            correo='diego.ochoa@espol.edu.ec', password='user123',
            nombres='Diego Fernando', apellidos='Ochoa Mora',
            identificacion='0956789012', telefono='042111222', celular='0954321098',
            direccion='Los Ceibos',
            estado_civil=Usuario.EstadoCivil.SOLTERO, rol=Usuario.Rol.USER,
            estado=Usuario.Estado.INACTIVO,
        )
        diego.is_active = False
        diego.save(update_fields=['is_active'])

        # El SUPERADMIN entra al panel de Django y al panel CRUD
        carlos.is_staff = True
        carlos.is_superuser = True
        carlos.save(update_fields=['is_staff', 'is_superuser'])

        # ── FACULTADES ────────────────────────────────────────
        self.stdout.write('Creando facultades...')
        fiec = Facultad.objects.create(
            codigo='FIEC',
            nombre='Facultad de Ingenieria en Electricidad y Computacion',
            admin=maria,
        )
        fcnm = Facultad.objects.create(
            codigo='FCNM',
            nombre='Facultad de Ciencias Naturales y Matematicas',
        )
        Facultad.objects.create(
            codigo='FIMCP',
            nombre='Facultad de Ingenieria Mecanica y Ciencias de la Produccion',
        )

        maria.facultad = fiec
        maria.save(update_fields=['facultad'])

        # ── CURSOS Y FORMULA ──────────────────────────────────
        self.stdout.write('Creando cursos...')
        cursos_data = [
            ('Desarrollo de Aplicaciones Web y Moviles', 'DAWM-2026A',
             'Curso de desarrollo frontend, backend, APIs y aplicaciones moviles.',
             fiec, '2026-03-01', '2026-07-31', Curso.Estado.ACTIVO,
             [('Tareas', 40), ('Quizzes', 30), ('Proyecto Final', 30)]),
            ('Estructuras de Datos', 'ED-2026A',
             'Algoritmos, listas, arboles, grafos y complejidad computacional.',
             fiec, '2026-03-01', '2026-07-31', Curso.Estado.ACTIVO,
             [('Tareas', 50), ('Examenes', 50)]),
            ('Calculo Diferencial', 'CD-2025B',
             'Limites, derivadas y aplicaciones del calculo.',
             fcnm, '2025-08-01', '2025-12-15', Curso.Estado.ARCHIVADO,
             [('Quizzes', 30), ('Examenes', 70)]),
        ]

        cursos = {}
        for nombre, codigo, desc, fac, inicio, fin, estado, formula in cursos_data:
            curso = Curso.objects.create(
                nombre=nombre, codigo=codigo, descripcion=desc,
                facultad=fac, profesor=roberto,
                fecha_inicio=inicio, fecha_fin=fin, estado=estado,
            )
            cursos[codigo] = curso

            for orden, (componente, porcentaje) in enumerate(formula):
                FormulaComponente.objects.create(
                    curso=curso, componente=componente,
                    porcentaje=porcentaje, orden=orden,
                )

        dawm = cursos['DAWM-2026A']
        ed = cursos['ED-2026A']

        # ── INSCRIPCIONES ─────────────────────────────────────
        self.stdout.write('Creando inscripciones...')
        for usuario, curso, rol in [
            (ana, dawm, Inscripcion.RolEnCurso.ESTUDIANTE),
            (diego, dawm, Inscripcion.RolEnCurso.ESTUDIANTE),
            (roberto, dawm, Inscripcion.RolEnCurso.PROFESOR),
            (ana, ed, Inscripcion.RolEnCurso.ESTUDIANTE),
            (roberto, ed, Inscripcion.RolEnCurso.PROFESOR),
        ]:
            Inscripcion.objects.create(usuario=usuario, curso=curso, rol_en_curso=rol)

        # ── MODULOS Y MATERIALES ──────────────────────────────
        self.stdout.write('Creando modulos y materiales...')
        m1 = Modulo.objects.create(
            curso=dawm, orden=1, titulo='Introduccion al Desarrollo Web',
            descripcion='Conceptos basicos de HTML, CSS y el ecosistema web.',
        )
        m2 = Modulo.objects.create(
            curso=dawm, orden=2, titulo='CSS Moderno y Responsive Design',
            descripcion='Flexbox, Grid, Bootstrap y diseno adaptativo.',
        )
        m3 = Modulo.objects.create(
            curso=dawm, orden=3, titulo='JavaScript Fundamentos',
            descripcion='Variables, funciones, DOM y eventos.',
        )
        Modulo.objects.create(
            curso=ed, orden=1, titulo='Complejidad Algoritmica',
            descripcion='Notacion Big O, analisis de algoritmos.',
        )

        materiales = [
            (m1, Material.Tipo.VIDEO, 'Que es la web y como funciona',
             'https://www.youtube.com/watch?v=example1'),
            (m1, Material.Tipo.PDF, 'Guia de referencia HTML5',
             'https://drive.google.com/file/example1'),
            (m2, Material.Tipo.VIDEO, 'Flexbox en 20 minutos',
             'https://www.youtube.com/watch?v=example2'),
            (m2, Material.Tipo.PDF, 'Cheatsheet Bootstrap 5',
             'https://drive.google.com/file/example2'),
            (m3, Material.Tipo.VIDEO, 'JavaScript desde cero',
             'https://www.youtube.com/watch?v=example3'),
        ]
        for modulo, tipo, titulo, url in materiales:
            Material.objects.create(modulo=modulo, tipo=tipo, titulo=titulo, url=url)

        # ── PROGRESO ──────────────────────────────────────────
        self.stdout.write('Creando progreso...')
        for modulo, completado in [(m1, True), (m2, True), (m3, False)]:
            ProgresoModulo.objects.create(usuario=ana, modulo=modulo, completado=completado)

        # ── TAREAS Y ENTREGAS ─────────────────────────────────
        self.stdout.write('Creando tareas y entregas...')
        t1 = Tarea.objects.create(
            curso=dawm, titulo='Pagina HTML estatica',
            descripcion='Crear una pagina web con estructura semantica correcta usando HTML5.',
            criterios='Uso correcto de etiquetas semanticas, estructura valida, al menos 3 secciones.',
            fecha_limite=parse_datetime('2026-04-10T23:59'), puntaje_maximo=10,
        )
        t2 = Tarea.objects.create(
            curso=dawm, titulo='Diseno responsive con Bootstrap',
            descripcion='Adaptar la pagina del ejercicio anterior usando el grid de Bootstrap 5.',
            criterios='Uso del sistema de grid, responsive en movil y escritorio.',
            fecha_limite=parse_datetime('2026-04-25T23:59'), puntaje_maximo=10,
        )

        Entrega.objects.create(
            tarea=t1, usuario=ana, estado=Entrega.Estado.ENTREGADO,
            fecha=parse_datetime('2026-04-09T18:30'),
            texto='Adjunto mi pagina HTML con las secciones solicitadas.',
            archivo='tarea1_ana.html', nota=9.0,
            comentario='Buen trabajo, falta atributo alt en las imagenes.',
        )
        Entrega.objects.create(tarea=t1, usuario=diego, estado=Entrega.Estado.PENDIENTE)
        Entrega.objects.create(
            tarea=t2, usuario=ana, estado=Entrega.Estado.ENTREGADO,
            fecha=parse_datetime('2026-04-24T20:10'),
            archivo='tarea2_ana.zip',
        )

        # ── QUIZ, PREGUNTAS Y RESPUESTAS ──────────────────────
        self.stdout.write('Creando quizzes...')
        quiz = Quiz.objects.create(
            curso=dawm, titulo='Quiz — HTML y CSS',
            descripcion='Evaluacion de conocimientos basicos del modulo 1 y 2.',
            tiempo_limite_min=20,
            fecha_limite=parse_datetime('2026-04-15T23:59'),
        )

        p1 = Pregunta.objects.create(
            quiz=quiz, orden=1, tipo=Pregunta.Tipo.OPCION_MULTIPLE_UNA,
            enunciado='Cual etiqueta define el titulo principal de una pagina?',
            puntaje=2, opciones=['<h1>', '<title>', '<header>', '<main>'],
            respuesta_correcta=0,
        )
        p2 = Pregunta.objects.create(
            quiz=quiz, orden=2, tipo=Pregunta.Tipo.VERDADERO_FALSO,
            enunciado='CSS Grid es una tecnica de diseno bidimensional.',
            puntaje=2, respuesta_correcta=True,
        )
        p3 = Pregunta.objects.create(
            quiz=quiz, orden=3, tipo=Pregunta.Tipo.COMPLETAR_ESPACIOS,
            enunciado='La propiedad ___ de flexbox alinea elementos en el eje principal.',
            puntaje=3, respuesta_correcta='justify-content',
        )
        p4 = Pregunta.objects.create(
            quiz=quiz, orden=4, tipo=Pregunta.Tipo.RESPUESTA_CORTA,
            enunciado='Explica la diferencia entre margin y padding.',
            puntaje=3, respuesta_correcta=None,
        )

        RespuestaQuiz.objects.create(
            quiz=quiz, usuario=ana,
            respuestas=[
                {'pregunta_id': p1.pk, 'valor': 0},
                {'pregunta_id': p2.pk, 'valor': True},
                {'pregunta_id': p3.pk, 'valor': 'justify-content'},
                {'pregunta_id': p4.pk,
                 'valor': 'Margin es el espacio exterior y padding el interior.'},
            ],
            nota_automatica=7,
        )

        self.stdout.write(self.style.SUCCESS('Seed completado exitosamente.'))
        self.stdout.write('Credenciales de prueba:')
        self.stdout.write('  SuperAdmin: carlos.mendoza@espol.edu.ec / admin123')
        self.stdout.write('  Admin:      maria.torres@espol.edu.ec   / admin123')
        self.stdout.write('  Profesor:   roberto.llerena@espol.edu.ec / user123')
        self.stdout.write('  Estudiante: ana.paredes@espol.edu.ec    / user123')
