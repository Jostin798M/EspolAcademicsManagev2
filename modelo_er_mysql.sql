-- ==============================================================
-- ESPOL ACADEMICS v2 - Modelo Entidad-Relacion (MySQL)
-- Generado con: python manage.py sqlmigrate <app> <migracion>
-- Las tablas las crea Django con: python manage.py migrate
-- ==============================================================

-- ── APP: accounts (migracion 0001) ──────────────────────────────
--
-- Create model Usuario
--
CREATE TABLE `usuario` (`password` varchar(128) NOT NULL, `last_login` datetime(6) NULL, `is_superuser` bool NOT NULL, `id_usuario` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `nombres` varchar(100) NOT NULL, `apellidos` varchar(100) NOT NULL, `identificacion` varchar(20) NOT NULL UNIQUE, `telefono` varchar(15) NULL, `celular` varchar(15) NOT NULL, `correo` varchar(254) NOT NULL UNIQUE, `direccion` varchar(200) NULL, `estado_civil` varchar(20) NOT NULL, `estado` varchar(10) NOT NULL, `fecha_registro` date NOT NULL, `rol` varchar(15) NOT NULL, `activo` bool NOT NULL, `es_staff` bool NOT NULL);

-- ── APP: cursos (migracion 0001) ──────────────────────────────
--
-- Create model Facultad
--
CREATE TABLE `facultad` (`id_facultad` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `nombre` varchar(200) NOT NULL UNIQUE, `codigo` varchar(10) NOT NULL UNIQUE, `id_admin` bigint NULL);
--
-- Create model Curso
--
CREATE TABLE `curso` (`id_curso` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `nombre` varchar(200) NOT NULL, `codigo` varchar(20) NOT NULL UNIQUE, `descripcion` longtext NOT NULL, `fecha_inicio` date NOT NULL, `fecha_fin` date NOT NULL, `estado` varchar(10) NOT NULL, `id_profesor` bigint NOT NULL, `id_facultad` bigint NOT NULL);
--
-- Create model FormulaComponente
--
CREATE TABLE `formula_componente` (`id_componente` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `componente` varchar(100) NOT NULL, `porcentaje` smallint UNSIGNED NOT NULL CHECK (`porcentaje` >= 0), `orden` smallint UNSIGNED NOT NULL CHECK (`orden` >= 0), `id_curso` bigint NOT NULL);
--
-- Create model Inscripcion
--
CREATE TABLE `inscripcion` (`id_inscripcion` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `rol_en_curso` varchar(15) NOT NULL, `fecha` date NOT NULL, `id_curso` bigint NOT NULL, `id_usuario` bigint NOT NULL);
--
-- Create model Modulo
--
CREATE TABLE `modulo` (`id_modulo` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `titulo` varchar(200) NOT NULL, `descripcion` longtext NULL, `orden` smallint UNSIGNED NOT NULL CHECK (`orden` >= 0), `id_curso` bigint NOT NULL);
--
-- Create model Material
--
CREATE TABLE `material` (`id_material` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `tipo` varchar(10) NOT NULL, `titulo` varchar(200) NOT NULL, `url` varchar(200) NOT NULL, `id_modulo` bigint NOT NULL);
--
-- Create model ProgresoModulo
--
CREATE TABLE `progreso_modulo` (`id_progreso` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `completado` bool NOT NULL, `fecha` date NOT NULL, `id_modulo` bigint NOT NULL, `id_usuario` bigint NOT NULL);
--
-- Create constraint ck_curso_fechas_coherentes on model curso
--
ALTER TABLE `curso` ADD CONSTRAINT `ck_curso_fechas_coherentes` CHECK (`fecha_fin` >= (`fecha_inicio`));
--
-- Create constraint uq_formula_curso_componente on model formulacomponente
--
ALTER TABLE `formula_componente` ADD CONSTRAINT `uq_formula_curso_componente` UNIQUE (`id_curso`, `componente`);
--
-- Create constraint ck_formula_porcentaje_valido on model formulacomponente
--
ALTER TABLE `formula_componente` ADD CONSTRAINT `ck_formula_porcentaje_valido` CHECK ((`porcentaje` >= 1 AND `porcentaje` <= 100));
--
-- Create constraint uq_inscripcion_usuario_curso on model inscripcion
--
ALTER TABLE `inscripcion` ADD CONSTRAINT `uq_inscripcion_usuario_curso` UNIQUE (`id_usuario`, `id_curso`);
--
-- Create constraint uq_modulo_curso_orden on model modulo
--
ALTER TABLE `modulo` ADD CONSTRAINT `uq_modulo_curso_orden` UNIQUE (`id_curso`, `orden`);
--
-- Create constraint ck_modulo_orden_positivo on model modulo
--
ALTER TABLE `modulo` ADD CONSTRAINT `ck_modulo_orden_positivo` CHECK (`orden` >= 1);
--
-- Create constraint uq_progreso_usuario_modulo on model progresomodulo
--
ALTER TABLE `progreso_modulo` ADD CONSTRAINT `uq_progreso_usuario_modulo` UNIQUE (`id_usuario`, `id_modulo`);
ALTER TABLE `facultad` ADD CONSTRAINT `facultad_id_admin_ea13e815_fk_usuario_id_usuario` FOREIGN KEY (`id_admin`) REFERENCES `usuario` (`id_usuario`);
ALTER TABLE `curso` ADD CONSTRAINT `curso_id_profesor_675deeaf_fk_usuario_id_usuario` FOREIGN KEY (`id_profesor`) REFERENCES `usuario` (`id_usuario`);
ALTER TABLE `curso` ADD CONSTRAINT `curso_id_facultad_59dd0021_fk_facultad_id_facultad` FOREIGN KEY (`id_facultad`) REFERENCES `facultad` (`id_facultad`);
ALTER TABLE `formula_componente` ADD CONSTRAINT `formula_componente_id_curso_6f23612b_fk_curso_id_curso` FOREIGN KEY (`id_curso`) REFERENCES `curso` (`id_curso`);
ALTER TABLE `inscripcion` ADD CONSTRAINT `inscripcion_id_curso_e77308cb_fk_curso_id_curso` FOREIGN KEY (`id_curso`) REFERENCES `curso` (`id_curso`);
ALTER TABLE `inscripcion` ADD CONSTRAINT `inscripcion_id_usuario_d04b5076_fk_usuario_id_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`);
ALTER TABLE `modulo` ADD CONSTRAINT `modulo_id_curso_81ae1ce6_fk_curso_id_curso` FOREIGN KEY (`id_curso`) REFERENCES `curso` (`id_curso`);
ALTER TABLE `material` ADD CONSTRAINT `material_id_modulo_3fd5ac3f_fk_modulo_id_modulo` FOREIGN KEY (`id_modulo`) REFERENCES `modulo` (`id_modulo`);
ALTER TABLE `progreso_modulo` ADD CONSTRAINT `progreso_modulo_id_modulo_30e9fe4b_fk_modulo_id_modulo` FOREIGN KEY (`id_modulo`) REFERENCES `modulo` (`id_modulo`);
ALTER TABLE `progreso_modulo` ADD CONSTRAINT `progreso_modulo_id_usuario_99b65703_fk_usuario_id_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`);

