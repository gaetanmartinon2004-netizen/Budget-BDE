from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from .database import (
    DEFAULT_BUDGET_TREE,
    connection,
    connection_for_mandat,
    delete_mandat_database,
    default_pole_color,
    utc_now,
)
from .models import BudgetNode, BudgetPlan, Mandat, dict_from_row


def get_active_mandat() -> Mandat:
    """Get current active mandat or create default."""
    with connection() as conn:
        row = conn.execute("SELECT * FROM mandats WHERE active = 1 LIMIT 1").fetchone()
        if row:
            return Mandat(
                id=row["id"],
                name=row["name"],
                date_debut=row["date_debut"],
                date_fin=row["date_fin"],
                active=bool(row["active"]),
            )
    
    # Fallback if no active mandat
    raise ValueError("No active mandat found")


def create_mandat(name: str, date_debut: str, date_fin: str) -> Mandat:
    """Create a new mandat."""
    _ensure_text(name, "Nom du mandat")
    _ensure_date(date_debut, "Date de début")
    _ensure_date(date_fin, "Date de fin")
    
    with connection() as conn:
        cursor = conn.execute(
            """INSERT INTO mandats (name, date_debut, date_fin, active, created_at)
               VALUES (?, ?, ?, 0, ?)""",
            (name, date_debut, date_fin, utc_now()),
        )
        mandat_id = int(cursor.lastrowid)
        _seed_mandat_budget_tree(conn, mandat_id)
        return Mandat(mandat_id, name, date_debut, date_fin, False)


def update_mandat(mandat_id: int, name: str, date_debut: str, date_fin: str) -> Mandat:
    """Update mandat metadata (name and dates)."""
    _ensure_text(name, "Nom du mandat")
    _ensure_date(date_debut, "Date de début")
    _ensure_date(date_fin, "Date de fin")

    with connection() as conn:
        row = conn.execute("SELECT * FROM mandats WHERE id = ?", (mandat_id,)).fetchone()
        if not row:
            raise ValueError("Mandat introuvable")

        conn.execute(
            "UPDATE mandats SET name = ?, date_debut = ?, date_fin = ? WHERE id = ?",
            (name, date_debut, date_fin, mandat_id),
        )

        updated = conn.execute("SELECT * FROM mandats WHERE id = ?", (mandat_id,)).fetchone()
        return Mandat(
            id=updated["id"],
            name=updated["name"],
            date_debut=updated["date_debut"],
            date_fin=updated["date_fin"],
            active=bool(updated["active"]),
        )


