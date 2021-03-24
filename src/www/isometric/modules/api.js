/*
 * If the login succeeds, stores the authtoken in the session
 * storage. Returns the JSON reply.
 */
export async function login(username, password)
{
    const reply = await apiRequest("/login", {username, password});
    if (reply.authtoken)
    {
        console.log("Login successful");
        sessionStorage.setItem('authtoken', reply.authtoken);
        return reply;
    }
    else
    {
        console.error(reply.error);
        return reply;
    }
}

/*
 * If the registration succeeds, stores the authtoken in the session
 * storage. Returns the JSON reply.
 */
export async function register(username, password)
{
    const reply = await apiRequest("/register", {username, password});
    if (reply.authtoken)
    {
        console.log("Registration successful");
        sessionStorage.setItem('authtoken', reply.authtoken);
        return reply;
    }
    else
    {
        console.error(reply.error);
        return reply;
    }
}

/*
 * Make a request to the API. Returns the JSON that
 * comes back.
 */
export async function apiRequest(endpoint, data)
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
        const reply = error.responseJSON;
        if (reply.error == "login required") {
            console.log("Session not valid, redirecting to /login...");
            window.location.replace("/login");
        }
        return reply;
    }
}