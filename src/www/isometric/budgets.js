import { apiRequest } from "./modules/api.js";
import { errorToast } from "./modules/ui.js";
import { hexToken } from "./modules/util.js";


async function updateBudgets() {
    const response = await apiRequest("/budget/list");
    if (response.error)
    {
        errorToast("A network error has occured. Reconnecting . . .");
        return;
    }

    $(".budget-list").html("");
    for (const budget of response.budgets)
    {
        $(".budget-list").append($("<p class=\"budget\">Test</p>"));
    }
    if (response.budgets.length == 0)
    {
        $(".budget-list").append($("<p class=\"info\">No budgets found.</p>"));
    }
}

$(async () => {
    // Set up handlers
    $("#new").on("click", async ev => {
        const response = await apiRequest("/budget/create", {
            budget_name: `Budget ${hexToken(8)}`
        });
        if (response.error) {
            console.error(response.error);
            return;
        }
        updateBudgets();
    });
    // Update the budgets list on load, then every 5 seconds
    updateBudgets();
    setInterval(updateBudgets, 5000);
});