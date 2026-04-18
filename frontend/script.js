const UI = {
    toast: document.getElementById('toast'),
    pageTitle: document.getElementById('page-title'),
    navBtns: document.querySelectorAll('.nav-btn'),
    sections: document.querySelectorAll('.view-section'),
    
    // Setup Navigation
    initNav() {
        this.navBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                this.navBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                const target = btn.getAttribute('data-target');
                this.pageTitle.textContent = btn.textContent;
                
                this.sections.forEach(sec => {
                    sec.classList.remove('active');
                    sec.classList.add('hidden');
                });
                
                document.getElementById(target).classList.remove('hidden');
                document.getElementById(target).classList.add('active');
                
                // Refresh data based on view
                API.refreshTarget(target);
            });
        });
    },

    showToast(msg, isError = false) {
        this.toast.textContent = msg;
        this.toast.className = `toast ${isError ? 'error' : 'success'}`;
        setTimeout(() => {
            this.toast.classList.add('hidden');
        }, 3000);
    }
};

const API = {
    async fetchMaterials() {
        const res = await fetch('/api/materials');
        return res.json();
    },
    
    async fetchOrders() {
        const res = await fetch('/api/orders');
        return res.json();
    },

    async fetchBom(productId) {
        if(!productId) return [];
        const res = await fetch(`/api/bom/${productId}`);
        return res.json();
    },

    async createMaterial(data) {
        const res = await fetch('/api/materials', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        return res;
    },

    async createOrder(data) {
        const res = await fetch('/api/orders', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        return res;
    },

    async startOrder(orderId) {
        return fetch('/api/production/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({order_id: orderId})
        });
    },

    async completeOrder(orderId) {
        return fetch('/api/production/complete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({order_id: orderId})
        });
    },

    refreshTarget(target) {
        if(target === 'dashboard') Render.dashboard();
        if(target === 'materials') Render.materials();
        if(target === 'bom') Render.bom();
        if(target === 'orders') Render.orders();
    }
};

const Render = {
    async dashboard() {
        const materials = await API.fetchMaterials();
        const orders = await API.fetchOrders();
        
        document.getElementById('stat-total-materials').textContent = materials.length;
        document.getElementById('stat-active-orders').textContent = orders.filter(o => o.status !== 'COMPLETED').length;
        document.getElementById('stat-finished-stock').textContent = materials.filter(m => m.type === 'FINISHED').reduce((acc, m) => acc + m.stock, 0);

        const tbody = document.querySelector('#dashboard-inventory-table tbody');
        tbody.innerHTML = materials.map(m => `
            <tr>
                <td>${m.id}</td>
                <td>${m.name}</td>
                <td><span class="badge" style="background: ${m.type === 'FINISHED' ? '#3b82f6' : '#64748b'}">${m.type}</span></td>
                <td>${m.stock}</td>
            </tr>
        `).join('');
    },

    async materials() {
        const materials = await API.fetchMaterials();
        const tbody = document.querySelector('#materials-table tbody');
        tbody.innerHTML = materials.map(m => `
            <tr>
                <td>${m.id}</td>
                <td>${m.name}</td>
                <td>${m.type}</td>
                <td>$${m.cost.toFixed(2)}</td>
                <td>${m.stock}</td>
            </tr>
        `).join('');
    },

    async bom() {
        const materials = await API.fetchMaterials();
        const finished = materials.filter(m => m.type === 'FINISHED');
        const select = document.getElementById('bom-product-filter');
        
        if (select.children.length === 0) {
            select.innerHTML = finished.map(m => `<option value="${m.id}">${m.name}</option>`).join('');
            select.addEventListener('change', () => this.bom());
        }

        const selectedId = select.value;
        const boms = await API.fetchBom(selectedId);
        const tbody = document.getElementById('bom-table-body');
        
        if(boms.length === 0) {
            tbody.innerHTML = `<tr><td colspan="3">No BOM found for this product.</td></tr>`;
        } else {
            tbody.innerHTML = boms.map(b => `
                <tr>
                    <td>${b.name}</td>
                    <td>${b.quantity}</td>
                    <td>$${b.cost.toFixed(2)}</td>
                </tr>
            `).join('');
        }
    },

    async orders() {
        const materials = await API.fetchMaterials();
        const finished = materials.filter(m => m.type === 'FINISHED');
        const select = document.getElementById('order-product');
        select.innerHTML = finished.map(m => `<option value="${m.id}">${m.name}</option>`).join('');

        const orders = await API.fetchOrders();
        const tbody = document.querySelector('#orders-table tbody');
        
        tbody.innerHTML = orders.map(o => {
            let actions = '';
            if (o.status === 'CREATED') {
                actions = `<button class="btn-small btn-start" onclick="Events.handleStart(${o.id})">Start Production</button>`;
            } else if (o.status === 'IN_PROGRESS') {
                actions = `<button class="btn-small btn-complete" onclick="Events.handleComplete(${o.id})">Complete</button>`;
            } else {
                actions = `<span style="color:var(--success)">Done</span>`;
            }

            return `
            <tr>
                <td>${o.id}</td>
                <td>${o.name}</td>
                <td>${o.quantity}</td>
                <td>$${o.total_cost.toFixed(2)}</td>
                <td><span class="badge" style="background: ${o.status === 'COMPLETED' ? 'var(--success)' : (o.status === 'IN_PROGRESS' ? 'var(--warning)' : '#64748b')}">${o.status.replace('_', ' ')}</span></td>
                <td>${actions}</td>
            </tr>
        `}).reverse().join('');
    }
};

const Events = {
    init() {
        document.getElementById('material-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                name: document.getElementById('mat-name').value,
                type: document.getElementById('mat-type').value,
                cost: parseFloat(document.getElementById('mat-cost').value),
                stock: parseInt(document.getElementById('mat-stock').value),
            };
            const res = await API.createMaterial(payload);
            if(res.ok) {
                UI.showToast("Material added successfully");
                e.target.reset();
                Render.materials();
            }
        });

        document.getElementById('order-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                product_id: document.getElementById('order-product').value,
                quantity: parseInt(document.getElementById('order-qty').value),
            };
            const res = await API.createOrder(payload);
            const data = await res.json();
            
            if(res.ok) {
                UI.showToast("Order generated successfully!");
                Render.orders();
            } else {
                UI.showToast(data.error + ": " + data.details, true);
            }
        });
    },

    async handleStart(orderId) {
        const res = await API.startOrder(orderId);
        if(res.ok) {
            UI.showToast("Production started, components deducted.");
            Render.orders();
        } else {
            const data = await res.json();
            UI.showToast(data.error || "Failed to start", true);
        }
    },

    async handleComplete(orderId) {
        const res = await API.completeOrder(orderId);
        if(res.ok) {
            UI.showToast("Production complete, yield received.");
            Render.orders();
        }
    }
}

// Init App
document.addEventListener('DOMContentLoaded', () => {
    UI.initNav();
    Events.init();
    Render.dashboard();
});
