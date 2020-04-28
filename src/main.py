import argparse
import os
import sourcetraildb as srctrl
import json
import jedi

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
		self.recordNode(self.fileId, None, None, True)

	def recordNode(self, id, nameHierarchy, location, scope = False, referencedNodeId = None):
		recordNode = {}
		recordNode["id"] = id
		recordNode["nameHierarchy"] = nameHierarchy
		recordNode["location"] = location
		recordNode["scope"] = scope
		recordNode["referencedNodeId"] = referencedNodeId
		return self.recordedLists.append(recordNode)

	def getLocationofNode(self, node):
		startLine = node["loc"]["start"]["line"]
		startColumn = node["loc"]["start"]["column"]
		endLine = node["loc"]["end"]["line"]
		endColumn = node["loc"]["end"]["column"]
		return [startLine, startColumn, endLine, endColumn]

	def visitFunctionDeclaration(self, node):
		if "id" in node:
			nodeName = { "prefix": "", "name": node["id"]["name"], "postfix": ""}
			location = self.getLocationofNode(node["id"])
		else:
			nodeName = { "prefix": "", "name": node["key"]["name"], "postfix": ""}
			location = self.getLocationofNode(node["key"])
		scopeLocation = self.getLocationofNode(node)
		#nodeName = { "prefix": "", "name": node["id"]["name"], "postfix": ""}
		parentName = self.getParentName(node)["nameHierarchy"]
		if parentName == None:
			nameHierarchy = [nodeName]
		else:
			nameHierarchy = [name for name in parentName]
			nameHierarchy.append(nodeName)
		string = { "name_delimiter": ".", "name_elements": [name for name in nameHierarchy] }
		symbolId = srctrl.recordSymbol(json.dumps(string))
		srctrl.recordSymbolDefinitionKind(symbolId, srctrl.DEFINITION_EXPLICIT)
		srctrl.recordSymbolKind(symbolId, srctrl.SYMBOL_FUNCTION)
		srctrl.recordSymbolLocation(symbolId, self.fileId, location[0], location[1] + 1, location[2], location[3])
		srctrl.recordSymbolScopeLocation(symbolId, self.fileId, scopeLocation[0], scopeLocation[1] + 1, scopeLocation[2], scopeLocation[3])
		self.recordNode(symbolId, nameHierarchy, scopeLocation, True)

	def visitClassDeclaration(self, node):
		location = self.getLocationofNode(node["id"])
		scopeLocation = self.getLocationofNode(node)
		nodeName = { "prefix": "", "name": node["id"]["name"], "postfix": ""}
		parentName = self.getParentName(node)["nameHierarchy"]
		if parentName == None:
			nameHierarchy = [nodeName]
		else:
			nameHierarchy = [name for name in parentName]
			nameHierarchy.append(nodeName)
		string = { "name_delimiter": ".", "name_elements": [name for name in nameHierarchy] }
		symbolId = srctrl.recordSymbol(json.dumps(string))
		srctrl.recordSymbolDefinitionKind(symbolId, srctrl.DEFINITION_EXPLICIT)
		srctrl.recordSymbolKind(symbolId, srctrl.SYMBOL_CLASS)
		srctrl.recordSymbolLocation(symbolId, self.fileId, location[0], location[1] + 1, location[2], location[3])
		srctrl.recordSymbolScopeLocation(symbolId, self.fileId, scopeLocation[0], scopeLocation[1] + 1, scopeLocation[2], scopeLocation[3])
		self.recordNode(symbolId, nameHierarchy, scopeLocation, True)

	def visitVariableDeclaration(self, node):
		if node["init"]["type"] == "FunctionExpression":
			self.visitFunctionDeclaration(node)
			return
		if node["init"]["type"] == "NewExpression":
			self.visitNewExpression(node)
			return
		location = self.getLocationofNode(node["id"])
		nodeName = { "prefix": "", "name": node["id"]["name"], "postfix": ""}
		
		parentName = self.getParentName(node)["nameHierarchy"]
		if parentName:
			return
		string = { "name_delimiter": ".", "name_elements": [nodeName] }
		symbolId = srctrl.recordSymbol(json.dumps(string))
		srctrl.recordSymbolDefinitionKind(symbolId, srctrl.DEFINITION_EXPLICIT)
		srctrl.recordSymbolKind(symbolId, srctrl.SYMBOL_GLOBAL_VARIABLE)
		srctrl.recordSymbolLocation(symbolId, self.fileId, location[0], location[1] + 1, location[2], location[3])
		#self.recordNode(symbolId, nameHierarchy, scopeLocation, False)

	def visitNewExpression(self, node):
		loc = node["id"]["loc"]
		node["init"]["callee"]["loc"] = loc

		location = self.getLocationofNode(node["id"])
		nodeName = { "prefix": "", "name": node["id"]["name"], "postfix": ""}
		
		parentName = self.getParentName(node)["nameHierarchy"]
		if parentName == None:
			nameHierarchy = [nodeName]
		else:
			nameHierarchy = [name for name in parentName]
			nameHierarchy.append(nodeName)
		string = { "name_delimiter": ".", "name_elements": [name for name in nameHierarchy] }
		v = self.visitCallExpression(node["init"])
		v["nameHierarchy"] = node["id"]["name"]
		

	def visitMemberExpression(self, node):
		if not "name" in node["object"]:
			return
		objName = node["object"]["name"]
		location = self.getLocationofNode(node["object"])
		referencedSymbolId = None
		for item in self.recordedLists:
			name = item["nameHierarchy"]
			if not name:
				continue
			if item["nameHierarchy"] == objName:
				referencedSymbolId = item["referencedNodeId"]
				break
		contextSymbolId = self.getParentName(node)["id"]
		referenceId = srctrl.recordReference(
						contextSymbolId,
						referencedSymbolId, 
						srctrl.REFERENCE_CALL
					)
		srctrl.recordReferenceLocation(referenceId, self.fileId, location[0], location[1] + 1, location[2], location[3])
		return self.visitCallExpression(node["property"])

	def visitCallExpression(self, node):
		
		if "callee" in node:
			if not "name" in node["callee"]:
				return 
			nodeName = node["callee"]["name"]
			location = self.getLocationofNode(node["callee"])
		else:
			if not "name" in node:
				return 
			nodeName = node["name"]
			location = self.getLocationofNode(node)
		referencedSymbolId = None
		for item in self.recordedLists:
			name = item["nameHierarchy"]
			if not name:
				continue
			if type(name) == list:
				if name[len(name) - 1]["name"] == nodeName:
					referencedSymbolId = item["id"]
					break

		if not referencedSymbolId:
			return

		contextSymbolId = self.getParentName(node)["id"]

		referenceId = srctrl.recordReference(
						contextSymbolId,
						referencedSymbolId, 
						srctrl.REFERENCE_CALL
					)
		srctrl.recordReferenceLocation(referenceId, self.fileId, location[0], location[1] + 1, location[2], location[3])
		self.recordNode(referenceId, nodeName, location, False, referencedSymbolId)
		return self.recordedLists[len(self.recordedLists) - 1]

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
		
	def getParentName(self, node):
		parents = self.getParentofNode(node)
		for parent in parents:
			if parent["type"] == "Program":
				return self.recordedLists[0]
			else:
				loc = self.getLocationofNode(parent)
				for item in self.recordedLists:
					if item["location"] == loc and item["scope"]:
						return item
				

	def traverseNode(self, node=None):
		node = node == None and self.parsedAst or node
		if node["type"] == "FunctionDeclaration" or node["type"] == "MethodDefinition" :
			self.visitFunctionDeclaration(node)
		elif node["type"] == "ClassDeclaration":
			self.visitClassDeclaration(node)
		elif node["type"] == "VariableDeclaration":
			for var in node["declarations"]:
				self.visitVariableDeclaration(var)
		elif node["type"] == "MemberExpression":
			self.visitMemberExpression(node)
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
