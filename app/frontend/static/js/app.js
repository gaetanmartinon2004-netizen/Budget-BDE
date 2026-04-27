// ===== APPLICATION PRINCIPALE =====

const App = {
    state: {
        activeView: 'dashboard',
        activeMandat: null,
        editingMandatId: null,
        managerSelectedMandatId: null,
        mandats: [],
        structure: [],
        transactionsRaw: [],
        transactions: [],
        editingTransactionId: null,
        dashboard: null,
        dashboardExpandedIds: [],
        dashboardYear: new Date().getFullYear(),
        transactionDisplayMode: 'history',
        transactionTreeExpandedIds: null,
        transactionFiltersInitialized: false,
        transactionModalListenersInitialized: false,
        transactionContextMenuInitialized: false,
    },

    async init() {
        await this.loadViews();
        this.setupEventListeners();
        await this.loadMandats();
    },

    async loadViews() {
        const content = document.getElementById('content');
        if (!content) return;

        const urls = ['/dashboard', '/transactions'];
        const htmlParts = await Promise.all(
            urls.map(async (url) => {
                const response = await fetch(url);
                if (!response.ok) {
                    throw new Error(`Impossible de charger ${url}`);
                }
                return response.text();
            })
        );

        content.innerHTML = htmlParts.join('\n');

        const initialView = this.getViewElement(this.state.activeView);
        if (initialView) {
            initialView.classList.add('active');
        }
    },

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const view = e.target.getAttribute('data-view');
                this.switchView(view);
            });
        });

        document.getElementById('current-mandat-btn')?.addEventListener('click', () => {
            this.openMandatManagerModal();
        });

        document.getElementById('mandat-select')?.addEventListener('change', (e) => {
            const selectedId = Number(e.target.value);
            this.state.managerSelectedMandatId = Number.isFinite(selectedId) && selectedId > 0 ? selectedId : null;
        });

        document.getElementById('use-mandat-btn')?.addEventListener('click', async () => {
            const selected = this.getSelectedMandatFromManager();
            if (!selected) {
                this.showToast('Aucun mandat sélectionné', 'error');
                return;
            }
            await this.switchMandat(selected.id);
            this.closeMandatManagerModal();
        });

        document.getElementById('new-mandat-btn')?.addEventListener('click', () => {
            this.openMandatModal();
        });
        document.getElementById('edit-mandat-btn')?.addEventListener('click', () => {
            this.openEditMandatModal();
        });
        document.getElementById('delete-mandat-btn')?.addEventListener('click', async () => {
            await this.deleteSelectedMandat();
        });
        document.getElementById('close-mandat-manager-btn')?.addEventListener('click', () => {
            this.closeMandatManagerModal();
        });
        document.getElementById('cancel-mandat-btn')?.addEventListener('click', () => {
            this.closeMandatModal();
        });
        document.getElementById('mandat-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            if (this.state.editingMandatId) {
                this.updateMandatFromModal();
                return;
            }
            this.createMandatFromModal();
        });

    },

    async loadMandats(refreshData = true) {
        try {
            const response = await fetch('/api/mandats');
            const data = await response.json();
            this.mandats = data.mandats || [];

            const select = document.getElementById('mandat-select');
            select.innerHTML = '';

            if (this.mandats.length === 0) {
                select.innerHTML = '<option>Aucun mandat</option>';
                this.activeMandat = null;
                this.state.managerSelectedMandatId = null;
                this.updateCurrentMandatButton();
                return;
            }

            this.mandats.forEach(m => {
                const option = document.createElement('option');
                option.value = m.id;
                option.text = m.name;
                option.selected = m.active;
                select.appendChild(option);
            });

            // Sélectionner le mandat actif ou, à défaut, le premier.
            const active = this.mandats.find(m => m.active) || this.mandats[0];
            if (!active) return;

            this.activeMandat = active;
            select.value = active.id;
            this.state.managerSelectedMandatId = Number(active.id);
            this.syncDashboardYearFromMandat(active);
            this.updateCurrentMandatButton();
            if (refreshData) {
                await Promise.all([this.loadDashboard(), this.loadTransactions()]);
            }
        } catch (error) {
            this.showToast('Erreur lors du chargement des mandats', 'error');
            console.error(error);
        }
    },

    async switchMandat(mandatId) {
        try {
            const response = await fetch('/api/mandat/active', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mandat_id: mandatId }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Impossible de changer de mandat');
            }

            const updated = await response.json();
            this.activeMandat = updated;
            this.mandats = this.mandats.map((m) => ({ ...m, active: Number(m.id) === Number(updated.id) }));
            this.state.dashboardExpandedIds = [];
            this.dashboard = [];
            this.transactions = [];
            this.syncDashboardYearFromMandat(updated);
            this.updateCurrentMandatButton();
            const select = document.getElementById('mandat-select');
            if (select) {
                select.value = String(updated.id);
            }
            await Promise.all([this.loadDashboard(), this.loadTransactions()]);
        } catch (error) {
            this.showToast(error.message || 'Erreur lors du changement de mandat', 'error');
        }
    },

    updateCurrentMandatButton() {
        const btn = document.getElementById('current-mandat-btn');
        if (!btn) {
            return;
        }
        const label = this.activeMandat?.name || 'Aucun mandat';
        btn.textContent = `Mandat: ${label}`;
    },

    async openMandatManagerModal() {
        const modal = document.getElementById('mandat-manager-modal');
        if (!modal) {
            return;
        }
        await this.loadMandats(false);
        modal.style.display = 'flex';
    },

    closeMandatManagerModal() {
        const modal = document.getElementById('mandat-manager-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    },

    getSelectedMandatFromManager() {
        const select = document.getElementById('mandat-select');
        const selectedId = Number(select?.value || this.state.managerSelectedMandatId || 0);
        if (!Number.isFinite(selectedId) || selectedId <= 0) {
            return null;
        }
        return this.mandats.find((m) => Number(m.id) === selectedId) || null;
    },

    syncDashboardYearFromMandat(mandat) {
        if (!mandat) return;
        const year = Number.parseInt(String(mandat.date_debut || '').slice(0, 4), 10);
        if (Number.isFinite(year)) {
            this.state.dashboardYear = year;
        }
    },

    getDashboardYear() {
        return Number.isFinite(Number(this.state.dashboardYear))
            ? Number(this.state.dashboardYear)
            : new Date().getFullYear();
    },

    openMandatModal() {
        const modal = document.getElementById('mandat-modal');
        if (!modal) return;
        const now = new Date();
        const year = now.getFullYear();
        this.state.editingMandatId = null;
        const title = document.getElementById('mandat-modal-title');
        if (title) {
            title.textContent = 'Créer un mandat';
        }
        document.getElementById('mandat-name').value = '';
        document.getElementById('mandat-date-debut').value = `${year}-01-01`;
        document.getElementById('mandat-date-fin').value = `${year}-12-31`;
        modal.style.display = 'flex';
    },

    openEditMandatModal() {
        const selected = this.getSelectedMandatFromManager() || this.activeMandat;
        if (!selected) {
            this.showToast('Aucun mandat sélectionné', 'error');
            return;
        }
        const modal = document.getElementById('mandat-modal');
        if (!modal) {
            return;
        }
        this.state.editingMandatId = Number(selected.id);
        const title = document.getElementById('mandat-modal-title');
        if (title) {
            title.textContent = 'Modifier le mandat';
        }
        document.getElementById('mandat-name').value = selected.name || '';
        document.getElementById('mandat-date-debut').value = selected.date_debut || '';
        document.getElementById('mandat-date-fin').value = selected.date_fin || '';
        modal.style.display = 'flex';
    },

    closeMandatModal() {
        const modal = document.getElementById('mandat-modal');
        if (modal) {
            modal.style.display = 'none';
        }
        this.state.editingMandatId = null;
    },

    async createMandatFromModal() {
        try {
            const payload = {
                name: document.getElementById('mandat-name').value,
                date_debut: document.getElementById('mandat-date-debut').value,
                date_fin: document.getElementById('mandat-date-fin').value,
            };

            const createResp = await fetch('/api/mandat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!createResp.ok) {
                const error = await createResp.json();
                throw new Error(error.error || 'Erreur lors de la création du mandat');
            }

            const created = await createResp.json();
            const activateResp = await fetch('/api/mandat/active', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mandat_id: created.id }),
            });
            if (!activateResp.ok) {
                const error = await activateResp.json();
                throw new Error(error.error || 'Mandat créé mais activation impossible');
            }

            this.closeMandatModal();
            await this.loadMandats();
            this.showToast('Mandat créé', 'success');
        } catch (error) {
            this.showToast(error.message || 'Erreur', 'error');
        }
    },

    async updateMandatFromModal() {
        const mandatId = this.state.editingMandatId;
        if (!mandatId) {
            return;
        }
        try {
            const payload = {
                name: document.getElementById('mandat-name').value,
                date_debut: document.getElementById('mandat-date-debut').value,
                date_fin: document.getElementById('mandat-date-fin').value,
            };

            const resp = await fetch(`/api/mandat/${mandatId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!resp.ok) {
                const error = await resp.json();
                throw new Error(error.error || 'Erreur lors de la modification du mandat');
            }

            this.closeMandatModal();
            await this.loadMandats();
            this.showToast('Mandat modifié', 'success');
        } catch (error) {
            this.showToast(error.message || 'Erreur', 'error');
        }
    },

    async deleteSelectedMandat() {
        const mandat = this.getSelectedMandatFromManager();
        if (!mandat || !mandat.id) {
            this.showToast('Aucun mandat sélectionné', 'error');
            return;
        }

        const confirmed = await this.showConfirmDialog({
            title: 'Supprimer le mandat',
            message: `Supprimer le mandat "${mandat.name}" ?`,
            details: 'Toutes les catégories, transactions et prévisionnels associés seront définitivement supprimés.',
            confirmText: 'Supprimer mandat',
            confirmClass: 'btn-danger',
        });

        if (!confirmed) {
            return;
        }

        try {
            const response = await fetch(`/api/mandat/${mandat.id}`, {
                method: 'DELETE',
            });
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Erreur lors de la suppression du mandat');
            }

            await this.loadMandats();
            this.showToast('Mandat supprimé', 'success');
        } catch (error) {
            this.showToast(error.message || 'Erreur', 'error');
        }
    },

    switchView(viewName) {
        // Masquer toutes les vues
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));

        // Mettre à jour la nav
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('data-view') === viewName) {
                link.classList.add('active');
            }
        });

        this.activeView = viewName;
        this.loadViewData();

        // Afficher la nouvelle vue
        const viewEl = this.getViewElement(viewName);
        if (viewEl) {
            viewEl.classList.add('active');
        }
    },

    getViewElement(viewName) {
        const viewMap = {
            'dashboard': 'dashboard-view',
            'transactions': 'transactions-view',
        };
        return document.getElementById(viewMap[viewName]);
    },

    async loadViewData() {
        if (!this.activeMandat) return;

        switch (this.activeView) {
            case 'dashboard':
                await this.loadDashboard();
                break;
            case 'transactions':
                await this.loadTransactions();
                break;
        }
    },

    // ===== DASHBOARD =====

    async loadDashboard() {
        try {
            this.captureDashboardExpandedState();
            await this.loadStructure();
            const response = await fetch(`/api/dashboard/${this.activeMandat.id}`);
            const data = await response.json();

            this.dashboard = data.performance || [];
            this.renderDashboard();
            this.restoreDashboardExpandedState();

            // Setup event listeners
            const refreshBtn = document.getElementById('dashboard-refresh');
            if (refreshBtn) {
                refreshBtn.onclick = () => this.loadDashboard();
            }
            document.getElementById('dashboard-expand-all').onclick = () => this.setAllExpanded('dashboard-content', true);
            document.getElementById('dashboard-collapse-all').onclick = () => this.setAllExpanded('dashboard-content', false);
            document.getElementById('dashboard-clear-previs').onclick = () => this.clearPrevisionnel();
            document.getElementById('dashboard-add-pole').onclick = () => this.showAddCategoryModal(null, null);
            document.getElementById('cancel-pole-btn')?.addEventListener('click', () => {
                document.getElementById('pole-modal').style.display = 'none';
            });
            document.getElementById('pole-form')?.addEventListener('submit', (e) => {
                e.preventDefault();
                this.updatePoleFromModal();
            });
        } catch (error) {
            console.error('Dashboard error:', error);
            this.showToast('Erreur lors du chargement du tableau de bord', 'error');
        }
    },

    renderDashboard() {
        const container = document.getElementById('dashboard-content');
        if (!container) return;

        container.innerHTML = '';

        const dashboardSummary = (this.dashboard || []).reduce((acc, node) => {
            acc.budgeted_expense += Number(node.budgeted_expense || 0);
            acc.budgeted_income += Number(node.budgeted_income || 0);
            acc.budgeted_total += Number(node.budgeted_total || 0);
            acc.actual_expense += Number(node.actual_expense || 0);
            acc.actual_income += Number(node.actual_income || 0);
            acc.actual_total += Number(node.actual_total || 0);
            return acc;
        }, {
            budgeted_expense: 0,
            budgeted_income: 0,
            budgeted_total: 0,
            actual_expense: 0,
            actual_income: 0,
            actual_total: 0,
        });
        dashboardSummary.variance = dashboardSummary.actual_total - dashboardSummary.budgeted_total;

        const renderNode = (node, depth = 0) => {
            const hasChildren = Array.isArray(node.children) && node.children.length > 0;
            const statusClass = node.variance > 0 ? 'status-good' : node.variance < 0 ? 'status-danger' : 'status-warning';

            const nodeEl = document.createElement('div');
            const poleThemeClass = depth === 0 ? this.getPoleThemeClass(node.name, 'dashboard-pole-theme') : '';
            nodeEl.className = `budget-node ${depth === 0 ? 'root-node' : ''} ${poleThemeClass}`.trim();
            if (depth === 0 && node.pole_color) {
                nodeEl.style.cssText = this.buildPoleStyleVariables(node.pole_color);
            }
            nodeEl.setAttribute('data-node-id', node.id);

            const header = document.createElement('div');
            header.className = `node-header ${statusClass}`;

            const labelCell = document.createElement('div');
            labelCell.className = 'node-label-cell';
            labelCell.style.paddingLeft = `${10 + depth * 18}px`;

            const toggle = document.createElement('button');
            toggle.className = 'expand-btn';
            toggle.textContent = '▶';
            toggle.style.visibility = hasChildren ? 'visible' : 'hidden';

            const name = document.createElement('span');
            name.className = 'node-name';
            name.textContent = node.name;

            labelCell.appendChild(toggle);
            labelCell.appendChild(name);

            const actions = document.createElement('div');
            actions.className = 'dashboard-node-actions';
            actions.innerHTML = `
                ${depth === 0 ? '<button type="button" class="dashboard-edit-pole" title="Modifier le pôle">⚙</button>' : ''}
                <button type="button" class="dashboard-add-node" title="Ajouter une sous-catégorie">+</button>
                <button type="button" class="dashboard-delete-node" title="Supprimer cette catégorie">✖</button>
            `;

            const budgetExpenseControl = hasChildren
                ? `<span class="budget budget-readonly" title="Calculé automatiquement depuis les sous-catégories">${this.formatCurrency(node.budgeted_expense || 0)}</span>`
                : `<button type="button" class="budget-edit" data-flow-type="expense" data-node-id="${node.id}" data-budget="${Number(node.budgeted_expense || 0)}">${this.formatCurrency(node.budgeted_expense || 0)}</button>`;

            const budgetIncomeControl = hasChildren
                ? `<span class="budget budget-readonly" title="Calculé automatiquement depuis les sous-catégories">${this.formatCurrency(node.budgeted_income || 0)}</span>`
                : `<button type="button" class="budget-edit" data-flow-type="income" data-node-id="${node.id}" data-budget="${Number(node.budgeted_income || 0)}">${this.formatCurrency(node.budgeted_income || 0)}</button>`;

            const values = document.createElement('span');
            values.className = 'node-values';
            const progress = this.computeAdvancement(node);
            values.innerHTML = `
                <span class="budget-col">${budgetExpenseControl}</span>
                <span class="budget-col">${budgetIncomeControl}</span>
                <span class="budget-col budget-total ${(Number(node.budgeted_total || 0) >= 0) ? 'is-positive' : 'is-negative'}">${this.formatCurrency(node.budgeted_total || 0)}</span>
                <span class="actual-col">${this.formatCurrency(node.actual_expense || 0)}</span>
                <span class="actual-col">${this.formatCurrency(node.actual_income || 0)}</span>
                <span class="actual-col actual-total ${(Number(node.actual_total || 0) >= 0) ? 'is-positive' : 'is-negative'}">${this.formatCurrency(node.actual_total || 0)}</span>
                <span class="progress-col">
                    <span class="progress-chip ${progress.levelClass}">${progress.percentText}</span>
                    <div class="progress-track" title="${progress.percentText}">
                        <div class="progress-fill ${progress.levelClass}" style="width:${progress.barWidth}%"></div>
                    </div>
                </span>
            `;

            header.appendChild(labelCell);
            header.appendChild(actions);
            header.appendChild(values);

            const childrenContainer = document.createElement('div');
            childrenContainer.className = 'node-children';
            childrenContainer.style.display = 'none';

            nodeEl.appendChild(header);
            nodeEl.appendChild(childrenContainer);

            if (hasChildren) {
                toggle.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const open = childrenContainer.style.display !== 'none';
                    childrenContainer.style.display = open ? 'none' : 'block';
                    toggle.classList.toggle('open', !open);
                });

                header.addEventListener('click', (e) => {
                    if (e.target.closest('.expand-btn') || e.target.closest('.budget-edit') || e.target.closest('.budget-edit-input')) {
                        return;
                    }
                    const open = childrenContainer.style.display !== 'none';
                    childrenContainer.style.display = open ? 'none' : 'block';
                    toggle.classList.toggle('open', !open);
                });

                node.children.forEach((child) => {
                    childrenContainer.appendChild(renderNode(child, depth + 1));
                });
            }

            const budgetButtons = values.querySelectorAll('.budget-edit');
            budgetButtons.forEach((btn) => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.startInlineBudgetEdit(
                        btn,
                        node.id,
                        Number(btn.getAttribute('data-budget') || 0),
                        btn.getAttribute('data-flow-type') || 'expense',
                    );
                });
            });

            const addNodeBtn = actions.querySelector('.dashboard-add-node');
            addNodeBtn?.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showAddCategoryModal(node.id, node.name);
            });

            const editPoleBtn = actions.querySelector('.dashboard-edit-pole');
            editPoleBtn?.addEventListener('click', (e) => {
                e.stopPropagation();
                this.openPoleModal(node.id);
            });

            const deleteNodeBtn = actions.querySelector('.dashboard-delete-node');
            deleteNodeBtn?.addEventListener('click', async (e) => {
                e.stopPropagation();
                const confirmed = await this.showConfirmDialog({
                    title: 'Supprimer une catégorie',
                    message: `Supprimer "${node.name}" et toutes ses sous-catégories ?`,
                    details: 'Les transactions associées seront masquées.',
                    confirmText: 'Supprimer',
                    confirmClass: 'btn-danger',
                });
                if (!confirmed) {
                    return;
                }
                await this.deleteNode(node.id);
            });

            return nodeEl;
        };

        const totalNode = document.createElement('div');
        totalNode.className = 'budget-node dashboard-total-node';

        const totalHeader = document.createElement('div');
        const totalStatusClass = dashboardSummary.variance > 0 ? 'status-good' : dashboardSummary.variance < 0 ? 'status-danger' : 'status-warning';
        totalHeader.className = `node-header ${totalStatusClass} dashboard-total-header`;

        const totalLabelCell = document.createElement('div');
        totalLabelCell.className = 'node-label-cell';
        totalLabelCell.style.paddingLeft = '10px';

        const totalTogglePlaceholder = document.createElement('button');
        totalTogglePlaceholder.className = 'expand-btn';
        totalTogglePlaceholder.textContent = '▶';
        totalTogglePlaceholder.style.visibility = 'hidden';

        const totalName = document.createElement('span');
        totalName.className = 'node-name';
        totalName.textContent = 'TOTAL MANDAT';

        totalLabelCell.appendChild(totalTogglePlaceholder);
        totalLabelCell.appendChild(totalName);

        const totalActions = document.createElement('div');
        totalActions.className = 'dashboard-node-actions';

        const totalValues = document.createElement('span');
        totalValues.className = 'node-values';
        const totalProgress = this.computeAdvancement({
            budgeted_total: dashboardSummary.budgeted_total,
            actual_total: dashboardSummary.actual_total,
        });
        totalValues.innerHTML = `
            <span class="budget-col"><span class="budget budget-readonly">${this.formatCurrency(dashboardSummary.budgeted_expense)}</span></span>
            <span class="budget-col"><span class="budget budget-readonly">${this.formatCurrency(dashboardSummary.budgeted_income)}</span></span>
            <span class="budget-col budget-total ${dashboardSummary.budgeted_total >= 0 ? 'is-positive' : 'is-negative'}">${this.formatCurrency(dashboardSummary.budgeted_total)}</span>
            <span class="actual-col">${this.formatCurrency(dashboardSummary.actual_expense)}</span>
            <span class="actual-col">${this.formatCurrency(dashboardSummary.actual_income)}</span>
            <span class="actual-col actual-total ${dashboardSummary.actual_total >= 0 ? 'is-positive' : 'is-negative'}">${this.formatCurrency(dashboardSummary.actual_total)}</span>
            <span class="progress-col">
                <span class="progress-chip ${totalProgress.levelClass}">${totalProgress.percentText}</span>
                <div class="progress-track" title="${totalProgress.percentText}">
                    <div class="progress-fill ${totalProgress.levelClass}" style="width:${totalProgress.barWidth}%"></div>
                </div>
            </span>
        `;

        totalHeader.appendChild(totalLabelCell);
        totalHeader.appendChild(totalActions);
        totalHeader.appendChild(totalValues);
        totalNode.appendChild(totalHeader);
        container.appendChild(totalNode);

        this.dashboard.forEach((node) => container.appendChild(renderNode(node)));
    },

    // ===== TRANSACTIONS =====

    async loadTransactions() {
        try {
            const response = await fetch(`/api/transactions/${this.activeMandat.id}`);
            const data = await response.json();
            this.state.transactionsRaw = data.transactions || [];
            this.loadTransactionTreeExpandedStateFromStorage();

            await this.loadStructure();
            this.populateTransactionCategoryFilter();
            this.setupTransactionFilters();

            const modeSelect = document.getElementById('trans-display-mode');
            if (modeSelect) {
                this.state.transactionDisplayMode = modeSelect.value || 'history';
                modeSelect.onchange = () => {
                    this.state.transactionDisplayMode = modeSelect.value || 'history';
                    this.applyTransactionFilters();
                    this.updateTransactionTreeControlsVisibility();
                };
            }

            this.applyTransactionFilters();
            this.setupTransactionListeners();
            this.updateTransactionTreeControlsVisibility();
        } catch (error) {
            console.error('Transactions error:', error);
            this.showToast('Erreur lors du chargement des transactions', 'error');
        }
    },

    setupTransactionFilters() {
        if (this.state.transactionFiltersInitialized) {
            return;
        }

        const searchInput = document.getElementById('trans-search');
        const typeFilter = document.getElementById('trans-filter-type');
        const categoryFilter = document.getElementById('trans-filter-category');
        const monthFilter = document.getElementById('trans-filter-month');

        const onFilterChange = () => this.applyTransactionFilters();

        searchInput?.addEventListener('input', onFilterChange);
        typeFilter?.addEventListener('change', onFilterChange);
        categoryFilter?.addEventListener('change', onFilterChange);
        monthFilter?.addEventListener('change', onFilterChange);

        this.state.transactionFiltersInitialized = true;
    },

    getStructureNodeMetaMap() {
        const map = new Map();

        const walk = (nodes, ancestors = []) => {
            (nodes || []).forEach((node) => {
                const name = String(node?.name || '');
                const path = [...ancestors, name];
                map.set(Number(node.id), {
                    id: Number(node.id),
                    name,
                    path,
                    pathLabel: path.join(' > '),
                });

                const children = Array.isArray(node.children) ? node.children : [];
                walk(children, path);
            });
        };

        walk(this.structure || []);
        return map;
    },

    populateTransactionCategoryFilter() {
        const categoryFilter = document.getElementById('trans-filter-category');
        if (!categoryFilter) {
            return;
        }

        const previousValue = categoryFilter.value;
        const nodeMetaMap = this.getStructureNodeMetaMap();
        const byNodeId = new Map();
        let hasUncategorized = false;

        (this.state.transactionsRaw || []).forEach((trans) => {
            const nodeId = Number(trans.node_id || 0);
            if (!Number.isFinite(nodeId) || nodeId <= 0) {
                hasUncategorized = true;
                return;
            }

            if (!byNodeId.has(nodeId)) {
                const meta = nodeMetaMap.get(nodeId);
                byNodeId.set(nodeId, {
                    id: nodeId,
                    label: meta?.pathLabel || String(trans.node_name || `Categorie #${nodeId}`),
                });
            }
        });

        const options = Array.from(byNodeId.values()).sort((a, b) => a.label.localeCompare(b.label, 'fr'));

        categoryFilter.innerHTML = '<option value="">Toutes les categories</option>';
        options.forEach((optionData) => {
            const option = document.createElement('option');
            option.value = String(optionData.id);
            option.textContent = optionData.label;
            categoryFilter.appendChild(option);
        });

        if (hasUncategorized) {
            const option = document.createElement('option');
            option.value = '__uncategorized';
            option.textContent = 'Non categorise';
            categoryFilter.appendChild(option);
        }

        const hasPrevious = Array.from(categoryFilter.options).some((opt) => opt.value === previousValue);
        categoryFilter.value = hasPrevious ? previousValue : '';
    },

    getFilteredTransactions() {
        const search = (document.getElementById('trans-search')?.value || '').trim().toLowerCase();
        const type = document.getElementById('trans-filter-type')?.value || '';
        const category = document.getElementById('trans-filter-category')?.value || '';
        const month = document.getElementById('trans-filter-month')?.value || '';

        return (this.state.transactionsRaw || []).filter((trans) => {
            if (type && String(trans.flow_type || '') !== type) {
                return false;
            }

            if (category === '__uncategorized') {
                const nodeId = Number(trans.node_id || 0);
                if (Number.isFinite(nodeId) && nodeId > 0) {
                    return false;
                }
            } else if (category && String(trans.node_id || '') !== category) {
                return false;
            }

            if (month && !String(trans.date || '').startsWith(month)) {
                return false;
            }

            if (!search) {
                return true;
            }

            const searchable = [
                trans.label,
                trans.description,
                trans.node_name,
                trans.order_number,
                trans.payment_method,
                trans.date,
                String(trans.amount ?? ''),
            ]
                .join(' ')
                .toLowerCase();

            return searchable.includes(search);
        });
    },

    applyTransactionFilters() {
        this.transactions = this.getFilteredTransactions();
        this.renderTransactions();
    },

    renderTransactions() {
        const container = document.getElementById('transactions-list');
        if (!container) return;

        container.innerHTML = '';
        this.updateTransactionTreeControlsVisibility();

        if (this.transactions.length === 0) {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-secondary);">Aucune transaction</div>';
            return;
        }

        if (this.state.transactionDisplayMode === 'tree') {
            this.renderTransactionsByTree(container);
            this.setupTransactionRowListeners();
            return;
        }

        this.renderTransactionsHistory(container);
        this.setupTransactionRowListeners();
    },

    renderTransactionsHistory(container) {
        if (!container) return;

        const orderedTransactions = [...(this.transactions || [])].sort((a, b) => {
            const createdA = Date.parse(String(a?.created_at || ''));
            const createdB = Date.parse(String(b?.created_at || ''));
            const safeCreatedA = Number.isFinite(createdA) ? createdA : 0;
            const safeCreatedB = Number.isFinite(createdB) ? createdB : 0;
            if (safeCreatedA !== safeCreatedB) {
                return safeCreatedB - safeCreatedA;
            }

            const idA = Number(a?.id || 0);
            const idB = Number(b?.id || 0);
            if (idA !== idB) {
                return idB - idA;
            }

            const dateA = Date.parse(String(a?.date || ''));
            const dateB = Date.parse(String(b?.date || ''));
            const safeDateA = Number.isFinite(dateA) ? dateA : 0;
            const safeDateB = Number.isFinite(dateB) ? dateB : 0;
            return safeDateB - safeDateA;
        });

        orderedTransactions.forEach(trans => {
            const poleInfo = this.getPoleInfoForNodeId(trans.node_id);
            const poleName = poleInfo?.name || '';
            const poleThemeClass = this.getPoleThemeClass(poleName, 'pole-theme');
            const poleStyle = this.buildPoleStyleVariables(poleInfo?.pole_color || '');
            const paymentMethodMap = {
                virement: 'Virement',
                cheque: 'Cheque',
                especes: 'Especes',
                carte: 'Carte',
            };
            const paymentKey = String(trans.payment_method || '').toLowerCase();
            const paymentLabel = paymentMethodMap[paymentKey] || (trans.payment_method ? String(trans.payment_method).charAt(0).toUpperCase() + String(trans.payment_method).slice(1) : '-');
            const orderLabel = trans.order_number ? this.escapeHtml(trans.order_number) : '-';
            const attachments = Array.isArray(trans.attachments) ? trans.attachments : [];
            const attachmentsHtml = attachments.length
                ? `<div class="transaction-attachments-links">${attachments.map((att, index) => {
                    const path = String(att.file_path || '').trim();
                    const fileName = path.split('/').pop() || `Justificatif ${index + 1}`;
                    return `<a href="/justificatifs/${encodeURI(path)}" target="_blank" rel="noopener noreferrer">${this.escapeHtml(fileName)}</a>`;
                }).join('')}</div>`
                : '<span class="transaction-empty">Aucun justificatif</span>';

            const row = document.createElement('div');
            row.className = `transaction-row ${poleThemeClass}`;
            if (poleStyle) {
                row.style.cssText = poleStyle;
            }
            row.setAttribute('data-transaction-id', trans.id);
            row.innerHTML = `
                <div class="transaction-main">
                    <div class="transaction-date">${this.formatDate(trans.date)}</div>
                    <div class="transaction-label">${this.escapeHtml(trans.label || '')}</div>
                    <div class="transaction-type ${trans.flow_type}">${trans.flow_type === 'income' ? 'Revenu' : 'Dépense'}</div>
                    <div class="transaction-amount ${trans.flow_type}">${this.formatCurrency(trans.amount)}</div>
                    <div class="transaction-order">${orderLabel}</div>
                    <div class="transaction-actions">
                        <button class="btn-action delete-btn" title="Supprimer">✖</button>
                    </div>
                </div>
                <div class="transaction-details">
                    <div class="transaction-details-col">
                        <div><span class="detail-label">Pôle:</span> <span class="detail-value">${this.escapeHtml(poleName || 'Non défini')}</span></div>
                        <div><span class="detail-label">Catégorie:</span> <span class="detail-value">${this.escapeHtml(trans.node_name || 'Non catégorisé')}</span></div>
                        <div><span class="detail-label">Description:</span> <span class="detail-value">${this.escapeHtml(trans.description || '-')}</span></div>
                    </div>
                    <div class="transaction-details-col">
                        <div><span class="detail-label">Paiement:</span> <span class="detail-value">${this.escapeHtml(paymentLabel)}</span></div>
                        <div><span class="detail-label">Ordre:</span> <span class="detail-value">${orderLabel}</span></div>
                        <div><span class="detail-label">Justificatifs (${attachments.length}):</span> ${attachmentsHtml}</div>
                    </div>
                </div>
            `;
            container.appendChild(row);
        });
    },

    renderTransactionsByTree(container) {
        if (!container) return;

        const summary = (this.transactions || []).reduce((acc, trans) => {
            const amount = Number(trans.amount || 0);
            if (String(trans.flow_type || '') === 'income') {
                acc.income += amount;
            } else {
                acc.expense += amount;
            }
            acc.count += 1;
            return acc;
        }, { income: 0, expense: 0, count: 0 });
        summary.total = summary.income - summary.expense;

        const formatPaymentMethod = (value) => {
            const key = String(value || '').toLowerCase();
            const map = {
                virement: 'Virement',
                cheque: 'Cheque',
                especes: 'Especes',
                carte: 'Carte',
            };
            return map[key] || (value ? String(value) : '-');
        };

        const renderAttachmentsCell = (attachments) => {
            if (!attachments.length) {
                return '<div class="tree-trans-attachments"><span class="tree-trans-empty">Aucun</span></div>';
            }

            return `<div class="tree-trans-attachments">${attachments.map((att, index) => {
                const path = String(att.file_path || '').trim();
                const fileName = path.split('/').pop() || `Justificatif ${index + 1}`;
                return `<a href="/justificatifs/${encodeURI(path)}" target="_blank" rel="noopener noreferrer">${this.escapeHtml(fileName)}</a>`;
            }).join('')}</div>`;
        };

        const byNodeId = new Map();
        this.transactions.forEach((trans) => {
            const key = Number(trans.node_id || 0);
            if (!byNodeId.has(key)) {
                byNodeId.set(key, []);
            }
            byNodeId.get(key).push(trans);
        });

        const makeTransactionsList = (items, depth = 0) => {
            const list = document.createElement('div');
            list.className = 'tree-trans-list';

            const orderedItems = [...(items || [])].sort((a, b) => {
                const createdA = Date.parse(String(a?.created_at || ''));
                const createdB = Date.parse(String(b?.created_at || ''));
                const safeCreatedA = Number.isFinite(createdA) ? createdA : 0;
                const safeCreatedB = Number.isFinite(createdB) ? createdB : 0;
                if (safeCreatedA !== safeCreatedB) {
                    return safeCreatedB - safeCreatedA;
                }

                const idA = Number(a?.id || 0);
                const idB = Number(b?.id || 0);
                return idB - idA;
            });

            orderedItems.forEach((trans) => {
                const amount = Number(trans.amount || 0);
                const isIncome = String(trans.flow_type || '') === 'income';
                const expenseValue = isIncome ? 0 : amount;
                const incomeValue = isIncome ? amount : 0;
                const totalValue = incomeValue - expenseValue;
                const attachments = Array.isArray(trans.attachments) ? trans.attachments : [];
                const orderLabel = trans.order_number ? this.escapeHtml(trans.order_number) : '-';

                const item = document.createElement('div');
                item.className = `tree-trans-item ${this.escapeHtml(trans.flow_type || '')}`;
                item.setAttribute('data-transaction-id', trans.id);
                item.innerHTML = `
                    <span class="tree-trans-col tree-trans-col-label" style="padding-left: ${14 + depth * 18}px;">
                        <span class="tree-trans-label-content">${this.escapeHtml(trans.label || '')}</span>
                    </span>
                    <span class="tree-trans-col tree-trans-col-date">${this.formatDate(trans.date)}</span>
                    <span class="tree-trans-col tree-trans-col-payment">${this.escapeHtml(formatPaymentMethod(trans.payment_method))}</span>
                    <span class="tree-trans-col tree-trans-col-order">${orderLabel}</span>
                    <span class="tree-trans-col tree-trans-col-justif">${renderAttachmentsCell(attachments)}</span>
                    <span class="tree-trans-col tree-trans-col-expense">${expenseValue > 0 ? this.formatCurrency(expenseValue) : '-'}</span>
                    <span class="tree-trans-col tree-trans-col-income">${incomeValue > 0 ? this.formatCurrency(incomeValue) : '-'}</span>
                    <span class="tree-trans-col tree-trans-col-total ${totalValue >= 0 ? 'is-positive' : 'is-negative'}">${this.formatCurrency(totalValue)}</span>
                `;
                list.appendChild(item);
            });

            return list;
        };

        const summarizeTransactions = (items) => {
            return (items || []).reduce((acc, trans) => {
                const amount = Number(trans.amount || 0);
                if (String(trans.flow_type || '') === 'income') {
                    acc.income += amount;
                } else {
                    acc.expense += amount;
                }
                acc.count += 1;
                return acc;
            }, { income: 0, expense: 0, count: 0 });
        };

        const buildTreeNode = (node, depth = 0) => {
            const ownTransactions = byNodeId.get(Number(node.id)) || [];
            const ownSummary = summarizeTransactions(ownTransactions);
            const childrenResults = [];

            (Array.isArray(node.children) ? node.children : []).forEach((child) => {
                const childResult = buildTreeNode(child, depth + 1);
                if (childResult) {
                    childrenResults.push(childResult);
                }
            });

            const summary = childrenResults.reduce((acc, child) => {
                acc.income += child.summary.income;
                acc.expense += child.summary.expense;
                acc.count += child.summary.count;
                return acc;
            }, { income: ownSummary.income, expense: ownSummary.expense, count: ownSummary.count });

            if (summary.count === 0) {
                return null;
            }

            const net = summary.income - summary.expense;
            const statusClass = net > 0 ? 'trans-status-income' : net < 0 ? 'trans-status-expense' : 'trans-status-balanced';

            const nodeEl = document.createElement('div');
            const poleThemeClass = depth === 0 ? this.getPoleThemeClass(node.name, 'trans-pole-theme') : '';
            nodeEl.className = `trans-budget-node depth-${Math.min(depth, 6)} ${depth === 0 ? 'root-node' : ''} ${poleThemeClass}`.trim();
            if (depth === 0 && node.pole_color) {
                nodeEl.style.cssText = this.buildPoleStyleVariables(node.pole_color);
            }
            nodeEl.setAttribute('data-node-id', String(node.id));

            const header = document.createElement('div');
            header.className = `trans-node-header ${statusClass}`;

            const labelCell = document.createElement('div');
            labelCell.className = 'trans-node-label-cell';
            labelCell.style.paddingLeft = `${10 + depth * 18}px`;

            const hasExpandableContent = childrenResults.length > 0 || ownTransactions.length > 0;
            const isLeafNode = childrenResults.length === 0;
            const toggle = document.createElement('button');
            toggle.className = 'expand-btn';
            toggle.textContent = '▶';
            toggle.style.visibility = hasExpandableContent ? 'visible' : 'hidden';

            const name = document.createElement('span');
            name.className = 'trans-node-name';
            name.textContent = String(node.name || 'Sans nom');

            labelCell.appendChild(toggle);
            labelCell.appendChild(name);

            if (isLeafNode) {
                const addBtn = document.createElement('button');
                addBtn.type = 'button';
                addBtn.className = 'btn-action trans-node-add-btn';
                addBtn.title = 'Ajouter une transaction dans cette categorie';
                addBtn.textContent = '+';
                addBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.openTransactionFormForCreateForNode(node.id);
                });
                labelCell.appendChild(addBtn);
            }

            const values = document.createElement('div');
            values.className = 'trans-node-values';
            values.style.display = 'contents';
            values.innerHTML = `
                <span class="trans-node-info muted">-</span>
                <span class="trans-node-info muted">-</span>
                <span class="trans-node-info muted">-</span>
                <span class="trans-node-info trans-node-info-justif">${summary.count} transaction(s)</span>
                <span class="trans-node-amount trans-node-expense">${this.formatCurrency(summary.expense)}</span>
                <span class="trans-node-amount trans-node-income">${this.formatCurrency(summary.income)}</span>
                <span class="trans-node-amount trans-node-total ${net >= 0 ? 'is-positive' : 'is-negative'}">${this.formatCurrency(net)}</span>
            `;

            const childrenContainer = document.createElement('div');
            childrenContainer.className = 'node-children';
            childrenContainer.style.display = depth === 0 ? 'block' : 'none';
            if (depth === 0) {
                toggle.classList.add('open');
            }

            if (ownTransactions.length) {
                childrenContainer.appendChild(makeTransactionsList(ownTransactions, depth + 1));
            }
            childrenResults.forEach((childResult) => {
                childrenContainer.appendChild(childResult.element);
            });

            header.appendChild(labelCell);
            header.appendChild(values);
            nodeEl.appendChild(header);
            nodeEl.appendChild(childrenContainer);

            if (hasExpandableContent) {
                const toggleExpand = () => {
                    const isOpen = childrenContainer.style.display !== 'none';
                    childrenContainer.style.display = isOpen ? 'none' : 'block';
                    toggle.classList.toggle('open', !isOpen);
                    this.captureTransactionTreeExpandedState();
                    this.saveTransactionTreeExpandedStateToStorage();
                };

                toggle.addEventListener('click', (e) => {
                    e.stopPropagation();
                    toggleExpand();
                });

                header.addEventListener('click', (e) => {
                    if (e.target.closest('.expand-btn')) {
                        return;
                    }
                    toggleExpand();
                });
            }

            return {
                element: nodeEl,
                summary,
            };
        };

        const table = document.createElement('div');
        table.className = 'trans-tree-table';

        const head = document.createElement('div');
        head.className = 'trans-tree-head';
        head.innerHTML = `
            <div class="trans-tree-head-group trans-tree-head-group-info">Informations</div>
            <div class="trans-tree-head-group trans-tree-head-group-amounts">Montants</div>
            <div class="trans-tree-head-sub trans-tree-head-sub-info">Categorie / Transaction</div>
            <div class="trans-tree-head-sub trans-tree-head-sub-info">Date</div>
            <div class="trans-tree-head-sub trans-tree-head-sub-info">Paiement</div>
            <div class="trans-tree-head-sub trans-tree-head-sub-info">Ordre</div>
            <div class="trans-tree-head-sub trans-tree-head-sub-info">Justificatif</div>
            <div class="trans-tree-head-sub trans-tree-head-sub-amount">Depenses</div>
            <div class="trans-tree-head-sub trans-tree-head-sub-amount">Recettes</div>
            <div class="trans-tree-head-sub trans-tree-head-sub-amount trans-tree-head-sub-total">Total</div>
        `;

        const fragment = document.createDocumentFragment();
        const totalBlock = document.createElement('div');
        totalBlock.className = 'trans-budget-node trans-total-row-node';
        const totalHeader = document.createElement('div');
        totalHeader.className = 'trans-node-header trans-status-balanced trans-total-header';
        totalHeader.innerHTML = `
            <div class="trans-node-label-cell" style="padding-left: 10px;">
                <span class="trans-node-name">TOTAL MANDAT</span>
            </div>
            <div class="trans-node-info muted">-</div>
            <div class="trans-node-info muted">-</div>
            <div class="trans-node-info muted">-</div>
            <div class="trans-node-info trans-node-info-justif">${summary.count} transaction(s)</div>
            <div class="trans-node-amount trans-node-expense">${this.formatCurrency(summary.expense)}</div>
            <div class="trans-node-amount trans-node-income">${this.formatCurrency(summary.income)}</div>
            <div class="trans-node-amount trans-node-total ${summary.total >= 0 ? 'is-positive' : 'is-negative'}">${this.formatCurrency(summary.total)}</div>
        `;
        totalBlock.appendChild(totalHeader);
        fragment.appendChild(totalBlock);

        (this.structure || []).forEach((node) => {
            const result = buildTreeNode(node);
            if (result) {
                fragment.appendChild(result.element);
            }
        });

        const uncategorized = byNodeId.get(0) || [];
        if (uncategorized.length) {
            const block = document.createElement('div');
            block.className = 'trans-budget-node uncategorized';

            const header = document.createElement('div');
            header.className = 'trans-node-header trans-status-balanced';
            header.innerHTML = `
                <div class="trans-node-label-cell" style="padding-left: 10px;">
                    <span class="trans-node-name">Non categorise</span>
                </div>
                <div class="trans-node-info muted">-</div>
                <div class="trans-node-info muted">-</div>
                <div class="trans-node-info muted">-</div>
                <div class="trans-node-info trans-node-info-justif">${uncategorized.length} transaction(s)</div>
                <div class="trans-node-amount trans-node-expense">-</div>
                <div class="trans-node-amount trans-node-income">-</div>
                <div class="trans-node-amount trans-node-total">-</div>
            `;

            block.appendChild(header);
            block.appendChild(makeTransactionsList(uncategorized));
            fragment.appendChild(block);
        }

        container.innerHTML = '';
        if (!fragment.childNodes.length) {
            container.innerHTML = '<div style="padding: 20px; color: var(--text-secondary);">Aucune transaction pour cette arborescence.</div>';
            return;
        }

        table.appendChild(head);
        table.appendChild(fragment);
        container.appendChild(table);
        this.restoreTransactionTreeExpandedState();
    },

    updateTransactionTreeControlsVisibility() {
        const show = this.state.transactionDisplayMode === 'tree';
        const expandBtn = document.getElementById('trans-expand-all');
        const collapseBtn = document.getElementById('trans-collapse-all');
        [expandBtn, collapseBtn].forEach((btn) => {
            if (!btn) {
                return;
            }
            btn.style.display = show ? 'inline-flex' : 'none';
            btn.disabled = !show;
        });
    },

    setAllTransactionsTreeExpanded(expanded) {
        const container = document.getElementById('transactions-list');
        if (!container) {
            return;
        }

        container.querySelectorAll('.trans-budget-node .node-children').forEach((el) => {
            el.style.display = expanded ? 'block' : 'none';
        });

        container.querySelectorAll('.trans-budget-node .expand-btn').forEach((btn) => {
            btn.classList.toggle('open', expanded);
        });

        this.captureTransactionTreeExpandedState();
        this.saveTransactionTreeExpandedStateToStorage();
    },

    getTransactionTreeStorageKey() {
        const mandatId = Number(this.activeMandat?.id || 0);
        return mandatId > 0 ? `bde:trans-tree-expanded:${mandatId}` : null;
    },

    loadTransactionTreeExpandedStateFromStorage() {
        const key = this.getTransactionTreeStorageKey();
        this.state.transactionTreeExpandedIds = null;
        if (!key) {
            return;
        }

        try {
            const raw = localStorage.getItem(key);
            if (raw == null) {
                return;
            }
            const parsed = JSON.parse(raw);
            if (Array.isArray(parsed)) {
                this.state.transactionTreeExpandedIds = parsed.map((id) => String(id));
            }
        } catch {
            this.state.transactionTreeExpandedIds = null;
        }
    },

    saveTransactionTreeExpandedStateToStorage() {
        const key = this.getTransactionTreeStorageKey();
        if (!key || !Array.isArray(this.state.transactionTreeExpandedIds)) {
            return;
        }

        try {
            localStorage.setItem(key, JSON.stringify(this.state.transactionTreeExpandedIds));
        } catch {
            // localStorage may be unavailable in some contexts.
        }
    },

    captureTransactionTreeExpandedState() {
        const container = document.getElementById('transactions-list');
        if (!container) {
            return;
        }

        const expandedIds = [];
        container.querySelectorAll('.trans-budget-node[data-node-id]').forEach((nodeEl) => {
            const children = nodeEl.querySelector(':scope > .node-children');
            if (children && children.style.display !== 'none') {
                const id = nodeEl.getAttribute('data-node-id');
                if (id) {
                    expandedIds.push(String(id));
                }
            }
        });

        this.state.transactionTreeExpandedIds = expandedIds;
    },

    restoreTransactionTreeExpandedState() {
        const container = document.getElementById('transactions-list');
        const wanted = this.state.transactionTreeExpandedIds;
        if (!container || !Array.isArray(wanted)) {
            return;
        }

        const wantedSet = new Set(wanted.map(String));
        container.querySelectorAll('.trans-budget-node[data-node-id]').forEach((nodeEl) => {
            const id = String(nodeEl.getAttribute('data-node-id') || '');
            const children = nodeEl.querySelector(':scope > .node-children');
            const btn = nodeEl.querySelector(':scope > .trans-node-header .expand-btn');
            if (!children || !id) {
                return;
            }

            const isOpen = wantedSet.has(id);
            children.style.display = isOpen ? 'block' : 'none';
            if (btn) {
                btn.classList.toggle('open', isOpen);
            }
        });
    },

    getPoleInfoForNodeId(nodeId) {
        const target = Number(nodeId);
        if (!Number.isFinite(target) || target <= 0) {
            return null;
        }

        const findInBranch = (node, rootPole) => {
            if (Number(node.id) === target) {
                return rootPole;
            }

            const children = Array.isArray(node.children) ? node.children : [];
            for (const child of children) {
                const found = findInBranch(child, rootPole);
                if (found) {
                    return found;
                }
            }
            return null;
        };

        for (const poleNode of this.structure || []) {
            const found = findInBranch(poleNode, poleNode);
            if (found) {
                return found;
            }
        }

        return null;
    },

    getPoleNameForNodeId(nodeId) {
        return String(this.getPoleInfoForNodeId(nodeId)?.name || '');
    },

    normalizeHexColor(value) {
        const raw = String(value || '').trim();
        if (!raw) {
            return '';
        }

        if (/^#[0-9a-fA-F]{3}$/.test(raw)) {
            return `#${raw.slice(1).split('').map((part) => part + part).join('')}`.toLowerCase();
        }

        if (/^#[0-9a-fA-F]{6}$/.test(raw)) {
            return raw.toLowerCase();
        }

        return '';
    },

    hexToRgb(hex) {
        const value = this.normalizeHexColor(hex);
        if (!value) {
            return null;
        }

        const numeric = Number.parseInt(value.slice(1), 16);
        return {
            r: (numeric >> 16) & 255,
            g: (numeric >> 8) & 255,
            b: numeric & 255,
        };
    },

    shadeHexColor(hex, percent) {
        const rgb = this.hexToRgb(hex);
        if (!rgb) {
            return '';
        }

        const clamp = (value) => Math.max(0, Math.min(255, value));
        const mix = percent >= 0 ? 255 : 0;
        const factor = Math.abs(percent);
        const red = clamp(Math.round((mix - rgb.r) * factor + rgb.r));
        const green = clamp(Math.round((mix - rgb.g) * factor + rgb.g));
        const blue = clamp(Math.round((mix - rgb.b) * factor + rgb.b));
        return `#${[red, green, blue].map((value) => value.toString(16).padStart(2, '0')).join('')}`;
    },

    getReadableTextColor(hex) {
        const rgb = this.hexToRgb(hex);
        if (!rgb) {
            return '#0d2238';
        }

        const luminance = (0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b) / 255;
        return luminance > 0.62 ? '#0d2238' : '#ffffff';
    },

    buildPoleStyleVariables(poleColor) {
        const base = this.normalizeHexColor(poleColor);
        if (!base) {
            return '';
        }

        const light = this.shadeHexColor(base, 0.16) || base;
        const dark = this.shadeHexColor(base, -0.18) || base;
        const text = this.getReadableTextColor(base);
        return `--pole-band: ${base}; --pole-bg: linear-gradient(180deg, ${light} 0%, ${dark} 100%); --pole-text: ${text}; --pole-text-primary: ${text}; --pole-text-secondary: ${text};`;
    },

    openPoleModal(nodeId) {
        const pole = this.getPoleInfoForNodeId(nodeId);
        if (!pole || pole.parent_id !== null) {
            this.showToast('Pôle introuvable', 'error');
            return;
        }

        document.getElementById('pole-id').value = String(pole.id || '');
        document.getElementById('pole-name').value = String(pole.name || '');
        document.getElementById('pole-color').value = this.normalizeHexColor(pole.pole_color) || '#83c9ff';
        document.getElementById('pole-modal').style.display = 'block';
    },

    async updatePoleFromModal() {
        try {
            if (!this.activeMandat?.id) {
                this.showToast('Aucun mandat sélectionné', 'error');
                return;
            }

            const nodeId = Number(document.getElementById('pole-id').value || 0);
            const name = document.getElementById('pole-name').value.trim();
            const poleColor = document.getElementById('pole-color').value;

            if (!nodeId || !name) {
                this.showToast('Nom de pôle invalide', 'error');
                return;
            }

            const response = await fetch(`/api/node/${this.activeMandat.id}/${nodeId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, pole_color: poleColor }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Erreur lors de la mise à jour du pôle');
            }

            document.getElementById('pole-modal').style.display = 'none';
            this.showToast('Pôle modifié', 'success');
            await this.loadStructure();
            await this.loadDashboard();
            await this.loadTransactions();
        } catch (error) {
            this.showToast(error.message || 'Erreur', 'error');
        }
    },

    setupTransactionListeners() {
        this.setupTransactionModalListeners();
        this.ensureTransactionContextMenu();

        document.getElementById('new-transaction-btn').onclick = () => {
            this.openTransactionFormForCreate();
        };

        document.getElementById('open-justif-folder-btn').onclick = () => {
            this.openMandatJustificatifsFolder();
        };

        document.getElementById('trans-expand-all').onclick = () => {
            this.setAllTransactionsTreeExpanded(true);
        };

        document.getElementById('trans-collapse-all').onclick = () => {
            this.setAllTransactionsTreeExpanded(false);
        };

        document.getElementById('cancel-form-btn').onclick = () => {
            this.closeAndResetTransactionForm();
        };

        document.getElementById('transaction-form').onsubmit = (e) => {
            e.preventDefault();
            if (this.state.editingTransactionId) {
                this.updateTransaction(this.state.editingTransactionId);
                return;
            }
            this.createTransaction();
        };

        this.setupTransactionRowListeners();
        this.updateTransactionTreeControlsVisibility();
    },

    setupTransactionModalListeners() {
        if (this.state.transactionModalListenersInitialized) {
            return;
        }

        const modal = document.getElementById('transaction-form-container');
        const closeBtn = document.getElementById('close-transaction-modal-btn');
        if (!modal) {
            return;
        }

        closeBtn?.addEventListener('click', () => {
            this.closeAndResetTransactionForm();
        });

        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                this.closeAndResetTransactionForm();
            }
        });

        document.addEventListener('keydown', (event) => {
            if (event.key !== 'Escape') {
                return;
            }
            if (modal.style.display === 'block') {
                this.closeAndResetTransactionForm();
            }
        });

        this.state.transactionModalListenersInitialized = true;
    },

    setupTransactionRowListeners() {
        document.querySelectorAll('.transaction-row').forEach((row) => {
            const transId = row.getAttribute('data-transaction-id');
            if (!transId) {
                return;
            }

            row.addEventListener('dblclick', async (event) => {
                if (event.target.closest('.delete-btn')) {
                    return;
                }
                await this.openTransactionFormForEdit(transId);
            });

            row.addEventListener('contextmenu', (event) => {
                if (event.target.closest('a')) {
                    return;
                }
                event.preventDefault();
                event.stopPropagation();
                this.showTransactionContextMenu(event.clientX, event.clientY, transId);
            });
        });

        document.querySelectorAll('.transaction-row .delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const holder = e.target.closest('.transaction-row');
                const transId = holder?.getAttribute('data-transaction-id');
                if (!transId) {
                    return;
                }
                const confirmed = await this.showConfirmDialog({
                    title: 'Supprimer une transaction',
                    message: 'Cette transaction sera supprimée.',
                    details: 'Cette action est irréversible.',
                    confirmText: 'Supprimer',
                    confirmClass: 'btn-danger',
                });
                if (confirmed) {
                    this.deleteTransaction(transId);
                }
            });
        });

        document.querySelectorAll('.tree-trans-item').forEach((item) => {
            const transId = item.getAttribute('data-transaction-id');
            if (!transId) return;
            item.addEventListener('dblclick', async (event) => {
                if (event.target.closest('a, button')) {
                    return;
                }
                await this.openTransactionFormForEdit(transId);
            });

            item.addEventListener('contextmenu', (event) => {
                if (event.target.closest('a')) {
                    return;
                }
                event.preventDefault();
                event.stopPropagation();
                this.showTransactionContextMenu(event.clientX, event.clientY, transId);
            });
        });

    },

    ensureTransactionContextMenu() {
        if (this.state.transactionContextMenuInitialized) {
            return;
        }

        let menu = document.getElementById('transaction-context-menu');
        if (!menu) {
            menu = document.createElement('div');
            menu.id = 'transaction-context-menu';
            menu.className = 'transaction-context-menu';
            menu.innerHTML = `
                <button type="button" class="transaction-context-item" data-action="edit">Modifier</button>
                <button type="button" class="transaction-context-item danger" data-action="delete">Supprimer</button>
            `;
            document.body.appendChild(menu);
        }

        menu.addEventListener('click', async (event) => {
            const actionBtn = event.target.closest('[data-action]');
            if (!actionBtn) {
                return;
            }

            const action = actionBtn.getAttribute('data-action');
            const transId = Number(menu.dataset.transactionId || 0);
            this.hideTransactionContextMenu();

            if (!Number.isFinite(transId) || transId <= 0) {
                return;
            }

            if (action === 'edit') {
                await this.openTransactionFormForEdit(transId);
                return;
            }

            if (action === 'delete') {
                const confirmed = await this.showConfirmDialog({
                    title: 'Supprimer une transaction',
                    message: 'Cette transaction sera supprimée.',
                    details: 'Cette action est irréversible.',
                    confirmText: 'Supprimer',
                    confirmClass: 'btn-danger',
                });
                if (confirmed) {
                    await this.deleteTransaction(transId);
                }
            }
        });

        document.addEventListener('click', (event) => {
            if (!event.target.closest('#transaction-context-menu')) {
                this.hideTransactionContextMenu();
            }
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                this.hideTransactionContextMenu();
            }
        });

        window.addEventListener('resize', () => {
            this.hideTransactionContextMenu();
        });

        document.addEventListener('scroll', () => {
            this.hideTransactionContextMenu();
        }, true);

        this.state.transactionContextMenuInitialized = true;
    },

    showTransactionContextMenu(clientX, clientY, transId) {
        const menu = document.getElementById('transaction-context-menu');
        if (!menu) {
            return;
        }

        menu.dataset.transactionId = String(transId || '');
        menu.classList.add('show');

        const menuRect = menu.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const margin = 8;

        let left = clientX;
        let top = clientY;

        if (left + menuRect.width + margin > viewportWidth) {
            left = viewportWidth - menuRect.width - margin;
        }
        if (top + menuRect.height + margin > viewportHeight) {
            top = viewportHeight - menuRect.height - margin;
        }

        menu.style.left = `${Math.max(margin, left)}px`;
        menu.style.top = `${Math.max(margin, top)}px`;
    },

    hideTransactionContextMenu() {
        const menu = document.getElementById('transaction-context-menu');
        if (!menu) {
            return;
        }
        menu.classList.remove('show');
    },

    async openMandatJustificatifsFolder() {
        const mandatId = Number(this.activeMandat?.id || 0);
        if (!Number.isFinite(mandatId) || mandatId <= 0) {
            this.showToast('Aucun mandat actif', 'error');
            return;
        }

        try {
            const response = await fetch(`/api/justificatifs/open-mandat/${mandatId}`, {
                method: 'POST',
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Impossible d\'ouvrir le dossier justificatifs');
            }

            this.showToast('Dossier justificatifs ouvert', 'success');
        } catch (error) {
            this.showToast(error.message || 'Erreur lors de l\'ouverture du dossier', 'error');
        }
    },

    openTransactionFormForCreate() {
        this.state.editingTransactionId = null;
        this.renderCategoryTree();
        this.renderTransactionExistingAttachments([]);
        this.updateTransactionFormUiMode();
        document.getElementById('transaction-form-container').style.display = 'block';
        const dateInput = document.getElementById('trans-date');
        if (dateInput && !dateInput.value) {
            dateInput.value = this.getPreferredTransactionDate();
        }
    },

    openTransactionFormForCreateForNode(nodeId) {
        this.openTransactionFormForCreate();

        const categorySelect = document.getElementById('trans-node-id');
        if (!categorySelect) {
            return;
        }

        const targetValue = String(nodeId || '');
        const hasOption = Array.from(categorySelect.options || []).some((opt) => String(opt.value) === targetValue);
        if (!hasOption) {
            this.showToast('Categorie introuvable', 'error');
            return;
        }

        categorySelect.value = targetValue;
        categorySelect.dispatchEvent(new Event('change'));
    },

    getPreferredTransactionDate() {
        const now = new Date();
        const year = now.getFullYear();
        const mm = String(now.getMonth() + 1).padStart(2, '0');
        const dd = String(now.getDate()).padStart(2, '0');
        return `${year}-${mm}-${dd}`;
    },

    async openTransactionFormForEdit(transId) {
        try {
            const response = await fetch(`/api/transaction/${this.activeMandat.id}/${transId}`);
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Impossible de charger la transaction');
            }

            const trans = await response.json();
            this.state.editingTransactionId = transId;

            this.renderCategoryTree();
            this.updateTransactionFormUiMode();
            document.getElementById('transaction-form-container').style.display = 'block';

            document.getElementById('trans-label').value = trans.label || '';
            document.getElementById('trans-amount').value = trans.amount ?? '';
            document.getElementById('trans-type').value = trans.flow_type || '';
            document.getElementById('trans-date').value = trans.date || '';
            document.getElementById('trans-description').value = trans.description || '';
            document.getElementById('trans-payment').value = trans.payment_method || '';
            document.getElementById('trans-order-number').value = trans.order_number || '';

            const categorySelect = document.getElementById('trans-node-id');
            if (categorySelect && trans.node_id != null) {
                categorySelect.value = String(trans.node_id);
                categorySelect.dispatchEvent(new Event('change'));
            }

            this.renderTransactionExistingAttachments(trans.attachments);
        } catch (error) {
            this.showToast(error.message || 'Erreur lors du chargement', 'error');
        }
    },

    renderTransactionExistingAttachments(attachments) {
        const container = document.getElementById('trans-existing-attachments');
        if (!container) {
            return;
        }

        const items = Array.isArray(attachments) ? attachments : [];
        if (items.length === 0) {
            container.innerHTML = '<span class="transaction-empty">Aucun justificatif existant</span>';
            return;
        }

        container.innerHTML = items.map((att, index) => {
            const path = String(att.file_path || '').trim();
            const fileName = path.split('/').pop() || `Justificatif ${index + 1}`;
            return `<a href="/justificatifs/${encodeURI(path)}" target="_blank" rel="noopener noreferrer">${this.escapeHtml(fileName)}</a>`;
        }).join('');
    },

    closeAndResetTransactionForm() {
        document.getElementById('transaction-form-container').style.display = 'none';
        document.getElementById('transaction-form').reset();
        this.state.editingTransactionId = null;
        this.updateTransactionFormUiMode();

        const preview = document.getElementById('trans-category-preview');
        if (preview) {
            preview.textContent = 'Aucune catégorie sélectionnée';
        }

        this.renderTransactionExistingAttachments([]);
    },

    updateTransactionFormUiMode() {
        const title = document.getElementById('transaction-form-title');
        const submitBtn = document.querySelector('#transaction-form .form-actions button[type="submit"]');
        if (!title || !submitBtn) {
            return;
        }

        if (this.state.editingTransactionId) {
            title.textContent = 'Modifier la Transaction';
            submitBtn.textContent = 'Mettre à jour';
            return;
        }

        title.textContent = 'Nouvelle Transaction';
        submitBtn.textContent = 'Enregistrer';
    },

    async createTransaction() {
        try {
            const paymentMethod = String(document.getElementById('trans-payment').value || '').trim();
            const orderNumber = String(document.getElementById('trans-order-number').value || '').trim();
            if (!paymentMethod || !orderNumber) {
                this.showToast('Le moyen de paiement et l ordre sont obligatoires', 'error');
                return;
            }

            const data = {
                mandat_id: this.activeMandat.id,
                node_id: document.getElementById('trans-node-id').value,
                label: document.getElementById('trans-label').value,
                amount: parseFloat(document.getElementById('trans-amount').value),
                flow_type: document.getElementById('trans-type').value,
                date: document.getElementById('trans-date').value,
                description: document.getElementById('trans-description').value,
                payment_method: paymentMethod,
                order_number: orderNumber,
            };

            const response = await fetch('/api/transaction', {
                method: 'POST',
                body: (() => {
                    const formData = new FormData();
                    Object.entries(data).forEach(([key, value]) => {
                        formData.append(key, value ?? '');
                    });

                    const attachmentsInput = document.getElementById('trans-attachments');
                    if (attachmentsInput && attachmentsInput.files) {
                        Array.from(attachmentsInput.files).forEach((file) => {
                            formData.append('attachments', file);
                        });
                    }

                    return formData;
                })(),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Erreur');
            }

            this.showToast('Transaction créée avec succès', 'success');
            this.closeAndResetTransactionForm();
            await this.loadTransactions();
            await this.loadDashboard();
        } catch (error) {
            this.showToast(error.message || 'Erreur lors de la création', 'error');
        }
    },

    async updateTransaction(transId) {
        try {
            const paymentMethod = String(document.getElementById('trans-payment').value || '').trim();
            const orderNumber = String(document.getElementById('trans-order-number').value || '').trim();
            if (!paymentMethod || !orderNumber) {
                this.showToast('Le moyen de paiement et l ordre sont obligatoires', 'error');
                return;
            }

            const nodeIdValue = document.getElementById('trans-node-id').value;
            const payload = {
                node_id: nodeIdValue ? parseInt(nodeIdValue, 10) : null,
                label: document.getElementById('trans-label').value,
                amount: parseFloat(document.getElementById('trans-amount').value),
                flow_type: document.getElementById('trans-type').value,
                date: document.getElementById('trans-date').value,
                description: document.getElementById('trans-description').value,
                payment_method: paymentMethod,
                order_number: orderNumber,
            };

            const response = await fetch(`/api/transaction/${this.activeMandat.id}/${transId}`, {
                method: 'PUT',
                body: (() => {
                    const formData = new FormData();
                    Object.entries(payload).forEach(([key, value]) => {
                        formData.append(key, value ?? '');
                    });

                    const attachmentsInput = document.getElementById('trans-attachments');
                    if (attachmentsInput && attachmentsInput.files) {
                        Array.from(attachmentsInput.files).forEach((file) => {
                            formData.append('attachments', file);
                        });
                    }

                    return formData;
                })(),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Erreur lors de la mise à jour');
            }

            this.showToast('Transaction mise à jour', 'success');
            this.closeAndResetTransactionForm();
            await this.loadTransactions();
            await this.loadDashboard();
        } catch (error) {
            this.showToast(error.message || 'Erreur lors de la mise à jour', 'error');
        }
    },

    async deleteTransaction(transId) {
        try {
            const response = await fetch(`/api/transaction/${this.activeMandat.id}/${transId}`, {
                method: 'DELETE',
            });

            if (!response.ok) throw new Error('Erreur');

            this.showToast('Transaction supprimée', 'success');
            await this.loadTransactions();
            await this.loadDashboard();
        } catch (error) {
            this.showToast(error.message || 'Erreur', 'error');
        }
    },

    // ===== STRUCTURE =====

    async loadStructure() {
        try {
            const response = await fetch(`/api/structure/${this.activeMandat.id}`);
            const data = await response.json();
            this.structure = data.structure || [];
        } catch (error) {
            console.error('Structure error:', error);
        }
    },

    renderStructure() {
        const container = document.getElementById('structure-tree');
        if (!container) return;

        container.innerHTML = '';

        const renderNode = (node, depth = 0) => {
            const hasChildren = Array.isArray(node.children) && node.children.length > 0;
            const nodeEl = document.createElement('div');
            nodeEl.className = `tree-node ${depth === 0 ? 'root-node' : ''}`.trim();
            nodeEl.setAttribute('data-node-id', node.id);
            if (depth === 0 && node.pole_color) {
                nodeEl.style.cssText = this.buildPoleStyleVariables(node.pole_color);
            }

            const icon = depth === 0 ? '📍' : depth === 1 ? '📂' : '📄';

            const content = document.createElement('div');
            content.className = 'tree-node-content';
            content.style.paddingLeft = `${8 + depth * 18}px`;

            const toggle = document.createElement('button');
            toggle.className = 'expand-toggle';
            toggle.textContent = '▶';
            toggle.style.visibility = hasChildren ? 'visible' : 'hidden';

            const iconEl = document.createElement('span');
            iconEl.className = 'node-icon';
            iconEl.textContent = icon;

            const label = document.createElement('span');
            label.className = 'node-label';
            label.textContent = node.name;

            const actions = document.createElement('div');
            actions.className = 'node-actions';
            actions.innerHTML = `
                <button class="btn-action add-child-btn" title="Ajouter">➕</button>
                <button class="btn-action delete-node-btn" title="Supprimer">🗑️</button>
            `;

            content.appendChild(toggle);
            content.appendChild(iconEl);
            content.appendChild(label);
            content.appendChild(actions);

            const childrenContainer = document.createElement('div');
            childrenContainer.className = 'tree-children';
            childrenContainer.style.display = 'none';

            nodeEl.appendChild(content);
            nodeEl.appendChild(childrenContainer);

            if (hasChildren) {
                toggle.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const isOpen = childrenContainer.style.display !== 'none';
                    childrenContainer.style.display = isOpen ? 'none' : 'block';
                    toggle.classList.toggle('open', !isOpen);
                });

                content.addEventListener('click', (e) => {
                    if (e.target.closest('.expand-toggle') || e.target.closest('.node-actions')) {
                        return;
                    }
                    const isOpen = childrenContainer.style.display !== 'none';
                    childrenContainer.style.display = isOpen ? 'none' : 'block';
                    toggle.classList.toggle('open', !isOpen);
                });

                node.children.forEach((child) => {
                    childrenContainer.appendChild(renderNode(child, depth + 1));
                });
            }

            content.querySelector('.add-child-btn')?.addEventListener('click', () => {
                this.showAddCategoryModal(node.id);
            });

            content.querySelector('.delete-node-btn')?.addEventListener('click', () => {
                this.showConfirmDialog({
                    title: 'Supprimer une catégorie',
                    message: `Supprimer "${node.name}" et tous ses enfants ?`,
                    details: 'Les transactions associées seront masquées.',
                    confirmText: 'Supprimer',
                    confirmClass: 'btn-danger',
                }).then((confirmed) => {
                    if (confirmed) {
                        this.deleteNode(node.id);
                    }
                });
            });

            return nodeEl;
        };

        this.structure.forEach((node) => container.appendChild(renderNode(node)));

        const expandAllBtn = document.getElementById('structure-expand-all');
        const collapseAllBtn = document.getElementById('structure-collapse-all');
        if (expandAllBtn) {
            expandAllBtn.onclick = () => this.setAllExpanded('structure-tree', true);
        }
        if (collapseAllBtn) {
            collapseAllBtn.onclick = () => this.setAllExpanded('structure-tree', false);
        }
    },

    renderCategoryTree() {
        const container = document.getElementById('trans-category-tree');
        if (!container) return;

        container.innerHTML = '';

        const select = document.createElement('select');
        select.id = 'trans-node-id';
        select.required = true;
        select.innerHTML = '<option value="">-- Sélectionner une catégorie --</option>';

        const preview = document.getElementById('trans-category-preview');
        if (preview) {
            preview.textContent = 'Aucune catégorie sélectionnée';
        }

        const flatten = (nodes, ancestors = []) => {
            const items = [];
            nodes.forEach((node) => {
                const path = [...ancestors, node.name];
                const children = Array.isArray(node.children) ? node.children : [];
                if (children.length === 0) {
                    items.push({
                        id: node.id,
                        pole: ancestors.length === 0 ? node.name : ancestors[0],
                        label: path.join(' > '),
                    });
                } else {
                    items.push(...flatten(node.children, path));
                }
            });

            return items;
        };

        const grouped = new Map();
        flatten(this.structure).forEach((item) => {
            if (!grouped.has(item.pole)) {
                grouped.set(item.pole, []);
            }
            grouped.get(item.pole).push(item);
        });

        grouped.forEach((items, poleName) => {
            const optgroup = document.createElement('optgroup');
            optgroup.label = poleName;

            items.forEach((item) => {
                const option = document.createElement('option');
                option.value = item.id;
                option.textContent = item.label;
                optgroup.appendChild(option);
            });

            select.appendChild(optgroup);
        });

        if (grouped.size === 0) {
            select.innerHTML = '<option value="">Aucun dernier niveau disponible</option>';
        }

        select.addEventListener('change', () => {
            if (preview) {
                preview.textContent = select.selectedOptions[0]?.textContent || 'Aucune catégorie sélectionnée';
            }
        });

        container.appendChild(select);
    },

    showAddCategoryModal(parentId, parentName = null) {
        document.getElementById('cat-parent-id').value = parentId || '';
        document.getElementById('cat-name').value = '';
        const parentDisplay = document.getElementById('cat-parent-display');
        if (parentDisplay) {
            parentDisplay.textContent = parentId ? (parentName || `Node #${parentId}`) : 'Racine (Pôle)';
        }
        document.getElementById('category-modal').style.display = 'block';

        document.getElementById('category-form').onsubmit = (e) => {
            e.preventDefault();
            this.addCategory();
        };
    },

    async addCategory() {
        try {
            const data = {
                mandat_id: this.activeMandat.id,
                parent_id: document.getElementById('cat-parent-id').value || null,
                name: document.getElementById('cat-name').value,
            };

            const response = await fetch('/api/node', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });

            if (!response.ok) throw new Error('Erreur');

            this.showToast('Catégorie créée', 'success');
            document.getElementById('category-modal').style.display = 'none';
            await this.loadStructure();
            await this.loadDashboard();
        } catch (error) {
            this.showToast(error.message, 'error');
        }
    },

    async deleteNode(nodeId) {
        try {
            const response = await fetch(`/api/node/${this.activeMandat.id}/${nodeId}`, {
                method: 'DELETE',
            });

            if (!response.ok) throw new Error('Erreur');

            this.showToast('Catégorie supprimée', 'success');
            await this.loadStructure();
            await this.loadDashboard();
        } catch (error) {
            this.showToast(error.message, 'error');
        }
    },

    startInlineBudgetEdit(button, nodeId, currentBudget, flowType) {
        if (!button || button.dataset.editing === '1') {
            return;
        }

        button.dataset.editing = '1';

        const input = document.createElement('input');
        input.type = 'number';
        input.step = '0.01';
        input.min = '0';
        input.className = 'budget-edit-input';
        input.value = String(currentBudget || 0);

        button.style.display = 'none';
        button.insertAdjacentElement('afterend', input);
        input.focus();
        input.select();

        let submitting = false;

        const cleanup = () => {
            input.remove();
            button.style.display = '';
            delete button.dataset.editing;
        };

        const submit = async () => {
            if (submitting) return;

            const amount = Number(String(input.value).replace(',', '.'));
            if (Number.isNaN(amount) || amount < 0) {
                this.showToast('Montant invalide', 'error');
                input.focus();
                return;
            }

            submitting = true;
            input.disabled = true;

            try {
                await this.editBudgetPlan(nodeId, amount, flowType || 'expense');
            } catch {
                submitting = false;
                input.disabled = false;
                input.focus();
            }
        };

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                submit();
            }
            if (e.key === 'Escape') {
                e.preventDefault();
                cleanup();
            }
        });

        input.addEventListener('blur', () => {
            if (!submitting) {
                submit();
            }
        });
    },

    async editBudgetPlan(nodeId, amount, flowType = 'expense') {
        const year = this.getDashboardYear();

        try {
            const response = await fetch('/api/budget-plan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    mandat_id: this.activeMandat.id,
                    node_id: nodeId,
                    year,
                    flow_type: flowType,
                    amount,
                }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Erreur lors de la sauvegarde');
            }

            this.showToast('Budget prévisionnel mis à jour', 'success');
            await this.loadDashboard();
        } catch (error) {
            this.showToast(error.message || 'Erreur', 'error');
            throw error;
        }
    },

    async clearPrevisionnel() {
        if (!this.activeMandat) {
            this.showToast('Aucun mandat actif', 'error');
            return;
        }

        const year = this.getDashboardYear();
        const confirmed = await this.showConfirmDialog({
            title: 'Clear prévisionnel',
            message: `Confirmer la suppression de tout le prévisionnel ${year} ?`,
            details: 'Cette action est irréversible.',
            confirmText: 'Tout supprimer',
            confirmClass: 'btn-danger',
        });
        if (!confirmed) return;

        try {
            const response = await fetch('/api/budget-plan/clear', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    mandat_id: this.activeMandat.id,
                    year,
                }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Erreur lors du clear prévisionnel');
            }

            const result = await response.json();
            this.showToast(`Prévisionnel effacé (${result.deleted || 0} lignes)`, 'success');
            await this.loadDashboard();
        } catch (error) {
            this.showToast(error.message || 'Erreur', 'error');
        }
    },

    setAllExpanded(containerId, expanded) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.querySelectorAll('.node-children, .tree-children').forEach((el) => {
            el.style.display = expanded ? 'block' : 'none';
        });

        container.querySelectorAll('.expand-btn, .expand-toggle').forEach((btn) => {
            btn.classList.toggle('open', expanded);
        });

        if (containerId === 'dashboard-content') {
            this.captureDashboardExpandedState();
        }
    },

    captureDashboardExpandedState() {
        const container = document.getElementById('dashboard-content');
        if (!container) return;

        const expandedIds = [];
        container.querySelectorAll('.budget-node[data-node-id]').forEach((nodeEl) => {
            const children = nodeEl.querySelector(':scope > .node-children');
            if (children && children.style.display !== 'none') {
                const id = nodeEl.getAttribute('data-node-id');
                if (id) {
                    expandedIds.push(id);
                }
            }
        });

        this.state.dashboardExpandedIds = expandedIds;
    },

    restoreDashboardExpandedState() {
        const container = document.getElementById('dashboard-content');
        if (!container || !Array.isArray(this.state.dashboardExpandedIds)) return;

        const wanted = new Set(this.state.dashboardExpandedIds.map(String));
        container.querySelectorAll('.budget-node[data-node-id]').forEach((nodeEl) => {
            const id = nodeEl.getAttribute('data-node-id');
            if (!id || !wanted.has(String(id))) return;

            const children = nodeEl.querySelector(':scope > .node-children');
            const btn = nodeEl.querySelector(':scope > .node-header .expand-btn');
            if (children) {
                children.style.display = 'block';
            }
            if (btn) {
                btn.classList.add('open');
            }
        });
    },

    computeAdvancement(node) {
        const budgetTotal = Number(node?.budgeted_total || 0);
        const actualTotal = Number(node?.actual_total || 0);

        let ratio = 0;
        if (budgetTotal !== 0) {
            ratio = Math.abs(actualTotal) / Math.abs(budgetTotal);
        }

        const percent = ratio * 100;
        let levelClass = 'progress-low';
        if (percent >= 100) {
            levelClass = 'progress-over';
        } else if (percent >= 70) {
            levelClass = 'progress-ok';
        }

        return {
            percent,
            percentText: `${percent.toFixed(1)}%`,
            barWidth: Math.max(0, Math.min(percent, 100)),
            levelClass,
        };
    },

    normalizeLabel(value) {
        return String(value || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase();
    },

    getPoleThemeKey(poleName) {
        const normalized = this.normalizeLabel(poleName);
        if (normalized.includes('pilot')) return 'pilot';
        if (normalized.includes('event')) return 'event';
        if (normalized.includes('com')) return 'com';
        if (normalized.includes('art')) return 'art';
        if (normalized.includes('huma')) return 'huma';
        if (normalized.includes('ddrs')) return 'ddrs';
        if (normalized.includes('lignes')) return 'lignes';
        if (normalized.includes('sport')) return 'sport';
        if (normalized.includes('kfet')) return 'kfet';
        return 'default';
    },

    getPoleThemeClass(poleName, prefix = 'pole-theme') {
        return `${prefix}-${this.getPoleThemeKey(poleName)}`;
    },

    // ===== UTILITIES =====

    formatCurrency(amount) {
        return new Intl.NumberFormat('fr-FR', {
            style: 'currency',
            currency: 'EUR',
        }).format(amount);
    },

    formatDate(dateStr) {
        try {
            if (!dateStr) {
                return 'Date inconnue';
            }
            const parsed = new Date(dateStr);
            if (Number.isNaN(parsed.getTime())) {
                return 'Date inconnue';
            }
            return parsed.toLocaleDateString('fr-FR');
        } catch {
            return 'Date inconnue';
        }
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = `toast show ${type}`;
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3200);
    },

    showConfirmDialog({
        title = 'Confirmation',
        message = 'Confirmer cette action ?',
        details = '',
        confirmText = 'Confirmer',
        cancelText = 'Annuler',
        confirmClass = 'btn-primary',
    } = {}) {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'modal confirm-modal';
            modal.innerHTML = `
                <div class="modal-content confirm-modal-content" role="dialog" aria-modal="true" aria-label="${this.escapeHtml(title)}">
                    <h3>${this.escapeHtml(title)}</h3>
                    <p class="confirm-message">${this.escapeHtml(message)}</p>
                    ${details ? `<p class="confirm-details">${this.escapeHtml(details)}</p>` : ''}
                    <div class="form-actions">
                        <button type="button" class="btn btn-secondary confirm-cancel">${this.escapeHtml(cancelText)}</button>
                        <button type="button" class="btn ${this.escapeHtml(confirmClass)} confirm-accept">${this.escapeHtml(confirmText)}</button>
                    </div>
                </div>
            `;

            const close = (value) => {
                modal.remove();
                resolve(value);
            };

            modal.addEventListener('click', (event) => {
                if (event.target === modal) {
                    close(false);
                }
            });

            modal.querySelector('.confirm-cancel')?.addEventListener('click', () => close(false));
            modal.querySelector('.confirm-accept')?.addEventListener('click', () => close(true));

            document.body.appendChild(modal);
        });
    },
};
