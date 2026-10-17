from datetime import datetime
import lmdb

''' 
For string storage, you may as well used a plain Store. For typed values, TypedStore is available.

'''
'''
TODOS:
    integrate put_value exception catching with the @lmdb_retryer decorator
    decide whether to use inheritance or not - not probably - X
    once have used it a bit decide resizing quantity strategy


    - sqlite backend
    - duckdb backend
    - sql interface for lmdb kv?
'''

# TODO set map_size larger
TEST_MAP_SIZE = 1024
MAP_SIZE = 100 * 1024 * 1024
#large_value = "asdfselfjlkjlkjalkesjflskejlkfjl" * 100
large_value = "asdfselfjlkjlkjalkesjflskejlkfjl" 
#large_value = "a" * 2147483648
#large_value = "a" * 1847483648
#large_value = large_value.encode()

if __name__ == '__main__':
    #env = lmdb.open('/tmp/mydb', map_size=256)
    env = lmdb.open('/tmp/mydb', map_size=len(large_value))
    #pass

# os page size multiple default
# 10485760 
# get os page size? - is 4096 on dev linux machine
# one env per process? share among threads?
# catch mdb_map_resized error
# EINVAL-  lmdb api suggests that lmdb itself will return error if active write transaction attempted during set_mapsize. 
# only one way to find out.
# add read AND write transactions
# ordered map interface - how are keys sorted? iterate through to see. lexi
# need to understand the threadedness of pylmdb
# use overwrite=False to ensure you dont use the same new id.
# generate id mode and not.
# is it key/value or is it object "storage"? 
#     - start with key value, with types?


def put_value(key, value):
    try:
        with env.begin(write=True) as txn:
            txn.put(key.encode(), value.encode()) # b'key'
            print(len(value))
    except lmdb.MapFullError:
        # Double the map size and retry.
        increase_map_size()
        print('mapsize resized')
        print(env.info()['map_size'])
        put_value(key, value)
    except lmdb.MapResizedError:
        # Call map resize to refresh the stored mapsize
        env.set_mapsize(0)
        put_value(key, value)


import threading
import time
#env1 = lmdb.open('/tmp/mydb', map_size=len(large_value))
def open_transaction():
    # env1 = lmdb.open('/tmp/mydb', map_size=len(large_value))
    with env.begin(write=True) as txn:
        txn.put(b'k1', b'asdfsd')
        time.sleep(5)

def spawn_open_transaction():
    t=threading.Thread(target=open_transaction)
    t.start()

def increase_map_size():
    try:
        env.set_mapsize(env.info()['map_size'] * 30)
    except lmdb.Error as e:
        if 'Cannot set_mapsize while a write transaction is active' in str(e):
            print('error resizing db, a write transaction was open')
            time.sleep(1)
            return increase_map_size()
        #'mdb_txn_commit: Input/output error'
        if 'Input/output error' in str(e):
            print('Couldnt allocate as not enough disk space on this partition')
            # TODO try a smaller map size if there is still disk space.
            quit()
    # Preemptively reset stored mapsize. One env per process.
    env.set_mapsize(0)
    return True


def test_map_size_errors():
    # Test map size errors etc.
    increase_map_size()            
    t2=threading.Thread(target=open_transaction)
    #t2.start()
    #open_transaction()

    #quit()

    for i in range(400):
        large_value = large_value * 2
        #TODO get this working put_value()
        put_value('k', large_value)
        if i == 10:
            t2.start()

    quit()


def lmdb_retryer(f):
    def inner(*args, **kwargs):
        return f(*args, **kwargs)
    return inner

from decimal import Decimal
types_to_code_map = {
        int: 'i',
        float: 'f',
        Decimal: 'D',
        str: 's',
        bool: 'l',

        }

code_to_types_map = {v: k for k, v in types_to_code_map.items()}

def match_subclass(value):
    for k, code in types_to_code_map.items():
        if issubclass(type(value), k):
            return types_to_code_map[k]
    return 's'