-- ── APP: accounts (migracion 0002) ──────────────────────────────
--
-- Add field facultad to usuario
--
ALTER TABLE `usuario` ADD COLUMN `id_facultad` bigint NULL , ADD CONSTRAINT `usuario_id_facultad_e6bf5076_fk_facultad_id_facultad` FOREIGN KEY (`id_facultad`) REFERENCES `facultad`(`id_facultad`);
--
-- Add field groups to usuario
--
CREATE TABLE `usuario_groups` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `usuario_id` bigint NOT NULL, `group_id` integer NOT NULL);
--
-- Add field user_permissions to usuario
--
CREATE TABLE `usuario_user_permissions` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `usuario_id` bigint NOT NULL, `permission_id` integer NOT NULL);
ALTER TABLE `usuario_groups` ADD CONSTRAINT `usuario_groups_usuario_id_group_id_2e3cd638_uniq` UNIQUE (`usuario_id`, `group_id`);
ALTER TABLE `usuario_groups` ADD CONSTRAINT `usuario_groups_usuario_id_161fc80c_fk_usuario_id_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuario` (`id_usuario`);
ALTER TABLE `usuario_groups` ADD CONSTRAINT `usuario_groups_group_id_c67c8651_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`);
ALTER TABLE `usuario_user_permissions` ADD CONSTRAINT `usuario_user_permissions_usuario_id_permission_id_3db58b8c_uniq` UNIQUE (`usuario_id`, `permission_id`);
ALTER TABLE `usuario_user_permissions` ADD CONSTRAINT `usuario_user_permiss_usuario_id_693d9c50_fk_usuario_i` FOREIGN KEY (`usuario_id`) REFERENCES `usuario` (`id_usuario`);
ALTER TABLE `usuario_user_permissions` ADD CONSTRAINT `usuario_user_permiss_permission_id_a8893ce7_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`);

