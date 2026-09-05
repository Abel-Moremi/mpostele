// Local, offline-first persistence for the frontend prototype.
//
// Uses sql.js (SQLite compiled to WebAssembly) as the query engine and
// IndexedDB purely as a byte-store for the exported database file, so the
// whole thing runs client-side with no server, cloud service, or native
// dependency. The wasm binary is bundled by Vite (see the `?url` import
// below), so it loads from the local build output rather than a CDN.
import initSqlJs from 'sql.js'
import sqlWasmUrl from 'sql.js/dist/sql-wasm.wasm?url'

const IDB_NAME = 'mpostele'
const IDB_STORE = 'sqlite'
const IDB_ROW_KEY = 'app.sqlite'
const SAVE_DEBOUNCE_MS = 300

let dbPromise = null
let saveTimer = null

function openIndexedDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(IDB_NAME, 1)
    request.onupgradeneeded = () => {
      request.result.createObjectStore(IDB_STORE)
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

async function loadPersistedBytes() {
  const idb = await openIndexedDb()
  return new Promise((resolve, reject) => {
    const tx = idb.transaction(IDB_STORE, 'readonly')
    const req = tx.objectStore(IDB_STORE).get(IDB_ROW_KEY)
    req.onsuccess = () => resolve(req.result ?? null)
    req.onerror = () => reject(req.error)
  })
}

async function persistBytes(bytes) {
  const idb = await openIndexedDb()
  return new Promise((resolve, reject) => {
    const tx = idb.transaction(IDB_STORE, 'readwrite')
    tx.objectStore(IDB_STORE).put(bytes, IDB_ROW_KEY)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

async function openDatabase() {
  const SQL = await initSqlJs({ locateFile: () => sqlWasmUrl })
  const existing = await loadPersistedBytes()
  const db = existing ? new SQL.Database(new Uint8Array(existing)) : new SQL.Database()

  db.run(`
    CREATE TABLE IF NOT EXISTS settings (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    );
  `)

  return db
}

function getDb() {
  if (!dbPromise) dbPromise = openDatabase()
  return dbPromise
}

function scheduleSave(db) {
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    persistBytes(db.export())
  }, SAVE_DEBOUNCE_MS)
}

/**
 * Reads a single stored setting value (as a raw string), or `null` if unset.
 */
export async function getSetting(key) {
  const db = await getDb()
  const result = db.exec('SELECT value FROM settings WHERE key = ?', [key])
  if (result.length === 0 || result[0].values.length === 0) return null
  return result[0].values[0][0]
}

/**
 * Writes (or updates) a single setting value and schedules a debounced
 * persist of the whole database out to IndexedDB.
 */
export async function setSetting(key, value) {
  const db = await getDb()
  db.run(
    `INSERT INTO settings (key, value) VALUES (?, ?)
     ON CONFLICT(key) DO UPDATE SET value = excluded.value`,
    [key, value]
  )
  scheduleSave(db)
}
