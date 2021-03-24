import { apiRequest, login, register } from "./modules/api.js";
import { errorToast } from "./modules/ui.js";

$(async () => {
    const response = await apiRequest("/budget/list");
    if (response.error)
    {
        errorToast("A network error has occured. Try refreshing the " +
            "page when your internet connectivity returns.");
        return;
    }

    for (const budget of response.budgets)
    {
        $("#budgets").appendChild($("<p>Test</p>"));
        console.log(budget);
    }
});