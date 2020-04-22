const fs = require("fs");
const flow= require("flow-parser");
const test = fs.readFileSync("data/file.js").toString();
const ast = flow.parse(test, esproposal_optional_chaining=true);
const ARGS = process.argv;

console.log(ARGS[ARGS.length - 1] === "prettify" ? JSON.stringify(ast, null, " ") : JSON.stringify(ast))

function isNode(ast){
    return ast instanceof Object && !(ast instanceof Array);
}

function isArray(ast){
    return ast instanceof Object && ast instanceof Array;
}
