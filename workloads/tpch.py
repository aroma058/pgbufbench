import random
import string
import datetime
import time
import threading
from workloads.base import BaseWorkload

REGIONS = ['AFRICA', 'AMERICA', 'ASIA', 'EUROPE', 'MIDDLE EAST']
NATIONS = [
    ('ALGERIA', 0), ('ARGENTINA', 1), ('BRAZIL', 1), ('CANADA', 1),
    ('EGYPT', 4), ('ETHIOPIA', 0), ('FRANCE', 3), ('GERMANY', 3),
    ('INDIA', 2), ('INDONESIA', 2), ('IRAN', 4), ('IRAQ', 4),
    ('JAPAN', 2), ('JORDAN', 4), ('KENYA', 0), ('MOROCCO', 0),
    ('MOZAMBIQUE', 0), ('PERU', 1), ('CHINA', 2), ('ROMANIA', 3),
    ('SAUDI ARABIA', 4), ('VIETNAM', 2), ('RUSSIA', 3),
    ('UNITED KINGDOM', 3), ('UNITED STATES', 1),
]
SEGMENTS   = ['AUTOMOBILE','BUILDING','FURNITURE','MACHINERY','HOUSEHOLD']
PRIORITIES = ['1-URGENT','2-HIGH','3-MEDIUM','4-NOT SPECIFIED','5-LOW']
SHIP_MODES = ['AIR','FOB','MAIL','RAIL','REG AIR','SHIP','TRUCK']
SHIP_INSTRUCT = ['DELIVER IN PERSON','COLLECT COD','NONE','TAKE BACK RETURN']
P_TYPES_1  = ['STANDARD','SMALL','MEDIUM','LARGE','ECONOMY','PROMO']
P_TYPES_2  = ['ANODIZED','BURNISHED','PLATED','POLISHED','BRUSHED']
P_TYPES_3  = ['TIN','NICKEL','BRASS','STEEL','COPPER']
P_CONTAINERS_1 = ['SM','LG','MED','JUMBO','WRAP']
P_CONTAINERS_2 = ['CASE','BOX','BAG','JAR','PKG','PACK','CAN','DRUM']


