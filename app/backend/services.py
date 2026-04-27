"""Business logic services."""

def get_mandats():
    """Get all mandats."""
    return []

def get_active_mandat():
    """Get the active mandat."""
    pass

def create_mandat(name, date_debut, date_fin):
    """Create a new mandat."""
    pass

def update_mandat(mandat_id, name, date_debut, date_fin):
    """Update an existing mandat."""
    pass

def set_active_mandat(mandat_id):
    """Set the active mandat."""
    pass

def delete_mandat(mandat_id):
    """Delete a mandat."""
    pass

def get_budget_tree(mandat_id):
    """Get the budget structure tree."""
    return []

def create_budget_node(mandat_id, parent_id, name):
    """Create a budget node."""
    pass

def update_budget_node(mandat_id, node_id, name, pole_color):
    """Update a budget node."""
    pass

def delete_budget_node(mandat_id, node_id):
    """Delete a budget node."""
    pass

def get_all_transactions(mandat_id, year=None, flow_type=None, node_id=None):
    """Get all transactions."""
    return []

def create_transaction(mandat_id, node_id, label, amount, flow_type, description, date, payment_method, order_number):
    """Create a transaction."""
    pass

def get_transaction(mandat_id, transaction_id):
    """Get a transaction."""
    pass

def update_transaction(mandat_id, transaction_id, node_id, label, amount, flow_type, description, date, payment_method, order_number):
    """Update a transaction."""
    pass

def delete_transaction(mandat_id, transaction_id):
    """Delete a transaction."""
    pass

def get_budget_performance(mandat_id):
    """Get budget performance data."""
    return {}

def save_budget_plan(mandat_id, node_id, year, flow_type, amount):
    """Save a budget plan."""
    pass

def clear_budget_plans(mandat_id, year, flow_type):
    """Clear budget plans."""
    pass

def add_attachment(mandat_id, transaction_id, file_path):
    """Add an attachment to a transaction."""
    pass

def get_top_pole_name(mandat_id, node_id):
    """Get the top pole name."""
    return ""

def get_mandat_name(mandat_id):
    """Get the mandat name."""
    return ""