def convert_v_to_typed(ba):
    t_code, v = chr(ba[0]), ba[1:]  # TODO memoryview
    #t_code, v = str(ba[0:1]), ba[1:]  # TODO memoryview
    print(bytes(ba).decode())
    print(t_code)
    print(t_code, v)
    type_ = code_to_types_map[t_code]
    print('cvtt')
    print(type_, v)
    if issubclass(type_, str):
        v = v.decode()
    else:
        v = type_(v)
    return v

def convert_k_to_id_and_name(k):
    print( k.split(':', 1) )
    parts = k.split(':', 1)
    print(len(parts), parts[0], parts[1])
    _id, name = (parts[0], parts[1]) if len(parts) > 1 else (parts[0], None)
    return _id, name

class CodedDocumentStore:
    pass

class DocumentStore:
    def __init__(self, path='record_store.db', db_name=None):
        self.path = path
        self.db_name = db_name.encode() if isinstance(db_name, str) else db_name
        self.db = self._get_db(self.path, self.db_name)
        # TODO one write at a time. classmethod/var lock
        
    def _get_db(self, path, db):
        self.env = lmdb.open(path, max_dbs=999, readonly=False)
        # Interface is:
        # db = env.open_db(None)  # For main database
        # db = env.open_db(b'record_store') # for sub database
        return self.env.open_db(self.db_name)

    def remove(self, document):
        # delete document given transaction

        #TODO IMPLEMENT
        raise NotImplementedError

    def update(self, update_document):
        #TODO IMPLEMENT
        raise NotImplementedError


    def save(self, document, generated_id=False):
        # 1) find and remove existing document by _id
        # as part of transaction

        # 2) insert document
        if '_id' in document and generated_id is False:
            _id = document['_id']
        else:
            _id = datetime.timestamp(datetime.now())
            generated_id = True  # regen if transaction fails.
        try:
            with self.env.begin(write=True, db=self.db) as txn:
                for k, v in document.items():
                    print(k, v)
                    # encode key
                    k = f'{_id}:{k}'
                    print('key', k)
                    # encode value
                    t = types_to_code_map.get(type(v)) 
                    if t is None:
                        t = match_subclass(v)
                    v = f'{t}{v}'
                    res = txn.put(k.encode(), v.encode())
            return res
        except Exception as e:
            print(e)
            import time
            time.sleep(1) # todo expo, jitter, async etc
            return self.save(document, generated_id)  # todo test


    def find(self, **kwargs):
        skip_entry = False
        entry = {}
        for k, v in self.__iter__():
            print(k,v)
            _id, name = convert_k_to_id_and_name(k)
            if name is None:
                # is new entry
                if skip_entry is False:
                    yield entry
                skip_entry = False
                entry = {}

            if name is None:  # _id
                if '_id' in kwargs:
                    arg_id = kwargs['_id']
                    if arg_id != _id:
                        skip_entry = True
                        continue

            if name in kwargs:
                arg_value = kwargs[name]
                if v != arg_value: 
                    skip_entry = True
                    continue

            # otherwise keep building entry
            print(v)
            entry[name] = v

        yield entry

    def find_one(self, **filters):  # TODO move downwards
        for entry in self.find(**filters):
            yield entry
            return

    def __iter__(self):
        with self.env.begin(write=False, db=self.db ) as txn:
            with txn.cursor() as cursor:
                for k, v in cursor:
                    yield k.decode(), convert_v_to_typed(v)  # v.decode()

            

 
if __name__ == '__main__':
    ds = DocumentStore()
    from datetime import datetime
    document = {'a': 'b23', 'b': 'c35', 'c': 'e355', 'd': 2, 'dt': datetime.now()}
    ds.save(document)
    print(list(ds.find()))
    print(list(ds.find_one()))

if __name__ == '__main__':
    spawn_open_transaction()

if __name__ == '__main__':
    test_map_size_errors()
    quit()

