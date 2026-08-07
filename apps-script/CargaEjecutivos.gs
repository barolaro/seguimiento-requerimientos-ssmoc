/**
 * SGTCP 3.0 · Carga inicial de ejecutivos
 * Ejecutar UNA vez desde Apps Script.
 * Requiere Codigo.gs cargado en el mismo proyecto.
 */
function cargarEjecutivosIniciales() {
  ensureSchema_();

  const ejecutivos = [
    {usuario:'alejandra.inostroza', nombre:'ALEJANDRA SOLEDAD INOSTROZA GONZÁLEZ'},
    {usuario:'beatriz.castillo', nombre:'BEATRIZ ERIKA CASTILLO PALMA'},
    {usuario:'gonzalo.barahona', nombre:'GONZALO IGNACIO BARAHONA CASTILLO'},
    {usuario:'jaime.diaz', nombre:'JAIME DIAZ TAPIA'},
    {usuario:'marcelo.gatica', nombre:'MARCELO GATICA ESPINOSA'},
    {usuario:'monica.delpino', nombre:'MONICA CECILIA DELPINO NUÑEZ'},
    {usuario:'nancy.rifo', nombre:'NANCY DEL CARMEN RIFO PINO'},
    {usuario:'sergio.carvajal', nombre:'SERGIO ALBERTO CARVAJAL VERA'},
    {usuario:'stephanie.besnier', nombre:'STEPHANIE MONIC BESNIER UNDA'},
    {usuario:'veronica.valenzuela', nombre:'VERONICA HELENA VALENZUELA SILVA'}
  ];

  const sh = sheet_(SH_USERS, USERS_COLS);
  const existentes = readObjects_(sh).map(function(u){ return String(u.usuario || '').toLowerCase().trim(); });
  let creados = 0;
  const credenciales = [];

  ejecutivos.forEach(function(e) {
    if (existentes.indexOf(e.usuario) >= 0) {
      Logger.log('YA EXISTE: ' + e.usuario);
      return;
    }
    const temp = tempPassword_();
    appendObject_(sh, USERS_COLS, {
      usuario:e.usuario,
      nombre:e.nombre,
      email:'',
      rol:'Ejecutivo',
      password_hash:hashPassword_(temp),
      activo:'SI',
      cambiar_password:'SI',
      ultimo_acceso:'',
      creado:now_()
    });
    audit_('sistema','carga_inicial_ejecutivo','usuario',e.usuario,e.nombre);
    credenciales.push(e.usuario + ' | ' + temp);
    creados++;
  });

  Logger.log('CARGA COMPLETADA. Ejecutivos creados: ' + creados);
  Logger.log('GUARDE ESTAS CREDENCIALES TEMPORALES EN UN LUGAR SEGURO:');
  credenciales.forEach(function(x){ Logger.log(x); });
  Logger.log('Cada ejecutivo deberá cambiar su contraseña en el primer ingreso.');
}
