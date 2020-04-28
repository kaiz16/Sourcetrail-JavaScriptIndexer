class Rectangle{
    constructor(height, weight){
        this.height = height;
        this.weight = weight;
    }

    getArea(){
        return calArea();
    }

    calArea(){
        return this.height * this.weight;
    }
}

const sq = new Rectangle();
sq.getArea()

function foo(){
    return bar()
}

function bar(){
    return printHello()
}

var printHello = function thatPrintsHello(){
    alert("Hello")
}
foo()