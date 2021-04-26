import {apiRequest} from "./api.js";


export const PERM_NONE = 0;
export const PERM_VIEW = 1;
export const PERM_UPDATE = 2;
export const PERM_ADMIN = 4;
export const PERM_OWNER = 8;


export class Budget {
    constructor(id, ticker_symbol, previous_id, next_id, name, permissions)
    {
        this.id = id;
        this.ticker_symbol = ticker_symbol;
        this.previous_id = previous_id;
        this.next_id = next_id;
        this._name = name;
        this._permissions = permissions;
        this._categories = null;
    }

    async child() {
        if (this.next_id) {
            return await Budget.from_id(this.next_id);
        }
        else {
            return null;
        }
    }

    async parent() {
        if (this.previous_id) {
            return await Budget.from_id(this.previous_id);
        }
        else {
            return null;
        }
    }

    get name() {
        return this._name;
    }

    async update(name, ticker_symbol) {
        if (!ticker_symbol)
        {
            ticker_symbol = null;
        }
        const response = await apiRequest(
            "/budget/update",
            {
                budget_id: this.id,
                budget_name: name,
                ticker_symbol: ticker_symbol
            }
        );
        if (response.error) {
            throw response.error;
        }
        this._name = name;
        this.ticker_symbol = ticker_symbol;
    }

    get permissions() {
        return this._permissions;
    }

    get role() {
        switch (this.permissions) {
            case PERM_NONE: return "None";
            case PERM_VIEW: return "View-Only";
            case PERM_UPDATE: return "User";
            case PERM_ADMIN: return "Admin";
            case PERM_OWNER: return "Owner";
            default: return "Level " + this.permissions;
        }
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
            response.ticker_symbol,
            response.previous_id,
            response.next_id,
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
                budgetData.id,
                budgetData.ticker_symbol,
                budgetData.previous_id,
                budgetData.next_id,
                budgetData.name,
                budgetData.permissions
            );
            budgets.push(budget);
        });
        return budgets;
    }

    async createChildBudget(name) {
        const response = await apiRequest(
            "/budget/create",
            {budget_name: name, previous_budget_id: this.id}
        );
        if (response.error) {
            throw response.error;
        }

        //constructor(id, ticker_symbol, previous_id, next_id, name, permissions)
        const childBudget = new Budget(response.id, null, this.id, null, name, PERM_OWNER);

        for (const category of await this.categories())
        {
            await childBudget.addCategory(category.name);
        }

        console.log(`Updating with name "${childBudget.name}" and symbol "${this.ticker_symbol}"`);
        await childBudget.update(childBudget.name, this.ticker_symbol);
        return childBudget;
    }

    static async create(name) {
        const response = await apiRequest(
            "/budget/create",
            {budget_name: name}
        );
        if (response.error) {
            throw response.error;
        }

        return new Budget(response.id, null, null, name, PERM_OWNER);
    }

    async addCategory(name) {
        const response = await apiRequest(
            "/category/create",
            {budget_id: this.id, category_name: name}
        );
        if (response.error) {
            throw response.error;
        }

        const category = new Category(response.id, this.id, name);
        category._budget = this;
        if (this._categories !== null) {
            this._categories.push(category);
        }
        return category;
    }

    async delete() {
        const response = await apiRequest(
            "/budget/delete",
            {
                budget_id: this.id
            }
        );
        if (response.error) {
            throw response.error;
        }
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
        const response = await apiRequest(
            "/category/update",
            {
                budget_id: this.budget_id,
                category_id: this.id,
                category_name: name
            }
        );
        if (response.error) {
            throw response.error;
        }
    }

    async budget() {
        if (!this._budget) {
            this._budget = await Budget.from_id(this.budget_id);
        }
        return this._budget;
    }

    async total() {
        let result = 0;
        const expenses = await this.expenses();
        for (const expense of expenses) {
            result += expense.value;
        }
        return result;
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

    async addExpense(description, amount, date) {
        const response = await apiRequest(
            "/expense/create",
            {
                budget_id: this.budget_id,
                category_id: this.id,
                description: description,
                expense_amount: amount,
                expense_date: date
            }
        );
        if (response.error) {
            throw response.error;
        }

        const expense = new Expense(
            response.id, this.id, this.budget_id,
            description, amount, date
        );
        expense._category = this;
        expense._budget = this._budget;
        if (this._expenses !== null) {
            this._expenses.push(expense);
        }
        return expense;
    }

    async delete() {
        // Get budget
        const budget = await this.budget();
        // Remove category from budget's categories list
        if (budget._categories !== null) {
            const index = budget._categories.indexOf(this)
            if (index != -1) {
                budget._categories.splice(index, 1);
            }
        }
        // Submit api request
        const response = await apiRequest(
            "/category/delete",
            {
                budget_id: this.budget_id,
                category_id: this.id
            }
        );
        if (response.error) {
            throw response.error;
        }
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

    get value() {
        return Number(this._amount.substring(1).replaceAll(',', ''));
    }

    get date() {
        return this._date;
    }

    async update(description, amount, date) {
        const response = await apiRequest(
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
        
        if (response.error) {
            throw response.error;
        }
        this._description = response.description;
        this._amount = response.amount;
        this._date = response.date;
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

    async delete() {
        // Get category
        const category = await this.category();
        // Remove expense from category's expenses list
        if (category._expenses !== null) {
            const index = category._expenses.indexOf(this)
            if (index != -1) {
                category._expenses.splice(index, 1);
            }
        }
        // Submit api request
        const response = await apiRequest(
            "/expense/delete",
            {
                budget_id: this.budget_id,
                category_id: this.category_id,
                expense_id: this.id
            }
        );
        if (response.error) {
            throw response.error;
        }
    }
}
