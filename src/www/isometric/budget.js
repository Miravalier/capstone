import { Budget, PERM_UPDATE, PERM_ADMIN } from "./modules/datatypes.js";


let g_budget = null;
const g_categoryCache = {};
const g_expenseCache = {};

async function createNewCategoryDialog()
{
    const dialogElement = $(`
        <div class="dialog">
            <div class="dialog-header">
                <span>Create New Category</span>
            </div>
            <div class="dialog-row">
                <input class="name" type="text">
            </div>
            <div class="dialog-row">
                <button class="create">Save <i class="fas fa-save"></i></button>
                <button class="cancel">Cancel <i class="fas fa-ban"></i></button>
            </div>
        </div>
    `);
    // Add save callback
    dialogElement.find(".create").on("click", async ev => {
        // Get name parameter
        const name = dialogElement.find(".name").val();
        if (!name) {
            console.error("Name parameter missing on category create.");
            dialogElement.remove();
            return;
        }
        // Insert category in DB
        await g_budget.addCategory(name);
        await updateCategories();
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

async function createExpenseDialog(expense)
{
    const category = await expense.category();
    const dialogElement = $(`
        <div class="dialog">
            <div class="dialog-header">
                <span>Expense ID#${expense.id}</span>
            </div>
            <div class="dialog-row">
                <input class="description" type="text">
                <span class="label">$</span>
                <input class="amount" type="number" step="0.01">
                <input class="date" type="date">
            </div>
            <div class="dialog-row">
                <button class="save">Save <i class="fas fa-save"></i></button>
                <button class="cancel">Cancel <i class="fas fa-ban"></i></button>
                <button class="delete">Delete <i class="fas fa-trash-alt"></i></button>
            </div>
        </div>
    `);
    // Pre fill inputs
    dialogElement.find(".description").val(expense.description);
    dialogElement.find(".amount").val(expense.amount.substring(1));
    dialogElement.find(".date").val(expense.date);
    // Add save callback
    dialogElement.find(".save").on("click", async ev => {
        // Save changes to DB
        let amount = dialogElement.find(".amount").val();
        let date = dialogElement.find(".date").val();
        if (!amount) amount = 0;
        if (!date) {
            dialogElement.remove();
            return;
        }
        await expense.update(
            dialogElement.find(".description").val(),
            amount,
            date
        );
        // Update element in html
        const expenseElement = g_expenseCache[category.id.toString()][expense.id];
        expenseElement.find(".description").text(expense.description);
        expenseElement.find(".amount").text(expense.amount);
        expenseElement.find(".date").text(expense.date);
        // Close dialog
        dialogElement.remove();
    });
    // Add cancel callback
    dialogElement.find(".cancel").on("click", async ev => {
        dialogElement.remove();
    });
    // Add delete callback
    dialogElement.find(".delete").on("click", async ev => {
        await expense.delete();
        await updateCategories();
        dialogElement.remove();
    });
    // Display dialog
    $('.overlay').append(dialogElement);
    return dialogElement;
}


function createExpenseElement(categoryElement, expense)
{
    const expenseElement = $(`
        <div class="expense">
            <span class="id">${expense.id}</span>
            <span class="description">${expense.description}</span>
            <span class="amount">${expense.amount}</span>
            <span class="date">${expense.date}</span>
            <span class="button edit"><i class="fas fa-pencil"></i></span>
        </div>
    `);
    expenseElement.find(".edit").on("click", async ev => {
        await createExpenseDialog(expense);
    });
    categoryElement.find(".expenses").append(expenseElement);
    return expenseElement;
}


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
                    const expenseElement = createExpenseElement(categoryElement, expense);
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
            const categoryElement = $(`
                <div class="category">
                    <div class="header">
                        <span>Category: ${category.name}</span>
                        <span class="button delete-category">
                            <i class="fas fa-trash-alt"></i>
                        </span>
                    </div>
                    <div class="expenses">
                        <div class="expense header">
                            <span class="id">ID</span>
                            <span class="description">Description</span>
                            <span class="amount">Amount</span>
                            <span class="date">Date</span>
                            <span class="button add-transaction">
                                <i class="fas fa-plus"></i>
                            </span>
                        </div>
                    </div>
                </div>
            `);
            // Create add and delete buttons
            if (g_budget.permissions >= PERM_UPDATE)
            {
                const addButton = categoryElement.find(".add-transaction");
                addButton.on("click", async ev => {
                    await category.addExpense(
                        "", // Description
                        "$0.00", // Amount
                        new Date().toISOString().substr(0, 10) // Date
                    );
                    await updateCategories();
                });
            }
            if (g_budget.permissions >= PERM_ADMIN )
            {
                const deleteButton = categoryElement.find(".delete-category");
                deleteButton.on("click", async ev => {
                    await category.delete();
                    await updateCategories();
                });
            }

            // Append header categoryElement to document
            $(".category-table").append(categoryElement);

            // Append each expense categoryElement, track them in a separate cache
            g_expenseCache[category.id.toString()] = {};
            const expenses = await category.expenses();
            for (const expense of expenses)
            {
                // Save expense element in cache
                const expenseElement = createExpenseElement(categoryElement, expense);
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
        createNewCategoryDialog();
    });

    $(".back").on("click", async ev => {
        window.location.href = "/home";
        return;
    });

    // Update the categories on load, then every 5 seconds
    await updateCategories();
    setInterval(updateCategories, 5000);
});