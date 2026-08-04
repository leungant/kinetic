import lmdb

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

def put_value():
    try:
        with env.begin(write=True) as txn:
            txn.put(b'key', large_value)
            print(len(large_value))
    except lmdb.MapFullError:
        # Double the map size and retry.
        env.set_mapsize(env.info()['map_size'] * 10)
        print('mapsize')
        print(env.info()['map_size'])
        with env.begin(write=True) as txn:
            print(len(large_value))
            try:
                txn.put(b'key', large_value)
            except lmdb.MapFullError:
                # try again
                put_value() # TODO
            except lmdb.MapResizedError:
                # Call map resize
                env.set_mapsize(0)
            except lmdb.Error:
                print('Couldnt allocate as not enough disk space on this partition')
                # TODO try a smaller map size if there is still disk space.

#for i in range(400):
    #large_value = large_value * 2
    #TODO get this working put_value()


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

def match_subclass(v):
    for k, v in types_to_code_map.items():
        if issubclass(v, k):
            return types_to_code_map[k]
    return 's'


def convert_v_to_typed(ba):
    t_code, v = chr(ba[0]), ba[1:]  # TODO memoryview
    #t_code, v = str(ba[0:1]), ba[1:]  # TODO memoryview
    print(bytes(ba).decode())
    print(t_code)
    print(t_code, v)
    type_ = code_to_types_map[t_code]
    v = type_(v)
    return v

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
