import {login, register, apiRequest} from "./modules/api.js";
import {Budget, Category, Expense} from "./modules/datatypes.js";

window.Budget = Budget;
window.Category = Category;
window.Expense = Expense;
window.login = login;
window.register = register;
window.apiRequest = apiRequest;

const hexCharacters = "0123456789abcdef";


function randomChoice(iterable) {
    return iterable[Math.floor(Math.random() * iterable.length)];
}


function hexToken(amount) {
    if (!amount) amount = 8;
    let result = "";
    for (i=0; i < amount; i++)
    {
        result += randomChoice(hexCharacters);
    }

    return result;
}