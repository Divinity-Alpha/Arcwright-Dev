// Copyright 2026 Divinity Alpha. All Rights Reserved.
#include "DataTableBuilder.h"
#include "SafeSavePackage.h"
#include "Engine/DataTable.h"
#include "Engine/UserDefinedStruct.h"
#include "UserDefinedStructure/UserDefinedStructEditorData.h"
#include "Kismet2/StructureEditorUtils.h"
#include "AssetRegistry/AssetRegistryModule.h"
// UObject/SavePackage.h included via SafeSavePackage.h
#include "Dom/JsonValue.h"
#include "EdGraphSchema_K2.h"
#include "Misc/PackageName.h"
#include "AssetRegistry/AssetData.h"

DEFINE_LOG_CATEGORY_STATIC(LogDTBuilder, Log, All);

// ============================================================
// Type mapping: DT DSL types -> UE property types
// ============================================================

FName FDataTableBuilder::ResolvePropertyType(const FString& DTType)
{
	// Map DT DSL type names to UE FProperty type names
	if (DTType.Equals(TEXT("String"), ESearchCase::IgnoreCase))
		return TEXT("StrProperty");
	if (DTType.Equals(TEXT("Text"), ESearchCase::IgnoreCase))
		return TEXT("TextProperty");
	if (DTType.Equals(TEXT("Float"), ESearchCase::IgnoreCase))
		return TEXT("DoubleProperty"); // UE 5.x uses double internally
	if (DTType.Equals(TEXT("Int"), ESearchCase::IgnoreCase))
		return TEXT("IntProperty");
	if (DTType.Equals(TEXT("Bool"), ESearchCase::IgnoreCase))
		return TEXT("BoolProperty");
	if (DTType.Equals(TEXT("Name"), ESearchCase::IgnoreCase))
		return TEXT("NameProperty");
	if (DTType.Equals(TEXT("Vector"), ESearchCase::IgnoreCase))
		return TEXT("StructProperty"); // FVector
	if (DTType.Equals(TEXT("Rotator"), ESearchCase::IgnoreCase))
		return TEXT("StructProperty"); // FRotator
	if (DTType.Equals(TEXT("Color"), ESearchCase::IgnoreCase))
		return TEXT("StructProperty"); // FLinearColor
	if (DTType.Equals(TEXT("SoftObjectPath"), ESearchCase::IgnoreCase))
		return TEXT("SoftObjectProperty");

	UE_LOG(LogDTBuilder, Warning, TEXT("Unknown DT type: %s — defaulting to String"), *DTType);
	return TEXT("StrProperty");
}

// ============================================================
// CreateOrFindStruct
// ============================================================

