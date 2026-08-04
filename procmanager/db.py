from datetime import datetime 
import os
import gzip
import sqlite3
from procmanager import config
from procmanager.config import SERVER_STATUS_PATH, JOB_DEFS_STATUS_PATH
from procmanager import process_utils
from procmanager import utils
from procmanager.record_store import Store

DB_PATH = config.DB_PATH


def _clear_db(): # for testing
    conn, cur = get_cursor()
    cur.execute("drop table if exists job_instances;")
    cur.execute("""drop table if exists transitions;""")
    conn.commit()

def create_db(conn, cur):
    JOB_INSTANCES =  """Create table if not exists job_instances (id VARCHAR, 
                 jobname VARCHAR,
                 status VARCHAR,
                 started_at INT,
                 finished_at INT,
                 pid INT,
                 had_errors INT
                 );"""
    
    TRANSITIONS = """Create table if not exists transitions (
           origin_id VARCHAR,
           transition_type VARCHAR,  -- NEXT, ERR
           destination_id VARCHAR,
           datetime INT
           );
    """


    cur.execute(JOB_INSTANCES)
    cur.execute(TRANSITIONS)
    conn.commit()

''' Remove after 2026
def create_server_status(conn, cur):
    SERVER_STATUS = """Create table if not exists server_status (
        pid INT,
        status VARCHAR
        );
    """
    cur.execute(SERVER_STATUS)
    conn.commit()
    '''


class C:
    """ Holds connection. TODO remove not sure it helps """
    def __init__(self):
        new_db = not os.path.exists(DB_PATH)
        self.conn = sqlite3.connect(DB_PATH, isolation_level=None, timeout=10) # autocommit
        if new_db:
            create_db(self.conn, self.conn.cursor())

c = C()


def get_cursor():
    #new_db = os.path.exists(DB_PATH)
    #conn = sqlite3.connect(DB_PATH, isolation_level=None) # autocommit
    #if new_db:
    #    create_db(conn, cur)
   
    #cur = c.conn.cursor()
    #return c.conn, cur
    conn = sqlite3.connect(DB_PATH, isolation_level=None, timeout=10) # autocommit
    return conn, conn.cursor()

if not os.path.exists(DB_PATH):
    conn, cursor = get_cursor()
    create_db(conn, cursor)

def insert_job_instance(_id, jobname):
    now_ts = datetime.now().timestamp()

    INSERT_JOB = f""" INSERT INTO job_instances VALUES (
                ?,  ?, "NW", ?, NULL, NULL, NULL
                               );"""
    conn, cur = get_cursor()
    cur.execute(INSERT_JOB, (_id, jobname, now_ts))
    conn.commit()    


def list_job_instances(jobname=None, top_down=False, limit=None, offset=None, last=None):
    # TODO remove limit and offset options
    by_jobname = 'where jobname = ?' if jobname else ''
    order_by = 'order by started_at desc' if top_down else ''
    limit_sql = f'limit {limit}' if limit is not None else ''
    offset_sql = f'offset {offset}' if offset is not None else ''

    conn, _ = get_cursor()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if last:
        # TODO Maybe redo this in same way to top_down, with an index on started_at
        COUNT_JOBS = f""" select count(*) from job_instances """
        res = cur.execute(COUNT_JOBS).fetchall()
        count = res[0][0]
        offset = count - last
        last_sql = f'OFFSET {offset}' 
        if limit_sql == '':
            limit_sql = f'limit -1'
    else:
        last_sql = ''

    # with cte, bit complicated for this
    # last_sql = f'LIMIT {last} OFFSET (select c - {last} from const)' if last is not None else ''
    #LIST_JOBS = f"""
    #               WITH const AS (select count(*) as c from job_instances)
    #                select *, coalesce(finished_at, strftime('%s', 'now')) - started_at as running_length from job_instances, const {by_jobname} {order_by} {limit_sql} {offset_sql} {last_sql}"""

    LIST_JOBS = f"""
                    select *, coalesce(finished_at, strftime('%s', 'now')) - started_at as running_length from job_instances {by_jobname} {order_by} {limit_sql} {offset_sql} {last_sql}"""
    # print(LIST_JOBS)

    if jobname:
        res = cur.execute(LIST_JOBS, jobname).fetchall()
    else:
        res = cur.execute(LIST_JOBS).fetchall()
    # print(res)
    #print(cur.description)
    return (dict(r) for r in res)




