/* deterministic in-memory database workload: schema, bulk insert in one
 * transaction, indexed point lookups, range aggregates, a join, and a delete
 * sweep. No file I/O, no timestamps -- byte-stable work. */
#include <stdio.h>
#include <stdlib.h>
#include "sqlite3.h"
static void ck(int rc, sqlite3 *db) {
    if (rc != SQLITE_OK && rc != SQLITE_DONE && rc != SQLITE_ROW) {
        fprintf(stderr, "sqlite: %s\n", sqlite3_errmsg(db)); exit(2);
    }
}
int main(int argc, char **argv) {
    int rows = argc > 1 ? atoi(argv[1]) : 40000;
    sqlite3 *db; ck(sqlite3_open(":memory:", &db), db);
    ck(sqlite3_exec(db, "CREATE TABLE t(id INTEGER PRIMARY KEY, k INTEGER, s TEXT);"
                        "CREATE INDEX tk ON t(k);"
                        "CREATE TABLE u(id INTEGER PRIMARY KEY, v REAL);", 0, 0, 0), db);
    sqlite3_stmt *ins; sqlite3_prepare_v2(db, "INSERT INTO t VALUES(?,?,?)", -1, &ins, 0);
    char buf[64];
    ck(sqlite3_exec(db, "BEGIN", 0, 0, 0), db);
    for (int i = 0; i < rows; i++) {
        snprintf(buf, sizeof buf, "row-%d-%x", i, i * 2654435761u);
        sqlite3_bind_int(ins, 1, i); sqlite3_bind_int(ins, 2, i * 7 % 9973);
        sqlite3_bind_text(ins, 3, buf, -1, SQLITE_TRANSIENT);
        sqlite3_step(ins); sqlite3_reset(ins);
    }
    ck(sqlite3_exec(db, "COMMIT", 0, 0, 0), db);
    ck(sqlite3_exec(db, "INSERT INTO u SELECT id, k*1.5 FROM t WHERE id % 3 = 0", 0, 0, 0), db);
    sqlite3_stmt *q; long long acc = 0;
    sqlite3_prepare_v2(db, "SELECT count(*), sum(k) FROM t WHERE k BETWEEN ? AND ?", -1, &q, 0);
    for (int i = 0; i < 2000; i++) {
        sqlite3_bind_int(q, 1, i % 9000); sqlite3_bind_int(q, 2, i % 9000 + 500);
        sqlite3_step(q); acc += sqlite3_column_int64(q, 1); sqlite3_reset(q);
    }
    sqlite3_prepare_v2(db, "SELECT count(*) FROM t JOIN u ON t.id=u.id WHERE t.k < 5000", -1, &q, 0);
    sqlite3_step(q); acc += sqlite3_column_int64(q, 0);
    ck(sqlite3_exec(db, "DELETE FROM t WHERE id % 7 = 0", 0, 0, 0), db);
    sqlite3_prepare_v2(db, "SELECT count(*) FROM t", -1, &q, 0);
    sqlite3_step(q); acc += sqlite3_column_int64(q, 0);
    printf("sqlite rows=%d acc=%lld\n", rows, acc);
    return 0;
}