UUserDefinedStruct* FDataTableBuilder::CreateOrFindStruct(
	const FString& StructName,
	const TArray<TSharedPtr<FJsonValue>>& Columns,
	const FString& PackagePath,
	FString& OutError)
{
	FString FullPath = PackagePath / StructName;

	// Check if struct already exists — delete it
	FString AssetPath = FString::Printf(TEXT("%s.%s"), *FullPath, *StructName);
	UUserDefinedStruct* ExistingStruct = LoadObject<UUserDefinedStruct>(nullptr, *AssetPath);
	if (ExistingStruct)
	{
		UE_LOG(LogDTBuilder, Log, TEXT("Deleting existing struct: %s"), *StructName);
		// Can't easily delete — we'll reuse it by removing all existing variables
		TArray<FGuid> ExistingGuids;
		for (const FStructVariableDescription& Var : FStructureEditorUtils::GetVarDesc(ExistingStruct))
		{
			ExistingGuids.Add(Var.VarGuid);
		}
		for (const FGuid& Guid : ExistingGuids)
		{
			FStructureEditorUtils::RemoveVariable(ExistingStruct, Guid);
		}
	}

	UUserDefinedStruct* Struct = ExistingStruct;

	if (!Struct)
	{
		// Create new UUserDefinedStruct
		UPackage* Package = CreatePackage(*FullPath);
		if (!Package)
		{
			OutError = FString::Printf(TEXT("Failed to create package: %s"), *FullPath);
			return nullptr;
		}

		Struct = FStructureEditorUtils::CreateUserDefinedStruct(
			Package, FName(*StructName), RF_Public | RF_Standalone);

		if (!Struct)
		{
			OutError = FString::Printf(TEXT("Failed to create UUserDefinedStruct: %s"), *StructName);
			return nullptr;
		}

		UE_LOG(LogDTBuilder, Log, TEXT("Created struct: %s"), *StructName);

		// Remember default MemberVar GUIDs — remove AFTER adding real columns
		// (UE won't let you remove the last variable from a struct)
	}

	// Track default vars to remove after we add real columns
	TArray<FGuid> DefaultGuids;
	for (const FStructVariableDescription& Var : FStructureEditorUtils::GetVarDesc(Struct))
	{
		DefaultGuids.Add(Var.VarGuid);
	}

	// PASS 1: Add all columns (with default MemberVar names) and collect info
	struct FColumnInfo
	{
		FString Name;
		FString TypeName;
		TSharedPtr<FJsonObject> ColJson;
	};
	TArray<FColumnInfo> ColumnInfos;

	for (const TSharedPtr<FJsonValue>& ColVal : Columns)
	{
		TSharedPtr<FJsonObject> Col = ColVal->AsObject();
		if (!Col.IsValid()) continue;

		FString ColName = Col->GetStringField(TEXT("name"));
		TSharedPtr<FJsonObject> TypeObj = Col->GetObjectField(TEXT("type"));
		FString TypeName = TypeObj.IsValid() ? TypeObj->GetStringField(TEXT("name")) : TEXT("String");

		FEdGraphPinType PinType;

		if (TypeName.Equals(TEXT("String"), ESearchCase::IgnoreCase) ||
			TypeName.Equals(TEXT("Text"), ESearchCase::IgnoreCase) ||
			TypeName.Equals(TEXT("Name"), ESearchCase::IgnoreCase))
		{
			if (TypeName.Equals(TEXT("Text"), ESearchCase::IgnoreCase))
				PinType.PinCategory = UEdGraphSchema_K2::PC_Text;
			else if (TypeName.Equals(TEXT("Name"), ESearchCase::IgnoreCase))
				PinType.PinCategory = UEdGraphSchema_K2::PC_Name;
			else
				PinType.PinCategory = UEdGraphSchema_K2::PC_String;
		}
		else if (TypeName.Equals(TEXT("Float"), ESearchCase::IgnoreCase))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_Real;
			PinType.PinSubCategory = UEdGraphSchema_K2::PC_Double;
		}
		else if (TypeName.Equals(TEXT("Int"), ESearchCase::IgnoreCase))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_Int;
		}
		else if (TypeName.Equals(TEXT("Bool"), ESearchCase::IgnoreCase))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
		}
		else if (TypeName.Equals(TEXT("Vector"), ESearchCase::IgnoreCase))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
			PinType.PinSubCategoryObject = TBaseStructure<FVector>::Get();
		}
		else if (TypeName.Equals(TEXT("Rotator"), ESearchCase::IgnoreCase))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
			PinType.PinSubCategoryObject = TBaseStructure<FRotator>::Get();
		}
		else if (TypeName.Equals(TEXT("Color"), ESearchCase::IgnoreCase))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
			PinType.PinSubCategoryObject = TBaseStructure<FLinearColor>::Get();
		}
		else if (TypeName.Equals(TEXT("SoftObjectPath"), ESearchCase::IgnoreCase))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_SoftObject;
		}
		else
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_String;
			UE_LOG(LogDTBuilder, Warning, TEXT("Unknown DT column type '%s' for column '%s' — using String"),
				*TypeName, *ColName);
		}

		bool bResult = FStructureEditorUtils::AddVariable(Struct, PinType);
		if (!bResult)
		{
			UE_LOG(LogDTBuilder, Warning, TEXT("Failed to add variable for column '%s'"), *ColName);
			continue;
		}

		FColumnInfo Info;
		Info.Name = ColName;
		Info.TypeName = TypeName;
		Info.ColJson = Col;
		ColumnInfos.Add(Info);
	}

	// Remove default MemberVar(s) — now safe because we have real columns
	for (const FGuid& Guid : DefaultGuids)
	{
		FStructureEditorUtils::RemoveVariable(Struct, Guid);
	}

	// PASS 2: Rename variables and set defaults
	// After removing defaults, remaining vars are our added columns in order
	const TArray<FStructVariableDescription>& FinalVarDescs = FStructureEditorUtils::GetVarDesc(Struct);
	for (int32 i = 0; i < FinalVarDescs.Num() && i < ColumnInfos.Num(); i++)
	{
		const FGuid& VarGuid = FinalVarDescs[i].VarGuid;
		const FString& ColName = ColumnInfos[i].Name;

		FStructureEditorUtils::RenameVariable(Struct, VarGuid, ColName);
		UE_LOG(LogDTBuilder, Log, TEXT("  Column: %s (%s) [renamed from %s]"),
			*ColName, *ColumnInfos[i].TypeName, *FinalVarDescs[i].FriendlyName);

		// Set default value if present
		TSharedPtr<FJsonObject> Col = ColumnInfos[i].ColJson;
		if (Col->HasField(TEXT("default")))
		{
			TSharedPtr<FJsonValue> DefaultVal = Col->TryGetField(TEXT("default"));
			if (DefaultVal.IsValid() && !DefaultVal->IsNull())
			{
				FString DefaultStr;
				if (DefaultVal->Type == EJson::String)
					DefaultStr = DefaultVal->AsString();
				else if (DefaultVal->Type == EJson::Number)
					DefaultStr = FString::SanitizeFloat(DefaultVal->AsNumber());
				else if (DefaultVal->Type == EJson::Boolean)
					DefaultStr = DefaultVal->AsBool() ? TEXT("true") : TEXT("false");

				if (!DefaultStr.IsEmpty())
				{
					FStructureEditorUtils::ChangeVariableDefaultValue(Struct, VarGuid, DefaultStr);
				}
			}
		}
	}

	// Compile the struct
	Struct->Status = UDSS_UpToDate;
	FStructureEditorUtils::CompileStructure(Struct);

	// Save the struct package
	UPackage* StructPackage = Struct->GetOutermost();
	StructPackage->MarkPackageDirty();

	FString StructFilePath = FPackageName::LongPackageNameToFilename(FullPath, FPackageName::GetAssetPackageExtension());
	FSavePackageArgs SaveArgs;
	SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
	SafeSavePackage(StructPackage, Struct, StructFilePath, SaveArgs);

	UE_LOG(LogDTBuilder, Log, TEXT("Struct saved: %s (%d columns)"), *StructName, Columns.Num());

	return Struct;
}

