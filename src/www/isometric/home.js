import { apiRequest } from "./modules/api.js";
import { errorToast } from "./modules/ui.js";
import { Budget } from "./modules/datatypes.js";


const g_budgetCache = {};


async function createNewBudgetDialog()
{
    const dialogElement = $(`
        <div class="dialog">
            <div class="dialog-header">
                <span>Create New Budget</span>
            </div>
            <div class="dialog-row">
                <input class="name" type="text">
            </div>
            <div class="dialog-row">
                <button class="create">Create <i class="fas fa-save"></i></button>
                <button class="cancel">Cancel <i class="fas fa-ban"></i></button>
            </div>
        </div>
    `);
    // Add save callback
    dialogElement.find(".create").on("click", async ev => {
        // Get name parameter
        const name = dialogElement.find(".name").val();
        if (!name) {
            console.error("Name parameter missing on budget create.");
            dialogElement.remove();
            return;
        }
        // Insert category in DB
        await Budget.create(name);
        await updateBudgets();
        // Close dialog
        dialogElement.remove();
    });
    // Add cancel callback
    dialogElement.find(".cancel").on("click", async ev => {
        // Close dialog
        dialogElement.remove();
    });
    // Display dialog
    $('.overlay').append(dialogElement);
    return dialogElement;
}


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

            // Add element to parent column
            let parentElement = null;
            const parent = await budget.parent();
            if (parent) {
                parentElement = $(`<p>${parent.name}</p>`);
            }
            else {
                parentElement = $(`<p>-</p>`);
            }
            $(".budget-column.parents").append(parentElement);

            // Create button elements
            const openButton = $(`
                <span class="button open-budget" data-id="${budget.id}">
                    <i class="fas fa-pencil"></i>
                </span>
            `);
            openButton.on("click", async ev => {
                const id = $(ev.currentTarget).attr("data-id");
                window.location.href = "/budget?id="+id;
            });

            const dashboardButton = $(`
                <span class="button view-dashboard" data-id="${budget.id}">
                    <i class="fas fa-chart-line"></i>
                </span>
            `);
            dashboardButton.on("click", async ev => {
                const id = $(ev.currentTarget).attr("data-id");
                window.location.href = "/dashboard?id="+id;
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
            buttonContainer.append(dashboardButton);
            buttonContainer.append(deleteButton);
            $(".budget-column.buttons").append(buttonContainer);
            
            // Save elements in cache
            g_budgetCache[budget.id.toString()] = [nameElement, roleElement, parentElement, buttonContainer];
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
        await createNewBudgetDialog();
    });

    $(".sign-out").on("click", async ev => {
        sessionStorage.setItem('authtoken', null);
        window.location.href = "/login";
    });

    // Update the budgets list on load, then every 5 seconds
    await updateBudgets();
    setInterval(updateBudgets, 5000);
});