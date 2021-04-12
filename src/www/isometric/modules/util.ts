import { Colors } from "./colors.js";

const hexCharacters = "0123456789abcdef";


export function randomChoice(iterable) {
    return iterable[Math.floor(Math.random() * iterable.length)];
}


export function randomColor() {
    return randomChoice(Colors);
}


export async function deriveColor(text) {
    const textBytes = new TextEncoder().encode(text);
    const digest = await crypto.subtle.digest("SHA-1", textBytes);
    const intHash = new Uint32Array(digest)[0];
    return Colors[intHash % Colors.length];
}


export function hexToken(amount) {
    if (!amount) amount = 8;
    let result = "";
    for (let i=0; i < amount; i++)
    {
        result += randomChoice(hexCharacters);
    }

    return result;
}