// ============================================================
// PopulateRows
// ============================================================

bool FDataTableBuilder::PopulateRows(
	UDataTable* Table,
	UUserDefinedStruct* RowStruct,
	const TArray<TSharedPtr<FJsonValue>>& Columns,
	const TArray<TSharedPtr<FJsonValue>>& Rows,
	FString& OutError)
{
	if (!Table || !RowStruct)
	{
		OutError = TEXT("Null table or struct");
		return false;
	}

	// Build column info from IR
	TArray<FString> ColumnNames;
	TArray<FString> ColumnTypes;
	for (const TSharedPtr<FJsonValue>& ColVal : Columns)
	{
		TSharedPtr<FJsonObject> Col = ColVal->AsObject();
		if (Col.IsValid())
		{
			ColumnNames.Add(Col->GetStringField(TEXT("name")));
			TSharedPtr<FJsonObject> TypeObj = Col->GetObjectField(TEXT("type"));
			ColumnTypes.Add(TypeObj.IsValid() ? TypeObj->GetStringField(TEXT("name")) : TEXT("String"));
		}
	}

	// Build friendly name → internal property name map
	// UUserDefinedStruct properties have GUID-suffixed names internally
	// Match by position: VarDescs and properties are in the same order
	TMap<FString, FString> FriendlyToInternal;
	{
		const TArray<FStructVariableDescription>& VarDescs = FStructureEditorUtils::GetVarDesc(RowStruct);
		int32 PropIdx = 0;
		for (TFieldIterator<FProperty> PropIt(RowStruct); PropIt; ++PropIt, ++PropIdx)
		{
			if (PropIdx < VarDescs.Num())
			{
				FriendlyToInternal.Add(VarDescs[PropIdx].FriendlyName, (*PropIt)->GetName());
				UE_LOG(LogDTBuilder, Log, TEXT("  Property map: %s → %s"), *VarDescs[PropIdx].FriendlyName, *(*PropIt)->GetName());
			}
		}
	}

	// Build a JSON string that UDataTable::CreateTableFromJSONString can parse
	FString JSONString = TEXT("[");
	bool bFirst = true;

	for (const TSharedPtr<FJsonValue>& RowVal : Rows)
	{
		TSharedPtr<FJsonObject> Row = RowVal->AsObject();
		if (!Row.IsValid()) continue;

		FString RowName = Row->GetStringField(TEXT("name"));
		TSharedPtr<FJsonObject> Values = Row->GetObjectField(TEXT("values"));
		if (!Values.IsValid()) continue;

		if (!bFirst) JSONString += TEXT(",");
		bFirst = false;

		JSONString += TEXT("{");
		JSONString += FString::Printf(TEXT("\"Name\":\"%s\""), *RowName);

		for (int32 i = 0; i < ColumnNames.Num(); i++)
		{
			const FString& ColName = ColumnNames[i];
			const FString& ColType = ColumnTypes[i];

			// Use internal property name for JSON key
			FString JsonKey = ColName;
			if (FriendlyToInternal.Contains(ColName))
			{
				JsonKey = FriendlyToInternal[ColName];
			}

			JSONString += TEXT(",");

			if (Values->HasField(ColName))
			{
				TSharedPtr<FJsonValue> Val = Values->TryGetField(ColName);
				if (Val.IsValid())
				{
					if (ColType.Equals(TEXT("String"), ESearchCase::IgnoreCase) ||
						ColType.Equals(TEXT("Text"), ESearchCase::IgnoreCase) ||
						ColType.Equals(TEXT("Name"), ESearchCase::IgnoreCase))
					{
						FString StrVal = Val->AsString();
						StrVal = StrVal.Replace(TEXT("\""), TEXT("\\\""));
						JSONString += FString::Printf(TEXT("\"%s\":\"%s\""), *JsonKey, *StrVal);
					}
					else if (ColType.Equals(TEXT("Bool"), ESearchCase::IgnoreCase))
					{
						bool bVal = Val->AsBool();
						JSONString += FString::Printf(TEXT("\"%s\":%s"), *JsonKey, bVal ? TEXT("true") : TEXT("false"));
					}
					else
					{
						double NumVal = Val->AsNumber();
						if (ColType.Equals(TEXT("Int"), ESearchCase::IgnoreCase))
						{
							JSONString += FString::Printf(TEXT("\"%s\":%d"), *JsonKey, (int32)NumVal);
						}
						else
						{
							JSONString += FString::Printf(TEXT("\"%s\":%f"), *JsonKey, NumVal);
						}
					}
				}
			}
		}

		JSONString += TEXT("}");
	}

	JSONString += TEXT("]");

	// Use the JSON import
	TArray<FString> ImportErrors = Table->CreateTableFromJSONString(JSONString);

	if (ImportErrors.Num() > 0)
	{
		for (const FString& Err : ImportErrors)
		{
			UE_LOG(LogDTBuilder, Warning, TEXT("DataTable JSON import: %s"), *Err);
		}
	}

	UE_LOG(LogDTBuilder, Log, TEXT("Populated %d rows in DataTable"), Table->GetRowMap().Num());
	return true;
}

