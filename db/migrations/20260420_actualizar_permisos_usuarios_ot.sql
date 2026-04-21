-- Actualiza los permisos en la tabla usuario reemplazando el valor antiguo 'ordenes' por el nuevo 'ordenes_trabajo'
-- Esto asegura que los usuarios que tenían acceso al módulo lo mantengan tras el refactor.

UPDATE usuario
SET permisos_ver = REPLACE(permisos_ver::text, '"ordenes"', '"ordenes_trabajo"')::json
WHERE permisos_ver::text LIKE '%"ordenes"%';

UPDATE usuario
SET permisos_crear = REPLACE(permisos_crear::text, '"ordenes"', '"ordenes_trabajo"')::json
WHERE permisos_crear::text LIKE '%"ordenes"%';

UPDATE usuario
SET permisos_editar = REPLACE(permisos_editar::text, '"ordenes"', '"ordenes_trabajo"')::json
WHERE permisos_editar::text LIKE '%"ordenes"%';

UPDATE usuario
SET permisos_eliminar = REPLACE(permisos_eliminar::text, '"ordenes"', '"ordenes_trabajo"')::json
WHERE permisos_eliminar::text LIKE '%"ordenes"%';
