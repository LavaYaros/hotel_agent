import psycopg2
import pandas as pd
from sklearn.metrics import confusion_matrix, fbeta_score
from db_helper import db_creds
import numpy as np
from itertools import product
from sqlalchemy import create_engine

from db_helper import db_creds

engine = create_engine(f"postgresql+psycopg2://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['dbname']}")

query_get_embeddings = """
SELECT  r.id,
        (SELECT MIN(r.embedding <=> p.vec) FROM pool_proto      p) AS dist_pos,
        (SELECT MIN(r.embedding <=> n.vec) FROM pool_proto_neg n) AS dist_neg,
        (r.pool_state = 1)::int                           AS actual
FROM    rooms r
WHERE   r.pool_state IS NOT NULL        -- only rows with ground-truth
  AND   r.embedding  IS NOT NULL;       -- make sure the vector is there
"""

df = pd.read_sql(query_get_embeddings, engine)
        

pos_grid = np.arange(0.40, 0.70, 0.01)
neg_grid = np.arange(0.20, 0.60, 0.01)

best_f1, best_pos, best_neg = -1, None, None

for pos_th, neg_th in product(pos_grid, neg_grid):
    pred = (df.dist_pos < pos_th) & (df.dist_neg > neg_th)
    f1   = fbeta_score(df.actual, pred, beta=0.7)

    if f1 > best_f1:
        best_f1, best_pos, best_neg = f1, pos_th, neg_th

print(f"best F1={best_f1:.3f}  →  pos_th={best_pos:.2f}, neg_th={best_neg:.2f}")


with psycopg2.connect(**db_creds) as conn, conn.cursor() as cur:
    cur.execute(
        """
        UPDATE rooms AS r
        SET    access_to_pool =
               ((SELECT MIN(r.embedding <=> p.vec) FROM pool_proto      p) < %s)  AND
               ((SELECT MIN(r.embedding <=> n.vec) FROM pool_proto_neg n) > %s);
        """,
        (float(best_pos), float(best_neg)),
    )
    conn.commit()



query_get_labels = """
    SELECT access_to_pool, pool_state
    FROM rooms
    WHERE access_to_pool IS NOT NULL
      AND pool_state   IS NOT NULL;
"""

df = pd.read_sql(query_get_labels, engine)

# map to binary labels
df["actual"] = (df["pool_state"] == 1).astype(int)
df["pred"]   = df["access_to_pool"].astype(int)

# confusion-matrix
cm = confusion_matrix(df["actual"], df["pred"])   # [[TN FP] [FN TP]]
tn, fp, fn, tp = cm.ravel()
print(f"TP={tp}  FP={fp}  FN={fn}  TN={tn}")


def create_pool_trigger(pos_threshold, neg_threshold):
    """
    Create a trigger to set access_to_pool based on embeddings.
    Each time a row is inserted or updated, 
    the trigger will set access_to_pool to True if the embedding is
    close to positive prototypes and not close to negative prototypes.
    """

    with psycopg2.connect(**db_creds) as conn, conn.cursor() as cur:
        cur.execute(f"""
            -- clean slate
            DROP TRIGGER  IF EXISTS trg_set_access_to_pool ON rooms;
            DROP FUNCTION IF EXISTS set_access_to_pool();

            CREATE FUNCTION set_access_to_pool() RETURNS trigger AS $$
            DECLARE
                d_pos FLOAT;                 -- nearest positive prototype
                d_neg FLOAT;                 -- nearest negative prototype
            BEGIN
                SELECT MIN(NEW.embedding <=> vec) INTO d_pos FROM pool_proto;
                SELECT MIN(NEW.embedding <=> vec) INTO d_neg FROM pool_proto_neg;

                IF NEW.access_to_pool IS NULL THEN
                    NEW.access_to_pool := (d_pos < {pos_threshold})   -- close to “has pool”
                                          AND (d_neg > {neg_threshold}); -- not close to “no pool”
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER trg_set_access_to_pool
            BEFORE INSERT OR UPDATE OF embedding
            ON rooms
            FOR EACH ROW EXECUTE FUNCTION set_access_to_pool();
        """)
    print("✅ pool trigger created")


# create_pool_trigger(best_pos, best_neg)
