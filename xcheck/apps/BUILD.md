# Reconstructing the app population

Sources come from 95emulator's code-sweep cache (`build/code-sweep/cache/`) and
one clone. Cross-build everything `aarch64-linux-gnu-gcc -static -O2`.

- bzip2-1.0.8, lz4-1.9.4, lua-5.4.7 — their own Makefiles (see RESULTS.md).
- sha256: crypto-algorithms-master + sha_driver.c
- cjson: cJSON-1.7.18 + cjson_driver.c
- sqlite: sqlite-autoconf tarball + sql_driver.c (-DSQLITE_THREADSAFE=0)
- net: mongoose-7.14 + net_driver.c (serve data.bin: python3 -m http.server 18930)
- pacman: git clone https://github.com/kcy1019/pacman (NO LICENSE — local
  measurement only, never redistribute); apply the one-line fixed-seed patch in
  random.hxx, add #include <tuple> to game.nogui.hxx, build xcheck_pacman.cc
- data.bin: the seeded generator one-liner in the session record (seed 42,
  4 MiB half-text half-random)
