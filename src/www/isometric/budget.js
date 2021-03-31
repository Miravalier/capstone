import { Budget, PERM_UPDATE, PERM_ADMIN } from "./modules/datatypes.js";
import { hexToken } from "./modules/util.js";


let g_budget = null;
const g_categoryCache = {};
const g_expenseCache = {};


async function updateCategories() {
    const categories = await g_budget.categories();

    // Hide the "no categories" message if there are categories
    if (categories.length == 0)
    {
        $(".info").css('display', 'block');
    }
    else
    {
        $(".info").css('display', 'none');
    }

    // Track the set of category keys that used to exist. If any no longer exist,
    // remove that category element from the page.
    const categoryKeys = new Set(Object.keys(g_categoryCache));
    for (const category of categories)
    {
        // If this key is in the cache, remove it from the category keys set
        if (g_categoryCache[category.id.toString()])
        {
            const categoryElement = g_categoryCache[category.id.toString()];
            categoryKeys.delete(category.id.toString());

            // Go through the expenses and add new expenses, delete missing ones
            const expenses = await category.expenses();
            const expenseKeys = new Set(Object.keys(g_expenseCache[category.id.toString()]));
            for (const expense of expenses)
            {
                // If this expense is in the cache, remove it from the set
                if (g_expenseCache[category.id.toString()][expense.id.toString()]) {
                    expenseKeys.delete(expense.id.toString());
                }
                // Otherwise, add it to the cache and the document
                else {
                    const expenseElement = $(`
                        <div>
                            <input class="description" type="text">
                            <span class="label">$</span>
                            <input class="amount" type="number" step="0.01">
                            <input class="date" type="date">
                            <span class="delete"><i class="fas fa-trash-alt"></i></span>
                        </div>
                    `);
                    expenseElement.find(".description").val(expense.description);
                    expenseElement.find(".amount").val(expense.amount);
                    expenseElement.find(".date").val(expense.date);
                    expenseElement.find(".delete").on("click", async ev => {
                        await expense.delete();
                        await updateCategories();
                    });
                    categoryElement.append(expenseElement);

                    // Save expense element in cache
                    g_expenseCache[category.id.toString()][expense.id.toString()] = expenseElement;
                }
            }

            // Remove any categories that used to exist but were deleted
            for (const id of expenseKeys)
            {
                console.log("Removing Expense #" + id);
                const expenseElement = g_expenseCache[category.id.toString()][id];
                expenseElement.remove();
                delete g_expenseCache[category.id.toString()][id];
            }
        }
        // Otherwise, add it to the global cache and create categoryElements
        // for it.
        else
        {
            // Create container categoryElement
            const categoryElement = $(`<div class="header"><p>${category.name}</p></div>`);
            // Create add and delete buttons
            if (g_budget.permissions >= PERM_UPDATE)
            {
                const addButton = $(`
                    <span class="button add-transaction">
                        <i class="fas fa-plus"></i>
                    </span>
                `);
                addButton.on("click", async ev => {
                    await category.addExpense(
                        "", // Description
                        0, // Amount
                        new Date().toISOString().substr(0, 10) // Date
                    );
                    await updateCategories();
                });
                categoryElement.append(addButton);
            }
            if (g_budget.permissions >= PERM_ADMIN )
            {
                const deleteButton = $(`
                    <span class="button delete-category">
                        <i class="fas fa-trash-alt"></i>
                    </span>
                `);
                deleteButton.on("click", async ev => {
                    await category.delete();
                    await updateCategories();
                });
                categoryElement.append(deleteButton);
            }

            // Append header categoryElement to document
            $(".category-table").append(categoryElement);

            // Append each expense categoryElement, track them in a separate cache
            g_expenseCache[category.id.toString()] = {};
            const expenses = await category.expenses();
            for (const expense of expenses)
            {
                const expenseElement = $(`
                    <div>
                        <input class="description" type="text">
                        <span class="label">$</span>
                        <input class="amount" type="number" step="0.01">
                        <input class="date" type="date">
                        <span class="delete"><i class="fas fa-trash-alt"></i></span>
                    </div>
                `)
                expenseElement.find(".description").val(expense.description);
                expenseElement.find(".amount").val(expense.amount);
                expenseElement.find(".date").val(expense.date);
                expenseElement.find(".delete").on("click", async ev => {
                    await expense.delete();
                    await updateCategories();
                });
                categoryElement.append(expenseElement);

                // Save expense element in cache
                g_expenseCache[category.id.toString()][expense.id.toString()] = expenseElement;
            }
            
            // Save header categoryElement in cache
            g_categoryCache[category.id.toString()] = categoryElement;
        }
    }

    // Remove any categories that used to exist but were deleted
    for (const id of categoryKeys)
    {
        console.log("Removing Category #" + id);
        const categoryElement = g_categoryCache[id];
        categoryElement.remove();
        delete g_categoryCache[id];
    }
}


$(async () => {
    // Parse out budget id
    const urlParams = new URLSearchParams(window.location.search);
    const budgetId = parseInt(urlParams.get('id'));

    // Get budget info
    try {
        g_budget = await Budget.from_id(budgetId);
    }
    catch (e) {
        window.location.href = "/home";
        return;
    }

    // Update title
    $(".title").text(g_budget.name + " Transactions");

    // Set up handlers
    $(".new-category").on("click", async ev => {
        await g_budget.addCategory(hexToken(8));
        await updateCategories();
    });

    $(".back").on("click", async ev => {
        window.location.href = "/home";
        return;
    });

    // Update the categories on load, then every 5 seconds
    await updateCategories();
    setInterval(updateCategories, 5000);
});