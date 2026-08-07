/**
 * SGTCP 3.0 · Backend Google Apps Script
 * Servicio de Salud Metropolitano Occidente
 *
 * Este archivo se pega en Extensiones > Apps Script de la planilla de producción
 * y se publica como Aplicación web (ejecutar como: Yo).
 *
 * Seguridad:
 * - No existe token maestro en el HTML.
 * - Login genera una sesión temporal aleatoria.
 * - Cada acción valida sesión, usuario activo y rol.
 * - Contraseñas se guard