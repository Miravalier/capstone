import {login, register, apiRequest} from "./modules/api.js";
import {Budget, Category, Expense} from "./modules/datatypes.js";

window.Budget = Budget;
window.Category = Category;
window.Expense = Expense;
window.login = login;
window.register = register;
window.apiRequest = apiRequest;