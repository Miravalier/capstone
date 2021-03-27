const hexCharacters = "0123456789abcdef";


export function randomChoice(iterable) {
    return iterable[Math.floor(Math.random() * iterable.length)];
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