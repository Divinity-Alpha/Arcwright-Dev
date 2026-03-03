#include "CommandServer.h"
#include "DSLImporter.h"
#include "BlueprintBuilder.h"

#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

#include "Engine/Blueprint.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "EdGraphSchema_K2.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "ObjectTools.h"
#include "Misc/FileHelper.h"
#include "Async/Async.h"
#include "SocketSubsystem.h"

DEFINE_LOG_CATEGORY(LogBlueprintLLM);

const FString FCommandServer::SERVER_VERSION = TEXT("1.0");

// ============================================================
// Lifecycle
// ============================================================

FCommandServer::FCommandServer()
{
}

FCommandServer::~FCommandServer()
{
	Stop();
}

bool FCommandServer::Start(int32 Port)
{
	if (bRunning)
	{
		UE_LOG(LogBlueprintLLM, Warning, TEXT("Command server already running"));
		return true;
	}

	FIPv4Endpoint Endpoint(FIPv4Address(127, 0, 0, 1), Port);

	Listener = new FTcpListener(Endpoint, FTimespan::FromSeconds(1.0), false);
	Listener->OnConnectionAccepted().BindRaw(this, &FCommandServer::OnConnectionAccepted);

	if (!Listener->Init())
	{
		UE_LOG(LogBlueprintLLM, Error, TEXT("Failed to bind TCP listener on port %d"), Port);
		delete Listener;
		Listener = nullptr;
		return false;
	}

	bRunning = true;
	UE_LOG(LogBlueprintLLM, Log, TEXT("BlueprintLLM Command Server listening on port %d"), Port);
	return true;
}

void FCommandServer::Stop()
{
	bRunning = false;

	if (Listener)
	{
		delete Listener;
		Listener = nullptr;
	}

	FScopeLock Lock(&ClientsMutex);
	for (FSocket* Client : ActiveClients)
	{
		Client->Close();
		ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Client);
	}
	ActiveClients.Empty();

	UE_LOG(LogBlueprintLLM, Log, TEXT("BlueprintLLM Command Server stopped"));
}

// ============================================================
// Connection handling
// ============================================================

bool FCommandServer::OnConnectionAccepted(FSocket* ClientSocket, const FIPv4Endpoint& ClientEndpoint)
{
	if (!bRunning)
	{
		return false;
	}

	UE_LOG(LogBlueprintLLM, Log, TEXT("Client connected: %s"), *ClientEndpoint.ToString());

	{
		FScopeLock Lock(&ClientsMutex);
		ActiveClients.Add(ClientSocket);
	}

	// Process on a background thread
	Async(EAsyncExecution::Thread, [this, ClientSocket]()
	{
		ProcessClient(ClientSocket);

		// Cleanup
		{
			FScopeLock Lock(&ClientsMutex);
			ActiveClients.Remove(ClientSocket);
		}
		ClientSocket->Close();
		ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(ClientSocket);

		UE_LOG(LogBlueprintLLM, Log, TEXT("Client disconnected"));
	});

	return true;
}

void FCommandServer::ProcessClient(FSocket* ClientSocket)
{
	while (bRunning)
	{
		FString Line = ReadLine(ClientSocket);
		if (Line.IsEmpty())
		{
			break; // Connection closed or error
		}

		UE_LOG(LogBlueprintLLM, Log, TEXT("Received: %s"), *Line);

		// Parse JSON
		TSharedPtr<FJsonObject> JsonMsg;
		TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Line);
		if (!FJsonSerializer::Deserialize(Reader, JsonMsg) || !JsonMsg.IsValid())
		{
			SendResponse(ClientSocket, FCommandResult::Error(TEXT("Invalid JSON")));
			continue;
		}

		FString Command = JsonMsg->GetStringField(TEXT("command"));
		TSharedPtr<FJsonObject> Params = JsonMsg->GetObjectField(TEXT("params"));
		if (!Params.IsValid())
		{
			Params = MakeShareable(new FJsonObject());
		}

		if (Command.IsEmpty())
		{
			SendResponse(ClientSocket, FCommandResult::Error(TEXT("Missing 'command' field")));
			continue;
		}

		// Dispatch on game thread and wait for result
		FCommandResult Result;
		FEvent* DoneEvent = FPlatformProcess::GetSynchEventFromPool(true);

		AsyncTask(ENamedThreads::GameThread, [this, &Result, &Command, &Params, DoneEvent]()
		{
			Result = DispatchCommand(Command, Params);
			DoneEvent->Trigger();
		});

		DoneEvent->Wait();
		FPlatformProcess::ReturnSynchEventToPool(DoneEvent);

		UE_LOG(LogBlueprintLLM, Log, TEXT("Response: %s — %s"),
			Result.bSuccess ? TEXT("ok") : TEXT("error"),
			Result.bSuccess ? TEXT("success") : *Result.ErrorMessage);

		SendResponse(ClientSocket, Result);
	}
}

