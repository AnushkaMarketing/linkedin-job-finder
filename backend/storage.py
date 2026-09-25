import ctypes
import json
import os
import sqlite3
import sys
import threading
import time
from pathlib import Path
from cryptography.fernet import Fernet


def windows_protect(data: bytes, decrypt: bool = False) -> bytes:
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buf = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    src, dest = Blob(len(data), buf), Blob()
    function = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(src), None, None, None, None, 1, ctypes.byref(dest)):
        raise OSError('Windows key protection failed')
    try:
        return ctypes.string_at(dest.data, dest.size)
    finally:
        ctypes.windll.kernel32.LocalFree(ctypes.cast(dest.data, ctypes.c_void_p))


class Store:
    def __init__(self, folder: Path):
        folder.mkdir(parents=True, exist_ok=True)
        self.folder = folder
        keyfile = folder / 'vault.key'
        if keyfile.exists():
            key = keyfile.read_bytes()
            if sys.platform == 'win32': key = windows_protect(key, True)
        else:
            key = Fernet.generate_key()
            secured = windows_protect(key) if sys.platform == 'win32' else key
            fd = os.open(keyfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as handle: handle.write(secured)
        self.cipher = Fernet(key)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(folder / 'intelligence.sqlite', check_same_thread=False)
        self.db.execute('PRAGMA secure_delete=ON')
        self.db.execute('CREATE TABLE IF NOT EXISTS records (bucket TEXT, key TEXT, payload BLOB, expires REAL, PRIMARY KEY(bucket,key))')
        self.db.commit()

    def put(self, bucket: str, key: str, value, ttl: float = 0):
        data = self.cipher.encrypt(json.dumps(value, ensure_ascii=False).encode())
        with self.lock:
            self.db.execute('INSERT OR REPLACE INTO records VALUES (?,?,?,?)', (bucket, key, data, time.time() + ttl if ttl else 0))
            self.db.commit()

    def get(self, bucket: str, key: str, default=None):
        with self.lock:
            row = self.db.execute('SELECT payload, expires FROM records WHERE bucket=? AND key=?', (bucket, key)).fetchone()
            if not row: return default
            if row[1] and row[1] < time.time():
                self.delete(bucket, key); return default
            return json.loads(self.cipher.decrypt(row[0]))

    def items(self, bucket: str) -> list:
        with self.lock:
            keys = self.db.execute('SELECT key FROM records WHERE bucket=?', (bucket,)).fetchall()
        return [v for key, in keys if (v := self.get(bucket, key)) is not None]

    def delete(self, bucket: str, key: str):
        with self.lock:
            self.db.execute('DELETE FROM records WHERE bucket=? AND key=?', (bucket, key)); self.db.commit()

    def clear(self):
        with self.lock:
            self.db.execute('DELETE FROM records'); self.db.commit(); self.db.execute('VACUUM')

    def close(self):
        self.db.close()
