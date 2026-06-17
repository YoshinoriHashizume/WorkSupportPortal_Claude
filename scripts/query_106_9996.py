import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); os.chdir(ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from apps.gonenkukumi.infrastructure.oracle.client import oracle_connection

with oracle_connection() as conn:
    cur = conn.cursor()
    for title, sql in [
        ('tables with CUST and VEND cols', """
            SELECT table_name, column_name FROM user_tab_columns
             WHERE (column_name LIKE '%CUST%' OR column_name LIKE '%VEND%')
               AND table_name LIKE 'M_%'
             ORDER BY table_name, column_id
        """),
        ('M_CUST class fields 106', """
            SELECT CUST_CLASS_01_CD, CUST_CLASS_01_NM, CUST_CLASS_02_CD, CUST_CLASS_02_NM
              FROM M_CUST WHERE TRIM(CUST_CD)='106'
        """),
        ('9996 cust item sample', """
            SELECT COUNT(*) FROM M_CUST_ITEM WHERE TRIM(CUST_CD)='9996'
        """),
        ('106 cust item sample', """
            SELECT COUNT(*) FROM M_CUST_ITEM WHERE TRIM(CUST_CD)='106'
        """),
    ]:
        print('===', title, '===')
        try:
            cur.execute(sql)
            for r in cur.fetchall()[:30]: print(r)
        except Exception as e:
            print('ERR', e)