def _seed_mandat_budget_tree(conn: Any, mandat_id: int) -> None:
    """Seed default categories for a new mandat without carrying over data."""
    now = utc_now()
    for pole_name, categories in DEFAULT_BUDGET_TREE:
        pole_cursor = conn.execute(
            "INSERT INTO budget_nodes (mandat_id, parent_id, name, created_at) VALUES (?, ?, ?, ?)",
            (mandat_id, None, pole_name, now),
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


def get_mandats() -> list[dict[str, Any]]:
    """Get all mandats."""
    with connection() as conn:
        rows = conn.execute("SELECT * FROM mandats ORDER BY date_debut DESC").fetchall()
        return [dict_from_row(row) for row in rows]


def get_mandat_name(mandat_id: int) -> str:
    """Get mandat display name by id."""
    with connection() as conn:
        row = conn.execute("SELECT name FROM mandats WHERE id = ?", (mandat_id,)).fetchone()
        if not row:
            raise ValueError("Mandat introuvable")
        return str(row["name"])


def set_active_mandat(mandat_id: int) -> Mandat:
    """Set one mandat as active and return it."""
    with connection() as conn:
        row = conn.execute("SELECT * FROM mandats WHERE id = ?", (mandat_id,)).fetchone()
        if not row:
            raise ValueError("Mandat introuvable")

        conn.execute("UPDATE mandats SET active = 0")
        conn.execute("UPDATE mandats SET active = 1 WHERE id = ?", (mandat_id,))

        updated = conn.execute("SELECT * FROM mandats WHERE id = ?", (mandat_id,)).fetchone()
        return Mandat(
            id=updated["id"],
            name=updated["name"],
            date_debut=updated["date_debut"],
            date_fin=updated["date_fin"],
            active=bool(updated["active"]),
        )


def delete_mandat(mandat_id: int) -> dict[str, Any]:
    """Delete a mandat and all related data, keeping at least one mandat in DB."""
    result: dict[str, Any]
    with connection() as conn:
        total = int(conn.execute("SELECT COUNT(*) FROM mandats").fetchone()[0])
        if total <= 1:
            raise ValueError("Impossible de supprimer le dernier mandat")

        mandat = conn.execute("SELECT * FROM mandats WHERE id = ?", (mandat_id,)).fetchone()
        if not mandat:
            raise ValueError("Mandat introuvable")

        was_active = bool(mandat["active"])
        mandat_name = str(mandat["name"])

        # Clear any legacy rows that may still exist in the main database from older layouts.
        conn.execute(
            "DELETE FROM attachments WHERE transaction_id IN (SELECT id FROM transactions WHERE mandat_id = ?)",
            (mandat_id,),
        )
        conn.execute("DELETE FROM transactions WHERE mandat_id = ?", (mandat_id,))
        conn.execute("DELETE FROM budget_plans WHERE mandat_id = ?", (mandat_id,))
        conn.execute("DELETE FROM yearly_budgets WHERE mandat_id = ?", (mandat_id,))
        conn.execute("DELETE FROM budget_nodes WHERE mandat_id = ?", (mandat_id,))
        conn.execute("DELETE FROM mandat_db_files WHERE mandat_id = ?", (mandat_id,))

        conn.execute("DELETE FROM mandats WHERE id = ?", (mandat_id,))

        new_active_id: int | None = None
        if was_active:
            fallback = conn.execute(
                "SELECT id FROM mandats ORDER BY date_debut DESC, id DESC LIMIT 1"
            ).fetchone()
            if fallback:
                new_active_id = int(fallback["id"])
                conn.execute("UPDATE mandats SET active = 0")
                conn.execute("UPDATE mandats SET active = 1 WHERE id = ?", (new_active_id,))

        result = {
            "deleted_mandat_id": mandat_id,
            "new_active_mandat_id": new_active_id,
        }
    delete_mandat_database(mandat_id, mandat_name=mandat_name)
    return result


def get_budget_tree(mandat_id: int) -> list[BudgetNode]:
    """Get hierarchical budget tree for a mandat (roots only, children attached)."""
    with connection_for_mandat(mandat_id) as conn:
        roots = conn.execute(
            "SELECT * FROM budget_nodes WHERE mandat_id = ? AND parent_id IS NULL AND deleted_at IS NULL ORDER BY id",
            (mandat_id,),
        ).fetchall()
        
        return [_build_node_tree(conn, row) for row in roots]


def _build_node_tree(conn: Any, row: Any) -> BudgetNode:
    """Recursively build node tree with children."""
    children = conn.execute(
        "SELECT * FROM budget_nodes WHERE mandat_id = ? AND parent_id = ? AND deleted_at IS NULL ORDER BY id",
        (row["mandat_id"], row["id"]),
    ).fetchall()
    
    node = BudgetNode(
        id=row["id"],
        mandat_id=row["mandat_id"],
        parent_id=row["parent_id"],
        name=row["name"],
        pole_color=row["pole_color"] if "pole_color" in row.keys() else None,
        children=[_build_node_tree(conn, child) for child in children] if children else [],
    )
    return node


def create_budget_node(mandat_id: int, parent_id: int | None, name: str) -> BudgetNode:
    """Create new budget node (category/pole)."""
    _ensure_text(name, "Nom de la catégorie")
    
    with connection_for_mandat(mandat_id) as conn:
        # Validate parent exists
        if parent_id:
            parent = conn.execute(
                "SELECT * FROM budget_nodes WHERE id = ? AND mandat_id = ? AND deleted_at IS NULL",
                (parent_id, mandat_id),
            ).fetchone()
            if not parent:
                raise ValueError("Parent category not found")
        
        pole_color = default_pole_color(name) if parent_id is None else None
        cursor = conn.execute(
            """INSERT INTO budget_nodes (mandat_id, parent_id, name, pole_color, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (mandat_id, parent_id, name, pole_color, utc_now()),
        )
        node_id = int(cursor.lastrowid)
        return BudgetNode(node_id, mandat_id, parent_id, name, pole_color)


def update_budget_node(
    mandat_id: int,
    node_id: int,
    name: str,
    pole_color: str | None = None,
) -> BudgetNode:
    """Update a root pole name and color."""
    _ensure_text(name, "Nom du pôle")
    if pole_color:
        pole_color = str(pole_color).strip()
        if not pole_color.startswith("#") or len(pole_color) not in (4, 7):
            raise ValueError("Couleur de pôle invalide")

    with connection_for_mandat(mandat_id) as conn:
        node = conn.execute(
            "SELECT * FROM budget_nodes WHERE id = ? AND mandat_id = ? AND deleted_at IS NULL",
            (node_id, mandat_id),
        ).fetchone()
        if not node:
            raise ValueError("Node not found")
        if node["parent_id"] is not None:
            raise ValueError("Seuls les pôles racines peuvent être modifiés")

        conn.execute(
            "UPDATE budget_nodes SET name = ?, pole_color = ? WHERE id = ? AND mandat_id = ?",
            (name, pole_color or default_pole_color(name), node_id, mandat_id),
        )

        updated = conn.execute(
            "SELECT * FROM budget_nodes WHERE id = ? AND mandat_id = ? AND deleted_at IS NULL",
            (node_id, mandat_id),
        ).fetchone()
        return BudgetNode(
            id=updated["id"],
            mandat_id=updated["mandat_id"],
            parent_id=updated["parent_id"],
            name=updated["name"],
            pole_color=updated["pole_color"],
        )


def delete_budget_node(mandat_id: int, node_id: int) -> None:
    """Soft delete a budget node and all its descendants."""
    with connection_for_mandat(mandat_id) as conn:
        # Verify node exists
        node = conn.execute(
            "SELECT * FROM budget_nodes WHERE id = ? AND mandat_id = ? AND deleted_at IS NULL",
            (node_id, mandat_id),
        ).fetchone()
        if not node:
            raise ValueError("Node not found")
        
        now = utc_now()
        
        # Get all descendants
        descendants = _get_descendants(conn, node_id)
        descendants.append(node_id)
        
        # Soft delete all
        for desc_id in descendants:
            conn.execute(
                "UPDATE budget_nodes SET deleted_at = ? WHERE id = ?",
                (now, desc_id),
            )
            # Soft delete all transactions for this node
            conn.execute(
                "UPDATE transactions SET deleted_at = ? WHERE node_id = ? AND mandat_id = ?",
                (now, desc_id, mandat_id),
            )


def _get_descendants(conn: Any, node_id: int) -> list[int]:
    """Get all descendant node IDs recursively."""
    children = conn.execute(
        "SELECT id FROM budget_nodes WHERE parent_id = ? AND deleted_at IS NULL",
        (node_id,),
    ).fetchall()
    
    result = []
    for child in children:
        child_id = child["id"]
        result.append(child_id)
        result.extend(_get_descendants(conn, child_id))
    return result


def get_all_transactions(
    mandat_id: int,
    year: int | None = None,
    flow_type: str | None = None,
    node_id: int | None = None,
) -> list[dict[str, Any]]:
    """Get transactions for mandat with optional filters."""
    query = """
        SELECT
            t.*,
            n.name AS node_name
        FROM transactions t
        LEFT JOIN budget_nodes n ON n.id = t.node_id
        WHERE t.mandat_id = ? AND t.deleted_at IS NULL
    """
    params = [mandat_id]
    
    if year:
        query += " AND SUBSTR(t.date, 1, 4) = ?"
        params.append(str(year))
    
    if flow_type:
        flow_type = _normalize_flow_type(flow_type)
        query += " AND t.flow_type = ?"
        params.append(flow_type)
    
    if node_id:
        query += " AND t.node_id = ?"
        params.append(node_id)
    
    query += " ORDER BY t.created_at DESC, t.id DESC, t.date DESC"
    
    with connection_for_mandat(mandat_id) as conn:
        rows = conn.execute(query, params).fetchall()
        transactions = [dict_from_row(row) for row in rows]

        if not transactions:
            return transactions

        trans_ids = [int(trans["id"]) for trans in transactions]
        placeholders = ", ".join(["?"] * len(trans_ids))
        attachments_rows = conn.execute(
            f"SELECT id, transaction_id, file_path FROM attachments WHERE deleted_at IS NULL AND transaction_id IN ({placeholders}) ORDER BY id",
            trans_ids,
        ).fetchall()

        attachments_by_trans: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in attachments_rows:
            row_dict = dict_from_row(row)
            attachments_by_trans[int(row_dict["transaction_id"])].append(row_dict)

        for trans in transactions:
            items = attachments_by_trans.get(int(trans["id"]), [])
            trans["attachments"] = items
            trans["attachments_count"] = len(items)

        return transactions


def create_transaction(
    mandat_id: int,
    node_id: int | None,
    label: str,
    amount: float | str,
    flow_type: str,
    description: str = "",
    date: str = "",
    payment_method: str = "",
    order_number: str = "",
) -> dict[str, Any]:
    """Create a transaction, creating node if needed."""
    _ensure_text(label, "Libellé")
    amount = _ensure_amount(amount, "Montant")
    flow_type = _normalize_flow_type(flow_type)
    if date:
        _ensure_date(date, "Date")
    else:
        date = str(datetime.now().date())
    
    with connection_for_mandat(mandat_id) as conn:
        # Create node if not provided
        if not node_id:
            cursor = conn.execute(
                """INSERT INTO budget_nodes (mandat_id, parent_id, name, created_at)
                   VALUES (?, ?, ?, ?)""",
                (mandat_id, None, label, utc_now()),
            )
            node_id = int(cursor.lastrowid)
        else:
            # Verify node exists
            node = conn.execute(
                "SELECT * FROM budget_nodes WHERE id = ? AND mandat_id = ? AND deleted_at IS NULL",
                (node_id, mandat_id),
            ).fetchone()
            if not node:
                raise ValueError("Node not found")
        
        cursor = conn.execute(
            """INSERT INTO transactions
               (mandat_id, node_id, flow_type, amount, label, description, date, payment_method, order_number, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (mandat_id, node_id, flow_type, amount, label, description, date, payment_method, order_number, utc_now()),
        )
        transaction_id = int(cursor.lastrowid)

        return _get_transaction_from_conn(conn, mandat_id, transaction_id)


def get_transaction(mandat_id: int, transaction_id: int) -> dict[str, Any]:
    """Get single transaction."""
    with connection_for_mandat(mandat_id) as conn:
        return _get_transaction_from_conn(conn, mandat_id, transaction_id)


def _get_transaction_from_conn(conn: Any, mandat_id: int, transaction_id: int) -> dict[str, Any]:
    """Read a transaction using the provided connection."""
    row = conn.execute(
        "SELECT * FROM transactions WHERE id = ? AND mandat_id = ? AND deleted_at IS NULL",
        (transaction_id, mandat_id),
    ).fetchone()

    if not row:
        raise ValueError("Transaction not found")

    result = dict_from_row(row)

    # Get node name
    node = conn.execute("SELECT name FROM budget_nodes WHERE id = ?", (row["node_id"],)).fetchone()
    result["node_name"] = node["name"] if node else ""

    # Get attachments
    attachments = conn.execute(
        "SELECT * FROM attachments WHERE transaction_id = ? AND deleted_at IS NULL",
        (transaction_id,),
    ).fetchall()
    result["attachments"] = [dict_from_row(a) for a in attachments]

    return result


def update_transaction(
    mandat_id: int,
    transaction_id: int,
    node_id: int | None = None,
    label: str | None = None,
    amount: float | str | None = None,
    flow_type: str | None = None,
    description: str | None = None,
    date: str | None = None,
    payment_method: str | None = None,
    order_number: str | None = None,
) -> dict[str, Any]:
    """Update transaction fields."""
    with connection_for_mandat(mandat_id) as conn:
        # Get current transaction
        row = conn.execute(
            "SELECT * FROM transactions WHERE id = ? AND mandat_id = ? AND deleted_at IS NULL",
            (transaction_id, mandat_id),
        ).fetchone()

        if not row:
            raise ValueError("Transaction not found")
        
        # Build update
        updates = {}
        if node_id is not None:
            node = conn.execute(
                "SELECT * FROM budget_nodes WHERE id = ? AND mandat_id = ? AND deleted_at IS NULL",
                (node_id, mandat_id),
            ).fetchone()
            if not node:
                raise ValueError("Node not found")
            updates["node_id"] = int(node_id)
        if label is not None:
            updates["label"] = _ensure_text(label, "Libellé")
        if amount is not None:
            updates["amount"] = _ensure_amount(amount, "Montant")
        if flow_type is not None:
            updates["flow_type"] = _normalize_flow_type(flow_type)
        if description is not None:
            updates["description"] = description
        if date is not None:
            _ensure_date(date, "Date")
            updates["date"] = date
        if payment_method is not None:
            updates["payment_method"] = payment_method
        if order_number is not None:
            updates["order_number"] = order_number
        
        if not updates:
            return _get_transaction_from_conn(conn, mandat_id, transaction_id)
        
        # Update
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        params = list(updates.values()) + [transaction_id, mandat_id]
        
        conn.execute(
            f"UPDATE transactions SET {set_clause} WHERE id = ? AND mandat_id = ?",
            params,
        )

        return _get_transaction_from_conn(conn, mandat_id, transaction_id)


def delete_transaction(mandat_id: int, transaction_id: int) -> None:
    """Soft delete a transaction and its attachments."""
    with connection_for_mandat(mandat_id) as conn:
        trans = conn.execute(
            "SELECT * FROM transactions WHERE id = ? AND mandat_id = ? AND deleted_at IS NULL",
            (transaction_id, mandat_id),
        ).fetchone()
        
        if not trans:
            raise ValueError("Transaction not found")
        
        now = utc_now()
        conn.execute(
            "UPDATE transactions SET deleted_at = ? WHERE id = ?",
            (now, transaction_id),
        )
        
        # Soft delete attachments
        conn.execute(
            "UPDATE attachments SET deleted_at = ? WHERE transaction_id = ?",
            (now, transaction_id),
        )


def get_budget_performance(mandat_id: int, year: int | None = None) -> list[dict[str, Any]]:
    """Calculate budget vs actual for all nodes hierarchically across full mandat data."""
    
    with connection_for_mandat(mandat_id) as conn:
        nodes = conn.execute(
            "SELECT * FROM budget_nodes WHERE mandat_id = ? AND parent_id IS NULL AND deleted_at IS NULL ORDER BY id",
            (mandat_id,),
        ).fetchall()
        
        result = []
        for node in nodes:
            result.append(_calculate_node_performance(conn, mandat_id, node))
        
        return result


def _calculate_node_performance(conn: Any, mandat_id: int, node: Any) -> dict[str, Any]:
    """Calculate performance for a node and its children."""
    node_id = node["id"]

    # Forecast values split by flow type.
    plans = conn.execute(
        """SELECT flow_type, amount FROM budget_plans
           WHERE mandat_id = ? AND node_id = ?""",
        (mandat_id, node_id),
    ).fetchall()
    budget_expense = 0.0
    budget_income = 0.0
    for plan in plans:
        flow = str(plan["flow_type"] or "")
        amount = float(plan["amount"] or 0)
        if flow == "expense":
            budget_expense += amount
        elif flow == "income":
            budget_income += amount

    # Actual values split by flow type.
    trans_rows = conn.execute(
        """SELECT flow_type, SUM(amount) as total FROM transactions
           WHERE mandat_id = ? AND node_id = ?
           AND deleted_at IS NULL
           GROUP BY flow_type""",
        (mandat_id, node_id),
    ).fetchall()
    actual_expense = 0.0
    actual_income = 0.0
    for trans in trans_rows:
        flow = str(trans["flow_type"] or "")
        total = float(trans["total"] or 0)
        if flow == "expense":
            actual_expense += total
        elif flow == "income":
            actual_income += total
    
    # Get children
    children_rows = conn.execute(
        "SELECT * FROM budget_nodes WHERE mandat_id = ? AND parent_id = ? AND deleted_at IS NULL ORDER BY id",
        (mandat_id, node_id),
    ).fetchall()
    
    children = [_calculate_node_performance(conn, mandat_id, child) for child in children_rows]
    
    # Aggregate children
    for child in children:
        budget_expense += child["budgeted_expense"]
        budget_income += child["budgeted_income"]
        actual_expense += child["actual_expense"]
        actual_income += child["actual_income"]

    budget_total = budget_income - budget_expense
    actual_total = actual_income - actual_expense
    variance_total = actual_total - budget_total
    variance_pct = (variance_total / abs(budget_total) * 100) if budget_total != 0 else 0
    
    return {
        "id": node_id,
        "name": node["name"],
        "budgeted_expense": budget_expense,
        "budgeted_income": budget_income,
        "budgeted_total": budget_total,
        "actual_expense": actual_expense,
        "actual_income": actual_income,
        "actual_total": actual_total,
        # Backward-compatible aliases for older UI code.
        "budgeted": budget_total,
        "actual": actual_total,
        "variance": variance_total,
        "variance_pct": variance_pct,
        "children": children,
    }


def save_budget_plan(
    mandat_id: int,
    node_id: int,
    year: int,
    flow_type: str,
    amount: float | str,
) -> BudgetPlan:
    """Save or update budget plan for a node."""
    year = _ensure_year(year, "Année")
    amount = _ensure_amount(amount, "Montant")
    flow_type = _normalize_flow_type(flow_type)
    
    with connection_for_mandat(mandat_id) as conn:
        # Verify node exists
        node = conn.execute(
            "SELECT * FROM budget_nodes WHERE id = ? AND mandat_id = ? AND deleted_at IS NULL",
            (node_id, mandat_id),
        ).fetchone()
        if not node:
            raise ValueError("Node not found")

        # Enforce budgeting only on leaf nodes.
        has_children = conn.execute(
            "SELECT 1 FROM budget_nodes WHERE mandat_id = ? AND parent_id = ? AND deleted_at IS NULL LIMIT 1",
            (mandat_id, node_id),
        ).fetchone()
        if has_children:
            raise ValueError("Le prévisionnel est modifiable uniquement sur le dernier niveau")
        
        # Delete existing
        conn.execute(
            "DELETE FROM budget_plans WHERE mandat_id = ? AND node_id = ? AND year = ? AND flow_type = ?",
            (mandat_id, node_id, year, flow_type),
        )
        
        # Insert new
        cursor = conn.execute(
            """INSERT INTO budget_plans (mandat_id, node_id, year, flow_type, amount)
               VALUES (?, ?, ?, ?, ?)""",
            (mandat_id, node_id, year, flow_type, amount),
        )
        plan_id = int(cursor.lastrowid)
        
        return BudgetPlan(plan_id, mandat_id, node_id, year, flow_type, amount)


def clear_budget_plans(
    mandat_id: int,
    year: int,
    flow_type: str | None = None,
) -> int:
    """Clear budget plans for a mandat/year. Returns deleted row count."""
    year = _ensure_year(year, "Année")
    normalized_flow = _normalize_flow_type(flow_type) if flow_type else None

    with connection_for_mandat(mandat_id) as conn:
        if normalized_flow:
            cursor = conn.execute(
                "DELETE FROM budget_plans WHERE mandat_id = ? AND year = ? AND flow_type = ?",
                (mandat_id, year, normalized_flow),
            )
        else:
            cursor = conn.execute(
                "DELETE FROM budget_plans WHERE mandat_id = ? AND year = ?",
                (mandat_id, year),
            )
        return int(cursor.rowcount or 0)


def add_attachment(mandat_id: int, transaction_id: int, file_path: str) -> dict[str, Any]:
    """Add file attachment to transaction."""
    _ensure_text(file_path, "Chemin du fichier")
    
    with connection_for_mandat(mandat_id) as conn:
        trans = conn.execute(
            "SELECT * FROM transactions WHERE id = ? AND deleted_at IS NULL",
            (transaction_id,),
        ).fetchone()
        
        if not trans:
            raise ValueError("Transaction not found")
        
        cursor = conn.execute(
            """INSERT INTO attachments (transaction_id, file_path, created_at)
               VALUES (?, ?, ?)""",
            (transaction_id, file_path, utc_now()),
        )
        
        return {
            "id": int(cursor.lastrowid),
            "transaction_id": transaction_id,
            "file_path": file_path,
        }


def get_top_pole_name(mandat_id: int, node_id: int | None) -> str:
    """Return root pole name for a node inside a mandat."""
    if not node_id:
        return "Sans pole"

    with connection_for_mandat(mandat_id) as conn:
        row = conn.execute(
            "SELECT id, parent_id, name FROM budget_nodes WHERE id = ? AND mandat_id = ? AND deleted_at IS NULL",
            (node_id, mandat_id),
        ).fetchone()
        if not row:
            return "Sans pole"

        current = row
        while current["parent_id"] is not None:
            parent = conn.execute(
                "SELECT id, parent_id, name FROM budget_nodes WHERE id = ? AND mandat_id = ? AND deleted_at IS NULL",
                (current["parent_id"], mandat_id),
            ).fetchone()
            if not parent:
                break
            current = parent

        return str(current["name"]) if current else "Sans pole"


# ===== VALIDATION HELPERS =====

def _normalize_flow_type(flow_type: str) -> str:
    """Normalize to 'income' or 'expense'."""
    flow_type = (flow_type or "").lower().strip()
    if flow_type in ("income", "revenu", "recette"):
        return "income"
    elif flow_type in ("expense", "dépense", "charge"):
        return "expense"
    else:
        raise ValueError(f"Type invalide: {flow_type}")


def _ensure_text(value: str | None, field_name: str) -> str:
    """Validate non-empty string."""
    if not value or not str(value).strip():
        raise ValueError(f"{field_name} ne peut pas être vide")
    return str(value).strip()


def _ensure_amount(value: float | str | None, field_name: str) -> float:
    """Convert and validate amount."""
    if value is None or value == "":
        raise ValueError(f"{field_name} ne peut pas être vide")
    
    try:
        amount_str = str(value).replace(",", ".")
        amount = float(amount_str)
        if amount < 0:
            raise ValueError()
        return round(amount, 2)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} invalide: {value}")


def _ensure_year(value: int | str | None, field_name: str) -> int:
    """Validate year."""
    try:
        year = int(value or 0)
        if 1900 <= year <= 2100:
            return year
    except (ValueError, TypeError):
        pass
    raise ValueError(f"{field_name} invalide: {value}")


def _ensure_date(value: str | None, field_name: str) -> str:
    """Validate ISO date YYYY-MM-DD."""
    if not value:
        raise ValueError(f"{field_name} ne peut pas être vide")
    
    value = str(value).strip()
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} invalide (format YYYY-MM-DD): {value}")
