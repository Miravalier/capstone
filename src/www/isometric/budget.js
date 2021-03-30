import { Budget, PERM_UPDATE, PERM_ADMIN } from "./modules/datatypes.js";
import { hexToken } from "./modules/util.js";


let g_budget = null;
const g_categoryCache = {};


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

    // Track the set of keys that used to exist. If any no longer exist,
    // remove that element from the page.
    const keys = new Set(Object.keys(g_categoryCache));
    for (const category of categories)
    {
        // If this key is in the cache, remove it from the keys set
        if (g_categoryCache[category.id.toString()])
        {
            keys.delete(category.id.toString());
        }
        // Otherwise, add it to the global cache and create elements
        // for it.
        else
        {
            // Create container element
            const element = $(`<div class="header"><p>${category.name}</p></div>`);
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
                element.append(addButton);
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
                element.append(deleteButton);
            }

            // Append elements to document
            $(".category-table").append(element);
            
            // Save elements in cache
            g_categoryCache[category.id.toString()] = element;
        }
    }

    // Remove any categories that used to exist but were deleted
    for (const id of keys)
    {
        console.log("Removing Category #" + id);
        const element = g_categoryCache[id];
        element.remove();
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

    // Set up handlers
    $(".new-category").on("click", async ev => {
        await g_budget.addCategory(hexToken(8));
        await updateCategories();
    });

    // Update the categories on load, then every 5 seconds
    await updateCategories();
    setInterval(updateCategories, 5000);
});