FString FCommandServer::ReadLine(FSocket* Socket)
{
	TArray<uint8> Buffer;
	uint8 Byte;
	int32 BytesRead;

	while (bRunning)
	{
		// Wait for data with timeout
		if (!Socket->Wait(ESocketWaitConditions::WaitForRead, FTimespan::FromSeconds(1.0)))
		{
			// Check if socket is still connected
			ESocketConnectionState State = Socket->GetConnectionState();
			if (State != ESocketConnectionState::SCS_Connected)
			{
				return FString();
			}
			continue;
		}

		if (!Socket->Recv(&Byte, 1, BytesRead))
		{
			return FString();
		}

		if (BytesRead == 0)
		{
			return FString();
		}

		if (Byte == '\n')
		{
			break;
		}

		Buffer.Add(Byte);
	}

	if (Buffer.Num() == 0)
	{
		return FString();
	}

	// Convert to FString (UTF-8)
	Buffer.Add(0); // Null terminate
	return FString(UTF8_TO_TCHAR(Buffer.GetData()));
}

void FCommandServer::SendResponse(FSocket* Socket, const FCommandResult& Result)
{
	TSharedPtr<FJsonObject> ResponseJson = MakeShareable(new FJsonObject());

	if (Result.bSuccess)
	{
		ResponseJson->SetStringField(TEXT("status"), TEXT("ok"));
		if (Result.Data.IsValid())
		{
			ResponseJson->SetObjectField(TEXT("data"), Result.Data);
		}
		else
		{
			ResponseJson->SetObjectField(TEXT("data"), MakeShareable(new FJsonObject()));
		}
	}
	else
	{
		ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
		ResponseJson->SetStringField(TEXT("message"), Result.ErrorMessage);
	}

	FString ResponseStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
		TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&ResponseStr);
	FJsonSerializer::Serialize(ResponseJson.ToSharedRef(), Writer);

	ResponseStr += TEXT("\n");

	FTCHARToUTF8 Converter(*ResponseStr);
	int32 BytesSent;
	Socket->Send((const uint8*)Converter.Get(), Converter.Length(), BytesSent);
}

// ============================================================
// Command dispatch
// ============================================================

FCommandResult FCommandServer::DispatchCommand(const FString& Command, const TSharedPtr<FJsonObject>& Params)
{
	if (Command == TEXT("health_check"))
	{
		return HandleHealthCheck(Params);
	}
	if (Command == TEXT("import_from_ir"))
	{
		return HandleImportFromIR(Params);
	}
	if (Command == TEXT("get_blueprint_info"))
	{
		return HandleGetBlueprintInfo(Params);
	}
	if (Command == TEXT("compile_blueprint"))
	{
		return HandleCompileBlueprint(Params);
	}
	if (Command == TEXT("delete_blueprint"))
	{
		return HandleDeleteBlueprint(Params);
	}

	return FCommandResult::Error(FString::Printf(TEXT("Unknown command: %s"), *Command));
}

// ============================================================
// Command handlers
// ============================================================

