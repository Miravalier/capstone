import { apiRequest } from "./modules/api.js";
import { errorToast } from "./modules/ui.js";
import { hexToken } from "./modules/util.js";
import { Budget } from "./modules/datatypes.js";


const g_budgetCache = {};


async function updateBudgets() {
    const budgets = await Budget.list();

    // Hide the "no budgets" message if there are budgets
    if (budgets.length == 0)
    {
        $(".info").css('display', 'block');
    }
    else
    {
        $(".info").css('display', 'none');
    }

    // Track the set of keys that used to exist. If any no longer exist,
    // remove that element from the page.
    const keys = new Set(Object.keys(g_budgetCache));
    for (const budget of budgets)
    {
        // If this key is in the cache, remove it from the keys set
        if (g_budgetCache[budget.id.toString()])
        {
            keys.delete(budget.id.toString());
        }
        // Otherwise, add it to the global cache and create elements
        // for it.
        else
        {
            // Add element to name column
            const nameElement = $(`<p>${budget.name}</p>`);
            $(".budget-column.names").append(nameElement);

            // Add element to role column
            const roleElement = $(`<p>${budget.role}</p>`);
            $(".budget-column.permissions").append(roleElement);

            // Create button elements
            const openButton = $(`
                <span class="button open-budget" data-id="${budget.id}">
                    <i class="fas fa-eye"></i>
                </span>
            `);
            openButton.on("click", async ev => {
                const id = $(ev.currentTarget).attr("data-id");
                window.location.href = "/budget?id="+id;
            });

            const deleteButton = $(`
                <span class="button delete-budget" data-id="${budget.id}">
                    <i class="fas fa-trash-alt"></i>
                </span>
            `);
            deleteButton.on("click", async ev => {
                const id = $(ev.currentTarget).attr("data-id");
                const response = await apiRequest("/budget/delete", {
                    budget_id: parseInt(id)
                });
                await updateBudgets();
            });

            // Add buttons and container to buttons column
            const buttonContainer = $(`<div></div>`);
            buttonContainer.append(openButton);
            buttonContainer.append(deleteButton);
            $(".budget-column.buttons").append(buttonContainer);
            
            // Save elements in cache
            g_budgetCache[budget.id.toString()] = [nameElement, roleElement, buttonContainer];
        }
    }

    // Remove any budget elements that used to exist but were deleted
    for (const id of keys)
    {
        console.log("Removing Budget #" + id);
        const elements = g_budgetCache[id];
        for (const element of elements)
        {
            element.remove();
        }
        delete g_budgetCache[id];
    }
}

$(async () => {
    // Set up handlers
    $(".new-budget").on("click", async ev => {
        const response = await apiRequest("/budget/create", {
            budget_name: `Budget ${hexToken(8)}`
        });
        if (response.error) {
            console.error(response.error);
            return;
        }
        await updateBudgets();
    });

    $(".sign-out").on("click", async ev => {
        sessionStorage.setItem('authtoken', null);
        window.location.href = "/login";
    });

    // Update the budgets list on load, then every 5 seconds
    await updateBudgets();
    setInterval(updateBudgets, 5000);
});