// ============================================================
// CreateFromIR
// ============================================================

FDataTableBuilder::FDTBuildResult FDataTableBuilder::CreateFromIR(
	const TSharedPtr<FJsonObject>& IRJson,
	const FString& PackagePath)
{
	FDTBuildResult Result;

	if (!IRJson.IsValid())
	{
		Result.ErrorMessage = TEXT("Invalid IR JSON");
		return Result;
	}

	// Parse metadata
	TSharedPtr<FJsonObject> Metadata = IRJson->GetObjectField(TEXT("metadata"));
	if (!Metadata.IsValid())
	{
		Result.ErrorMessage = TEXT("Missing metadata in IR");
		return Result;
	}

	FString TableName = Metadata->GetStringField(TEXT("table_name"));
	FString StructName = Metadata->GetStringField(TEXT("struct_name"));

	if (TableName.IsEmpty() || StructName.IsEmpty())
	{
		Result.ErrorMessage = TEXT("Missing table_name or struct_name in metadata");
		return Result;
	}

	// Get columns and rows
	const TArray<TSharedPtr<FJsonValue>>* ColumnsPtr = nullptr;
	const TArray<TSharedPtr<FJsonValue>>* RowsPtr = nullptr;

	if (!IRJson->TryGetArrayField(TEXT("columns"), ColumnsPtr) || ColumnsPtr->Num() == 0)
	{
		Result.ErrorMessage = TEXT("No columns defined in IR");
		return Result;
	}

	IRJson->TryGetArrayField(TEXT("rows"), RowsPtr);

	UE_LOG(LogDTBuilder, Log, TEXT("Creating DataTable: %s (struct: %s, %d columns, %d rows)"),
		*TableName, *StructName, ColumnsPtr->Num(), RowsPtr ? RowsPtr->Num() : 0);

	// Step 1: Create the struct
	FString StructError;
	UUserDefinedStruct* RowStruct = CreateOrFindStruct(StructName, *ColumnsPtr, PackagePath, StructError);
	if (!RowStruct)
	{
		Result.ErrorMessage = FString::Printf(TEXT("Failed to create struct: %s"), *StructError);
		return Result;
	}

	// Step 2: Create the DataTable
	FString TableFullPath = PackagePath / TableName;
	FString TableAssetPath = FString::Printf(TEXT("%s.%s"), *TableFullPath, *TableName);

	// Delete existing DataTable if it exists
	UDataTable* ExistingTable = LoadObject<UDataTable>(nullptr, *TableAssetPath);
	if (ExistingTable)
	{
		UE_LOG(LogDTBuilder, Log, TEXT("Deleting existing DataTable: %s"), *TableName);
		ExistingTable->EmptyTable();
		// Reset the row struct reference
	}

	UDataTable* Table = ExistingTable;

	if (!Table)
	{
		UPackage* TablePackage = CreatePackage(*TableFullPath);
		if (!TablePackage)
		{
			Result.ErrorMessage = FString::Printf(TEXT("Failed to create package: %s"), *TableFullPath);
			return Result;
		}

		Table = NewObject<UDataTable>(TablePackage, FName(*TableName), RF_Public | RF_Standalone);
		if (!Table)
		{
			Result.ErrorMessage = FString::Printf(TEXT("Failed to create DataTable: %s"), *TableName);
			return Result;
		}
	}

	// Set the row struct
	Table->RowStruct = RowStruct;

	// Step 3: Populate rows
	if (RowsPtr && RowsPtr->Num() > 0)
	{
		FString PopError;
		if (!PopulateRows(Table, RowStruct, *ColumnsPtr, *RowsPtr, PopError))
		{
			UE_LOG(LogDTBuilder, Warning, TEXT("Row population issues: %s"), *PopError);
			// Continue — partial data is better than none
		}
	}

	// Save the DataTable
	UPackage* TablePackage = Table->GetOutermost();
	TablePackage->MarkPackageDirty();

	FString TableFilePath = FPackageName::LongPackageNameToFilename(TableFullPath, FPackageName::GetAssetPackageExtension());
	FSavePackageArgs SaveArgs;
	SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
	SafeSavePackage(TablePackage, Table, TableFilePath, SaveArgs);

	UE_LOG(LogDTBuilder, Log, TEXT("DataTable saved: %s (%d columns, %d rows)"),
		*TableName, ColumnsPtr->Num(), Table->GetRowMap().Num());

	// Build result
	Result.bSuccess = true;
	Result.TableAssetPath = TableFullPath;
	Result.StructAssetPath = PackagePath / StructName;
	Result.ColumnCount = ColumnsPtr->Num();
	Result.RowCount = Table->GetRowMap().Num();

	return Result;
}

