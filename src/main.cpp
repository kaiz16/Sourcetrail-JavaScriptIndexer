#include <cstdlib>
#include <fstream>
#include <iostream>
#include "nlohmann/json.hpp"
#include "SourcetrailDBWriter.h"
using json = nlohmann::json;
void findAndReplaceAll(std::string &data, const std::string &toSearch, const std::string &replaceStr)
{
	size_t pos = data.find(toSearch);

	while (pos != std::string::npos)
	{
		data.replace(pos, toSearch.size(), replaceStr);
		pos = data.find(toSearch, pos + replaceStr.size());
	}
}

int main(int argc, const char *argv[])
{
	sourcetrail::SourcetrailDBWriter dbWriter;

	std::cout << "\nSourcetrailDB JavaScript Indexer" << std::endl;
	std::cout << std::endl;
	std::cout << "SourcetrailDB version: " << dbWriter.getVersionString() << std::endl;
	std::cout << "Supported database version: " << dbWriter.getSupportedDatabaseVersion() << std::endl;
	std::cout << std::endl;

	std::string dbPath = argv[1];
	std::string sourcePath = argv[2];
	findAndReplaceAll(sourcePath, "\\", "/");

	int dbVersion = 0;
	if (argc == 4)
	{
		char* end;
		dbVersion = strtol(argv[3], &end, 10);
	}

	if (dbVersion && dbVersion != dbWriter.getSupportedDatabaseVersion())
	{
		std::cerr << "error: binary only supports database version: " << dbWriter.getSupportedDatabaseVersion()
			<< ". Requested version: " << dbVersion << std::endl;
		return 1;
	}

	// open database by passing .srctrldb or .srctrldb_tmp path
	std::cout << "Opening Database: " << dbPath << std::endl;
	if (!dbWriter.open(dbPath))
	{
		std::cerr << "error: " << dbWriter.getLastError() << std::endl;
		return 1;
	}

	std::cout << "Clearing Database... " << std::endl;
	if (!dbWriter.clear())
	{
		std::cerr << "error: " << dbWriter.getLastError() << std::endl;
		return 1;
	}

	std::cout << "Starting Indexing..." << std::endl;

	// start recording with faster speed
	if (!dbWriter.beginTransaction())
	{
		std::cerr << "error: " << dbWriter.getLastError() << std::endl;
		return 1;
	}

	// record source file by passing it's absolute path
	int fileId = dbWriter.recordFile(sourcePath);
	dbWriter.recordFileLanguage(fileId, "js"); // record file language for syntax highlighting

    std::ifstream input("test.json");
    for (std::string line; std::getline(input, line);){
		
		std::string j3 = line;
		auto j4 = json::parse(j3);
		for (auto x : j4.items()){
				for (auto y: x.value().items()){
					if (y.key() == "type" && y.value() == "FunctionDeclaration") {
						sourcetrail::NameHierarchy foo { "::", { { "", y.value(), "" }, { "function", "foo", "()" } } };
						int symbolId = dbWriter.recordSymbol(foo);
					}
					
						// sourcetrail::NameHierarchy foo { "::", { { "", "Foo", "" }, { "function", "foo", "()" } } };
						// int symbolId = dbWriter.recordSymbol(foo);
				}
			}
    }

	// end recording
	if (!dbWriter.commitTransaction())
	{
		std::cerr << "error: " << dbWriter.getLastError() << std::endl;
		return 1;
	}

	// check for errors before finishing
	if (dbWriter.getLastError().size())
	{
		std::cerr << "error: " << dbWriter.getLastError() << std::endl;
		return 1;
	}

	std::cout << "done!" << std::endl;

	return 0;
}