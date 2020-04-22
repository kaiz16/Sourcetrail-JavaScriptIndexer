import argparse
import os
import sourcetraildb as srctrl
import json

class AstVisitor:
	sourceFile = None
	parsedAst = None
	fileId = None
	recordedLists = []
	def __init__(self, _sourceFile, _ast):
		self.parsedAst = _ast
		self.sourceFile = _sourceFile
		self.fileId = srctrl.recordFile(_sourceFile)
		if not self.fileId:
			print("ERROR: " + srctrl.getLastError())
		srctrl.recordFileLanguage(self.fileId, "js")

	def recordNode(self, node, id, nameHierarchy):
		recordNode = {}
		recordNode["type"] = node["type"]
		recordNode["id"] = id
		recordNode["name"] = nameHierarchy
		recordNode["json"] = node
		return self.recordedLists.append(recordNode)

	def getLocationofNode(self, node):
		if node["id"]:
			startLine = node["id"]["loc"]["start"]["line"]
			startColumn = node["id"]["loc"]["start"]["column"]
			endLine = node["id"]["loc"]["end"]["line"]
			endColumn = node["id"]["loc"]["end"]["column"]
			return [startLine, startColumn, endLine, endColumn]
		else:
			startLine = node["loc"]["start"]["line"]
			startColumn = node["loc"]["start"]["column"]
			endLine = node["loc"]["end"]["line"]
			endColumn = node["loc"]["end"]["column"]
			return [startLine, startColumn, endLine, endColumn]

	def recordGlobalWindowObject(self, node):
		nameHierarchy = { "prefix": "", "name": node["type"], "postfix": ""}
		string = '{ "name_delimiter": ".", "name_elements": [ ''{ "prefix": "%s", "name": "%s", "postfix": "%s" } ''] }'%(
			nameHierarchy["prefix"], 
			nameHierarchy["name"], 
			nameHierarchy["postfix"]
			)
		symbolId = srctrl.recordSymbol(str(string))
		srctrl.recordSymbolDefinitionKind(symbolId, srctrl.DEFINITION_EXPLICIT)
		srctrl.recordSymbolKind(symbolId, srctrl.SYMBOL_MODULE)
		self.recordNode(node, symbolId, nameHierarchy)

	def visitVariableDeclaration(self, node):
		location = self.getLocationofNode(node)
		parentScope = self.getParentScope(node)
		# Do not record local variables for now
		if parentScope["type"] != "Program":
			return

		nameHierarchy = { "prefix": "", "name": node["id"]["name"], "postfix": ""}
		parentNameHierarchy = None
		for item in self.recordedLists:
			if parentScope == item["json"]:
				parentNameHierarchy = item["name"]
		string = '{ "name_delimiter": ".", "name_elements": [ ' '{ "prefix": "%s", "name": "%s", "postfix": "%s" }, ' '{ "prefix": "%s", "name": "%s", "postfix": "%s" } ''] }' %(
			parentNameHierarchy["prefix"], 
			parentNameHierarchy["name"], 
			parentNameHierarchy["postfix"], 
			nameHierarchy["prefix"], 
			nameHierarchy["name"], 
			nameHierarchy["postfix"]
			)
		symbolId = srctrl.recordSymbol(str(string))
		srctrl.recordSymbolDefinitionKind(symbolId, srctrl.DEFINITION_EXPLICIT)
		srctrl.recordSymbolKind(symbolId, srctrl.SYMBOL_GLOBAL_VARIABLE) 
		srctrl.recordSymbolLocation(symbolId, self.fileId, location[0], location[1] + 1, location[2], location[3])
		self.recordNode(node, symbolId, nameHierarchy)

	def visitFunctionDeclaration(self, node):
		location = self.getLocationofNode(node)
		parentScope = self.getParentScope(node)
		nameHierarchy = { "prefix": "", "name": node["id"]["name"], "postfix": ""}
		parentSymbolId = None
		parentNameHierarchy = None
		for item in self.recordedLists:
			if parentScope == item["json"]:
				parentSymbolId = item["id"]
				parentNameHierarchy = item["name"]
		string = None
		if parentScope["type"] != "Program":
			string = '{ "name_delimiter": ".", "name_elements": [ ' '{ "prefix": "%s", "name": "%s", "postfix": "%s" }, ' '{ "prefix": "%s", "name": "%s", "postfix": "%s" } ''] }' %(
				parentNameHierarchy["prefix"], 
				parentNameHierarchy["name"], 
				parentNameHierarchy["postfix"], 
				nameHierarchy["prefix"], 
				nameHierarchy["name"], 
				nameHierarchy["postfix"]
				)
		else:
			string = '{ "name_delimiter": ".", "name_elements": [ ' '{ "prefix": "%s", "name": "%s", "postfix": "%s" } ''] }' %(
				nameHierarchy["prefix"], 
				nameHierarchy["name"], 
				nameHierarchy["postfix"]
				)
		# print(parentSymbolId.name)
		symbolId = srctrl.recordSymbol(str(string))
		srctrl.recordSymbolDefinitionKind(symbolId, srctrl.DEFINITION_EXPLICIT)
		srctrl.recordSymbolKind(symbolId, srctrl.SYMBOL_FUNCTION)
		srctrl.recordSymbolLocation(symbolId, self.fileId, location[0], location[1] + 1, location[2], location[3])
		self.recordNode(node, symbolId, nameHierarchy)

	def getParentofNode(self, targetNode, ast=None, parentNode=None): 
		ast = ast == None and self.parsedAst or ast
		if ast["type"] == targetNode["type"] and ast["loc"] == targetNode["loc"]:
			return parentNode
		else:
			parentNode = ast
			for key in ast.keys():
				if (key == "loc" or key == "range"):
					continue
				if type(ast[key]) == dict: 
					return self.getParentofNode(targetNode, ast[key], parentNode)
				elif type(ast[key]) == list: # Array
					for item in ast[key]:
						return self.getParentofNode(targetNode, item, parentNode)
		return parentNode
		
	def getParentScope(self, targetNode):
		parent = self.getParentofNode(targetNode)
		if parent["type"] == "Program" or parent["type"] == "FunctionDeclaration" or parent["type"] == "ClassDeclaration":
			return parent
		else:
			return self.getParentScope(parent)

	def traverseNode(self, node=None):
		node = node == None and self.parsedAst or node
		if node["type"] == "Program":
			self.recordGlobalWindowObject(node)
		elif node["type"] == "FunctionDeclaration":
			self.visitFunctionDeclaration(node)
		elif node["type"] == "VariableDeclaration":
			for var in node["declarations"]:
				self.visitVariableDeclaration(var)

		for key in node.keys():
			if (key == "loc" or key == "range"):
				continue
			if type(node[key]) == dict: 
				self.traverseNode(node[key])
			elif type(node[key]) == list: # Array
					for item in node[key]:
						self.traverseNode(item)


