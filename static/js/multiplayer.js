const socket = io()

const suits = {
  h: { symbol: "♥", color: "red" },
  d: { symbol: "♦", color: "red" },
  c: { symbol: "♣", color: "black" },
  s: { symbol: "♠", color: "black" },
}

const actionLabels = {
  fold: "Retirarse",
  check: "Pasar",
  call: "Igualar",
  raise: "Subir",
}

let joinedRoomCode = null
let latestPublicState = null
let isCurrentClientHost = false

function byId(id) {
  return document.getElementById(id)
}

function setText(id, text) {
  const element = byId(id)
  if (element) element.textContent = text
}

function showError(message) {
  const error = byId("room-error")
  if (!error) return
  error.textContent = message
  error.classList.remove("hidden")
}

function clearError() {
  const error = byId("room-error")
  if (!error) return
  error.textContent = ""
  error.classList.add("hidden")
}

function showNotice(message) {
  const notice = byId("room-notice")
  if (!notice) return
  notice.textContent = message
  notice.classList.remove("hidden")
}

function cardHtml(code, extraClass = "") {
  const rank = code[0]
  const suit = suits[code[1].toLowerCase()]
  return `<span class="playing-card ${extraClass} ${suit.color}" title="${code}"><span class="card-rank">${rank}</span><span class="card-suit">${suit.symbol}</span></span>`
}

function renderCards(targetId, cards, emptyText) {
  const target = byId(targetId)
  if (!target) return
  target.innerHTML = cards.length ? cards.map((card) => cardHtml(card)).join("") : `<span class="muted">${emptyText}</span>`
}

function renderRoom(room) {
  if (!room) return
  joinedRoomCode = room.code
  const list = byId("room-players")
  if (list) {
    list.innerHTML = room.players.map((player) => `
      <article class="player-seat ${player.connected ? "" : "is-folded"} ${player.is_host ? "is-current" : ""}">
        <h3>${player.name}</h3>
        <p>Asiento ${player.player_index + 1}</p>
        <p>${player.connected ? "Conectado" : "Desconectado"}${player.is_host ? " · Host" : ""}</p>
      </article>
    `).join("")
  }
  const storedName = window.sessionStorage.getItem(`room:${room.code}:name`)
  const ownSeat = room.players.find((player) => player.name === storedName)
  isCurrentClientHost = Boolean(ownSeat?.is_host)
  const startButton = byId("start-game")
  if (startButton) {
    startButton.classList.toggle("hidden", !(isCurrentClientHost && room.players.length >= 2 && !room.started))
  }
  const joinPanel = byId("join-panel")
  if (joinPanel && room.started) joinPanel.classList.add("hidden")
}

function renderState(payload) {
  renderRoom(payload.room)
  const publicState = payload.public
  const privateState = payload.private
  latestPublicState = publicState
  const newHandButton = byId("start-new-hand")
  if (newHandButton) {
    newHandButton.classList.toggle("hidden", !(isCurrentClientHost && publicState.stage === "finished"))
  }
  setText("mp-pot", publicState.pot)
  setText("mp-turn", publicState.current_player ? `Turno de ${publicState.current_player}` : "Partida finalizada")
  setText("mp-stage", `Etapa: ${publicState.stage} · Apuesta actual: ${publicState.current_bet}`)
  const raiseInput = byId("mp-raise-amount")
  if (raiseInput) {
    raiseInput.value = publicState.minimum_raise
    raiseInput.min = publicState.minimum_raise
  }
  renderCards("mp-community", publicState.community_cards, "Aun no hay cartas comunitarias")
  renderCards("mp-hole-cards", privateState.hole_cards, "Tus cartas apareceran al iniciar")

  const players = byId("mp-players")
  if (players) {
    players.innerHTML = publicState.players.map((player) => `
      <article class="player-seat ${player.name === publicState.current_player ? "is-current" : ""} ${player.folded ? "is-folded" : ""} ${player.all_in ? "is-all-in" : ""}">
        <h3>${player.name}</h3>
        <p>${player.chips} fichas</p>
        <p>Apuesta: ${player.current_bet} · Total: ${player.total_bet}</p>
        <p>${player.folded ? "Fold" : player.all_in ? "All-in" : "Activo"}</p>
      </article>
    `).join("")
  }

  const actions = byId("mp-actions")
  if (actions) {
    actions.innerHTML = privateState.available_actions.map((action) => `
      <button class="action-button action-${action}" data-action="${action}" type="button">${actionLabels[action] || action}</button>
    `).join("")
  }
  const raiseLabel = byId("mp-raise-label")
  if (raiseLabel) {
    raiseLabel.classList.toggle("hidden", !privateState.available_actions.includes("raise"))
  }

  const log = byId("mp-log")
  if (log) {
    log.innerHTML = publicState.action_log.length ? publicState.action_log.map((entry) => `
      <li>${entry.stage} · ${entry.player} hizo ${entry.action}${entry.action === "raise" ? ` ${entry.amount}` : ""}</li>
    `).join("") : "<li>Sin acciones todavia.</li>"
  }
}

