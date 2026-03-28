// Copyright 2026 Divinity Alpha. All Rights Reserved.
#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"

class UDataTable;
class UUserDefinedStruct;

/**
 * Creates UDataTable + UUserDefinedStruct assets from DT IR JSON.
 * Called by the TCP command server for create_data_table and
 * get_data_table_info commands.
 */
class FDataTableBuilder
{
public:
	struct FDTBuildResult
	{
		bool bSuccess = false;
		FString ErrorMessage;
		FString TableAssetPath;
		FString StructAssetPath;
		int32 ColumnCount = 0;
		int32 RowCount = 0;
	};

	/**
	 * Create a DataTable + UserDefinedStruct from parsed IR JSON.
	 * @param IRJson - The root IR object (metadata, columns, rows)
	 * @param PackagePath - Content Browser path (e.g. "/Game/Arcwright/DataTables")
	 * @return Build result with asset paths and counts
	 */
	static FDTBuildResult CreateFromIR(const TSharedPtr<FJsonObject>& IRJson, const FString& PackagePath);

	/**
	 * Query an existing DataTable asset.
	 * @param Name - Asset name (e.g. "DT_Weapons")
	 * @return JSON object with table info, or nullptr if not found
	 */
	static TSharedPtr<FJsonObject> GetDataTableInfo(const FString& Name);

private:
	// Struct creation
	static UUserDefinedStruct* CreateOrFindStruct(
		const FString& StructName,
		const TArray<TSharedPtr<FJsonValue>>& Columns,
		const FString& PackagePath,
		FString& OutError);

	// Row population
	static bool PopulateRows(
		UDataTable* Table,
		UUserDefinedStruct* RowStruct,
		const TArray<TSharedPtr<FJsonValue>>& Columns,
		const TArray<TSharedPtr<FJsonValue>>& Rows,
		FString& OutError);

	// Type mapping
	static FName ResolvePropertyType(const FString& DTType);

	// Helpers
	static UDataTable* FindDataTableByName(const FString& Name);
};
