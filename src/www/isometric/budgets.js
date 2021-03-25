import { apiRequest, login, register } from "./modules/api.js";
import { errorToast } from "./modules/ui.js";

async function updateBudgets() {
    const response = await apiRequest("/budget/list");
    if (response.error)
    {
        errorToast("A network error has occured. Reconnecting . . .");
        return;
    }

    $("#budgets").html("");
    for (const budget of response.budgets)
    {
        $("#budgets").appendChild($("<p class=\"budget\">Test</p>"));
        console.log(budget);
    }
    if (response.budgets.length == 0)
    {
        $("#budgets").appendChild($("<p class=\"info\">No budgets found.</p>"));
    }
}

$(async () => {
    updateBudgets();
});