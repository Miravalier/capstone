export class Budget {
    constructor(id, name, permissions) {
        this.id = id;
        this._name = name;
        this._permissions = permissions;
        this._categories = null;
    }

    get name() {
        return this._name;
    }

    async update(name) {
        this._name = name;
        await apiRequest(
            "/budget/update",
            {
                budget_id: this.id,
                budget_name: name
            }
        );
    }

    get permissions() {
        return this._permissions;
    }

    async categories() {
        if (!this._categories) {
            this._categories = await Category.list(this.id);
            this._categories.forEach(category => {
                category._budget = this;
            });
        }
        return this._categories;
    }

    static async from_id(budget_id) {
        const response = await apiRequest("/budget/info", {
            budget_id
        });
        if (response.error) {
            throw response.error;
        }
        return new Budget(
            budget_id,
            response.name,
            response.permissions
        );
    }

    static async list() {
        const response = await apiRequest("/budget/list");
        if (response.error) {
            throw response.error;
        }
        const budgets = [];
        response.budgets.forEach(budgetData => {
            const budget = new Budget(
                budgetData.id, budgetData.name, budgetData.permissions
            );
            budgets.push(budget);
        });
        return budgets;
    }
}


export class Category {
    constructor(id, budget_id, name) {
        this.id = id;
        this.budget_id = budget_id;
        this._name = name;
        this._budget = null;
        this._expenses = null;
    }

    get name() {
        return this._name;
    }

    async update(name) {
        this._name = name;
        await apiRequest(
            "/category/update",
            {
                budget_id: this.budget_id,
                category_id: this.id,
                category_name: name
            }
        );
    }

    async budget() {
        if (!this._budget) {
            this._budget = await Budget.from_id(this.budget_id);
        }
        return this._budget;
    }

    async expenses() {
        if (!this._expenses) {
            this._expenses = await Expense.list(this.budget_id, this.id);
            this._expenses.forEach(expense => {
                expense._category = this;
                expense._budget = this._budget;
            });
        }
        return this._expenses;
    }

    static async from_id(budget_id, category_id) {
        const response = await apiRequest("/category/info", {
            budget_id, category_id
        });
        if (response.error) {
            throw response.error;
        }
        return new Category(
            category_id,
            budget_id,
            response.name
        );
    }

    static async list(budget_id) {
        const response = await apiRequest("/category/list", {budget_id});
        if (response.error) {
            throw response.error;
        }
        const categories = [];
        response.categories.forEach(category => {
            categories.push(new Category(
                category.id, budget_id, category.name
            ));
        });
        return categories;
    }
}


export class Expense {
    constructor(id, category_id, budget_id, description, amount, date) {
        this.id = id;
        this.category_id = category_id;
        this.budget_id = budget_id;
        this._description = description;
        this._amount = amount;
        this._date = date;
        this._category = null;
        this._budget = null;
    }

    get description() {
        return this._description;
    }

    get amount() {
        return this._amount;
    }

    get date() {
        return this._date;
    }

    async update(description, amount, date) {
        this._description = description;
        this._amount = amount;
        this._date = date;
        await apiRequest(
            "/expense/update",
            {
                budget_id: this.budget_id,
                category_id: this.category_id,
                expense_id: this.id,
                description: description,
                expense_amount: amount,
                expense_date: date
            }
        );
    }

    async category() {
        if (!this._category) {
            this._category = await Category.from_id(
                this.budget_id, this.category_id
            );
        }
        return this._category;
    }

    async budget() {
        if (!this._budget) {
            this._budget = await Budget.from_id(this.budget_id);
        }
        return this._budget;
    }

    static async from_id(budget_id, category_id, expense_id) {
        const response = await apiRequest("/expense/info", {
            budget_id, category_id, expense_id
        });
        if (response.error) {
            throw response.error;
        }
        return new Expense(
            expense_id,
            category_id,
            budget_id,
            response.description,
            response.amount,
            response.date
        );
    }

    static async list(budget_id, category_id) {
        const response = await apiRequest(
            "/expense/list", {budget_id, category_id}
        );
        if (response.error) {
            throw response.error;
        }
        const expenses = [];
        response.expenses.forEach(expense => {
            expenses.push(new Expense(
                expense.id, category_id, budget_id,
                expense.description, expense.amount, expense.date
            ));
        });
        return expenses;
    }
}