function renderFinished(payload) {
  const result = byId("mp-result")
  if (!result) return
  result.classList.remove("hidden")
  result.innerHTML = `
    <p class="eyebrow">Partida finalizada</p>
    <h2>Resultado</h2>
    <div class="winner-grid">
      ${payload.winners.map((winner) => `
        <article class="winner-tile">
          <p>Ganador</p>
          <h3>${winner.name}</h3>
          <p>${winner.hand_name}</p>
          <div class="cards-row">${winner.cards.length ? winner.cards.map((card) => cardHtml(card, "private")).join("") : '<span class="muted">Gano por fold.</span>'}</div>
        </article>
      `).join("")}
    </div>
    <div class="cards-row final-community">${payload.community_cards.map((card) => cardHtml(card)).join("")}</div>
    ${isCurrentClientHost ? '<button id="start-new-hand-result" class="primary-button" type="button">Iniciar nueva mano</button>' : '<p class="muted">Esperando que el host inicie una nueva mano.</p>'}
  `
}

socket.on("connected", () => setText("connection-status", "Conectado en tiempo real"))
socket.on("room_error", (payload) => showError(payload.message))
socket.on("action_error", (payload) => showError(payload.message))
socket.on("room_notice", (payload) => showNotice(payload.message))
socket.on("room_created", (room) => {
  clearError()
  const name = byId("player-name")?.value || ""
  window.sessionStorage.setItem(`room:${room.code}:name`, name)
  window.location.href = `/multiplayer/room/${room.code}`
})
socket.on("room_joined", (payload) => {
  clearError()
  window.sessionStorage.setItem(`room:${payload.room.code}:name`, payload.player.name)
  const joinPanel = byId("join-panel")
  if (joinPanel) joinPanel.classList.add("hidden")
  renderRoom(payload.room)
})
socket.on("room_updated", (room) => renderRoom(room))
socket.on("game_started", (room) => renderRoom(room))
socket.on("state_updated", (payload) => renderState(payload))
socket.on("game_finished", (payload) => renderFinished(payload))
socket.on("new_hand_started", (room) => {
  const result = byId("mp-result")
  if (result) result.classList.add("hidden")
  renderRoom(room)
})
socket.on("player_disconnected", (payload) => {
  showNotice(`${payload.player} se desconecto`)
  renderRoom(payload.room)
})
socket.on("player_auto_folded", (payload) => {
  showNotice(`${payload.player} fue retirado automaticamente por desconexion`)
  renderRoom(payload.room)
})

document.addEventListener("click", (event) => {
  if (event.target?.id === "create-room") {
    socket.emit("create_room", { name: byId("player-name")?.value || "" })
  }
  if (event.target?.id === "join-room") {
    const roomCode = byId("room-code")?.value || ""
    window.location.href = `/multiplayer/room/${roomCode.trim().toUpperCase()}`
  }
  if (event.target?.id === "join-current-room") {
    const roomCode = document.querySelector("[data-room-code]")?.dataset.roomCode
    socket.emit("join_room", { room_code: roomCode, name: byId("player-name")?.value || "" })
  }
  if (event.target?.id === "start-game") {
    socket.emit("start_game", { room_code: joinedRoomCode || document.querySelector("[data-room-code]")?.dataset.roomCode })
  }
  if (event.target?.id === "start-new-hand" || event.target?.id === "start-new-hand-result") {
    socket.emit("start_new_hand", { room_code: joinedRoomCode || document.querySelector("[data-room-code]")?.dataset.roomCode })
  }
  if (event.target?.dataset?.action) {
    const action = event.target.dataset.action
    const amount = action === "raise" ? Number(byId("mp-raise-amount")?.value || latestPublicState?.minimum_raise || 0) : 0
    socket.emit("player_action", {
      room_code: joinedRoomCode || document.querySelector("[data-room-code]")?.dataset.roomCode,
      action,
      amount,
    })
  }
})

document.addEventListener("DOMContentLoaded", () => {
  const roomCode = document.querySelector("[data-room-code]")?.dataset.roomCode
  if (roomCode) {
    const storedName = window.sessionStorage.getItem(`room:${roomCode}:name`)
    if (storedName && byId("player-name")) {
      byId("player-name").value = storedName
      socket.emit("join_room", { room_code: roomCode, name: storedName })
    }
    socket.emit("request_state", { room_code: roomCode })
  }
})
