// O trackball pelo celular (desligado por enquanto: o cartao fica escondido).
"use strict";

// ── Trackball: o celular como mouse do gabinete ──────────────────
// O dedo na area rola a bola: os movimentos vao pelo WebSocket
// /api/trackball, juntados a cada quadro da tela. Soltando depois de um
// giro rapido, a bola continua rolando e freia aos poucos, como um trackball
// de fliperama; um toque a segura.

let ball = null, ballSend = { x: 0, y: 0 }, ballVel = { x: 0, y: 0 }, ballLast = null, ballSpin = 0;

function ballWs(msg) {
  if (ball && ball.readyState === 1) ball.send(JSON.stringify(msg));
}

function ballFlush() {
  const dx = Math.trunc(ballSend.x), dy = Math.trunc(ballSend.y);
  if (dx || dy) {
    ballWs({ m: [dx, dy] });
    ballSend.x -= dx;
    ballSend.y -= dy;
  }
}

function ballFrame(time) {
  // A inercia: anda com a velocidade e freia (a cada 16 ms, 6%).
  if (ballSpin && !ballLast) {
    const dt = Math.min(50, time - ballSpin);
    ballSpin = time;
    ballSend.x += ballVel.x * dt;
    ballSend.y += ballVel.y * dt;
    const friction = Math.pow(0.94, dt / 16);
    ballVel.x *= friction;
    ballVel.y *= friction;
    if (Math.abs(ballVel.x) + Math.abs(ballVel.y) < 0.01) ballSpin = 0;
  }
  ballFlush();
  if (ball) requestAnimationFrame(ballFrame);
}

function openBall() {
  const scheme = location.protocol === "https:" ? "wss://" : "ws://";
  ball = new WebSocket(scheme + location.host + "/api/trackball");
  ball.onopen = () => {
    $("ball").hidden = false;
    $("ball-open").hidden = true;
    $("ball-note").textContent = t("ball_on");
    requestAnimationFrame(ballFrame);
  };
  ball.onclose = () => {
    $("ball").hidden = true;
    $("ball-open").hidden = false;
    $("ball-note").textContent = t("term_off");
    ball = null;
  };
}

$("ball-open").addEventListener("click", openBall);
const pad = $("ball-pad");
pad.addEventListener("pointerdown", (ev) => {
  pad.setPointerCapture(ev.pointerId);
  pad.classList.add("active");
  ballSpin = 0;
  ballVel = { x: 0, y: 0 };
  ballLast = { x: ev.clientX, y: ev.clientY, t: ev.timeStamp };
});
pad.addEventListener("pointermove", (ev) => {
  if (!ballLast) return;
  const sens = Number($("ball-sens").value);
  const dx = (ev.clientX - ballLast.x) * sens, dy = (ev.clientY - ballLast.y) * sens;
  const dt = Math.max(1, ev.timeStamp - ballLast.t);
  ballSend.x += dx;
  ballSend.y += dy;
  // A velocidade (por ms), suavizada: e a que a bola leva ao soltar.
  ballVel.x = 0.6 * (dx / dt) + 0.4 * ballVel.x;
  ballVel.y = 0.6 * (dy / dt) + 0.4 * ballVel.y;
  ballLast = { x: ev.clientX, y: ev.clientY, t: ev.timeStamp };
});
function padUp(ev) {
  if (!ballLast) return;
  // Parado antes de soltar (mais de 60 ms): sem inercia.
  const still = ev.timeStamp - ballLast.t > 60;
  ballLast = null;
  pad.classList.remove("active");
  if ($("ball-spin").checked && !still) ballSpin = performance.now();
}
pad.addEventListener("pointerup", padUp);
pad.addEventListener("pointercancel", padUp);
pad.addEventListener("wheel", (ev) => {
  ev.preventDefault();
  ballWs({ m: [0, 0], w: ev.deltaY > 0 ? -1 : 1 });
}, { passive: false });
document.querySelectorAll(".ball-buttons button").forEach((button) => {
  const name = button.dataset.button;
  const up = () => {
    if (!button.classList.contains("down")) return;
    button.classList.remove("down");
    ballWs({ b: [name, 0] });
  };
  button.addEventListener("pointerdown", (ev) => {
    button.setPointerCapture(ev.pointerId);
    button.classList.add("down");
    ballWs({ b: [name, 1] });
  });
  button.addEventListener("pointerup", up);
  button.addEventListener("pointercancel", up);
  button.addEventListener("contextmenu", (ev) => ev.preventDefault());
});
