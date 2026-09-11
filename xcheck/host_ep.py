"""Host endpoint for the network-power sweep.
5201 = sink   (host reads and discards; the BOARD is transmitting)
5202 = source (host writes; the BOARD is receiving)
Plain TCP so nothing has to be installed on either side."""
import socket, threading, os

CHUNK = os.urandom(256 * 1024)

def serve(port, mode):
    s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', port)); s.listen(4)
    while True:
        c, _ = s.accept()
        threading.Thread(target=handle, args=(c, mode), daemon=True).start()

def handle(c, mode):
    c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    try:
        if mode == 'sink':
            while c.recv(1 << 20):
                pass
        else:
            while True:
                c.sendall(CHUNK)
    except OSError:
        pass
    finally:
        c.close()

threading.Thread(target=serve, args=(5201, 'sink'), daemon=True).start()
threading.Thread(target=serve, args=(5202, 'source'), daemon=True).start()
print('host endpoint up on 5201 (sink) / 5202 (source)', flush=True)
threading.Event().wait()
