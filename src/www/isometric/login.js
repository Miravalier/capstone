import { apiRequest, login, register } from "./modules/api.js";

$(() => {
    $("#register").on("click", async ev => {
        const username = $("#username").val();
        const password = $("#password").val();
        if (!username) {
            console.error("Username cannot be left blank");
            return;
        }
        if (!password) {
            console.error("Password cannot be left blank");
            return;
        }
        const response = await register(username, password);
        if (response.status == "success") {
            window.location.href = "/budgets";
        }
    });

    $("#login").on("click", async ev => {
        const username = $("#username").val();
        const password = $("#password").val();
        if (!username) {
            console.error("Username cannot be left blank");
            return;
        }
        if (!password) {
            console.error("Password cannot be left blank");
            return;
        }
        const response = await login(username, password);
        if (response.status == "success") {
            window.location.href = "/home";
        }
    });
});