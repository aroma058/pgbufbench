import random
from workloads.base import BaseWorkload


class TATpWorkload(BaseWorkload):

    def __init__(self, config):
        super().__init__(config)
        self.num_subscribers = self.scale * 100000
        # Pre-shuffle hot set so hot pages are spread throughout the table
        total    = self.num_subscribers
        hot_size = int(total * 0.20)
        self._hot_ids = random.sample(range(1, total + 1), hot_size)
        print(f"[TATP] Subscribers: {self.num_subscribers:,}")

    def _rand_string(self, length):
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        return ''.join(random.choices(chars, k=length))

    def _rand_subscriber_zipfian(self):
        if random.random() < 0.80:
            return random.choice(self._hot_ids)
        else:
            return random.randint(1, self.num_subscribers)

    def create_schema(self, conn):
        cur = conn.cursor()
        print("[TATP] Creating schema...")
        cur.execute("DROP TABLE IF EXISTS call_forwarding CASCADE")
        cur.execute("DROP TABLE IF EXISTS special_facility CASCADE")
        cur.execute("DROP TABLE IF EXISTS access_info CASCADE")
        cur.execute("DROP TABLE IF EXISTS subscriber CASCADE")
        cur.execute("""
            CREATE TABLE subscriber (
                s_id INT PRIMARY KEY, sub_nbr CHAR(15) NOT NULL,
                bit_1 SMALLINT NOT NULL, bit_2 SMALLINT NOT NULL,
                bit_3 SMALLINT NOT NULL, bit_4 SMALLINT NOT NULL,
                bit_5 SMALLINT NOT NULL, bit_6 SMALLINT NOT NULL,
                bit_7 SMALLINT NOT NULL, bit_8 SMALLINT NOT NULL,
                bit_9 SMALLINT NOT NULL, bit_10 SMALLINT NOT NULL,
                hex_1 SMALLINT NOT NULL, hex_2 SMALLINT NOT NULL,
                hex_3 SMALLINT NOT NULL, hex_4 SMALLINT NOT NULL,
                hex_5 SMALLINT NOT NULL, hex_6 SMALLINT NOT NULL,
                hex_7 SMALLINT NOT NULL, hex_8 SMALLINT NOT NULL,
                byte2_1 SMALLINT NOT NULL, byte2_2 SMALLINT NOT NULL,
                byte2_3 SMALLINT NOT NULL, byte2_4 SMALLINT NOT NULL,
                byte2_5 SMALLINT NOT NULL, byte2_6 SMALLINT NOT NULL,
                byte2_7 SMALLINT NOT NULL, byte2_8 SMALLINT NOT NULL,
                byte2_9 SMALLINT NOT NULL, byte2_10 SMALLINT NOT NULL,
                msc_location INT NOT NULL, vlr_location INT NOT NULL
            )""")
        cur.execute("""
            CREATE TABLE access_info (
                s_id INT NOT NULL, ai_type SMALLINT NOT NULL,
                data1 SMALLINT NOT NULL, data2 SMALLINT NOT NULL,
                data3 CHAR(3) NOT NULL, data4 CHAR(5) NOT NULL,
                PRIMARY KEY (s_id, ai_type),
                FOREIGN KEY (s_id) REFERENCES subscriber(s_id))""")
        cur.execute("""
            CREATE TABLE special_facility (
                s_id INT NOT NULL, sf_type SMALLINT NOT NULL,
                is_active SMALLINT NOT NULL, error_cntrl SMALLINT NOT NULL,
                data_a SMALLINT NOT NULL, data_b CHAR(5) NOT NULL,
                PRIMARY KEY (s_id, sf_type),
                FOREIGN KEY (s_id) REFERENCES subscriber(s_id))""")
        cur.execute("""
            CREATE TABLE call_forwarding (
                s_id INT NOT NULL, sf_type SMALLINT NOT NULL,
                start_time SMALLINT NOT NULL, end_time SMALLINT NOT NULL,
                numberx CHAR(15) NOT NULL,
                PRIMARY KEY (s_id, sf_type, start_time),
                FOREIGN KEY (s_id, sf_type)
                    REFERENCES special_facility(s_id, sf_type))""")
        cur.execute("CREATE INDEX idx_sub_nbr ON subscriber (sub_nbr)")
        cur.execute("CREATE INDEX idx_ai_sid ON access_info (s_id)")
        cur.execute("CREATE INDEX idx_sf_sid ON special_facility (s_id)")
        cur.execute("CREATE INDEX idx_cf_sid ON call_forwarding (s_id)")
        conn.commit()
        cur.close()
        print("[TATP] Schema created.")

    def load_data(self, conn):
        self._load_subscribers(conn)
        self._load_access_info(conn)
        self._load_special_facility_and_call_forwarding(conn)
        print("[TATP] Running VACUUM ANALYZE...")
        old_iso = conn.isolation_level
        conn.set_isolation_level(0)
        cur = conn.cursor()
        for t in ['subscriber', 'access_info',
                  'special_facility', 'call_forwarding']:
            cur.execute(f"VACUUM ANALYZE {t}")
        cur.close()
        conn.set_isolation_level(old_iso)
        print("[TATP] Data loading complete.")

    def _load_subscribers(self, conn):
        cur   = conn.cursor()
        total = self.num_subscribers
        batch = 5000
        print(f"[TATP] Loading {total:,} subscribers...")
        for start in range(1, total + 1, batch):
            end  = min(start + batch - 1, total)
            rows = []
            for s_id in range(start, end + 1):
                rows.append((
                    s_id, str(s_id).zfill(15),
                    *[random.randint(0, 1)   for _ in range(10)],
                    *[random.randint(0, 15)  for _ in range(8)],
                    *[random.randint(0, 255) for _ in range(10)],
                    random.randint(1, 2**31 - 1),
                    random.randint(1, 2**31 - 1),
                ))
            cur.executemany(
                "INSERT INTO subscriber VALUES "
                "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,"
                "%s,%s,%s,%s,%s,%s,%s,%s,"
                "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,"
                "%s,%s)", rows)
            conn.commit()
            if end % 100000 == 0 or end == total:
                print(f"[TATP] Subscribers: {end:,}/{total:,}")
        cur.close()

    def _load_access_info(self, conn):
        cur   = conn.cursor()
        total = self.num_subscribers
        batch = 5000
        print(f"[TATP] Loading access_info...")
        for start in range(1, total + 1, batch):
            end  = min(start + batch - 1, total)
            rows = []
            for s_id in range(start, end + 1):
                num_ai   = random.randint(1, 4)
                ai_types = random.sample([1, 2, 3, 4], num_ai)
                for ai_type in ai_types:
                    rows.append((s_id, ai_type,
                        random.randint(0, 255), random.randint(0, 255),
                        self._rand_string(3), self._rand_string(5)))
            cur.executemany(
                "INSERT INTO access_info VALUES (%s,%s,%s,%s,%s,%s)", rows)
            conn.commit()
        cur.close()
        print(f"[TATP] Access info loaded.")

    def _load_special_facility_and_call_forwarding(self, conn):
        cur   = conn.cursor()
        total = self.num_subscribers
        batch = 2000
        print(f"[TATP] Loading special_facility + call_forwarding...")
        for start in range(1, total + 1, batch):
            end     = min(start + batch - 1, total)
            sf_rows = []
            cf_rows = []
            for s_id in range(start, end + 1):
                num_sf   = random.randint(1, 4)
                sf_types = random.sample([1, 2, 3, 4], num_sf)
                for sf_type in sf_types:
                    sf_rows.append((s_id, sf_type, random.randint(0, 1),
                        random.randint(0, 255), random.randint(0, 255),
                        self._rand_string(5)))
                    num_cf      = random.randint(0, 3)
                    start_times = random.sample([0, 8, 16], min(num_cf, 3))
                    for start_time in start_times:
                        cf_rows.append((s_id, sf_type, start_time,
                            start_time + random.randint(1, 8),
                            self._rand_string(15)))
            cur.executemany(
                "INSERT INTO special_facility VALUES (%s,%s,%s,%s,%s,%s)",
                sf_rows)
            cur.executemany(
                "INSERT INTO call_forwarding VALUES (%s,%s,%s,%s,%s)",
                cf_rows)
            conn.commit()
            if end % 100000 == 0 or end == total:
                print(f"[TATP] Special facility: {end:,}/{total:,}")
        cur.close()

    def _txn_get_subscriber_data(self, conn):
        cur = conn.cursor()
        try:
            cur.execute("SELECT * FROM subscriber WHERE s_id = %s",
                       (self._rand_subscriber_zipfian(),))
            cur.fetchone()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    def _txn_get_new_destination(self, conn):
        s_id    = self._rand_subscriber_zipfian()
        sf_type = random.randint(1, 4)
        start_t = random.choice([0, 8, 16])
        cur     = conn.cursor()
        try:
            cur.execute("""
                SELECT cf.numberx FROM special_facility sf
                JOIN call_forwarding cf
                  ON sf.s_id=cf.s_id AND sf.sf_type=cf.sf_type
                WHERE sf.s_id=%s AND sf.sf_type=%s AND sf.is_active=1
                  AND cf.start_time<=%s AND cf.end_time>%s
            """, (s_id, sf_type, start_t, start_t))
            cur.fetchall()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    def _txn_get_access_data(self, conn):
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT data1,data2,data3,data4 FROM access_info "
                "WHERE s_id=%s AND ai_type=%s",
                (self._rand_subscriber_zipfian(), random.randint(1, 4)))
            cur.fetchone()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    def _txn_update_subscriber_data(self, conn):
        s_id = self._rand_subscriber_zipfian()
        cur  = conn.cursor()
        try:
            cur.execute("UPDATE subscriber SET bit_1=%s WHERE s_id=%s",
                       (random.randint(0, 1), s_id))
            cur.execute("UPDATE special_facility SET data_a=%s "
                       "WHERE s_id=%s AND sf_type=%s",
                       (random.randint(0, 255), s_id, random.randint(1, 4)))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    def _txn_update_location(self, conn):
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE subscriber SET vlr_location=%s WHERE s_id=%s",
                (random.randint(1, 2**31-1), self._rand_subscriber_zipfian()))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    def _txn_insert_call_forwarding(self, conn):
        s_id       = self._rand_subscriber_zipfian()
        sf_type    = random.randint(1, 4)
        start_time = random.choice([0, 8, 16])
        cur        = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO call_forwarding VALUES (%s,%s,%s,%s,%s)",
                (s_id, sf_type, start_time,
                 start_time + random.randint(1, 8), self._rand_string(15)))
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            cur.close()

    def _txn_delete_call_forwarding(self, conn):
        cur = conn.cursor()
        try:
            cur.execute(
                "DELETE FROM call_forwarding "
                "WHERE s_id=%s AND sf_type=%s AND start_time=%s",
                (self._rand_subscriber_zipfian(),
                 random.randint(1, 4), random.choice([0, 8, 16])))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    def run_transaction(self, conn):
        r = random.random()
        if r < 0.35:
            self._txn_get_subscriber_data(conn)
        elif r < 0.45:
            self._txn_get_new_destination(conn)
        elif r < 0.80:
            self._txn_get_access_data(conn)
        elif r < 0.82:
            self._txn_update_subscriber_data(conn)
        elif r < 0.96:
            self._txn_update_location(conn)
        elif r < 0.98:
            self._txn_insert_call_forwarding(conn)
        else:
            self._txn_delete_call_forwarding(conn)
