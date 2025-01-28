import requests
import sqlite3
from loguru import logger

class DBCachedDownload:

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.cursor.execute('CREATE TABLE IF NOT EXISTS cache (url TEXT PRIMARY KEY, content BLOB, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')
        self.conn.commit()

    def download(self, url: str) -> bytes:
        self.cursor.execute('SELECT content FROM cache WHERE url = ?', (url,))
        row = self.cursor.fetchone()
        if row:
            logger.debug(f'Cache hit: {url}')
            return row[0]
        else:
            logger.debug(f'Cache miss: {url}')
            response = requests.get(url)
            self.cursor.execute('INSERT INTO cache (url, content) VALUES (?, ?)', (url, response.content))
            self.conn.commit()
            return response.content

    def clear(self, url: str):
        self.cursor.execute('DELETE FROM cache WHERE url = ?', (url,))
        self.conn.commit()

    def close(self):
        self.conn.close()
        