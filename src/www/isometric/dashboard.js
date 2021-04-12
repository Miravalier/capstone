import { Budget, PERM_UPDATE, PERM_ADMIN } from "./modules/datatypes.js";
import { deriveColor } from "./modules/util.js";
import { errorToast } from "./modules/ui.js";

let g_budget = null;


function moneyLabel(label, value) {
    const formattedValue = new Intl.NumberFormat(
        'en-US',
        { style: 'currency', currency: 'USD' }
    ).format(value);
    return `${label}: ${formattedValue}`;
}


async function generatePieChart() {
    // Generate pie chart data
    const categoryNames = [];
    const categoryAmounts = [];
    const categoryColors = [];
    
    const categories = await g_budget.categories();
    for (const category of categories) {
        categoryNames.push(category.name);
        categoryAmounts.push(await category.total());
        categoryColors.push(await deriveColor(category.name));
    }

    // Render pie chart
    const pieChart = new Chart(
        document.getElementById('pieChart').getContext('2d'),
        {
            type: 'doughnut',
            data: {
                labels: categoryNames,
                datasets: [{
                    data: categoryAmounts,
                    backgroundColor: categoryColors,
                    hoverOffset: 4
                }]
            },
            options: {
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: ctx => moneyLabel(ctx.label, ctx.parsed)
                        }
                    }
                }
            }
        }
    );
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
    $(".title").text(g_budget.name + " Dashboard");

    $(".back").on("click", ev => {
        window.location.href = "/home";
        return;
    });

    generatePieChart();
});