def create_job_instance(jobname) -> str:
    encoded_timestamp = utils.encode_timestamp(datetime.now().timestamp())
    # _id = f'{jobname}-{datetime.now().timestamp()}'
    _id = f'{jobname}-{encoded_timestamp}'
    insert_job_instance(_id, jobname)
    return _id

def update_job_instance(_id, **kwargs):
    update_clauses = []
    for k, v in kwargs.items():
        update_clauses.append(f"{k} = ?")
    
    update_clause = ', '.join(update_clauses)
    UPDATE_JOB_INSTANCE = f"""UPDATE job_instances set
        {update_clause}
        where id = ?; """
    conn, cur = get_cursor()
    # print(UPDATE_JOB_INSTANCE)
    #conn.set_trace_callback(print)
    cur.execute(UPDATE_JOB_INSTANCE, (*list(kwargs.values()), _id))
    conn.commit()


def is_process_running(_id, pid):
    running_result = False
    if process_utils.is_running(pid):
        running_result = True
    else:
        update_job_instance(_id, status='EX', finished_at=datetime.now().timestamp())
    return running_result

def is_job_running(jobname):
    """ Checks db if process running, then verifies if pid
       is really running, clears up if not """
    IS_JOB_RUNNING = f"""SELECT id, pid from job_instances where
         jobname = ? and
         (status = 'GO') """
         # (status = 'NW' or status = 'GO') """
    conn, cur = get_cursor()
    print(IS_JOB_RUNNING)
    res = list(cur.execute(IS_JOB_RUNNING, (jobname,)).fetchall())
    running_result = False
    for _id, pid in res:
        if is_process_running(_id, pid):
            running_result = True
            #poll_pid(parent_pid)  # poll parent to avoid bob/zombies.
    print(running_result)
    return running_result


def add_transition(orig_id, transition_type, dest_id):
    """ For error, next progressions. transition_type = ERR, NEXT"""

    INSERT_TRANSITION = f"""
    INSERT INTO transitions VALUES (?, ?, ?);
    """
    conn, cur = get_cursor()
    cur.execute(INSERT_TRANSITION, (orig_id, transition_type, dest_id))
    conn.commit()



'''
def update_server_status(pid: int, status: str): 
    conn, cur = get_cursor()
    create_server_status(conn, cur)  # TODO remove after 2026
    UPDATE_SERVER_STATUS = f"""
    DELETE server_status;
    INSERT INTO server_status VALUES (?, ?);"""
    cur.execute(UPDATE_SERVER_STATUS, (pid, status))
    conn.commit()

def get_server_status():
    conn, cur = get_cursor()
    create_server_status(conn, cur)  # TODO remove after 2026
    GET_SERVER_STATUS = f"""
    select * from server_status LIMIT 1;"""
    res = list(cur.execute(GET_SERVER_STATUS))
    for pid, status in res:
        return pid, status
     
'''

def get_server_status():
    s = Store(SERVER_STATUS_PATH, 'server_status')
    statuses = {int(k): v for k, v in s}
    return statuses

def update_server_status(pid: int, status: str):
    s = Store(SERVER_STATUS_PATH, 'server_status')
    s.save(str(pid), status)

def remove_server_status(pid: int):
    s = Store(SERVER_STATUS_PATH, 'server_status')
    s.delete(str(pid))


def set_job_defs_status(status):
    s = Store(JOB_DEFS_STATUS_PATH, 'job_defs_status')
    s.save('status', status)

def get_job_defs_status():
    s = Store(JOB_DEFS_STATUS_PATH, 'job_defs_status')
    return s.get('status')

