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
    // Generate chart data
    const categoryNames = [];
    const categoryAmounts = [];
    const categoryColors = [];
    
    const categories = await g_budget.categories();
    for (const category of categories) {
        categoryNames.push(category.name);
        categoryAmounts.push(await category.total());
        categoryColors.push(await deriveColor(category.name));
    }

    // Render chart
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
    return pieChart;
}


async function generateLineGraph() {
    // Generate chart data
    const categoryData = {};
    const budgetLabels = [g_budget.name];
    
    const categories = await g_budget.categories();
    for (const category of categories) {
        categoryData[category.name] = {
            values: [await category.total()],
            color: await deriveColor(category.name)
        }
    }

    // Add historical data
    let parent = await g_budget.parent();
    while (parent)
    {
        const missingCategories = new Set(Object.keys(categoryData));
        const parentCategories = await parent.categories();
        for (const category of parentCategories)
        {
            if (missingCategories.has(category.name))
            {
                missingCategories.delete(category.name);
                categoryData[category.name].values.unshift(await category.total());
            }
        }
        for (const name of missingCategories)
        {
            categoryData[name].values.unshift(0);
        }
        budgetLabels.unshift(parent.name);
        parent = await parent.parent();
    }

    // Add future data
    let child = await g_budget.child();
    while (child)
    {
        const missingCategories = new Set(Object.keys(categoryData));
        const childCategories = await child.categories();
        for (const category of childCategories)
        {
            if (missingCategories.has(category.name))
            {
                missingCategories.delete(category.name);
                categoryData[category.name].values.push(await category.total());
            }
        }
        for (const name of missingCategories)
        {
            categoryData[name].values.push(0);
        }
        budgetLabels.push(child.name);
        child = await child.child();
    }

    // Construct datasets
    const datasets = [];
    for (const [name, cdata] of Object.entries(categoryData))
    {
        datasets.push({
            label: name,
            data: cdata.values,
            fill: false,
            borderColor: cdata.color,
            tension: 0.1
        });
    }

    // Render chart
    const lineGraph = new Chart(
        document.getElementById('lineGraph').getContext('2d'),
        {
            type: 'line',
            data: {
                labels: budgetLabels,
                datasets: datasets
            },
            options: {
                maintainAspectRatio: false,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: ctx => moneyLabel(ctx.dataset.label || '', ctx.parsed.y)
                        }
                    }
                }
            }
        }
    );
    return lineGraph;
}


async function generateBarGraph() {
    // Generate chart data
    const categoryNames = [];
    const categoryAmounts = [];
    const categoryColors = [];
    
    const categories = await g_budget.categories();
    for (const category of categories) {
        categoryNames.push(category.name);
        categoryAmounts.push(await category.total());
        categoryColors.push(await deriveColor(category.name));
    }

    // Render chart
    const barGraph = new Chart(
        document.getElementById('barGraph').getContext('2d'),
        {
            type: 'bar',
            data: {
                labels: categoryNames,
                datasets: [{
                    label: g_budget.name,
                    data: categoryAmounts,
                    backgroundColor: categoryColors
                }]
            },
            options: {
                maintainAspectRatio: false,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: ctx => moneyLabel(ctx.dataset.label || '', ctx.parsed.y)
                        }
                    }
                }
            }
        }
    );
    return barGraph;
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
    generateLineGraph();
    generateBarGraph();
});