FCommandResult FCommandServer::HandleHealthCheck(const TSharedPtr<FJsonObject>& Params)
{
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("server"), TEXT("BlueprintLLM"));
	Data->SetStringField(TEXT("version"), SERVER_VERSION);
	Data->SetStringField(TEXT("engine"), TEXT("UnrealEngine"));
	Data->SetStringField(TEXT("engine_version"), *FEngineVersion::Current().ToString());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleImportFromIR(const TSharedPtr<FJsonObject>& Params)
{
	FString IRPath = Params->GetStringField(TEXT("path"));
	if (IRPath.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'path' parameter"));
	}

	// Normalize path separators
	IRPath.ReplaceInline(TEXT("/"), TEXT("\\"));

	if (!FPaths::FileExists(IRPath))
	{
		return FCommandResult::Error(FString::Printf(TEXT("File not found: %s"), *IRPath));
	}

	// Parse the IR file
	FDSLBlueprint DSL;
	if (!FDSLImporter::ParseIR(IRPath, DSL))
	{
		return FCommandResult::Error(FString::Printf(TEXT("Failed to parse IR: %s"), *IRPath));
	}

	// Delete existing Blueprint with same name (Strategic Rule 8)
	DeleteExistingBlueprint(DSL.Name);

	// Build the Blueprint — SAME code path as the Tools menu import
	const FString PackagePath = TEXT("/Game/BlueprintLLM/Generated");
	UBlueprint* NewBP = FBlueprintBuilder::CreateBlueprint(DSL, PackagePath);

	if (!NewBP)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Failed to build Blueprint: %s"), *DSL.Name));
	}

	// Count actual nodes created in the graph
	int32 NodesCreated = 0;
	int32 ConnectionsWired = 0;
	UEdGraph* EventGraph = FBlueprintEditorUtils::FindEventGraph(NewBP);
	if (EventGraph)
	{
		NodesCreated = EventGraph->Nodes.Num();
		for (UEdGraphNode* Node : EventGraph->Nodes)
		{
			for (UEdGraphPin* Pin : Node->Pins)
			{
				if (Pin->Direction == EGPD_Output)
				{
					ConnectionsWired += Pin->LinkedTo.Num();
				}
			}
		}
	}

	// Check compilation status
	bool bCompiled = NewBP->Status != BS_Error;
	TArray<TSharedPtr<FJsonValue>> CompileErrors;
	if (NewBP->Status == BS_Error)
	{
		// Collect any compile messages
		for (UEdGraph* Graph : NewBP->UbergraphPages)
		{
			for (UEdGraphNode* Node : Graph->Nodes)
			{
				if (Node->bHasCompilerMessage)
				{
					CompileErrors.Add(MakeShareable(new FJsonValueString(
						FString::Printf(TEXT("Node %s: compiler error"), *Node->GetNodeTitle(ENodeTitleType::FullTitle).ToString())
					)));
				}
			}
		}
	}

	// Build response
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("blueprint_name"), DSL.Name);
	Data->SetStringField(TEXT("asset_path"), PackagePath / DSL.Name);
	Data->SetNumberField(TEXT("nodes_created"), NodesCreated);
	Data->SetNumberField(TEXT("nodes_expected"), DSL.Nodes.Num());
	Data->SetNumberField(TEXT("connections_wired"), ConnectionsWired);
	Data->SetNumberField(TEXT("connections_expected"), DSL.Connections.Num());
	Data->SetBoolField(TEXT("compiled"), bCompiled);
	Data->SetArrayField(TEXT("compile_errors"), CompileErrors);
	Data->SetNumberField(TEXT("variables_created"), DSL.Variables.Num());

	UE_LOG(LogBlueprintLLM, Log, TEXT("Imported %s: %d/%d nodes, %d/%d connections, compiled=%s"),
		*DSL.Name, NodesCreated, DSL.Nodes.Num(),
		ConnectionsWired, DSL.Connections.Num(),
		bCompiled ? TEXT("true") : TEXT("false"));

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetBlueprintInfo(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'name' parameter"));
	}

	UBlueprint* BP = FindBlueprintByName(Name);
	if (!BP)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Blueprint not found: %s"), *Name));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("blueprint_name"), Name);
	Data->SetStringField(TEXT("parent_class"), BP->ParentClass ? BP->ParentClass->GetName() : TEXT("Unknown"));

	// Variables
	TArray<TSharedPtr<FJsonValue>> VarsArray;
	for (const FBPVariableDescription& Var : BP->NewVariables)
	{
		TSharedPtr<FJsonObject> VarObj = MakeShareable(new FJsonObject());
		VarObj->SetStringField(TEXT("name"), Var.VarName.ToString());
		VarObj->SetStringField(TEXT("type"), Var.VarType.PinCategory.ToString());
		VarObj->SetStringField(TEXT("default"), Var.DefaultValue);
		VarsArray.Add(MakeShareable(new FJsonValueObject(VarObj)));
	}
	Data->SetArrayField(TEXT("variables"), VarsArray);

	// Nodes
	TArray<TSharedPtr<FJsonValue>> NodesArray;
	TMap<UEdGraphNode*, FString> NodeIdMap;
	int32 NodeIndex = 0;

	UEdGraph* EventGraph = FBlueprintEditorUtils::FindEventGraph(BP);
	if (EventGraph)
	{
		for (UEdGraphNode* Node : EventGraph->Nodes)
		{
			FString NodeId = FString::Printf(TEXT("node_%d"), NodeIndex++);
			NodeIdMap.Add(Node, NodeId);

			TSharedPtr<FJsonObject> NodeObj = MakeShareable(new FJsonObject());
			NodeObj->SetStringField(TEXT("id"), NodeId);
			NodeObj->SetStringField(TEXT("class"), Node->GetClass()->GetName());
			NodeObj->SetStringField(TEXT("title"), Node->GetNodeTitle(ENodeTitleType::ListView).ToString());

			// Pins
			TArray<TSharedPtr<FJsonValue>> PinsArray;
			for (UEdGraphPin* Pin : Node->Pins)
			{
				TSharedPtr<FJsonObject> PinObj = MakeShareable(new FJsonObject());
				PinObj->SetStringField(TEXT("name"), Pin->PinName.ToString());
				PinObj->SetStringField(TEXT("direction"),
					Pin->Direction == EGPD_Input ? TEXT("input") : TEXT("output"));
				PinObj->SetStringField(TEXT("type"), Pin->PinType.PinCategory.ToString());
				if (!Pin->DefaultValue.IsEmpty())
				{
					PinObj->SetStringField(TEXT("default"), Pin->DefaultValue);
				}
				PinsArray.Add(MakeShareable(new FJsonValueObject(PinObj)));
			}
			NodeObj->SetArrayField(TEXT("pins"), PinsArray);

			NodesArray.Add(MakeShareable(new FJsonValueObject(NodeObj)));
		}
	}
	Data->SetArrayField(TEXT("nodes"), NodesArray);

	// Connections
	TArray<TSharedPtr<FJsonValue>> ConnsArray;
	if (EventGraph)
	{
		for (UEdGraphNode* Node : EventGraph->Nodes)
		{
			for (UEdGraphPin* Pin : Node->Pins)
			{
				if (Pin->Direction == EGPD_Output)
				{
					for (UEdGraphPin* LinkedPin : Pin->LinkedTo)
					{
						UEdGraphNode* TargetNode = LinkedPin->GetOwningNode();

						TSharedPtr<FJsonObject> ConnObj = MakeShareable(new FJsonObject());
						ConnObj->SetStringField(TEXT("source_node"),
							NodeIdMap.Contains(Node) ? NodeIdMap[Node] : TEXT("unknown"));
						ConnObj->SetStringField(TEXT("source_pin"), Pin->PinName.ToString());
						ConnObj->SetStringField(TEXT("target_node"),
							NodeIdMap.Contains(TargetNode) ? NodeIdMap[TargetNode] : TEXT("unknown"));
						ConnObj->SetStringField(TEXT("target_pin"), LinkedPin->PinName.ToString());
						ConnsArray.Add(MakeShareable(new FJsonValueObject(ConnObj)));
					}
				}
			}
		}
	}
	Data->SetArrayField(TEXT("connections"), ConnsArray);

	Data->SetBoolField(TEXT("compiled"), BP->Status != BS_Error);

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCompileBlueprint(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'name' parameter"));
	}

	UBlueprint* BP = FindBlueprintByName(Name);
	if (!BP)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Blueprint not found: %s"), *Name));
	}

	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	bool bSuccess = BP->Status != BS_Error;

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("blueprint_name"), Name);
	Data->SetBoolField(TEXT("compiled"), bSuccess);
	Data->SetStringField(TEXT("status"), bSuccess ? TEXT("clean") : TEXT("error"));

	UE_LOG(LogBlueprintLLM, Log, TEXT("Compiled %s: %s"), *Name, bSuccess ? TEXT("success") : TEXT("error"));

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleDeleteBlueprint(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'name' parameter"));
	}

	bool bDeleted = DeleteExistingBlueprint(Name);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("blueprint_name"), Name);
	Data->SetBoolField(TEXT("deleted"), bDeleted);

	return FCommandResult::Ok(Data);
}

