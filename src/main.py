import argparse
import os
import sourcetraildb as srctrl
import json

class AstVisitor:
	sourceFile = None
	parsedAst = None
	fileId = None
	recordedLists = []
	callNodes = []
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
	#	print(recordNode)
		return self.recordedLists.append(recordNode)

	def getLocationofNode(self, node):
		if "id" in node:
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
		nameHierarchy = [{ 'prefix': '', 'name': node["type"], 'postfix': ''}]
		string = { "name_delimiter": ".", "name_elements": [name for name in nameHierarchy] }
		symbolId = srctrl.recordSymbol(json.dumps(string))
		srctrl.recordSymbolDefinitionKind(symbolId, srctrl.DEFINITION_EXPLICIT)
		srctrl.recordSymbolKind(symbolId, srctrl.SYMBOL_MODULE)
		self.recordNode(node, symbolId, nameHierarchy)

	def visitVariableDeclaration(self, node):
		location = self.getLocationofNode(node)
		parentNode = self.getParentScope(node)
		# Do not record local variables for now
		if parentNode["type"] != "Program":
			return
		nodeName = { "prefix": "", "name": node["id"]["name"], "postfix": ""}
		nameHierarchy = None
		for item in self.recordedLists:
			if parentNode["type"] == item["type"] and parentNode == item["json"]:
				nameHierarchy = item["name"].copy()
				break

		nameHierarchy.append(nodeName)
		string = { "name_delimiter": ".", "name_elements": [name for name in nameHierarchy] }
		symbolId = srctrl.recordSymbol(json.dumps(string))
		srctrl.recordSymbolDefinitionKind(symbolId, srctrl.DEFINITION_EXPLICIT)
		srctrl.recordSymbolKind(symbolId, srctrl.SYMBOL_GLOBAL_VARIABLE) 
		srctrl.recordSymbolLocation(symbolId, self.fileId, location[0], location[1] + 1, location[2], location[3])
		self.recordNode(node, symbolId, nameHierarchy)

	def visitFunctionDeclaration(self, node):
		location = self.getLocationofNode(node)
		nodeName = { "prefix": "function", "name": node["id"]["name"], "postfix": ""}
		nameHierarchy = []
		parentNode = self.getParentScope(node)
		# if parentNode["type"] != "Program":
		# 	print(parentNode["id"]["name"])
		for item in self.recordedLists:
			if parentNode["type"] == item["type"] and parentNode == item["json"]:
				nameHierarchy = item["name"].copy()
				break
		
		nameHierarchy.append(nodeName)
		string = { "name_delimiter": ".", "name_elements": [name for name in nameHierarchy] }
		symbolId = srctrl.recordSymbol(json.dumps(string))
		srctrl.recordSymbolDefinitionKind(symbolId, srctrl.DEFINITION_EXPLICIT)
		srctrl.recordSymbolKind(symbolId, srctrl.SYMBOL_FUNCTION)
		srctrl.recordSymbolLocation(symbolId, self.fileId, location[0], location[1] + 1, location[2], location[3])
		self.recordNode(node, symbolId, nameHierarchy)

	def visitCallExpression(self, node):
		if not "name" in node["callee"]:
			return 
		location = self.getLocationofNode(node["callee"])
		referencedSymbolId = None
		for item in self.recordedLists:
			if item["name"][(len(item["name"]) - 1)]["name"] == node["callee"]["name"]:
				referencedSymbolId = item["id"]
				break

		if not referencedSymbolId:
			return
		contextSymbolId = None
		parentNode = self.getParentScope(node)
		for item in self.recordedLists:
			if parentNode["type"] == item["type"] and parentNode == item["json"]:
				contextSymbolId = item["id"]
				break
		referenceId = srctrl.recordReference(
						contextSymbolId,
						referencedSymbolId, 
						srctrl.REFERENCE_CALL
					)
		srctrl.recordReferenceLocation(referenceId, self.fileId, location[0], location[1] + 1, location[2], location[3])

	def getParentofNode(self, targetNode, ast=None, stacks=None):
		if not ast:
			ast = self.parsedAst
			stacks = []

		if ast["type"] == targetNode["type"] and ast["loc"] == targetNode["loc"]:
				return True
		else:
			for key in ast.keys():
				if (key == "loc" or key == "range"):
					continue
				if type(ast[key]) == dict: 
					if self.getParentofNode(targetNode, ast[key], stacks):
						stacks.append(ast)
						return stacks
				elif type(ast[key]) == list: # Array
					for item in ast[key]:
						if self.getParentofNode(targetNode, item, stacks):
							stacks.append(ast)
							return stacks
			return False
		
	def getParentScope(self, node):
		trails = self.getParentofNode(node)
		for trail in trails:
			if trail["type"] == "Program" or trail["type"] == "FunctionDeclaration" or trail["type"] == "ClassDeclaration":
				parentNode = trail
				break
		return parentNode

	def traverseNode(self, node=None):
		node = node == None and self.parsedAst or node
		if node["type"] == "Program":
			self.recordGlobalWindowObject(node)
		elif node["type"] == "FunctionDeclaration":
			self.visitFunctionDeclaration(node)
		elif node["type"] == "VariableDeclaration":
			for var in node["declarations"]:
				self.visitVariableDeclaration(var)
		elif node["type"] == "CallExpression":
				self.callNodes.append(node)

		for key in node.keys():
			if (key == "loc" or key == "range"):
				continue
			if type(node[key]) == dict: 
				self.traverseNode(node[key])
			elif type(node[key]) == list: # Array
					for item in node[key]:
						self.traverseNode(item)
					
	def solveCallExpressions(self):	
		for call in self.callNodes:
			self.visitCallExpression(call)

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
	astVisitor.solveCallExpressions()
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
