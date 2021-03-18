// Utility functions
async function apiRequest(endpoint, data)
{
    return await $.ajax({
        type: "POST",
        dataType: "json",
        url: "/api" + endpoint,
        data: JSON.stringify(data),
        contentType: "application/json; charset=utf-8"
    });
}

// Main Function
$(async function() {
    console.log("Initializing Isometric Finance");
    
    console.log(await apiRequest('/register', {username: "myname", password: "mypassword"}));
    console.log(await apiRequest('/login', {username: "myname", password: "mypassword"}));
})