// ============================================================
// FindDataTableByName
// ============================================================

UDataTable* FDataTableBuilder::FindDataTableByName(const FString& Name)
{
	// Try our default location first
	FString AssetPath = FString::Printf(TEXT("/Game/Arcwright/DataTables/%s.%s"), *Name, *Name);
	UDataTable* Table = LoadObject<UDataTable>(nullptr, *AssetPath);
	if (Table) return Table;

	// Try asset registry search
	FAssetRegistryModule& ARModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	IAssetRegistry& AR = ARModule.Get();

	TArray<FAssetData> Assets;
	AR.GetAssetsByClass(UDataTable::StaticClass()->GetClassPathName(), Assets);

	for (const FAssetData& Asset : Assets)
	{
		if (Asset.AssetName.ToString() == Name)
		{
			return Cast<UDataTable>(Asset.GetAsset());
		}
	}

	return nullptr;
}

// ============================================================
// GetDataTableInfo
// ============================================================

TSharedPtr<FJsonObject> FDataTableBuilder::GetDataTableInfo(const FString& Name)
{
	UDataTable* Table = FindDataTableByName(Name);
	if (!Table) return nullptr;

	TSharedPtr<FJsonObject> Info = MakeShareable(new FJsonObject());
	Info->SetStringField(TEXT("name"), Name);
	Info->SetStringField(TEXT("asset_path"), Table->GetPathName());

	// Row struct info
	UScriptStruct* RowStruct = Table->RowStruct;
	if (RowStruct)
	{
		Info->SetStringField(TEXT("struct_name"), RowStruct->GetName());

		// Columns from struct properties — use FriendlyName for UUserDefinedStruct
		TArray<TSharedPtr<FJsonValue>> ColumnsArray;
		UUserDefinedStruct* UDS = Cast<UUserDefinedStruct>(RowStruct);
		if (UDS)
		{
			// UUserDefinedStruct: use variable descriptions for friendly names
			for (const FStructVariableDescription& VarDesc : FStructureEditorUtils::GetVarDesc(UDS))
			{
				TSharedPtr<FJsonObject> ColObj = MakeShareable(new FJsonObject());
				ColObj->SetStringField(TEXT("name"), VarDesc.FriendlyName);
				ColObj->SetStringField(TEXT("type"), VarDesc.Category.ToString());
				ColumnsArray.Add(MakeShareable(new FJsonValueObject(ColObj)));
			}
		}
		else
		{
			// Native struct: use property names directly
			for (TFieldIterator<FProperty> PropIt(RowStruct); PropIt; ++PropIt)
			{
				FProperty* Prop = *PropIt;
				TSharedPtr<FJsonObject> ColObj = MakeShareable(new FJsonObject());
				ColObj->SetStringField(TEXT("name"), Prop->GetName());
				ColObj->SetStringField(TEXT("type"), Prop->GetCPPType());
				ColumnsArray.Add(MakeShareable(new FJsonValueObject(ColObj)));
			}
		}
		Info->SetArrayField(TEXT("columns"), ColumnsArray);
		Info->SetNumberField(TEXT("column_count"), ColumnsArray.Num());
	}

	// Row info
	TArray<FName> RowNames = Table->GetRowNames();
	Info->SetNumberField(TEXT("row_count"), RowNames.Num());

	TArray<TSharedPtr<FJsonValue>> RowNamesArray;
	for (const FName& RN : RowNames)
	{
		RowNamesArray.Add(MakeShareable(new FJsonValueString(RN.ToString())));
	}
	Info->SetArrayField(TEXT("row_names"), RowNamesArray);

	return Info;
}
