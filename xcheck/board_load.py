"""Board side: drive TX or RX at a target rate for a fixed duration, then
report the throughput actually achieved and the CPU time consumed."""
import socket, sys, time, os

host, mode, mbps, secs = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
port = 5201 if mode == 'tx' else 5202
CH = 256 * 1024
buf = os.urandom(CH)

def cpu():
    f = open('/proc/stat').readline().split()[1:]
    v = [int(x) for x in f]
    return sum(v), sum(v) - v[3] - v[4]        # total, busy (minus idle+iowait)

s = socket.create_connection((host, port))
s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
byte_budget = mbps * 1e6 / 8
t0 = time.time(); end = t0 + secs
sent = 0
c0t, c0b = cpu()
while time.time() < end:
    if mode == 'tx':
        s.sendall(buf); sent += CH
    else:
        d = s.recv(1 << 20)
        if not d: break
        sent += len(d)
    if mbps > 0:                                # simple pacing to a target rate
        want = (time.time() - t0) * byte_budget
        if sent > want:
            time.sleep(min(0.02, (sent - want) / byte_budget))
c1t, c1b = cpu()
el = time.time() - t0
s.close()
util = (c1b - c0b) / (c1t - c0t) * 100 if c1t > c0t else 0
print(f"mode={mode} target={mbps:.0f}Mbps actual={sent*8/el/1e6:.1f}Mbps "
      f"bytes={sent} elapsed={el:.2f} cpu_util={util:.1f}%")