// ============================================================
// Helpers
// ============================================================

UBlueprint* FCommandServer::FindBlueprintByName(const FString& Name)
{
	// Search in our generated path first
	FString AssetPath = FString::Printf(TEXT("/Game/BlueprintLLM/Generated/%s.%s"), *Name, *Name);
	UBlueprint* BP = LoadObject<UBlueprint>(nullptr, *AssetPath);
	if (BP)
	{
		return BP;
	}

	// Search asset registry
	FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	IAssetRegistry& AssetRegistry = AssetRegistryModule.Get();

	TArray<FAssetData> AssetList;
	AssetRegistry.GetAssetsByClass(UBlueprint::StaticClass()->GetClassPathName(), AssetList);

	for (const FAssetData& Asset : AssetList)
	{
		if (Asset.AssetName.ToString() == Name)
		{
			return Cast<UBlueprint>(Asset.GetAsset());
		}
	}

	return nullptr;
}

bool FCommandServer::DeleteExistingBlueprint(const FString& Name)
{
	UBlueprint* Existing = FindBlueprintByName(Name);
	if (!Existing)
	{
		return false; // Nothing to delete
	}

	UE_LOG(LogBlueprintLLM, Log, TEXT("Deleting existing Blueprint: %s"), *Name);

	// Get the package path for cleanup
	UPackage* Package = Existing->GetOutermost();
	FString PackagePath = Package->GetPathName();

	// Remove from asset registry and delete
	TArray<UObject*> ObjectsToDelete;
	ObjectsToDelete.Add(Existing);

	// Force delete without confirmation
	int32 NumDeleted = ObjectTools::ForceDeleteObjects(ObjectsToDelete, false);

	if (NumDeleted > 0)
	{
		UE_LOG(LogBlueprintLLM, Log, TEXT("Deleted Blueprint: %s"), *Name);
		return true;
	}

	UE_LOG(LogBlueprintLLM, Warning, TEXT("Failed to delete Blueprint: %s"), *Name);
	return false;
}