def main():
	parser = argparse.ArgumentParser(description="SourcetrailDB JavaScript Indexer")
	parser.add_argument("--database-file-path", help="path to the generated Sourcetrail database file",
		type=str, required=True)
	parser.add_argument("--source-file-path", help="path to the source file to index",
		type=str, required=True)
	parser.add_argument("--database-version", help="database version of the invoking Sourcetrail binary",
		type=int, required=False, default=0)

	args = parser.parse_args()
	databaseFilePath = args.database_file_path
	sourceFilePath = args.source_file_path.replace("\\", "/")
	dbVersion = args.database_version

	print("SourcetrailDB JavaScript Indexer")
	print("Supported database version: " + str(srctrl.getSupportedDatabaseVersion()))

	if dbVersion > 0 and dbVersion != srctrl.getSupportedDatabaseVersion():
		print("ERROR: Only supports database version: " + str(srctrl.getSupportedDatabaseVersion()) +
			". Requested version: " + str(dbVersion))
		return 1

	if not srctrl.open(databaseFilePath):
		print("ERROR: " + srctrl.getLastError())
		return 1

	print("Clearing loaded database now...")
	srctrl.clear()

	print("start indexing")
	srctrl.beginTransaction()

	
	ast = open("raw.json", "r").read()
	parsedAst = json.loads(ast)
	astVisitor = AstVisitor(sourceFilePath, parsedAst)
	astVisitor.traverseNode()
	srctrl.commitTransaction()

	if len(srctrl.getLastError()) > 0:
		print("ERROR: " + srctrl.getLastError())
		return 1

	if not srctrl.close():
		print("ERROR: " + srctrl.getLastError())
		return 1

	# print("Recorded lists", astVisitor.recordedLists)
	print("done")
	return 0
main()
