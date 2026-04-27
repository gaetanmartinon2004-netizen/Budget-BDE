from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterator

import psycopg2
from psycopg2.extras import DictCursor

from .justificatifs import ensure_pole_directories
from .paths import database_file, justificatifs_root, mandat_database_file, mandats_database_file


DATABASE_URL = os.environ.get("DATABASE_URL")


DEFAULT_BUDGET_TREE: list[tuple[str, list[tuple[str, list[str]]]]] = [
    (
        "Pôle Pilote",
        [
            ("Administration", [
                "Frais de gestion ACEITC",
                "Frais Banque",
                "Fournitures de bureau + Cordonnerie",
                "Matériel",
                "Divers / Imprévu",
            ]),
            ("Financement", [
                "Cotisations Élèves (10/12)",
                "Cotisations Élèves (2/12)",
                "Aide École",
            ]),
            ("Partenariats / Réseaux", ["AFEB", "Builders", "BDE Arche"]),
            ("Événements & Actions", ["FORUM", "SOSO"]),
            ("Produits", ["Distributeur", "Pull de promo"]),
        ],
    ),
    (
        "Pôle Event",
        [
            ("Infrastructure", [
                "Location salle",
                "Salle",
                "Sécurité / Vigile",
                "Sécurité civile",
            ]),
            ("Restauration & Boissons", [
                "Traiteur",
                "Nourriture / Boissons",
                "Boissons",
                "Coupes de champagne",
            ]),
            ("Production Événement", [
                "DJ",
                "Lumière / Son",
                "Film / Aftermovie",
                "Bâche / Stand photo",
            ]),
            ("Logistique", ["Transport", "Produits ménagers", "Eco-cup"]),
            ("Communication", ["Impression papier", "Concours affiches"]),
            ("Revenus", ["Préventes", "Pré-ventes TC1 à TC5", "Sponsors"]),
            ("Décoration", ["Décoration salle / table / stand"]),
            ("Divers", ["Imprévus / dégradations", "Divers et aléas"]),
            ("Merch événementiel", ["Vêtements", "Activités"]),
        ],
    ),
    (
        "Pôle Com",
        [
            ("Contenu", ["Yearbook", "Photos KFET"]),
            ("Outils", ["Canva Pro", "Crédit Imprimante", "Carte SD"]),
            ("Matériel", ["Caméra"]),
            ("Abonnements", ["Abonnement"]),
        ],
    ),
    (
        "Pôle Art",
        [
            ("Événements", ["Décoration Semaine Art", "Activités Semaine Art"]),
            ("Sorties", ["Cinéma / Théâtre / Musées / Expositions"]),
            ("Création", ["Poterie / Peinture / Sculpture"]),
        ],
    ),
    (
        "Pôle Huma",
        [
            ("Événements solidaires", [
                "Octobre Rose dons",
                "Builders Run participation",
                "Builders Run don entreprises",
                "Builders Run nourriture",
            ]),
            ("Activités", ["Laser game", "Bowling", "Parcours pompiers"]),
            ("Cohésion", ["Aprem Cohésion achats", "Aprem Cohésion boissons"]),
            ("Bien-être", ["Sophrologie / Relaxation"]),
            ("Formation", ["Formation PSC1", "Sensibilisation ASSE matériel"]),
            ("Événements internes", ["Soirée K-fêt", "Tombola"]),
            ("Produits / ventes", ["Calendrier impression + vente", "Déco / Gobelets", "Sapin"]),
            ("Récompenses", ["Gain concours photos", "Cadeaux journaliers"]),
            ("Repas", ["Repas laser game"]),
        ],
    ),
    (
        "Pôle DDRS",
        [
            ("Environnement", ["Sac poubelle / gants / pince", "Boîte à compost"]),
            ("Événements", ["Trail vélo (repas / carburant)", "Préventes trail vélo"]),
            ("Activités", ["Matériel pêche à l’aimant", "Camping"]),
            ("Communication", ["Conférence", "Affichages"]),
            ("Financement", ["Dons", "Sponsors"]),
        ],
    ),
    (
        "Pôle Lignes de vêtements",
        [
            ("Ligne École", ["Sweat brodé ligne école"]),
            ("Ligne BDE", ["Tshirt ligne BDE"]),
            ("Accessoires", ["Casquette", "Tote-bag", "Accessoires gala"]),
            ("Ligne Sport", ["Shorts ligne sport", "Veste / Pull ligne sport", "Maillot ligne sport"]),
        ],
    ),
    (
        "Pôle Sport",
        [
            ("Événements Ski", ["SKI Mania J1 à J4", "Weekend SKI (inscription / déplacement / logement / nourriture / forfait)"]),
            ("Compétitions", ["Derby (inscription / transport)", "Tournoi foot", "Tournoi pétanque", "Tournoi paddle"]),
            ("Activités", ["Tir à l’arc", "Hockey sur glace"]),
            ("Interpromo", ["Activités sportives interpromo", "Lots interpromo"]),
        ],
    ),
    (
        "Pôle KFET",
        [
            ("Restauration quotidienne", ["Midi Burger", "Midi Sandwich", "Snacks + Canettes", "Petits Déjeuners"]),
            ("Événements", [
                "Soirées KFET repas + soft / décos",
                "Soirées BONUS repas / soft",
                "Méchoui repas / soft",
                "Banquets repas / soft",
                "Inter KFET repas / soft / after",
            ]),
            ("Achats", ["Achats matériels KFET", "Produits d’entretien"]),
            ("Autres", ["Repas Five", "Imprévu"]),
        ],
    ),
]