class TypedStore:
    def __init__(self, path='record_store.db', sub_db=None):
        self.path = path
        # String is a subdatabase, None is just the main database (default)
        self.db_name = sub_db.encode() if isinstance(sub_db, str) else sub_db
        self.db = self._get_db(self.path, self.db_name)

    def _get_db(self, path, db):
        self.env = lmdb.open(path, max_dbs=999, readonly=False)
        # Interface is:
        # db = env.open_db(None)  # For main database
        # db = env.open_db(b'record_store') # for sub database
        return self.env.open_db(self.db_name)

    @lmdb_retryer
    def save(self, k, v):
        t = types_to_code_map.get(type(v)) 
        if t is None:
            t = match_subclass(v)
        v = f'{t}{v}' 
        with self.env.begin(write=True, db=self.db) as txn:
            res = txn.put(k.encode(), v.encode())
        return res

    @lmdb_retryer
    def get(self, k):
        print(self.db_name)
        print(self.db)
        with self.env.begin(write=False, db=self.db, buffers=True) as txn: # buffers=True means use memoryviews
            v = txn.get(k.encode())
        return convert_v_to_typed(v)
        # return .decode() if isinstance(res, bytes ) else res

    @lmdb_retryer
    def delete(self, k):
        with self.env.begin(write=True, db=self.db) as txn:
            res = txn.delete(k.encode())
        return res.decode() if isinstance(res, bytes ) else res

    @lmdb_retryer
    def __iter__(self):
        with self.env.begin(write=False, db=self.db, buffers=True) as txn: # buffers True => use memoryviews
            with txn.cursor() as cursor:
                for k, v in cursor:
                    yield k.decode(), convert_v_to_typed(v)  # v.decode()
        # return res.decode() if isinstance(res, bytes ) else res
        return

s = TypedStore('./testdb')
s.save('asdf', 'asdfsaf')
s.get('asdf')


class Store:
    def __init__(self, path='record_store.db', sub_db=None):
        self.path = path
        # String is a subdatabase, None is just the main database (default)
        self.db_name = sub_db.encode() if isinstance(sub_db, str) else sub_db
        self.db = self._get_db(self.path, self.db_name)

    def _get_db(self, path, db):
        self.env = lmdb.open(path, max_dbs=999, readonly=False)
        # Interface is:
        # db = env.open_db(None)  # For main database
        # db = env.open_db(b'record_store') # for sub database
        return self.env.open_db(self.db_name)

    @lmdb_retryer
    def save(self, k, v):
        with self.env.begin(write=True, db=self.db) as txn:
            res = txn.put(k.encode(), v.encode())
        return res

    @lmdb_retryer
    def get(self, k):
        print(self.db_name)
        print(self.db)
        with self.env.begin(write=False, db=self.db, buffers=True) as txn: # buffers True => use memoryviews
            res = txn.get(k.encode())
        return res.decode() if isinstance(res, bytes ) else res

    @lmdb_retryer
    def delete(self, k):
        with self.env.begin(write=True, db=self.db) as txn:
            res = txn.delete(k.encode())
        return res.decode() if isinstance(res, bytes ) else res

    @lmdb_retryer
    def __iter__(self):
        with self.env.begin(write=False, db=self.db, buffers=True) as txn: # buffers True => use memoryviews
            with txn.cursor() as cursor:
                for k, v in cursor:
                    yield bytes(k).decode(), bytes(v).decode()
        # return res.decode() if isinstance(res, bytes ) else res
        return

if __name__ =='__main__':
    st = Store('./testrecords.db', 'test')
    #res = put_record('nwe', 'va', 'newdb2')
    res = st.get('nwe')
    print(res)
    res = st.save('nwe', 'newdb3123')
    print(res)
    res = st.save('nwe2', 'newvalue')
    print(res)
    print([k for k in st])
    print([(k, v) for k, v in st])
    print('delete record')
    res = st.delete('nwe2')
    print([(k, v) for k, v in st])
    quit()


    # drop newdb, newdb2
    for db_name in ['newdb', 'newdb2', 'newdb3']:
        dbo = env.open_db(db_name.encode())
        with env.begin(write=True, db=dbo) as txn:
            txn.drop(dbo)
            print(env.stat())