-- ── APP: evaluaciones (migracion 0001) ──────────────────────────────
--
-- Create model Quiz
--
CREATE TABLE `quiz` (`id_quiz` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `titulo` varchar(200) NOT NULL, `descripcion` longtext NULL, `tiempo_limite_min` smallint UNSIGNED NULL CHECK (`tiempo_limite_min` >= 0), `fecha_limite` datetime(6) NOT NULL, `id_curso` bigint NOT NULL);
--
-- Create model Pregunta
--
CREATE TABLE `pregunta` (`id_pregunta` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `tipo` varchar(30) NOT NULL, `enunciado` longtext NOT NULL, `puntaje` numeric(10, 2) NOT NULL, `orden` smallint UNSIGNED NOT NULL CHECK (`orden` >= 0), `opciones` json NOT NULL, `respuesta_correcta` json NULL, `id_quiz` bigint NOT NULL);
--
-- Create model RespuestaQuiz
--
CREATE TABLE `respuesta_quiz` (`id_respuesta_quiz` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `respuestas` json NOT NULL, `nota_automatica` numeric(10, 2) NOT NULL, `nota_manual` numeric(10, 2) NULL, `fecha` datetime(6) NOT NULL, `id_quiz` bigint NOT NULL, `id_usuario` bigint NOT NULL);
--
-- Create model Tarea
--
CREATE TABLE `tarea` (`id_tarea` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `titulo` varchar(200) NOT NULL, `descripcion` longtext NOT NULL, `criterios` longtext NULL, `fecha_limite` datetime(6) NOT NULL, `puntaje_maximo` numeric(10, 2) NOT NULL, `id_curso` bigint NOT NULL);
--
-- Create model Entrega
--
CREATE TABLE `entrega` (`id_entrega` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `estado` varchar(15) NOT NULL, `fecha` datetime(6) NULL, `texto` longtext NULL, `archivo` varchar(300) NULL, `imagen` varchar(200) NULL, `link` varchar(200) NULL, `nota` numeric(10, 2) NULL, `comentario` longtext NULL, `id_usuario` bigint NOT NULL, `id_tarea` bigint NOT NULL);
--
-- Create constraint uq_quiz_curso_titulo on model quiz
--
ALTER TABLE `quiz` ADD CONSTRAINT `uq_quiz_curso_titulo` UNIQUE (`id_curso`, `titulo`);
--
-- Create constraint ck_pregunta_puntaje_no_negativo on model pregunta
--
ALTER TABLE `pregunta` ADD CONSTRAINT `ck_pregunta_puntaje_no_negativo` CHECK (`puntaje` >= 0);
--
-- Create constraint uq_respuesta_quiz_usuario on model respuestaquiz
--
ALTER TABLE `respuesta_quiz` ADD CONSTRAINT `uq_respuesta_quiz_usuario` UNIQUE (`id_quiz`, `id_usuario`);
--
-- Create constraint ck_respuesta_quiz_nota_auto_no_negativa on model respuestaquiz
--
ALTER TABLE `respuesta_quiz` ADD CONSTRAINT `ck_respuesta_quiz_nota_auto_no_negativa` CHECK (`nota_automatica` >= 0);
--
-- Create constraint ck_respuesta_quiz_nota_manual_no_negativa on model respuestaquiz
--
ALTER TABLE `respuesta_quiz` ADD CONSTRAINT `ck_respuesta_quiz_nota_manual_no_negativa` CHECK ((`nota_manual` IS NULL OR `nota_manual` >= 0));
--
-- Create constraint uq_tarea_curso_titulo on model tarea
--
ALTER TABLE `tarea` ADD CONSTRAINT `uq_tarea_curso_titulo` UNIQUE (`id_curso`, `titulo`);
--
-- Create constraint ck_tarea_puntaje_no_negativo on model tarea
--
ALTER TABLE `tarea` ADD CONSTRAINT `ck_tarea_puntaje_no_negativo` CHECK (`puntaje_maximo` >= 0);
--
-- Create constraint uq_entrega_tarea_usuario on model entrega
--
ALTER TABLE `entrega` ADD CONSTRAINT `uq_entrega_tarea_usuario` UNIQUE (`id_tarea`, `id_usuario`);
--
-- Create constraint ck_entrega_nota_no_negativa on model entrega
--
ALTER TABLE `entrega` ADD CONSTRAINT `ck_entrega_nota_no_negativa` CHECK ((`nota` IS NULL OR `nota` >= 0));
ALTER TABLE `quiz` ADD CONSTRAINT `quiz_id_curso_5f96f3f1_fk_curso_id_curso` FOREIGN KEY (`id_curso`) REFERENCES `curso` (`id_curso`);
ALTER TABLE `pregunta` ADD CONSTRAINT `pregunta_id_quiz_7f1f81da_fk_quiz_id_quiz` FOREIGN KEY (`id_quiz`) REFERENCES `quiz` (`id_quiz`);
ALTER TABLE `respuesta_quiz` ADD CONSTRAINT `respuesta_quiz_id_quiz_8da3002f_fk_quiz_id_quiz` FOREIGN KEY (`id_quiz`) REFERENCES `quiz` (`id_quiz`);
ALTER TABLE `respuesta_quiz` ADD CONSTRAINT `respuesta_quiz_id_usuario_9b4f0132_fk_usuario_id_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`);
ALTER TABLE `tarea` ADD CONSTRAINT `tarea_id_curso_0d25225a_fk_curso_id_curso` FOREIGN KEY (`id_curso`) REFERENCES `curso` (`id_curso`);
ALTER TABLE `entrega` ADD CONSTRAINT `entrega_id_usuario_d93b5124_fk_usuario_id_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`);
ALTER TABLE `entrega` ADD CONSTRAINT `entrega_id_tarea_606578d6_fk_tarea_id_tarea` FOREIGN KEY (`id_tarea`) REFERENCES `tarea` (`id_tarea`);