DEFAULT_POLE_COLORS: dict[str, str] = {
    "pilot": "#91c4f4",
    "event": "#cdacd4",
    "com": "#ffae48",
    "art": "#cdc1a6",
    "huma": "#f8e27e",
    "ddrs": "#afc479",
    "lignes": "#dfd9cd",
    "sport": "#6644b4",
    "kfet": "#a1c9be",
    "default": "#83c9ff",
}


def default_pole_color(pole_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(pole_name or "")).encode("ascii", "ignore").decode("ascii").lower()
    if "pilot" in normalized:
        return DEFAULT_POLE_COLORS["pilot"]
    if "event" in normalized:
        return DEFAULT_POLE_COLORS["event"]
    if "com" in normalized:
        return DEFAULT_POLE_COLORS["com"]
    if "art" in normalized:
        return DEFAULT_POLE_COLORS["art"]
    if "huma" in normalized:
        return DEFAULT_POLE_COLORS["huma"]
    if "ddrs" in normalized:
        return DEFAULT_POLE_COLORS["ddrs"]
    if "lignes" in normalized:
        return DEFAULT_POLE_COLORS["lignes"]
    if "sport" in normalized:
        return DEFAULT_POLE_COLORS["sport"]
    if "kfet" in normalized:
        return DEFAULT_POLE_COLORS["kfet"]
    return DEFAULT_POLE_COLORS["default"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def using_postgres() -> bool:
    return bool(DATABASE_URL)


def _convert_placeholders(query: str) -> str:
    out: list[str] = []
    in_single_quote = False
    prev = ""
    for ch in query:
        if ch == "'" and prev != "\\":
            in_single_quote = not in_single_quote
        if ch == "?" and not in_single_quote:
            out.append("%s")
        else:
            out.append(ch)
        prev = ch
    return "".join(out)


def _adapt_sql_for_postgres(query: str) -> str:
    adapted = _convert_placeholders(query)
    adapted = re.sub(
        r"INSERT\s+OR\s+IGNORE\s+INTO",
        "INSERT INTO",
        adapted,
        flags=re.IGNORECASE,
    )
    if re.search(r"INSERT\s+INTO[\s\S]*ON\s+CONFLICT", adapted, flags=re.IGNORECASE):
        return adapted
    if re.match(r"\s*INSERT\s+INTO", adapted, flags=re.IGNORECASE) and "OR IGNORE" in query.upper():
        adapted = f"{adapted} ON CONFLICT DO NOTHING"
    return adapted


class CompatConnection:
    def __init__(self, backend: str, conn: Any):
        self.backend = backend
        self._conn = conn

    def execute(self, query: str, params: tuple | list | None = None):
        if self.backend == "sqlite":
            if params is None:
                return self._conn.execute(query)
            return self._conn.execute(query, params)

        pg_query = _adapt_sql_for_postgres(query)
        cur = self._conn.cursor(cursor_factory=DictCursor)
        cur.execute(pg_query, tuple(params or ()))
        if pg_query.lstrip().upper().startswith("INSERT") and "RETURNING" not in pg_query.upper():
            try:
                last_id_cur = self._conn.cursor(cursor_factory=DictCursor)
                last_id_cur.execute("SELECT LASTVAL() AS id")
                row = last_id_cur.fetchone()
                cur.lastrowid = int(row["id"]) if row and "id" in row and row["id"] is not None else None
                last_id_cur.close()
            except Exception:
                cur.lastrowid = None
        return cur

    def executemany(self, query: str, params_seq: list[tuple] | list[list]):
        if self.backend == "sqlite":
            return self._conn.executemany(query, params_seq)

        pg_query = _adapt_sql_for_postgres(query)
        cur = self._conn.cursor(cursor_factory=DictCursor)
        cur.executemany(pg_query, params_seq)
        return cur

    def executescript(self, script: str):
        if self.backend == "sqlite":
            return self._conn.executescript(script)

        cur = self._conn.cursor(cursor_factory=DictCursor)
        statements = [stmt.strip() for stmt in script.split(";") if stmt.strip()]
        for statement in statements:
            cur.execute(statement)
        return cur

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()


def _configure_sqlite_connection(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # Keep one physical file per DB (no -wal/-shm side files).
    conn.execute("PRAGMA journal_mode = DELETE")
    conn.execute("PRAGMA synchronous = NORMAL")


def get_connection() -> CompatConnection:
    if using_postgres():
        pg_conn = psycopg2.connect(DATABASE_URL)
        pg_conn.autocommit = False
        return CompatConnection("postgres", pg_conn)

    db_file = mandats_database_file()
    db_file.parent.mkdir(parents=True, exist_ok=True)
    sqlite_conn = sqlite3.connect(db_file, timeout=30)
    _configure_sqlite_connection(sqlite_conn)

    # Initialize schema if DB is empty
    cursor = sqlite_conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mandats'")
    if not cursor.fetchone():
        _create_full_schema(sqlite_conn)
        sqlite_conn.commit()

    # Migrate from legacy budget.db if needed
    _migrate_mandats_from_budget_db(sqlite_conn)

    return CompatConnection("sqlite", sqlite_conn)


@contextmanager
def connection() -> Iterator[CompatConnection]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_mandat_connection(mandat_id: int) -> CompatConnection:
    if using_postgres():
        return get_connection()

    db_file = _resolve_mandat_database_file(mandat_id)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    sqlite_conn = sqlite3.connect(db_file, timeout=30)
    _configure_sqlite_connection(sqlite_conn)
    return CompatConnection("sqlite", sqlite_conn)


@contextmanager
def connection_for_mandat(mandat_id: int) -> Iterator[CompatConnection]:
    if using_postgres():
        with connection() as conn:
            yield conn
        return

    ensure_mandat_database(mandat_id)
    conn = get_mandat_connection(mandat_id)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_mandat_database(mandat_id: int) -> None:
    if using_postgres():
        return

    db_file = _resolve_mandat_database_file(mandat_id)
    legacy_db_file = mandat_database_file(mandat_id)

    if db_file != legacy_db_file and legacy_db_file.exists() and not db_file.exists():
        db_file.parent.mkdir(parents=True, exist_ok=True)
        legacy_db_file.replace(db_file)

    if db_file.exists():
        with sqlite3.connect(db_file, timeout=30) as target:
            _configure_sqlite_connection(target)
            _create_full_schema(target)
            _ensure_local_mandat_state(target, mandat_id)
        return

    db_file.parent.mkdir(parents=True, exist_ok=True)
    target = sqlite3.connect(db_file, timeout=30)
    _configure_sqlite_connection(target)

    try:
        _create_full_schema(target)
        _copy_mandat_data_from_main(target, mandat_id)
        _ensure_local_mandat_state(target, mandat_id)
        target.commit()
    except Exception:
        target.rollback()
        raise
    finally:
        target.close()


def _ensure_local_mandat_state(target: sqlite3.Connection, mandat_id: int) -> None:
    """Ensure a mandat DB contains only its own metadata and a base node tree when empty."""
    with connection() as source:
        mandat = source.execute(
            "SELECT id, name, date_debut, date_fin, active, created_at FROM mandats WHERE id = ?",
            (mandat_id,),
        ).fetchone()

    if mandat is None:
        target.execute(
            "INSERT OR IGNORE INTO mandats (id, name, date_debut, date_fin, active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (mandat_id, f"Mandat {mandat_id}", "2025-01-01", "2025-12-31", 0, utc_now()),
        )
    else:
        target.execute(
            """INSERT INTO mandats (id, name, date_debut, date_fin, active, created_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   name = excluded.name,
                   date_debut = excluded.date_debut,
                   date_fin = excluded.date_fin,
                   active = excluded.active,
                   created_at = excluded.created_at""",
            (
                int(mandat["id"]),
                str(mandat["name"]),
                str(mandat["date_debut"]),
                str(mandat["date_fin"]),
                int(mandat["active"]),
                str(mandat["created_at"]),
            ),
        )

    nodes_count = int(target.execute("SELECT COUNT(*) FROM budget_nodes WHERE mandat_id = ?", (mandat_id,)).fetchone()[0])
    if nodes_count == 0:
        _seed_default_nodes_for_mandat(target, mandat_id)


def delete_mandat_database(mandat_id: int, mandat_name: str | None = None) -> None:
    if using_postgres():
        return

    candidates = {mandat_database_file(mandat_id)}
    candidates.add(_resolve_mandat_database_file(mandat_id, mandat_name=mandat_name, use_main_lookup=False))

    with connection() as conn:
        row = conn.execute(
            "SELECT db_filename FROM mandat_db_files WHERE mandat_id = ?",
            (mandat_id,),
        ).fetchone()
        if row and row["db_filename"]:
            legacy = mandat_database_file(mandat_id)
            candidates.add(legacy.parent / str(row["db_filename"]))
        conn.execute("DELETE FROM mandat_db_files WHERE mandat_id = ?", (mandat_id,))

    for db_file in candidates:
        if db_file.exists():
            db_file.unlink()
        wal_file = Path(f"{db_file}-wal")
        shm_file = Path(f"{db_file}-shm")
        if wal_file.exists():
            wal_file.unlink()
        if shm_file.exists():
            shm_file.unlink()


def _slugify_mandat_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode("ascii")
    lowered = normalized.lower()
    lowered = re.sub(r"[^a-z0-9]+", "_", lowered)
    lowered = lowered.strip("_")
    return lowered or "mandat"


def _resolve_mandat_database_file(
    mandat_id: int,
    mandat_name: str | None = None,
    use_main_lookup: bool = True,
) -> Path:
    legacy = mandat_database_file(mandat_id)

    with connection() as conn:
        mapped = conn.execute(
            "SELECT db_filename FROM mandat_db_files WHERE mandat_id = ?",
            (mandat_id,),
        ).fetchone()
        if mapped and mapped["db_filename"]:
            return legacy.parent / str(mapped["db_filename"])

    if mandat_name:
        db_filename = f"budget_{_slugify_mandat_name(mandat_name)}.db"
        if use_main_lookup:
            with connection() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO mandat_db_files (mandat_id, db_filename, created_at) VALUES (?, ?, ?)",
                    (mandat_id, db_filename, utc_now()),
                )
        return legacy.parent / db_filename

    if use_main_lookup:
        with connection() as conn:
            row = conn.execute("SELECT name FROM mandats WHERE id = ?", (mandat_id,)).fetchone()
            if row and row["name"]:
                db_filename = f"budget_{_slugify_mandat_name(str(row['name']))}.db"
                conn.execute(
                    "INSERT OR IGNORE INTO mandat_db_files (mandat_id, db_filename, created_at) VALUES (?, ?, ?)",
                    (mandat_id, db_filename, utc_now()),
                )
                return legacy.parent / db_filename

    return legacy



def _migrate_mandats_from_budget_db(mandats_conn: sqlite3.Connection) -> None:
    """Migrate mandats from legacy budget.db to mandats.db if needed."""
    # Check if mandats_conn already has mandats
    current_count = int(mandats_conn.execute("SELECT COUNT(*) FROM mandats").fetchone()[0])
    if current_count > 0:
        return
    
    # Try to read from legacy budget.db
    budget_db_path = database_file()
    if not budget_db_path.exists():
        return
    
    try:
        legacy_conn = sqlite3.connect(budget_db_path, timeout=5)
        legacy_conn.row_factory = sqlite3.Row
        
        # Check if mandats table exists in budget.db
        cursor = legacy_conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mandats'")
        if not cursor.fetchone():
            legacy_conn.close()
            return
        
        # Copy mandats from budget.db to mandats.db
        cursor = legacy_conn.execute("SELECT id, name, date_debut, date_fin, active, created_at FROM mandats")
        rows = cursor.fetchall()
        
        for row in rows:
            mandats_conn.execute(
                "INSERT OR IGNORE INTO mandats (id, name, date_debut, date_fin, active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (row["id"], row["name"], row["date_debut"], row["date_fin"], row["active"], row["created_at"])
            )
        
        mandats_conn.commit()
        legacy_conn.close()
    except Exception as e:
        pass


def _create_full_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS mandats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            date_debut TEXT NOT NULL,
            date_fin TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS budget_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mandat_id INTEGER NOT NULL,
            parent_id INTEGER,
            name TEXT NOT NULL,
            pole_color TEXT,
            created_at TEXT NOT NULL,
            deleted_at TEXT,
            FOREIGN KEY (mandat_id) REFERENCES mandats(id),
            FOREIGN KEY (parent_id) REFERENCES budget_nodes(id),
            UNIQUE(mandat_id, parent_id, name)
        );

        CREATE TABLE IF NOT EXISTS yearly_budgets (
            mandat_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            flow_type TEXT NOT NULL,
            amount REAL NOT NULL,
            PRIMARY KEY (mandat_id, year, flow_type),
            FOREIGN KEY (mandat_id) REFERENCES mandats(id)
        );

        CREATE TABLE IF NOT EXISTS budget_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mandat_id INTEGER NOT NULL,
            node_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            flow_type TEXT NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (mandat_id) REFERENCES mandats(id),
            FOREIGN KEY (node_id) REFERENCES budget_nodes(id)
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mandat_id INTEGER NOT NULL,
            node_id INTEGER NOT NULL,
            flow_type TEXT NOT NULL,
            amount REAL NOT NULL,
            label TEXT,
            description TEXT,
            date TEXT NOT NULL,
            payment_method TEXT,
            order_number TEXT,
            created_at TEXT NOT NULL,
            deleted_at TEXT,
            FOREIGN KEY (mandat_id) REFERENCES mandats(id),
            FOREIGN KEY (node_id) REFERENCES budget_nodes(id)
        );

        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            deleted_at TEXT,
            FOREIGN KEY (transaction_id) REFERENCES transactions(id)
        );
        """
    )
    _migrate_budget_nodes_unique_constraint(conn)
    _migrate_transactions_order_number_column(conn)


def _copy_rows(source: sqlite3.Connection, target: sqlite3.Connection, query: str, insert_sql: str, params: tuple) -> None:
    rows = source.execute(query, params).fetchall()
    if not rows:
        return
    target.executemany(insert_sql, [tuple(row) for row in rows])


def _copy_mandat_data_from_main(target: sqlite3.Connection, mandat_id: int) -> None:
    with connection() as source:
        mandat = source.execute("SELECT * FROM mandats WHERE id = ?", (mandat_id,)).fetchone()
        if mandat is None:
            now = utc_now()
            target.execute(
                "INSERT OR REPLACE INTO mandats (id, name, date_debut, date_fin, active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (mandat_id, f"Mandat {mandat_id}", "2025-01-01", "2025-12-31", 1, now),
            )
        else:
            target.execute(
                "INSERT OR REPLACE INTO mandats (id, name, date_debut, date_fin, active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    int(mandat["id"]),
                    str(mandat["name"]),
                    str(mandat["date_debut"]),
                    str(mandat["date_fin"]),
                    int(mandat["active"]),
                    str(mandat["created_at"]),
                ),
            )

        _copy_rows(
            source,
            target,
            "SELECT id, mandat_id, parent_id, name, pole_color, created_at, deleted_at FROM budget_nodes WHERE mandat_id = ? ORDER BY id",
            "INSERT INTO budget_nodes (id, mandat_id, parent_id, name, pole_color, created_at, deleted_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (mandat_id,),
        )
        _copy_rows(
            source,
            target,
            "SELECT id, mandat_id, node_id, year, flow_type, amount FROM budget_plans WHERE mandat_id = ? ORDER BY id",
            "INSERT INTO budget_plans (id, mandat_id, node_id, year, flow_type, amount) VALUES (?, ?, ?, ?, ?, ?)",
            (mandat_id,),
        )
        _copy_rows(
            source,
            target,
            "SELECT id, mandat_id, node_id, flow_type, amount, label, description, date, payment_method, order_number, created_at, deleted_at FROM transactions WHERE mandat_id = ? ORDER BY id",
            "INSERT INTO transactions (id, mandat_id, node_id, flow_type, amount, label, description, date, payment_method, order_number, created_at, deleted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (mandat_id,),
        )
        _copy_rows(
            source,
            target,
            "SELECT a.id, a.transaction_id, a.file_path, a.created_at, a.deleted_at FROM attachments a INNER JOIN transactions t ON t.id = a.transaction_id WHERE t.mandat_id = ? ORDER BY a.id",
            "INSERT INTO attachments (id, transaction_id, file_path, created_at, deleted_at) VALUES (?, ?, ?, ?, ?)",
            (mandat_id,),
        )

        nodes_count = int(target.execute("SELECT COUNT(*) FROM budget_nodes WHERE mandat_id = ?", (mandat_id,)).fetchone()[0])
        if nodes_count == 0:
            _seed_default_nodes_for_mandat(target, mandat_id)


def _seed_default_nodes_for_mandat(conn: sqlite3.Connection, mandat_id: int) -> None:
    now = utc_now()
    for pole_name, categories in DEFAULT_BUDGET_TREE:
        pole_cursor = conn.execute(
            "INSERT INTO budget_nodes (mandat_id, parent_id, name, pole_color, created_at) VALUES (?, ?, ?, ?, ?)",
            (mandat_id, None, pole_name, default_pole_color(pole_name), now),
        )
        pole_id = int(pole_cursor.lastrowid)
        for category_name, items in categories:
            category_cursor = conn.execute(
                "INSERT INTO budget_nodes (mandat_id, parent_id, name, created_at) VALUES (?, ?, ?, ?)",
                (mandat_id, pole_id, category_name, now),
            )
            category_id = int(category_cursor.lastrowid)
            for item_name in items:
                conn.execute(
                    "INSERT INTO budget_nodes (mandat_id, parent_id, name, created_at) VALUES (?, ?, ?, ?)",
                    (mandat_id, category_id, item_name, now),
                )


def initialize_database() -> None:
    justificatifs_root().mkdir(parents=True, exist_ok=True)

    if using_postgres():
        _initialize_postgres_database()
        return

    with connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS mandats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                date_debut TEXT NOT NULL,
                date_fin TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS mandat_db_files (
                mandat_id INTEGER PRIMARY KEY,
                db_filename TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                FOREIGN KEY (mandat_id) REFERENCES mandats(id)
            );

            CREATE TABLE IF NOT EXISTS budget_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mandat_id INTEGER NOT NULL,
                parent_id INTEGER,
                name TEXT NOT NULL,
                pole_color TEXT,
                created_at TEXT NOT NULL,
                deleted_at TEXT,
                FOREIGN KEY (mandat_id) REFERENCES mandats(id),
                FOREIGN KEY (parent_id) REFERENCES budget_nodes(id),
                UNIQUE(mandat_id, parent_id, name)
            );

            CREATE TABLE IF NOT EXISTS yearly_budgets (
                mandat_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                flow_type TEXT NOT NULL,
                amount REAL NOT NULL,
                PRIMARY KEY (mandat_id, year, flow_type),
                FOREIGN KEY (mandat_id) REFERENCES mandats(id)
            );

            CREATE TABLE IF NOT EXISTS budget_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mandat_id INTEGER NOT NULL,
                node_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                flow_type TEXT NOT NULL,
                amount REAL NOT NULL,
                FOREIGN KEY (mandat_id) REFERENCES mandats(id),
                FOREIGN KEY (node_id) REFERENCES budget_nodes(id)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mandat_id INTEGER NOT NULL,
                node_id INTEGER NOT NULL,
                flow_type TEXT NOT NULL,
                amount REAL NOT NULL,
                label TEXT,
                description TEXT,
                date TEXT NOT NULL,
                payment_method TEXT,
                order_number TEXT,
                created_at TEXT NOT NULL,
                deleted_at TEXT,
                FOREIGN KEY (mandat_id) REFERENCES mandats(id),
                FOREIGN KEY (node_id) REFERENCES budget_nodes(id)
            );

            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                deleted_at TEXT,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id)
            );
            """
        )
        _migrate_budget_nodes_unique_constraint(conn._conn)
        _migrate_budget_nodes_pole_color_column(conn._conn)
        _migrate_transactions_order_number_column(conn._conn)
        _recover_mandats_from_mandat_dbs(conn)
        _seed_default_mandats_and_nodes(conn)
        for row in conn.execute("SELECT id FROM mandats ORDER BY id").fetchall():
            try:
                ensure_mandat_database(int(row["id"]))
            except Exception:
                continue
        _ensure_justificatifs_structure(conn)


