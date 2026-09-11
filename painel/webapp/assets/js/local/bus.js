/* Tempo real do modo local: avisa esta aba e as outras abas abertas do app no mesmo navegador. */

const listeners = new Set();
const remoteChangeHandlers = new Set();
const channel = typeof BroadcastChannel === "function" ? new BroadcastChannel("drivesafe-local") : null;

function deliver(message) {
  for (const listener of listeners) {
    try {
      listener(message);
    } catch (error) {
      console.error(error);
    }
  }
}

export function publish(type, data) {
  const message = { type, data };
  deliver(message);
  if (channel) channel.postMessage(message);
}

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Outra aba mudou os dados: quem guarda cópia em memória precisa reler. */
export function onRemoteChange(handler) {
  remoteChangeHandlers.add(handler);
}

if (channel) {
  channel.onmessage = (event) => {
    for (const handler of remoteChangeHandlers) handler();
    deliver(event.data);
  };
}
