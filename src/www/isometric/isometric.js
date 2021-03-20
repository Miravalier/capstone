import {Budget, Category, Expense} from "./datatypes.js";

// Utility functions

/*
 * Return true if the login succeeds, false otherwise.
 */
async function login(username, password)
{
    const reply = await apiRequest("/login", {username, password});
    if (reply.authtoken)
    {
        console.log("Login successful");
        sessionStorage.setItem('authtoken', reply.authtoken);
        return true;
    }
    else
    {
        console.error(reply.error);
        return false;
    }
}

/*
 * Return true if the registration succeeds, false otherwise.
 */
async function register(username, password)
{
    const reply = await apiRequest("/register", {username, password});
    if (reply.authtoken)
    {
        console.log("Registration successful");
        sessionStorage.setItem('authtoken', reply.authtoken);
        return true;
    }
    else
    {
        console.error(reply.error);
        return false;
    }
}

/*
 * Make a request to the API. Returns the JSON that
 * comes back.
 */
async function apiRequest(endpoint, data)
{
    if (!endpoint) {
        endpoint = "/status";
    }
    if (!data) {
        data = {};
    }
    let authtoken = sessionStorage.getItem('authtoken');
    if (authtoken) {
        data.authtoken = authtoken;
    }
    try {
        return await $.ajax({
            type: "POST",
            dataType: "json",
            url: "/api" + endpoint,
            data: JSON.stringify(data),
            contentType: "application/json; charset=utf-8"
        });
    }
    catch (error) {
        return error.responseJSON;
    }
}

// Main Function
$(async function() {
    console.log("Initializing Isometric Finance");
});