def _initialize_postgres_database() -> None:
    with connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS mandats (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                date_debut TEXT NOT NULL,
                date_fin TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS mandat_db_files (
                mandat_id INTEGER PRIMARY KEY,
                db_filename TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                FOREIGN KEY (mandat_id) REFERENCES mandats(id)
            );

            CREATE TABLE IF NOT EXISTS budget_nodes (
                id SERIAL PRIMARY KEY,
                mandat_id INTEGER NOT NULL,
                parent_id INTEGER,
                name TEXT NOT NULL,
                pole_color TEXT,
                created_at TEXT NOT NULL,
                deleted_at TEXT,
                FOREIGN KEY (mandat_id) REFERENCES mandats(id),
                FOREIGN KEY (parent_id) REFERENCES budget_nodes(id),
                UNIQUE(mandat_id, parent_id, name)
            );

            CREATE TABLE IF NOT EXISTS yearly_budgets (
                mandat_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                flow_type TEXT NOT NULL,
                amount NUMERIC NOT NULL,
                PRIMARY KEY (mandat_id, year, flow_type),
                FOREIGN KEY (mandat_id) REFERENCES mandats(id)
            );

            CREATE TABLE IF NOT EXISTS budget_plans (
                id SERIAL PRIMARY KEY,
                mandat_id INTEGER NOT NULL,
                node_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                flow_type TEXT NOT NULL,
                amount NUMERIC NOT NULL,
                FOREIGN KEY (mandat_id) REFERENCES mandats(id),
                FOREIGN KEY (node_id) REFERENCES budget_nodes(id)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                mandat_id INTEGER NOT NULL,
                node_id INTEGER NOT NULL,
                flow_type TEXT NOT NULL,
                amount NUMERIC NOT NULL,
                label TEXT,
                description TEXT,
                date TEXT NOT NULL,
                payment_method TEXT,
                order_number TEXT,
                created_at TEXT NOT NULL,
                deleted_at TEXT,
                FOREIGN KEY (mandat_id) REFERENCES mandats(id),
                FOREIGN KEY (node_id) REFERENCES budget_nodes(id)
            );

            CREATE TABLE IF NOT EXISTS attachments (
                id SERIAL PRIMARY KEY,
                transaction_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                deleted_at TEXT,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id)
            );
            """
        )
        _seed_default_mandats_and_nodes(conn)
        _ensure_justificatifs_structure(conn)


def _recover_mandats_from_mandat_dbs(conn: sqlite3.Connection) -> None:
    """Sync mandat metadata and filename mapping from per-mandat DB files."""
    db_dir = mandat_database_file(0).parent
    if not db_dir.exists():
        return

    recovered_any = False

    for db_path in sorted(db_dir.glob("*.db")):
        try:
            ext_conn = sqlite3.connect(db_path, timeout=5)
            ext_conn.row_factory = sqlite3.Row
            table_exists = ext_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='mandats'"
            ).fetchone()
            if not table_exists:
                ext_conn.close()
                continue

            row = ext_conn.execute(
                "SELECT id, name, date_debut, date_fin, active, created_at FROM mandats ORDER BY active DESC, id ASC LIMIT 1"
            ).fetchone()
            ext_conn.close()
        except Exception:
            continue

        if not row:
            continue

        try:
            mandat_id = int(row["id"])
            mandat_name = str(row["name"])
            date_debut = str(row["date_debut"])
            date_fin = str(row["date_fin"])
            active = int(row["active"])
            created_at = str(row["created_at"]) if row["created_at"] else utc_now()

            conn.execute(
                """INSERT INTO mandats (id, name, date_debut, date_fin, active, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       name = excluded.name,
                       date_debut = excluded.date_debut,
                       date_fin = excluded.date_fin,
                       active = excluded.active,
                       created_at = excluded.created_at""",
                (
                    mandat_id,
                    mandat_name,
                    date_debut,
                    date_fin,
                    active,
                    created_at,
                ),
            )

            conn.execute(
                """INSERT INTO mandat_db_files (mandat_id, db_filename, created_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(mandat_id) DO UPDATE SET
                       db_filename = excluded.db_filename""",
                (mandat_id, db_path.name, utc_now()),
            )

            recovered_any = True
        except Exception:
            continue

    if not recovered_any:
        return

    active_row = conn.execute("SELECT id FROM mandats WHERE active = 1 LIMIT 1").fetchone()
    if active_row:
        return

    fallback = conn.execute("SELECT id FROM mandats ORDER BY date_debut DESC, id DESC LIMIT 1").fetchone()
    if fallback:
        conn.execute("UPDATE mandats SET active = 0")
        conn.execute("UPDATE mandats SET active = 1 WHERE id = ?", (int(fallback["id"]),))


def _migrate_budget_nodes_unique_constraint(conn: sqlite3.Connection) -> None:
    """Migrate legacy UNIQUE(mandat_id, name) to UNIQUE(mandat_id, parent_id, name)."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'budget_nodes'"
    ).fetchone()
    if not row or not row[0]:
        return

    create_sql = str(row[0]).replace("\n", " ")
    if "UNIQUE(mandat_id, name)" not in create_sql:
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    conn.executescript(
        """
        CREATE TABLE budget_nodes_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mandat_id INTEGER NOT NULL,
            parent_id INTEGER,
            name TEXT NOT NULL,
            pole_color TEXT,
            created_at TEXT NOT NULL,
            deleted_at TEXT,
            FOREIGN KEY (mandat_id) REFERENCES mandats(id),
            FOREIGN KEY (parent_id) REFERENCES budget_nodes_new(id),
            UNIQUE(mandat_id, parent_id, name)
        );

        INSERT INTO budget_nodes_new (id, mandat_id, parent_id, name, pole_color, created_at, deleted_at)
        SELECT id, mandat_id, parent_id, name, NULL, created_at, deleted_at
        FROM budget_nodes;

        DROP TABLE budget_nodes;
        ALTER TABLE budget_nodes_new RENAME TO budget_nodes;
        """
    )
    conn.execute("PRAGMA foreign_keys = ON")


def _migrate_budget_nodes_pole_color_column(conn: sqlite3.Connection) -> None:
    """Add pole_color to budget_nodes tables and backfill root pole colors."""
    columns = conn.execute("PRAGMA table_info(budget_nodes)").fetchall()
    has_pole_color = any(str(column[1]) == "pole_color" for column in columns)
    if not has_pole_color:
        conn.execute("ALTER TABLE budget_nodes ADD COLUMN pole_color TEXT")

    root_rows = conn.execute(
        "SELECT id, name, pole_color FROM budget_nodes WHERE parent_id IS NULL"
    ).fetchall()
    for row in root_rows:
        if row["pole_color"]:
            continue
        conn.execute(
            "UPDATE budget_nodes SET pole_color = ? WHERE id = ?",
            (default_pole_color(str(row["name"])), int(row["id"])),
        )


def _migrate_transactions_order_number_column(conn: sqlite3.Connection) -> None:
    """Add the order_number column to legacy transactions tables if needed."""
    columns = conn.execute("PRAGMA table_info(transactions)").fetchall()
    has_order_number = any(str(column[1]) == "order_number" for column in columns)
    if has_order_number:
        return

    conn.execute("ALTER TABLE transactions ADD COLUMN order_number TEXT")


def _seed_default_mandats_and_nodes(conn: sqlite3.Connection) -> None:
    # Create default mandat if none exists
    mandats_count = conn.execute("SELECT COUNT(*) FROM mandats").fetchone()[0]
    if int(mandats_count) == 0:
        now = utc_now()
        cursor = conn.execute(
            "INSERT INTO mandats (name, date_debut, date_fin, active, created_at) VALUES (?, ?, ?, ?, ?)",
            ("Mandat 2025-2026", "2025-09-01", "2026-08-31", 1, now),
        )
        mandat_id = int(cursor.lastrowid)
    else:
        mandat_id = int(conn.execute("SELECT id FROM mandats WHERE active = 1 LIMIT 1").fetchone()[0])

    # Seed budget nodes if empty for this mandat
    nodes_count = conn.execute("SELECT COUNT(*) FROM budget_nodes WHERE mandat_id = ?", (mandat_id,)).fetchone()[0]
    if int(nodes_count) > 0:
        return

    now = utc_now()
    for pole_name, categories in DEFAULT_BUDGET_TREE:
        pole_cursor = conn.execute(
            "INSERT INTO budget_nodes (mandat_id, parent_id, name, pole_color, created_at) VALUES (?, ?, ?, ?, ?)",
            (mandat_id, None, pole_name, default_pole_color(pole_name), now),
        )
        pole_id = int(pole_cursor.lastrowid)

        for category_name, items in categories:
            category_cursor = conn.execute(
                "INSERT INTO budget_nodes (mandat_id, parent_id, name, created_at) VALUES (?, ?, ?, ?)",
                (mandat_id, pole_id, category_name, now),
            )
            category_id = int(category_cursor.lastrowid)

            for item_name in items:
                conn.execute(
                    "INSERT INTO budget_nodes (mandat_id, parent_id, name, created_at) VALUES (?, ?, ?, ?)",
                    (mandat_id, category_id, item_name, now),
                )


def _ensure_justificatifs_structure(conn: sqlite3.Connection) -> None:
    """Pre-create justificatifs folders for all mandats and root poles."""
    mandats = conn.execute("SELECT id, name FROM mandats").fetchall()
    for mandat in mandats:
        mandat_id = int(mandat["id"])
        mandat_name = str(mandat["name"])
        poles = conn.execute(
            "SELECT name FROM budget_nodes WHERE mandat_id = ? AND parent_id IS NULL AND deleted_at IS NULL ORDER BY id",
            (mandat_id,),
        ).fetchall()
        ensure_pole_directories(mandat_id, mandat_name, [str(pole["name"]) for pole in poles])


