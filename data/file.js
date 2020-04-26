function foo(){
   return bar()
}

function bar(){
   return printHello()
}

function printHello(){
    console.log("hello")
}
foo()

function findFactorial(number){
    if (number == 0) return 1
    return number * findFactorial(number - 1)
}

findFactorial(1)