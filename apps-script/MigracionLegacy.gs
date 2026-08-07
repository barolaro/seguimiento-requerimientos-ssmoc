/**
 * Migración de una cuenta administrativa heredada hacia SGTCP 3.0.
 * Ejecutar UNA sola vez desde el editor de Apps Script.
 *
 * Requiere que Codigo.gs esté instalado en el mismo proyecto.
 */
function migrarAdministradorLegacy() {
  ensureSchema_();

  const sh = sheet_(SH_USERS, USERS_COLS);
  const users = readObjects_(sh);
  let user = users.find(function(u) {
    return String(u.usuario || '').toLowerCase().trim() === 'admin';
  });

  if (!user) {
    user = users.find(function(u) {
      return String(u.rol || '').toLowerCase().trim() === 'administrador';
    });
  }

  if (!user) {
    Logger.log('No se encontró un administrador heredado. No se realizaron cambios.');
    return;
  }

  const temp = tempPassword_();
  updateRowByKey_(sh, USERS_COLS, 'usuario', user.usuario, {
    nombre: String(user.nombre || 'Administrador Abastecimiento'),
    rol: 'Administrador',
    password_hash: hashPassword_(temp),
    activo: 'SI',
    cambiar_password: 'SI',
    ultimo_acceso: '',
    creado: user.creado || now_()
  });

  audit_('sistema', 'migrar_administrador_legacy', 'usuario', String(user.usuario), 'Cuenta migrada al esquema SGTCP 3.0');

  Logger.log('MIGRACIÓN COMPLETADA');
  Logger.log('USUARIO: ' + user.usuario);
  Logger.log('CONTRASEÑA TEMPORAL: ' + temp);
  Logger.log('El sistema solicitará cambiar esta contraseña en el primer ingreso.');
}
