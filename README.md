# Texas Hold'em Poker

Motor inicial de Texas Hold'em en Python puro con una interfaz Flask local basica.

## Incluye

- Cartas y baraja de 52 cartas unicas.
- Jugadores con fichas, cartas privadas, fold y all-in basico.
- Evaluador de manos de 5 a 7 cartas.
- Flujo de mano: preflop, flop, turn, river y showdown.
- Blinds, bote y acciones basicas: fold, check, call y raise.
- Registro de contribuciones totales por jugador durante la mano.
- All-in avanzado con revelado automatico cuando ya no hay accion posible.
- Side pots para repartir botes principal y secundarios.
- Control de turnos con jugadores que ya actuaron por ronda.
- Acciones disponibles por jugador con `available_actions()`.
- Avance automatico con `advance_if_ready()`.
- Estado publico y privado serializable para futura interfaz.
- Historial simple de acciones.
- Demo por consola.
- Modo consola interactivo con `console_game.py`.
- Interfaz Flask local con formularios HTML.
- Cartas visuales con simbolos de palo y colores.
- Acciones web en espanol y ayuda de turno.
- Mesa responsive con jugador actual destacado.
- Multiplayer local inicial con Flask-SocketIO.
- Salas en memoria para crear/unirse e iniciar partida.
- Emision segura de estado publico y cartas privadas por jugador.
- Pruebas unitarias del motor.

## Instalar dependencias

```bash
pip install -r requirements.txt
```

## Ejecutar pruebas

```bash
python -m pytest
```

## Ejecutar demo

```bash
python demo.py
```

## Jugar por consola

```bash
python console_game.py
```

Comandos aceptados durante el turno:

- `fold` o `f`
- `check` o `k`
- `call` o `c`
- `raise 20` o `r 20`

## Jugar en navegador

```bash
python app.py
```

Luego abre:

```text
http://127.0.0.1:5000
```

La version Flask usa una sola partida en memoria. Si reinicias el servidor, la partida se pierde.

## Probar multiplayer local

```bash
python app.py
```

Abre el lobby multiplayer:

```text
http://127.0.0.1:5000/multiplayer
```

Para probar desde otro dispositivo de la misma red, usa la IP local de tu PC:

```text
http://TU-IP-LOCAL:5000/multiplayer
```

Estado actual del multiplayer:

- Crear sala.
- Unirse por codigo.
- Host de sala con permisos para iniciar partida y nueva mano.
- Ver jugadores conectados.
- Iniciar partida con 2 a 6 jugadores.
- Recibir estado publico y cartas privadas de forma separada.
- Ejecutar acciones en tiempo real.
- Actualizar la mesa automaticamente en todos los clientes.
- Mostrar resultado final cuando termina la mano.
- Iniciar nueva mano manteniendo fichas.
- Reconexion basica con el mismo nombre.
- Reasignacion de host si el host se desconecta.
- Marcar desconexiones y hacer fold automatico si se desconecta el jugador en turno.
- Limpieza de salas sin jugadores conectados.

Pendiente del multiplayer:

- Persistencia de salas si se reinicia el servidor.
- Usuarios con login.

## Pendiente Para Fases Futuras

- WebSockets y multiplayer online.
- Usuarios, salas, estadisticas y persistencia.
