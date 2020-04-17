const fs = require("fs");
const { Parser } = require("acorn");
const test = fs.readFileSync("../data/file.js").toString();
const ast = Parser.parse(test);

sourcetrailDB = []
// for (let key in ast.body){
//    references.push(ast.body[key].type)
// }
// console.log(references)
const result = []
function astVisitor(ast){
    result.push(ast);
    for (let key in ast){
       if (isNode(ast[key])){
            astVisitor(ast[key])
       }else if (isArray(ast[key])) {
            ast[key].forEach(node => {
                astVisitor(node);
            });
       }
    }
}

const ignore = ["BlockStatement"]
const watch = ["FunctionDeclaration", "Identifier", "MemberExpression", "VariableDeclaration", ""]
astVisitor(ast);
console.log(result);



// console.log(JSON.stringify(result))

function isNode(ast){
    return ast instanceof Object && !(ast instanceof Array);
}

function isArray(ast){
    return ast instanceof Object && ast instanceof Array;
}
// console.log(sourcetrailDB)