class TPCHWorkload(BaseWorkload):

    def __init__(self, config):
        super().__init__(config)
        self.sf            = self.scale
        self.num_suppliers = self.sf * 10000
        self.num_customers = self.sf * 150000
        self.num_parts     = self.sf * 200000
        self.num_orders    = self.sf * 1500000
        print(f"[TPC-H] Scale factor: {self.sf}")
        print(f"[TPC-H] Suppliers: {self.num_suppliers:,}")
        print(f"[TPC-H] Customers: {self.num_customers:,}")
        print(f"[TPC-H] Parts:     {self.num_parts:,}")
        print(f"[TPC-H] Orders:    {self.num_orders:,}")
        self._query_times = {}
        self._lock        = threading.Lock()
        self._duration    = self.duration

    def _rand_string(self, min_len, max_len):
        length = random.randint(min_len, max_len)
        return ' '.join(random.choices(
            ['the','of','and','to','a','in','for','is','on','that',
             'by','this','with','from','or','an','are','at','be'],
            k=max(1, length // 5)))[:length]

    def _rand_phone(self, nation_id):
        return (f"{10+nation_id}-{random.randint(100,999)}-"
                f"{random.randint(100,999)}-{random.randint(1000,9999)}")

    def _rand_date(self, start_year=1992, end_year=1998):
        start = datetime.date(start_year, 1, 1)
        end   = datetime.date(end_year, 12, 31)
        return start + datetime.timedelta(
            days=random.randint(0, (end-start).days))

    def _part_name(self):
        words = ['almond','antique','aquamarine','azure','beige','bisque',
                 'black','blanched','blue','blush','brown','burlywood',
                 'burnished','chartreuse','chiffon','chocolate','coral',
                 'cornflower','cornsilk','cream','cyan','dark','deep',
                 'dodger','drab','firebrick','floral','forest','frosted',
                 'gainsboro','goldenrod','green','grey','honeydew','hot',
                 'ivory','khaki','lace','lavender','lawn','lemon','light',
                 'lime','linen','magenta','maroon','medium','metallic',
                 'midnight','mint','misty','navy','olive','orange','orchid',
                 'pale','papaya','peach','peru','pink','plum','powder',
                 'purple','red','rose','rosy','royal','saddle','salmon',
                 'sandy','seashell','sienna','sky','slate','smoke','snow',
                 'spring','steel','tan','thistle','tomato','turquoise',
                 'violet','wheat','white','yellow']
        return ' '.join(random.sample(words, 5))

    def create_schema(self, conn):
        cur = conn.cursor()
        print("[TPC-H] Creating schema...")
        for t in ['lineitem','partsupp','orders','part',
                  'supplier','customer','nation','region']:
            cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
        cur.execute("""CREATE TABLE region (
            r_regionkey INT PRIMARY KEY, r_name CHAR(25) NOT NULL,
            r_comment VARCHAR(152))""")
        cur.execute("""CREATE TABLE nation (
            n_nationkey INT PRIMARY KEY, n_name CHAR(25) NOT NULL,
            n_regionkey INT NOT NULL, n_comment VARCHAR(152),
            FOREIGN KEY (n_regionkey) REFERENCES region(r_regionkey))""")
        cur.execute("""CREATE TABLE supplier (
            s_suppkey INT PRIMARY KEY, s_name CHAR(25) NOT NULL,
            s_address VARCHAR(40) NOT NULL, s_nationkey INT NOT NULL,
            s_phone CHAR(15) NOT NULL, s_acctbal NUMERIC(15,2) NOT NULL,
            s_comment VARCHAR(101),
            FOREIGN KEY (s_nationkey) REFERENCES nation(n_nationkey))""")
        cur.execute("""CREATE TABLE customer (
            c_custkey INT PRIMARY KEY, c_name VARCHAR(25) NOT NULL,
            c_address VARCHAR(40) NOT NULL, c_nationkey INT NOT NULL,
            c_phone CHAR(15) NOT NULL, c_acctbal NUMERIC(15,2) NOT NULL,
            c_mktsegment CHAR(10) NOT NULL, c_comment VARCHAR(117),
            FOREIGN KEY (c_nationkey) REFERENCES nation(n_nationkey))""")
        cur.execute("""CREATE TABLE part (
            p_partkey INT PRIMARY KEY, p_name VARCHAR(55) NOT NULL,
            p_mfgr CHAR(25) NOT NULL, p_brand CHAR(10) NOT NULL,
            p_type VARCHAR(25) NOT NULL, p_size INT NOT NULL,
            p_container CHAR(10) NOT NULL, p_retailprice NUMERIC(15,2) NOT NULL,
            p_comment VARCHAR(23))""")
        cur.execute("""CREATE TABLE partsupp (
            ps_partkey INT NOT NULL, ps_suppkey INT NOT NULL,
            ps_availqty INT NOT NULL, ps_supplycost NUMERIC(15,2) NOT NULL,
            ps_comment VARCHAR(199),
            PRIMARY KEY (ps_partkey, ps_suppkey),
            FOREIGN KEY (ps_partkey) REFERENCES part(p_partkey),
            FOREIGN KEY (ps_suppkey) REFERENCES supplier(s_suppkey))""")
        cur.execute("""CREATE TABLE orders (
            o_orderkey INT PRIMARY KEY, o_custkey INT NOT NULL,
            o_orderstatus CHAR(1) NOT NULL, o_totalprice NUMERIC(15,2) NOT NULL,
            o_orderdate DATE NOT NULL, o_orderpriority CHAR(15) NOT NULL,
            o_clerk CHAR(15) NOT NULL, o_shippriority INT NOT NULL,
            o_comment VARCHAR(79),
            FOREIGN KEY (o_custkey) REFERENCES customer(c_custkey))""")
        cur.execute("""CREATE TABLE lineitem (
            l_orderkey INT NOT NULL, l_partkey INT NOT NULL,
            l_suppkey INT NOT NULL, l_linenumber INT NOT NULL,
            l_quantity NUMERIC(15,2) NOT NULL,
            l_extendedprice NUMERIC(15,2) NOT NULL,
            l_discount NUMERIC(15,2) NOT NULL, l_tax NUMERIC(15,2) NOT NULL,
            l_returnflag CHAR(1) NOT NULL, l_linestatus CHAR(1) NOT NULL,
            l_shipdate DATE NOT NULL, l_commitdate DATE NOT NULL,
            l_receiptdate DATE NOT NULL, l_shipinstruct CHAR(25) NOT NULL,
            l_shipmode CHAR(10) NOT NULL, l_comment VARCHAR(44),
            PRIMARY KEY (l_orderkey, l_linenumber),
            FOREIGN KEY (l_orderkey) REFERENCES orders(o_orderkey))""")
        cur.execute("CREATE INDEX idx_lineitem_shipdate ON lineitem (l_shipdate)")
        cur.execute("CREATE INDEX idx_lineitem_orderkey ON lineitem (l_orderkey)")
        cur.execute("CREATE INDEX idx_orders_custkey ON orders (o_custkey)")
        cur.execute("CREATE INDEX idx_orders_orderdate ON orders (o_orderdate)")
        cur.execute("CREATE INDEX idx_supplier_nationkey ON supplier (s_nationkey)")
        cur.execute("CREATE INDEX idx_customer_nationkey ON customer (c_nationkey)")
        conn.commit()
        cur.close()
        print("[TPC-H] Schema created.")

    def load_data(self, conn):
        self._load_region(conn)
        self._load_nation(conn)
        self._load_supplier(conn)
        self._load_customer(conn)
        self._load_part_and_partsupp(conn)
        self._load_orders_and_lineitem(conn)
        print("[TPC-H] Data loading complete.")

    def _load_region(self, conn):
        cur = conn.cursor()
        for i, name in enumerate(REGIONS):
            cur.execute("INSERT INTO region VALUES (%s,%s,%s)",
                       (i, name, self._rand_string(31, 115)))
        conn.commit()
        cur.close()
        print("[TPC-H] Regions loaded.")

    def _load_nation(self, conn):
        cur = conn.cursor()
        for i, (name, region) in enumerate(NATIONS):
            cur.execute("INSERT INTO nation VALUES (%s,%s,%s,%s)",
                       (i, name, region, self._rand_string(31, 114)))
        conn.commit()
        cur.close()
        print("[TPC-H] Nations loaded.")

    def _load_supplier(self, conn):
        cur = conn.cursor()
        total = self.num_suppliers
        batch = 1000
        print(f"[TPC-H] Loading {total:,} suppliers...")
        for start in range(1, total+1, batch):
            end  = min(start+batch-1, total)
            rows = []
            for s in range(start, end+1):
                n_key = random.randint(0, 24)
                rows.append((s, f"Supplier#{s:09d}",
                    self._rand_string(10,40), n_key,
                    self._rand_phone(n_key),
                    round(random.uniform(-999.99, 9999.99), 2),
                    self._rand_string(25, 100)))
            cur.executemany(
                "INSERT INTO supplier VALUES (%s,%s,%s,%s,%s,%s,%s)", rows)
            conn.commit()
        cur.close()
        print("[TPC-H] Suppliers loaded.")

    def _load_customer(self, conn):
        cur = conn.cursor()
        total = self.num_customers
        batch = 2000
        print(f"[TPC-H] Loading {total:,} customers...")
        for start in range(1, total+1, batch):
            end  = min(start+batch-1, total)
            rows = []
            for c in range(start, end+1):
                n_key = random.randint(0, 24)
                rows.append((c, f"Customer#{c:09d}",
                    self._rand_string(10,40), n_key,
                    self._rand_phone(n_key),
                    round(random.uniform(-999.99, 9999.99), 2),
                    random.choice(SEGMENTS),
                    self._rand_string(29, 116)))
            cur.executemany(
                "INSERT INTO customer VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", rows)
            conn.commit()
            if end % 50000 == 0 or end == total:
                print(f"[TPC-H] Customers: {end:,}/{total:,}")
        cur.close()

    def _load_part_and_partsupp(self, conn):
        cur = conn.cursor()
        total     = self.num_parts
        batch     = 2000
        num_supps = self.num_suppliers
        print(f"[TPC-H] Loading {total:,} parts + partsupp...")
        for start in range(1, total+1, batch):
            end       = min(start+batch-1, total)
            part_rows = []
            ps_rows   = []
            for p in range(start, end+1):
                p_type = (f"{random.choice(P_TYPES_1)} "
                         f"{random.choice(P_TYPES_2)} "
                         f"{random.choice(P_TYPES_3)}")
                p_cont = (f"{random.choice(P_CONTAINERS_1)} "
                         f"{random.choice(P_CONTAINERS_2)}")
                retail = round(90000 + (p/self.num_parts)*10000, 2)
                part_rows.append((p, self._part_name(),
                    f"Manufacturer#{random.randint(1,5)}",
                    f"Brand#{random.randint(1,5)}{random.randint(1,5)}",
                    p_type, random.randint(1,50), p_cont, retail,
                    self._rand_string(5,22)))
                suppkeys = random.sample(range(1, num_supps+1), min(4, num_supps))
                for s in suppkeys:
                    ps_rows.append((p, s, random.randint(1,9999),
                        round(random.uniform(1.00,1000.00),2),
                        self._rand_string(49,198)))
            cur.executemany(
                "INSERT INTO part VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                part_rows)
            cur.executemany(
                "INSERT INTO partsupp VALUES (%s,%s,%s,%s,%s)", ps_rows)
            conn.commit()
            if end % 50000 == 0 or end == total:
                print(f"[TPC-H] Parts: {end:,}/{total:,}")
        cur.close()

    def _load_orders_and_lineitem(self, conn):
        cur       = conn.cursor()
        total     = self.num_orders
        batch     = 1000
        num_cust  = self.num_customers
        num_parts = self.num_parts
        num_supps = self.num_suppliers
        print(f"[TPC-H] Loading {total:,} orders + lineitems...")
        for start in range(1, total+1, batch):
            end      = min(start+batch-1, total)
            ord_rows = []
            li_rows  = []
            for o in range(start, end+1):
                o_date   = self._rand_date(1992, 1998)
                cust_key = random.randint(1, num_cust)
                ord_rows.append((o, cust_key, random.choice(['F','O','P']),
                    round(random.uniform(1000,500000),2), o_date,
                    random.choice(PRIORITIES),
                    f"Clerk#{random.randint(1,1000):09d}", 0,
                    self._rand_string(19,78)))
                for l in range(1, random.randint(1,7)+1):
                    p_key     = random.randint(1, num_parts)
                    s_key     = random.randint(1, num_supps)
                    ship_date = o_date + datetime.timedelta(days=random.randint(1,121))
                    comm_date = o_date + datetime.timedelta(days=random.randint(30,90))
                    recv_date = ship_date + datetime.timedelta(days=random.randint(1,30))
                    qty       = round(random.uniform(1,50), 2)
                    price     = round(random.uniform(900,104950), 2)
                    discount  = round(random.uniform(0,0.10), 2)
                    tax       = round(random.uniform(0,0.08), 2)
                    ret_flag  = random.choice(['A','N','R'])
                    status_l  = 'F' if ship_date < datetime.date(1995,6,17) else 'O'
                    li_rows.append((o, p_key, s_key, l, qty, price, discount,
                        tax, ret_flag, status_l, ship_date, comm_date, recv_date,
                        random.choice(SHIP_INSTRUCT), random.choice(SHIP_MODES),
                        self._rand_string(10,43)))
            cur.executemany(
                "INSERT INTO orders VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                ord_rows)
            cur.executemany(
                "INSERT INTO lineitem VALUES "
                "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                li_rows)
            conn.commit()
            if end % 100000 == 0 or end == total:
                print(f"[TPC-H] Orders: {end:,}/{total:,}")
        cur.close()

    QUERIES = {
        'Q1': """SELECT l_returnflag, l_linestatus,
                   SUM(l_quantity), SUM(l_extendedprice),
                   SUM(l_extendedprice*(1-l_discount)),
                   SUM(l_extendedprice*(1-l_discount)*(1+l_tax)),
                   AVG(l_quantity), AVG(l_extendedprice),
                   AVG(l_discount), COUNT(*)
            FROM lineitem
            WHERE l_shipdate <= DATE '1998-12-01' - INTERVAL '90 days'
            GROUP BY l_returnflag, l_linestatus
            ORDER BY l_returnflag, l_linestatus""",
        'Q3': """SELECT l_orderkey,
                   SUM(l_extendedprice*(1-l_discount)) AS revenue,
                   o_orderdate, o_shippriority
            FROM customer, orders, lineitem
            WHERE c_mktsegment='BUILDING' AND c_custkey=o_custkey
              AND l_orderkey=o_orderkey
              AND o_orderdate < DATE '1995-03-15'
              AND l_shipdate > DATE '1995-03-15'
            GROUP BY l_orderkey, o_orderdate, o_shippriority
            ORDER BY revenue DESC, o_orderdate LIMIT 10""",
        'Q6': """SELECT SUM(l_extendedprice * l_discount) AS revenue
            FROM lineitem
            WHERE l_shipdate >= DATE '1994-01-01'
              AND l_shipdate < DATE '1994-01-01' + INTERVAL '1 year'
              AND l_discount BETWEEN 0.05 AND 0.07
              AND l_quantity < 24""",
        'Q12': """SELECT l_shipmode,
                   SUM(CASE WHEN o_orderpriority='1-URGENT'
                        OR o_orderpriority='2-HIGH' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN o_orderpriority<>'1-URGENT'
                        AND o_orderpriority<>'2-HIGH' THEN 1 ELSE 0 END)
            FROM orders, lineitem
            WHERE o_orderkey=l_orderkey
              AND l_shipmode IN ('MAIL','SHIP')
              AND l_commitdate < l_receiptdate
              AND l_shipdate < l_commitdate
              AND l_receiptdate >= DATE '1994-01-01'
              AND l_receiptdate < DATE '1994-01-01' + INTERVAL '1 year'
            GROUP BY l_shipmode ORDER BY l_shipmode""",
        'Q14': """SELECT 100.00*SUM(CASE WHEN p_type LIKE 'PROMO%'
                    THEN l_extendedprice*(1-l_discount) ELSE 0 END)
                   /SUM(l_extendedprice*(1-l_discount)) AS promo_revenue
            FROM lineitem, part
            WHERE l_partkey=p_partkey
              AND l_shipdate >= DATE '1995-09-01'
              AND l_shipdate < DATE '1995-09-01' + INTERVAL '1 month'""",
    }

    def _record_query(self, q_name, elapsed_ms):
        with self._lock:
            if q_name not in self._query_times:
                self._query_times[q_name] = []
            self._query_times[q_name].append(elapsed_ms)

    def get_analytical_summary(self):
        summary = {}
        with self._lock:
            for q, times in self._query_times.items():
                if times:
                    sorted_t = sorted(times)
                    summary[q] = {
                        'count':  len(times),
                        'avg_ms': round(sum(times) / len(times), 1),
                        'p50_ms': round(sorted_t[int(len(sorted_t) * 0.50)], 1),
                        'p99_ms': round(sorted_t[int(len(sorted_t) * 0.99)], 1),
                        'qph':    round(len(times) / self._duration * 3600, 1),
                    }
        return summary

    def run_transaction(self, conn):
        q_name = random.choice(list(self.QUERIES.keys()))
        cur    = conn.cursor()
        try:
            cur.execute("SET statement_timeout = '120s'")
            start = time.time()
            cur.execute(self.QUERIES[q_name])
            cur.fetchall()
            elapsed = (time.time() - start) * 1000
            conn.commit()
            self._record_query(q_name, elapsed)
        except Exception:
            conn.rollback()
        finally:
            cur.close()
