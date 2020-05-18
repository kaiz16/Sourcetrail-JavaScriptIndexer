# Sourcetrail JavaScript Indexer
### Requirements
SourcetrailDB
Swig (4.0.1)
Python3
NodeJS
### Setting up requirements
First download swig at (http://www.swig.org/download.html) and extract it somewhere.
Before you install Swig, you need to install Perl Compatible Regular Expressions (PRCE)
```sh
$ sudo apt-get install libpcre3 libpcre3-dev python3-dev python-dev
```
Next install swig
```sh
$ cd swig
$ ./configure
$ make
$ sudo make install
```
Then configure your bashrc to use python3 instead of python2
Check your python3 location
```sh
$ which python3
/usr/bin/python3
```
Set alias in your bashrc
```sh
alias python='/usr/bin/python3'
```
For installing nodejs follow the instructions below
https://github.com/nodesource/distributions/blob/master/README.md

### Installation
Clone this repo (Sourcetrail-JavaScriptIndexer)
```sh
$ git clone https://github.com/kaiz16/Sourcetrail-JavaScriptIndexer
```

Clone SourcetrailDB and build python bindings
```sh
$ git clone https://github.com/CoatiSoftware/SourcetrailDB
$ cd SourcetrailDB
$ mkdir build
$ cd build
$ cmake -D BUILD_BINDINGS_PYTHON=ON ..
$ make
```

Then copy and paste sourcetraildb.py and _sourcetraildb.so inside bindings_python to src folder of Sourcetrail-JavaScriptIndexer
```sh
$ cp sourcetraildb.py _sourcetraildb.so ~/path/to/Sourcetrail-JavaScriptIndexer/src
```
Replace data/file.js with the file you want to index (rename it to file.js)
```sh
$ cd Sourcetrail-JavaScriptIndexer
$ npm install
$ node src/ast.js > raw.json
$ python3 src/main.py --database-file-path=python_js_indexer.srctrldb --source-file-path=data/file.js
```
This will generate an indexer python_js_indexer.srctrlprj. Open it up using Sourcetrail. That's it.