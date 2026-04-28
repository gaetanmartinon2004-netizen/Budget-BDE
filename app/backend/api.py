from __future__ import annotations

import os
import sys
from pathlib import Path

from bottle import Bottle, static_file, request, response

from . import services
from .database import initialize_database
from .justificatifs import safe_path_segment, save_justificatif
from .paths import get_app_root, justificatifs_root


def create_app() -> Bottle:
    """Create and configure Bottle app."""
    app = Bottle()
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-local")
    
    # Initialize database on startup
    initialize_database()
    
    # ===== STATIC & TEMPLATES =====
    
    @app.route("/")
    def index():
        return static_file("index.html", root=Path(__file__).parent.parent / "frontend" / "templates")
    
    @app.route("/dashboard")
    def dashboard():
        return static_file("dashboard.html", root=Path(__file__).parent.parent / "frontend" / "templates")
    
    @app.route("/transactions")
    def transactions_page():
        return static_file("transactions.html", root=Path(__file__).parent.parent / "frontend" / "templates")
    
    @app.route("/structure")
    def structure_page():
        return static_file("structure.html", root=Path(__file__).parent.parent / "frontend" / "templates")
    
    @app.route("/static/<path:path>")
    def serve_static(path):
        return static_file(path, root=Path(__file__).parent.parent / "frontend" / "static")
    
    @app.route("/health")
    def health():
        return {"status": "ok"}
    
    # ===== MANDAT ENDPOINTS =====
    
    @app.route("/api/mandats", method="GET")
    def get_mandats():
        try:
            mandats = services.get_mandats()
            return {"mandats": mandats}
        except Exception as e:
            response.status = 400
            return {"error": str(e)}
    
    @app.route("/api/mandat/active", method="GET")
    def get_active_mandat():
        try:
            mandat = services.get_active_mandat()
            return {
                "id": mandat.id,
                "name": mandat.name,
                "date_debut": mandat.date_debut,
                "date_fin": mandat.date_fin,
                "active": mandat.active,
            }
        except Exception as e:
            response.status = 400
            return {"error": str(e)}
    
    @app.route("/api/mandat", method="POST")
    def create_mandat():
        try:
            data = request.json
            mandat = services.create_mandat(
                name=data.get("name"),
                date_debut=data.get("date_debut"),
                date_fin=data.get("date_fin"),
            )
            return {
                "id": mandat.id,
                "name": mandat.name,
                "date_debut": mandat.date_debut,
                "date_fin": mandat.date_fin,
                "active": mandat.active,
            }
        except Exception as e:
            response.status = 400
            return {"error": str(e)}

    @app.route("/api/mandat/<mandat_id:int>", method="PUT")
    def update_mandat_endpoint(mandat_id):
        try:
            data = request.json
            mandat = services.update_mandat(
                mandat_id=mandat_id,
                name=data.get("name"),
                date_debut=data.get("date_debut"),
                date_fin=data.get("date_fin"),
            )
            return {
                "id": mandat.id,
                "name": mandat.name,
                "date_debut": mandat.date_debut,
                "date_fin": mandat.date_fin,
                "active": mandat.active,
            }
        except Exception as e:
            response.status = 400
            return {"error": str(e)}

    @app.route("/api/mandat/active", method="POST")
    def set_active_mandat_endpoint():
        try:
            data = request.json
            mandat = services.set_active_mandat(int(data.get("mandat_id")))
            return {
                "id": mandat.id,
                "name": mandat.name,
                "date_debut": mandat.date_debut,
                "date_fin": mandat.date_fin,
                "active": mandat.active,
            }
        except Exception as e:
            response.status = 400
            return {"error": str(e)}

    @app.route("/api/mandat/<mandat_id:int>", method="DELETE")
    def delete_mandat_endpoint(mandat_id):
        try:
            result = services.delete_mandat(mandat_id)
            return {"success": True, **result}
        except Exception as e:
            response.status = 400
            return {"error": str(e)}
    
    # ===== STRUCTURE ENDPOINTS =====
    
    @app.route("/api/structure/<mandat_id:int>", method="GET")
    def get_structure(mandat_id):
        try:
            tree = services.get_budget_tree(mandat_id)
            return {"structure": _serialize_nodes(tree)}
        except Exception as e:
            response.status = 400
            return {"error": str(e)}
    
    @app.route("/api/node", method="POST")
    def create_node():
        try:
            data = request.json
            node = services.create_budget_node(
                mandat_id=int(data.get("mandat_id")),
                parent_id=data.get("parent_id"),
                name=data.get("name"),
            )
            return {
                "id": node.id,
                "mandat_id": node.mandat_id,
                "parent_id": node.parent_id,
                "name": node.name,
                "pole_color": node.pole_color,
            }
        except Exception as e:
            response.status = 400
            return {"error": str(e)}

    @app.route("/api/node/<mandat_id:int>/<node_id:int>", method="PUT")
    def update_node(mandat_id, node_id):
        try:
            data = request.json
            node = services.update_budget_node(
                mandat_id=mandat_id,
                node_id=node_id,
                name=data.get("name"),
                pole_color=data.get("pole_color"),
            )
            return {
                "id": node.id,
                "mandat_id": node.mandat_id,
                "parent_id": node.parent_id,
                "name": node.name,
                "pole_color": node.pole_color,
            }
        except Exception as e:
            response.status = 400
            return {"error": str(e)}
    
    @app.route("/api/node/<mandat_id:int>/<node_id:int>", method="DELETE")
    def delete_node(mandat_id, node_id):
        try:
            services.delete_budget_node(mandat_id, node_id)
            return {"success": True}
        except Exception as e:
            response.status = 400
            return {"error": str(e)}
    
    # ===== TRANSACTIONS ENDPOINTS =====
    
    @app.route("/api/transactions/<mandat_id:int>", method="GET")
    def get_transactions(mandat_id):
        try:
            year = request.query.get("year")
            flow_type = request.query.get("flow_type")
            node_id = request.query.get("node_id")
            
            transactions = services.get_all_transactions(
                mandat_id=mandat_id,
                year=int(year) if year else None,
                flow_type=flow_type,
                node_id=int(node_id) if node_id else None,
            )
            return {"transactions": transactions}
        except Exception as e:
            response.status = 400
            return {"error": str(e)}
    
    @app.route("/api/transaction", method="POST")
    def create_transaction_endpoint():
        try:
            data = request.json if request.json is not None else request.forms
            trans = services.create_transaction(
                mandat_id=int(data.get("mandat_id")),
                node_id=int(data.get("node_id")) if data.get("node_id") else None,
                label=data.get("label"),
                amount=data.get("amount"),
                flow_type=data.get("flow_type"),
                description=data.get("description", ""),
                date=data.get("date", ""),
                payment_method=data.get("payment_method", ""),
                order_number=data.get("order_number", ""),
            )

            pole_name = services.get_top_pole_name(
                mandat_id=int(trans["mandat_id"]),
                node_id=int(trans.get("node_id")) if trans.get("node_id") is not None else None,
            )
            mandat_name = services.get_mandat_name(int(trans["mandat_id"]))

            attachments = []
            for upload in request.files.getall("attachments"):
                if not upload or not upload.filename:
                    continue

                relative_path = save_justificatif(
                    mandat_id=int(trans["mandat_id"]),
                    transaction_id=int(trans["id"]),
                    file_obj=upload.file,
                    filename=upload.filename,
                    mandat_name=mandat_name,
                    pole_name=pole_name,
                    label=str(trans.get("label") or "transaction"),
                    transaction_date=str(trans.get("date") or ""),
                )
                attachment = services.add_attachment(
                    mandat_id=int(trans["mandat_id"]),
                    transaction_id=int(trans["id"]),
                    file_path=relative_path,
                )
                attachments.append(attachment)

            result = services.get_transaction(int(trans["mandat_id"]), int(trans["id"]))
            result["attachments"] = attachments or result.get("attachments", [])
            return result
        except Exception as e:
            response.status = 400
            return {"error": str(e)}
    
    @app.route("/api/transaction/<mandat_id:int>/<transaction_id:int>", method="GET")
    def get_transaction_endpoint(mandat_id, transaction_id):
        try:
            trans = services.get_transaction(mandat_id, transaction_id)
            return trans
        except Exception as e:
            response.status = 400
            return {"error": str(e)}
    
    @app.route("/api/transaction/<mandat_id:int>/<transaction_id:int>", method="PUT")
    def update_transaction_endpoint(mandat_id, transaction_id):
        try:
            data = request.json if request.json is not None else request.forms
            trans = services.update_transaction(
                mandat_id=mandat_id,
                transaction_id=transaction_id,
                node_id=int(data.get("node_id")) if data.get("node_id") else None,
                label=data.get("label"),
                amount=data.get("amount"),
                flow_type=data.get("flow_type"),
                description=data.get("description"),
                date=data.get("date"),
                payment_method=data.get("payment_method"),
                order_number=data.get("order_number"),
            )

            attachments = []
            uploads = request.files.getall("attachments")
            if uploads:
                pole_name = services.get_top_pole_name(
                    mandat_id=mandat_id,
                    node_id=int(data.get("node_id")) if data.get("node_id") else None,
                )
                mandat_name = services.get_mandat_name(mandat_id)
                for upload in uploads:
                    if not upload or not upload.filename:
                        continue
                    relative_path = save_justificatif(
                        mandat_id=mandat_id,
                        transaction_id=transaction_id,
                        file_obj=upload.file,
                        filename=upload.filename,
                        mandat_name=mandat_name,
                        pole_name=pole_name,
                        label=str(trans.get("label") or "transaction"),
                        transaction_date=str(trans.get("date") or ""),
                    )
                    attachment = services.add_attachment(
                        mandat_id=mandat_id,
                        transaction_id=transaction_id,
                        file_path=relative_path,
                    )
                    attachments.append(attachment)

            result = services.get_transaction(mandat_id, int(trans["id"]))
            if attachments:
                result["attachments"] = attachments
            return result
        except Exception as e:
            response.status = 400
            return {"error": str(e)}
    
    @app.route("/api/transaction/<mandat_id:int>/<transaction_id:int>", method="DELETE")
    def delete_transaction_endpoint(mandat_id, transaction_id):
        try:
            services.delete_transaction(mandat_id, transaction_id)
            return {"success": True}
        except Exception as e:
            response.status = 400
            return {"error": str(e)}
    
    # ===== DASHBOARD ENDPOINTS =====
    
    @app.route("/api/dashboard/<mandat_id:int>", method="GET")
    def get_dashboard(mandat_id):
        try:
            performance = services.get_budget_performance(mandat_id)
            
            return {
                "performance": performance,
                "year": None,
            }
        except Exception as e:
            response.status = 400
            return {"error": str(e)}
    
    # ===== BUDGET PLANS ENDPOINTS =====
    
    @app.route("/api/budget-plan", method="POST")
    def save_budget_plan():
        try:
            data = request.json
            plan = services.save_budget_plan(
                mandat_id=int(data.get("mandat_id")),
                node_id=int(data.get("node_id")),
                year=int(data.get("year")),
                flow_type=data.get("flow_type"),
                amount=data.get("amount"),
            )
            return {
                "id": plan.id,
                "mandat_id": plan.mandat_id,
                "node_id": plan.node_id,
                "year": plan.year,
                "flow_type": plan.flow_type,
                "amount": plan.amount,
            }
        except Exception as e:
            response.status = 400
            return {"error": str(e)}

    @app.route("/api/budget-plan/clear", method="POST")
    def clear_budget_plan():
        try:
            data = request.json
            deleted = services.clear_budget_plans(
                mandat_id=int(data.get("mandat_id")),
                year=int(data.get("year")),
                flow_type=data.get("flow_type"),
            )
            return {"success": True, "deleted": deleted}
        except Exception as e:
            response.status = 400
            return {"error": str(e)}
    
    # ===== ATTACHMENTS ENDPOINTS =====
    
    @app.route("/api/attachment", method="POST")
    def add_attachment():
        try:
            data = request.json
            attachment = services.add_attachment(
                mandat_id=int(data.get("mandat_id")),
                transaction_id=int(data.get("transaction_id")),
                file_path=data.get("file_path"),
            )
            return attachment
        except Exception as e:
            response.status = 400
            return {"error": str(e)}

    @app.route("/api/justificatifs/open-mandat/<mandat_id:int>", method="POST")
    def open_mandat_justificatifs_folder(mandat_id):
        try:
            mandat_name = services.get_mandat_name(mandat_id)
            folder_name = safe_path_segment(mandat_name) if mandat_name else f"mandat_{mandat_id}"
            folder_path = justificatifs_root() / folder_name
            folder_path.mkdir(parents=True, exist_ok=True)

            if sys.platform.startswith("win"):
                os.startfile(str(folder_path))
            elif sys.platform == "darwin":
                os.system(f"open '{folder_path}'")
            else:
                os.system(f"xdg-open '{folder_path}'")

            return {"success": True, "folder": str(folder_path)}
        except Exception as e:
            response.status = 400
            return {"error": str(e)}
    
    @app.route("/justificatifs/<path:path>")
    def serve_justificatif(path):
        return static_file(path, root=justificatifs_root())
    
    return app


def _serialize_nodes(nodes: list) -> list[dict]:
    """Recursively serialize BudgetNode objects to dicts."""
    result = []
    for node in nodes:
        result.append({
            "id": node.id,
            "name": node.name,
            "parent_id": node.parent_id,
            "pole_color": node.pole_color,
            "children": _serialize_nodes(node.children or []),
        })
    return result
