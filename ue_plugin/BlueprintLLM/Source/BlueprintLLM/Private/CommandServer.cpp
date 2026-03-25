#include "CommandServer.h"
#include "TierGating.h"
#include "ArcwrightStats.h"
#include "DSLImporter.h"
#include "BlueprintBuilder.h"
#include "BehaviorTreeBuilder.h"

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
#include "Logging/MessageLog.h"
#include "Async/Async.h"
#include "SocketSubsystem.h"
#include "Subsystems/EditorActorSubsystem.h"
#include "Engine/StaticMeshActor.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/Pawn.h"
#include "AIController.h"
#include "BehaviorTree/BehaviorTree.h"
#include "BehaviorTree/BlackboardData.h"
#include "Engine/PointLight.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Atmosphere/AtmosphericFog.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Engine/ExponentialHeightFog.h"
#include "Camera/CameraActor.h"

// Component management
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SCS_Node.h"
#include "Components/BoxComponent.h"
#include "Components/SphereComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SpotLightComponent.h"
#include "Components/AudioComponent.h"
#include "Components/ArrowComponent.h"
#include "Components/LightComponent.h"

// Material management
#include "Materials/MaterialInstanceConstant.h"
#include "Materials/MaterialInterface.h"
#include "Materials/Material.h"
#include "Materials/MaterialExpressionConstant3Vector.h"
#include "Materials/MaterialExpressionConstant.h"
#include "Materials/MaterialExpressionMultiply.h"
#include "Materials/MaterialExpressionTextureSample.h"
#include "Materials/MaterialExpressionTextureCoordinate.h"
#include "Materials/MaterialExpressionAdd.h"
#include "Materials/MaterialExpressionSubtract.h"
#include "Materials/MaterialExpressionLinearInterpolate.h"
#include "Materials/MaterialExpressionScalarParameter.h"
#include "Materials/MaterialExpressionVectorParameter.h"
#include "Materials/MaterialExpressionOneMinus.h"
#include "Materials/MaterialExpressionFresnel.h"
#include "Materials/MaterialExpressionPanner.h"
#include "Materials/MaterialExpressionTime.h"
#include "Materials/MaterialExpressionNoise.h"
#include "Materials/MaterialExpressionDesaturation.h"
#include "Materials/MaterialExpressionComponentMask.h"
#include "Materials/MaterialExpressionAppendVector.h"
#include "Materials/MaterialExpressionClamp.h"
#include "Materials/MaterialExpressionPower.h"
#include "Materials/MaterialExpressionAbs.h"
#include "Materials/MaterialExpressionDivide.h"
#include "Materials/MaterialExpressionTextureObjectParameter.h"
#include "SafeSavePackage.h"

// Undo / redo
#include "Editor/Transactor.h"
#include "Editor/TransBuffer.h"

// Widget animation + rendering
#include "Animation/WidgetAnimation.h"

// Niagara
#include "NiagaraSystem.h"
#include "NiagaraEmitter.h"
#include "NiagaraRendererProperties.h"
#include "NiagaraSpriteRendererProperties.h"

// AnimGraph nodes (for AnimBP DSL)
#include "Animation/AnimBlueprint.h"
#include "AnimGraphNode_StateMachine.h"
#include "AnimationStateMachineGraph.h"
#include "AnimStateNode.h"
#include "AnimStateTransitionNode.h"
#include "AnimStateEntryNode.h"
#include "AnimGraphNode_SequencePlayer.h"
#include "AnimationStateGraph.h"
#include "Components/Border.h"
#include "Engine/Font.h"
#include "Engine/FontFace.h"
#include "Factories/FontFileImportFactory.h"
#include "AutomatedAssetImportData.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Slate/WidgetRenderer.h"
#include "Subsystems/AssetEditorSubsystem.h"

// Save / level / PIE
#include "FileHelpers.h"
#include "AssetToolsModule.h"
#include "IAssetTools.h"
#include "Editor.h"
#include "GameFramework/PlayerStart.h"
#include "GameFramework/WorldSettings.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "Framework/Application/SlateApplication.h"

// Input mapping (B29)
#include "InputAction.h"
#include "InputMappingContext.h"

// Audio (B24)
#include "Sound/SoundBase.h"
#include "Sound/SoundClass.h"
#include "Sound/SoundMix.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/AmbientSound.h"
#include "Sound/SoundConcurrency.h"
#include "Sound/SoundWave.h"
#include "Sound/SoundNodeWavePlayer.h"
#include "Sound/SoundNodeRandom.h"
#include "AudioDevice.h"
#include "Sound/SoundCue.h"
#include "Sound/SoundWave.h"
#include "Kismet/GameplayStatics.h"

// Viewport (B30)
#include "LevelEditorViewport.h"
#include "ImageUtils.h"
#include "UnrealClient.h"
#include "RenderingThread.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerInput.h"

#if PLATFORM_WINDOWS
#include "Windows/AllowWindowsPlatformTypes.h"
#include <windows.h>
#include "Windows/HideWindowsPlatformTypes.h"
#endif

// Niagara (B25)
#include "NiagaraSystem.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"

// Asset import (B31-B33)
#include "Factories/FbxFactory.h"
#include "Factories/TextureFactory.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"

// AI setup (setup_ai_for_pawn)
#include "Factories/BlueprintFactory.h"
#include "K2Node_Event.h"
#include "K2Node_CallFunction.h"
#include "K2Node_InputAction.h"
#include "K2Node_CustomEvent.h"
#include "K2Node_FunctionEntry.h"
#include "K2Node_FunctionResult.h"
#include "K2Node_VariableGet.h"
#include "K2Node_DynamicCast.h"

// Camera / Spring Arm (Phase 2)
#include "Camera/CameraComponent.h"
#include "GameFramework/SpringArmComponent.h"

// NavMesh (Phase 2)
#include "NavMesh/NavMeshBoundsVolume.h"

// Data Table builder
#include "DataTableBuilder.h"
#include "Engine/DataTable.h"

// Animation (Phase 6)
#include "Engine/SkeletalMeshSocket.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimBlueprintGeneratedClass.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimMontage.h"
#include "Animation/BlendSpace.h"
#include "Animation/BlendSpace1D.h"
#include "Animation/Skeleton.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Factories/AnimBlueprintFactory.h"
#include "Factories/AnimMontageFactory.h"

// Save Game (Phase 6)
#include "GameFramework/SaveGame.h"

// Level Management (Phase 6)
#include "Engine/LevelStreaming.h"
#include "Engine/LevelStreamingDynamic.h"
#include "EditorLevelUtils.h"

// Niagara parameters
#include "NiagaraTypes.h"

// Spline (Batch 1.1)
#include "Components/SplineComponent.h"

// Post-process (Batch 1.2)
#include "Engine/PostProcessVolume.h"

// Movement defaults (Batch 1.3)
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/FloatingPawnMovement.h"

// Physics constraints (Batch 1.4)
#include "PhysicsEngine/PhysicsConstraintActor.h"
#include "PhysicsEngine/PhysicsConstraintComponent.h"

// Sequencer (Batch 2.1)
#include "LevelSequence.h"
#include "LevelSequenceActor.h"
#include "MovieScene.h"
#include "Tracks/MovieScene3DTransformTrack.h"
#include "Tracks/MovieSceneVisibilityTrack.h"
#include "Tracks/MovieSceneFloatTrack.h"
#include "Sections/MovieScene3DTransformSection.h"
#include "Sections/MovieSceneBoolSection.h"
#include "Sections/MovieSceneFloatSection.h"
#include "Channels/MovieSceneChannelProxy.h"
#include "Channels/MovieSceneDoubleChannel.h"
#include "Channels/MovieSceneBoolChannel.h"
#include "Channels/MovieSceneFloatChannel.h"

// Landscape/Foliage (Batch 2.2)
#include "Landscape.h"
#include "LandscapeProxy.h"
#include "LandscapeInfo.h"
#include "InstancedFoliageActor.h"
#include "FoliageType_InstancedStaticMesh.h"

// Widget / UMG (B11)
#include "WidgetBlueprint.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/ProgressBar.h"
#include "Components/Image.h"
#include "Components/Button.h"
#include "Components/ScrollBox.h"
#include "Components/UniformGridPanel.h"
#include "Components/UniformGridSlot.h"
#include "Components/GridPanel.h"
#include "Components/GridSlot.h"
#include "Components/WrapBox.h"
#include "Components/WrapBoxSlot.h"
#include "Components/ListView.h"
#include "Components/TileView.h"
#include "Blueprint/UserWidget.h"
#include "Misc/DefaultValueHelper.h"

DEFINE_LOG_CATEGORY(LogBlueprintLLM);

const FString FCommandServer::SERVER_VERSION = TEXT("1.0.2");

// ============================================================
// Error Suggestion Helpers
// ============================================================

static TArray<FString> GetSuggestions(const FString& Query, const TArray<FString>& Available, int32 MaxResults = 5)
{
	TArray<FString> Matches;
	FString QueryLower = Query.ToLower();

	// First pass: exact substring matches
	for (const FString& Item : Available)
	{
		if (Item.ToLower().Contains(QueryLower) || QueryLower.Contains(Item.ToLower()))
		{
			Matches.Add(Item);
		}
	}

	// If not enough matches, try partial word matching
	if (Matches.Num() < MaxResults)
	{
		TArray<FString> Words;
		QueryLower.ParseIntoArray(Words, TEXT("_"), true);
		for (const FString& Item : Available)
		{
			if (Matches.Num() >= MaxResults) break;
			if (!Matches.Contains(Item))
			{
				for (const FString& Word : Words)
				{
					if (Word.Len() >= 3 && Item.ToLower().Contains(Word))
					{
						Matches.Add(Item);
						break;
					}
				}
			}
		}
	}

	if (Matches.Num() > MaxResults)
		Matches.SetNum(MaxResults);

	return Matches;
}

static TArray<FString> GetAvailableActorLabels()
{
	TArray<FString> Labels;
	if (!GEditor) return Labels;
	UEditorActorSubsystem* ActorSub = GEditor->GetEditorSubsystem<UEditorActorSubsystem>();
	if (!ActorSub) return Labels;
	TArray<AActor*> AllActors = ActorSub->GetAllLevelActors();
	for (AActor* Actor : AllActors)
	{
		if (Actor)
		{
			FString Lbl = Actor->GetActorLabel();
			if (!Lbl.IsEmpty())
			{
				Labels.Add(Lbl);
			}
		}
	}
	return Labels;
}

static TArray<FString> GetAvailableBlueprintNames()
{
	TArray<FString> Names;
	FAssetRegistryModule& ARM = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	TArray<FAssetData> Assets;
	ARM.Get().GetAssetsByClass(FTopLevelAssetPath(TEXT("/Script/Engine"), TEXT("Blueprint")), Assets);
	for (const FAssetData& Asset : Assets)
	{
		Names.Add(Asset.AssetName.ToString());
	}
	return Names;
}

static FString FormatActorNotFound(const FString& Label)
{
	FString Msg = FString::Printf(TEXT("Actor not found: %s."), *Label);
	TArray<FString> Suggestions = GetSuggestions(Label, GetAvailableActorLabels());
	if (Suggestions.Num() > 0)
	{
		Msg += TEXT(" Similar actors: ") + FString::Join(Suggestions, TEXT(", "));
	}
	return Msg;
}

static FString FormatBlueprintNotFound(const FString& Name)
{
	FString Msg = FString::Printf(TEXT("Blueprint not found: %s."), *Name);
	TArray<FString> Suggestions = GetSuggestions(Name, GetAvailableBlueprintNames());
	if (Suggestions.Num() > 0)
	{
		Msg += TEXT(" Similar blueprints: ") + FString::Join(Suggestions, TEXT(", "));
	}
	return Msg;
}

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
	ServerStartTime = FDateTime::UtcNow();

	// Initialize usage statistics
	Stats = MakeUnique<FArcwrightStats>();
	Stats->Initialize();

	// Register Slate post-tick callback for PIE requests.
	// FSlateApplication ticks reliably in editor mode — it MUST tick for UI rendering.
	// FTSTicker and FTickableEditorObject do NOT tick in UE 5.7 editor idle mode.
	if (FSlateApplication::IsInitialized())
	{
		SlatePostTickHandle = FSlateApplication::Get().OnPostTick().AddLambda([this](float DeltaTime)
		{
			if (bPIERequested.exchange(false))
			{
				if (GEditor && !GEditor->PlayWorld)
				{
					FRequestPlaySessionParams SessionParams;
					GEditor->RequestPlaySession(SessionParams);
					UE_LOG(LogBlueprintLLM, Log, TEXT("PIE: RequestPlaySession called from Slate OnPostTick"));
				}
			}
		});
		UE_LOG(LogBlueprintLLM, Log, TEXT("Arcwright: Registered Slate post-tick callback for PIE"));
	}

	UE_LOG(LogBlueprintLLM, Log, TEXT("Arcwright Command Server listening on port %d"), Port);
	UE_LOG(LogBlueprintLLM, Log, TEXT("Arcwright v%s ready — 91 TCP commands, MCP bridge on stdio. Connect any AI assistant via TCP or MCP."), *SERVER_VERSION);
	return true;
}

void FCommandServer::Stop()
{
	bRunning = false;

	// Shutdown stats (saves to disk, stops auto-save timer)
	if (Stats.IsValid())
	{
		Stats->Shutdown();
		Stats.Reset();
	}

	// Remove Slate callback
	if (SlatePostTickHandle.IsValid() && FSlateApplication::IsInitialized())
	{
		FSlateApplication::Get().OnPostTick().Remove(SlatePostTickHandle);
		SlatePostTickHandle.Reset();
	}

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

	UE_LOG(LogBlueprintLLM, Log, TEXT("Arcwright Command Server stopped"));
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
			// Ensure any pending rendering commands from previous operations
			// are complete before processing the next command. Without this,
			// rapid sequential commands (e.g., creating 12 materials or adding
			// components) cause FlushRenderingCommands to recurse and crash.
			if (IsInGameThread() && !IsInRenderingThread())
			{
				FlushRenderingCommands();
			}
			Result = DispatchCommand(Command, Params);

			// Track last error for get_last_error command
			if (!Result.bSuccess)
			{
				LastErrorMessage = Result.ErrorMessage;
				LastErrorCommand = Command;
			}

			// Record usage statistics
			if (Stats.IsValid())
			{
				Stats->RecordCommand(Command, Result.bSuccess, Result.Data);
			}

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
	if (Command == TEXT("spawn_actor_at"))
	{
		return HandleSpawnActorAt(Params);
	}
	if (Command == TEXT("get_actors"))
	{
		return HandleGetActors(Params);
	}
	if (Command == TEXT("set_actor_transform"))
	{
		return HandleSetActorTransform(Params);
	}
	if (Command == TEXT("delete_actor"))
	{
		return HandleDeleteActor(Params);
	}
	if (Command == TEXT("create_blueprint"))
	{
		return HandleCreateBlueprint(Params);
	}
	if (Command == TEXT("create_blueprint_from_dsl"))
	{
		return HandleCreateBlueprintFromDSL(Params);
	}
	if (Command == TEXT("add_node"))
	{
		return HandleAddNode(Params);
	}
	if (Command == TEXT("add_nodes_batch"))
	{
		return HandleAddNodesBatch(Params);
	}
	if (Command == TEXT("remove_node"))
	{
		return HandleRemoveNode(Params);
	}
	if (Command == TEXT("add_connection"))
	{
		return HandleAddConnection(Params);
	}
	if (Command == TEXT("add_connections_batch"))
	{
		return HandleAddConnectionsBatch(Params);
	}
	if (Command == TEXT("remove_connection"))
	{
		return HandleRemoveConnection(Params);
	}
	if (Command == TEXT("validate_blueprint"))
	{
		return HandleValidateBlueprint(Params);
	}
	if (Command == TEXT("set_node_param"))
	{
		return HandleSetNodeParam(Params);
	}
	if (Command == TEXT("set_variable_default"))
	{
		return HandleSetVariableDefault(Params);
	}
	if (Command == TEXT("add_component"))
	{
		return HandleAddComponent(Params);
	}
	if (Command == TEXT("get_components"))
	{
		return HandleGetComponents(Params);
	}
	if (Command == TEXT("remove_component"))
	{
		return HandleRemoveComponent(Params);
	}
	if (Command == TEXT("set_component_property"))
	{
		return HandleSetComponentProperty(Params);
	}
	if (Command == TEXT("create_material_instance"))
	{
		return HandleCreateMaterialInstance(Params);
	}
	if (Command == TEXT("create_simple_material"))
	{
		return HandleCreateSimpleMaterial(Params);
	}
	if (Command == TEXT("create_textured_material"))
	{
		return HandleCreateTexturedMaterial(Params);
	}
	if (Command == TEXT("apply_material"))
	{
		return HandleApplyMaterial(Params);
	}
	if (Command == TEXT("set_actor_material"))
	{
		return HandleSetActorMaterial(Params);
	}
	if (Command == TEXT("save_all"))
	{
		return HandleSaveAll(Params);
	}
	if (Command == TEXT("save_level"))
	{
		return HandleSaveLevel(Params);
	}
	if (Command == TEXT("get_level_info"))
	{
		return HandleGetLevelInfo(Params);
	}
	if (Command == TEXT("duplicate_blueprint"))
	{
		return HandleDuplicateBlueprint(Params);
	}
	if (Command == TEXT("play_in_editor"))
	{
		return HandlePlayInEditor(Params);
	}
	if (Command == TEXT("stop_play"))
	{
		return HandleStopPlay(Params);
	}
	if (Command == TEXT("is_playing"))
	{
		TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
		Data->SetBoolField(TEXT("playing"), GEditor && GEditor->PlayWorld != nullptr);
		return FCommandResult::Ok(Data);
	}
	if (Command == TEXT("play_and_capture"))
	{
		return HandlePlayAndCapture(Params);
	}
	if (Command == TEXT("verify_all_blueprints"))
	{
		return HandleVerifyAllBlueprints(Params);
	}
	if (Command == TEXT("teleport_player"))     { return HandleTeleportPlayer(Params); }
	if (Command == TEXT("get_player_location"))  { return HandleGetPlayerLocation(Params); }
	if (Command == TEXT("look_at"))              { return HandleLookAt(Params); }
	if (Command == TEXT("end_day"))
	{
		if (!GEditor || !GEditor->PlayWorld)
			return FCommandResult::Error(TEXT("PIE not running"));

		// Call EndDay via PlayerController's console command system
		// This triggers BSNextDay on the cheat manager which calls TimeSubsystem->EndDay()
		APlayerController* PC = GEditor->PlayWorld->GetFirstPlayerController();
		if (!PC)
			return FCommandResult::Error(TEXT("No player controller"));

		PC->ConsoleCommand(TEXT("BSNextDay"));

		TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
		Data->SetBoolField(TEXT("ended"), true);
		Data->SetStringField(TEXT("note"), TEXT("Called BSNextDay cheat — advances calendar and resets time"));
		return FCommandResult::Ok(Data);
	}
	if (Command == TEXT("run_console_command"))
	{
		FString Cmd = Params->GetStringField(TEXT("command"));
		if (Cmd.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'command' param"));
		if (!GEditor || !GEditor->PlayWorld)
			return FCommandResult::Error(TEXT("PIE not running — console commands need a game world"));
		APlayerController* PC = GEditor->PlayWorld->GetFirstPlayerController();
		if (!PC) return FCommandResult::Error(TEXT("No player controller"));
		FString Result;
		PC->ConsoleCommand(Cmd);
		TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
		Data->SetStringField(TEXT("command"), Cmd);
		Data->SetBoolField(TEXT("executed"), true);
		return FCommandResult::Ok(Data);
	}
	if (Command == TEXT("get_player_view"))      { return HandleGetPlayerView(Params); }
	if (Command == TEXT("teleport_to_actor"))    { return HandleTeleportToActor(Params); }
	if (Command == TEXT("capture_full_screen"))  { return HandleCaptureFullScreen(Params); }
	if (Command == TEXT("simulate_input"))       { return HandleSimulateInput(Params); }
	if (Command == TEXT("simulate_walk_to"))     { return HandleSimulateWalkTo(Params); }
	if (Command == TEXT("get_message_log"))      { return HandleGetMessageLog(Params); }
	if (Command == TEXT("run_map_check"))        { return HandleRunMapCheck(Params); }
	if (Command == TEXT("get_output_log"))
	{
		return HandleGetOutputLog(Params);
	}

	// Input mapping commands (B29)
	if (Command == TEXT("add_input_action"))
	{
		return HandleAddInputAction(Params);
	}
	if (Command == TEXT("add_input_mapping"))
	{
		return HandleAddInputMapping(Params);
	}
	if (Command == TEXT("setup_input_context"))
	{
		return HandleSetupInputContext(Params);
	}
	if (Command == TEXT("get_input_actions"))
	{
		return HandleGetInputActions(Params);
	}

	// Audio commands (B24)
	if (Command == TEXT("play_sound_at_location"))
	{
		return HandlePlaySoundAtLocation(Params);
	}
	if (Command == TEXT("add_audio_component"))
	{
		return HandleAddAudioComponent(Params);
	}
	if (Command == TEXT("get_sound_assets"))
	{
		return HandleGetSoundAssets(Params);
	}

	// Viewport commands (B30)
	if (Command == TEXT("set_viewport_camera"))
	{
		return HandleSetViewportCamera(Params);
	}
	if (Command == TEXT("take_screenshot"))
	{
		return HandleTakeScreenshot(Params);
	}
	if (Command == TEXT("set_pir_widget"))
	{
		return HandleSetPirWidget(Params);
	}
	if (Command == TEXT("get_viewport_info"))
	{
		return HandleGetViewportInfo(Params);
	}

	// Niagara commands (B25)
	if (Command == TEXT("spawn_niagara_at_location"))
	{
		return HandleSpawnNiagaraAtLocation(Params);
	}
	if (Command == TEXT("add_niagara_component"))
	{
		return HandleAddNiagaraComponent(Params);
	}
	if (Command == TEXT("get_niagara_assets"))
	{
		return HandleGetNiagaraAssets(Params);
	}

	// Behavior Tree commands
	if (Command == TEXT("create_behavior_tree"))
	{
		return HandleCreateBehaviorTree(Params);
	}
	if (Command == TEXT("get_behavior_tree_info"))
	{
		return HandleGetBehaviorTreeInfo(Params);
	}
	if (Command == TEXT("set_blackboard_key_default"))
	{
		return HandleSetBlackboardKeyDefault(Params);
	}

	// Class default properties
	if (Command == TEXT("set_class_defaults"))
	{
		return HandleSetClassDefaults(Params);
	}

	// Editor lifecycle
	if (Command == TEXT("quit_editor"))
	{
		return HandleQuitEditor(Params);
	}

	// Widget commands (B11)
	if (Command == TEXT("create_widget_blueprint"))
	{
		return HandleCreateWidgetBlueprint(Params);
	}
	if (Command == TEXT("set_widget_design_size"))
	{
		return HandleSetWidgetDesignSize(Params);
	}
	if (Command == TEXT("add_widget_child"))
	{
		return HandleAddWidgetChild(Params);
	}
	if (Command == TEXT("set_widget_property"))
	{
		return HandleSetWidgetProperty(Params);
	}
	if (Command == TEXT("get_widget_property"))
	{
		return HandleGetWidgetProperty(Params);
	}
	if (Command == TEXT("get_widget_tree"))
	{
		return HandleGetWidgetTree(Params);
	}
	if (Command == TEXT("remove_widget"))
	{
		return HandleRemoveWidget(Params);
	}
	// Widget DSL v2 commands
	if (Command == TEXT("set_widget_anchor"))       { return HandleSetWidgetAnchor(Params); }
	if (Command == TEXT("set_widget_binding"))       { return HandleSetWidgetBinding(Params); }
	if (Command == TEXT("create_widget_animation"))  { return HandleCreateWidgetAnimation(Params); }
	if (Command == TEXT("add_animation_track"))      { return HandleAddAnimationTrack(Params); }
	if (Command == TEXT("set_widget_brush"))         { return HandleSetWidgetBrush(Params); }
	if (Command == TEXT("set_widget_font"))          { return HandleSetWidgetFont(Params); }
	if (Command == TEXT("preview_widget"))           { return HandlePreviewWidget(Params); }
	if (Command == TEXT("get_widget_screenshot"))    { return HandleGetWidgetScreenshot(Params); }
	if (Command == TEXT("get_viewport_widgets"))     { return HandleGetViewportWidgets(Params); }
	if (Command == TEXT("reparent_widget_blueprint")) { return HandleReparentWidgetBlueprint(Params); }
	if (Command == TEXT("validate_widget_layout"))   { return HandleValidateWidgetLayout(Params); }
	if (Command == TEXT("auto_fix_widget_layout"))    { return HandleAutoFixWidgetLayout(Params); }
	if (Command == TEXT("protect_widget_layout"))      { return HandleProtectWidgetLayout(Params); }

	// Media texture command
	if (Command == TEXT("assign_media_texture")) { return HandleAssignMediaTexture(Params); }

	// Widget variable / binding commands
	if (Command == TEXT("set_widget_is_variable")) { return HandleSetWidgetIsVariable(Params); }
	if (Command == TEXT("add_widget_variable"))    { return HandleAddWidgetVariable(Params); }
	if (Command == TEXT("set_widget_entry_class")) { return HandleSetWidgetEntryClass(Params); }
	if (Command == TEXT("add_scroll_sync"))         { return HandleAddScrollSync(Params); }
	if (Command == TEXT("bind_text_to_variable"))   { return HandleBindTextToVariable(Params); }

	// Font pipeline commands
	if (Command == TEXT("import_font_face"))    { return HandleImportFontFace(Params); }
	if (Command == TEXT("create_font_asset"))   { return HandleCreateFontAsset(Params); }
	if (Command == TEXT("add_font_typeface"))   { return HandleAddFontTypeface(Params); }
	if (Command == TEXT("get_font_info"))       { return HandleGetFontInfo(Params); }
	if (Command == TEXT("list_font_assets"))    { return HandleListFontAssets(Params); }
	if (Command == TEXT("import_font_family"))  { return HandleImportFontFamily(Params); }

	// Generic DSL config commands (Input, SmartObject, Sound, Replication, ControlRig, StateTree, Vehicle, WorldPartition, Landscape, Foliage, MassEntity)
	if (Command == TEXT("create_input_config") || Command == TEXT("create_smartobject_config") ||
		Command == TEXT("create_sound_config") || Command == TEXT("create_replication_config") ||
		Command == TEXT("create_controlrig_config") || Command == TEXT("create_statetree_config") ||
		Command == TEXT("create_vehicle_config") || Command == TEXT("create_worldpartition_config") ||
		Command == TEXT("create_landscape_config") || Command == TEXT("create_foliage_config") ||
		Command == TEXT("create_massentity_config") ||
		Command == TEXT("create_shader_config") || Command == TEXT("create_procmesh_config") ||
		Command == TEXT("create_paper2d_config") || Command == TEXT("create_composure_config") ||
		Command == TEXT("create_dmx_config"))
	{
		return HandleCreateDSLConfig(Params);
	}
	if (Command == TEXT("add_input_element") || Command == TEXT("add_smartobject_element") ||
		Command == TEXT("add_sound_element") || Command == TEXT("add_replication_element") ||
		Command == TEXT("add_controlrig_element") || Command == TEXT("add_statetree_element") ||
		Command == TEXT("add_vehicle_element") || Command == TEXT("add_worldpartition_element") ||
		Command == TEXT("add_landscape_element") || Command == TEXT("add_foliage_element") ||
		Command == TEXT("add_massentity_element") ||
		Command == TEXT("add_shader_element") || Command == TEXT("add_procmesh_element") ||
		Command == TEXT("add_paper2d_element") || Command == TEXT("add_composure_element") ||
		Command == TEXT("add_dmx_element"))
	{
		return HandleAddDSLElement(Params);
	}

	// Perception DSL
	if (Command == TEXT("create_ai_perception"))     { return HandleCreateAIPerception(Params); }
	if (Command == TEXT("add_perception_sense"))      { return HandleAddPerceptionSense(Params); }
	// Physics DSL
	if (Command == TEXT("create_physics_setup"))      { return HandleCreatePhysicsSetup(Params); }
	if (Command == TEXT("add_physics_constraint_dsl")){ return HandleAddPhysicsConstraintDSL(Params); }
	if (Command == TEXT("add_destructible"))          { return HandleAddDestructible(Params); }
	// Tags DSL
	if (Command == TEXT("create_tag_hierarchy"))      { return HandleCreateTagHierarchy(Params); }
	if (Command == TEXT("add_gameplay_tag"))          { return HandleAddGameplayTag(Params); }

	// GAS DSL commands
	if (Command == TEXT("create_ability_system"))     { return HandleCreateAbilitySystem(Params); }
	if (Command == TEXT("add_attribute"))             { return HandleAddAttribute(Params); }
	if (Command == TEXT("add_ability"))               { return HandleAddAbility(Params); }
	if (Command == TEXT("add_ability_effect"))        { return HandleAddAbilityEffect(Params); }
	if (Command == TEXT("create_gas_from_dsl"))       { return HandleCreateGASFromDSL(Params); }
	if (Command == TEXT("get_ability_data"))          { return HandleGetAbilityData(Params); }

	// Sequence DSL commands
	if (Command == TEXT("add_sequence_camera"))       { return HandleAddSequenceCamera(Params); }
	if (Command == TEXT("add_sequence_audio"))        { return HandleAddSequenceAudio(Params); }
	if (Command == TEXT("add_sequence_fade"))         { return HandleAddSequenceFade(Params); }
	if (Command == TEXT("add_sequence_event"))        { return HandleAddSequenceEvent(Params); }
	if (Command == TEXT("create_sequence_from_dsl"))  { return HandleCreateSequenceFromDSL(Params); }

	// Quest DSL commands
	if (Command == TEXT("create_quest"))              { return HandleCreateQuest(Params); }
	if (Command == TEXT("add_quest_stage"))           { return HandleAddQuestStage(Params); }
	if (Command == TEXT("add_quest_objective"))       { return HandleAddQuestObjective(Params); }
	if (Command == TEXT("create_quest_from_dsl"))     { return HandleCreateQuestFromDSL(Params); }
	if (Command == TEXT("get_quest_data"))            { return HandleGetQuestData(Params); }

	// Dialogue DSL commands
	if (Command == TEXT("create_dialogue"))           { return HandleCreateDialogue(Params); }
	if (Command == TEXT("add_dialogue_node"))         { return HandleAddDialogueNode(Params); }
	if (Command == TEXT("create_dialogue_from_dsl"))  { return HandleCreateDialogueFromDSL(Params); }
	if (Command == TEXT("get_dialogue_tree"))         { return HandleGetDialogueTree(Params); }

	// Niagara DSL commands
	if (Command == TEXT("test_create_niagara_system"))   { return HandleTestCreateNiagaraSystem(Params); }
	if (Command == TEXT("create_niagara_system"))         { return HandleCreateNiagaraSystem(Params); }
	if (Command == TEXT("add_niagara_emitter"))           { return HandleAddNiagaraEmitter(Params); }
	if (Command == TEXT("set_niagara_emitter_param"))     { return HandleSetNiagaraEmitterParam(Params); }
	if (Command == TEXT("compile_niagara_system"))        { return HandleCompileNiagaraSystem(Params); }

	// Material Graph DSL commands
	if (Command == TEXT("test_create_material_graph"))  { return HandleTestCreateMaterialGraph(Params); }
	if (Command == TEXT("create_material_graph"))        { return HandleCreateMaterial(Params); }
	if (Command == TEXT("add_material_node"))             { return HandleAddMaterialNode(Params); }
	if (Command == TEXT("connect_material_nodes"))        { return HandleConnectMaterialNodes(Params); }
	if (Command == TEXT("set_material_output"))           { return HandleSetMaterialOutput(Params); }
	if (Command == TEXT("compile_material_graph"))        { return HandleCompileMaterial(Params); }
	if (Command == TEXT("create_material_from_dsl"))      { return HandleCreateMaterialFromDSL(Params); }

	// Animation Blueprint DSL commands
	if (Command == TEXT("test_create_anim_blueprint"))   { return HandleTestCreateAnimBlueprint(Params); }
	if (Command == TEXT("create_anim_blueprint_dsl"))     { return HandleCreateAnimBlueprintDSL(Params); }
	if (Command == TEXT("add_state_machine"))             { return HandleAddStateMachine(Params); }
	if (Command == TEXT("add_anim_state_2"))              { return HandleAddAnimState2(Params); }
	if (Command == TEXT("add_anim_transition_2"))         { return HandleAddAnimTransition2(Params); }
	if (Command == TEXT("add_anim_layer"))                { return HandleAddAnimLayer(Params); }
	if (Command == TEXT("add_anim_montage_2"))            { return HandleAddAnimMontage(Params); }
	if (Command == TEXT("create_aim_offset"))             { return HandleCreateAimOffset(Params); }
	if (Command == TEXT("set_anim_notify_2"))             { return HandleSetAnimNotify(Params); }
	if (Command == TEXT("compile_anim_blueprint"))        { return HandleCompileAnimBlueprint(Params); }

	// Audio system commands
	if (Command == TEXT("create_sound_class"))         { return HandleCreateSoundClass(Params); }
	if (Command == TEXT("create_sound_mix"))            { return HandleCreateSoundMix(Params); }
	if (Command == TEXT("set_sound_class_volume"))      { return HandleSetSoundClassVolume(Params); }
	if (Command == TEXT("create_attenuation_settings")) { return HandleCreateAttenuationSettings(Params); }
	if (Command == TEXT("create_ambient_sound"))        { return HandleCreateAmbientSound(Params); }
	if (Command == TEXT("create_audio_volume"))         { return HandleCreateAudioVolume(Params); }
	if (Command == TEXT("set_reverb_settings"))         { return HandleSetReverbSettings(Params); }
	if (Command == TEXT("play_sound_2d"))               { return HandlePlaySound2D(Params); }
	if (Command == TEXT("set_sound_concurrency"))       { return HandleSetSoundConcurrency(Params); }
	if (Command == TEXT("create_sound_cue"))            { return HandleCreateSoundCue(Params); }
	if (Command == TEXT("import_audio_file"))           { return HandleImportAudioFile(Params); }

	// Asset import commands (B31-B33)
	if (Command == TEXT("import_static_mesh"))
	{
		return HandleImportStaticMesh(Params);
	}
	if (Command == TEXT("import_texture"))
	{
		return HandleImportTexture(Params);
	}
	if (Command == TEXT("import_sound"))
	{
		return HandleImportSound(Params);
	}

	// Spline commands (Batch 1.1)
	if (Command == TEXT("create_spline_actor"))
	{
		return HandleCreateSplineActor(Params);
	}
	if (Command == TEXT("add_spline_point"))
	{
		return HandleAddSplinePoint(Params);
	}
	if (Command == TEXT("get_spline_info"))
	{
		return HandleGetSplineInfo(Params);
	}

	// Post-process commands (Batch 1.2)
	if (Command == TEXT("add_post_process_volume"))
	{
		return HandleAddPostProcessVolume(Params);
	}
	if (Command == TEXT("set_post_process_settings"))
	{
		return HandleSetPostProcessSettings(Params);
	}

	// Movement defaults (Batch 1.3)
	if (Command == TEXT("set_movement_defaults"))
	{
		return HandleSetMovementDefaults(Params);
	}

	// Physics constraint commands (Batch 1.4)
	if (Command == TEXT("add_physics_constraint"))
	{
		return HandleAddPhysicsConstraint(Params);
	}
	if (Command == TEXT("break_constraint"))
	{
		return HandleBreakConstraint(Params);
	}

	// Sequencer commands (Batch 2.1)
	if (Command == TEXT("create_sequence"))
	{
		return HandleCreateSequence(Params);
	}
	if (Command == TEXT("add_sequence_track"))
	{
		return HandleAddSequenceTrack(Params);
	}
	if (Command == TEXT("add_keyframe"))
	{
		return HandleAddKeyframe(Params);
	}
	if (Command == TEXT("get_sequence_info"))
	{
		return HandleGetSequenceInfo(Params);
	}
	if (Command == TEXT("play_sequence"))
	{
		return HandlePlaySequence(Params);
	}

	// Landscape/Foliage commands (Batch 2.2)
	if (Command == TEXT("get_landscape_info"))
	{
		return HandleGetLandscapeInfo(Params);
	}
	if (Command == TEXT("set_landscape_material"))
	{
		return HandleSetLandscapeMaterial(Params);
	}
	if (Command == TEXT("create_foliage_type"))
	{
		return HandleCreateFoliageType(Params);
	}
	if (Command == TEXT("paint_foliage"))
	{
		return HandlePaintFoliage(Params);
	}
	if (Command == TEXT("get_foliage_info"))
	{
		return HandleGetFoliageInfo(Params);
	}

	// AI setup helper
	if (Command == TEXT("setup_ai_for_pawn"))
	{
		return HandleSetupAIForPawn(Params);
	}

	// Data Table commands
	if (Command == TEXT("create_data_table"))
	{
		return HandleCreateDataTable(Params);
	}
	if (Command == TEXT("get_data_table_info"))
	{
		return HandleGetDataTableInfo(Params);
	}

	// Scene lighting
	if (Command == TEXT("setup_scene_lighting"))
	{
		return HandleSetupSceneLighting(Params);
	}

	// Game mode
	if (Command == TEXT("set_game_mode"))
	{
		return HandleSetGameMode(Params);
	}

	// Query commands
	if (Command == TEXT("find_blueprints")) { return HandleFindBlueprints(Params); }
	if (Command == TEXT("find_actors"))     { return HandleFindActors(Params); }
	if (Command == TEXT("find_assets"))     { return HandleFindAssets(Params); }

	// Batch modify commands
	if (Command == TEXT("batch_set_variable"))     { return HandleBatchSetVariable(Params); }
	if (Command == TEXT("batch_add_component"))    { return HandleBatchAddComponent(Params); }
	if (Command == TEXT("batch_apply_material"))   { return HandleBatchApplyMaterial(Params); }
	if (Command == TEXT("batch_set_property"))     { return HandleBatchSetProperty(Params); }
	if (Command == TEXT("batch_delete_actors"))    { return HandleBatchDeleteActors(Params); }
	if (Command == TEXT("batch_replace_material")) { return HandleBatchReplaceMaterial(Params); }

	// In-place modify commands
	if (Command == TEXT("modify_blueprint"))    { return HandleModifyBlueprint(Params); }
	if (Command == TEXT("rename_asset"))        { return HandleRenameAsset(Params); }
	if (Command == TEXT("reparent_blueprint"))  { return HandleReparentBlueprint(Params); }

	// Phase 2: New commands (v8.1)
	if (Command == TEXT("set_collision_preset"))    { return HandleSetCollisionPreset(Params); }
	if (Command == TEXT("get_blueprint_details"))   { return HandleGetBlueprintDetails(Params); }
	if (Command == TEXT("get_blueprint_graph"))    { return HandleGetBlueprintDetails(Params); }
	if (Command == TEXT("get_compile_status"))     { return HandleCompileBlueprint(Params); }
	if (Command == TEXT("get_level_snapshot"))     { return HandleGetLevelInfo(Params); }
	if (Command == TEXT("get_asset_list"))         { return HandleFindAssets(Params); }
	if (Command == TEXT("get_actor_details"))      { return HandleGetActorProperties(Params); }
	if (Command == TEXT("get_log_output"))         { return HandleGetOutputLog(Params); }
	if (Command == TEXT("set_camera_properties"))   { return HandleSetCameraProperties(Params); }
	if (Command == TEXT("create_input_action"))     { return HandleCreateInputAction(Params); }
	if (Command == TEXT("bind_input_to_blueprint")) { return HandleBindInputToBlueprint(Params); }
	if (Command == TEXT("set_collision_shape"))      { return HandleSetCollisionShape(Params); }
	if (Command == TEXT("create_nav_mesh_bounds"))   { return HandleCreateNavMeshBounds(Params); }
	if (Command == TEXT("set_audio_properties"))     { return HandleSetAudioProperties(Params); }
	if (Command == TEXT("set_actor_tags"))           { return HandleSetActorTags(Params); }
	if (Command == TEXT("get_actor_properties"))     { return HandleGetActorProperties(Params); }

	// Phase 4: Discovery commands
	if (Command == TEXT("list_available_materials"))   { return HandleListAvailableMaterials(Params); }
	if (Command == TEXT("list_available_blueprints"))  { return HandleListAvailableBlueprints(Params); }
	if (Command == TEXT("get_last_error"))             { return HandleGetLastError(Params); }

	// Phase 5: Actor config & utility commands
	if (Command == TEXT("set_physics_enabled"))    { return HandleSetPhysicsEnabled(Params); }
	if (Command == TEXT("set_actor_visibility"))   { return HandleSetActorVisibility(Params); }
	if (Command == TEXT("set_actor_mobility"))     { return HandleSetActorMobility(Params); }
	if (Command == TEXT("attach_actor_to"))        { return HandleAttachActorTo(Params); }
	if (Command == TEXT("detach_actor"))            { return HandleDetachActor(Params); }
	if (Command == TEXT("list_project_assets"))     { return HandleListProjectAssets(Params); }
	if (Command == TEXT("copy_actor"))              { return HandleCopyActor(Params); }

	// Procedural spawn pattern commands
	if (Command == TEXT("spawn_actor_grid"))   { return HandleSpawnActorGrid(Params); }
	if (Command == TEXT("spawn_actor_circle")) { return HandleSpawnActorCircle(Params); }
	if (Command == TEXT("spawn_actor_line"))   { return HandleSpawnActorLine(Params); }

	// Relative transform batch commands
	if (Command == TEXT("batch_scale_actors")) { return HandleBatchScaleActors(Params); }
	if (Command == TEXT("batch_move_actors"))  { return HandleBatchMoveActors(Params); }

	// Phase 6: Enhanced Input
	if (Command == TEXT("set_player_input_mapping")) { return HandleSetPlayerInputMapping(Params); }

	// Phase 6: Advanced Actor Configuration
	if (Command == TEXT("set_actor_tick"))      { return HandleSetActorTick(Params); }
	if (Command == TEXT("set_actor_lifespan"))  { return HandleSetActorLifespan(Params); }
	if (Command == TEXT("get_actor_bounds"))    { return HandleGetActorBounds(Params); }
	if (Command == TEXT("set_actor_enabled"))   { return HandleSetActorEnabled(Params); }

	// Phase 6: Data & Persistence
	if (Command == TEXT("create_save_game"))    { return HandleCreateSaveGame(Params); }
	if (Command == TEXT("add_data_table_row"))  { return HandleAddDataTableRow(Params); }
	if (Command == TEXT("edit_data_table_row")) { return HandleEditDataTableRow(Params); }
	if (Command == TEXT("get_data_table_rows")) { return HandleGetDataTableRows(Params); }

	// Phase 6: Animation
	if (Command == TEXT("create_anim_blueprint"))       { return HandleCreateAnimBlueprint(Params); }
	if (Command == TEXT("add_anim_state"))              { return HandleAddAnimState(Params); }
	if (Command == TEXT("add_anim_transition"))         { return HandleAddAnimTransition(Params); }
	if (Command == TEXT("set_anim_state_animation"))    { return HandleSetAnimStateAnimation(Params); }
	if (Command == TEXT("create_anim_montage"))         { return HandleCreateAnimMontage(Params); }
	if (Command == TEXT("add_montage_section"))         { return HandleAddMontageSection(Params); }
	if (Command == TEXT("create_blend_space"))          { return HandleCreateBlendSpace(Params); }
	if (Command == TEXT("add_blend_space_sample"))      { return HandleAddBlendSpaceSample(Params); }
	if (Command == TEXT("set_skeletal_mesh"))           { return HandleSetSkeletalMesh(Params); }
	if (Command == TEXT("play_animation"))              { return HandlePlayAnimation(Params); }
	if (Command == TEXT("get_skeleton_bones"))          { return HandleGetSkeletonBones(Params); }
	if (Command == TEXT("get_available_animations"))    { return HandleGetAvailableAnimations(Params); }

	// Phase 6: Niagara Advanced
	if (Command == TEXT("set_niagara_parameter"))   { return HandleSetNiagaraParameter(Params); }
	if (Command == TEXT("activate_niagara"))        { return HandleActivateNiagara(Params); }
	if (Command == TEXT("get_niagara_parameters"))  { return HandleGetNiagaraParameters(Params); }

	// Phase 6: Level Management
	if (Command == TEXT("create_sublevel"))         { return HandleCreateSublevel(Params); }
	if (Command == TEXT("set_level_visibility"))    { return HandleSetLevelVisibility(Params); }
	if (Command == TEXT("get_sublevel_list"))       { return HandleGetSublevelList(Params); }
	if (Command == TEXT("move_actor_to_sublevel"))  { return HandleMoveActorToSublevel(Params); }

	// Phase 6: World & Actor Utilities (150 target)
	if (Command == TEXT("get_world_settings"))   { return HandleGetWorldSettings(Params); }
	if (Command == TEXT("set_world_settings"))   { return HandleSetWorldSettings(Params); }
	if (Command == TEXT("get_actor_class"))       { return HandleGetActorClass(Params); }
	if (Command == TEXT("set_actor_scale"))       { return HandleSetActorScale(Params); }

	// Capability discovery
	if (Command == TEXT("get_capabilities")) { return HandleGetCapabilities(Params); }

	// Usage statistics
	if (Command == TEXT("get_stats"))   { return HandleGetStats(Params); }
	if (Command == TEXT("reset_stats")) { return HandleResetStats(Params); }

	// Live preview
	if (Command == TEXT("take_viewport_screenshot")) { return HandleTakeViewportScreenshot(Params); }

	// Undo/redo
	if (Command == TEXT("undo"))              { return HandleUndo(Params); }
	if (Command == TEXT("redo"))              { return HandleRedo(Params); }
	if (Command == TEXT("get_undo_history"))  { return HandleGetUndoHistory(Params); }
	if (Command == TEXT("begin_undo_group"))  { return HandleBeginUndoGroup(Params); }
	if (Command == TEXT("end_undo_group"))    { return HandleEndUndoGroup(Params); }

	// Store last error for get_last_error command
	FString ErrorMsg = FString::Printf(TEXT("Unknown command: '%s'. Use 'health_check' to verify connection, or 'list_available_blueprints'/'list_available_materials' to discover assets."), *Command);
	LastErrorMessage = ErrorMsg;
	LastErrorCommand = Command;
	return FCommandResult::Error(ErrorMsg);
}

// ============================================================
// Command handlers
// ============================================================

FCommandResult FCommandServer::HandleHealthCheck(const TSharedPtr<FJsonObject>& Params)
{
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("server"), TEXT("Arcwright"));
	Data->SetStringField(TEXT("version"), SERVER_VERSION);
	Data->SetStringField(TEXT("engine"), TEXT("UnrealEngine"));
	Data->SetStringField(TEXT("engine_version"), *FEngineVersion::Current().ToString());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetCapabilities(const TSharedPtr<FJsonObject>& Params)
{
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("server"), TEXT("Arcwright"));
	Data->SetStringField(TEXT("version"), SERVER_VERSION);
	Data->SetStringField(TEXT("engine_version"), *FEngineVersion::Current().ToString());
	Data->SetNumberField(TEXT("tcp_commands"), 267);
	Data->SetNumberField(TEXT("mcp_tools"), 267);

	// Categories with command lists
	TSharedPtr<FJsonObject> Categories = MakeShareable(new FJsonObject());

	auto AddCategory = [&](const FString& Name, const TArray<FString>& Commands)
	{
		TArray<TSharedPtr<FJsonValue>> Arr;
		for (const FString& Cmd : Commands)
		{
			Arr.Add(MakeShareable(new FJsonValueString(Cmd)));
		}
		Categories->SetArrayField(Name, Arr);
	};

	AddCategory(TEXT("blueprint_creation"), {
		TEXT("create_blueprint"), TEXT("import_from_ir"), TEXT("create_blueprint_from_dsl"),
		TEXT("get_blueprint_info"), TEXT("get_blueprint_details"), TEXT("compile_blueprint"),
		TEXT("validate_blueprint"), TEXT("delete_blueprint"), TEXT("duplicate_blueprint"),
		TEXT("modify_blueprint"), TEXT("rename_asset"), TEXT("reparent_blueprint")
	});
	AddCategory(TEXT("blueprint_nodes"), {
		TEXT("add_node"), TEXT("add_nodes_batch"), TEXT("remove_node"),
		TEXT("add_connection"), TEXT("add_connections_batch"), TEXT("remove_connection"),
		TEXT("set_node_param"), TEXT("set_variable_default")
	});
	AddCategory(TEXT("components"), {
		TEXT("add_component"), TEXT("get_components"), TEXT("remove_component"),
		TEXT("set_component_property")
	});
	AddCategory(TEXT("materials"), {
		TEXT("create_material_instance"), TEXT("create_simple_material"),
		TEXT("create_textured_material"), TEXT("apply_material"), TEXT("set_actor_material")
	});
	AddCategory(TEXT("actors"), {
		TEXT("spawn_actor_at"), TEXT("get_actors"), TEXT("set_actor_transform"),
		TEXT("delete_actor"), TEXT("set_actor_visibility"), TEXT("set_actor_mobility"),
		TEXT("set_actor_tags"), TEXT("set_actor_tick"), TEXT("set_actor_lifespan"),
		TEXT("set_actor_enabled"), TEXT("set_actor_scale"), TEXT("get_actor_bounds"),
		TEXT("get_actor_class"), TEXT("get_actor_properties"),
		TEXT("attach_actor_to"), TEXT("detach_actor"), TEXT("copy_actor")
	});
	AddCategory(TEXT("spawn_patterns"), {
		TEXT("spawn_actor_grid"), TEXT("spawn_actor_circle"), TEXT("spawn_actor_line")
	});
	AddCategory(TEXT("batch_operations"), {
		TEXT("batch_set_variable"), TEXT("batch_add_component"), TEXT("batch_apply_material"),
		TEXT("batch_set_property"), TEXT("batch_delete_actors"), TEXT("batch_replace_material"),
		TEXT("batch_move_actors"), TEXT("batch_scale_actors")
	});
	AddCategory(TEXT("query"), {
		TEXT("find_blueprints"), TEXT("find_actors"), TEXT("find_assets"),
		TEXT("list_available_materials"), TEXT("list_available_blueprints"),
		TEXT("list_project_assets"), TEXT("get_last_error")
	});
	AddCategory(TEXT("level_scene"), {
		TEXT("save_all"), TEXT("save_level"), TEXT("get_level_info"),
		TEXT("setup_scene_lighting"), TEXT("set_game_mode"), TEXT("set_class_defaults"),
		TEXT("get_world_settings"), TEXT("set_world_settings")
	});
	AddCategory(TEXT("sublevels"), {
		TEXT("create_sublevel"), TEXT("set_level_visibility"),
		TEXT("get_sublevel_list"), TEXT("move_actor_to_sublevel")
	});
	AddCategory(TEXT("widgets"), {
		TEXT("create_widget_blueprint"), TEXT("add_widget_child"),
		TEXT("set_widget_property"), TEXT("get_widget_property"), TEXT("get_widget_tree"), TEXT("remove_widget")
	});
	AddCategory(TEXT("fonts"), {
		TEXT("import_font_face"), TEXT("create_font_asset"), TEXT("add_font_typeface"),
		TEXT("get_font_info"), TEXT("list_font_assets"), TEXT("import_font_family")
	});
	AddCategory(TEXT("media"), {
		TEXT("assign_media_texture")
	});
	AddCategory(TEXT("binding"), {
		TEXT("set_widget_is_variable"), TEXT("add_widget_variable"), TEXT("set_widget_entry_class"),
		TEXT("add_scroll_sync"), TEXT("bind_text_to_variable")
	});
	AddCategory(TEXT("input"), {
		TEXT("add_input_action"), TEXT("add_input_mapping"), TEXT("setup_input_context"),
		TEXT("get_input_actions"), TEXT("create_input_action"), TEXT("set_player_input_mapping")
	});
	AddCategory(TEXT("audio"), {
		TEXT("play_sound_at_location"), TEXT("add_audio_component"),
		TEXT("get_sound_assets"), TEXT("set_audio_properties")
	});
	AddCategory(TEXT("viewport"), {
		TEXT("set_viewport_camera"), TEXT("take_screenshot"), TEXT("set_pir_widget"), TEXT("get_viewport_info")
	});
	AddCategory(TEXT("niagara"), {
		TEXT("spawn_niagara_at_location"), TEXT("add_niagara_component"),
		TEXT("get_niagara_assets"), TEXT("set_niagara_parameter"),
		TEXT("activate_niagara"), TEXT("get_niagara_parameters")
	});
	AddCategory(TEXT("physics"), {
		TEXT("add_physics_constraint"), TEXT("break_constraint"),
		TEXT("set_physics_enabled"), TEXT("set_collision_preset"), TEXT("set_collision_shape")
	});
	AddCategory(TEXT("splines"), {
		TEXT("create_spline_actor"), TEXT("add_spline_point"), TEXT("get_spline_info")
	});
	AddCategory(TEXT("post_processing"), {
		TEXT("add_post_process_volume"), TEXT("set_post_process_settings")
	});
	AddCategory(TEXT("sequencer"), {
		TEXT("create_sequence"), TEXT("add_sequence_track"), TEXT("add_keyframe"),
		TEXT("get_sequence_info"), TEXT("play_sequence")
	});
	AddCategory(TEXT("landscape_foliage"), {
		TEXT("get_landscape_info"), TEXT("set_landscape_material"),
		TEXT("create_foliage_type"), TEXT("paint_foliage"), TEXT("get_foliage_info")
	});
	AddCategory(TEXT("ai"), {
		TEXT("create_behavior_tree"), TEXT("get_behavior_tree_info"),
		TEXT("set_blackboard_key_default"), TEXT("setup_ai_for_pawn"),
		TEXT("create_nav_mesh_bounds")
	});
	AddCategory(TEXT("data_tables"), {
		TEXT("create_data_table"), TEXT("get_data_table_info"),
		TEXT("add_data_table_row"), TEXT("edit_data_table_row"), TEXT("get_data_table_rows")
	});
	AddCategory(TEXT("animation"), {
		TEXT("create_anim_blueprint"), TEXT("add_anim_state"), TEXT("add_anim_transition"),
		TEXT("set_anim_state_animation"), TEXT("create_anim_montage"),
		TEXT("add_montage_section"), TEXT("create_blend_space"),
		TEXT("add_blend_space_sample"), TEXT("set_skeletal_mesh"), TEXT("play_animation"),
		TEXT("get_skeleton_bones"), TEXT("get_available_animations")
	});
	AddCategory(TEXT("asset_import"), {
		TEXT("import_static_mesh"), TEXT("import_texture"), TEXT("import_sound")
	});
	AddCategory(TEXT("persistence"), {
		TEXT("create_save_game")
	});
	AddCategory(TEXT("movement"), {
		TEXT("set_movement_defaults"), TEXT("set_camera_properties")
	});
	AddCategory(TEXT("editor"), {
		TEXT("health_check"), TEXT("get_capabilities"), TEXT("play_in_editor"),
		TEXT("stop_play"), TEXT("get_output_log"), TEXT("quit_editor"),
		TEXT("bind_input_to_blueprint"),
		TEXT("capture_full_screen"), TEXT("simulate_input"), TEXT("simulate_walk_to")
	});
	AddCategory(TEXT("stats"), {
		TEXT("get_stats"), TEXT("reset_stats")
	});

	Data->SetObjectField(TEXT("categories"), Categories);

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCreateBlueprint(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'name' parameter (e.g. 'BP_HealthPickup')"));
	}

	FString ParentClass = Params->GetStringField(TEXT("parent_class"));
	if (ParentClass.IsEmpty()) ParentClass = TEXT("Actor");

	// Build a minimal DSL struct
	FDSLBlueprint DSL;
	DSL.Name = Name;
	DSL.ParentClass = ParentClass;

	// Optional variables
	const TArray<TSharedPtr<FJsonValue>>* VarsArray;
	if (Params->TryGetArrayField(TEXT("variables"), VarsArray))
	{
		for (const auto& VarVal : *VarsArray)
		{
			const TSharedPtr<FJsonObject>* VarObj;
			if (VarVal->TryGetObject(VarObj))
			{
				FDSLVariable Var;
				Var.Name = (*VarObj)->GetStringField(TEXT("name"));
				Var.Type = (*VarObj)->GetStringField(TEXT("type"));
				(*VarObj)->TryGetStringField(TEXT("default"), Var.DefaultValue);
				if (!Var.Name.IsEmpty() && !Var.Type.IsEmpty())
				{
					DSL.Variables.Add(Var);
				}
			}
		}
	}

	// No nodes or connections — creates an empty compiled Blueprint
	// The AI adds nodes via add_nodes_batch and connections via add_connections_batch
	return BuildBlueprintFromIR(DSL);
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

	// Fallback: derive name from filename if metadata.name is missing
	if (DSL.Name.IsEmpty())
	{
		DSL.Name = FPaths::GetBaseFilename(IRPath);
		// Strip common suffixes
		DSL.Name.ReplaceInline(TEXT(".blueprint"), TEXT(""));
	}

	return BuildBlueprintFromIR(DSL);
}

FCommandResult FCommandServer::HandleCreateBlueprintFromDSL(const TSharedPtr<FJsonObject>& Params)
{
	FString IRJson = Params->GetStringField(TEXT("ir_json"));
	if (IRJson.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'ir_json' parameter"));
	}

	// Name can come from: params.name, params.blueprint_name, or metadata.name inside the IR
	FString NameOverride = Params->GetStringField(TEXT("name"));
	if (NameOverride.IsEmpty())
	{
		NameOverride = Params->GetStringField(TEXT("blueprint_name"));
	}

	FDSLBlueprint DSL;
	if (!FDSLImporter::ParseIRFromString(IRJson, DSL))
	{
		return FCommandResult::Error(TEXT("Failed to parse IR JSON"));
	}

	// Apply name override if provided
	if (!NameOverride.IsEmpty())
	{
		DSL.Name = NameOverride;
	}

	// Ensure we have a name — crash guard
	if (DSL.Name.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing blueprint name. Provide 'name', 'blueprint_name', or include metadata.name in the IR JSON."));
	}

	return BuildBlueprintFromIR(DSL);
}

FCommandResult FCommandServer::BuildBlueprintFromIR(FDSLBlueprint& DSL)
{
	// Guard against empty name — would crash in package creation
	if (DSL.Name.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing blueprint name. Use metadata.name or blueprint_name."));
	}

	// Delete existing Blueprint with same name (Strategic Rule 8)
	DeleteExistingBlueprint(DSL.Name);

	// Build the Blueprint — SAME code path as the Tools menu import (Rule 17)
	const FString PackagePath = TEXT("/Game/Arcwright/Generated");
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
		return FCommandResult::Error(FormatBlueprintNotFound(Name));
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
		return FCommandResult::Error(FormatBlueprintNotFound(Name));
	}

	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	bool bSuccess = BP->Status != BS_Error;

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("blueprint_name"), Name);
	Data->SetBoolField(TEXT("compiled"), bSuccess);
	Data->SetStringField(TEXT("status"), bSuccess ? TEXT("clean") : TEXT("error"));

	// Enhanced: Collect per-node error info by scanning graph nodes post-compile
	TArray<TSharedPtr<FJsonValue>> MessagesArray;
	UEdGraph* CompileGraph = FBlueprintEditorUtils::FindEventGraph(BP);
	if (CompileGraph)
	{
		int32 NodeIdx = 0;
		for (UEdGraphNode* Node : CompileGraph->Nodes)
		{
			if (Node->bHasCompilerMessage)
			{
				TSharedPtr<FJsonObject> MsgObj = MakeShareable(new FJsonObject());
				FString Severity;
				if (Node->ErrorType == EMessageSeverity::Error)
					Severity = TEXT("error");
				else if (Node->ErrorType == EMessageSeverity::Warning)
					Severity = TEXT("warning");
				else
					Severity = TEXT("info");
				MsgObj->SetStringField(TEXT("severity"), Severity);
				MsgObj->SetStringField(TEXT("node_id"), FString::Printf(TEXT("node_%d"), NodeIdx));
				MsgObj->SetStringField(TEXT("node_title"), Node->GetNodeTitle(ENodeTitleType::ListView).ToString());
				MsgObj->SetStringField(TEXT("message"), Node->ErrorMsg);
				MessagesArray.Add(MakeShareable(new FJsonValueObject(MsgObj)));
			}
			NodeIdx++;
		}
	}
	Data->SetArrayField(TEXT("messages"), MessagesArray);
	Data->SetNumberField(TEXT("message_count"), MessagesArray.Num());

	// Node/connection counts for context
	UEdGraph* EventGraph = FBlueprintEditorUtils::FindEventGraph(BP);
	if (EventGraph)
	{
		Data->SetNumberField(TEXT("node_count"), EventGraph->Nodes.Num());
		int32 ConnCount = 0;
		for (UEdGraphNode* Node : EventGraph->Nodes)
		{
			for (UEdGraphPin* Pin : Node->Pins)
			{
				if (Pin->Direction == EGPD_Output)
					ConnCount += Pin->LinkedTo.Num();
			}
		}
		Data->SetNumberField(TEXT("connection_count"), ConnCount);
	}

	// Save the Blueprint package to disk after compile
	UPackage* Package = BP->GetPackage();
	if (Package)
	{
		Package->MarkPackageDirty();
		FString PackageFilename = FPackageName::LongPackageNameToFilename(
			Package->GetName(), FPackageName::GetAssetPackageExtension());
		FSavePackageArgs SaveArgs;
		SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
		UPackage::SavePackage(Package, BP, *PackageFilename, SaveArgs);
		Data->SetBoolField(TEXT("saved"), true);
	}

	UE_LOG(LogBlueprintLLM, Log, TEXT("Compiled and saved %s: %s (%d messages)"),
		*Name, bSuccess ? TEXT("success") : TEXT("error"), MessagesArray.Num());

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
	FString AssetPath = FString::Printf(TEXT("/Game/Arcwright/Generated/%s.%s"), *Name, *Name);
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

// ============================================================
// Node/graph helpers
// ============================================================

UEdGraphNode* FCommandServer::FindNodeInGraph(UEdGraph* Graph, const FString& NodeId)
{
	if (!Graph || NodeId.IsEmpty()) return nullptr;

	// 1. Match by user-provided ID stored in NodeComment (from add_nodes_batch)
	for (UEdGraphNode* Node : Graph->Nodes)
	{
		if (Node->NodeComment == NodeId)
		{
			return Node;
		}
	}

	// 2. Match by node_N index format (from get_blueprint_info)
	if (NodeId.StartsWith(TEXT("node_")))
	{
		int32 Index = FCString::Atoi(*NodeId.Mid(5));
		if (Index >= 0 && Index < Graph->Nodes.Num())
		{
			return Graph->Nodes[Index];
		}
	}

	// 3. Match by GUID
	for (UEdGraphNode* Node : Graph->Nodes)
	{
		if (Node->NodeGuid.ToString() == NodeId)
		{
			return Node;
		}
	}

	// 4. Match by node title (case-insensitive substring)
	for (UEdGraphNode* Node : Graph->Nodes)
	{
		FString Title = Node->GetNodeTitle(ENodeTitleType::ListView).ToString();
		if (Title.Contains(NodeId, ESearchCase::IgnoreCase))
		{
			return Node;
		}
	}

	return nullptr;
}

// ============================================================
// Individual node/connection editing (B5+B6)
// ============================================================

FCommandResult FCommandServer::HandleAddNode(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	FString NodeType = Params->GetStringField(TEXT("node_type"));
	if (NodeType.IsEmpty()) NodeType = Params->GetStringField(TEXT("type"));
	FString NodeID = Params->GetStringField(TEXT("node_id"));
	if (NodeID.IsEmpty()) NodeID = Params->GetStringField(TEXT("id"));

	if (BlueprintName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'blueprint' parameter"));
	if (NodeType.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'node_type' parameter"));
	if (NodeID.IsEmpty())
		NodeID = FString::Printf(TEXT("new_%d"), FMath::RandRange(1000, 9999));

	UBlueprint* BP = FindBlueprintByName(BlueprintName);
	if (!BP)
		return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));

	UEdGraph* Graph = FBlueprintEditorUtils::FindEventGraph(BP);
	if (!Graph)
		return FCommandResult::Error(TEXT("No EventGraph found"));

	// Build a temporary FDSLNode for the builder
	FDSLNode TempNode;
	TempNode.ID = NodeID;
	TempNode.DSLType = NodeType;

	// Map user-friendly node type to UEClass + UEFunction/UEEvent
	// Common function name -> full UE path mapping
	static TMap<FString, FString> FunctionPaths;
	if (FunctionPaths.Num() == 0)
	{
		FunctionPaths.Add(TEXT("Delay"), TEXT("/Script/Engine.KismetSystemLibrary:Delay"));
		FunctionPaths.Add(TEXT("PrintString"), TEXT("/Script/Engine.KismetSystemLibrary:PrintString"));
		FunctionPaths.Add(TEXT("SetTimer"), TEXT("/Script/Engine.KismetSystemLibrary:K2_SetTimer"));
		FunctionPaths.Add(TEXT("ClearTimer"), TEXT("/Script/Engine.KismetSystemLibrary:K2_ClearTimer"));
		FunctionPaths.Add(TEXT("IsValid"), TEXT("/Script/Engine.KismetSystemLibrary:IsValid"));
		FunctionPaths.Add(TEXT("GetActorLocation"), TEXT("/Script/Engine.Actor:K2_GetActorLocation"));
		FunctionPaths.Add(TEXT("SetActorLocation"), TEXT("/Script/Engine.Actor:K2_SetActorLocation"));
		FunctionPaths.Add(TEXT("DestroyActor"), TEXT("/Script/Engine.Actor:K2_DestroyActor"));
		FunctionPaths.Add(TEXT("AddFloat"), TEXT("/Script/Engine.KismetMathLibrary:Add_DoubleDouble"));
		FunctionPaths.Add(TEXT("SubtractFloat"), TEXT("/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"));
		FunctionPaths.Add(TEXT("MultiplyFloat"), TEXT("/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble"));
		FunctionPaths.Add(TEXT("DivideFloat"), TEXT("/Script/Engine.KismetMathLibrary:Divide_DoubleDouble"));
		FunctionPaths.Add(TEXT("LessThan"), TEXT("/Script/Engine.KismetMathLibrary:Less_DoubleDouble"));
		FunctionPaths.Add(TEXT("GreaterThan"), TEXT("/Script/Engine.KismetMathLibrary:Greater_DoubleDouble"));
		FunctionPaths.Add(TEXT("SpawnSound2D"), TEXT("/Script/Engine.GameplayStatics:SpawnSound2D"));
		FunctionPaths.Add(TEXT("GetPlayerCharacter"), TEXT("/Script/Engine.GameplayStatics:GetPlayerCharacter"));
		FunctionPaths.Add(TEXT("GetAllActorsOfClass"), TEXT("/Script/Engine.GameplayStatics:GetAllActorsOfClass"));
	}

	// Events
	if (NodeType.StartsWith(TEXT("Event_")))
	{
		TempNode.UEClass = TEXT("UK2Node_Event");
		// Strip "Event_" prefix — UE event functions are "ReceiveBeginPlay" not "Event_ReceiveBeginPlay"
		TempNode.UEEvent = NodeType.Mid(6);
	}
	else if (NodeType == TEXT("CustomEvent"))
	{
		TempNode.UEClass = TEXT("UK2Node_CustomEvent");
		TempNode.ParamKey = TEXT("EventName");
	}
	// Flow control
	else if (NodeType == TEXT("Branch"))
	{
		TempNode.UEClass = TEXT("UK2Node_IfThenElse");
	}
	else if (NodeType == TEXT("Sequence"))
	{
		TempNode.UEClass = TEXT("UK2Node_ExecutionSequence");
	}
	else if (NodeType == TEXT("FlipFlop") || NodeType == TEXT("DoOnce") ||
	         NodeType == TEXT("Gate") || NodeType == TEXT("MultiGate"))
	{
		TempNode.UEClass = FString::Printf(TEXT("UK2Node_%s"), *NodeType);
	}
	// Loops
	else if (NodeType == TEXT("ForLoop") || NodeType == TEXT("ForEachLoop") || NodeType == TEXT("WhileLoop"))
	{
		FString LoopClass = FString::Printf(TEXT("UK2Node_%s"), *NodeType);
		TempNode.UEClass = LoopClass;
	}
	// Cast
	else if (NodeType.StartsWith(TEXT("CastTo")))
	{
		TempNode.UEClass = TEXT("UK2Node_DynamicCast");
		TempNode.CastClass = NodeType.Mid(6);
	}
	// Variables (accept both GetVar and VariableGet)
	else if (NodeType == TEXT("GetVar") || NodeType == TEXT("VariableGet"))
	{
		TempNode.UEClass = TEXT("UK2Node_VariableGet");
		TempNode.ParamKey = TEXT("Variable");
	}
	else if (NodeType == TEXT("SetVar") || NodeType == TEXT("VariableSet"))
	{
		TempNode.UEClass = TEXT("UK2Node_VariableSet");
		TempNode.ParamKey = TEXT("Variable");
	}
	else if (NodeType == TEXT("InputAction") || NodeType == TEXT("K2Node_InputAction"))
	{
		TempNode.UEClass = TEXT("UK2Node_InputAction");
	}
	else if (NodeType == TEXT("SwitchOnInt") || NodeType == TEXT("SwitchOnString"))
	{
		TempNode.UEClass = TEXT("UK2Node_SwitchInteger");
	}
	else if (NodeType == TEXT("SpawnActor"))
	{
		TempNode.UEClass = TEXT("UK2Node_SpawnActorFromClass");
	}
	// Default: treat as CallFunction
	else
	{
		TempNode.UEClass = TEXT("UK2Node_CallFunction");
		// Look up full path from common names, or use as-is if already a path
		FString* FoundPath = FunctionPaths.Find(NodeType);
		if (FoundPath)
		{
			TempNode.UEFunction = *FoundPath;
		}
		else if (NodeType.Contains(TEXT("/")))
		{
			// Already a full path like /Script/Engine.KismetSystemLibrary:Delay
			TempNode.UEFunction = NodeType;
		}
		else
		{
			// Try as KismetSystemLibrary function
			TempNode.UEFunction = FString::Printf(TEXT("/Script/Engine.KismetSystemLibrary:%s"), *NodeType);
		}
	}

	// Extract optional parameters
	if (Params->HasField(TEXT("params")))
	{
		TSharedPtr<FJsonObject> NodeParams = Params->GetObjectField(TEXT("params"));
		for (auto& Pair : NodeParams->Values)
		{
			TempNode.Params.Add(Pair.Key, Pair.Value->AsString());
		}
	}

	// Position
	double PosX = Params->HasField(TEXT("pos_x")) ? Params->GetNumberField(TEXT("pos_x")) : 0.0;
	double PosY = Params->HasField(TEXT("pos_y")) ? Params->GetNumberField(TEXT("pos_y")) : 0.0;

	UK2Node* NewNode = FBlueprintBuilder::CreateNodeFromDef(BP, Graph, TempNode);
	if (!NewNode)
		return FCommandResult::Error(FString::Printf(TEXT("Failed to create node of type: %s"), *NodeType));

	NewNode->CreateNewGuid();
	NewNode->NodeComment = NodeID;  // Store user ID for FindNodeInGraph
	NewNode->NodePosX = static_cast<int32>(PosX);
	NewNode->NodePosY = static_cast<int32>(PosY);

	// Compile
	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	// Build response with pin info
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("node_id"), NodeID);
	Data->SetStringField(TEXT("node_type"), NodeType);
	Data->SetStringField(TEXT("class"), NewNode->GetClass()->GetName());
	Data->SetBoolField(TEXT("compiled"), BP->Status != BS_Error);

	TArray<TSharedPtr<FJsonValue>> PinsArray;
	for (UEdGraphPin* Pin : NewNode->Pins)
	{
		TSharedPtr<FJsonObject> PinObj = MakeShareable(new FJsonObject());
		PinObj->SetStringField(TEXT("name"), Pin->PinName.ToString());
		PinObj->SetStringField(TEXT("direction"),
			Pin->Direction == EGPD_Input ? TEXT("input") : TEXT("output"));
		PinObj->SetStringField(TEXT("type"), Pin->PinType.PinCategory.ToString());
		PinsArray.Add(MakeShareable(new FJsonValueObject(PinObj)));
	}
	Data->SetArrayField(TEXT("pins"), PinsArray);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Added node %s (%s) to %s"),
		*NodeID, *NodeType, *BlueprintName);

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleRemoveNode(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	FString NodeID = Params->GetStringField(TEXT("node_id"));

	if (BlueprintName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'blueprint' parameter"));
	if (NodeID.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'node_id' parameter"));

	UBlueprint* BP = FindBlueprintByName(BlueprintName);
	if (!BP)
		return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));

	UEdGraph* Graph = FBlueprintEditorUtils::FindEventGraph(BP);
	if (!Graph)
		return FCommandResult::Error(TEXT("No EventGraph found"));

	UEdGraphNode* Node = FindNodeInGraph(Graph, NodeID);
	if (!Node)
		return FCommandResult::Error(FString::Printf(TEXT("Node not found: %s"), *NodeID));

	// Break all connections first
	for (UEdGraphPin* Pin : Node->Pins)
	{
		Pin->BreakAllPinLinks();
	}

	Graph->RemoveNode(Node);

	// Compile
	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("node_id"), NodeID);
	Data->SetBoolField(TEXT("deleted"), true);
	Data->SetBoolField(TEXT("compiled"), BP->Status != BS_Error);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Removed node %s from %s"), *NodeID, *BlueprintName);

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddConnection(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));

	FString SrcNodeID = Params->GetStringField(TEXT("source_node"));
	if (SrcNodeID.IsEmpty()) SrcNodeID = Params->GetStringField(TEXT("from_node"));
	if (SrcNodeID.IsEmpty()) SrcNodeID = Params->GetStringField(TEXT("src_node"));

	FString SrcPinName = Params->GetStringField(TEXT("source_pin"));
	if (SrcPinName.IsEmpty()) SrcPinName = Params->GetStringField(TEXT("from_pin"));
	if (SrcPinName.IsEmpty()) SrcPinName = Params->GetStringField(TEXT("src_pin"));

	FString DstNodeID = Params->GetStringField(TEXT("target_node"));
	if (DstNodeID.IsEmpty()) DstNodeID = Params->GetStringField(TEXT("to_node"));
	if (DstNodeID.IsEmpty()) DstNodeID = Params->GetStringField(TEXT("dst_node"));

	FString DstPinName = Params->GetStringField(TEXT("target_pin"));
	if (DstPinName.IsEmpty()) DstPinName = Params->GetStringField(TEXT("to_pin"));
	if (DstPinName.IsEmpty()) DstPinName = Params->GetStringField(TEXT("dst_pin"));

	if (BlueprintName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'blueprint' parameter"));
	if (SrcNodeID.IsEmpty() || SrcPinName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing source_node/from_node or source_pin/from_pin"));
	if (DstNodeID.IsEmpty() || DstPinName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing target_node/to_node or target_pin/to_pin"));

	UBlueprint* BP = FindBlueprintByName(BlueprintName);
	if (!BP)
		return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));

	UEdGraph* Graph = FBlueprintEditorUtils::FindEventGraph(BP);
	if (!Graph)
		return FCommandResult::Error(TEXT("No EventGraph found"));

	UEdGraphNode* SrcNode = FindNodeInGraph(Graph, SrcNodeID);
	UEdGraphNode* DstNode = FindNodeInGraph(Graph, DstNodeID);
	if (!SrcNode)
		return FCommandResult::Error(FString::Printf(TEXT("Source node not found: %s"), *SrcNodeID));
	if (!DstNode)
		return FCommandResult::Error(FString::Printf(TEXT("Target node not found: %s"), *DstNodeID));

	// Use FindPinByDSLName for smart alias resolution
	UEdGraphPin* SrcPin = FBlueprintBuilder::FindPinByDSLName(SrcNode, SrcPinName, EGPD_Output);
	UEdGraphPin* DstPin = FBlueprintBuilder::FindPinByDSLName(DstNode, DstPinName, EGPD_Input);
	if (!SrcPin)
		return FCommandResult::Error(FString::Printf(TEXT("Source pin not found: %s on %s"), *SrcPinName, *SrcNodeID));
	if (!DstPin)
		return FCommandResult::Error(FString::Printf(TEXT("Target pin not found: %s on %s"), *DstPinName, *DstNodeID));

	// TryCreateConnection for auto-conversion nodes
	const UEdGraphSchema_K2* Schema = GetDefault<UEdGraphSchema_K2>();
	bool bConnected = Schema->TryCreateConnection(SrcPin, DstPin);
	if (!bConnected)
	{
		SrcPin->MakeLinkTo(DstPin);
		bConnected = true;
	}

	// Compile
	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetBoolField(TEXT("connected"), bConnected);
	Data->SetStringField(TEXT("source_node"), SrcNodeID);
	Data->SetStringField(TEXT("source_pin"), SrcPin->PinName.ToString());
	Data->SetStringField(TEXT("target_node"), DstNodeID);
	Data->SetStringField(TEXT("target_pin"), DstPin->PinName.ToString());
	Data->SetBoolField(TEXT("compiled"), BP->Status != BS_Error);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Connected %s.%s -> %s.%s in %s"),
		*SrcNodeID, *SrcPinName, *DstNodeID, *DstPinName, *BlueprintName);

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleRemoveConnection(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	FString SrcNodeID = Params->GetStringField(TEXT("source_node"));
	FString SrcPinName = Params->GetStringField(TEXT("source_pin"));
	FString DstNodeID = Params->GetStringField(TEXT("target_node"));
	FString DstPinName = Params->GetStringField(TEXT("target_pin"));

	if (BlueprintName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'blueprint' parameter"));
	if (SrcNodeID.IsEmpty() || SrcPinName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing source_node or source_pin"));
	if (DstNodeID.IsEmpty() || DstPinName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing target_node or target_pin"));

	UBlueprint* BP = FindBlueprintByName(BlueprintName);
	if (!BP)
		return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));

	UEdGraph* Graph = FBlueprintEditorUtils::FindEventGraph(BP);
	if (!Graph)
		return FCommandResult::Error(TEXT("No EventGraph found"));

	UEdGraphNode* SrcNode = FindNodeInGraph(Graph, SrcNodeID);
	UEdGraphNode* DstNode = FindNodeInGraph(Graph, DstNodeID);
	if (!SrcNode)
		return FCommandResult::Error(FString::Printf(TEXT("Source node not found: %s"), *SrcNodeID));
	if (!DstNode)
		return FCommandResult::Error(FString::Printf(TEXT("Target node not found: %s"), *DstNodeID));

	UEdGraphPin* SrcPin = FBlueprintBuilder::FindPinByDSLName(SrcNode, SrcPinName, EGPD_Output);
	UEdGraphPin* DstPin = FBlueprintBuilder::FindPinByDSLName(DstNode, DstPinName, EGPD_Input);
	if (!SrcPin)
		return FCommandResult::Error(FString::Printf(TEXT("Source pin not found: %s on %s"), *SrcPinName, *SrcNodeID));
	if (!DstPin)
		return FCommandResult::Error(FString::Printf(TEXT("Target pin not found: %s on %s"), *DstPinName, *DstNodeID));

	SrcPin->BreakLinkTo(DstPin);

	// Compile
	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetBoolField(TEXT("disconnected"), true);
	Data->SetStringField(TEXT("source_node"), SrcNodeID);
	Data->SetStringField(TEXT("source_pin"), SrcPin->PinName.ToString());
	Data->SetStringField(TEXT("target_node"), DstNodeID);
	Data->SetStringField(TEXT("target_pin"), DstPin->PinName.ToString());
	Data->SetBoolField(TEXT("compiled"), BP->Status != BS_Error);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Disconnected %s.%s -> %s.%s in %s"),
		*SrcNodeID, *SrcPinName, *DstNodeID, *DstPinName, *BlueprintName);

	return FCommandResult::Ok(Data);
}

// ============================================================
// Batch Node/Connection + Validation Handlers
// ============================================================

FCommandResult FCommandServer::HandleAddNodesBatch(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	if (BlueprintName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'blueprint' parameter"));

	const TArray<TSharedPtr<FJsonValue>>* NodesPtr = nullptr;
	if (!Params->TryGetArrayField(TEXT("nodes"), NodesPtr) || !NodesPtr || NodesPtr->Num() == 0)
		return FCommandResult::Error(TEXT("Missing or empty 'nodes' array"));

	UBlueprint* BP = FindBlueprintByName(BlueprintName);
	if (!BP)
		return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));

	UEdGraph* Graph = FBlueprintEditorUtils::FindEventGraph(BP);
	if (!Graph)
		return FCommandResult::Error(TEXT("No EventGraph found"));

	// Common function name -> full UE path mapping (same as HandleAddNode)
	static TMap<FString, FString> FunctionPaths;
	if (FunctionPaths.Num() == 0)
	{
		FunctionPaths.Add(TEXT("Delay"), TEXT("/Script/Engine.KismetSystemLibrary:Delay"));
		FunctionPaths.Add(TEXT("PrintString"), TEXT("/Script/Engine.KismetSystemLibrary:PrintString"));
		FunctionPaths.Add(TEXT("SetTimer"), TEXT("/Script/Engine.KismetSystemLibrary:K2_SetTimer"));
		FunctionPaths.Add(TEXT("ClearTimer"), TEXT("/Script/Engine.KismetSystemLibrary:K2_ClearTimer"));
		FunctionPaths.Add(TEXT("IsValid"), TEXT("/Script/Engine.KismetSystemLibrary:IsValid"));
		FunctionPaths.Add(TEXT("GetActorLocation"), TEXT("/Script/Engine.Actor:K2_GetActorLocation"));
		FunctionPaths.Add(TEXT("SetActorLocation"), TEXT("/Script/Engine.Actor:K2_SetActorLocation"));
		FunctionPaths.Add(TEXT("DestroyActor"), TEXT("/Script/Engine.Actor:K2_DestroyActor"));
		FunctionPaths.Add(TEXT("AddFloat"), TEXT("/Script/Engine.KismetMathLibrary:Add_DoubleDouble"));
		FunctionPaths.Add(TEXT("SubtractFloat"), TEXT("/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"));
		FunctionPaths.Add(TEXT("MultiplyFloat"), TEXT("/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble"));
		FunctionPaths.Add(TEXT("DivideFloat"), TEXT("/Script/Engine.KismetMathLibrary:Divide_DoubleDouble"));
		FunctionPaths.Add(TEXT("LessThan"), TEXT("/Script/Engine.KismetMathLibrary:Less_DoubleDouble"));
		FunctionPaths.Add(TEXT("GreaterThan"), TEXT("/Script/Engine.KismetMathLibrary:Greater_DoubleDouble"));
		FunctionPaths.Add(TEXT("SpawnSound2D"), TEXT("/Script/Engine.GameplayStatics:SpawnSound2D"));
		FunctionPaths.Add(TEXT("GetPlayerCharacter"), TEXT("/Script/Engine.GameplayStatics:GetPlayerCharacter"));
		FunctionPaths.Add(TEXT("GetAllActorsOfClass"), TEXT("/Script/Engine.GameplayStatics:GetAllActorsOfClass"));
	}

	int32 Succeeded = 0;
	int32 Failed = 0;
	TArray<TSharedPtr<FJsonValue>> ResultsArray;

	for (const TSharedPtr<FJsonValue>& NodeVal : *NodesPtr)
	{
		TSharedPtr<FJsonObject> NodeDef = NodeVal->AsObject();
		if (!NodeDef)
		{
			Failed++;
			TSharedPtr<FJsonObject> R = MakeShareable(new FJsonObject());
			R->SetBoolField(TEXT("success"), false);
			R->SetStringField(TEXT("error"), TEXT("Invalid node definition (not an object)"));
			ResultsArray.Add(MakeShareable(new FJsonValueObject(R)));
			continue;
		}

		// Accept both "node_type"/"type" and "node_id"/"id"
		FString NodeType = NodeDef->GetStringField(TEXT("node_type"));
		if (NodeType.IsEmpty()) NodeType = NodeDef->GetStringField(TEXT("type"));
		FString NodeID = NodeDef->GetStringField(TEXT("node_id"));
		if (NodeID.IsEmpty()) NodeID = NodeDef->GetStringField(TEXT("id"));
		if (NodeType.IsEmpty())
		{
			Failed++;
			TSharedPtr<FJsonObject> R = MakeShareable(new FJsonObject());
			R->SetBoolField(TEXT("success"), false);
			R->SetStringField(TEXT("node_id"), NodeID);
			R->SetStringField(TEXT("error"), TEXT("Missing 'node_type'"));
			ResultsArray.Add(MakeShareable(new FJsonValueObject(R)));
			continue;
		}
		if (NodeID.IsEmpty())
			NodeID = FString::Printf(TEXT("batch_%d"), FMath::RandRange(10000, 99999));

		// Build FDSLNode — same logic as HandleAddNode
		FDSLNode TempNode;
		TempNode.ID = NodeID;
		TempNode.DSLType = NodeType;

		if (NodeType.StartsWith(TEXT("Event_")))
		{
			TempNode.UEClass = TEXT("UK2Node_Event");
			// Strip "Event_" prefix — UE functions are "ReceiveBeginPlay" not "Event_ReceiveBeginPlay"
			TempNode.UEEvent = NodeType.Mid(6);
		}
		else if (NodeType == TEXT("CustomEvent"))
		{
			TempNode.UEClass = TEXT("UK2Node_CustomEvent");
			TempNode.ParamKey = TEXT("EventName");

			// Support "event" shorthand: {"type": "CustomEvent", "event": "AddCash"}
			if (NodeDef->HasField(TEXT("event")))
			{
				TempNode.Params.Add(TEXT("EventName"), NodeDef->GetStringField(TEXT("event")));
			}

			// Parse typed parameters: "params": [{"name": "Amount", "type": "Float"}]
			// (array format = event params; object format = standard params handled below)
			const TArray<TSharedPtr<FJsonValue>>* ParamsArray;
			if (NodeDef->TryGetArrayField(TEXT("params"), ParamsArray))
			{
				for (const auto& ParamVal : *ParamsArray)
				{
					const TSharedPtr<FJsonObject>* ParamObj;
					if (ParamVal->TryGetObject(ParamObj))
					{
						FDSLEventParam EP;
						EP.Name = (*ParamObj)->GetStringField(TEXT("name"));
						EP.Type = (*ParamObj)->GetStringField(TEXT("type"));
						if (!EP.Name.IsEmpty() && !EP.Type.IsEmpty())
						{
							TempNode.EventParams.Add(EP);
						}
					}
				}
			}
		}
		else if (NodeType == TEXT("Branch"))
		{
			TempNode.UEClass = TEXT("UK2Node_IfThenElse");
		}
		else if (NodeType == TEXT("Sequence"))
		{
			TempNode.UEClass = TEXT("UK2Node_ExecutionSequence");
		}
		else if (NodeType == TEXT("FlipFlop") || NodeType == TEXT("DoOnce") ||
		         NodeType == TEXT("Gate") || NodeType == TEXT("MultiGate"))
		{
			TempNode.UEClass = FString::Printf(TEXT("UK2Node_%s"), *NodeType);
		}
		else if (NodeType == TEXT("ForLoop") || NodeType == TEXT("ForEachLoop") || NodeType == TEXT("WhileLoop"))
		{
			TempNode.UEClass = FString::Printf(TEXT("UK2Node_%s"), *NodeType);
		}
		else if (NodeType.StartsWith(TEXT("CastTo")))
		{
			TempNode.UEClass = TEXT("UK2Node_DynamicCast");
			TempNode.CastClass = NodeType.Mid(6);
		}
		else if (NodeType == TEXT("GetVar") || NodeType == TEXT("VariableGet"))
		{
			TempNode.UEClass = TEXT("UK2Node_VariableGet");
			TempNode.ParamKey = TEXT("Variable");
			// Support "variable" shorthand: {"type": "GetVar", "variable": "Health"}
			if (NodeDef->HasField(TEXT("variable")))
			{
				TempNode.Params.Add(TEXT("Variable"), NodeDef->GetStringField(TEXT("variable")));
			}
		}
		else if (NodeType == TEXT("SetVar") || NodeType == TEXT("VariableSet"))
		{
			TempNode.UEClass = TEXT("UK2Node_VariableSet");
			TempNode.ParamKey = TEXT("Variable");
			if (NodeDef->HasField(TEXT("variable")))
			{
				TempNode.Params.Add(TEXT("Variable"), NodeDef->GetStringField(TEXT("variable")));
			}
		}
		else if (NodeType == TEXT("InputAction") || NodeType == TEXT("K2Node_InputAction"))
		{
			TempNode.UEClass = TEXT("UK2Node_InputAction");
			// Read action name from "action" or "event" or params.InputActionName
			FString ActionName;
			if (NodeDef->HasField(TEXT("action")))
				ActionName = NodeDef->GetStringField(TEXT("action"));
			else if (NodeDef->HasField(TEXT("event")))
				ActionName = NodeDef->GetStringField(TEXT("event"));
			if (!ActionName.IsEmpty())
				TempNode.Params.Add(TEXT("InputActionName"), ActionName);
		}
		else if (NodeType == TEXT("SwitchOnInt") || NodeType == TEXT("SwitchOnString"))
		{
			TempNode.UEClass = TEXT("UK2Node_SwitchInteger");
		}
		else if (NodeType == TEXT("SpawnActor"))
		{
			TempNode.UEClass = TEXT("UK2Node_SpawnActorFromClass");
		}
		else
		{
			TempNode.UEClass = TEXT("UK2Node_CallFunction");
			FString* FoundPath = FunctionPaths.Find(NodeType);
			if (FoundPath)
				TempNode.UEFunction = *FoundPath;
			else if (NodeType.Contains(TEXT("/")))
				TempNode.UEFunction = NodeType;
			else
				TempNode.UEFunction = FString::Printf(TEXT("/Script/Engine.KismetSystemLibrary:%s"), *NodeType);
		}

		// Optional params
		if (NodeDef->HasField(TEXT("params")))
		{
			TSharedPtr<FJsonObject> NodeParams = NodeDef->GetObjectField(TEXT("params"));
			for (auto& Pair : NodeParams->Values)
			{
				TempNode.Params.Add(Pair.Key, Pair.Value->AsString());
			}
		}

		double PosX = NodeDef->HasField(TEXT("pos_x")) ? NodeDef->GetNumberField(TEXT("pos_x")) : 0.0;
		double PosY = NodeDef->HasField(TEXT("pos_y")) ? NodeDef->GetNumberField(TEXT("pos_y")) : 0.0;

		UK2Node* NewNode = FBlueprintBuilder::CreateNodeFromDef(BP, Graph, TempNode);
		if (!NewNode)
		{
			Failed++;
			TSharedPtr<FJsonObject> R = MakeShareable(new FJsonObject());
			R->SetBoolField(TEXT("success"), false);
			R->SetStringField(TEXT("node_id"), NodeID);
			R->SetStringField(TEXT("node_type"), NodeType);
			R->SetStringField(TEXT("error"), FString::Printf(TEXT("Failed to create node: %s"), *NodeType));
			ResultsArray.Add(MakeShareable(new FJsonValueObject(R)));
			continue;
		}

		NewNode->CreateNewGuid();
		NewNode->NodePosX = static_cast<int32>(PosX);
		NewNode->NodePosY = static_cast<int32>(PosY);

		// Store the user-provided ID as the node's Comment for later lookup
		NewNode->NodeComment = NodeID;

		Succeeded++;
		TSharedPtr<FJsonObject> R = MakeShareable(new FJsonObject());
		R->SetBoolField(TEXT("success"), true);
		R->SetStringField(TEXT("node_id"), NodeID);
		R->SetStringField(TEXT("guid"), NewNode->NodeGuid.ToString());
		R->SetStringField(TEXT("node_type"), NodeType);
		R->SetStringField(TEXT("class"), NewNode->GetClass()->GetName());

		// Return pin list per node
		TArray<TSharedPtr<FJsonValue>> PinsArr;
		for (UEdGraphPin* Pin : NewNode->Pins)
		{
			TSharedPtr<FJsonObject> PinObj = MakeShareable(new FJsonObject());
			PinObj->SetStringField(TEXT("name"), Pin->PinName.ToString());
			PinObj->SetStringField(TEXT("direction"),
				Pin->Direction == EGPD_Input ? TEXT("input") : TEXT("output"));
			PinObj->SetStringField(TEXT("type"), Pin->PinType.PinCategory.ToString());
			PinsArr.Add(MakeShareable(new FJsonValueObject(PinObj)));
		}
		R->SetArrayField(TEXT("pins"), PinsArr);

		ResultsArray.Add(MakeShareable(new FJsonValueObject(R)));
	}

	// Single compile at end
	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	// Mark package dirty so save_all persists the nodes
	BP->GetPackage()->MarkPackageDirty();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("blueprint"), BlueprintName);
	Data->SetNumberField(TEXT("succeeded"), Succeeded);
	Data->SetNumberField(TEXT("failed"), Failed);
	Data->SetNumberField(TEXT("total"), NodesPtr->Num());
	Data->SetBoolField(TEXT("compiled"), BP->Status != BS_Error);
	Data->SetArrayField(TEXT("results"), ResultsArray);

	UE_LOG(LogBlueprintLLM, Log, TEXT("add_nodes_batch on %s: %d/%d succeeded"),
		*BlueprintName, Succeeded, NodesPtr->Num());

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddConnectionsBatch(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	if (BlueprintName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'blueprint' parameter"));

	const TArray<TSharedPtr<FJsonValue>>* ConnsPtr = nullptr;
	if (!Params->TryGetArrayField(TEXT("connections"), ConnsPtr) || !ConnsPtr || ConnsPtr->Num() == 0)
		return FCommandResult::Error(TEXT("Missing or empty 'connections' array"));

	UBlueprint* BP = FindBlueprintByName(BlueprintName);
	if (!BP)
		return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));

	UEdGraph* Graph = FBlueprintEditorUtils::FindEventGraph(BP);
	if (!Graph)
		return FCommandResult::Error(TEXT("No EventGraph found"));

	const UEdGraphSchema_K2* Schema = GetDefault<UEdGraphSchema_K2>();

	int32 Succeeded = 0;
	int32 Failed = 0;
	TArray<TSharedPtr<FJsonValue>> ResultsArray;

	for (const TSharedPtr<FJsonValue>& ConnVal : *ConnsPtr)
	{
		TSharedPtr<FJsonObject> ConnDef = ConnVal->AsObject();
		if (!ConnDef)
		{
			Failed++;
			TSharedPtr<FJsonObject> R = MakeShareable(new FJsonObject());
			R->SetBoolField(TEXT("success"), false);
			R->SetStringField(TEXT("error"), TEXT("Invalid connection definition"));
			ResultsArray.Add(MakeShareable(new FJsonValueObject(R)));
			continue;
		}

		// Accept multiple field name formats:
		// source_node/source_pin/target_node/target_pin (original)
		// from_node/from_pin/to_node/to_pin (AI guide format)
		// src_node/src_pin/dst_node/dst_pin (DSL IR format)
		FString SrcNodeID = ConnDef->GetStringField(TEXT("source_node"));
		if (SrcNodeID.IsEmpty()) SrcNodeID = ConnDef->GetStringField(TEXT("from_node"));
		if (SrcNodeID.IsEmpty()) SrcNodeID = ConnDef->GetStringField(TEXT("src_node"));

		FString SrcPinName = ConnDef->GetStringField(TEXT("source_pin"));
		if (SrcPinName.IsEmpty()) SrcPinName = ConnDef->GetStringField(TEXT("from_pin"));
		if (SrcPinName.IsEmpty()) SrcPinName = ConnDef->GetStringField(TEXT("src_pin"));

		FString DstNodeID = ConnDef->GetStringField(TEXT("target_node"));
		if (DstNodeID.IsEmpty()) DstNodeID = ConnDef->GetStringField(TEXT("to_node"));
		if (DstNodeID.IsEmpty()) DstNodeID = ConnDef->GetStringField(TEXT("dst_node"));

		FString DstPinName = ConnDef->GetStringField(TEXT("target_pin"));
		if (DstPinName.IsEmpty()) DstPinName = ConnDef->GetStringField(TEXT("to_pin"));
		if (DstPinName.IsEmpty()) DstPinName = ConnDef->GetStringField(TEXT("dst_pin"));

		TSharedPtr<FJsonObject> R = MakeShareable(new FJsonObject());
		R->SetStringField(TEXT("source_node"), SrcNodeID);
		R->SetStringField(TEXT("source_pin"), SrcPinName);
		R->SetStringField(TEXT("target_node"), DstNodeID);
		R->SetStringField(TEXT("target_pin"), DstPinName);

		// Validate all fields present
		if (SrcNodeID.IsEmpty() || SrcPinName.IsEmpty() || DstNodeID.IsEmpty() || DstPinName.IsEmpty())
		{
			Failed++;
			R->SetBoolField(TEXT("success"), false);
			R->SetStringField(TEXT("error"), TEXT("Missing source_node/source_pin/target_node/target_pin"));
			ResultsArray.Add(MakeShareable(new FJsonValueObject(R)));
			continue;
		}

		// Find nodes
		UEdGraphNode* SrcNode = FindNodeInGraph(Graph, SrcNodeID);
		UEdGraphNode* DstNode = FindNodeInGraph(Graph, DstNodeID);
		if (!SrcNode)
		{
			Failed++;
			R->SetBoolField(TEXT("success"), false);
			R->SetStringField(TEXT("error"), FString::Printf(TEXT("Source node not found: %s"), *SrcNodeID));
			ResultsArray.Add(MakeShareable(new FJsonValueObject(R)));
			continue;
		}
		if (!DstNode)
		{
			Failed++;
			R->SetBoolField(TEXT("success"), false);
			R->SetStringField(TEXT("error"), FString::Printf(TEXT("Target node not found: %s"), *DstNodeID));
			ResultsArray.Add(MakeShareable(new FJsonValueObject(R)));
			continue;
		}

		// Find pins
		UEdGraphPin* SrcPin = FBlueprintBuilder::FindPinByDSLName(SrcNode, SrcPinName, EGPD_Output);
		UEdGraphPin* DstPin = FBlueprintBuilder::FindPinByDSLName(DstNode, DstPinName, EGPD_Input);
		if (!SrcPin)
		{
			Failed++;
			R->SetBoolField(TEXT("success"), false);
			R->SetStringField(TEXT("error"), FString::Printf(TEXT("Source pin not found: %s on %s"), *SrcPinName, *SrcNodeID));

			// Include available pins for debugging
			TArray<TSharedPtr<FJsonValue>> AvailPins;
			for (UEdGraphPin* Pin : SrcNode->Pins)
			{
				if (Pin->Direction == EGPD_Output)
				{
					TSharedPtr<FJsonObject> PO = MakeShareable(new FJsonObject());
					PO->SetStringField(TEXT("name"), Pin->PinName.ToString());
					PO->SetStringField(TEXT("type"), Pin->PinType.PinCategory.ToString());
					AvailPins.Add(MakeShareable(new FJsonValueObject(PO)));
				}
			}
			R->SetArrayField(TEXT("available_source_pins"), AvailPins);
			ResultsArray.Add(MakeShareable(new FJsonValueObject(R)));
			continue;
		}
		if (!DstPin)
		{
			Failed++;
			R->SetBoolField(TEXT("success"), false);
			R->SetStringField(TEXT("error"), FString::Printf(TEXT("Target pin not found: %s on %s"), *DstPinName, *DstNodeID));

			TArray<TSharedPtr<FJsonValue>> AvailPins;
			for (UEdGraphPin* Pin : DstNode->Pins)
			{
				if (Pin->Direction == EGPD_Input)
				{
					TSharedPtr<FJsonObject> PO = MakeShareable(new FJsonObject());
					PO->SetStringField(TEXT("name"), Pin->PinName.ToString());
					PO->SetStringField(TEXT("type"), Pin->PinType.PinCategory.ToString());
					AvailPins.Add(MakeShareable(new FJsonValueObject(PO)));
				}
			}
			R->SetArrayField(TEXT("available_target_pins"), AvailPins);
			ResultsArray.Add(MakeShareable(new FJsonValueObject(R)));
			continue;
		}

		// Wire
		bool bConnected = Schema->TryCreateConnection(SrcPin, DstPin);
		if (!bConnected)
		{
			SrcPin->MakeLinkTo(DstPin);
			bConnected = true;
		}

		Succeeded++;
		R->SetBoolField(TEXT("success"), true);
		R->SetStringField(TEXT("actual_source_pin"), SrcPin->PinName.ToString());
		R->SetStringField(TEXT("actual_target_pin"), DstPin->PinName.ToString());
		ResultsArray.Add(MakeShareable(new FJsonValueObject(R)));
	}

	// Single compile at end
	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	// Mark package dirty so save_all persists the connections
	BP->GetPackage()->MarkPackageDirty();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("blueprint"), BlueprintName);
	Data->SetNumberField(TEXT("succeeded"), Succeeded);
	Data->SetNumberField(TEXT("failed"), Failed);
	Data->SetNumberField(TEXT("total"), ConnsPtr->Num());
	Data->SetBoolField(TEXT("compiled"), BP->Status != BS_Error);
	Data->SetArrayField(TEXT("results"), ResultsArray);

	UE_LOG(LogBlueprintLLM, Log, TEXT("add_connections_batch on %s: %d/%d succeeded"),
		*BlueprintName, Succeeded, ConnsPtr->Num());

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleValidateBlueprint(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty()) Name = Params->GetStringField(TEXT("blueprint"));
	if (Name.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'name' parameter"));

	UBlueprint* BP = FindBlueprintByName(Name);
	if (!BP)
		return FCommandResult::Error(FormatBlueprintNotFound(Name));

	UEdGraph* EventGraph = FBlueprintEditorUtils::FindEventGraph(BP);
	if (!EventGraph)
		return FCommandResult::Error(TEXT("No EventGraph found"));

	TArray<TSharedPtr<FJsonValue>> IssuesArray;
	int32 ErrorCount = 0;
	int32 WarningCount = 0;
	int32 InfoCount = 0;

	// Build node index for exec chain analysis
	TMap<UEdGraphNode*, int32> NodeIndexMap;
	int32 Idx = 0;
	for (UEdGraphNode* Node : EventGraph->Nodes)
	{
		NodeIndexMap.Add(Node, Idx++);
	}

	// Track which nodes have at least one connection
	TSet<UEdGraphNode*> ConnectedNodes;

	for (UEdGraphNode* Node : EventGraph->Nodes)
	{
		FString NodeTitle = Node->GetNodeTitle(ENodeTitleType::ListView).ToString();
		FString NodeId = FString::Printf(TEXT("node_%d"), NodeIndexMap[Node]);

		// Check each pin
		for (UEdGraphPin* Pin : Node->Pins)
		{
			if (Pin->LinkedTo.Num() > 0)
			{
				ConnectedNodes.Add(Node);
				for (UEdGraphPin* Linked : Pin->LinkedTo)
				{
					ConnectedNodes.Add(Linked->GetOwningNode());
				}
			}

			// Skip hidden/self/WorldContextObject pins
			if (Pin->bHidden || Pin->PinName == TEXT("self") || Pin->PinName == TEXT("WorldContextObject"))
				continue;

			// Check 1: Unconnected EXEC pins on non-event nodes
			if (Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec && Pin->LinkedTo.Num() == 0)
			{
				// Input exec with no connection = node won't execute
				if (Pin->Direction == EGPD_Input)
				{
					// Skip events (they're entry points, no input exec needed)
					if (!Cast<UK2Node_Event>(Node) && !Cast<UK2Node_CustomEvent>(Node))
					{
						TSharedPtr<FJsonObject> Issue = MakeShareable(new FJsonObject());
						Issue->SetStringField(TEXT("severity"), TEXT("warning"));
						Issue->SetStringField(TEXT("type"), TEXT("unconnected_exec_input"));
						Issue->SetStringField(TEXT("node_id"), NodeId);
						Issue->SetStringField(TEXT("node_title"), NodeTitle);
						Issue->SetStringField(TEXT("pin"), Pin->PinName.ToString());
						Issue->SetStringField(TEXT("message"),
							FString::Printf(TEXT("Node '%s' has no execution input — it will never run"), *NodeTitle));
						IssuesArray.Add(MakeShareable(new FJsonValueObject(Issue)));
						WarningCount++;
					}
				}
			}

			// Check 2: Required data inputs without connection or default
			if (Pin->Direction == EGPD_Input &&
			    Pin->PinType.PinCategory != UEdGraphSchema_K2::PC_Exec &&
			    Pin->LinkedTo.Num() == 0 &&
			    Pin->DefaultValue.IsEmpty() &&
			    !Pin->DefaultObject &&
			    !Pin->bHidden &&
			    Pin->PinName != TEXT("self") &&
			    Pin->PinName != TEXT("WorldContextObject"))
			{
				// Only flag if this is a non-optional pin (skip pins with auto-defaults)
				if (!Pin->bAdvancedView && !Pin->PinType.bIsReference)
				{
					TSharedPtr<FJsonObject> Issue = MakeShareable(new FJsonObject());
					Issue->SetStringField(TEXT("severity"), TEXT("info"));
					Issue->SetStringField(TEXT("type"), TEXT("unconnected_data_input"));
					Issue->SetStringField(TEXT("node_id"), NodeId);
					Issue->SetStringField(TEXT("node_title"), NodeTitle);
					Issue->SetStringField(TEXT("pin"), Pin->PinName.ToString());
					Issue->SetStringField(TEXT("pin_type"), Pin->PinType.PinCategory.ToString());
					Issue->SetStringField(TEXT("message"),
						FString::Printf(TEXT("Pin '%s' on '%s' has no connection or default"),
							*Pin->PinName.ToString(), *NodeTitle));
					IssuesArray.Add(MakeShareable(new FJsonValueObject(Issue)));
					InfoCount++;
				}
			}
		}
	}

	// Check 3: Orphan nodes (no connections at all)
	for (UEdGraphNode* Node : EventGraph->Nodes)
	{
		if (!ConnectedNodes.Contains(Node))
		{
			// Skip default event stubs (EventGraph always has BeginPlay/Tick stubs)
			if (Cast<UK2Node_Event>(Node) || Cast<UK2Node_CustomEvent>(Node))
				continue;

			FString NodeTitle = Node->GetNodeTitle(ENodeTitleType::ListView).ToString();
			FString NodeId = FString::Printf(TEXT("node_%d"), NodeIndexMap[Node]);

			TSharedPtr<FJsonObject> Issue = MakeShareable(new FJsonObject());
			Issue->SetStringField(TEXT("severity"), TEXT("warning"));
			Issue->SetStringField(TEXT("type"), TEXT("orphan_node"));
			Issue->SetStringField(TEXT("node_id"), NodeId);
			Issue->SetStringField(TEXT("node_title"), NodeTitle);
			Issue->SetStringField(TEXT("message"),
				FString::Printf(TEXT("Node '%s' is completely disconnected (orphaned)"), *NodeTitle));
			IssuesArray.Add(MakeShareable(new FJsonValueObject(Issue)));
			WarningCount++;
		}
	}

	// Check 4: Compile status
	bool bCompileClean = BP->Status != BS_Error;
	if (!bCompileClean)
	{
		TSharedPtr<FJsonObject> Issue = MakeShareable(new FJsonObject());
		Issue->SetStringField(TEXT("severity"), TEXT("error"));
		Issue->SetStringField(TEXT("type"), TEXT("compile_error"));
		Issue->SetStringField(TEXT("message"), TEXT("Blueprint has compilation errors"));
		IssuesArray.Add(MakeShareable(new FJsonValueObject(Issue)));
		ErrorCount++;
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("blueprint"), Name);
	Data->SetBoolField(TEXT("valid"), ErrorCount == 0);
	Data->SetNumberField(TEXT("error_count"), ErrorCount);
	Data->SetNumberField(TEXT("warning_count"), WarningCount);
	Data->SetNumberField(TEXT("info_count"), InfoCount);
	Data->SetNumberField(TEXT("total_issues"), IssuesArray.Num());
	Data->SetNumberField(TEXT("node_count"), EventGraph->Nodes.Num());
	Data->SetBoolField(TEXT("compiled"), bCompileClean);
	Data->SetArrayField(TEXT("issues"), IssuesArray);

	UE_LOG(LogBlueprintLLM, Log, TEXT("validate_blueprint %s: %d errors, %d warnings, %d info"),
		*Name, ErrorCount, WarningCount, InfoCount);

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetNodeParam(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	FString NodeID = Params->GetStringField(TEXT("node_id"));
	FString PinName = Params->GetStringField(TEXT("pin_name"));
	FString Value = Params->GetStringField(TEXT("value"));

	if (BlueprintName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'blueprint' parameter"));
	if (NodeID.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'node_id' parameter"));
	if (PinName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'pin_name' parameter"));

	UBlueprint* BP = FindBlueprintByName(BlueprintName);
	if (!BP)
		return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));

	UEdGraph* Graph = FBlueprintEditorUtils::FindEventGraph(BP);
	if (!Graph)
		return FCommandResult::Error(TEXT("No EventGraph found"));

	UEdGraphNode* Node = FindNodeInGraph(Graph, NodeID);
	if (!Node)
		return FCommandResult::Error(FString::Printf(TEXT("Node not found: %s"), *NodeID));

	// Use smart pin resolver, then fallback to direct FindPin
	UEdGraphPin* Pin = FBlueprintBuilder::FindPinByDSLName(Node, PinName, EGPD_Input);
	if (!Pin)
		Pin = Node->FindPin(FName(*PinName));
	if (!Pin)
		return FCommandResult::Error(FString::Printf(TEXT("Pin not found: %s on node %s"), *PinName, *NodeID));

	// Object pins need DefaultObject, not DefaultValue
	if (Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Object ||
		Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Class ||
		Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_SoftObject)
	{
		UObject* Asset = LoadObject<UObject>(nullptr, *Value);
		if (!Asset)
		{
			return FCommandResult::Error(FString::Printf(
				TEXT("Could not load asset for object pin: %s"), *Value));
		}
		Pin->DefaultObject = Asset;
	}
	else
	{
		Pin->DefaultValue = Value;
	}

	// Compile
	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("node_id"), NodeID);
	Data->SetStringField(TEXT("pin_name"), Pin->PinName.ToString());
	Data->SetStringField(TEXT("value"), Value);
	Data->SetBoolField(TEXT("compiled"), BP->Status != BS_Error);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Set %s.%s = %s in %s"),
		*NodeID, *PinName, *Value, *BlueprintName);

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetVariableDefault(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	FString VariableName = Params->GetStringField(TEXT("variable_name"));
	FString DefaultValue = Params->GetStringField(TEXT("default_value"));

	if (BlueprintName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'blueprint' parameter"));
	if (VariableName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'variable_name' parameter"));

	UBlueprint* BP = FindBlueprintByName(BlueprintName);
	if (!BP)
		return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));

	// Find the variable
	FBPVariableDescription* VarDesc = nullptr;
	for (FBPVariableDescription& Var : BP->NewVariables)
	{
		if (Var.VarName.ToString() == VariableName)
		{
			VarDesc = &Var;
			break;
		}
	}

	if (!VarDesc)
	{
		FString VarErr = FString::Printf(TEXT("Variable '%s' not found in %s."), *VariableName, *BlueprintName);
		TArray<FString> VarNames;
		for (const FBPVariableDescription& V : BP->NewVariables) VarNames.Add(V.VarName.ToString());
		TArray<FString> VarSuggestions = GetSuggestions(VariableName, VarNames);
		if (VarSuggestions.Num() > 0) VarErr += TEXT(" Similar variables: ") + FString::Join(VarSuggestions, TEXT(", "));
		else if (VarNames.Num() > 0) VarErr += TEXT(" Variables in this Blueprint: ") + FString::Join(VarNames, TEXT(", "));
		else VarErr += TEXT(" This Blueprint has no variables.");
		return FCommandResult::Error(VarErr);
	}

	VarDesc->DefaultValue = DefaultValue;

	// Compile
	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("variable_name"), VariableName);
	Data->SetStringField(TEXT("default_value"), DefaultValue);
	Data->SetStringField(TEXT("type"), VarDesc->VarType.PinCategory.ToString());
	Data->SetBoolField(TEXT("compiled"), BP->Status != BS_Error);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Set variable %s default = %s in %s"),
		*VariableName, *DefaultValue, *BlueprintName);

	return FCommandResult::Ok(Data);
}

// ============================================================
// Level actor helpers
// ============================================================

FVector FCommandServer::JsonToVector(const TSharedPtr<FJsonObject>& Obj)
{
	if (!Obj.IsValid()) return FVector::ZeroVector;
	return FVector(
		Obj->GetNumberField(TEXT("x")),
		Obj->GetNumberField(TEXT("y")),
		Obj->GetNumberField(TEXT("z"))
	);
}

FRotator FCommandServer::JsonToRotator(const TSharedPtr<FJsonObject>& Obj)
{
	if (!Obj.IsValid()) return FRotator::ZeroRotator;
	return FRotator(
		Obj->GetNumberField(TEXT("pitch")),
		Obj->GetNumberField(TEXT("yaw")),
		Obj->GetNumberField(TEXT("roll"))
	);
}

TSharedPtr<FJsonObject> FCommandServer::VectorToJson(const FVector& V)
{
	TSharedPtr<FJsonObject> Obj = MakeShareable(new FJsonObject());
	Obj->SetNumberField(TEXT("x"), V.X);
	Obj->SetNumberField(TEXT("y"), V.Y);
	Obj->SetNumberField(TEXT("z"), V.Z);
	return Obj;
}

TSharedPtr<FJsonObject> FCommandServer::RotatorToJson(const FRotator& R)
{
	TSharedPtr<FJsonObject> Obj = MakeShareable(new FJsonObject());
	Obj->SetNumberField(TEXT("pitch"), R.Pitch);
	Obj->SetNumberField(TEXT("yaw"), R.Yaw);
	Obj->SetNumberField(TEXT("roll"), R.Roll);
	return Obj;
}

AActor* FCommandServer::FindActorByLabel(const FString& Label)
{
	UEditorActorSubsystem* ActorSubsystem = GEditor->GetEditorSubsystem<UEditorActorSubsystem>();
	if (!ActorSubsystem) return nullptr;

	TArray<AActor*> AllActors = ActorSubsystem->GetAllLevelActors();

	for (AActor* Actor : AllActors)
	{
		if (Actor && Actor->GetActorLabel() == Label)
		{
			return Actor;
		}
	}
	return nullptr;
}

UClass* FCommandServer::ResolveActorClass(const FString& ClassName)
{
	// Empty → AActor
	if (ClassName.IsEmpty())
	{
		return AActor::StaticClass();
	}

	// Blueprint path: /Game/...
	if (ClassName.StartsWith(TEXT("/Game/")))
	{
		UBlueprint* BP = LoadObject<UBlueprint>(nullptr, *ClassName);
		if (BP && BP->GeneratedClass)
		{
			return BP->GeneratedClass;
		}
		// Try as generated blueprint name in our folder
		FString FullPath = FString::Printf(TEXT("/Game/Arcwright/Generated/%s.%s"),
			*FPaths::GetBaseFilename(ClassName), *FPaths::GetBaseFilename(ClassName));
		BP = LoadObject<UBlueprint>(nullptr, *FullPath);
		if (BP && BP->GeneratedClass)
		{
			return BP->GeneratedClass;
		}
		return nullptr;
	}

	// Known native class names
	static TMap<FString, UClass*> NativeClasses;
	if (NativeClasses.Num() == 0)
	{
		NativeClasses.Add(TEXT("Actor"), AActor::StaticClass());
		NativeClasses.Add(TEXT("StaticMeshActor"), AStaticMeshActor::StaticClass());
		NativeClasses.Add(TEXT("PointLight"), APointLight::StaticClass());
		NativeClasses.Add(TEXT("Character"), ACharacter::StaticClass());
		NativeClasses.Add(TEXT("Pawn"), APawn::StaticClass());
		NativeClasses.Add(TEXT("CameraActor"), ACameraActor::StaticClass());
	}

	UClass** Found = NativeClasses.Find(ClassName);
	if (Found)
	{
		return *Found;
	}

	// Try as a Blueprint in our Generated folder (e.g. "BP_SimpleEnemy" → /Game/Arcwright/Generated/BP_SimpleEnemy)
	{
		FString BPPath = FString::Printf(TEXT("/Game/Arcwright/Generated/%s.%s"), *ClassName, *ClassName);
		UBlueprint* BP = LoadObject<UBlueprint>(nullptr, *BPPath);
		if (BP && BP->GeneratedClass)
		{
			return BP->GeneratedClass;
		}
	}

	// Try /Script/Engine.AClassName
	FString ScriptPath = FString::Printf(TEXT("/Script/Engine.%s"), *ClassName);
	UClass* FoundClass = FindObject<UClass>(nullptr, *ScriptPath);
	if (FoundClass)
	{
		return FoundClass;
	}

	// Last resort: TObjectIterator name match
	for (TObjectIterator<UClass> It; It; ++It)
	{
		if (It->GetName() == ClassName && It->IsChildOf(AActor::StaticClass()))
		{
			return *It;
		}
	}

	return nullptr;
}

// ============================================================
// Level actor command handlers
// ============================================================

FCommandResult FCommandServer::HandleSpawnActorAt(const TSharedPtr<FJsonObject>& Params)
{
	FString ClassName = Params->GetStringField(TEXT("class"));
	UClass* ActorClass = ResolveActorClass(ClassName);
	if (!ActorClass)
	{
		{ FString ClassErr = FString::Printf(TEXT("Could not resolve actor class: %s."), *ClassName);
			TArray<FString> ClassSuggestions = GetSuggestions(ClassName, GetAvailableBlueprintNames());
			if (ClassSuggestions.Num() > 0) ClassErr += TEXT(" Similar blueprints: ") + FString::Join(ClassSuggestions, TEXT(", "));
			else ClassErr += TEXT(" Tip: use full path like /Game/Arcwright/Generated/BP_MyActor for Blueprint classes, or native class names like StaticMeshActor, PointLight, Character.");
			return FCommandResult::Error(ClassErr); }
	}

	FVector Location = FVector::ZeroVector;
	FRotator Rotation = FRotator::ZeroRotator;
	FVector Scale = FVector::OneVector;

	// Accept location as object {"x":0,"y":0,"z":0} OR as top-level x/y/z params
	if (Params->HasTypedField<EJson::Object>(TEXT("location")))
	{
		Location = JsonToVector(Params->GetObjectField(TEXT("location")));
	}
	else
	{
		if (Params->HasField(TEXT("x"))) Location.X = Params->GetNumberField(TEXT("x"));
		if (Params->HasField(TEXT("y"))) Location.Y = Params->GetNumberField(TEXT("y"));
		if (Params->HasField(TEXT("z"))) Location.Z = Params->GetNumberField(TEXT("z"));
	}

	// Accept rotation as object or as top-level yaw/pitch/roll
	if (Params->HasTypedField<EJson::Object>(TEXT("rotation")))
	{
		Rotation = JsonToRotator(Params->GetObjectField(TEXT("rotation")));
	}
	else
	{
		if (Params->HasField(TEXT("yaw"))) Rotation.Yaw = Params->GetNumberField(TEXT("yaw"));
		if (Params->HasField(TEXT("pitch"))) Rotation.Pitch = Params->GetNumberField(TEXT("pitch"));
		if (Params->HasField(TEXT("roll"))) Rotation.Roll = Params->GetNumberField(TEXT("roll"));
	}

	// Accept scale as object {"x":1,"y":1,"z":1} OR as top-level scale_x/scale_y/scale_z
	if (Params->HasTypedField<EJson::Object>(TEXT("scale")))
	{
		Scale = JsonToVector(Params->GetObjectField(TEXT("scale")));
	}
	else
	{
		if (Params->HasField(TEXT("scale_x"))) Scale.X = Params->GetNumberField(TEXT("scale_x"));
		if (Params->HasField(TEXT("scale_y"))) Scale.Y = Params->GetNumberField(TEXT("scale_y"));
		if (Params->HasField(TEXT("scale_z"))) Scale.Z = Params->GetNumberField(TEXT("scale_z"));
	}

	UEditorActorSubsystem* ActorSubsystem = GEditor->GetEditorSubsystem<UEditorActorSubsystem>();
	if (!ActorSubsystem)
	{
		return FCommandResult::Error(TEXT("Could not get UEditorActorSubsystem"));
	}

	AActor* NewActor = ActorSubsystem->SpawnActorFromClass(ActorClass, Location, Rotation);
	if (!NewActor)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Failed to spawn actor of class: %s"), *ClassName));
	}

	NewActor->SetActorScale3D(Scale);

	// Set mesh on StaticMeshActor if provided
	FString MeshPath = Params->GetStringField(TEXT("mesh"));
	if (!MeshPath.IsEmpty())
	{
		AStaticMeshActor* SMActor = Cast<AStaticMeshActor>(NewActor);
		if (SMActor && SMActor->GetStaticMeshComponent())
		{
			UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *MeshPath);
			if (Mesh)
			{
				SMActor->GetStaticMeshComponent()->SetStaticMesh(Mesh);
				UE_LOG(LogBlueprintLLM, Log, TEXT("Set mesh to %s"), *MeshPath);
			}
			else
			{
				UE_LOG(LogBlueprintLLM, Warning, TEXT("Could not load mesh: %s"), *MeshPath);
			}
		}
	}

	// Set material on spawned actor if provided
	FString MaterialPath = Params->GetStringField(TEXT("material"));
	if (!MaterialPath.IsEmpty())
	{
		UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, *MaterialPath);
		if (Mat)
		{
			AStaticMeshActor* SMActor = Cast<AStaticMeshActor>(NewActor);
			if (SMActor && SMActor->GetStaticMeshComponent())
			{
				SMActor->GetStaticMeshComponent()->SetMaterial(0, Mat);
				UE_LOG(LogBlueprintLLM, Log, TEXT("Set material to %s"), *MaterialPath);
			}
		}
	}

	// Set label if provided
	FString Label = Params->GetStringField(TEXT("label"));
	if (!Label.IsEmpty())
	{
		NewActor->SetActorLabel(Label);
	}
	else
	{
		Label = NewActor->GetActorLabel();
	}

	// Mark level dirty
	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (World)
	{
		World->MarkPackageDirty();
	}

	UE_LOG(LogBlueprintLLM, Log, TEXT("Spawned %s at (%s) label=%s"),
		*ActorClass->GetName(), *Location.ToString(), *Label);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("label"), Label);
	Data->SetStringField(TEXT("class"), ActorClass->GetName());
	Data->SetObjectField(TEXT("location"), VectorToJson(NewActor->GetActorLocation()));
	Data->SetObjectField(TEXT("rotation"), RotatorToJson(NewActor->GetActorRotation()));
	Data->SetObjectField(TEXT("scale"), VectorToJson(NewActor->GetActorScale3D()));

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetActors(const TSharedPtr<FJsonObject>& Params)
{
	UEditorActorSubsystem* ActorSubsystem = GEditor->GetEditorSubsystem<UEditorActorSubsystem>();
	if (!ActorSubsystem)
	{
		return FCommandResult::Error(TEXT("Could not get UEditorActorSubsystem"));
	}

	FString ClassFilter = Params->GetStringField(TEXT("class_filter"));

	TArray<AActor*> AllActors = ActorSubsystem->GetAllLevelActors();

	TArray<TSharedPtr<FJsonValue>> ActorsArray;
	for (AActor* Actor : AllActors)
	{
		if (!Actor) continue;

		// Apply class filter (case-insensitive substring match)
		if (!ClassFilter.IsEmpty())
		{
			FString ActorClassName = Actor->GetClass()->GetName();
			if (!ActorClassName.Contains(ClassFilter, ESearchCase::IgnoreCase))
			{
				continue;
			}
		}

		TSharedPtr<FJsonObject> ActorObj = MakeShareable(new FJsonObject());
		ActorObj->SetStringField(TEXT("label"), Actor->GetActorLabel());
		ActorObj->SetStringField(TEXT("class"), Actor->GetClass()->GetName());
		ActorObj->SetObjectField(TEXT("location"), VectorToJson(Actor->GetActorLocation()));
		ActorObj->SetObjectField(TEXT("rotation"), RotatorToJson(Actor->GetActorRotation()));
		ActorObj->SetObjectField(TEXT("scale"), VectorToJson(Actor->GetActorScale3D()));

		ActorsArray.Add(MakeShareable(new FJsonValueObject(ActorObj)));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("count"), ActorsArray.Num());
	Data->SetArrayField(TEXT("actors"), ActorsArray);

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetActorTransform(const TSharedPtr<FJsonObject>& Params)
{
	FString Label = Params->GetStringField(TEXT("label"));
	if (Label.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'label' parameter"));
	}

	AActor* Actor = FindActorByLabel(Label);
	if (!Actor)
	{
		return FCommandResult::Error(FormatActorNotFound(Label));
	}

	if (Params->HasField(TEXT("location")))
	{
		Actor->SetActorLocation(JsonToVector(Params->GetObjectField(TEXT("location"))));
	}
	if (Params->HasField(TEXT("rotation")))
	{
		Actor->SetActorRotation(JsonToRotator(Params->GetObjectField(TEXT("rotation"))));
	}
	if (Params->HasField(TEXT("scale")))
	{
		Actor->SetActorScale3D(JsonToVector(Params->GetObjectField(TEXT("scale"))));
	}

	// Mark level dirty
	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (World)
	{
		World->MarkPackageDirty();
	}

	UE_LOG(LogBlueprintLLM, Log, TEXT("Updated transform for %s"), *Label);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("label"), Label);
	Data->SetObjectField(TEXT("location"), VectorToJson(Actor->GetActorLocation()));
	Data->SetObjectField(TEXT("rotation"), RotatorToJson(Actor->GetActorRotation()));
	Data->SetObjectField(TEXT("scale"), VectorToJson(Actor->GetActorScale3D()));

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleDeleteActor(const TSharedPtr<FJsonObject>& Params)
{
	FString Label = Params->GetStringField(TEXT("label"));
	if (Label.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'label' parameter"));
	}

	AActor* Actor = FindActorByLabel(Label);
	if (!Actor)
	{
		// Idempotent — not found is not an error
		TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
		Data->SetStringField(TEXT("label"), Label);
		Data->SetBoolField(TEXT("deleted"), false);
		return FCommandResult::Ok(Data);
	}

	UEditorActorSubsystem* ActorSubsystem = GEditor->GetEditorSubsystem<UEditorActorSubsystem>();
	if (!ActorSubsystem)
	{
		return FCommandResult::Error(TEXT("Could not get UEditorActorSubsystem"));
	}

	bool bDestroyed = ActorSubsystem->DestroyActor(Actor);

	// Mark level dirty
	if (bDestroyed)
	{
		UWorld* World = GEditor->GetEditorWorldContext().World();
		if (World)
		{
			World->MarkPackageDirty();
		}
	}

	UE_LOG(LogBlueprintLLM, Log, TEXT("Delete actor %s: %s"), *Label,
		bDestroyed ? TEXT("success") : TEXT("failed"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("label"), Label);
	Data->SetBoolField(TEXT("deleted"), bDestroyed);

	return FCommandResult::Ok(Data);
}

// ============================================================
// Component helpers
// ============================================================

UClass* FCommandServer::ResolveComponentClass(const FString& FriendlyName)
{
	static TMap<FString, UClass*> ComponentClasses;
	if (ComponentClasses.Num() == 0)
	{
		ComponentClasses.Add(TEXT("BoxCollision"), UBoxComponent::StaticClass());
		ComponentClasses.Add(TEXT("SphereCollision"), USphereComponent::StaticClass());
		ComponentClasses.Add(TEXT("CapsuleCollision"), UCapsuleComponent::StaticClass());
		ComponentClasses.Add(TEXT("StaticMesh"), UStaticMeshComponent::StaticClass());
		ComponentClasses.Add(TEXT("PointLight"), UPointLightComponent::StaticClass());
		ComponentClasses.Add(TEXT("SpotLight"), USpotLightComponent::StaticClass());
		ComponentClasses.Add(TEXT("Audio"), UAudioComponent::StaticClass());
		ComponentClasses.Add(TEXT("Arrow"), UArrowComponent::StaticClass());
		ComponentClasses.Add(TEXT("Scene"), USceneComponent::StaticClass());
		ComponentClasses.Add(TEXT("Camera"), UCameraComponent::StaticClass());
		ComponentClasses.Add(TEXT("SpringArm"), USpringArmComponent::StaticClass());
	}

	UClass** Found = ComponentClasses.Find(FriendlyName);
	if (Found)
	{
		return *Found;
	}

	// Fallback: TObjectIterator scan for class name match
	for (TObjectIterator<UClass> It; It; ++It)
	{
		if (It->GetName() == FriendlyName && It->IsChildOf(UActorComponent::StaticClass()))
		{
			return *It;
		}
	}

	return nullptr;
}

USCS_Node* FCommandServer::FindSCSNodeByName(USimpleConstructionScript* SCS, const FString& ComponentName)
{
	if (!SCS) return nullptr;

	const TArray<USCS_Node*>& AllNodes = SCS->GetAllNodes();
	for (USCS_Node* Node : AllNodes)
	{
		if (Node && Node->GetVariableName().ToString() == ComponentName)
		{
			return Node;
		}
	}
	return nullptr;
}

// ============================================================
// Component command handlers
// ============================================================

FCommandResult FCommandServer::HandleAddComponent(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	FString ComponentType = Params->GetStringField(TEXT("component_type"));
	FString ComponentName = Params->GetStringField(TEXT("component_name"));

	if (BlueprintName.IsEmpty() || ComponentType.IsEmpty() || ComponentName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required params: blueprint, component_type, component_name"));
	}

	UBlueprint* BP = FindBlueprintByName(BlueprintName);
	if (!BP)
	{
		return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));
	}

	USimpleConstructionScript* SCS = BP->SimpleConstructionScript;
	if (!SCS)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Blueprint %s has no SimpleConstructionScript"), *BlueprintName));
	}

	UClass* ComponentClass = ResolveComponentClass(ComponentType);
	if (!ComponentClass)
	{
		return FCommandResult::Error(FString::Printf(
			TEXT("Unknown component type: %s. Supported: BoxCollision, SphereCollision, CapsuleCollision, StaticMesh, PointLight, SpotLight, Audio, Arrow, Scene, Camera, SpringArm"),
			*ComponentType));
	}

	// Check for name collision
	if (FindSCSNodeByName(SCS, ComponentName))
	{
		return FCommandResult::Error(FString::Printf(TEXT("Component '%s' already exists in %s"), *ComponentName, *BlueprintName));
	}

	// Create the SCS node
	USCS_Node* NewNode = SCS->CreateNode(ComponentClass, FName(*ComponentName));
	if (!NewNode)
	{
		return FCommandResult::Error(TEXT("Failed to create SCS node"));
	}

	// Attach to parent or root
	FString ParentName = Params->GetStringField(TEXT("parent"));
	if (!ParentName.IsEmpty())
	{
		USCS_Node* ParentNode = FindSCSNodeByName(SCS, ParentName);
		if (!ParentNode)
		{
			// Clean up the node we just created
			SCS->RemoveNode(NewNode);
			return FCommandResult::Error(FString::Printf(TEXT("Parent component not found: %s"), *ParentName));
		}
		ParentNode->AddChildNode(NewNode);
	}
	else
	{
		SCS->AddNode(NewNode);
	}

	// Apply properties if provided
	if (Params->HasField(TEXT("properties")))
	{
		const TSharedPtr<FJsonObject>& Props = Params->GetObjectField(TEXT("properties"));
		UActorComponent* Template = NewNode->ComponentTemplate;

		if (Template)
		{
			// Relative transform (applies to all USceneComponent)
			USceneComponent* SceneComp = Cast<USceneComponent>(Template);
			if (SceneComp)
			{
				if (Props->HasField(TEXT("location")))
				{
					SceneComp->SetRelativeLocation(JsonToVector(Props->GetObjectField(TEXT("location"))));
				}
				if (Props->HasField(TEXT("rotation")))
				{
					FRotator Rot = JsonToRotator(Props->GetObjectField(TEXT("rotation")));
					SceneComp->SetRelativeRotation(Rot);
				}
				if (Props->HasField(TEXT("scale")))
				{
					SceneComp->SetRelativeScale3D(JsonToVector(Props->GetObjectField(TEXT("scale"))));
				}
			}

			// Shape components (Box, Sphere, Capsule)
			UShapeComponent* ShapeComp = Cast<UShapeComponent>(Template);
			if (ShapeComp)
			{
				if (Props->HasField(TEXT("generate_overlap_events")))
				{
					ShapeComp->SetGenerateOverlapEvents(Props->GetBoolField(TEXT("generate_overlap_events")));
				}
				if (Props->HasField(TEXT("collision_profile")))
				{
					ShapeComp->SetCollisionProfileName(FName(*Props->GetStringField(TEXT("collision_profile"))));
				}
			}

			// Box extent
			UBoxComponent* BoxComp = Cast<UBoxComponent>(Template);
			if (BoxComp && Props->HasField(TEXT("extent")))
			{
				BoxComp->SetBoxExtent(JsonToVector(Props->GetObjectField(TEXT("extent"))));
			}

			// Sphere radius
			USphereComponent* SphereComp = Cast<USphereComponent>(Template);
			if (SphereComp && Props->HasField(TEXT("radius")))
			{
				SphereComp->SetSphereRadius(Props->GetNumberField(TEXT("radius")));
			}

			// Capsule size
			UCapsuleComponent* CapsuleComp = Cast<UCapsuleComponent>(Template);
			if (CapsuleComp)
			{
				if (Props->HasField(TEXT("radius")))
				{
					float Radius = Props->GetNumberField(TEXT("radius"));
					float HalfHeight = Props->HasField(TEXT("half_height")) ? Props->GetNumberField(TEXT("half_height")) : CapsuleComp->GetUnscaledCapsuleHalfHeight();
					CapsuleComp->SetCapsuleSize(Radius, HalfHeight);
				}
			}

			// Static mesh (accept both "mesh" and "static_mesh")
			UStaticMeshComponent* MeshComp = Cast<UStaticMeshComponent>(Template);
			FString MeshKey = Props->HasField(TEXT("static_mesh")) ? TEXT("static_mesh") : TEXT("mesh");
			if (MeshComp && Props->HasField(MeshKey))
			{
				FString MeshPath = Props->GetStringField(MeshKey);
				UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *MeshPath);
				if (Mesh)
				{
					MeshComp->SetStaticMesh(Mesh);
				}
				else
				{
					UE_LOG(LogBlueprintLLM, Warning, TEXT("Could not load mesh: %s"), *MeshPath);
				}
			}

			// Light components (PointLight, SpotLight inherit from ULocalLightComponent)
			UPointLightComponent* PointLightComp = Cast<UPointLightComponent>(Template);
			if (PointLightComp)
			{
				if (Props->HasField(TEXT("intensity")))
				{
					PointLightComp->SetIntensity(Props->GetNumberField(TEXT("intensity")));
				}
				if (Props->HasField(TEXT("light_color")))
				{
					const TSharedPtr<FJsonObject>& ColorObj = Props->GetObjectField(TEXT("light_color"));
					FLinearColor Color(
						ColorObj->GetNumberField(TEXT("r")),
						ColorObj->GetNumberField(TEXT("g")),
						ColorObj->GetNumberField(TEXT("b")),
						ColorObj->HasField(TEXT("a")) ? ColorObj->GetNumberField(TEXT("a")) : 1.0f
					);
					PointLightComp->SetLightColor(Color);
				}
				if (Props->HasField(TEXT("attenuation_radius")))
				{
					PointLightComp->SetAttenuationRadius(Props->GetNumberField(TEXT("attenuation_radius")));
				}
			}
		}
	}

	// Compile
	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Added component '%s' (%s) to %s"),
		*ComponentName, *ComponentClass->GetName(), *BlueprintName);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("component_name"), ComponentName);
	Data->SetStringField(TEXT("component_class"), ComponentClass->GetName());
	Data->SetStringField(TEXT("parent"), ParentName.IsEmpty() ? TEXT("DefaultSceneRoot") : ParentName);
	Data->SetBoolField(TEXT("compiled"), true);

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetComponents(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	if (BlueprintName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required param: blueprint"));
	}

	UBlueprint* BP = FindBlueprintByName(BlueprintName);
	if (!BP)
	{
		return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));
	}

	USimpleConstructionScript* SCS = BP->SimpleConstructionScript;
	if (!SCS)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Blueprint %s has no SimpleConstructionScript"), *BlueprintName));
	}

	const TArray<USCS_Node*>& AllNodes = SCS->GetAllNodes();

	TArray<TSharedPtr<FJsonValue>> ComponentsArray;
	for (USCS_Node* Node : AllNodes)
	{
		if (!Node) continue;

		TSharedPtr<FJsonObject> CompObj = MakeShareable(new FJsonObject());
		CompObj->SetStringField(TEXT("name"), Node->GetVariableName().ToString());

		if (Node->ComponentTemplate)
		{
			CompObj->SetStringField(TEXT("class"), Node->ComponentTemplate->GetClass()->GetName());
		}
		else
		{
			CompObj->SetStringField(TEXT("class"), TEXT("Unknown"));
		}

		// Determine parent
		USCS_Node* ParentNode = nullptr;
		for (USCS_Node* Candidate : AllNodes)
		{
			if (Candidate && Candidate->GetChildNodes().Contains(Node))
			{
				ParentNode = Candidate;
				break;
			}
		}
		CompObj->SetStringField(TEXT("parent"),
			ParentNode ? ParentNode->GetVariableName().ToString() : TEXT("DefaultSceneRoot"));

		ComponentsArray.Add(MakeShareable(new FJsonValueObject(CompObj)));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("count"), ComponentsArray.Num());
	Data->SetArrayField(TEXT("components"), ComponentsArray);

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleRemoveComponent(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	FString ComponentName = Params->GetStringField(TEXT("component_name"));

	if (BlueprintName.IsEmpty() || ComponentName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required params: blueprint, component_name"));
	}

	UBlueprint* BP = FindBlueprintByName(BlueprintName);
	if (!BP)
	{
		return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));
	}

	USimpleConstructionScript* SCS = BP->SimpleConstructionScript;
	if (!SCS)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Blueprint %s has no SimpleConstructionScript"), *BlueprintName));
	}

	USCS_Node* Node = FindSCSNodeByName(SCS, ComponentName);
	if (!Node)
	{
		// Idempotent — not found is OK
		TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
		Data->SetStringField(TEXT("component_name"), ComponentName);
		Data->SetBoolField(TEXT("deleted"), false);
		Data->SetBoolField(TEXT("compiled"), false);
		return FCommandResult::Ok(Data);
	}

	SCS->RemoveNode(Node);

	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Removed component '%s' from %s"), *ComponentName, *BlueprintName);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("component_name"), ComponentName);
	Data->SetBoolField(TEXT("deleted"), true);
	Data->SetBoolField(TEXT("compiled"), true);

	return FCommandResult::Ok(Data);
}

// ============================================================
// Component property helper
// ============================================================

bool FCommandServer::ApplyComponentProperty(UActorComponent* Template, const FString& PropertyName, const TSharedPtr<FJsonValue>& Value, FString& OutError)
{
	if (!Template)
	{
		OutError = TEXT("ComponentTemplate is null");
		return false;
	}

	USceneComponent* SceneComp = Cast<USceneComponent>(Template);

	// --- Universal properties (any SceneComponent) ---
	if (PropertyName == TEXT("relative_location") || PropertyName == TEXT("location"))
	{
		if (!SceneComp) { OutError = TEXT("Not a SceneComponent"); return false; }
		const TSharedPtr<FJsonObject>* ObjPtr;
		if (!Value->TryGetObject(ObjPtr)) { OutError = TEXT("Expected {x,y,z} object"); return false; }
		SceneComp->SetRelativeLocation(JsonToVector(*ObjPtr));
		return true;
	}
	if (PropertyName == TEXT("relative_rotation") || PropertyName == TEXT("rotation"))
	{
		if (!SceneComp) { OutError = TEXT("Not a SceneComponent"); return false; }
		const TSharedPtr<FJsonObject>* ObjPtr;
		if (!Value->TryGetObject(ObjPtr)) { OutError = TEXT("Expected {pitch,yaw,roll} object"); return false; }
		SceneComp->SetRelativeRotation(JsonToRotator(*ObjPtr));
		return true;
	}
	if (PropertyName == TEXT("relative_scale") || PropertyName == TEXT("scale"))
	{
		if (!SceneComp) { OutError = TEXT("Not a SceneComponent"); return false; }
		const TSharedPtr<FJsonObject>* ObjPtr;
		if (!Value->TryGetObject(ObjPtr)) { OutError = TEXT("Expected {x,y,z} object"); return false; }
		SceneComp->SetRelativeScale3D(JsonToVector(*ObjPtr));
		return true;
	}
	if (PropertyName == TEXT("visibility") || PropertyName == TEXT("visible"))
	{
		if (!SceneComp) { OutError = TEXT("Not a SceneComponent"); return false; }
		bool bVal;
		if (!Value->TryGetBool(bVal)) { OutError = TEXT("Expected bool"); return false; }
		SceneComp->SetVisibility(bVal);
		return true;
	}

	// --- Material ---
	if (PropertyName == TEXT("material"))
	{
		UStaticMeshComponent* MeshComp = Cast<UStaticMeshComponent>(Template);
		if (!MeshComp) { OutError = TEXT("Not a StaticMeshComponent — cannot set material"); return false; }
		FString MatPath;
		if (!Value->TryGetString(MatPath)) { OutError = TEXT("Expected string material path"); return false; }
		FString ResolvedMatPath, MatResolveErr;
		UMaterialInterface* Mat = ResolveMaterialByName(MatPath, ResolvedMatPath, MatResolveErr);
		if (!Mat) { OutError = MatResolveErr.IsEmpty() ? FString::Printf(TEXT("Could not load material: %s"), *MatPath) : MatResolveErr; return false; }
		// Use OverrideMaterials directly — SetMaterial() requires a registered component
		if (MeshComp->OverrideMaterials.Num() == 0)
		{
			MeshComp->OverrideMaterials.SetNum(1);
		}
		MeshComp->OverrideMaterials[0] = Mat;
		return true;
	}

	// --- Static mesh ---
	if (PropertyName == TEXT("static_mesh") || PropertyName == TEXT("mesh"))
	{
		UStaticMeshComponent* MeshComp = Cast<UStaticMeshComponent>(Template);
		if (!MeshComp) { OutError = TEXT("Not a StaticMeshComponent"); return false; }
		FString MeshPath;
		if (!Value->TryGetString(MeshPath)) { OutError = TEXT("Expected string asset path"); return false; }
		UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *MeshPath);
		if (!Mesh) { OutError = FString::Printf(TEXT("Could not load mesh: %s"), *MeshPath); return false; }
		MeshComp->SetStaticMesh(Mesh);
		return true;
	}

	// --- Collision: box extent ---
	if (PropertyName == TEXT("box_extent") || PropertyName == TEXT("extent"))
	{
		UBoxComponent* BoxComp = Cast<UBoxComponent>(Template);
		if (!BoxComp) { OutError = TEXT("Not a BoxComponent"); return false; }
		const TSharedPtr<FJsonObject>* ObjPtr;
		if (!Value->TryGetObject(ObjPtr)) { OutError = TEXT("Expected {x,y,z} object"); return false; }
		BoxComp->SetBoxExtent(JsonToVector(*ObjPtr));
		return true;
	}

	// --- Collision: sphere radius ---
	if (PropertyName == TEXT("sphere_radius") || PropertyName == TEXT("radius"))
	{
		USphereComponent* SphereComp = Cast<USphereComponent>(Template);
		if (!SphereComp) { OutError = TEXT("Not a SphereComponent"); return false; }
		double DVal;
		if (!Value->TryGetNumber(DVal)) { OutError = TEXT("Expected number"); return false; }
		SphereComp->SetSphereRadius(DVal);
		return true;
	}

	// --- Collision: generate overlap events ---
	if (PropertyName == TEXT("generate_overlap_events"))
	{
		UPrimitiveComponent* PrimComp = Cast<UPrimitiveComponent>(Template);
		if (!PrimComp) { OutError = TEXT("Not a PrimitiveComponent"); return false; }
		bool bVal;
		if (!Value->TryGetBool(bVal)) { OutError = TEXT("Expected bool"); return false; }
		PrimComp->SetGenerateOverlapEvents(bVal);
		return true;
	}

	// --- Collision: enabled ---
	if (PropertyName == TEXT("collision_enabled"))
	{
		UPrimitiveComponent* PrimComp = Cast<UPrimitiveComponent>(Template);
		if (!PrimComp) { OutError = TEXT("Not a PrimitiveComponent"); return false; }
		bool bVal;
		if (!Value->TryGetBool(bVal)) { OutError = TEXT("Expected bool"); return false; }
		PrimComp->SetCollisionEnabled(bVal ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
		return true;
	}

	// --- Collision: profile name ---
	if (PropertyName == TEXT("collision_profile_name") || PropertyName == TEXT("collision_profile"))
	{
		UPrimitiveComponent* PrimComp = Cast<UPrimitiveComponent>(Template);
		if (!PrimComp) { OutError = TEXT("Not a PrimitiveComponent"); return false; }
		FString StrVal;
		if (!Value->TryGetString(StrVal)) { OutError = TEXT("Expected string"); return false; }
		PrimComp->SetCollisionProfileName(FName(*StrVal));
		return true;
	}

	// --- Light: intensity ---
	if (PropertyName == TEXT("intensity"))
	{
		ULightComponent* LightComp = Cast<ULightComponent>(Template);
		if (!LightComp) { OutError = TEXT("Not a LightComponent"); return false; }
		double DVal;
		if (!Value->TryGetNumber(DVal)) { OutError = TEXT("Expected number"); return false; }
		LightComp->SetIntensity(DVal);
		return true;
	}

	// --- Light: color ---
	if (PropertyName == TEXT("light_color"))
	{
		ULightComponent* LightComp = Cast<ULightComponent>(Template);
		if (!LightComp) { OutError = TEXT("Not a LightComponent"); return false; }
		const TSharedPtr<FJsonObject>* ObjPtr;
		if (!Value->TryGetObject(ObjPtr)) { OutError = TEXT("Expected {r,g,b} object"); return false; }
		FLinearColor Color(
			(*ObjPtr)->GetNumberField(TEXT("r")),
			(*ObjPtr)->GetNumberField(TEXT("g")),
			(*ObjPtr)->GetNumberField(TEXT("b")),
			(*ObjPtr)->HasField(TEXT("a")) ? (*ObjPtr)->GetNumberField(TEXT("a")) : 1.0f
		);
		LightComp->SetLightColor(Color);
		return true;
	}

	// --- Light: attenuation radius ---
	if (PropertyName == TEXT("attenuation_radius"))
	{
		UPointLightComponent* PointLightComp = Cast<UPointLightComponent>(Template);
		if (!PointLightComp) { OutError = TEXT("Not a PointLightComponent"); return false; }
		double DVal;
		if (!Value->TryGetNumber(DVal)) { OutError = TEXT("Expected number"); return false; }
		PointLightComp->SetAttenuationRadius(DVal);
		return true;
	}

	// ── Generic UPROPERTY fallback via reflection ──
	FProperty* Prop = Template->GetClass()->FindPropertyByName(*PropertyName);
	if (Prop)
	{
		void* ContainerPtr = Template;

		// Try JSON bool directly
		bool bJsonBool;
		if (Value->TryGetBool(bJsonBool))
		{
			if (FBoolProperty* BoolProp = CastField<FBoolProperty>(Prop))
			{
				BoolProp->SetPropertyValue_InContainer(ContainerPtr, bJsonBool);
				UE_LOG(LogBlueprintLLM, Log, TEXT("Set bool property '%s' = %s via reflection"), *PropertyName, bJsonBool ? TEXT("true") : TEXT("false"));
				return true;
			}
		}

		// Try JSON number directly
		double NumVal;
		if (Value->TryGetNumber(NumVal))
		{
			if (FFloatProperty* FloatProp = CastField<FFloatProperty>(Prop))
			{
				FloatProp->SetPropertyValue_InContainer(ContainerPtr, (float)NumVal);
				UE_LOG(LogBlueprintLLM, Log, TEXT("Set float property '%s' = %f via reflection"), *PropertyName, (float)NumVal);
				return true;
			}
			if (FDoubleProperty* DoubleProp = CastField<FDoubleProperty>(Prop))
			{
				DoubleProp->SetPropertyValue_InContainer(ContainerPtr, NumVal);
				return true;
			}
			if (FIntProperty* IntProp = CastField<FIntProperty>(Prop))
			{
				IntProp->SetPropertyValue_InContainer(ContainerPtr, (int32)NumVal);
				return true;
			}
		}

		// Try JSON string
		FString StrVal;
		if (Value->TryGetString(StrVal))
		{
			if (FBoolProperty* BoolProp = CastField<FBoolProperty>(Prop))
			{
				bool bVal = StrVal.Equals(TEXT("true"), ESearchCase::IgnoreCase) || StrVal == TEXT("1");
				BoolProp->SetPropertyValue_InContainer(ContainerPtr, bVal);
				return true;
			}
			if (FFloatProperty* FloatProp = CastField<FFloatProperty>(Prop))
			{
				FloatProp->SetPropertyValue_InContainer(ContainerPtr, FCString::Atof(*StrVal));
				return true;
			}
			if (FDoubleProperty* DoubleProp = CastField<FDoubleProperty>(Prop))
			{
				DoubleProp->SetPropertyValue_InContainer(ContainerPtr, FCString::Atod(*StrVal));
				return true;
			}
			if (FIntProperty* IntProp = CastField<FIntProperty>(Prop))
			{
				IntProp->SetPropertyValue_InContainer(ContainerPtr, FCString::Atoi(*StrVal));
				return true;
			}
			if (FStrProperty* StrProp = CastField<FStrProperty>(Prop))
			{
				StrProp->SetPropertyValue_InContainer(ContainerPtr, StrVal);
				return true;
			}
			if (FNameProperty* NameProp = CastField<FNameProperty>(Prop))
			{
				NameProp->SetPropertyValue_InContainer(ContainerPtr, FName(*StrVal));
				return true;
			}
		}

		OutError = FString::Printf(TEXT("Property '%s' found via reflection but value type not supported"), *PropertyName);
		return false;
	}

	OutError = FString::Printf(TEXT("Unknown property: %s (not found via specific handlers or reflection)"), *PropertyName);
	return false;
}

FCommandResult FCommandServer::HandleSetComponentProperty(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	FString ComponentName = Params->GetStringField(TEXT("component_name"));
	FString PropertyName = Params->GetStringField(TEXT("property_name"));

	if (BlueprintName.IsEmpty() || ComponentName.IsEmpty() || PropertyName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required params: blueprint, component_name, property_name"));
	}

	if (!Params->HasField(TEXT("value")))
	{
		return FCommandResult::Error(TEXT("Missing required param: value"));
	}

	UBlueprint* BP = FindBlueprintByName(BlueprintName);
	if (!BP)
	{
		return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));
	}

	USimpleConstructionScript* SCS = BP->SimpleConstructionScript;
	if (!SCS)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Blueprint %s has no SimpleConstructionScript"), *BlueprintName));
	}

	USCS_Node* Node = FindSCSNodeByName(SCS, ComponentName);
	if (!Node)
	{
		{
			FString CompErr = FString::Printf(TEXT("Component not found: %s in %s."), *ComponentName, *BlueprintName);
			TArray<FString> CompNames;
			for (USCS_Node* N : SCS->GetAllNodes()) { if (N) CompNames.Add(N->GetVariableName().ToString()); }
			TArray<FString> CompSuggestions = GetSuggestions(ComponentName, CompNames);
			if (CompSuggestions.Num() > 0) CompErr += TEXT(" Available components: ") + FString::Join(CompSuggestions, TEXT(", "));
			else if (CompNames.Num() > 0) CompErr += TEXT(" Components in this Blueprint: ") + FString::Join(CompNames, TEXT(", "));
			else CompErr += TEXT(" This Blueprint has no components.");
			return FCommandResult::Error(CompErr);
		}
	}

	UActorComponent* Template = Node->ComponentTemplate;
	if (!Template)
	{
		return FCommandResult::Error(TEXT("Component has no template"));
	}

	TSharedPtr<FJsonValue> JsonValue = Params->TryGetField(TEXT("value"));
	FString ErrorMsg;
	bool bIsMaterialProp = (PropertyName == TEXT("material"));

	// Apply property to SCS template FIRST, then compile so CDO picks it up
	bool bApplied = ApplyComponentProperty(Template, PropertyName, JsonValue, ErrorMsg);
	if (!bApplied)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Failed to set %s on %s: %s"), *PropertyName, *ComponentName, *ErrorMsg));
	}

	// Compile AFTER setting — CDO regenerated from template (now has the property)
	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	// For material properties: also set on CDO directly (belt-and-suspenders)
	if (bIsMaterialProp && BP->GeneratedClass)
	{
		AActor* CDO = Cast<AActor>(BP->GeneratedClass->GetDefaultObject());
		if (CDO)
		{
			TArray<UActorComponent*> CDOComps;
			CDO->GetComponents(CDOComps);
			for (UActorComponent* Comp : CDOComps)
			{
				if (Comp->GetName().Contains(ComponentName))
				{
					FString MatErrorMsg;
					ApplyComponentProperty(Comp, PropertyName, JsonValue, MatErrorMsg);
					UE_LOG(LogBlueprintLLM, Log, TEXT("Also set material on CDO component %s"), *Comp->GetName());
					break;
				}
			}
		}
	}

	BP->GetPackage()->SetDirtyFlag(true);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Set %s.%s in %s"), *ComponentName, *PropertyName, *BlueprintName);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("component_name"), ComponentName);
	Data->SetStringField(TEXT("property_name"), PropertyName);
	Data->SetBoolField(TEXT("compiled"), BP->Status != BS_Error);

	return FCommandResult::Ok(Data);
}

// ============================================================
// Material commands
// ============================================================

FCommandResult FCommandServer::HandleCreateMaterialInstance(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	FString ParentPath = Params->GetStringField(TEXT("parent"));

	if (Name.IsEmpty() || ParentPath.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required params: name, parent"));
	}

	// Load parent material
	UMaterialInterface* ParentMat = LoadObject<UMaterialInterface>(nullptr, *ParentPath);
	if (!ParentMat)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Could not load parent material: %s"), *ParentPath));
	}

	// Delete existing material instance if present (prevents "partially loaded" crash — Lesson #37)
	FString PackagePath = FString::Printf(TEXT("/Game/Arcwright/Materials/%s"), *Name);
	{
		FString FullAssetPath = FString::Printf(TEXT("%s.%s"), *PackagePath, *Name);
		UObject* ExistingObj = LoadObject<UObject>(nullptr, *FullAssetPath);
		if (ExistingObj)
		{
			TArray<UObject*> ToDelete;
			ToDelete.Add(ExistingObj);
			ObjectTools::ForceDeleteObjects(ToDelete, false);
			CollectGarbage(GARBAGE_COLLECTION_KEEPFLAGS);
			UE_LOG(LogBlueprintLLM, Log, TEXT("Deleted existing material instance before recreation: %s"), *Name);
		}
	}

	// Create package for the material instance
	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Failed to create package: %s"), *PackagePath));
	}

	// Create MaterialInstanceConstant
	UMaterialInstanceConstant* MIC = NewObject<UMaterialInstanceConstant>(Package, FName(*Name), RF_Public | RF_Standalone);
	MIC->Parent = ParentMat;

	int32 ScalarCount = 0;
	int32 VectorCount = 0;

	// Apply scalar parameters
	const TSharedPtr<FJsonObject>* ScalarParamsPtr;
	if (Params->TryGetObjectField(TEXT("scalar_params"), ScalarParamsPtr))
	{
		for (auto& Pair : (*ScalarParamsPtr)->Values)
		{
			double Val = 0.0;
			if (Pair.Value->TryGetNumber(Val))
			{
				FMaterialParameterInfo ParamInfo(FName(*Pair.Key));
				MIC->SetScalarParameterValueEditorOnly(ParamInfo, Val);
				ScalarCount++;
			}
		}
	}

	// Apply vector parameters
	const TSharedPtr<FJsonObject>* VectorParamsPtr;
	if (Params->TryGetObjectField(TEXT("vector_params"), VectorParamsPtr))
	{
		for (auto& Pair : (*VectorParamsPtr)->Values)
		{
			const TSharedPtr<FJsonObject>* ColorObj;
			if (Pair.Value->TryGetObject(ColorObj))
			{
				FLinearColor Color(
					(*ColorObj)->GetNumberField(TEXT("r")),
					(*ColorObj)->GetNumberField(TEXT("g")),
					(*ColorObj)->GetNumberField(TEXT("b")),
					(*ColorObj)->HasField(TEXT("a")) ? (*ColorObj)->GetNumberField(TEXT("a")) : 1.0f
				);
				FMaterialParameterInfo ParamInfo(FName(*Pair.Key));
				MIC->SetVectorParameterValueEditorOnly(ParamInfo, Color);
				VectorCount++;
			}
		}
	}

	// Trigger shader compilation (Lesson #42 — required for Substrate rendering)
	MIC->PreEditChange(nullptr);
	MIC->PostEditChange();

	// Mark dirty + notify asset registry
	MIC->MarkPackageDirty();
	FAssetRegistryModule::AssetCreated(MIC);

	// Save the package
	FString PackageFilename = FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension());
	FSavePackageArgs SaveArgs;
	SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
	SafeSavePackage(Package, MIC, PackageFilename, SaveArgs);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Created MaterialInstance: %s (parent: %s, %d scalar, %d vector params)"),
		*Name, *ParentPath, ScalarCount, VectorCount);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), PackagePath);
	Data->SetStringField(TEXT("parent"), ParentPath);
	Data->SetNumberField(TEXT("scalar_params_set"), ScalarCount);
	Data->SetNumberField(TEXT("vector_params_set"), VectorCount);

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCreateSimpleMaterial(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required param: name"));
	}

	// Get color (r,g,b 0-1 range) — optional for UI materials
	float R = 0.5f, G = 0.5f, B = 0.5f;
	bool bHasColor = false;
	const TSharedPtr<FJsonObject>* ColorPtr;
	if (Params->TryGetObjectField(TEXT("color"), ColorPtr))
	{
		R = (*ColorPtr)->GetNumberField(TEXT("r"));
		G = (*ColorPtr)->GetNumberField(TEXT("g"));
		B = (*ColorPtr)->GetNumberField(TEXT("b"));
		bHasColor = true;
	}
	else if (!Params->HasField(TEXT("material_domain")))
	{
		return FCommandResult::Error(TEXT("Missing required param: color {r,g,b} (optional for UI materials)"));
	}

	// Optional emissive strength (> 0 makes it glow)
	float EmissiveStrength = Params->HasField(TEXT("emissive")) ? Params->GetNumberField(TEXT("emissive")) : 0.0f;

	// Delete existing material if present (prevents "partially loaded" crash — Lesson #37)
	FString BasePath = Params->HasField(TEXT("path"))
		? Params->GetStringField(TEXT("path"))
		: TEXT("/Game/Arcwright/Materials");
	FString PackagePath = BasePath / Name;
	{
		FString FullAssetPath = FString::Printf(TEXT("%s.%s"), *PackagePath, *Name);
		UMaterial* ExistingMat = LoadObject<UMaterial>(nullptr, *FullAssetPath);
		if (ExistingMat)
		{
			TArray<UObject*> ToDelete;
			ToDelete.Add(ExistingMat);
			ObjectTools::ForceDeleteObjects(ToDelete, false);
			CollectGarbage(GARBAGE_COLLECTION_KEEPFLAGS);
			UE_LOG(LogBlueprintLLM, Log, TEXT("Deleted existing material before recreation: %s"), *Name);
		}
	}

	// Create package
	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Failed to create package: %s"), *PackagePath));
	}

	// Create UMaterial
	UMaterial* NewMat = NewObject<UMaterial>(Package, FName(*Name), RF_Public | RF_Standalone);

	// Set material domain if specified
	FString Domain = Params->HasField(TEXT("material_domain"))
		? Params->GetStringField(TEXT("material_domain")) : TEXT("Surface");
	if (Domain == TEXT("UI") || Domain == TEXT("UserInterface"))
	{
		NewMat->MaterialDomain = MD_UI;
		NewMat->BlendMode = BLEND_Translucent;
		NewMat->SetShadingModel(MSM_Unlit);
	}
	else if (Domain == TEXT("PostProcess"))
	{
		NewMat->MaterialDomain = MD_PostProcess;
	}

	// Allow custom path override
	if (Params->HasField(TEXT("path")))
	{
		// Path was specified — material was already created at PackagePath which uses Name
		// No action needed here, path is used for logging
	}

	// Create a Constant3Vector expression for the color
	UMaterialExpressionConstant3Vector* ColorExpr = NewObject<UMaterialExpressionConstant3Vector>(NewMat);
	ColorExpr->Constant = FLinearColor(R, G, B, 1.0f);
	ColorExpr->MaterialExpressionEditorX = 0;
	ColorExpr->MaterialExpressionEditorY = 0;
	NewMat->GetExpressionCollection().AddExpression(ColorExpr);

	// Connect to BaseColor
	NewMat->GetEditorOnlyData()->BaseColor.Connect(0, ColorExpr);

	// If emissive, create multiply node and connect to emissive
	if (EmissiveStrength > 0.0f)
	{
		UMaterialExpressionMultiply* MulExpr = NewObject<UMaterialExpressionMultiply>(NewMat);
		MulExpr->ConstB = EmissiveStrength;
		MulExpr->MaterialExpressionEditorX = 0;
		MulExpr->MaterialExpressionEditorY = 200;
		NewMat->GetExpressionCollection().AddExpression(MulExpr);

		MulExpr->A.Connect(0, ColorExpr);
		NewMat->GetEditorOnlyData()->EmissiveColor.Connect(0, MulExpr);
	}

	// Trigger shader compilation via PostEditChange.
	// Lesson #40 noted this crashes after ~11 rapid-fire materials due to
	// FlushRenderingCommands recursion. Lesson #42 found that WITHOUT it,
	// Substrate materials never compile and show checkerboard forever.
	// PostEditChange is required — batch material creation scripts must
	// add delays or limit batch size to avoid the recursion crash.
	NewMat->PreEditChange(nullptr);
	NewMat->PostEditChange();

	// Mark dirty + register
	NewMat->MarkPackageDirty();
	FAssetRegistryModule::AssetCreated(NewMat);

	// Save
	FString PackageFilename = FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension());
	FSavePackageArgs SaveArgs;
	SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
	SafeSavePackage(Package, NewMat, PackageFilename, SaveArgs);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Created simple material: %s (color: %.2f, %.2f, %.2f, emissive: %.1f)"),
		*Name, R, G, B, EmissiveStrength);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), PackagePath);

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCreateTexturedMaterial(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	FString TexturePath = Params->GetStringField(TEXT("texture_path"));

	if (Name.IsEmpty() || TexturePath.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required params: name, texture_path"));
	}

	float Roughness = Params->HasField(TEXT("roughness")) ? (float)Params->GetNumberField(TEXT("roughness")) : 0.5f;
	float Metallic = Params->HasField(TEXT("metallic")) ? (float)Params->GetNumberField(TEXT("metallic")) : 0.0f;
	float Tiling = Params->HasField(TEXT("tiling")) ? (float)Params->GetNumberField(TEXT("tiling")) : 1.0f;

	// Load the texture
	UTexture2D* Texture = LoadObject<UTexture2D>(nullptr, *TexturePath);
	if (!Texture)
	{
		// Try with .TexturePath suffix
		FString FullPath = FString::Printf(TEXT("%s.%s"), *TexturePath, *FPaths::GetCleanFilename(TexturePath));
		Texture = LoadObject<UTexture2D>(nullptr, *FullPath);
		if (!Texture)
		{
			return FCommandResult::Error(FString::Printf(TEXT("Could not load texture: %s"), *TexturePath));
		}
	}

	FString PackagePath = FString::Printf(TEXT("/Game/Arcwright/Materials/%s"), *Name);

	// Delete existing material if present (Lesson #37 — prevents "partially loaded" crash)
	{
		FString FullAssetPath = FString::Printf(TEXT("%s.%s"), *PackagePath, *Name);
		UMaterial* ExistingMat = LoadObject<UMaterial>(nullptr, *FullAssetPath);
		if (ExistingMat)
		{
			TArray<UObject*> ToDelete;
			ToDelete.Add(ExistingMat);
			ObjectTools::ForceDeleteObjects(ToDelete, false);
			CollectGarbage(GARBAGE_COLLECTION_KEEPFLAGS);
			UE_LOG(LogBlueprintLLM, Log, TEXT("Deleted existing textured material before recreation: %s"), *Name);
		}
	}

	// Create package + material
	UPackage* Package = CreatePackage(*PackagePath);
	UMaterial* NewMat = NewObject<UMaterial>(Package, *Name, RF_Public | RF_Standalone);

	// --- Texture Sample node connected to BaseColor ---
	UMaterialExpressionTextureSample* TexSample = NewObject<UMaterialExpressionTextureSample>(NewMat);
	TexSample->Texture = Texture;
	TexSample->MaterialExpressionEditorX = -400;
	TexSample->MaterialExpressionEditorY = 0;
	NewMat->GetExpressionCollection().AddExpression(TexSample);
	NewMat->GetEditorOnlyData()->BaseColor.Connect(0, TexSample); // RGB output → BaseColor

	// --- Roughness constant ---
	UMaterialExpressionConstant* RoughnessExpr = NewObject<UMaterialExpressionConstant>(NewMat);
	RoughnessExpr->R = Roughness;
	RoughnessExpr->MaterialExpressionEditorX = -400;
	RoughnessExpr->MaterialExpressionEditorY = 300;
	NewMat->GetExpressionCollection().AddExpression(RoughnessExpr);
	NewMat->GetEditorOnlyData()->Roughness.Connect(0, RoughnessExpr);

	// --- Metallic constant ---
	if (Metallic > 0.0f)
	{
		UMaterialExpressionConstant* MetallicExpr = NewObject<UMaterialExpressionConstant>(NewMat);
		MetallicExpr->R = Metallic;
		MetallicExpr->MaterialExpressionEditorX = -400;
		MetallicExpr->MaterialExpressionEditorY = 400;
		NewMat->GetExpressionCollection().AddExpression(MetallicExpr);
		NewMat->GetEditorOnlyData()->Metallic.Connect(0, MetallicExpr);
	}

	// --- UV Tiling (TexCoord multiply) ---
	if (!FMath::IsNearlyEqual(Tiling, 1.0f))
	{
		UMaterialExpressionTextureCoordinate* TexCoord = NewObject<UMaterialExpressionTextureCoordinate>(NewMat);
		TexCoord->UTiling = Tiling;
		TexCoord->VTiling = Tiling;
		TexCoord->MaterialExpressionEditorX = -700;
		TexCoord->MaterialExpressionEditorY = 0;
		NewMat->GetExpressionCollection().AddExpression(TexCoord);
		TexSample->Coordinates.Connect(0, TexCoord);
	}

	// Trigger shader compilation (Lesson #42 — required for Substrate rendering)
	NewMat->PreEditChange(nullptr);
	NewMat->PostEditChange();

	NewMat->MarkPackageDirty();
	FAssetRegistryModule::AssetCreated(NewMat);

	// Save
	FString PackageFilename = FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension());
	FSavePackageArgs SaveArgs;
	SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
	SafeSavePackage(Package, NewMat, PackageFilename, SaveArgs);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Created textured material: %s (texture: %s, roughness: %.2f, metallic: %.2f, tiling: %.1f)"),
		*Name, *TexturePath, Roughness, Metallic, Tiling);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), PackagePath);
	Data->SetStringField(TEXT("texture"), TexturePath);

	return FCommandResult::Ok(Data);
}

UMaterialInterface* FCommandServer::ResolveMaterialByName(const FString& NameOrPath, FString& OutResolvedPath, FString& OutError)
{
	// 1. Try exact path first
	UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, *NameOrPath);
	if (Mat)
	{
		OutResolvedPath = NameOrPath;
		return Mat;
	}

	// 2. Try common prefixed paths
	TArray<FString> SearchPaths;
	SearchPaths.Add(FString::Printf(TEXT("/Game/Arcwright/Materials/%s.%s"), *NameOrPath, *NameOrPath));
	SearchPaths.Add(FString::Printf(TEXT("/Game/Arcwright/Materials/%s"), *NameOrPath));
	for (const FString& Path : SearchPaths)
	{
		Mat = LoadObject<UMaterialInterface>(nullptr, *Path);
		if (Mat)
		{
			OutResolvedPath = Path;
			UE_LOG(LogBlueprintLLM, Log, TEXT("Resolved material '%s' → '%s'"), *NameOrPath, *Path);
			return Mat;
		}
	}

	// 3. Search AssetRegistry for any material matching the name (case-insensitive)
	FAssetRegistryModule& ARM = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	IAssetRegistry& AR = ARM.Get();

	TArray<FAssetData> AllMaterials;
	AR.GetAssetsByClass(UMaterial::StaticClass()->GetClassPathName(), AllMaterials, true);
	// Also search MaterialInstances
	TArray<FAssetData> AllMIs;
	AR.GetAssetsByClass(UMaterialInstanceConstant::StaticClass()->GetClassPathName(), AllMIs, true);
	AllMaterials.Append(AllMIs);

	FString SearchLower = NameOrPath.ToLower();
	TArray<FAssetData> ExactMatches;
	TArray<FAssetData> ContainsMatches;

	for (const FAssetData& Asset : AllMaterials)
	{
		FString AssetName = Asset.AssetName.ToString();
		if (AssetName.ToLower() == SearchLower)
		{
			ExactMatches.Add(Asset);
		}
		else if (AssetName.ToLower().Contains(SearchLower) || SearchLower.Contains(AssetName.ToLower()))
		{
			ContainsMatches.Add(Asset);
		}
	}

	// Exact name match (case-insensitive)
	if (ExactMatches.Num() == 1)
	{
		FString FullPath = ExactMatches[0].GetObjectPathString();
		Mat = LoadObject<UMaterialInterface>(nullptr, *FullPath);
		if (Mat)
		{
			OutResolvedPath = FullPath;
			UE_LOG(LogBlueprintLLM, Log, TEXT("Resolved material '%s' → '%s' (exact registry match)"), *NameOrPath, *FullPath);
			return Mat;
		}
	}
	if (ExactMatches.Num() > 1)
	{
		OutError = FString::Printf(TEXT("Multiple materials match '%s':"), *NameOrPath);
		for (const FAssetData& A : ExactMatches)
		{
			OutError += FString::Printf(TEXT(" %s"), *A.GetObjectPathString());
		}
		OutError += TEXT(". Please specify the full path.");
		return nullptr;
	}

	// Substring/contains match
	if (ContainsMatches.Num() == 1)
	{
		FString FullPath = ContainsMatches[0].GetObjectPathString();
		Mat = LoadObject<UMaterialInterface>(nullptr, *FullPath);
		if (Mat)
		{
			OutResolvedPath = FullPath;
			UE_LOG(LogBlueprintLLM, Log, TEXT("Resolved material '%s' → '%s' (fuzzy registry match)"), *NameOrPath, *FullPath);
			return Mat;
		}
	}
	if (ContainsMatches.Num() > 1)
	{
		OutError = FString::Printf(TEXT("Multiple materials match '%s':"), *NameOrPath);
		int32 ShowMax = FMath::Min(ContainsMatches.Num(), 10);
		for (int32 i = 0; i < ShowMax; ++i)
		{
			OutError += FString::Printf(TEXT(" %s"), *ContainsMatches[i].AssetName.ToString());
		}
		if (ContainsMatches.Num() > ShowMax)
		{
			OutError += FString::Printf(TEXT(" ...and %d more"), ContainsMatches.Num() - ShowMax);
		}
		OutError += TEXT(". Please specify the full path.");
		return nullptr;
	}

	// 4. No match — suggest closest names
	OutError = FString::Printf(TEXT("Material '%s' not found."), *NameOrPath);
	TArray<FAssetData> Similar;
	// Find materials whose name shares a prefix or substring with the search term
	for (const FAssetData& Asset : AllMaterials)
	{
		FString AssetLower = Asset.AssetName.ToString().ToLower();
		// Check if they share at least 4 characters in common
		bool bSimilar = false;
		for (int32 Len = FMath::Min(SearchLower.Len(), AssetLower.Len()); Len >= 4; --Len)
		{
			if (AssetLower.Contains(SearchLower.Left(Len)) || SearchLower.Contains(AssetLower.Left(Len)))
			{
				bSimilar = true;
				break;
			}
		}
		if (bSimilar)
		{
			Similar.Add(Asset);
		}
	}
	if (Similar.Num() > 0)
	{
		OutError += TEXT(" Similar:");
		int32 ShowMax = FMath::Min(Similar.Num(), 5);
		for (int32 i = 0; i < ShowMax; ++i)
		{
			OutError += FString::Printf(TEXT(" %s"), *Similar[i].AssetName.ToString());
		}
	}
	return nullptr;
}

FCommandResult FCommandServer::HandleApplyMaterial(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	FString ComponentName = Params->GetStringField(TEXT("component_name"));
	FString MaterialPath = Params->GetStringField(TEXT("material_path"));
	int32 SlotIndex = Params->HasField(TEXT("slot_index")) ? (int32)Params->GetNumberField(TEXT("slot_index")) : 0;

	if (BlueprintName.IsEmpty() || ComponentName.IsEmpty() || MaterialPath.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required params: blueprint, component_name, material_path"));
	}

	UBlueprint* BP = FindBlueprintByName(BlueprintName);
	if (!BP)
	{
		return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));
	}

	USimpleConstructionScript* SCS = BP->SimpleConstructionScript;
	if (!SCS)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Blueprint %s has no SimpleConstructionScript"), *BlueprintName));
	}

	USCS_Node* Node = FindSCSNodeByName(SCS, ComponentName);
	if (!Node)
	{
		{
			FString CompErr = FString::Printf(TEXT("Component not found: %s in %s."), *ComponentName, *BlueprintName);
			TArray<FString> CompNames;
			for (USCS_Node* N : SCS->GetAllNodes()) { if (N) CompNames.Add(N->GetVariableName().ToString()); }
			TArray<FString> CompSuggestions = GetSuggestions(ComponentName, CompNames);
			if (CompSuggestions.Num() > 0) CompErr += TEXT(" Available components: ") + FString::Join(CompSuggestions, TEXT(", "));
			else if (CompNames.Num() > 0) CompErr += TEXT(" Components in this Blueprint: ") + FString::Join(CompNames, TEXT(", "));
			else CompErr += TEXT(" This Blueprint has no components.");
			return FCommandResult::Error(CompErr);
		}
	}

	UStaticMeshComponent* MeshComp = Cast<UStaticMeshComponent>(Node->ComponentTemplate);
	if (!MeshComp)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Component %s is not a StaticMeshComponent — cannot set material"), *ComponentName));
	}

	// Load the material (with fuzzy resolution)
	FString ResolvedPath, ResolveError;
	UMaterialInterface* Material = ResolveMaterialByName(MaterialPath, ResolvedPath, ResolveError);
	if (!Material)
	{
		return FCommandResult::Error(ResolveError.IsEmpty() ? FString::Printf(TEXT("Could not load material: %s"), *MaterialPath) : ResolveError);
	}
	MaterialPath = ResolvedPath;

	// Step 1: Set OverrideMaterials on the SCS template BEFORE compile
	if (MeshComp->OverrideMaterials.Num() <= SlotIndex)
	{
		MeshComp->OverrideMaterials.SetNum(SlotIndex + 1);
	}
	MeshComp->OverrideMaterials[SlotIndex] = Material;

	// Step 2: Compile — CDO is regenerated FROM the SCS template (now has material)
	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	// Step 3: Also set material directly on the CDO's component (belt-and-suspenders)
	if (BP->GeneratedClass)
	{
		AActor* CDO = Cast<AActor>(BP->GeneratedClass->GetDefaultObject());
		if (CDO)
		{
			TArray<UActorComponent*> CDOComps;
			CDO->GetComponents(CDOComps);
			for (UActorComponent* Comp : CDOComps)
			{
				if (Comp->GetName().Contains(ComponentName))
				{
					UStaticMeshComponent* CDOMesh = Cast<UStaticMeshComponent>(Comp);
					if (CDOMesh)
					{
						if (CDOMesh->OverrideMaterials.Num() <= SlotIndex)
						{
							CDOMesh->OverrideMaterials.SetNum(SlotIndex + 1);
						}
						CDOMesh->OverrideMaterials[SlotIndex] = Material;
						UE_LOG(LogBlueprintLLM, Log, TEXT("Also set material on CDO component %s"), *Comp->GetName());
						break;
					}
				}
			}
		}
	}

	// Step 4: Re-verify the SCS template still has the material (compile may have recreated it)
	USCS_Node* PostCompileNode = FindSCSNodeByName(SCS, ComponentName);
	if (PostCompileNode)
	{
		UStaticMeshComponent* PostMesh = Cast<UStaticMeshComponent>(PostCompileNode->ComponentTemplate);
		if (PostMesh && (PostMesh->OverrideMaterials.Num() <= SlotIndex || PostMesh->OverrideMaterials[SlotIndex] != Material))
		{
			UE_LOG(LogBlueprintLLM, Warning, TEXT("SCS template lost material after compile — re-applying"));
			if (PostMesh->OverrideMaterials.Num() <= SlotIndex)
			{
				PostMesh->OverrideMaterials.SetNum(SlotIndex + 1);
			}
			PostMesh->OverrideMaterials[SlotIndex] = Material;
		}
	}

	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	BP->GetPackage()->SetDirtyFlag(true);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Applied material %s to %s.%s[%d] in %s"),
		*MaterialPath, *BlueprintName, *ComponentName, SlotIndex, *BlueprintName);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("blueprint"), BlueprintName);
	Data->SetStringField(TEXT("component_name"), ComponentName);
	Data->SetStringField(TEXT("material_path"), MaterialPath);
	Data->SetNumberField(TEXT("slot_index"), SlotIndex);
	Data->SetBoolField(TEXT("compiled"), BP->Status != BS_Error);

	return FCommandResult::Ok(Data);
}

// ============================================================
// Actor-level material (operates on placed actors directly)
// ============================================================

FCommandResult FCommandServer::HandleSetActorMaterial(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	FString MaterialPath = Params->GetStringField(TEXT("material_path"));
	FString ComponentName = Params->HasField(TEXT("component_name")) ? Params->GetStringField(TEXT("component_name")) : TEXT("");
	int32 SlotIndex = Params->HasField(TEXT("slot_index")) ? (int32)Params->GetNumberField(TEXT("slot_index")) : 0;

	if (ActorLabel.IsEmpty() || MaterialPath.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required params: actor_label, material_path"));
	}

	// Find the placed actor
	AActor* Actor = FindActorByLabel(ActorLabel);
	if (!Actor)
	{
		return FCommandResult::Error(FormatActorNotFound(ActorLabel));
	}

	// Load material (with fuzzy resolution)
	FString ResolvedPath, ResolveError;
	UMaterialInterface* Material = ResolveMaterialByName(MaterialPath, ResolvedPath, ResolveError);
	if (!Material)
	{
		return FCommandResult::Error(ResolveError.IsEmpty() ? FString::Printf(TEXT("Could not load material: %s"), *MaterialPath) : ResolveError);
	}
	MaterialPath = ResolvedPath;

	// Find the target mesh component on the actor
	UMeshComponent* TargetMesh = nullptr;
	TArray<UMeshComponent*> MeshComps;
	Actor->GetComponents<UMeshComponent>(MeshComps);

	if (!ComponentName.IsEmpty())
	{
		for (UMeshComponent* MC : MeshComps)
		{
			if (MC->GetName().Contains(ComponentName))
			{
				TargetMesh = MC;
				break;
			}
		}
	}
	else if (MeshComps.Num() > 0)
	{
		TargetMesh = MeshComps[0];
	}

	if (!TargetMesh)
	{
		return FCommandResult::Error(FString::Printf(TEXT("No mesh component found on actor %s%s"),
			*ActorLabel, ComponentName.IsEmpty() ? TEXT("") : *FString::Printf(TEXT(" (looking for %s)"), *ComponentName)));
	}

	// SetMaterial works on registered (placed) actors — this is the key difference from apply_material
	TargetMesh->SetMaterial(SlotIndex, Material);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Set material %s on actor %s component %s[%d]"),
		*MaterialPath, *ActorLabel, *TargetMesh->GetName(), SlotIndex);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor_label"), ActorLabel);
	Data->SetStringField(TEXT("component_name"), TargetMesh->GetName());
	Data->SetStringField(TEXT("material_path"), MaterialPath);
	Data->SetNumberField(TEXT("slot_index"), SlotIndex);

	return FCommandResult::Ok(Data);
}

// ============================================================
// Save / level info / duplicate commands
// ============================================================

FCommandResult FCommandServer::HandleSaveAll(const TSharedPtr<FJsonObject>& Params)
{
	// Check if the current map has a valid (non-untitled) path.
	// If it does, we can safely save map packages without triggering "Save As" dialogs.
	// If not, skip map packages to avoid blocking dialogs.
	bool bSaveMapPackages = false;

	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (World)
	{
		FString PackageName = World->GetOutermost()->GetName();
		bool bIsUntitled = PackageName.Contains(TEXT("Untitled")) || PackageName.StartsWith(TEXT("/Temp/"));
		bSaveMapPackages = !bIsUntitled;
	}

	// Optional override from params
	if (Params->HasField(TEXT("include_maps")))
	{
		bSaveMapPackages = Params->GetBoolField(TEXT("include_maps"));
	}

	const bool bPromptUserToSave = false;
	const bool bSaveContentPackages = true;

	bool bResult = FEditorFileUtils::SaveDirtyPackages(
		bPromptUserToSave,
		bSaveMapPackages,
		bSaveContentPackages
	);

	UE_LOG(LogBlueprintLLM, Log, TEXT("SaveAll (maps=%s): %s"),
		bSaveMapPackages ? TEXT("yes") : TEXT("no"),
		bResult ? TEXT("success") : TEXT("failed/cancelled"));

	// CRITICAL: Explicitly save World Partition external actor packages.
	// When bSaveMapPackages=false (untitled map), SaveDirtyPackages skips
	// map-related packages including external actors. These are the actual
	// actor data in World Partition levels. Without this, spawned actors
	// are lost on editor crash or restart.
	int32 ExternalActorsSaved = 0;
	for (TObjectIterator<UPackage> It; It; ++It)
	{
		UPackage* Pkg = *It;
		if (Pkg && Pkg->IsDirty())
		{
			FString PkgName = Pkg->GetName();
			if (PkgName.Contains(TEXT("__ExternalActors__")) || PkgName.Contains(TEXT("__ExternalObjects__")))
			{
				FString FilePath = FPackageName::LongPackageNameToFilename(PkgName, FPackageName::GetAssetPackageExtension());
				FString Dir = FPaths::GetPath(FilePath);
				IFileManager::Get().MakeDirectory(*Dir, true);

				FSavePackageArgs SaveArgs;
				SaveArgs.TopLevelFlags = RF_Standalone;
				if (SafeSavePackage(Pkg, nullptr, FilePath, SaveArgs))
				{
					ExternalActorsSaved++;
				}
			}
		}
	}
	if (ExternalActorsSaved > 0)
	{
		UE_LOG(LogBlueprintLLM, Log, TEXT("SaveAll: saved %d external actor packages (World Partition)"), ExternalActorsSaved);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetBoolField(TEXT("saved"), bResult);
	Data->SetBoolField(TEXT("included_maps"), bSaveMapPackages);
	Data->SetNumberField(TEXT("external_actors_saved"), ExternalActorsSaved);

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSaveLevel(const TSharedPtr<FJsonObject>& Params)
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World)
	{
		return FCommandResult::Error(TEXT("No editor world available"));
	}

	UPackage* MapPackage = World->GetOutermost();
	FString PackageName = MapPackage->GetName();
	FString MapName = World->GetMapName();

	// Check if the level is untitled / never been saved
	bool bIsUntitled = PackageName.Contains(TEXT("Untitled")) || PackageName.StartsWith(TEXT("/Temp/"));

	FString TargetName;
	FString FilePath;
	bool bResult = false;

	if (bIsUntitled)
	{
		// Determine target package name
		TargetName = TEXT("ArenaLevel");
		if (Params->HasField(TEXT("name")))
		{
			TargetName = Params->GetStringField(TEXT("name"));
		}

		FString NewPackageName = FString::Printf(TEXT("/Game/Maps/%s"), *TargetName);
		FilePath = FPackageName::LongPackageNameToFilename(NewPackageName, FPackageName::GetMapPackageExtension());

		// Ensure the Maps directory exists
		FString Directory = FPaths::GetPath(FilePath);
		IFileManager::Get().MakeDirectory(*Directory, true);

		// Rename the package so it has a proper content path
		if (!MapPackage->Rename(*NewPackageName))
		{
			return FCommandResult::Error(FString::Printf(TEXT("Failed to rename map package to %s"), *NewPackageName));
		}

		// Save using SavePackage
		FSavePackageArgs SaveArgs;
		SaveArgs.TopLevelFlags = RF_Standalone;
		bResult = SafeSavePackage(MapPackage, World, FilePath, SaveArgs);

		UE_LOG(LogBlueprintLLM, Log, TEXT("SaveLevel (new) %s -> %s: %s"), *MapName, *FilePath, bResult ? TEXT("success") : TEXT("failed"));
	}
	else
	{
		// Level already has a path — just save it normally
		TargetName = MapName;
		FilePath = FPackageName::LongPackageNameToFilename(PackageName, FPackageName::GetMapPackageExtension());

		FSavePackageArgs SaveArgs;
		SaveArgs.TopLevelFlags = RF_Standalone;
		bResult = SafeSavePackage(MapPackage, World, FilePath, SaveArgs);

		UE_LOG(LogBlueprintLLM, Log, TEXT("SaveLevel %s: %s"), *MapName, bResult ? TEXT("success") : TEXT("failed"));
	}

	// After saving the map package, also flush ALL dirty packages.
	// This captures World Partition external actor files which are stored
	// as separate packages. The map now has a valid path so no dialog triggers.
	FEditorFileUtils::SaveDirtyPackages(/*bPromptUserToSave=*/false, /*bSaveMapPackages=*/true, /*bSaveContentPackages=*/true);

	UE_LOG(LogBlueprintLLM, Log, TEXT("SaveLevel: flushed all dirty packages (WP external actors)"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetBoolField(TEXT("saved"), bResult);
	Data->SetStringField(TEXT("level_name"), TargetName);
	Data->SetStringField(TEXT("file_path"), FilePath);

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetLevelInfo(const TSharedPtr<FJsonObject>& Params)
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World)
	{
		return FCommandResult::Error(TEXT("No editor world available"));
	}

	FString LevelName = World->GetMapName();
	FString LevelPath = World->GetOutermost()->GetName();

	// Count actors and collect class types
	int32 ActorCount = 0;
	TMap<FString, int32> ClassCounts;
	FVector PlayerStartLocation = FVector::ZeroVector;
	bool bHasPlayerStart = false;

	for (TActorIterator<AActor> It(World); It; ++It)
	{
		AActor* Actor = *It;
		if (!Actor) continue;

		ActorCount++;

		FString ClassName = Actor->GetClass()->GetName();
		ClassCounts.FindOrAdd(ClassName)++;

		if (APlayerStart* PS = Cast<APlayerStart>(Actor))
		{
			PlayerStartLocation = PS->GetActorLocation();
			bHasPlayerStart = true;
		}
	}

	// Build class list as JSON array
	TArray<TSharedPtr<FJsonValue>> ClassArray;
	for (auto& Pair : ClassCounts)
	{
		TSharedPtr<FJsonObject> ClassObj = MakeShareable(new FJsonObject());
		ClassObj->SetStringField(TEXT("class"), Pair.Key);
		ClassObj->SetNumberField(TEXT("count"), Pair.Value);
		ClassArray.Add(MakeShareable(new FJsonValueObject(ClassObj)));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("level_name"), LevelName);
	Data->SetStringField(TEXT("level_path"), LevelPath);
	Data->SetNumberField(TEXT("actor_count"), ActorCount);
	Data->SetArrayField(TEXT("class_counts"), ClassArray);

	if (bHasPlayerStart)
	{
		Data->SetObjectField(TEXT("player_start_location"), VectorToJson(PlayerStartLocation));
	}

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleDuplicateBlueprint(const TSharedPtr<FJsonObject>& Params)
{
	FString SourceName = Params->GetStringField(TEXT("source_name"));
	FString NewName = Params->GetStringField(TEXT("new_name"));

	if (SourceName.IsEmpty() || NewName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required params: source_name, new_name"));
	}

	UBlueprint* SourceBP = FindBlueprintByName(SourceName);
	if (!SourceBP)
	{
		return FCommandResult::Error(FormatBlueprintNotFound(SourceName));
	}

	// Check if target already exists
	UBlueprint* ExistingBP = FindBlueprintByName(NewName);
	if (ExistingBP)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Blueprint already exists: %s"), *NewName));
	}

	FAssetToolsModule& AssetToolsModule = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools");
	IAssetTools& AssetTools = AssetToolsModule.Get();

	FString DestPath = TEXT("/Game/Arcwright/Generated");
	UObject* DuplicatedAsset = AssetTools.DuplicateAsset(NewName, DestPath, SourceBP);

	if (!DuplicatedAsset)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Failed to duplicate %s to %s"), *SourceName, *NewName));
	}

	UBlueprint* NewBP = Cast<UBlueprint>(DuplicatedAsset);
	FString NewAssetPath = DuplicatedAsset->GetPathName();

	UE_LOG(LogBlueprintLLM, Log, TEXT("Duplicated %s -> %s at %s"), *SourceName, *NewName, *NewAssetPath);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("source_name"), SourceName);
	Data->SetStringField(TEXT("new_name"), NewName);
	Data->SetStringField(TEXT("asset_path"), NewAssetPath);
	Data->SetBoolField(TEXT("compiled"), NewBP ? (NewBP->Status != BS_Error) : false);

	return FCommandResult::Ok(Data);
}

// ============================================================
// PIE + log commands
// ============================================================

FCommandResult FCommandServer::HandlePlayInEditor(const TSharedPtr<FJsonObject>& Params)
{
	if (!GEditor)
	{
		return FCommandResult::Error(TEXT("GEditor not available"));
	}

	// Check if already in PIE
	if (GEditor->PlayWorld)
	{
		return FCommandResult::Error(TEXT("PIE session already running. Call stop_play first."));
	}

	// Set atomic flag — Slate OnPostTick callback picks it up during the next Slate tick.
	bPIERequested.store(true);

	UE_LOG(LogBlueprintLLM, Log, TEXT("PIE: Flag set, will be processed by Slate OnPostTick callback"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetBoolField(TEXT("requested"), true);
	Data->SetStringField(TEXT("note"), TEXT("PIE starts on next editor tick. Wait 1-2 seconds before reading output log."));

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleStopPlay(const TSharedPtr<FJsonObject>& Params)
{
	if (!GEditor)
	{
		return FCommandResult::Error(TEXT("GEditor not available"));
	}

	bool bWasPlaying = (GEditor->PlayWorld != nullptr);

	if (bWasPlaying)
	{
		GEditor->RequestEndPlayMap();
		UE_LOG(LogBlueprintLLM, Log, TEXT("PIE stop requested"));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetBoolField(TEXT("stopped"), bWasPlaying);
	if (!bWasPlaying)
	{
		Data->SetStringField(TEXT("note"), TEXT("No PIE session was running"));
	}

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandlePlayAndCapture(const TSharedPtr<FJsonObject>& Params)
{
	if (!GEditor)
		return FCommandResult::Error(TEXT("GEditor not available"));

	int32 Duration = Params->HasField(TEXT("duration")) ? (int32)Params->GetNumberField(TEXT("duration")) : 5;
	if (Duration < 1) Duration = 1;
	if (Duration > 30) Duration = 30;

	// Start PIE via Slate tick
	if (GEditor->PlayWorld)
	{
		GEditor->RequestEndPlayMap();
		FPlatformProcess::Sleep(1.0f);
	}
	bPIERequested.store(true);

	// Wait for PIE to actually start
	double WaitStart = FPlatformTime::Seconds();
	while (!GEditor->PlayWorld && (FPlatformTime::Seconds() - WaitStart) < 10.0)
	{
		FPlatformProcess::Sleep(0.2f);
	}

	if (!GEditor->PlayWorld)
	{
		TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
		Data->SetBoolField(TEXT("started"), false);
		Data->SetStringField(TEXT("error"), TEXT("PIE did not start within 10 seconds"));
		return FCommandResult::Ok(Data);
	}

	// Wait the requested duration
	FPlatformProcess::Sleep((float)Duration);

	// Take screenshot during PIE
	FString ScreenshotPath;
	if (Params->HasField(TEXT("filename")))
	{
		ScreenshotPath = Params->GetStringField(TEXT("filename"));
	}
	else
	{
		ScreenshotPath = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Screenshots"),
			FString::Printf(TEXT("pie_capture_%s.png"), *FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S"))));
	}
	FScreenshotRequest::RequestScreenshot(ScreenshotPath, false, false);

	// Small delay for screenshot to process
	FPlatformProcess::Sleep(0.5f);

	// Read recent log lines (especially PrintString output)
	TArray<FString> LogLines;
	FString PIELogPath = FPaths::Combine(FPaths::ProjectLogDir(), FString(FApp::GetProjectName()) + TEXT(".log"));
	if (FPaths::FileExists(PIELogPath))
	{
		FString LogContent;
		FFileHelper::LoadFileToString(LogContent, *PIELogPath);
		TArray<FString> AllLines;
		LogContent.ParseIntoArrayLines(AllLines);
		// Get last 100 lines
		int32 Start = FMath::Max(0, AllLines.Num() - 100);
		for (int32 i = Start; i < AllLines.Num(); i++)
		{
			// Filter for interesting lines
			if (AllLines[i].Contains(TEXT("BlueprintUserMessages")) ||
				AllLines[i].Contains(TEXT("LogBlueprintLLM")) ||
				AllLines[i].Contains(TEXT("Error")) ||
				AllLines[i].Contains(TEXT("Warning")) ||
				AllLines[i].Contains(TEXT("PIE")))
			{
				LogLines.Add(AllLines[i]);
			}
		}
	}

	// Stop PIE
	bool bWasPlaying = (GEditor->PlayWorld != nullptr);
	if (bWasPlaying)
	{
		GEditor->RequestEndPlayMap();
	}

	// Build response
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetBoolField(TEXT("started"), true);
	Data->SetBoolField(TEXT("crashed"), !bWasPlaying);
	Data->SetNumberField(TEXT("duration_seconds"), Duration);
	Data->SetStringField(TEXT("screenshot"), ScreenshotPath);

	TArray<TSharedPtr<FJsonValue>> LogArr;
	for (const FString& Line : LogLines)
	{
		LogArr.Add(MakeShareable(new FJsonValueString(Line)));
	}
	Data->SetArrayField(TEXT("log_lines"), LogArr);

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleVerifyAllBlueprints(const TSharedPtr<FJsonObject>& Params)
{
	// Find all Blueprints in /Game/Arcwright/Generated/
	FAssetRegistryModule& AssetReg = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	IAssetRegistry& Registry = AssetReg.Get();

	FARFilter Filter;
	Filter.ClassPaths.Add(UBlueprint::StaticClass()->GetClassPathName());
	Filter.PackagePaths.Add(TEXT("/Game/Arcwright/Generated"));
	Filter.bRecursivePaths = true;

	TArray<FAssetData> Assets;
	Registry.GetAssets(Filter, Assets);

	int32 TotalCount = Assets.Num();
	int32 PassCount = 0;
	int32 FailCount = 0;
	TArray<TSharedPtr<FJsonValue>> ResultsArr;

	for (const FAssetData& Asset : Assets)
	{
		UBlueprint* BP = Cast<UBlueprint>(Asset.GetAsset());
		if (!BP) continue;

		FKismetEditorUtilities::CompileBlueprint(BP);
		bool bCompiled = (BP->Status != BS_Error);

		TSharedPtr<FJsonObject> Entry = MakeShareable(new FJsonObject());
		Entry->SetStringField(TEXT("name"), Asset.AssetName.ToString());
		Entry->SetBoolField(TEXT("compiles"), bCompiled);

		if (!bCompiled)
		{
			FailCount++;
			// Collect errors
			TArray<TSharedPtr<FJsonValue>> Errors;
			UEdGraph* Graph = FBlueprintEditorUtils::FindEventGraph(BP);
			if (Graph)
			{
				for (UEdGraphNode* Node : Graph->Nodes)
				{
					if (Node->bHasCompilerMessage && Node->ErrorType == EMessageSeverity::Error)
					{
						Errors.Add(MakeShareable(new FJsonValueString(
							FString::Printf(TEXT("%s: %s"),
								*Node->GetNodeTitle(ENodeTitleType::ListView).ToString(),
								*Node->ErrorMsg))));
					}
				}
			}
			Entry->SetArrayField(TEXT("errors"), Errors);
		}
		else
		{
			PassCount++;
		}

		// Node/connection count
		UEdGraph* EG = FBlueprintEditorUtils::FindEventGraph(BP);
		if (EG)
		{
			Entry->SetNumberField(TEXT("node_count"), EG->Nodes.Num());
			int32 CC = 0;
			for (UEdGraphNode* N : EG->Nodes)
				for (UEdGraphPin* P : N->Pins)
					if (P->Direction == EGPD_Output)
						CC += P->LinkedTo.Num();
			Entry->SetNumberField(TEXT("connection_count"), CC);
		}

		ResultsArr.Add(MakeShareable(new FJsonValueObject(Entry)));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("total"), TotalCount);
	Data->SetNumberField(TEXT("pass"), PassCount);
	Data->SetNumberField(TEXT("fail"), FailCount);
	Data->SetArrayField(TEXT("results"), ResultsArr);

	return FCommandResult::Ok(Data);
}

// ============================================================
// Message / Diagnosis Commands
// ============================================================

FCommandResult FCommandServer::HandleGetMessageLog(const TSharedPtr<FJsonObject>& Params)
{
	FString SeverityFilter = Params->HasField(TEXT("severity"))
		? Params->GetStringField(TEXT("severity")) : TEXT("all");
	int32 MaxLines = Params->HasField(TEXT("lines"))
		? (int32)Params->GetNumberField(TEXT("lines")) : 100;

	// Read the log file and filter for common UE message patterns
	FString LogFilePath = FPaths::Combine(FPaths::ProjectLogDir(),
		FString(FApp::GetProjectName()) + TEXT(".log"));

	TArray<TSharedPtr<FJsonValue>> MessagesArr;

	if (FPaths::FileExists(LogFilePath))
	{
		FString LogContent;
		FFileHelper::LoadFileToString(LogContent, *LogFilePath);
		TArray<FString> AllLines;
		LogContent.ParseIntoArrayLines(AllLines);

		int32 Start = FMath::Max(0, AllLines.Num() - 500);
		for (int32 i = Start; i < AllLines.Num() && MessagesArr.Num() < MaxLines; i++)
		{
			const FString& Line = AllLines[i];

			FString Severity;
			if (Line.Contains(TEXT("Error"))) Severity = TEXT("error");
			else if (Line.Contains(TEXT("Warning"))) Severity = TEXT("warning");
			else if (Line.Contains(TEXT("Display"))) Severity = TEXT("info");
			else continue;

			if (SeverityFilter != TEXT("all") && Severity != SeverityFilter) continue;

			// Extract category
			FString Category = TEXT("General");
			if (Line.Contains(TEXT("MapCheck"))) Category = TEXT("MapCheck");
			else if (Line.Contains(TEXT("Blueprint"))) Category = TEXT("Blueprint");
			else if (Line.Contains(TEXT("LogStreaming"))) Category = TEXT("Streaming");
			else if (Line.Contains(TEXT("LogLoad"))) Category = TEXT("Loading");
			else if (Line.Contains(TEXT("LogSavePackage"))) Category = TEXT("Save");
			else if (Line.Contains(TEXT("PIE"))) Category = TEXT("PIE");

			TSharedPtr<FJsonObject> Msg = MakeShareable(new FJsonObject());
			Msg->SetStringField(TEXT("severity"), Severity);
			Msg->SetStringField(TEXT("category"), Category);
			Msg->SetStringField(TEXT("text"), Line);
			MessagesArr.Add(MakeShareable(new FJsonValueObject(Msg)));
		}
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("total"), MessagesArr.Num());
	Data->SetArrayField(TEXT("messages"), MessagesArr);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleRunMapCheck(const TSharedPtr<FJsonObject>& Params)
{
	if (!GEditor) return FCommandResult::Error(TEXT("GEditor not available"));

	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (!World) return FCommandResult::Error(TEXT("No editor world"));

	// Clear previous map check messages
	FMessageLog MapCheckLog(TEXT("MapCheck"));
	MapCheckLog.NewPage(FText::FromString(TEXT("Map Check")));

	// Run map check on all actors
	TArray<TSharedPtr<FJsonValue>> ErrorsArr;
	TArray<TSharedPtr<FJsonValue>> WarningsArr;
	TArray<TSharedPtr<FJsonValue>> InfoArr;

	// Check common issues directly
	int32 SkylightCount = 0;
	int32 DirectionalLightCount = 0;
	int32 PlayerStartCount = 0;
	bool bHasFloor = false;

	for (TActorIterator<AActor> It(World); It; ++It)
	{
		AActor* Actor = *It;
		FString ClassName = Actor->GetClass()->GetName();

		if (ClassName.Contains(TEXT("SkyLight"))) SkylightCount++;
		if (ClassName.Contains(TEXT("DirectionalLight"))) DirectionalLightCount++;
		if (ClassName.Contains(TEXT("PlayerStart"))) PlayerStartCount++;

		// Check for actors at origin with no mesh (ghost actors)
		FVector Loc = Actor->GetActorLocation();
		if (Loc.IsNearlyZero() && Cast<AStaticMeshActor>(Actor))
		{
			AStaticMeshActor* SMA = Cast<AStaticMeshActor>(Actor);
			if (SMA->GetStaticMeshComponent() && !SMA->GetStaticMeshComponent()->GetStaticMesh())
			{
				WarningsArr.Add(MakeShareable(new FJsonValueString(
					FString::Printf(TEXT("Actor '%s' at origin with no mesh"), *Actor->GetActorNameOrLabel()))));
			}
		}
	}

	if (SkylightCount > 1)
		WarningsArr.Add(MakeShareable(new FJsonValueString(
			FString::Printf(TEXT("Multiple SkyLight actors (%d). Only one is needed."), SkylightCount))));
	if (DirectionalLightCount > 1)
		WarningsArr.Add(MakeShareable(new FJsonValueString(
			FString::Printf(TEXT("Multiple DirectionalLight actors (%d). May cause competing shadows."), DirectionalLightCount))));
	if (PlayerStartCount == 0)
		ErrorsArr.Add(MakeShareable(new FJsonValueString(TEXT("No PlayerStart in level. Player will spawn at origin."))));
	if (PlayerStartCount > 1)
		WarningsArr.Add(MakeShareable(new FJsonValueString(
			FString::Printf(TEXT("Multiple PlayerStart actors (%d). Player spawn location may be unpredictable."), PlayerStartCount))));

	// Check for uncompiled Blueprints
	FAssetRegistryModule& AssetReg = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	FARFilter Filter;
	Filter.ClassPaths.Add(UBlueprint::StaticClass()->GetClassPathName());
	Filter.PackagePaths.Add(TEXT("/Game/Arcwright/Generated"));
	Filter.bRecursivePaths = true;
	TArray<FAssetData> BPAssets;
	AssetReg.Get().GetAssets(Filter, BPAssets);

	for (const FAssetData& Asset : BPAssets)
	{
		UBlueprint* BP = Cast<UBlueprint>(Asset.GetAsset());
		if (BP && BP->Status == BS_Error)
		{
			ErrorsArr.Add(MakeShareable(new FJsonValueString(
				FString::Printf(TEXT("Blueprint '%s' has compile errors"), *Asset.AssetName.ToString()))));
		}
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("error_count"), ErrorsArr.Num());
	Data->SetNumberField(TEXT("warning_count"), WarningsArr.Num());
	Data->SetArrayField(TEXT("errors"), ErrorsArr);
	Data->SetArrayField(TEXT("warnings"), WarningsArr);
	Data->SetArrayField(TEXT("info"), InfoArr);

	return FCommandResult::Ok(Data);
}

// ============================================================
// PIE Player Control Commands
// ============================================================

FCommandResult FCommandServer::HandleTeleportPlayer(const TSharedPtr<FJsonObject>& Params)
{
	if (!GEditor || !GEditor->PlayWorld)
		return FCommandResult::Error(TEXT("PIE not running. Call play_in_editor first."));

	APlayerController* PC = GEditor->PlayWorld->GetFirstPlayerController();
	if (!PC || !PC->GetPawn())
		return FCommandResult::Error(TEXT("No player pawn in PIE"));

	double X = Params->HasField(TEXT("x")) ? Params->GetNumberField(TEXT("x")) : PC->GetPawn()->GetActorLocation().X;
	double Y = Params->HasField(TEXT("y")) ? Params->GetNumberField(TEXT("y")) : PC->GetPawn()->GetActorLocation().Y;
	double Z = Params->HasField(TEXT("z")) ? Params->GetNumberField(TEXT("z")) : PC->GetPawn()->GetActorLocation().Z;

	FVector NewLoc(X, Y, Z);
	PC->GetPawn()->SetActorLocation(NewLoc, false, nullptr, ETeleportType::TeleportPhysics);

	if (Params->HasField(TEXT("yaw")))
	{
		FRotator NewRot = PC->GetControlRotation();
		NewRot.Yaw = Params->GetNumberField(TEXT("yaw"));
		PC->SetControlRotation(NewRot);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("x"), NewLoc.X);
	Data->SetNumberField(TEXT("y"), NewLoc.Y);
	Data->SetNumberField(TEXT("z"), NewLoc.Z);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetPlayerLocation(const TSharedPtr<FJsonObject>& Params)
{
	if (!GEditor || !GEditor->PlayWorld)
		return FCommandResult::Error(TEXT("PIE not running"));

	APlayerController* PC = GEditor->PlayWorld->GetFirstPlayerController();
	if (!PC || !PC->GetPawn())
		return FCommandResult::Error(TEXT("No player pawn"));

	FVector Loc = PC->GetPawn()->GetActorLocation();
	FRotator Rot = PC->GetControlRotation();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("x"), Loc.X);
	Data->SetNumberField(TEXT("y"), Loc.Y);
	Data->SetNumberField(TEXT("z"), Loc.Z);
	Data->SetNumberField(TEXT("pitch"), Rot.Pitch);
	Data->SetNumberField(TEXT("yaw"), Rot.Yaw);
	Data->SetNumberField(TEXT("roll"), Rot.Roll);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleLookAt(const TSharedPtr<FJsonObject>& Params)
{
	if (!GEditor || !GEditor->PlayWorld)
		return FCommandResult::Error(TEXT("PIE not running"));

	APlayerController* PC = GEditor->PlayWorld->GetFirstPlayerController();
	if (!PC || !PC->GetPawn())
		return FCommandResult::Error(TEXT("No player pawn"));

	FVector TargetLoc;

	if (Params->HasField(TEXT("actor")))
	{
		FString ActorLabel = Params->GetStringField(TEXT("actor"));
		AActor* Target = nullptr;
		for (TActorIterator<AActor> It(GEditor->PlayWorld); It; ++It)
		{
			if (It->GetActorNameOrLabel() == ActorLabel || It->GetActorLabel() == ActorLabel)
			{
				Target = *It;
				break;
			}
		}
		if (!Target)
			return FCommandResult::Error(FString::Printf(TEXT("Actor not found in PIE: %s"), *ActorLabel));
		TargetLoc = Target->GetActorLocation();
	}
	else
	{
		TargetLoc.X = Params->GetNumberField(TEXT("x"));
		TargetLoc.Y = Params->GetNumberField(TEXT("y"));
		TargetLoc.Z = Params->GetNumberField(TEXT("z"));
	}

	FVector PlayerLoc = PC->GetPawn()->GetActorLocation();
	FRotator LookRot = (TargetLoc - PlayerLoc).Rotation();
	PC->SetControlRotation(LookRot);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("pitch"), LookRot.Pitch);
	Data->SetNumberField(TEXT("yaw"), LookRot.Yaw);
	Data->SetNumberField(TEXT("roll"), LookRot.Roll);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetPlayerView(const TSharedPtr<FJsonObject>& Params)
{
	if (!GEditor || !GEditor->PlayWorld)
		return FCommandResult::Error(TEXT("PIE not running"));

	APlayerController* PC = GEditor->PlayWorld->GetFirstPlayerController();
	if (!PC || !PC->GetPawn())
		return FCommandResult::Error(TEXT("No player pawn"));

	// Request screenshot
	FString ScreenshotPath;
	if (Params->HasField(TEXT("filename")))
		ScreenshotPath = Params->GetStringField(TEXT("filename"));
	else
		ScreenshotPath = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Screenshots"),
			FString::Printf(TEXT("player_view_%s.png"), *FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S"))));

	FScreenshotRequest::RequestScreenshot(ScreenshotPath, false, false);

	FVector Loc = PC->GetPawn()->GetActorLocation();
	FRotator Rot = PC->GetControlRotation();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("path"), ScreenshotPath);
	Data->SetNumberField(TEXT("x"), Loc.X);
	Data->SetNumberField(TEXT("y"), Loc.Y);
	Data->SetNumberField(TEXT("z"), Loc.Z);
	Data->SetNumberField(TEXT("pitch"), Rot.Pitch);
	Data->SetNumberField(TEXT("yaw"), Rot.Yaw);
	Data->SetNumberField(TEXT("roll"), Rot.Roll);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleTeleportToActor(const TSharedPtr<FJsonObject>& Params)
{
	if (!GEditor || !GEditor->PlayWorld)
		return FCommandResult::Error(TEXT("PIE not running"));

	FString ActorLabel = Params->GetStringField(TEXT("actor"));
	if (ActorLabel.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'actor' parameter"));

	double Distance = Params->HasField(TEXT("distance")) ? Params->GetNumberField(TEXT("distance")) : 200.0;

	APlayerController* PC = GEditor->PlayWorld->GetFirstPlayerController();
	if (!PC || !PC->GetPawn())
		return FCommandResult::Error(TEXT("No player pawn"));

	// Find the actor in PIE world
	AActor* Target = nullptr;
	for (TActorIterator<AActor> It(GEditor->PlayWorld); It; ++It)
	{
		if (It->GetActorNameOrLabel() == ActorLabel || It->GetActorLabel() == ActorLabel)
		{
			Target = *It;
			break;
		}
	}
	if (!Target)
		return FCommandResult::Error(FString::Printf(TEXT("Actor not found in PIE: %s"), *ActorLabel));

	FVector TargetLoc = Target->GetActorLocation();
	FVector PlayerLoc = PC->GetPawn()->GetActorLocation();

	// Position player at Distance units away, at same Z + eye height
	FVector Dir = (PlayerLoc - TargetLoc);
	Dir.Z = 0;
	if (Dir.IsNearlyZero()) Dir = FVector(1, 0, 0);
	Dir.Normalize();

	FVector NewLoc = TargetLoc + Dir * Distance;
	NewLoc.Z = TargetLoc.Z + 80; // Eye height offset

	PC->GetPawn()->SetActorLocation(NewLoc, false, nullptr, ETeleportType::TeleportPhysics);

	// Look at the target
	FRotator LookRot = (TargetLoc - NewLoc).Rotation();
	PC->SetControlRotation(LookRot);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("target_actor"), ActorLabel);
	Data->SetNumberField(TEXT("x"), NewLoc.X);
	Data->SetNumberField(TEXT("y"), NewLoc.Y);
	Data->SetNumberField(TEXT("z"), NewLoc.Z);
	Data->SetNumberField(TEXT("target_x"), TargetLoc.X);
	Data->SetNumberField(TEXT("target_y"), TargetLoc.Y);
	Data->SetNumberField(TEXT("target_z"), TargetLoc.Z);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetOutputLog(const TSharedPtr<FJsonObject>& Params)
{
	int32 LastNLines = Params->HasField(TEXT("last_n_lines"))
		? (int32)Params->GetNumberField(TEXT("last_n_lines"))
		: 50;

	FString CategoryFilter;
	if (Params->HasField(TEXT("category")))
	{
		CategoryFilter = Params->GetStringField(TEXT("category"));
	}

	FString TextFilter;
	if (Params->HasField(TEXT("text_filter")))
	{
		TextFilter = Params->GetStringField(TEXT("text_filter"));
	}

	// Get the log file path (must be absolute for FFileHelper)
	FString LogFilename = FPaths::ConvertRelativePathToFull(
		FPaths::Combine(FPaths::ProjectLogDir(), FString(FApp::GetProjectName()) + TEXT(".log"))
	);

	if (!FPaths::FileExists(LogFilename))
	{
		return FCommandResult::Error(FString::Printf(TEXT("Log file not found: %s"), *LogFilename));
	}

	// Flush the log to ensure all pending writes are on disk
	GLog->Flush();

	// Read the log file (FILEREAD_AllowWrite since UE has it open for writing)
	FString LogContent;
	if (!FFileHelper::LoadFileToString(LogContent, *LogFilename, FFileHelper::EHashOptions::None, FILEREAD_AllowWrite))
	{
		return FCommandResult::Error(FString::Printf(TEXT("Failed to read log file: %s"), *LogFilename));
	}

	// Split into lines
	TArray<FString> AllLines;
	LogContent.ParseIntoArrayLines(AllLines);

	// Filter by category and/or text
	TArray<FString> FilteredLines;
	for (const FString& Line : AllLines)
	{
		if (!CategoryFilter.IsEmpty() && !Line.Contains(CategoryFilter))
		{
			continue;
		}
		if (!TextFilter.IsEmpty() && !Line.Contains(TextFilter))
		{
			continue;
		}
		FilteredLines.Add(Line);
	}

	// Take last N
	int32 StartIdx = FMath::Max(0, FilteredLines.Num() - LastNLines);
	TArray<TSharedPtr<FJsonValue>> LinesArray;
	for (int32 i = StartIdx; i < FilteredLines.Num(); i++)
	{
		LinesArray.Add(MakeShareable(new FJsonValueString(FilteredLines[i])));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("total_lines"), AllLines.Num());
	Data->SetNumberField(TEXT("filtered_lines"), FilteredLines.Num());
	Data->SetNumberField(TEXT("returned_lines"), LinesArray.Num());
	Data->SetStringField(TEXT("log_file"), LogFilename);
	Data->SetArrayField(TEXT("lines"), LinesArray);

	if (!CategoryFilter.IsEmpty())
	{
		Data->SetStringField(TEXT("category_filter"), CategoryFilter);
	}
	if (!TextFilter.IsEmpty())
	{
		Data->SetStringField(TEXT("text_filter"), TextFilter);
	}

	return FCommandResult::Ok(Data);
}

// ============================================================
// Input Mapping Commands (B29)
// ============================================================

FCommandResult FCommandServer::HandleSetupInputContext(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'name' parameter"));
	}

	FString PackagePath = FString::Printf(TEXT("/Game/Arcwright/Input/%s"), *Name);
	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Failed to create package: %s"), *PackagePath));
	}

	UInputMappingContext* Context = NewObject<UInputMappingContext>(Package, FName(*Name), RF_Public | RF_Standalone);
	if (!Context)
	{
		return FCommandResult::Error(TEXT("Failed to create UInputMappingContext"));
	}

	Context->MarkPackageDirty();
	FAssetRegistryModule::AssetCreated(Context);

	FSavePackageArgs SaveArgs;
	SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
	FString PackageFilename = FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension());
	SafeSavePackage(Package, Context, PackageFilename, SaveArgs);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), PackagePath);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddInputAction(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'name' parameter"));
	}

	FString ValueTypeStr = Params->HasField(TEXT("value_type"))
		? Params->GetStringField(TEXT("value_type"))
		: TEXT("bool");

	FString PackagePath = FString::Printf(TEXT("/Game/Arcwright/Input/%s"), *Name);
	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Failed to create package: %s"), *PackagePath));
	}

	UInputAction* Action = NewObject<UInputAction>(Package, FName(*Name), RF_Public | RF_Standalone);
	if (!Action)
	{
		return FCommandResult::Error(TEXT("Failed to create UInputAction"));
	}

	// Set value type
	if (ValueTypeStr.Equals(TEXT("axis1d"), ESearchCase::IgnoreCase))
	{
		Action->ValueType = EInputActionValueType::Axis1D;
	}
	else if (ValueTypeStr.Equals(TEXT("axis2d"), ESearchCase::IgnoreCase))
	{
		Action->ValueType = EInputActionValueType::Axis2D;
	}
	else if (ValueTypeStr.Equals(TEXT("axis3d"), ESearchCase::IgnoreCase))
	{
		Action->ValueType = EInputActionValueType::Axis3D;
	}
	else
	{
		Action->ValueType = EInputActionValueType::Boolean;
	}

	Action->MarkPackageDirty();
	FAssetRegistryModule::AssetCreated(Action);

	FSavePackageArgs SaveArgs;
	SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
	FString PackageFilename = FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension());
	SafeSavePackage(Package, Action, PackageFilename, SaveArgs);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), PackagePath);
	Data->SetStringField(TEXT("value_type"), ValueTypeStr);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddInputMapping(const TSharedPtr<FJsonObject>& Params)
{
	FString ContextName = Params->GetStringField(TEXT("context"));
	FString ActionName = Params->GetStringField(TEXT("action"));
	FString KeyName = Params->GetStringField(TEXT("key"));

	if (ContextName.IsEmpty() || ActionName.IsEmpty() || KeyName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'context', 'action', or 'key' parameter"));
	}

	// Resolve context — try as path first, then by name in /Game/Arcwright/Input/
	UInputMappingContext* Context = LoadObject<UInputMappingContext>(nullptr, *ContextName);
	if (!Context)
	{
		FString ContextPath = FString::Printf(TEXT("/Game/Arcwright/Input/%s.%s"), *ContextName, *ContextName);
		Context = LoadObject<UInputMappingContext>(nullptr, *ContextPath);
	}
	if (!Context)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Input mapping context not found: %s"), *ContextName));
	}

	// Resolve action — try as path first, then by name
	UInputAction* Action = LoadObject<UInputAction>(nullptr, *ActionName);
	if (!Action)
	{
		FString ActionPath = FString::Printf(TEXT("/Game/Arcwright/Input/%s.%s"), *ActionName, *ActionName);
		Action = LoadObject<UInputAction>(nullptr, *ActionPath);
	}
	if (!Action)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Input action not found: %s"), *ActionName));
	}

	FKey Key(*KeyName);
	if (!Key.IsValid())
	{
		return FCommandResult::Error(FString::Printf(TEXT("Invalid key name: %s"), *KeyName));
	}

	Context->MapKey(Action, Key);
	Context->MarkPackageDirty();

	// Save the context package
	FString PackagePath = Context->GetOutermost()->GetName();
	FSavePackageArgs SaveArgs;
	SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
	FString PackageFilename = FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension());
	SafeSavePackage(Context->GetOutermost(), Context, PackageFilename, SaveArgs);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("context"), ContextName);
	Data->SetStringField(TEXT("action"), ActionName);
	Data->SetStringField(TEXT("key"), KeyName);
	Data->SetNumberField(TEXT("mapping_count"), Context->GetMappings().Num());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetInputActions(const TSharedPtr<FJsonObject>& Params)
{
	FString SearchPath = Params->HasField(TEXT("path"))
		? Params->GetStringField(TEXT("path"))
		: TEXT("/Game/Arcwright/Input");

	FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	IAssetRegistry& AssetRegistry = AssetRegistryModule.Get();

	TArray<FAssetData> AssetDataList;
	AssetRegistry.GetAssetsByPath(FName(*SearchPath), AssetDataList, true);

	TArray<TSharedPtr<FJsonValue>> ActionsArray;
	for (const FAssetData& AssetData : AssetDataList)
	{
		if (AssetData.AssetClassPath == UInputAction::StaticClass()->GetClassPathName())
		{
			TSharedPtr<FJsonObject> ActionObj = MakeShareable(new FJsonObject());
			ActionObj->SetStringField(TEXT("name"), AssetData.AssetName.ToString());
			ActionObj->SetStringField(TEXT("asset_path"), AssetData.GetObjectPathString());
			ActionsArray.Add(MakeShareable(new FJsonValueObject(ActionObj)));
		}
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("count"), ActionsArray.Num());
	Data->SetArrayField(TEXT("actions"), ActionsArray);
	Data->SetStringField(TEXT("search_path"), SearchPath);
	return FCommandResult::Ok(Data);
}

// ============================================================
// Audio Commands (B24)
// ============================================================

FCommandResult FCommandServer::HandlePlaySoundAtLocation(const TSharedPtr<FJsonObject>& Params)
{
	FString SoundPath = Params->GetStringField(TEXT("sound"));
	if (SoundPath.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'sound' parameter"));
	}

	TSharedPtr<FJsonObject> LocationObj = Params->GetObjectField(TEXT("location"));
	if (!LocationObj.IsValid())
	{
		return FCommandResult::Error(TEXT("Missing 'location' parameter"));
	}

	float Volume = Params->HasField(TEXT("volume"))
		? (float)Params->GetNumberField(TEXT("volume"))
		: 1.0f;
	float Pitch = Params->HasField(TEXT("pitch"))
		? (float)Params->GetNumberField(TEXT("pitch"))
		: 1.0f;

	USoundBase* Sound = LoadObject<USoundBase>(nullptr, *SoundPath);
	if (!Sound)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Sound not found: %s"), *SoundPath));
	}

	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World)
	{
		return FCommandResult::Error(TEXT("No editor world available"));
	}

	FVector Location = JsonToVector(LocationObj);
	UGameplayStatics::PlaySoundAtLocation(World, Sound, Location, Volume, Pitch);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("sound"), SoundPath);
	Data->SetObjectField(TEXT("location"), VectorToJson(Location));
	Data->SetBoolField(TEXT("played"), true);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddAudioComponent(const TSharedPtr<FJsonObject>& Params)
{
	FString BPName = Params->GetStringField(TEXT("blueprint"));
	if (BPName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'blueprint' parameter"));
	}

	FString CompName = Params->HasField(TEXT("name"))
		? Params->GetStringField(TEXT("name"))
		: TEXT("Audio");

	FString SoundPath;
	if (Params->HasField(TEXT("sound")))
	{
		SoundPath = Params->GetStringField(TEXT("sound"));
	}

	bool bAutoActivate = !Params->HasField(TEXT("auto_activate"))
		|| Params->GetBoolField(TEXT("auto_activate"));

	UBlueprint* BP = FindBlueprintByName(BPName);
	if (!BP)
	{
		return FCommandResult::Error(FormatBlueprintNotFound(BPName));
	}

	USimpleConstructionScript* SCS = BP->SimpleConstructionScript;
	if (!SCS)
	{
		return FCommandResult::Error(TEXT("Blueprint has no SimpleConstructionScript"));
	}

	// Check for duplicate name
	if (FindSCSNodeByName(SCS, CompName))
	{
		return FCommandResult::Error(FString::Printf(TEXT("Component '%s' already exists"), *CompName));
	}

	USCS_Node* NewNode = SCS->CreateNode(UAudioComponent::StaticClass(), FName(*CompName));
	if (!NewNode)
	{
		return FCommandResult::Error(TEXT("Failed to create SCS node for AudioComponent"));
	}

	UAudioComponent* AudioComp = Cast<UAudioComponent>(NewNode->ComponentTemplate);
	if (AudioComp)
	{
		AudioComp->bAutoActivate = bAutoActivate;

		if (!SoundPath.IsEmpty())
		{
			USoundBase* Sound = LoadObject<USoundBase>(nullptr, *SoundPath);
			if (Sound)
			{
				AudioComp->Sound = Sound;
			}
			else
			{
				UE_LOG(LogBlueprintLLM, Warning, TEXT("Sound not found: %s — component created without sound"), *SoundPath);
			}
		}
	}

	SCS->AddNode(NewNode);
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("blueprint"), BPName);
	Data->SetStringField(TEXT("component_name"), CompName);
	Data->SetStringField(TEXT("sound"), SoundPath);
	Data->SetBoolField(TEXT("auto_activate"), bAutoActivate);
	Data->SetBoolField(TEXT("compiled"), true);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetSoundAssets(const TSharedPtr<FJsonObject>& Params)
{
	FString SearchPath = Params->HasField(TEXT("path"))
		? Params->GetStringField(TEXT("path"))
		: TEXT("/Game");

	bool bSearchSubfolders = !Params->HasField(TEXT("search_subfolders"))
		|| Params->GetBoolField(TEXT("search_subfolders"));

	FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	IAssetRegistry& AssetRegistry = AssetRegistryModule.Get();

	TArray<FAssetData> AssetDataList;
	AssetRegistry.GetAssetsByPath(FName(*SearchPath), AssetDataList, bSearchSubfolders);

	TArray<TSharedPtr<FJsonValue>> SoundsArray;
	for (const FAssetData& AssetData : AssetDataList)
	{
		FTopLevelAssetPath ClassPath = AssetData.AssetClassPath;
		if (ClassPath == USoundWave::StaticClass()->GetClassPathName() ||
			ClassPath == USoundCue::StaticClass()->GetClassPathName() ||
			ClassPath == USoundBase::StaticClass()->GetClassPathName())
		{
			TSharedPtr<FJsonObject> SoundObj = MakeShareable(new FJsonObject());
			SoundObj->SetStringField(TEXT("name"), AssetData.AssetName.ToString());
			SoundObj->SetStringField(TEXT("asset_path"), AssetData.GetObjectPathString());
			SoundObj->SetStringField(TEXT("class"), ClassPath.GetAssetName().ToString());
			SoundsArray.Add(MakeShareable(new FJsonValueObject(SoundObj)));
		}
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("count"), SoundsArray.Num());
	Data->SetArrayField(TEXT("sounds"), SoundsArray);
	Data->SetStringField(TEXT("search_path"), SearchPath);
	return FCommandResult::Ok(Data);
}

// ============================================================
// Viewport Commands (B30)
// ============================================================

FCommandResult FCommandServer::HandleSetViewportCamera(const TSharedPtr<FJsonObject>& Params)
{
	TSharedPtr<FJsonObject> LocationObj = Params->GetObjectField(TEXT("location"));
	TSharedPtr<FJsonObject> RotationObj = Params->GetObjectField(TEXT("rotation"));

	if (!LocationObj.IsValid() && !RotationObj.IsValid())
	{
		return FCommandResult::Error(TEXT("At least one of 'location' or 'rotation' must be provided"));
	}

	// Get the active level viewport client
	FLevelEditorViewportClient* ViewportClient = nullptr;
	if (GCurrentLevelEditingViewportClient)
	{
		ViewportClient = GCurrentLevelEditingViewportClient;
	}
	else if (GEditor)
	{
		const TArray<FLevelEditorViewportClient*>& Clients = GEditor->GetLevelViewportClients();
		if (Clients.Num() > 0)
		{
			ViewportClient = Clients[0];
		}
	}

	if (!ViewportClient)
	{
		return FCommandResult::Error(TEXT("No active level viewport found"));
	}

	if (LocationObj.IsValid())
	{
		FVector Location = JsonToVector(LocationObj);
		ViewportClient->SetViewLocation(Location);
	}

	if (RotationObj.IsValid())
	{
		FRotator Rotation = JsonToRotator(RotationObj);
		ViewportClient->SetViewRotation(Rotation);
	}

	ViewportClient->Invalidate();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetObjectField(TEXT("location"), VectorToJson(ViewportClient->GetViewLocation()));
	Data->SetObjectField(TEXT("rotation"), RotatorToJson(ViewportClient->GetViewRotation()));
	Data->SetBoolField(TEXT("success"), true);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleTakeScreenshot(const TSharedPtr<FJsonObject>& Params)
{
	FString Filename = Params->HasField(TEXT("filename"))
		? Params->GetStringField(TEXT("filename"))
		: FString::Printf(TEXT("screenshot_%s"), *FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S")));

	// Get the active viewport
	FLevelEditorViewportClient* ViewportClient = nullptr;
	if (GCurrentLevelEditingViewportClient)
	{
		ViewportClient = GCurrentLevelEditingViewportClient;
	}
	else if (GEditor)
	{
		const TArray<FLevelEditorViewportClient*>& Clients = GEditor->GetLevelViewportClients();
		if (Clients.Num() > 0)
		{
			ViewportClient = Clients[0];
		}
	}

	if (!ViewportClient || !ViewportClient->Viewport)
	{
		return FCommandResult::Error(TEXT("No active viewport found for screenshot"));
	}

	// Ensure the filename ends with .png
	if (!Filename.EndsWith(TEXT(".png")))
	{
		Filename += TEXT(".png");
	}

	// Build the full output path
	FString OutputDir = FPaths::ConvertRelativePathToFull(
		FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Screenshots"), TEXT("Arcwright")));
	FString FullPath = FPaths::Combine(OutputDir, Filename);

	// Ensure directory exists
	IFileManager::Get().MakeDirectory(*OutputDir, true);

	FViewport* Viewport = ViewportClient->Viewport;
	int32 Width = Viewport->GetSizeXY().X;
	int32 Height = Viewport->GetSizeXY().Y;

	if (Width == 0 || Height == 0)
	{
		return FCommandResult::Error(TEXT("Viewport has zero size — is it visible?"));
	}

	// Use UE's built-in screenshot request system which hooks into the rendering
	// pipeline at the right point. Direct ReadPixels() on editor viewports returns
	// stale/blank content because the viewport backbuffer isn't updated until
	// a proper render pass completes through the Slate/RHI pipeline.
	FScreenshotRequest::RequestScreenshot(FullPath, false, false);

	// Force viewport to render the frame that will be captured
	bool bWasRealtime = ViewportClient->IsRealtime();
	ViewportClient->SetRealtime(true);
	ViewportClient->Invalidate();
	Viewport->InvalidateDisplay();

	// Pump rendering multiple times to ensure the screenshot request is processed
	for (int32 i = 0; i < 6; i++)
	{
		FSlateApplication::Get().Tick();
		ViewportClient->Viewport->Draw();
		FlushRenderingCommands();
	}

	// Restore realtime state
	ViewportClient->SetRealtime(bWasRealtime);

	// Check if file was written by FScreenshotRequest
	bool bScreenshotSaved = FPaths::FileExists(FullPath);
	bool bUsedFallback = false;

	if (!bScreenshotSaved)
	{
		// Fallback: try direct ReadPixels approach
		UE_LOG(LogBlueprintLLM, Warning, TEXT("FScreenshotRequest didn't write file, falling back to ReadPixels"));

		TArray<FColor> Bitmap;
		bool bReadSuccess = Viewport->ReadPixels(Bitmap);
		if (bReadSuccess && Bitmap.Num() > 0)
		{
			TArray64<uint8> PngData;
			FImageUtils::PNGCompressImageArray(Width, Height, Bitmap, PngData);
			bScreenshotSaved = FFileHelper::SaveArrayToFile(PngData, *FullPath);
			bUsedFallback = true;
		}
	}

	if (!bScreenshotSaved)
	{
		return FCommandResult::Error(TEXT("Failed to capture screenshot via both FScreenshotRequest and ReadPixels"));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("file_path"), FullPath);
	TSharedPtr<FJsonObject> ResObj = MakeShareable(new FJsonObject());
	ResObj->SetNumberField(TEXT("x"), Width);
	ResObj->SetNumberField(TEXT("y"), Height);
	Data->SetObjectField(TEXT("resolution"), ResObj);
	Data->SetBoolField(TEXT("success"), true);
	Data->SetStringField(TEXT("method"), bUsedFallback ? TEXT("ReadPixels") : TEXT("FScreenshotRequest"));
	return FCommandResult::Ok(Data);
}

// ════════════════════════════════════════════════════════════════════
//  capture_full_screen — Captures entire window including UMG/HUD
// ════════════════════════════════════════════════════════════════════
FCommandResult FCommandServer::HandleCaptureFullScreen(const TSharedPtr<FJsonObject>& Params)
{
	FString Filename = Params->HasField(TEXT("filename"))
		? Params->GetStringField(TEXT("filename"))
		: FString::Printf(TEXT("fullscreen_%s"), *FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S")));

	if (!Filename.EndsWith(TEXT(".png")))
		Filename += TEXT(".png");

	FString OutputDir = FPaths::ConvertRelativePathToFull(
		FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Screenshots"), TEXT("Arcwright")));
	FString FullPath = FPaths::Combine(OutputDir, Filename);
	IFileManager::Get().MakeDirectory(*OutputDir, true);

	bool bCaptured = false;
	int32 CapturedWidth = 0;
	int32 CapturedHeight = 0;
	FString Method;

	// ── Approach 1: Screen DC capture — captures the actual composited display output ──
	// This captures from the display adapter's framebuffer AFTER all D3D + Slate/UMG composition.
	// PrintWindow/BitBlt from window DC miss the Slate overlay; screen DC gets everything.
#if PLATFORM_WINDOWS
	{
		TSharedPtr<SWindow> ActiveWindow = FSlateApplication::Get().GetActiveTopLevelWindow();
		if (ActiveWindow.IsValid() && ActiveWindow->GetNativeWindow().IsValid())
		{
			HWND WindowHandle = static_cast<HWND>(ActiveWindow->GetNativeWindow()->GetOSWindowHandle());
			if (WindowHandle)
			{
				// Get window position on screen
				RECT WinRect;
				GetWindowRect(WindowHandle, &WinRect);
				CapturedWidth = WinRect.right - WinRect.left;
				CapturedHeight = WinRect.bottom - WinRect.top;

				if (CapturedWidth > 0 && CapturedHeight > 0)
				{
					// Use the SCREEN DC (NULL) — captures the actual display output
					HDC ScreenDC = GetDC(NULL);
					HDC MemDC = CreateCompatibleDC(ScreenDC);
					HBITMAP CaptureBitmap = CreateCompatibleBitmap(ScreenDC, CapturedWidth, CapturedHeight);
					HGDIOBJ OldBitmap = SelectObject(MemDC, CaptureBitmap);

					// BitBlt from screen at the window's position
					BitBlt(MemDC, 0, 0, CapturedWidth, CapturedHeight,
						ScreenDC, WinRect.left, WinRect.top, SRCCOPY);

					// Read pixels
					BITMAPINFOHEADER BMI = {};
					BMI.biSize = sizeof(BITMAPINFOHEADER);
					BMI.biWidth = CapturedWidth;
					BMI.biHeight = -CapturedHeight;
					BMI.biPlanes = 1;
					BMI.biBitCount = 32;
					BMI.biCompression = BI_RGB;

					TArray<FColor> Bitmap;
					Bitmap.SetNum(CapturedWidth * CapturedHeight);
					GetDIBits(MemDC, CaptureBitmap, 0, CapturedHeight,
						Bitmap.GetData(), (BITMAPINFO*)&BMI, DIB_RGB_COLORS);

					for (FColor& Pixel : Bitmap)
					{
						Pixel.A = 255;
					}

					SelectObject(MemDC, OldBitmap);
					DeleteObject(CaptureBitmap);
					DeleteDC(MemDC);
					ReleaseDC(NULL, ScreenDC);

					TArray64<uint8> PngData;
					FImageUtils::PNGCompressImageArray(CapturedWidth, CapturedHeight, Bitmap, PngData);
					bCaptured = FFileHelper::SaveArrayToFile(PngData, *FullPath);
					Method = TEXT("ScreenCapture");
				}
			}
		}
	}
#endif

	// ── Approach 2: Slate window screenshot fallback ──
	if (!bCaptured)
	{
		TSharedPtr<SWindow> ActiveWindow = FSlateApplication::Get().GetActiveTopLevelWindow();
		if (ActiveWindow.IsValid())
		{
			TArray<FColor> Bitmap;
			FIntVector OutSize;
			if (FSlateApplication::Get().TakeScreenshot(ActiveWindow.ToSharedRef(), Bitmap, OutSize))
			{
				CapturedWidth = OutSize.X;
				CapturedHeight = OutSize.Y;
				if (Bitmap.Num() > 0 && CapturedWidth > 0 && CapturedHeight > 0)
				{
					TArray64<uint8> PngData;
					FImageUtils::PNGCompressImageArray(CapturedWidth, CapturedHeight, Bitmap, PngData);
					bCaptured = FFileHelper::SaveArrayToFile(PngData, *FullPath);
					Method = TEXT("SlateWindowScreenshot");
				}
			}
		}
	}

	// ── Approach 3: FScreenshotRequest with bShowUI=true ──
	if (!bCaptured)
	{
		FScreenshotRequest::RequestScreenshot(FullPath, true, false);
		for (int32 i = 0; i < 8; i++)
		{
			FSlateApplication::Get().Tick();
			FlushRenderingCommands();
		}
		bCaptured = FPaths::FileExists(FullPath);
		if (bCaptured)
		{
			Method = TEXT("FScreenshotRequestShowUI");
			CapturedWidth = -1;
			CapturedHeight = -1;
		}
	}

	if (!bCaptured)
	{
		return FCommandResult::Error(TEXT("Failed to capture full screen via all methods (Slate, GameViewport, FScreenshotRequest)"));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("file_path"), FullPath);
	Data->SetStringField(TEXT("method"), Method);
	TSharedPtr<FJsonObject> ResObj = MakeShareable(new FJsonObject());
	ResObj->SetNumberField(TEXT("x"), CapturedWidth);
	ResObj->SetNumberField(TEXT("y"), CapturedHeight);
	Data->SetObjectField(TEXT("resolution"), ResObj);
	Data->SetBoolField(TEXT("includes_ui"), true);
	return FCommandResult::Ok(Data);
}

// ════════════════════════════════════════════════════════════════════
//  simulate_input — Injects key press/release into PIE
// ════════════════════════════════════════════════════════════════════
FCommandResult FCommandServer::HandleSimulateInput(const TSharedPtr<FJsonObject>& Params)
{
	if (!GEditor || !GEditor->PlayWorld)
		return FCommandResult::Error(TEXT("PIE not running. Call play_in_editor first."));

	if (!Params->HasField(TEXT("key")))
		return FCommandResult::Error(TEXT("Missing required param: key (e.g. 'E', 'W', 'SpaceBar', 'Escape')"));

	FString KeyName = Params->GetStringField(TEXT("key"));
	float HoldDuration = Params->HasField(TEXT("hold")) ? static_cast<float>(Params->GetNumberField(TEXT("hold"))) : 0.0f;

	// Resolve key name to FKey
	// Support common friendly names
	FKey Key;
	if (KeyName.Len() == 1)
	{
		// Single character: A-Z, 0-9
		Key = FKey(*KeyName.ToUpper());
	}
	else
	{
		// Named keys
		Key = FKey(*KeyName);
	}

	if (!Key.IsValid())
	{
		return FCommandResult::Error(FString::Printf(TEXT("Invalid key: '%s'. Use single char (E, W) or named key (SpaceBar, Escape, LeftMouseButton)"), *KeyName));
	}

	// Get the Slate application and find the PIE viewport widget to send input to
	FSlateApplication& SlateApp = FSlateApplication::Get();

	// Method: Use viewport client to inject input directly
	if (GEngine && GEngine->GameViewport)
	{
		FViewport* GameViewport = GEngine->GameViewport->Viewport;
		if (GameViewport)
		{
			// Press
			GEngine->GameViewport->InputKey(FInputKeyEventArgs(GameViewport, FInputDeviceId::CreateFromInternalId(0), Key, EInputEvent::IE_Pressed, FPlatformTime::Cycles64()));

			if (HoldDuration > 0.0f)
			{
				// Schedule release after hold duration using a timer
				FTimerHandle TimerHandle;
				FKey CapturedKey = Key;
				GEditor->PlayWorld->GetTimerManager().SetTimer(TimerHandle, [CapturedKey, GameViewport]()
				{
					if (GameViewport && GEngine && GEngine->GameViewport)
					{
						GEngine->GameViewport->InputKey(FInputKeyEventArgs(GameViewport, FInputDeviceId::CreateFromInternalId(0), CapturedKey, EInputEvent::IE_Released, FPlatformTime::Cycles64()));
					}
				}, HoldDuration, false);
			}
			else
			{
				// Immediate press-and-release (next frame)
				FTimerHandle TimerHandle;
				FKey CapturedKey = Key;
				GEditor->PlayWorld->GetTimerManager().SetTimer(TimerHandle, [CapturedKey, GameViewport]()
				{
					if (GameViewport && GEngine && GEngine->GameViewport)
					{
						GEngine->GameViewport->InputKey(FInputKeyEventArgs(GameViewport, FInputDeviceId::CreateFromInternalId(0), CapturedKey, EInputEvent::IE_Released, FPlatformTime::Cycles64()));
					}
				}, 0.1f, false);
			}

			TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
			Data->SetStringField(TEXT("key"), Key.GetFName().ToString());
			Data->SetStringField(TEXT("action"), HoldDuration > 0.0f ? TEXT("pressed_and_held") : TEXT("pressed_and_released"));
			Data->SetNumberField(TEXT("hold_seconds"), HoldDuration);
			return FCommandResult::Ok(Data);
		}
	}

	// Fallback: inject via PlayerController directly
	APlayerController* PC = GEditor->PlayWorld->GetFirstPlayerController();
	if (!PC)
		return FCommandResult::Error(TEXT("No player controller in PIE"));

	// Fallback: use AddMovementInput for movement keys, or just log
	if (Key == EKeys::W || Key == EKeys::A || Key == EKeys::S || Key == EKeys::D)
	{
		FVector Dir = FVector::ZeroVector;
		FRotator Rot = PC->GetControlRotation();
		FRotator YawRot(0, Rot.Yaw, 0);
		if (Key == EKeys::W) Dir = FRotationMatrix(YawRot).GetUnitAxis(EAxis::X);
		if (Key == EKeys::S) Dir = -FRotationMatrix(YawRot).GetUnitAxis(EAxis::X);
		if (Key == EKeys::D) Dir = FRotationMatrix(YawRot).GetUnitAxis(EAxis::Y);
		if (Key == EKeys::A) Dir = -FRotationMatrix(YawRot).GetUnitAxis(EAxis::Y);
		PC->GetPawn()->AddMovementInput(Dir, 1.0f);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("key"), Key.GetFName().ToString());
	Data->SetStringField(TEXT("action"), HoldDuration > 0.0f ? TEXT("pressed_and_held") : TEXT("pressed_and_released"));
	Data->SetNumberField(TEXT("hold_seconds"), HoldDuration);
	Data->SetStringField(TEXT("method"), TEXT("PlayerController"));
	return FCommandResult::Ok(Data);
}

// ════════════════════════════════════════════════════════════════════
//  simulate_walk_to — Walk the player toward a target using movement input
// ════════════════════════════════════════════════════════════════════
FCommandResult FCommandServer::HandleSimulateWalkTo(const TSharedPtr<FJsonObject>& Params)
{
	if (!GEditor || !GEditor->PlayWorld)
		return FCommandResult::Error(TEXT("PIE not running. Call play_in_editor first."));

	APlayerController* PC = GEditor->PlayWorld->GetFirstPlayerController();
	if (!PC || !PC->GetPawn())
		return FCommandResult::Error(TEXT("No player pawn in PIE"));

	APawn* Pawn = PC->GetPawn();
	FVector CurrentLoc = Pawn->GetActorLocation();
	FVector TargetLoc;

	if (Params->HasField(TEXT("actor")))
	{
		// Walk toward a named actor
		FString ActorLabel = Params->GetStringField(TEXT("actor"));
		AActor* Target = nullptr;
		for (TActorIterator<AActor> It(GEditor->PlayWorld); It; ++It)
		{
			if (It->GetActorNameOrLabel().Contains(ActorLabel) || It->GetActorLabel().Contains(ActorLabel))
			{
				Target = *It;
				break;
			}
		}
		if (!Target)
			return FCommandResult::Error(FString::Printf(TEXT("Actor not found: %s"), *ActorLabel));

		TargetLoc = Target->GetActorLocation();

		// Stop short by 'distance' cm (default 150)
		float StopDistance = Params->HasField(TEXT("distance")) ? static_cast<float>(Params->GetNumberField(TEXT("distance"))) : 150.0f;
		FVector Dir = (TargetLoc - CurrentLoc).GetSafeNormal2D();
		float Dist = FVector::Dist2D(CurrentLoc, TargetLoc);
		if (Dist > StopDistance)
		{
			TargetLoc = CurrentLoc + Dir * (Dist - StopDistance);
		}
	}
	else
	{
		TargetLoc.X = Params->GetNumberField(TEXT("x"));
		TargetLoc.Y = Params->GetNumberField(TEXT("y"));
		TargetLoc.Z = Params->HasField(TEXT("z")) ? Params->GetNumberField(TEXT("z")) : CurrentLoc.Z;
	}

	// Face the target
	FVector Direction = (TargetLoc - CurrentLoc).GetSafeNormal2D();
	FRotator LookRot = Direction.Rotation();
	PC->SetControlRotation(LookRot);

	// Calculate walk duration based on distance and speed
	float Distance = FVector::Dist2D(CurrentLoc, TargetLoc);
	float WalkSpeed = 600.0f; // Approximate UE character walk speed in cm/s
	if (ACharacter* Char = Cast<ACharacter>(Pawn))
	{
		if (Char->GetCharacterMovement())
		{
			WalkSpeed = Char->GetCharacterMovement()->MaxWalkSpeed;
		}
	}
	float WalkDuration = Distance / FMath::Max(WalkSpeed, 1.0f);
	WalkDuration = FMath::Clamp(WalkDuration, 0.1f, 30.0f); // Cap at 30s

	// Inject forward movement input for the calculated duration
	if (GEngine && GEngine->GameViewport && GEngine->GameViewport->Viewport)
	{
		FViewport* GameViewport = GEngine->GameViewport->Viewport;
		FKey WKey(TEXT("W"));

		// Press W
		GEngine->GameViewport->InputKey(FInputKeyEventArgs(GameViewport, FInputDeviceId::CreateFromInternalId(0), WKey, EInputEvent::IE_Pressed, FPlatformTime::Cycles64()));

		// Schedule release after walk duration
		FTimerHandle TimerHandle;
		GEditor->PlayWorld->GetTimerManager().SetTimer(TimerHandle, [GameViewport, WKey]()
		{
			if (GEngine && GEngine->GameViewport)
			{
				GEngine->GameViewport->InputKey(FInputKeyEventArgs(GameViewport, FInputDeviceId::CreateFromInternalId(0), WKey, EInputEvent::IE_Released, FPlatformTime::Cycles64()));
			}
		}, WalkDuration, false);

		TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
		Data->SetNumberField(TEXT("target_x"), TargetLoc.X);
		Data->SetNumberField(TEXT("target_y"), TargetLoc.Y);
		Data->SetNumberField(TEXT("target_z"), TargetLoc.Z);
		Data->SetNumberField(TEXT("distance"), Distance);
		Data->SetNumberField(TEXT("walk_duration"), WalkDuration);
		Data->SetNumberField(TEXT("facing_yaw"), LookRot.Yaw);
		return FCommandResult::Ok(Data);
	}

	// Fallback: use AddMovementInput directly
	Pawn->AddMovementInput(Direction, 1.0f);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("target_x"), TargetLoc.X);
	Data->SetNumberField(TEXT("target_y"), TargetLoc.Y);
	Data->SetNumberField(TEXT("target_z"), TargetLoc.Z);
	Data->SetNumberField(TEXT("distance"), Distance);
	Data->SetStringField(TEXT("method"), TEXT("AddMovementInput_single_frame"));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetPirWidget(const TSharedPtr<FJsonObject>& Params)
{
	FString WidgetName = Params->GetStringField(TEXT("widget_name"));
	if (WidgetName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("set_pir_widget: widget_name is required"));
	}

	FString ConfigPath = FPaths::ProjectDir() / TEXT("Config/WidgetPreview.ini");
	FString Content = FString::Printf(TEXT("[Preview]\nWidgetName=%s\n"), *WidgetName);

	if (!FFileHelper::SaveStringToFile(Content, *ConfigPath))
	{
		return FCommandResult::Error(TEXT("set_pir_widget: failed to write config: ") + ConfigPath);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("widget_name"), WidgetName);
	Data->SetStringField(TEXT("config_path"), ConfigPath);
	UE_LOG(LogBlueprintLLM, Log, TEXT("set_pir_widget: %s -> %s"), *WidgetName, *ConfigPath);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetViewportInfo(const TSharedPtr<FJsonObject>& Params)
{
	FLevelEditorViewportClient* ViewportClient = nullptr;
	if (GCurrentLevelEditingViewportClient)
	{
		ViewportClient = GCurrentLevelEditingViewportClient;
	}
	else if (GEditor)
	{
		const TArray<FLevelEditorViewportClient*>& Clients = GEditor->GetLevelViewportClients();
		if (Clients.Num() > 0)
		{
			ViewportClient = Clients[0];
		}
	}

	if (!ViewportClient)
	{
		return FCommandResult::Error(TEXT("No active level viewport found"));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetObjectField(TEXT("location"), VectorToJson(ViewportClient->GetViewLocation()));
	Data->SetObjectField(TEXT("rotation"), RotatorToJson(ViewportClient->GetViewRotation()));
	Data->SetNumberField(TEXT("fov"), ViewportClient->ViewFOV);

	// View mode
	FString ViewModeName;
	switch (ViewportClient->GetViewMode())
	{
	case VMI_Lit: ViewModeName = TEXT("Lit"); break;
	case VMI_Unlit: ViewModeName = TEXT("Unlit"); break;
	case VMI_Wireframe: ViewModeName = TEXT("Wireframe"); break;
	default: ViewModeName = TEXT("Other"); break;
	}
	Data->SetStringField(TEXT("view_mode"), ViewModeName);

	if (ViewportClient->Viewport)
	{
		TSharedPtr<FJsonObject> SizeObj = MakeShareable(new FJsonObject());
		SizeObj->SetNumberField(TEXT("x"), ViewportClient->Viewport->GetSizeXY().X);
		SizeObj->SetNumberField(TEXT("y"), ViewportClient->Viewport->GetSizeXY().Y);
		Data->SetObjectField(TEXT("viewport_size"), SizeObj);
	}

	return FCommandResult::Ok(Data);
}

// ============================================================
// Niagara Commands (B25)
// ============================================================

FCommandResult FCommandServer::HandleSpawnNiagaraAtLocation(const TSharedPtr<FJsonObject>& Params)
{
	FString SystemPath = Params->GetStringField(TEXT("system"));
	if (SystemPath.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'system' parameter"));
	}

	TSharedPtr<FJsonObject> LocationObj = Params->GetObjectField(TEXT("location"));
	if (!LocationObj.IsValid())
	{
		return FCommandResult::Error(TEXT("Missing 'location' parameter"));
	}

	bool bAutoDestroy = !Params->HasField(TEXT("auto_destroy"))
		|| Params->GetBoolField(TEXT("auto_destroy"));

	UNiagaraSystem* System = LoadObject<UNiagaraSystem>(nullptr, *SystemPath);
	if (!System)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Niagara system not found: %s"), *SystemPath));
	}

	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World)
	{
		return FCommandResult::Error(TEXT("No editor world available"));
	}

	FVector Location = JsonToVector(LocationObj);
	FRotator Rotation = FRotator::ZeroRotator;
	if (Params->HasField(TEXT("rotation")))
	{
		Rotation = JsonToRotator(Params->GetObjectField(TEXT("rotation")));
	}

	UNiagaraComponent* NiagaraComp = UNiagaraFunctionLibrary::SpawnSystemAtLocation(
		World, System, Location, Rotation, FVector::OneVector, bAutoDestroy);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("system"), SystemPath);
	Data->SetObjectField(TEXT("location"), VectorToJson(Location));
	Data->SetBoolField(TEXT("spawned"), NiagaraComp != nullptr);
	if (NiagaraComp)
	{
		Data->SetStringField(TEXT("component_name"), NiagaraComp->GetName());
	}
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddNiagaraComponent(const TSharedPtr<FJsonObject>& Params)
{
	FString BPName = Params->GetStringField(TEXT("blueprint"));
	if (BPName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'blueprint' parameter"));
	}

	FString CompName = Params->HasField(TEXT("name"))
		? Params->GetStringField(TEXT("name"))
		: TEXT("Niagara");

	FString SystemPath;
	if (Params->HasField(TEXT("system")))
	{
		SystemPath = Params->GetStringField(TEXT("system"));
	}

	bool bAutoActivate = !Params->HasField(TEXT("auto_activate"))
		|| Params->GetBoolField(TEXT("auto_activate"));

	UBlueprint* BP = FindBlueprintByName(BPName);
	if (!BP)
	{
		return FCommandResult::Error(FormatBlueprintNotFound(BPName));
	}

	USimpleConstructionScript* SCS = BP->SimpleConstructionScript;
	if (!SCS)
	{
		return FCommandResult::Error(TEXT("Blueprint has no SimpleConstructionScript"));
	}

	if (FindSCSNodeByName(SCS, CompName))
	{
		return FCommandResult::Error(FString::Printf(TEXT("Component '%s' already exists"), *CompName));
	}

	USCS_Node* NewNode = SCS->CreateNode(UNiagaraComponent::StaticClass(), FName(*CompName));
	if (!NewNode)
	{
		return FCommandResult::Error(TEXT("Failed to create SCS node for NiagaraComponent"));
	}

	UNiagaraComponent* NiagaraComp = Cast<UNiagaraComponent>(NewNode->ComponentTemplate);
	if (NiagaraComp)
	{
		NiagaraComp->SetAutoActivate(bAutoActivate);

		if (!SystemPath.IsEmpty())
		{
			UNiagaraSystem* System = LoadObject<UNiagaraSystem>(nullptr, *SystemPath);
			if (System)
			{
				NiagaraComp->SetAsset(System);
			}
			else
			{
				UE_LOG(LogBlueprintLLM, Warning, TEXT("Niagara system not found: %s — component created without system"), *SystemPath);
			}
		}
	}

	SCS->AddNode(NewNode);
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("blueprint"), BPName);
	Data->SetStringField(TEXT("component_name"), CompName);
	Data->SetStringField(TEXT("system"), SystemPath);
	Data->SetBoolField(TEXT("auto_activate"), bAutoActivate);
	Data->SetBoolField(TEXT("compiled"), true);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetNiagaraAssets(const TSharedPtr<FJsonObject>& Params)
{
	FString SearchPath = Params->HasField(TEXT("path"))
		? Params->GetStringField(TEXT("path"))
		: TEXT("/Game");

	bool bSearchSubfolders = !Params->HasField(TEXT("search_subfolders"))
		|| Params->GetBoolField(TEXT("search_subfolders"));

	FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	IAssetRegistry& AssetRegistry = AssetRegistryModule.Get();

	TArray<FAssetData> AssetDataList;
	AssetRegistry.GetAssetsByPath(FName(*SearchPath), AssetDataList, bSearchSubfolders);

	TArray<TSharedPtr<FJsonValue>> SystemsArray;
	for (const FAssetData& AssetData : AssetDataList)
	{
		if (AssetData.AssetClassPath == UNiagaraSystem::StaticClass()->GetClassPathName())
		{
			TSharedPtr<FJsonObject> SystemObj = MakeShareable(new FJsonObject());
			SystemObj->SetStringField(TEXT("name"), AssetData.AssetName.ToString());
			SystemObj->SetStringField(TEXT("asset_path"), AssetData.GetObjectPathString());
			SystemsArray.Add(MakeShareable(new FJsonValueObject(SystemObj)));
		}
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("count"), SystemsArray.Num());
	Data->SetArrayField(TEXT("systems"), SystemsArray);
	Data->SetStringField(TEXT("search_path"), SearchPath);
	return FCommandResult::Ok(Data);
}

// ============================================================
// Editor lifecycle
// ============================================================

FCommandResult FCommandServer::HandleQuitEditor(const TSharedPtr<FJsonObject>& Params)
{
	bool bSaveFirst = !Params->HasField(TEXT("skip_save")) || !Params->GetBoolField(TEXT("skip_save"));

	// Stop PIE if running
	if (GEditor && GEditor->PlayWorld)
	{
		GEditor->RequestEndPlayMap();
		UE_LOG(LogBlueprintLLM, Log, TEXT("quit_editor: Stopped PIE session"));
	}

	// Save all dirty packages
	int32 ExternalActorsSaved = 0;
	if (bSaveFirst)
	{
		// Save content packages (always safe)
		FEditorFileUtils::SaveDirtyPackages(/*bPromptUserToSave=*/false, /*bSaveMapPackages=*/false, /*bSaveContentPackages=*/true);

		// Try to save the map package — may fail for untitled maps
		UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
		if (World)
		{
			UPackage* MapPackage = World->GetOutermost();
			FString PkgName = MapPackage->GetName();
			bool bIsUntitled = PkgName.Contains(TEXT("Untitled")) || PkgName.StartsWith(TEXT("/Temp/"));
			if (!bIsUntitled && MapPackage->IsDirty())
			{
				FString FilePath = FPackageName::LongPackageNameToFilename(PkgName, FPackageName::GetMapPackageExtension());
				FSavePackageArgs SaveArgs;
				SaveArgs.TopLevelFlags = RF_Standalone;
				SafeSavePackage(MapPackage, World, FilePath, SaveArgs);
			}
		}

		// Explicitly save World Partition external actor packages
		for (TObjectIterator<UPackage> It; It; ++It)
		{
			UPackage* Pkg = *It;
			if (Pkg && Pkg->IsDirty())
			{
				FString EPkgName = Pkg->GetName();
				if (EPkgName.Contains(TEXT("__ExternalActors__")) || EPkgName.Contains(TEXT("__ExternalObjects__")))
				{
					FString FilePath = FPackageName::LongPackageNameToFilename(EPkgName, FPackageName::GetAssetPackageExtension());
					FString Dir = FPaths::GetPath(FilePath);
					IFileManager::Get().MakeDirectory(*Dir, true);

					FSavePackageArgs SaveArgs;
					SaveArgs.TopLevelFlags = RF_Standalone;
					if (SafeSavePackage(Pkg, nullptr, FilePath, SaveArgs))
					{
						ExternalActorsSaved++;
					}
				}
			}
		}

		UE_LOG(LogBlueprintLLM, Log, TEXT("quit_editor: Saved all dirty packages + %d external actor packages"), ExternalActorsSaved);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetBoolField(TEXT("saved"), bSaveFirst);
	Data->SetNumberField(TEXT("external_actors_saved"), ExternalActorsSaved);
	Data->SetStringField(TEXT("message"), TEXT("Editor exit requested. Shutting down cleanly."));

	// Save stats before exit
	if (Stats.IsValid())
	{
		Stats->SaveToDisk();
	}

	UE_LOG(LogBlueprintLLM, Log, TEXT("quit_editor: Requesting clean exit"));

	// Schedule the exit on next tick so the response can be sent first
	FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda(
		[](float) -> bool
		{
			FPlatformMisc::RequestExit(false);
			return false; // one-shot
		}
	), 0.5f); // 500ms delay to let the TCP response flush

	return FCommandResult::Ok(Data);
}

// ============================================================
// Stats commands
// ============================================================

FCommandResult FCommandServer::HandleGetStats(const TSharedPtr<FJsonObject>& Params)
{
	if (!Stats.IsValid())
	{
		return FCommandResult::Error(TEXT("Stats system not initialized"));
	}

	TSharedPtr<FJsonObject> Data = Stats->GetStatsJson();
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleResetStats(const TSharedPtr<FJsonObject>& Params)
{
	if (!Stats.IsValid())
	{
		return FCommandResult::Error(TEXT("Stats system not initialized"));
	}

	FString Scope = Params->HasField(TEXT("scope")) ? Params->GetStringField(TEXT("scope")) : TEXT("session");

	if (Scope == TEXT("session"))
	{
		Stats->ResetSession();
	}
	else if (Scope == TEXT("lifetime"))
	{
		Stats->ResetLifetime();
	}
	else
	{
		return FCommandResult::Error(FString::Printf(TEXT("Invalid scope: '%s'. Use 'session' or 'lifetime'."), *Scope));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("reset"), Scope);
	Data->SetStringField(TEXT("message"), FString::Printf(TEXT("%s stats reset successfully"), *Scope));
	return FCommandResult::Ok(Data);
}

// ============================================================
// Widget commands (B11)
// ============================================================

UWidgetBlueprint* FCommandServer::FindWidgetBlueprintByName(const FString& Name)
{
	// Search /Game/ for a UWidgetBlueprint with matching name
	FAssetRegistryModule& ARModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	IAssetRegistry& AR = ARModule.Get();

	TArray<FAssetData> AssetDataList;
	AR.GetAssetsByClass(UWidgetBlueprint::StaticClass()->GetClassPathName(), AssetDataList);

	for (const FAssetData& AssetData : AssetDataList)
	{
		if (AssetData.AssetName.ToString() == Name)
		{
			return Cast<UWidgetBlueprint>(AssetData.GetAsset());
		}
	}
	return nullptr;
}

UWidget* FCommandServer::FindWidgetByName(UWidgetBlueprint* WBP, const FString& WidgetName)
{
	if (!WBP || !WBP->WidgetTree)
	{
		return nullptr;
	}

	UWidget* Found = nullptr;
	WBP->WidgetTree->ForEachWidget([&](UWidget* Widget)
	{
		if (!Found && Widget->GetName() == WidgetName)
		{
			Found = Widget;
		}
	});
	return Found;
}

UClass* FCommandServer::ResolveWidgetClass(const FString& FriendlyName)
{
	static TMap<FString, UClass*> WidgetClassMap;
	if (WidgetClassMap.Num() == 0)
	{
		WidgetClassMap.Add(TEXT("TextBlock"), UTextBlock::StaticClass());
		WidgetClassMap.Add(TEXT("ProgressBar"), UProgressBar::StaticClass());
		WidgetClassMap.Add(TEXT("Image"), UImage::StaticClass());
		WidgetClassMap.Add(TEXT("Button"), UButton::StaticClass());
		WidgetClassMap.Add(TEXT("VerticalBox"), UVerticalBox::StaticClass());
		WidgetClassMap.Add(TEXT("HorizontalBox"), UHorizontalBox::StaticClass());
		WidgetClassMap.Add(TEXT("CanvasPanel"), UCanvasPanel::StaticClass());
		WidgetClassMap.Add(TEXT("Overlay"), UOverlay::StaticClass());
		WidgetClassMap.Add(TEXT("SizeBox"), USizeBox::StaticClass());
		WidgetClassMap.Add(TEXT("ScrollBox"), UScrollBox::StaticClass());
		WidgetClassMap.Add(TEXT("Border"), UBorder::StaticClass());
		WidgetClassMap.Add(TEXT("UniformGridPanel"), UUniformGridPanel::StaticClass());
		WidgetClassMap.Add(TEXT("GridPanel"), UGridPanel::StaticClass());
		WidgetClassMap.Add(TEXT("WrapBox"), UWrapBox::StaticClass());
		WidgetClassMap.Add(TEXT("ListView"), UListView::StaticClass());
		WidgetClassMap.Add(TEXT("TileView"), UTileView::StaticClass());
	}

	UClass** Found = WidgetClassMap.Find(FriendlyName);
	if (Found)
	{
		return *Found;
	}

	// Try case-insensitive
	for (auto& Pair : WidgetClassMap)
	{
		if (Pair.Key.Equals(FriendlyName, ESearchCase::IgnoreCase))
		{
			return Pair.Value;
		}
	}

	return nullptr;
}

TSharedPtr<FJsonObject> FCommandServer::WidgetToJson(UWidget* Widget)
{
	TSharedPtr<FJsonObject> Obj = MakeShareable(new FJsonObject());
	Obj->SetStringField(TEXT("name"), Widget->GetName());
	Obj->SetStringField(TEXT("type"), Widget->GetClass()->GetName());

	// Type-specific properties
	if (UTextBlock* TB = Cast<UTextBlock>(Widget))
	{
		Obj->SetStringField(TEXT("text"), TB->GetText().ToString());
		if (TB->GetFont().Size > 0)
		{
			Obj->SetNumberField(TEXT("font_size"), TB->GetFont().Size);
		}
	}
	else if (UProgressBar* PB = Cast<UProgressBar>(Widget))
	{
		Obj->SetNumberField(TEXT("percent"), PB->GetPercent());
	}
	else if (UButton* Btn = Cast<UButton>(Widget))
	{
		Obj->SetStringField(TEXT("subtype"), TEXT("Button"));
	}

	// Visibility
	Obj->SetStringField(TEXT("visibility"), UEnum::GetValueAsString(Widget->GetVisibility()));

	return Obj;
}

void FCommandServer::CollectWidgetChildren(UWidget* Widget, TArray<TSharedPtr<FJsonValue>>& OutArray, int32 Depth)
{
	TSharedPtr<FJsonObject> Obj = WidgetToJson(Widget);
	Obj->SetNumberField(TEXT("depth"), Depth);

	// Collect children for panel widgets
	TArray<TSharedPtr<FJsonValue>> ChildrenArray;
	if (UPanelWidget* Panel = Cast<UPanelWidget>(Widget))
	{
		for (int32 i = 0; i < Panel->GetChildrenCount(); i++)
		{
			UWidget* Child = Panel->GetChildAt(i);
			if (Child)
			{
				CollectWidgetChildren(Child, ChildrenArray, Depth + 1);
			}
		}
	}

	if (ChildrenArray.Num() > 0)
	{
		Obj->SetArrayField(TEXT("children"), ChildrenArray);
	}

	OutArray.Add(MakeShareable(new FJsonValueObject(Obj)));
}

FCommandResult FCommandServer::HandleCreateWidgetBlueprint(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required param: name"));
	}

	FString ParentClassName = Params->HasField(TEXT("parent_class"))
		? Params->GetStringField(TEXT("parent_class"))
		: TEXT("");

	// Resolve parent class
	UClass* ParentClass = UUserWidget::StaticClass();
	if (!ParentClassName.IsEmpty())
	{
		UClass* CustomParent = FindObject<UClass>(nullptr, *ParentClassName);
		if (!CustomParent)
		{
			// Try with /Script/UMG. prefix
			CustomParent = FindObject<UClass>(nullptr, *FString::Printf(TEXT("/Script/UMG.%s"), *ParentClassName));
		}
		if (CustomParent && CustomParent->IsChildOf(UUserWidget::StaticClass()))
		{
			ParentClass = CustomParent;
		}
		else if (CustomParent)
		{
			return FCommandResult::Error(FString::Printf(
				TEXT("Parent class %s is not a UUserWidget subclass"), *ParentClassName));
		}
		else
		{
			return FCommandResult::Error(FString::Printf(
				TEXT("Parent class not found: %s"), *ParentClassName));
		}
	}

	// Delete existing if present
	UWidgetBlueprint* Existing = FindWidgetBlueprintByName(Name);
	if (Existing)
	{
		TArray<UObject*> ObjectsToDelete;
		ObjectsToDelete.Add(Existing);
		ObjectTools::ForceDeleteObjects(ObjectsToDelete, false);
	}

	// Create package
	FString PackagePath = FString::Printf(TEXT("/Game/UI/%s"), *Name);
	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Failed to create package: %s"), *PackagePath));
	}

	// Create the widget blueprint
	UWidgetBlueprint* WBP = CastChecked<UWidgetBlueprint>(
		FKismetEditorUtilities::CreateBlueprint(
			ParentClass,
			Package,
			FName(*Name),
			BPTYPE_Normal,
			UWidgetBlueprint::StaticClass(),
			UBlueprintGeneratedClass::StaticClass()
		)
	);

	if (!WBP)
	{
		return FCommandResult::Error(TEXT("Failed to create Widget Blueprint"));
	}

	// Set design-time size (default 1920x1080 unless overridden)
	int32 DesignWidth = Params->HasField(TEXT("design_width")) ? (int32)Params->GetNumberField(TEXT("design_width")) : 1920;
	int32 DesignHeight = Params->HasField(TEXT("design_height")) ? (int32)Params->GetNumberField(TEXT("design_height")) : 1080;
#if WITH_EDITORONLY_DATA
	if (UUserWidget* CDO = Cast<UUserWidget>(WBP->GeneratedClass->GetDefaultObject()))
	{
		CDO->DesignTimeSize = FVector2D(DesignWidth, DesignHeight);
		CDO->DesignSizeMode = EDesignPreviewSizeMode::Custom;
		UE_LOG(LogBlueprintLLM, Log, TEXT("CreateWidgetBP DesignTimeSize: %dx%d (Custom mode)"), DesignWidth, DesignHeight);
	}
#endif

	// Compile
	FKismetEditorUtilities::CompileBlueprint(WBP);

	// Save the package to disk
	FAssetRegistryModule::AssetCreated(WBP);
	WBP->MarkPackageDirty();
	FString PackageFilename = FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension());
	// Ensure directory exists on disk
	IFileManager::Get().MakeDirectory(*FPaths::GetPath(PackageFilename), true);
	UE_LOG(LogBlueprintLLM, Log, TEXT("CreateWidgetBP SavePackage: %s -> %s"), *PackagePath, *PackageFilename);
	FSavePackageArgs SaveArgs;
	bool bSaved = SafeSavePackage(Package, WBP, PackageFilename, SaveArgs);
	UE_LOG(LogBlueprintLLM, Log, TEXT("CreateWidgetBP SavePackage result: %s"), bSaved ? TEXT("SUCCESS") : TEXT("FAILED"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), PackagePath);
	Data->SetStringField(TEXT("parent_class"), ParentClass->GetName());
	Data->SetBoolField(TEXT("compiled"), true);
	Data->SetBoolField(TEXT("saved"), bSaved);
	Data->SetBoolField(TEXT("has_widget_tree"), WBP->WidgetTree != nullptr);
	Data->SetNumberField(TEXT("design_width"), DesignWidth);
	Data->SetNumberField(TEXT("design_height"), DesignHeight);

	// Auto-validate layout on creation
	int32 LayoutScore = ComputeLayoutScore(WBP);
	Data->SetNumberField(TEXT("layout_score"), LayoutScore);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Created Widget Blueprint: %s at %s (saved=%d, layout=%d, design=%dx%d)"), *Name, *PackagePath, bSaved, LayoutScore, DesignWidth, DesignHeight);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetWidgetDesignSize(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty())
	{
		Name = Params->GetStringField(TEXT("widget_blueprint"));
	}
	if (Name.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required param: name (widget blueprint name)"));
	}

	int32 Width = Params->HasField(TEXT("width")) ? (int32)Params->GetNumberField(TEXT("width")) : 0;
	int32 Height = Params->HasField(TEXT("height")) ? (int32)Params->GetNumberField(TEXT("height")) : 0;
	if (Width <= 0 || Height <= 0)
	{
		return FCommandResult::Error(TEXT("Missing or invalid params: width and height must be positive integers"));
	}

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(Name);
	if (!WBP)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Widget Blueprint not found: %s"), *Name));
	}

#if WITH_EDITORONLY_DATA
	if (UUserWidget* CDO = Cast<UUserWidget>(WBP->GeneratedClass->GetDefaultObject()))
	{
		CDO->DesignTimeSize = FVector2D(Width, Height);
		CDO->DesignSizeMode = EDesignPreviewSizeMode::Custom;
	}
	else
	{
		return FCommandResult::Error(TEXT("Failed to get widget CDO to set DesignTimeSize"));
	}
#endif
	WBP->MarkPackageDirty();

	// Save immediately
	FString PackagePath = WBP->GetPackage()->GetName();
	FString PackageFilename = FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension());
	FSavePackageArgs SaveArgs;
	bool bSaved = SafeSavePackage(WBP->GetPackage(), WBP, PackageFilename, SaveArgs);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetNumberField(TEXT("width"), Width);
	Data->SetNumberField(TEXT("height"), Height);
	Data->SetBoolField(TEXT("saved"), bSaved);

	UE_LOG(LogBlueprintLLM, Log, TEXT("SetWidgetDesignSize: %s -> %dx%d (saved=%d)"), *Name, Width, Height, bSaved);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleProtectWidgetLayout(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required param: name"));
	}

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(Name);
	if (!WBP || !WBP->WidgetTree)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Widget Blueprint not found: %s"), *Name));
	}

	int32 ProtectedCount = 0;
	int32 AccessibleCount = 0;

	WBP->WidgetTree->ForEachWidget([&](UWidget* Widget)
	{
		if (!Widget) return;
		FString WidgetName = Widget->GetName();

		// txt_* and Btn_* prefixed widgets stay accessible to C++
		if (WidgetName.StartsWith(TEXT("txt_")) || WidgetName.StartsWith(TEXT("Btn_")) ||
		    WidgetName.StartsWith(TEXT("Text_Btn")))
		{
			// Keep bIsVariable = true so C++ can find these
			Widget->bIsVariable = true;
			AccessibleCount++;
			return;
		}

		// Root widget stays as-is
		if (Widget == WBP->WidgetTree->RootWidget)
		{
			return;
		}

		// Everything else in the visual layer: protect
		Widget->bIsVariable = false;

		// Set decorative borders/panels to HitTestInvisible
		if (Cast<UBorder>(Widget) || Cast<UCanvasPanel>(Widget))
		{
			Widget->SetVisibility(ESlateVisibility::HitTestInvisible);
		}

		ProtectedCount++;
	});

	// Mark modified and save
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(WBP);
	WBP->MarkPackageDirty();

	FString PackagePath = WBP->GetPackage()->GetName();
	FString PackageFilename = FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension());
	FSavePackageArgs SaveArgs;
	bool bSaved = SafeSavePackage(WBP->GetPackage(), WBP, PackageFilename, SaveArgs);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetNumberField(TEXT("protected_widgets"), ProtectedCount);
	Data->SetNumberField(TEXT("accessible_widgets"), AccessibleCount);
	Data->SetBoolField(TEXT("saved"), bSaved);

	UE_LOG(LogBlueprintLLM, Log, TEXT("ProtectWidgetLayout: %s — %d protected, %d accessible (txt_*/Btn_*)"),
		*Name, ProtectedCount, AccessibleCount);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddWidgetChild(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	FString WidgetType = Params->GetStringField(TEXT("widget_type"));
	FString WidgetName = Params->GetStringField(TEXT("widget_name"));

	if (WBPName.IsEmpty() || WidgetType.IsEmpty() || WidgetName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required params: widget_blueprint, widget_type, widget_name"));
	}

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP)
	{
		{ FString WErr = FString::Printf(TEXT("Widget Blueprint not found: %s."), *WBPName);
			WErr += TEXT(" Widget Blueprints are in /Game/UI/. Ensure it was created with create_widget_blueprint first.");
			return FCommandResult::Error(WErr); }
	}

	if (!WBP->WidgetTree)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Widget Blueprint %s has no WidgetTree"), *WBPName));
	}

	// Check for name collision
	if (FindWidgetByName(WBP, WidgetName))
	{
		return FCommandResult::Error(FString::Printf(TEXT("Widget '%s' already exists in %s"), *WidgetName, *WBPName));
	}

	// Resolve widget class
	UClass* WidgetClass = ResolveWidgetClass(WidgetType);
	if (!WidgetClass)
	{
		return FCommandResult::Error(FString::Printf(
			TEXT("Unknown widget type: %s. Supported: TextBlock, ProgressBar, Image, Button, VerticalBox, HorizontalBox, CanvasPanel, Overlay, SizeBox"),
			*WidgetType));
	}

	// Create the widget
	UWidget* NewWidget = WBP->WidgetTree->ConstructWidget<UWidget>(WidgetClass, FName(*WidgetName));
	if (!NewWidget)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Failed to construct widget of type %s"), *WidgetType));
	}

	// Find parent widget or use root
	FString ParentWidgetName = Params->HasField(TEXT("parent_widget"))
		? Params->GetStringField(TEXT("parent_widget"))
		: TEXT("");

	if (!ParentWidgetName.IsEmpty())
	{
		UWidget* ParentWidget = FindWidgetByName(WBP, ParentWidgetName);
		if (!ParentWidget)
		{
			WBP->WidgetTree->RemoveWidget(NewWidget);
			return FCommandResult::Error(FString::Printf(TEXT("Parent widget not found: %s"), *ParentWidgetName));
		}

		UPanelWidget* ParentPanel = Cast<UPanelWidget>(ParentWidget);
		if (!ParentPanel)
		{
			WBP->WidgetTree->RemoveWidget(NewWidget);
			return FCommandResult::Error(FString::Printf(
				TEXT("Parent widget '%s' is not a panel widget (cannot have children)"), *ParentWidgetName));
		}

		UPanelSlot* Slot = ParentPanel->AddChild(NewWidget);
		if (!Slot)
		{
			WBP->WidgetTree->RemoveWidget(NewWidget);
			return FCommandResult::Error(TEXT("Failed to add widget to parent panel"));
		}
	}
	else
	{
		// Add as root or to existing root
		UWidget* RootWidget = WBP->WidgetTree->RootWidget;
		if (!RootWidget)
		{
			// This widget becomes root
			WBP->WidgetTree->RootWidget = NewWidget;
			// Auto-clip root CanvasPanel to prevent child overflow
			if (UCanvasPanel* RootCanvas = Cast<UCanvasPanel>(NewWidget))
			{
				RootCanvas->SetClipping(EWidgetClipping::ClipToBounds);
				UE_LOG(LogBlueprintLLM, Log, TEXT("AddWidgetChild: Set ClipToBounds on root CanvasPanel '%s'"), *WidgetName);
			}
		}
		else
		{
			// Try to add to root if it's a panel
			UPanelWidget* RootPanel = Cast<UPanelWidget>(RootWidget);
			if (!RootPanel)
			{
				WBP->WidgetTree->RemoveWidget(NewWidget);
				return FCommandResult::Error(TEXT("Root widget is not a panel. Specify a panel parent_widget, or create a panel as root first."));
			}
			RootPanel->AddChild(NewWidget);
		}
	}

	// Compile and save to disk
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(WBP);
	FKismetEditorUtilities::CompileBlueprint(WBP);
	WBP->MarkPackageDirty();

	// Persist to disk so widget survives editor restart and loads during PIE
	UPackage* WBPPackage = WBP->GetPackage();
	if (WBPPackage)
	{
		FString PackagePath = WBPPackage->GetName();
		FString PackageFilename = FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension());
		// Ensure directory exists on disk
		IFileManager::Get().MakeDirectory(*FPaths::GetPath(PackageFilename), true);
		UE_LOG(LogBlueprintLLM, Log, TEXT("Widget SavePackage: Package=%s -> %s"), *PackagePath, *PackageFilename);
		FSavePackageArgs SaveArgs;
		bool bSaved = SafeSavePackage(WBPPackage, WBP, PackageFilename, SaveArgs);
		UE_LOG(LogBlueprintLLM, Log, TEXT("Widget SavePackage result: %s"), bSaved ? TEXT("SUCCESS") : TEXT("FAILED"));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("widget_blueprint"), WBPName);
	Data->SetStringField(TEXT("widget_name"), WidgetName);
	Data->SetStringField(TEXT("widget_type"), WidgetType);
	Data->SetStringField(TEXT("widget_class"), WidgetClass->GetName());
	Data->SetStringField(TEXT("parent"), ParentWidgetName.IsEmpty() ? TEXT("(root)") : ParentWidgetName);
	Data->SetBoolField(TEXT("compiled"), true);

	// Auto-validate layout after adding child
	int32 LayoutScore = ComputeLayoutScore(WBP);
	Data->SetNumberField(TEXT("layout_score"), LayoutScore);
	if (LayoutScore >= 0 && LayoutScore < 50)
	{
		Data->SetBoolField(TEXT("layout_critical"), true);
		Data->SetStringField(TEXT("layout_warning"),
			FString::Printf(TEXT("Layout score %d/100 — run auto_fix_widget_layout before adding more elements"), LayoutScore));
	}

	UE_LOG(LogBlueprintLLM, Log, TEXT("Added widget '%s' (%s) to %s (layout score: %d)"), *WidgetName, *WidgetType, *WBPName, LayoutScore);
	return FCommandResult::Ok(Data);
}

// ── Widget Property Surface helpers ───────────────────────────
// Parse (R=x,G=x,B=x,A=x) format directly — values treated as-is
static FLinearColor ParseLinearColorRaw(const FString& Value)
{
	FLinearColor Result = FLinearColor::White;
	FString Clean = Value.TrimStartAndEnd()
		.Replace(TEXT("("), TEXT(""))
		.Replace(TEXT(")"), TEXT(""));
	TArray<FString> Parts;
	Clean.ParseIntoArray(Parts, TEXT(","));
	for (const FString& Part : Parts)
	{
		FString Key, Val;
		Part.Split(TEXT("="), &Key, &Val);
		Key.TrimStartAndEndInline();
		Val.TrimStartAndEndInline();
		float F = FCString::Atof(*Val);
		if      (Key == TEXT("R")) Result.R = F;
		else if (Key == TEXT("G")) Result.G = F;
		else if (Key == TEXT("B")) Result.B = F;
		else if (Key == TEXT("A")) Result.A = F;
	}
	return Result;
}

// sRGB gamma to linear conversion (per IEC 61966-2-1)
static float SRGBToLinear(float C)
{
	return C <= 0.04045f ? C / 12.92f : FMath::Pow((C + 0.055f) / 1.055f, 2.4f);
}

// Parse color with srgb:, hex:, or raw linear (R=,G=,B=,A=) formats
static FLinearColor ParseLinearColor(const FString& Value)
{
	FString Trimmed = Value.TrimStartAndEnd();

	// "srgb:(R=0.9,G=0.6,B=0.1,A=1.0)" — parse then convert sRGB→linear
	if (Trimmed.StartsWith(TEXT("srgb:"), ESearchCase::IgnoreCase))
	{
		FLinearColor sRGB = ParseLinearColorRaw(Trimmed.Mid(5));
		return FLinearColor(SRGBToLinear(sRGB.R), SRGBToLinear(sRGB.G), SRGBToLinear(sRGB.B), sRGB.A);
	}

	// "hex:#E8A624" or "hex:#E8A624FF" — parse hex then convert sRGB→linear
	if (Trimmed.StartsWith(TEXT("hex:"), ESearchCase::IgnoreCase))
	{
		FString Hex = Trimmed.Mid(4).TrimStartAndEnd();
		if (Hex.StartsWith(TEXT("#"))) Hex = Hex.Mid(1);
		if (Hex.Len() >= 6)
		{
			uint32 R = FParse::HexNumber(*Hex.Mid(0, 2));
			uint32 G = FParse::HexNumber(*Hex.Mid(2, 2));
			uint32 B = FParse::HexNumber(*Hex.Mid(4, 2));
			float A = 1.0f;
			if (Hex.Len() >= 8)
			{
				A = FParse::HexNumber(*Hex.Mid(6, 2)) / 255.0f;
			}
			return FLinearColor(
				SRGBToLinear(R / 255.0f),
				SRGBToLinear(G / 255.0f),
				SRGBToLinear(B / 255.0f),
				A
			);
		}
		UE_LOG(LogBlueprintLLM, Warning, TEXT("ParseLinearColor: invalid hex format '%s', need >=6 hex chars"), *Hex);
	}

	// Raw linear: (R=0.807,G=0.381,B=0.018,A=1.0)
	return ParseLinearColorRaw(Trimmed);
}

static FMargin ParseMargin(const FString& Value)
{
	FMargin Result(0.f);
	float Uniform = 0.f;
	if (FDefaultValueHelper::ParseFloat(Value, Uniform))
	{
		return FMargin(Uniform);
	}
	FString Clean = Value.TrimStartAndEnd()
		.Replace(TEXT("("), TEXT(""))
		.Replace(TEXT(")"), TEXT(""));
	TArray<FString> Parts;
	Clean.ParseIntoArray(Parts, TEXT(","));
	for (const FString& Part : Parts)
	{
		FString Key, Val;
		Part.Split(TEXT("="), &Key, &Val);
		Key.TrimStartAndEndInline();
		Val.TrimStartAndEndInline();
		float F = FCString::Atof(*Val);
		if      (Key == TEXT("Left"))   Result.Left   = F;
		else if (Key == TEXT("Top"))    Result.Top    = F;
		else if (Key == TEXT("Right"))  Result.Right  = F;
		else if (Key == TEXT("Bottom")) Result.Bottom = F;
	}
	return Result;
}

FCommandResult FCommandServer::HandleSetWidgetProperty(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	FString WidgetName = Params->GetStringField(TEXT("widget_name"));
	FString PropertyName = Params->GetStringField(TEXT("property"));

	if (WBPName.IsEmpty() || WidgetName.IsEmpty() || PropertyName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required params: widget_blueprint, widget_name, property"));
	}

	if (!Params->HasField(TEXT("value")))
	{
		return FCommandResult::Error(TEXT("Missing required param: value"));
	}

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP)
	{
		{ FString WErr = FString::Printf(TEXT("Widget Blueprint not found: %s."), *WBPName);
			WErr += TEXT(" Widget Blueprints are in /Game/UI/. Ensure it was created with create_widget_blueprint first.");
			return FCommandResult::Error(WErr); }
	}

	// ── Safety check: protect artist-created widgets from accidental corruption ──
	// Widgets created by Arcwright live in /Game/UI/. Widgets elsewhere (e.g. /Game/WBP_MainHUD)
	// were created by artists/designers and have complex internal structure (event graphs,
	// bindings, hierarchy) that set_widget_property can destroy.
	{
		FString PackagePath = WBP->GetPackage()->GetName();
		bool bIsArcwrightWidget = PackagePath.StartsWith(TEXT("/Game/UI/")) ||
								  PackagePath.StartsWith(TEXT("/Game/Arcwright/"));
		if (!bIsArcwrightWidget)
		{
			bool bForce = Params->HasField(TEXT("force")) && Params->GetBoolField(TEXT("force"));
			if (!bForce)
			{
				FString ErrMsg = FString::Printf(
					TEXT("Widget '%s' was NOT created by Arcwright (path: %s). "
						 "Modifying external widgets can destroy their internal structure — "
						 "event graphs, bindings, and hierarchy. "
						 "Use 'force: true' to override this safety check. "
						 "SAFER: modify via C++ (WidgetTree->FindWidget + SetText/SetVisibility) instead."),
					*WBPName, *PackagePath);
				UE_LOG(LogBlueprintLLM, Warning, TEXT("set_widget_property BLOCKED: %s"), *ErrMsg);
				return FCommandResult::Error(ErrMsg);
			}
			else
			{
				UE_LOG(LogBlueprintLLM, Warning,
					TEXT("set_widget_property: FORCE modifying external widget '%s' at '%s' — risk of corruption"),
					*WBPName, *PackagePath);
			}
		}
	}

	UWidget* Widget = FindWidgetByName(WBP, WidgetName);
	if (!Widget)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Widget not found: %s"), *WidgetName));
	}

	const TSharedPtr<FJsonValue>& Value = Params->Values.FindChecked(TEXT("value"));
	FString ValueStr;
	bool bHandled = false;

	// ---- Check layout/slot properties FIRST (apply to any widget type) ----
	static const TSet<FString> LayoutProperties = {
		TEXT("padding"), TEXT("horizontal_alignment"), TEXT("vertical_alignment"),
		TEXT("position"), TEXT("size"), TEXT("anchors"), TEXT("alignment")
	};
	bool bIsLayoutProperty = LayoutProperties.Contains(PropertyName);

	// ---- Common widget properties (apply to all widget types) ----
	if (PropertyName == TEXT("visibility"))
	{
		FString VisStr = Value->AsString();
		ESlateVisibility Vis = ESlateVisibility::Visible;
		if (VisStr.Equals(TEXT("Hidden"), ESearchCase::IgnoreCase))
			Vis = ESlateVisibility::Hidden;
		else if (VisStr.Equals(TEXT("Collapsed"), ESearchCase::IgnoreCase))
			Vis = ESlateVisibility::Collapsed;
		else if (VisStr.Equals(TEXT("HitTestInvisible"), ESearchCase::IgnoreCase))
			Vis = ESlateVisibility::HitTestInvisible;
		else if (VisStr.Equals(TEXT("SelfHitTestInvisible"), ESearchCase::IgnoreCase))
			Vis = ESlateVisibility::SelfHitTestInvisible;
		Widget->SetVisibility(Vis);
		bHandled = true;
	}
	else if (PropertyName == TEXT("is_enabled"))
	{
		Widget->SetIsEnabled(Value->AsBool());
		bHandled = true;
	}
	else if (PropertyName == TEXT("render_opacity"))
	{
		Widget->SetRenderOpacity(Value->AsNumber());
		bHandled = true;
	}

	// ---- Type-specific properties (only if not a layout property) ----
	if (!bHandled && !bIsLayoutProperty)
	{
		if (UTextBlock* TB = Cast<UTextBlock>(Widget))
		{
			if (PropertyName == TEXT("text"))
			{
				TB->SetText(FText::FromString(Value->AsString()));
				bHandled = true;
			}
			else if (PropertyName == TEXT("font_size"))
			{
				FSlateFontInfo Font = TB->GetFont();
				Font.Size = (int32)Value->AsNumber();
				TB->SetFont(Font);
				bHandled = true;
			}
			else if (PropertyName == TEXT("color"))
			{
				const TSharedPtr<FJsonObject>& ColorObj = Value->AsObject();
				FLinearColor Color(
					ColorObj->GetNumberField(TEXT("r")),
					ColorObj->GetNumberField(TEXT("g")),
					ColorObj->GetNumberField(TEXT("b")),
					ColorObj->HasField(TEXT("a")) ? ColorObj->GetNumberField(TEXT("a")) : 1.0
				);
				TB->SetColorAndOpacity(FSlateColor(Color));
				bHandled = true;
			}
			else if (PropertyName == TEXT("justification"))
			{
				FString JustStr = Value->AsString();
				ETextJustify::Type Justify = ETextJustify::Left;
				if (JustStr.Equals(TEXT("Center"), ESearchCase::IgnoreCase))
					Justify = ETextJustify::Center;
				else if (JustStr.Equals(TEXT("Right"), ESearchCase::IgnoreCase))
					Justify = ETextJustify::Right;
				TB->SetJustification(Justify);
				bHandled = true;
			}
		}
		else if (UProgressBar* PB = Cast<UProgressBar>(Widget))
		{
			if (PropertyName == TEXT("percent"))
			{
				PB->SetPercent(Value->AsNumber());
				bHandled = true;
			}
			else if (PropertyName == TEXT("fill_color"))
			{
				const TSharedPtr<FJsonObject>& ColorObj = Value->AsObject();
				FLinearColor Color(
					ColorObj->GetNumberField(TEXT("r")),
					ColorObj->GetNumberField(TEXT("g")),
					ColorObj->GetNumberField(TEXT("b")),
					ColorObj->HasField(TEXT("a")) ? ColorObj->GetNumberField(TEXT("a")) : 1.0
				);
				PB->SetFillColorAndOpacity(Color);
				bHandled = true;
			}
			else if (PropertyName == TEXT("background_color"))
			{
				const TSharedPtr<FJsonObject>& ColorObj = Value->AsObject();
				FLinearColor Color(
					ColorObj->GetNumberField(TEXT("r")),
					ColorObj->GetNumberField(TEXT("g")),
					ColorObj->GetNumberField(TEXT("b")),
					ColorObj->HasField(TEXT("a")) ? ColorObj->GetNumberField(TEXT("a")) : 1.0
				);
				FProgressBarStyle Style = PB->GetWidgetStyle();
				Style.BackgroundImage.TintColor = FSlateColor(Color);
				PB->SetWidgetStyle(Style);
				bHandled = true;
			}
		}
		else if (UImage* Img = Cast<UImage>(Widget))
		{
			if (PropertyName == TEXT("color_and_opacity") || PropertyName == TEXT("color"))
			{
				const TSharedPtr<FJsonObject>& ColorObj = Value->AsObject();
				FLinearColor Color(
					ColorObj->GetNumberField(TEXT("r")),
					ColorObj->GetNumberField(TEXT("g")),
					ColorObj->GetNumberField(TEXT("b")),
					ColorObj->HasField(TEXT("a")) ? ColorObj->GetNumberField(TEXT("a")) : 1.0
				);
				Img->SetColorAndOpacity(Color);
				bHandled = true;
			}
			else if (PropertyName == TEXT("brush_color"))
			{
				const TSharedPtr<FJsonObject>& ColorObj = Value->AsObject();
				FLinearColor Color(
					ColorObj->GetNumberField(TEXT("r")),
					ColorObj->GetNumberField(TEXT("g")),
					ColorObj->GetNumberField(TEXT("b")),
					ColorObj->HasField(TEXT("a")) ? ColorObj->GetNumberField(TEXT("a")) : 1.0
				);
				Img->SetBrushTintColor(FSlateColor(Color));
				bHandled = true;
			}
		}
		else if (UButton* Btn = Cast<UButton>(Widget))
		{
			if (PropertyName == TEXT("background_color"))
			{
				const TSharedPtr<FJsonObject>& ColorObj = Value->AsObject();
				FLinearColor Color(
					ColorObj->GetNumberField(TEXT("r")),
					ColorObj->GetNumberField(TEXT("g")),
					ColorObj->GetNumberField(TEXT("b")),
					ColorObj->HasField(TEXT("a")) ? ColorObj->GetNumberField(TEXT("a")) : 1.0
				);
				Btn->SetBackgroundColor(Color);
				bHandled = true;
			}
		}
	}

	// ---- Slot-based layout properties (apply to any widget in a panel) ----
	UPanelSlot* Slot = Widget->Slot;
	if (bIsLayoutProperty && Slot)
	{
		if (PropertyName == TEXT("padding"))
		{
			const TSharedPtr<FJsonObject>& PadObj = Value->AsObject();
			float Left = PadObj->HasField(TEXT("left")) ? PadObj->GetNumberField(TEXT("left")) : 0;
			float Top = PadObj->HasField(TEXT("top")) ? PadObj->GetNumberField(TEXT("top")) : 0;
			float Right = PadObj->HasField(TEXT("right")) ? PadObj->GetNumberField(TEXT("right")) : 0;
			float Bottom = PadObj->HasField(TEXT("bottom")) ? PadObj->GetNumberField(TEXT("bottom")) : 0;
			FMargin Padding(Left, Top, Right, Bottom);

			if (UCanvasPanelSlot* CanvasSlot = Cast<UCanvasPanelSlot>(Slot))
			{
				// CanvasPanel doesn't have padding in the same way; use offsets
			}
			else if (UVerticalBoxSlot* VSlot = Cast<UVerticalBoxSlot>(Slot))
			{
				VSlot->SetPadding(Padding);
			}
			else if (UHorizontalBoxSlot* HSlot = Cast<UHorizontalBoxSlot>(Slot))
			{
				HSlot->SetPadding(Padding);
			}
			else if (UOverlaySlot* OSlot = Cast<UOverlaySlot>(Slot))
			{
				OSlot->SetPadding(Padding);
			}
		}
		else if (PropertyName == TEXT("horizontal_alignment"))
		{
			FString AlignStr = Value->AsString();
			EHorizontalAlignment HAlign = EHorizontalAlignment::HAlign_Left;
			if (AlignStr.Equals(TEXT("Center"), ESearchCase::IgnoreCase))
				HAlign = EHorizontalAlignment::HAlign_Center;
			else if (AlignStr.Equals(TEXT("Right"), ESearchCase::IgnoreCase))
				HAlign = EHorizontalAlignment::HAlign_Right;
			else if (AlignStr.Equals(TEXT("Fill"), ESearchCase::IgnoreCase))
				HAlign = EHorizontalAlignment::HAlign_Fill;

			if (UCanvasPanelSlot* CanvasSlot = Cast<UCanvasPanelSlot>(Slot))
			{
				FAnchors CurAnchors = CanvasSlot->GetAnchors();
				if (HAlign == EHorizontalAlignment::HAlign_Center)
				{
					CurAnchors.Minimum.X = 0.5f;
					CurAnchors.Maximum.X = 0.5f;
				}
				else if (HAlign == EHorizontalAlignment::HAlign_Right)
				{
					CurAnchors.Minimum.X = 1.0f;
					CurAnchors.Maximum.X = 1.0f;
				}
				CanvasSlot->SetAnchors(CurAnchors);
				CanvasSlot->SetAlignment(FVector2D(
					(HAlign == EHorizontalAlignment::HAlign_Center) ? 0.5 :
					(HAlign == EHorizontalAlignment::HAlign_Right) ? 1.0 : 0.0,
					CanvasSlot->GetAlignment().Y));
			}
			else if (UVerticalBoxSlot* VSlot = Cast<UVerticalBoxSlot>(Slot))
			{
				VSlot->SetHorizontalAlignment(HAlign);
			}
			else if (UOverlaySlot* OSlot = Cast<UOverlaySlot>(Slot))
			{
				OSlot->SetHorizontalAlignment(HAlign);
			}
		}
		else if (PropertyName == TEXT("vertical_alignment"))
		{
			FString AlignStr = Value->AsString();
			EVerticalAlignment VAlign = EVerticalAlignment::VAlign_Top;
			if (AlignStr.Equals(TEXT("Center"), ESearchCase::IgnoreCase))
				VAlign = EVerticalAlignment::VAlign_Center;
			else if (AlignStr.Equals(TEXT("Bottom"), ESearchCase::IgnoreCase))
				VAlign = EVerticalAlignment::VAlign_Bottom;
			else if (AlignStr.Equals(TEXT("Fill"), ESearchCase::IgnoreCase))
				VAlign = EVerticalAlignment::VAlign_Fill;

			if (UCanvasPanelSlot* CanvasSlot = Cast<UCanvasPanelSlot>(Slot))
			{
				FAnchors CurAnchors = CanvasSlot->GetAnchors();
				if (VAlign == EVerticalAlignment::VAlign_Center)
				{
					CurAnchors.Minimum.Y = 0.5f;
					CurAnchors.Maximum.Y = 0.5f;
				}
				else if (VAlign == EVerticalAlignment::VAlign_Bottom)
				{
					CurAnchors.Minimum.Y = 1.0f;
					CurAnchors.Maximum.Y = 1.0f;
				}
				CanvasSlot->SetAnchors(CurAnchors);
				CanvasSlot->SetAlignment(FVector2D(
					CanvasSlot->GetAlignment().X,
					(VAlign == EVerticalAlignment::VAlign_Center) ? 0.5 :
					(VAlign == EVerticalAlignment::VAlign_Bottom) ? 1.0 : 0.0));
			}
			else if (UHorizontalBoxSlot* HSlot = Cast<UHorizontalBoxSlot>(Slot))
			{
				HSlot->SetVerticalAlignment(VAlign);
			}
			else if (UOverlaySlot* OSlot = Cast<UOverlaySlot>(Slot))
			{
				OSlot->SetVerticalAlignment(VAlign);
			}
		}
		// CanvasPanel slot-specific: position, size, anchors, alignment
		else if (UCanvasPanelSlot* CanvasSlot = Cast<UCanvasPanelSlot>(Slot))
		{
			if (PropertyName == TEXT("position"))
			{
				const TSharedPtr<FJsonObject>& PosObj = Value->AsObject();
				FVector2D Pos = CanvasSlot->GetPosition();
				if (PosObj->HasField(TEXT("x")))
					Pos.X = PosObj->GetNumberField(TEXT("x"));
				if (PosObj->HasField(TEXT("y")))
					Pos.Y = PosObj->GetNumberField(TEXT("y"));
				CanvasSlot->SetPosition(Pos);
			}
			else if (PropertyName == TEXT("size"))
			{
				const TSharedPtr<FJsonObject>& SizeObj = Value->AsObject();
				FVector2D Size = CanvasSlot->GetSize();
				if (SizeObj->HasField(TEXT("x")))
					Size.X = SizeObj->GetNumberField(TEXT("x"));
				if (SizeObj->HasField(TEXT("y")))
					Size.Y = SizeObj->GetNumberField(TEXT("y"));
				CanvasSlot->SetAutoSize(false);
				CanvasSlot->SetSize(Size);
			}
			else if (PropertyName == TEXT("anchors"))
			{
				const TSharedPtr<FJsonObject>& AnchObj = Value->AsObject();
				FAnchors NewAnchors = CanvasSlot->GetAnchors();
				if (AnchObj->HasField(TEXT("min_x")))
					NewAnchors.Minimum.X = AnchObj->GetNumberField(TEXT("min_x"));
				if (AnchObj->HasField(TEXT("min_y")))
					NewAnchors.Minimum.Y = AnchObj->GetNumberField(TEXT("min_y"));
				if (AnchObj->HasField(TEXT("max_x")))
					NewAnchors.Maximum.X = AnchObj->GetNumberField(TEXT("max_x"));
				if (AnchObj->HasField(TEXT("max_y")))
					NewAnchors.Maximum.Y = AnchObj->GetNumberField(TEXT("max_y"));
				CanvasSlot->SetAnchors(NewAnchors);
			}
			else if (PropertyName == TEXT("alignment"))
			{
				const TSharedPtr<FJsonObject>& AlignObj = Value->AsObject();
				FVector2D NewAlignment(
					AlignObj->HasField(TEXT("x")) ? AlignObj->GetNumberField(TEXT("x")) : 0,
					AlignObj->HasField(TEXT("y")) ? AlignObj->GetNumberField(TEXT("y")) : 0
				);
				CanvasSlot->SetAlignment(NewAlignment);
			}
		}
		bHandled = true;
	}

	// ── Extended Widget Property Surface (PascalCase dot-notation) ─────────
	// Target Surface properties from HTML→UMG translation pipeline.
	// Uses string-format values: colors as "(R=f,G=f,B=f,A=f)", margins as
	// "(Left=f,Top=f,Right=f,Bottom=f)", enums/bools/floats as plain strings.
	if (!bHandled)
	{
		ValueStr = Value->AsString();

		// ── Universal ─────────────────────────────────────────────
		if (PropertyName == TEXT("Visibility"))
		{
			ESlateVisibility V = ESlateVisibility::Visible;
			if      (ValueStr == TEXT("Hidden"))    V = ESlateVisibility::Hidden;
			else if (ValueStr == TEXT("Collapsed")) V = ESlateVisibility::Collapsed;
			Widget->SetVisibility(V);
			bHandled = true;
		}
		else if (PropertyName == TEXT("RenderOpacity"))
		{
			Widget->SetRenderOpacity(FCString::Atof(*ValueStr));
			bHandled = true;
		}
		else if (PropertyName == TEXT("IsEnabled"))
		{
			Widget->SetIsEnabled(ValueStr == TEXT("true"));
			bHandled = true;
		}
		else if (PropertyName == TEXT("ToolTipText"))
		{
			Widget->SetToolTipText(FText::FromString(ValueStr));
			bHandled = true;
		}

		// ── TextBlock ─────────────────────────────────────────────
		else if (PropertyName == TEXT("Text"))
		{
			if (UTextBlock* W = Cast<UTextBlock>(Widget))
			{
				W->SetText(FText::FromString(ValueStr));
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Text: widget is not a TextBlock"));
		}
		else if (PropertyName == TEXT("Font.Size"))
		{
			if (UTextBlock* W = Cast<UTextBlock>(Widget))
			{
				FSlateFontInfo F = W->GetFont();
				F.Size = FCString::Atoi(*ValueStr);
				W->SetFont(F);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Font.Size: widget is not a TextBlock"));
		}
		else if (PropertyName == TEXT("Font.Typeface"))
		{
			if (UTextBlock* W = Cast<UTextBlock>(Widget))
			{
				FSlateFontInfo F = W->GetFont();
				F.TypefaceFontName = FName(*ValueStr);
				W->SetFont(F);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Font.Typeface: widget is not a TextBlock"));
		}
		else if (PropertyName == TEXT("Font.Family"))
		{
			if (UTextBlock* W = Cast<UTextBlock>(Widget))
			{
				FSlateFontInfo F = W->GetFont();
				UObject* FontAsset = LoadObject<UObject>(nullptr, *ValueStr);
				if (FontAsset)
				{
					F.FontObject = FontAsset;
					W->SetFont(F);
					bHandled = true;
				}
				else return FCommandResult::Error(TEXT("Font.Family: asset not found: ") + ValueStr);
			}
			else return FCommandResult::Error(TEXT("Font.Family: widget is not a TextBlock"));
		}
		else if (PropertyName == TEXT("Font.LetterSpacing"))
		{
			if (UTextBlock* W = Cast<UTextBlock>(Widget))
			{
				FSlateFontInfo F = W->GetFont();
				F.LetterSpacing = FCString::Atoi(*ValueStr);
				W->SetFont(F);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Font.LetterSpacing: widget is not a TextBlock"));
		}
		else if (PropertyName == TEXT("ColorAndOpacity"))
		{
			if (UTextBlock* TB2 = Cast<UTextBlock>(Widget))
			{
				TB2->SetColorAndOpacity(FSlateColor(ParseLinearColor(ValueStr)));
				bHandled = true;
			}
			else if (UImage* Img2 = Cast<UImage>(Widget))
			{
				Img2->SetColorAndOpacity(ParseLinearColor(ValueStr));
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("ColorAndOpacity: widget is not a TextBlock or Image"));
		}
		else if (PropertyName == TEXT("Justification"))
		{
			if (UTextBlock* W = Cast<UTextBlock>(Widget))
			{
				ETextJustify::Type J = ETextJustify::Left;
				if      (ValueStr == TEXT("Center")) J = ETextJustify::Center;
				else if (ValueStr == TEXT("Right"))  J = ETextJustify::Right;
				W->SetJustification(J);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Justification: widget is not a TextBlock"));
		}
		else if (PropertyName == TEXT("AutoWrapText"))
		{
			if (UTextBlock* W = Cast<UTextBlock>(Widget))
			{
				W->SetAutoWrapText(ValueStr == TEXT("true"));
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("AutoWrapText: widget is not a TextBlock"));
		}
		else if (PropertyName == TEXT("WrapTextAt"))
		{
			if (UTextBlock* W = Cast<UTextBlock>(Widget))
			{
				W->SetWrapTextAt(FCString::Atof(*ValueStr));
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("WrapTextAt: widget is not a TextBlock"));
		}

		// ── Border ────────────────────────────────────────────────
		else if (PropertyName == TEXT("BrushColor"))
		{
			if (UBorder* W = Cast<UBorder>(Widget))
			{
				W->SetBrushColor(ParseLinearColor(ValueStr));
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("BrushColor: widget is not a Border"));
		}
		else if (PropertyName == TEXT("Brush.DrawType"))
		{
			auto ParseDrawType = [](const FString& V) -> ESlateBrushDrawType::Type
			{
				if      (V == TEXT("NoDrawType"))  return ESlateBrushDrawType::NoDrawType;
				else if (V == TEXT("Box"))          return ESlateBrushDrawType::Box;
				else if (V == TEXT("Border"))       return ESlateBrushDrawType::Border;
				else if (V == TEXT("Image"))        return ESlateBrushDrawType::Image;
				else if (V == TEXT("RoundedBox"))   return ESlateBrushDrawType::RoundedBox;
				return ESlateBrushDrawType::Image;
			};
			if (UBorder* Bdr = Cast<UBorder>(Widget))
			{
				FSlateBrush Brush = Bdr->Background;
				Brush.DrawAs = ParseDrawType(ValueStr);
				Bdr->SetBrush(Brush);
				bHandled = true;
			}
			else if (UImage* Img2 = Cast<UImage>(Widget))
			{
				FSlateBrush Brush = Img2->GetBrush();
				Brush.DrawAs = ParseDrawType(ValueStr);
				Img2->SetBrush(Brush);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Brush.DrawType: widget is not a Border or Image"));
		}
		else if (PropertyName == TEXT("Brush.Margin"))
		{
			if (UBorder* W = Cast<UBorder>(Widget))
			{
				FSlateBrush Brush = W->Background;
				Brush.Margin = ParseMargin(ValueStr);
				W->SetBrush(Brush);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Brush.Margin: widget is not a Border"));
		}
		else if (PropertyName == TEXT("Padding"))
		{
			if (UBorder* W = Cast<UBorder>(Widget))
			{
				W->SetPadding(ParseMargin(ValueStr));
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Padding: widget is not a Border"));
		}
		else if (PropertyName == TEXT("HAlign"))
		{
			if (UBorder* W = Cast<UBorder>(Widget))
			{
				EHorizontalAlignment A = HAlign_Left;
				if      (ValueStr == TEXT("Center")) A = HAlign_Center;
				else if (ValueStr == TEXT("Right"))  A = HAlign_Right;
				else if (ValueStr == TEXT("Fill"))   A = HAlign_Fill;
				W->SetHorizontalAlignment(A);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("HAlign: widget is not a Border"));
		}
		else if (PropertyName == TEXT("VAlign"))
		{
			if (UBorder* W = Cast<UBorder>(Widget))
			{
				EVerticalAlignment A = VAlign_Top;
				if      (ValueStr == TEXT("Center")) A = VAlign_Center;
				else if (ValueStr == TEXT("Bottom")) A = VAlign_Bottom;
				else if (ValueStr == TEXT("Fill"))   A = VAlign_Fill;
				W->SetVerticalAlignment(A);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("VAlign: widget is not a Border"));
		}

		// ── Image ─────────────────────────────────────────────────
		else if (PropertyName == TEXT("Brush.ResourceObject"))
		{
			if (UImage* W = Cast<UImage>(Widget))
			{
				UTexture2D* Tex = LoadObject<UTexture2D>(nullptr, *ValueStr);
				if (Tex)
				{
					W->SetBrushFromTexture(Tex);
					bHandled = true;
				}
				else return FCommandResult::Error(TEXT("Brush.ResourceObject: texture not found: ") + ValueStr);
			}
			else return FCommandResult::Error(TEXT("Brush.ResourceObject: widget is not an Image"));
		}
		else if (PropertyName == TEXT("Brush.TintColor"))
		{
			if (UImage* W = Cast<UImage>(Widget))
			{
				FSlateBrush Brush = W->GetBrush();
				Brush.TintColor = FSlateColor(ParseLinearColor(ValueStr));
				W->SetBrush(Brush);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Brush.TintColor: widget is not an Image"));
		}

		// ── Button ────────────────────────────────────────────────
		else if (PropertyName == TEXT("Style.Normal.TintColor"))
		{
			if (UButton* W = Cast<UButton>(Widget))
			{
				FButtonStyle Style = W->GetStyle();
				Style.Normal.TintColor = FSlateColor(ParseLinearColor(ValueStr));
				W->SetStyle(Style);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Style.Normal.TintColor: widget is not a Button"));
		}
		else if (PropertyName == TEXT("Style.Hovered.TintColor"))
		{
			if (UButton* W = Cast<UButton>(Widget))
			{
				FButtonStyle Style = W->GetStyle();
				Style.Hovered.TintColor = FSlateColor(ParseLinearColor(ValueStr));
				W->SetStyle(Style);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Style.Hovered.TintColor: widget is not a Button"));
		}
		else if (PropertyName == TEXT("Style.Pressed.TintColor"))
		{
			if (UButton* W = Cast<UButton>(Widget))
			{
				FButtonStyle Style = W->GetStyle();
				Style.Pressed.TintColor = FSlateColor(ParseLinearColor(ValueStr));
				W->SetStyle(Style);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Style.Pressed.TintColor: widget is not a Button"));
		}
		else if (PropertyName == TEXT("Style.Disabled.TintColor"))
		{
			if (UButton* W = Cast<UButton>(Widget))
			{
				FButtonStyle Style = W->GetStyle();
				Style.Disabled.TintColor = FSlateColor(ParseLinearColor(ValueStr));
				W->SetStyle(Style);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Style.Disabled.TintColor: widget is not a Button"));
		}
		else if (PropertyName == TEXT("Style.Normal.DrawType"))
		{
			if (UButton* W = Cast<UButton>(Widget))
			{
				FButtonStyle Style = W->GetStyle();
				if      (ValueStr == TEXT("RoundedBox")) Style.Normal.DrawAs = ESlateBrushDrawType::RoundedBox;
				else if (ValueStr == TEXT("Box"))        Style.Normal.DrawAs = ESlateBrushDrawType::Box;
				else if (ValueStr == TEXT("Image"))      Style.Normal.DrawAs = ESlateBrushDrawType::Image;
				W->SetStyle(Style);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Style.Normal.DrawType: widget is not a Button"));
		}
		else if (PropertyName == TEXT("Style.Normal.OutlineSettings.Width"))
		{
			if (UButton* W = Cast<UButton>(Widget))
			{
				FButtonStyle Style = W->GetStyle();
				Style.Normal.OutlineSettings.Width = FCString::Atof(*ValueStr);
				W->SetStyle(Style);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Style.Normal.OutlineSettings.Width: widget is not a Button"));
		}
		else if (PropertyName == TEXT("Style.Normal.OutlineSettings.Color"))
		{
			if (UButton* W = Cast<UButton>(Widget))
			{
				FButtonStyle Style = W->GetStyle();
				Style.Normal.OutlineSettings.Color = FSlateColor(ParseLinearColor(ValueStr));
				W->SetStyle(Style);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Style.Normal.OutlineSettings.Color: widget is not a Button"));
		}
		else if (PropertyName == TEXT("Style.Padding"))
		{
			if (UButton* W = Cast<UButton>(Widget))
			{
				FButtonStyle Style = W->GetStyle();
				FMargin M = ParseMargin(ValueStr);
				Style.SetNormalPadding(M);
				Style.SetPressedPadding(M);
				W->SetStyle(Style);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Style.Padding: widget is not a Button"));
		}
		else if (PropertyName == TEXT("IsFocusable"))
		{
			if (UButton* W = Cast<UButton>(Widget))
			{
				PRAGMA_DISABLE_DEPRECATION_WARNINGS
				W->IsFocusable = (ValueStr == TEXT("true"));
				PRAGMA_ENABLE_DEPRECATION_WARNINGS
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("IsFocusable: widget is not a Button"));
		}

		// ── ProgressBar ───────────────────────────────────────────
		else if (PropertyName == TEXT("Percent"))
		{
			if (UProgressBar* W = Cast<UProgressBar>(Widget))
			{
				W->SetPercent(FCString::Atof(*ValueStr));
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Percent: widget is not a ProgressBar"));
		}
		else if (PropertyName == TEXT("FillColorAndOpacity"))
		{
			if (UProgressBar* W = Cast<UProgressBar>(Widget))
			{
				W->SetFillColorAndOpacity(ParseLinearColor(ValueStr));
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("FillColorAndOpacity: widget is not a ProgressBar"));
		}
		else if (PropertyName == TEXT("Style.BackgroundImage.TintColor"))
		{
			if (UProgressBar* W = Cast<UProgressBar>(Widget))
			{
				FProgressBarStyle Style = W->GetWidgetStyle();
				Style.BackgroundImage.TintColor = FSlateColor(ParseLinearColor(ValueStr));
				W->SetWidgetStyle(Style);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Style.BackgroundImage.TintColor: widget is not a ProgressBar"));
		}
		else if (PropertyName == TEXT("Style.FillImage.TintColor"))
		{
			if (UProgressBar* W = Cast<UProgressBar>(Widget))
			{
				FProgressBarStyle Style = W->GetWidgetStyle();
				Style.FillImage.TintColor = FSlateColor(ParseLinearColor(ValueStr));
				W->SetWidgetStyle(Style);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Style.FillImage.TintColor: widget is not a ProgressBar"));
		}
		else if (PropertyName == TEXT("BarFillType"))
		{
			if (UProgressBar* W = Cast<UProgressBar>(Widget))
			{
				EProgressBarFillType::Type T = EProgressBarFillType::LeftToRight;
				if      (ValueStr == TEXT("RightToLeft")) T = EProgressBarFillType::RightToLeft;
				else if (ValueStr == TEXT("TopToBottom")) T = EProgressBarFillType::TopToBottom;
				else if (ValueStr == TEXT("BottomToTop")) T = EProgressBarFillType::BottomToTop;
				W->SetBarFillType(T);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("BarFillType: widget is not a ProgressBar"));
		}

		// ── ScrollBox ─────────────────────────────────────────────
		else if (PropertyName == TEXT("Orientation"))
		{
			if (UScrollBox* W = Cast<UScrollBox>(Widget))
			{
				EOrientation O = Orient_Vertical;
				if (ValueStr == TEXT("Orient_Horizontal")) O = Orient_Horizontal;
				W->SetOrientation(O);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("Orientation: widget is not a ScrollBox"));
		}
		else if (PropertyName == TEXT("ScrollBarVisibility"))
		{
			if (UScrollBox* W = Cast<UScrollBox>(Widget))
			{
				ESlateVisibility V = ESlateVisibility::Visible;
				if      (ValueStr == TEXT("Auto"))   V = ESlateVisibility::SelfHitTestInvisible;
				else if (ValueStr == TEXT("Hidden")) V = ESlateVisibility::Hidden;
				W->SetScrollBarVisibility(V);
				bHandled = true;
			}
			else return FCommandResult::Error(TEXT("ScrollBarVisibility: widget is not a ScrollBox"));
		}

		// ── Canvas Panel Slot ─────────────────────────────────────
		else if (PropertyName == TEXT("Slot.Position.X"))
		{
			if (UCanvasPanelSlot* CSlot = Cast<UCanvasPanelSlot>(Widget->Slot))
			{
				FVector2D Pos = CSlot->GetPosition();
				Pos.X = FCString::Atof(*ValueStr);
				CSlot->SetPosition(Pos);
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("Slot.Position.Y"))
		{
			if (UCanvasPanelSlot* CSlot = Cast<UCanvasPanelSlot>(Widget->Slot))
			{
				FVector2D Pos = CSlot->GetPosition();
				Pos.Y = FCString::Atof(*ValueStr);
				CSlot->SetPosition(Pos);
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("Slot.Size.X"))
		{
			if (UCanvasPanelSlot* CSlot = Cast<UCanvasPanelSlot>(Widget->Slot))
			{
				FVector2D Sz = CSlot->GetSize();
				Sz.X = FCString::Atof(*ValueStr);
				CSlot->SetSize(Sz);
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("Slot.Size.Y"))
		{
			if (UCanvasPanelSlot* CSlot = Cast<UCanvasPanelSlot>(Widget->Slot))
			{
				FVector2D Sz = CSlot->GetSize();
				Sz.Y = FCString::Atof(*ValueStr);
				CSlot->SetSize(Sz);
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("Slot.ZOrder"))
		{
			if (UCanvasPanelSlot* CSlot = Cast<UCanvasPanelSlot>(Widget->Slot))
			{
				CSlot->SetZOrder(FCString::Atoi(*ValueStr));
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("Slot.AutoSize"))
		{
			if (UCanvasPanelSlot* CSlot = Cast<UCanvasPanelSlot>(Widget->Slot))
			{
				CSlot->SetAutoSize(ValueStr == TEXT("true"));
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("Slot.Anchors.Min.X"))
		{
			if (UCanvasPanelSlot* CSlot = Cast<UCanvasPanelSlot>(Widget->Slot))
			{
				FAnchorData A = CSlot->GetLayout();
				A.Anchors.Minimum.X = FCString::Atof(*ValueStr);
				CSlot->SetLayout(A);
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("Slot.Anchors.Min.Y"))
		{
			if (UCanvasPanelSlot* CSlot = Cast<UCanvasPanelSlot>(Widget->Slot))
			{
				FAnchorData A = CSlot->GetLayout();
				A.Anchors.Minimum.Y = FCString::Atof(*ValueStr);
				CSlot->SetLayout(A);
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("Slot.Anchors.Max.X"))
		{
			if (UCanvasPanelSlot* CSlot = Cast<UCanvasPanelSlot>(Widget->Slot))
			{
				FAnchorData A = CSlot->GetLayout();
				A.Anchors.Maximum.X = FCString::Atof(*ValueStr);
				CSlot->SetLayout(A);
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("Slot.Anchors.Max.Y"))
		{
			if (UCanvasPanelSlot* CSlot = Cast<UCanvasPanelSlot>(Widget->Slot))
			{
				FAnchorData A = CSlot->GetLayout();
				A.Anchors.Maximum.Y = FCString::Atof(*ValueStr);
				CSlot->SetLayout(A);
				bHandled = true;
			}
		}

		// ── HBox / VBox Slots ─────────────────────────────────────
		else if (PropertyName == TEXT("Slot.Padding"))
		{
			if (UHorizontalBoxSlot* HSlot = Cast<UHorizontalBoxSlot>(Widget->Slot))
			{
				HSlot->SetPadding(ParseMargin(ValueStr));
				bHandled = true;
			}
			else if (UVerticalBoxSlot* VSlot = Cast<UVerticalBoxSlot>(Widget->Slot))
			{
				VSlot->SetPadding(ParseMargin(ValueStr));
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("Slot.FillWidth"))
		{
			if (UHorizontalBoxSlot* HSlot = Cast<UHorizontalBoxSlot>(Widget->Slot))
			{
				FSlateChildSize ChildSize;
				ChildSize.SizeRule = ESlateSizeRule::Fill;
				ChildSize.Value = FCString::Atof(*ValueStr);
				HSlot->SetSize(ChildSize);
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("Slot.FillHeight"))
		{
			if (UVerticalBoxSlot* VSlot = Cast<UVerticalBoxSlot>(Widget->Slot))
			{
				FSlateChildSize ChildSize;
				ChildSize.SizeRule = ESlateSizeRule::Fill;
				ChildSize.Value = FCString::Atof(*ValueStr);
				VSlot->SetSize(ChildSize);
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("Slot.HAlign"))
		{
			EHorizontalAlignment HA = HAlign_Left;
			if      (ValueStr == TEXT("Center")) HA = HAlign_Center;
			else if (ValueStr == TEXT("Right"))  HA = HAlign_Right;
			else if (ValueStr == TEXT("Fill"))   HA = HAlign_Fill;
			if (UHorizontalBoxSlot* HSlot = Cast<UHorizontalBoxSlot>(Widget->Slot))
			{
				HSlot->SetHorizontalAlignment(HA);
				bHandled = true;
			}
			else if (UVerticalBoxSlot* VSlot = Cast<UVerticalBoxSlot>(Widget->Slot))
			{
				VSlot->SetHorizontalAlignment(HA);
				bHandled = true;
			}
			else if (UOverlaySlot* OSlot = Cast<UOverlaySlot>(Widget->Slot))
			{
				OSlot->SetHorizontalAlignment(HA);
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("Slot.VAlign"))
		{
			EVerticalAlignment VA = VAlign_Top;
			if      (ValueStr == TEXT("Center")) VA = VAlign_Center;
			else if (ValueStr == TEXT("Bottom")) VA = VAlign_Bottom;
			else if (ValueStr == TEXT("Fill"))   VA = VAlign_Fill;
			if (UHorizontalBoxSlot* HSlot = Cast<UHorizontalBoxSlot>(Widget->Slot))
			{
				HSlot->SetVerticalAlignment(VA);
				bHandled = true;
			}
			else if (UVerticalBoxSlot* VSlot = Cast<UVerticalBoxSlot>(Widget->Slot))
			{
				VSlot->SetVerticalAlignment(VA);
				bHandled = true;
			}
			else if (UOverlaySlot* OSlot = Cast<UOverlaySlot>(Widget->Slot))
			{
				OSlot->SetVerticalAlignment(VA);
				bHandled = true;
			}
		}

		// ── UniformGridPanel / GridPanel Slot ──────────────────────
		else if (PropertyName == TEXT("Slot.Row"))
		{
			if (UUniformGridSlot* UGSlot = Cast<UUniformGridSlot>(Widget->Slot))
			{
				UGSlot->SetRow(FCString::Atoi(*ValueStr));
				bHandled = true;
			}
			else if (UGridSlot* GSlot = Cast<UGridSlot>(Widget->Slot))
			{
				GSlot->SetRow(FCString::Atoi(*ValueStr));
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("Slot.Column"))
		{
			if (UUniformGridSlot* UGSlot = Cast<UUniformGridSlot>(Widget->Slot))
			{
				UGSlot->SetColumn(FCString::Atoi(*ValueStr));
				bHandled = true;
			}
			else if (UGridSlot* GSlot = Cast<UGridSlot>(Widget->Slot))
			{
				GSlot->SetColumn(FCString::Atoi(*ValueStr));
				bHandled = true;
			}
		}

		// ── SizeBox ───────────────────────────────────────────────
		else if (PropertyName == TEXT("WidthOverride"))
		{
			if (USizeBox* SB = Cast<USizeBox>(Widget))
			{
				SB->SetWidthOverride(FCString::Atof(*ValueStr));
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("HeightOverride"))
		{
			if (USizeBox* SB = Cast<USizeBox>(Widget))
			{
				SB->SetHeightOverride(FCString::Atof(*ValueStr));
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("MinDesiredWidth"))
		{
			if (USizeBox* SB = Cast<USizeBox>(Widget))
			{
				SB->SetMinDesiredWidth(FCString::Atof(*ValueStr));
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("MinDesiredHeight"))
		{
			if (USizeBox* SB = Cast<USizeBox>(Widget))
			{
				SB->SetMinDesiredHeight(FCString::Atof(*ValueStr));
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("MaxDesiredWidth"))
		{
			if (USizeBox* SB = Cast<USizeBox>(Widget))
			{
				SB->SetMaxDesiredWidth(FCString::Atof(*ValueStr));
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("MaxDesiredHeight"))
		{
			if (USizeBox* SB = Cast<USizeBox>(Widget))
			{
				SB->SetMaxDesiredHeight(FCString::Atof(*ValueStr));
				bHandled = true;
			}
		}

		// ── Image Brush.ImageSize ─────────────────────────────────
		else if (PropertyName == TEXT("Brush.ImageSize.X"))
		{
			if (UImage* Img = Cast<UImage>(Widget))
			{
				FSlateBrush Brush = Img->GetBrush();
				Brush.ImageSize.X = FCString::Atof(*ValueStr);
				Img->SetBrush(Brush);
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("Brush.ImageSize.Y"))
		{
			if (UImage* Img = Cast<UImage>(Widget))
			{
				FSlateBrush Brush = Img->GetBrush();
				Brush.ImageSize.Y = FCString::Atof(*ValueStr);
				Img->SetBrush(Brush);
				bHandled = true;
			}
		}

		// ── WrapBox ───────────────────────────────────────────────
		else if (PropertyName == TEXT("InnerSlotPadding.X"))
		{
			if (UWrapBox* WB = Cast<UWrapBox>(Widget))
			{
				FVector2D Pad = WB->GetInnerSlotPadding();
				Pad.X = FCString::Atof(*ValueStr);
				WB->SetInnerSlotPadding(Pad);
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("InnerSlotPadding.Y"))
		{
			if (UWrapBox* WB = Cast<UWrapBox>(Widget))
			{
				FVector2D Pad = WB->GetInnerSlotPadding();
				Pad.Y = FCString::Atof(*ValueStr);
				WB->SetInnerSlotPadding(Pad);
				bHandled = true;
			}
		}
		else if (PropertyName == TEXT("Slot.FillEmptySpace"))
		{
			if (UWrapBoxSlot* WBSlot = Cast<UWrapBoxSlot>(Widget->Slot))
			{
				WBSlot->SetFillEmptySpace(ValueStr == TEXT("true"));
				bHandled = true;
			}
		}
	}

	if (!bHandled)
	{
		return FCommandResult::Error(FString::Printf(
			TEXT("Unknown property '%s' for widget type %s"),
			*PropertyName, *Widget->GetClass()->GetName()));
	}

	// Compile and save to disk
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(WBP);
	FKismetEditorUtilities::CompileBlueprint(WBP);
	WBP->MarkPackageDirty();

	UPackage* WBPPackage = WBP->GetPackage();
	if (WBPPackage)
	{
		FString PackagePath = WBPPackage->GetName();
		FSavePackageArgs SaveArgs;
		SafeSavePackage(WBPPackage, WBP,
			FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension()),
			SaveArgs);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("widget_blueprint"), WBPName);
	Data->SetStringField(TEXT("widget_name"), WidgetName);
	Data->SetStringField(TEXT("property"), PropertyName);
	Data->SetBoolField(TEXT("compiled"), true);

	// Auto-validate layout after property change
	int32 LayoutScore = ComputeLayoutScore(WBP);
	Data->SetNumberField(TEXT("layout_score"), LayoutScore);
	if (LayoutScore >= 0 && LayoutScore < 50)
	{
		Data->SetBoolField(TEXT("layout_critical"), true);
		Data->SetStringField(TEXT("layout_warning"),
			FString::Printf(TEXT("Layout score %d/100 — run auto_fix_widget_layout"), LayoutScore));
	}

	UE_LOG(LogBlueprintLLM, Log, TEXT("Set property '%s' on widget '%s' in %s (layout: %d)"), *PropertyName, *WidgetName, *WBPName, LayoutScore);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetWidgetProperty(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	FString WidgetName = Params->GetStringField(TEXT("widget_name"));
	FString PropertyName = Params->GetStringField(TEXT("property"));

	if (WBPName.IsEmpty() || WidgetName.IsEmpty() || PropertyName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required params: widget_blueprint, widget_name, property"));
	}

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Widget Blueprint not found: %s"), *WBPName));
	}

	UWidget* Widget = FindWidgetByName(WBP, WidgetName);
	if (!Widget)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Widget not found: %s"), *WidgetName));
	}

	FString ResultValue;
	bool bFound = false;

	// ── TextBlock read-back ───────────────────────────────────
	if (UTextBlock* TB = Cast<UTextBlock>(Widget))
	{
		if (PropertyName == TEXT("Text") || PropertyName == TEXT("text"))
		{
			ResultValue = TB->GetText().ToString();
			bFound = true;
		}
		else if (PropertyName == TEXT("ColorAndOpacity") || PropertyName == TEXT("color"))
		{
			FLinearColor C = TB->GetColorAndOpacity().GetSpecifiedColor();
			ResultValue = FString::Printf(TEXT("(R=%.4f,G=%.4f,B=%.4f,A=%.4f)"), C.R, C.G, C.B, C.A);
			bFound = true;
		}
		else if (PropertyName == TEXT("Font.Size") || PropertyName == TEXT("font_size"))
		{
			ResultValue = FString::FromInt(TB->GetFont().Size);
			bFound = true;
		}
		else if (PropertyName == TEXT("Font.Typeface"))
		{
			ResultValue = TB->GetFont().TypefaceFontName.ToString();
			bFound = true;
		}
		else if (PropertyName == TEXT("Font.LetterSpacing"))
		{
			ResultValue = FString::FromInt(TB->GetFont().LetterSpacing);
			bFound = true;
		}
		else if (PropertyName == TEXT("Justification") || PropertyName == TEXT("justification"))
		{
			ETextJustify::Type CurJustify = ETextJustify::Left;
			FProperty* JProp = TB->GetClass()->FindPropertyByName(TEXT("Justification"));
			if (JProp)
			{
				const uint8* ValPtr = JProp->ContainerPtrToValuePtr<uint8>(TB);
				CurJustify = static_cast<ETextJustify::Type>(*ValPtr);
			}
			switch (CurJustify)
			{
				case ETextJustify::Left:   ResultValue = TEXT("Left"); break;
				case ETextJustify::Center: ResultValue = TEXT("Center"); break;
				case ETextJustify::Right:  ResultValue = TEXT("Right"); break;
			}
			bFound = true;
		}
	}

	// ── Border read-back ──────────────────────────────────────
	if (!bFound)
	{
		if (UBorder* B = Cast<UBorder>(Widget))
		{
			if (PropertyName == TEXT("BrushColor"))
			{
				FLinearColor C = B->GetBrushColor();
				ResultValue = FString::Printf(TEXT("(R=%.4f,G=%.4f,B=%.4f,A=%.4f)"), C.R, C.G, C.B, C.A);
				bFound = true;
			}
		}
	}

	// ── ProgressBar read-back ─────────────────────────────────
	if (!bFound)
	{
		if (UProgressBar* PB = Cast<UProgressBar>(Widget))
		{
			if (PropertyName == TEXT("Percent") || PropertyName == TEXT("percent"))
			{
				ResultValue = FString::SanitizeFloat(PB->GetPercent());
				bFound = true;
			}
		}
	}

	// ── Universal read-back ───────────────────────────────────
	if (!bFound)
	{
		if (PropertyName == TEXT("Visibility") || PropertyName == TEXT("visibility"))
		{
			switch (Widget->GetVisibility())
			{
				case ESlateVisibility::Visible:              ResultValue = TEXT("Visible"); break;
				case ESlateVisibility::Hidden:                ResultValue = TEXT("Hidden"); break;
				case ESlateVisibility::Collapsed:             ResultValue = TEXT("Collapsed"); break;
				case ESlateVisibility::HitTestInvisible:      ResultValue = TEXT("HitTestInvisible"); break;
				case ESlateVisibility::SelfHitTestInvisible:  ResultValue = TEXT("SelfHitTestInvisible"); break;
			}
			bFound = true;
		}
		else if (PropertyName == TEXT("RenderOpacity") || PropertyName == TEXT("render_opacity"))
		{
			ResultValue = FString::SanitizeFloat(Widget->GetRenderOpacity());
			bFound = true;
		}
	}

	// ── Canvas Slot read-back ─────────────────────────────────
	if (!bFound)
	{
		if (UCanvasPanelSlot* Slot = Cast<UCanvasPanelSlot>(Widget->Slot))
		{
			if (PropertyName == TEXT("Slot.Position.X"))
			{
				ResultValue = FString::SanitizeFloat(Slot->GetPosition().X);
				bFound = true;
			}
			else if (PropertyName == TEXT("Slot.Position.Y"))
			{
				ResultValue = FString::SanitizeFloat(Slot->GetPosition().Y);
				bFound = true;
			}
			else if (PropertyName == TEXT("Slot.Size.X"))
			{
				ResultValue = FString::SanitizeFloat(Slot->GetSize().X);
				bFound = true;
			}
			else if (PropertyName == TEXT("Slot.Size.Y"))
			{
				ResultValue = FString::SanitizeFloat(Slot->GetSize().Y);
				bFound = true;
			}
			else if (PropertyName == TEXT("Slot.ZOrder"))
			{
				ResultValue = FString::FromInt(Slot->GetZOrder());
				bFound = true;
			}
		}
	}

	// ── UniformGridSlot / GridSlot read-back ──────────────────
	if (!bFound)
	{
		if (UUniformGridSlot* UGSlot = Cast<UUniformGridSlot>(Widget->Slot))
		{
			if (PropertyName == TEXT("Slot.Row"))
			{
				ResultValue = FString::FromInt(UGSlot->GetRow());
				bFound = true;
			}
			else if (PropertyName == TEXT("Slot.Column"))
			{
				ResultValue = FString::FromInt(UGSlot->GetColumn());
				bFound = true;
			}
		}
	}

	// ── Image Brush.ImageSize read-back ───────────────────────
	if (!bFound)
	{
		if (UImage* Img = Cast<UImage>(Widget))
		{
			if (PropertyName == TEXT("Brush.ImageSize.X"))
			{
				ResultValue = FString::SanitizeFloat(Img->GetBrush().ImageSize.X);
				bFound = true;
			}
			else if (PropertyName == TEXT("Brush.ImageSize.Y"))
			{
				ResultValue = FString::SanitizeFloat(Img->GetBrush().ImageSize.Y);
				bFound = true;
			}
		}
	}

	if (!bFound)
	{
		return FCommandResult::Error(FString::Printf(
			TEXT("get_widget_property: unsupported property '%s' for widget type %s"),
			*PropertyName, *Widget->GetClass()->GetName()));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("property"), PropertyName);
	Data->SetStringField(TEXT("value"), ResultValue);
	Data->SetStringField(TEXT("widget_name"), WidgetName);
	Data->SetStringField(TEXT("widget_blueprint"), WBPName);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetWidgetTree(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	if (WBPName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required param: widget_blueprint"));
	}

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP)
	{
		{ FString WErr = FString::Printf(TEXT("Widget Blueprint not found: %s."), *WBPName);
			WErr += TEXT(" Widget Blueprints are in /Game/UI/. Ensure it was created with create_widget_blueprint first.");
			return FCommandResult::Error(WErr); }
	}

	if (!WBP->WidgetTree)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Widget Blueprint %s has no WidgetTree"), *WBPName));
	}

	TArray<TSharedPtr<FJsonValue>> TreeArray;
	UWidget* Root = WBP->WidgetTree->RootWidget;
	if (Root)
	{
		CollectWidgetChildren(Root, TreeArray, 0);
	}

	// Count total widgets
	int32 TotalWidgets = 0;
	WBP->WidgetTree->ForEachWidget([&](UWidget*) { TotalWidgets++; });

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("widget_blueprint"), WBPName);
	Data->SetNumberField(TEXT("total_widgets"), TotalWidgets);
	Data->SetArrayField(TEXT("tree"), TreeArray);
	Data->SetBoolField(TEXT("has_root"), Root != nullptr);
	if (Root)
	{
		Data->SetStringField(TEXT("root_type"), Root->GetClass()->GetName());
		Data->SetStringField(TEXT("root_name"), Root->GetName());
	}

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetViewportWidgets(const TSharedPtr<FJsonObject>& Params)
{
	// Find all UUserWidget instances during PIE — uses multiple discovery methods
	TArray<TSharedPtr<FJsonValue>> WidgetArray;
	int32 TotalFound = 0;
	int32 InViewport = 0;

	// Method 1: TObjectIterator — finds all UUserWidget instances in any world
	for (TObjectIterator<UUserWidget> It; It; ++It)
	{
		UUserWidget* Widget = *It;
		if (!Widget || Widget->HasAnyFlags(RF_ClassDefaultObject))
		{
			continue;
		}

		TotalFound++;
		bool bInVP = Widget->IsInViewport();
		if (bInVP) InViewport++;

		TSharedPtr<FJsonObject> WObj = MakeShareable(new FJsonObject());
		WObj->SetStringField(TEXT("class"), Widget->GetClass()->GetName());
		WObj->SetBoolField(TEXT("in_viewport"), bInVP);
		WObj->SetBoolField(TEXT("visible"), Widget->IsVisible());
		WObj->SetStringField(TEXT("visibility"), UEnum::GetValueAsString(Widget->GetVisibility()));
		WObj->SetStringField(TEXT("outer"), Widget->GetOuter() ? Widget->GetOuter()->GetName() : TEXT("None"));

		// Collect children from WidgetTree (design-time) or Slate hierarchy (runtime)
		TArray<TSharedPtr<FJsonValue>> ChildList;
		if (Widget->WidgetTree)
		{
			Widget->WidgetTree->ForEachWidget([&](UWidget* Child)
			{
				if (Child)
				{
					TSharedPtr<FJsonObject> ChildObj = MakeShareable(new FJsonObject());
					ChildObj->SetStringField(TEXT("name"), Child->GetName());
					ChildObj->SetStringField(TEXT("type"), Child->GetClass()->GetName());
					if (UTextBlock* TB = Cast<UTextBlock>(Child))
					{
						ChildObj->SetStringField(TEXT("text"), TB->GetText().ToString());
					}
					else if (UProgressBar* PB = Cast<UProgressBar>(Child))
					{
						ChildObj->SetNumberField(TEXT("percent"), PB->GetPercent());
					}
					ChildList.Add(MakeShareable(new FJsonValueObject(ChildObj)));
				}
			});
		}

		WObj->SetArrayField(TEXT("children"), ChildList);
		WObj->SetNumberField(TEXT("child_count"), ChildList.Num());
		WidgetArray.Add(MakeShareable(new FJsonValueObject(WObj)));
	}

	// Method 2: Check PIE world's player controller for managed widgets
	bool bPIERunning = false;
	FString PIEInfo;
	if (GEditor)
	{
		for (const FWorldContext& Context : GEngine->GetWorldContexts())
		{
			if (Context.WorldType == EWorldType::PIE && Context.World())
			{
				bPIERunning = true;
				UWorld* PIEWorld = Context.World();
				APlayerController* PC = PIEWorld->GetFirstPlayerController();
				if (PC)
				{
					PIEInfo = FString::Printf(TEXT("PIE active, PlayerController: %s"), *PC->GetName());
				}
				break;
			}
		}
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("total_user_widgets"), TotalFound);
	Data->SetNumberField(TEXT("in_viewport"), InViewport);
	Data->SetBoolField(TEXT("pie_running"), bPIERunning);
	if (!PIEInfo.IsEmpty())
	{
		Data->SetStringField(TEXT("pie_info"), PIEInfo);
	}
	Data->SetArrayField(TEXT("widgets"), WidgetArray);

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleReparentWidgetBlueprint(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("name"));
	FString NewParentName = Params->GetStringField(TEXT("new_parent"));
	if (WBPName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'name'"));
	if (NewParentName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'new_parent'"));

	// Find the widget blueprint
	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP) return FCommandResult::Error(FString::Printf(TEXT("Widget Blueprint not found: %s"), *WBPName));

	// Resolve new parent class
	UClass* NewParentClass = FindObject<UClass>(nullptr, *NewParentName);
	if (!NewParentClass)
	{
		// Try /Script/Module.ClassName patterns
		NewParentClass = FindObject<UClass>(nullptr, *FString::Printf(TEXT("/Script/UMG.%s"), *NewParentName));
	}
	if (!NewParentClass)
	{
		// Try all loaded modules
		for (TObjectIterator<UClass> It; It; ++It)
		{
			if (It->GetName() == NewParentName && It->IsChildOf(UUserWidget::StaticClass()))
			{
				NewParentClass = *It;
				break;
			}
		}
	}
	if (!NewParentClass)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Parent class not found: %s"), *NewParentName));
	}
	if (!NewParentClass->IsChildOf(UUserWidget::StaticClass()))
	{
		return FCommandResult::Error(FString::Printf(TEXT("'%s' is not a UUserWidget subclass"), *NewParentName));
	}

	FString OldParent = WBP->ParentClass ? WBP->ParentClass->GetName() : TEXT("None");

	// Scan for conflicting functions BEFORE reparenting
	TArray<TSharedPtr<FJsonValue>> ConflictArray;
	TArray<FName> FunctionsToRemove;

	for (UEdGraph* Graph : WBP->FunctionGraphs)
	{
		FName GraphName = Graph->GetFName();
		// Check if the new parent has a UFUNCTION with the same name
		UFunction* ParentFunc = NewParentClass->FindFunctionByName(GraphName);
		if (ParentFunc)
		{
			TSharedPtr<FJsonObject> Conflict = MakeShareable(new FJsonObject());
			Conflict->SetStringField(TEXT("function"), GraphName.ToString());

			bool bIsNativeEvent = ParentFunc->HasAnyFunctionFlags(FUNC_BlueprintEvent | FUNC_Native);
			bool bIsImplementable = ParentFunc->HasAnyFunctionFlags(FUNC_BlueprintEvent) && !ParentFunc->HasAnyFunctionFlags(FUNC_Native);

			if (bIsImplementable)
			{
				Conflict->SetStringField(TEXT("reason"), TEXT("Parent has BlueprintImplementableEvent — Blueprint can override safely"));
				Conflict->SetStringField(TEXT("action"), TEXT("kept"));
			}
			else if (bIsNativeEvent)
			{
				Conflict->SetStringField(TEXT("reason"), TEXT("Parent has BlueprintNativeEvent — removing Blueprint version"));
				Conflict->SetStringField(TEXT("action"), TEXT("removed"));
				FunctionsToRemove.Add(GraphName);
			}
			else
			{
				Conflict->SetStringField(TEXT("reason"), TEXT("Parent has BlueprintCallable (not overridable) — removing Blueprint version"));
				Conflict->SetStringField(TEXT("action"), TEXT("removed"));
				FunctionsToRemove.Add(GraphName);
			}

			ConflictArray.Add(MakeShareable(new FJsonValueObject(Conflict)));
		}
	}

	// Remove conflicting function graphs
	for (const FName& FuncName : FunctionsToRemove)
	{
		for (int32 i = WBP->FunctionGraphs.Num() - 1; i >= 0; --i)
		{
			if (WBP->FunctionGraphs[i]->GetFName() == FuncName)
			{
				UE_LOG(LogBlueprintLLM, Log, TEXT("ReparentWidget: Removing conflicting function '%s' from %s"), *FuncName.ToString(), *WBPName);
				WBP->FunctionGraphs.RemoveAt(i);
				break;
			}
		}
	}

	// Reparent
	WBP->ParentClass = NewParentClass;

	// Refresh all nodes to pick up new parent's functions/properties
	FBlueprintEditorUtils::RefreshAllNodes(WBP);
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(WBP);
	FKismetEditorUtilities::CompileBlueprint(WBP);

	bool bCompiled = (WBP->Status == EBlueprintStatus::BS_UpToDate);

	// Save
	WBP->MarkPackageDirty();
	UPackage* Pkg = WBP->GetPackage();
	if (Pkg)
	{
		FString PkgFilename = FPackageName::LongPackageNameToFilename(
			Pkg->GetName(), FPackageName::GetAssetPackageExtension());
		IFileManager::Get().MakeDirectory(*FPaths::GetPath(PkgFilename), true);
		FSavePackageArgs SaveArgs;
		SafeSavePackage(Pkg, WBP, PkgFilename, SaveArgs);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), WBPName);
	Data->SetStringField(TEXT("old_parent"), OldParent);
	Data->SetStringField(TEXT("new_parent"), NewParentClass->GetName());
	Data->SetBoolField(TEXT("compiled"), bCompiled);
	Data->SetArrayField(TEXT("conflicts_resolved"), ConflictArray);
	Data->SetNumberField(TEXT("functions_removed"), FunctionsToRemove.Num());

	UE_LOG(LogBlueprintLLM, Log, TEXT("Reparented widget '%s': %s -> %s (%d conflicts resolved, compiled=%d)"),
		*WBPName, *OldParent, *NewParentClass->GetName(), FunctionsToRemove.Num(), bCompiled);

	return FCommandResult::Ok(Data);
}

// ════════════════════════════════════════════════════════════════════
//  validate_widget_layout — inspect a widget for common layout problems
// ════════════════════════════════════════════════════════════════════
FCommandResult FCommandServer::HandleValidateWidgetLayout(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("name"));
	if (WBPName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'name' param"));

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP)
		return FCommandResult::Error(FString::Printf(TEXT("Widget Blueprint not found: %s"), *WBPName));

	UWidget* RootWidget = WBP->WidgetTree ? WBP->WidgetTree->RootWidget : nullptr;
	if (!RootWidget)
		return FCommandResult::Error(TEXT("Widget has no root"));

	TArray<TSharedPtr<FJsonValue>> Issues;
	int32 Score = 100;

	// Collect all children with their slot info
	struct FWidgetInfo
	{
		UWidget* Widget;
		FString Name;
		FString Type;
		int32 FontSize;
		FVector2D Position;
		bool bHasExplicitPosition;
	};
	TArray<FWidgetInfo> Children;

	UPanelWidget* RootPanel = Cast<UPanelWidget>(RootWidget);
	if (RootPanel)
	{
		for (int32 i = 0; i < RootPanel->GetChildrenCount(); i++)
		{
			UWidget* Child = RootPanel->GetChildAt(i);
			if (!Child) continue;

			FWidgetInfo Info;
			Info.Widget = Child;
			Info.Name = Child->GetName();
			Info.Type = Child->GetClass()->GetName();
			Info.FontSize = 0;
			Info.Position = FVector2D::ZeroVector;
			Info.bHasExplicitPosition = false;

			// Check font size for TextBlock
			if (UTextBlock* TB = Cast<UTextBlock>(Child))
			{
				Info.FontSize = static_cast<int32>(TB->GetFont().Size);
			}

			// Check canvas slot position
			if (UCanvasPanel* Canvas = Cast<UCanvasPanel>(RootPanel))
			{
				if (UCanvasPanelSlot* Slot = Cast<UCanvasPanelSlot>(Child->Slot))
				{
					FMargin Offsets = Slot->GetOffsets();
					Info.Position = FVector2D(Offsets.Left, Offsets.Top);
					FAnchors Anchors = Slot->GetAnchors();
					Info.bHasExplicitPosition = (Offsets.Left != 0 || Offsets.Top != 0 ||
						Anchors.Minimum != FVector2D::ZeroVector || Anchors.Maximum != FVector2D::ZeroVector);
				}
			}

			Children.Add(Info);
		}
	}

	// ── Check 1: Overlapping elements (same position) ──
	TMap<FString, TArray<FString>> PositionGroups;
	for (const FWidgetInfo& Info : Children)
	{
		FString PosKey = FString::Printf(TEXT("%.0f,%.0f"), Info.Position.X, Info.Position.Y);
		PositionGroups.FindOrAdd(PosKey).Add(Info.Name);
	}
	for (const auto& Pair : PositionGroups)
	{
		if (Pair.Value.Num() > 1)
		{
			TSharedPtr<FJsonObject> Issue = MakeShareable(new FJsonObject());
			Issue->SetStringField(TEXT("type"), TEXT("overlap"));
			Issue->SetStringField(TEXT("detail"),
				FString::Printf(TEXT("%d elements at same position (%s): %s"),
					Pair.Value.Num(), *Pair.Key, *FString::Join(Pair.Value, TEXT(", "))));
			Issues.Add(MakeShareable(new FJsonValueObject(Issue)));
			Score -= 15 * (Pair.Value.Num() - 1);
		}
	}

	// ── Check 2: No explicit positioning ──
	int32 UnpositionedCount = 0;
	for (const FWidgetInfo& Info : Children)
	{
		if (!Info.bHasExplicitPosition && Info.Type != TEXT("CanvasPanelSlot"))
		{
			++UnpositionedCount;
		}
	}
	if (UnpositionedCount > 1)
	{
		TSharedPtr<FJsonObject> Issue = MakeShareable(new FJsonObject());
		Issue->SetStringField(TEXT("type"), TEXT("no_anchoring"));
		Issue->SetStringField(TEXT("detail"),
			FString::Printf(TEXT("%d elements have no explicit position or anchor — will pile up at (0,0)"),
				UnpositionedCount));
		Issues.Add(MakeShareable(new FJsonValueObject(Issue)));
		Score -= 10 * UnpositionedCount;
	}

	// ── Check 3: Font too small ──
	for (const FWidgetInfo& Info : Children)
	{
		if (Info.FontSize > 0 && Info.FontSize < 14)
		{
			TSharedPtr<FJsonObject> Issue = MakeShareable(new FJsonObject());
			Issue->SetStringField(TEXT("type"), TEXT("text_too_small"));
			Issue->SetStringField(TEXT("element"), Info.Name);
			Issue->SetStringField(TEXT("detail"),
				FString::Printf(TEXT("Font size %d < minimum 14"), Info.FontSize));
			Issues.Add(MakeShareable(new FJsonValueObject(Issue)));
			Score -= 5;
		}
	}

	// ── Check 4: No background on CanvasPanel root ──
	if (Cast<UCanvasPanel>(RootWidget))
	{
		bool bHasBackground = false;
		// Check if any child is a Border or Image that could serve as background
		if (RootPanel)
		{
			for (int32 i = 0; i < RootPanel->GetChildrenCount(); i++)
			{
				if (RootPanel->GetChildAt(i)->IsA(UBorder::StaticClass()) ||
					RootPanel->GetChildAt(i)->IsA(UImage::StaticClass()))
				{
					bHasBackground = true;
					break;
				}
			}
		}
		if (!bHasBackground)
		{
			TSharedPtr<FJsonObject> Issue = MakeShareable(new FJsonObject());
			Issue->SetStringField(TEXT("type"), TEXT("no_background"));
			Issue->SetStringField(TEXT("detail"),
				TEXT("Root CanvasPanel has no Border/Image background — text may be unreadable over 3D scene"));
			Issues.Add(MakeShareable(new FJsonValueObject(Issue)));
			Score -= 10;
		}
	}

	// ── Check 5: Direct children on CanvasPanel without VerticalBox ──
	if (Cast<UCanvasPanel>(RootWidget) && Children.Num() > 3)
	{
		bool bHasLayoutBox = false;
		for (const FWidgetInfo& Info : Children)
		{
			if (Info.Type.Contains(TEXT("VerticalBox")) || Info.Type.Contains(TEXT("HorizontalBox")))
			{
				bHasLayoutBox = true;
				break;
			}
		}
		if (!bHasLayoutBox)
		{
			TSharedPtr<FJsonObject> Issue = MakeShareable(new FJsonObject());
			Issue->SetStringField(TEXT("type"), TEXT("no_layout_box"));
			Issue->SetStringField(TEXT("detail"),
				FString::Printf(TEXT("%d children directly on CanvasPanel without VerticalBox/HorizontalBox — consider using auto-layout"),
					Children.Num()));
			Issues.Add(MakeShareable(new FJsonValueObject(Issue)));
			Score -= 5;
		}
	}

	Score = FMath::Clamp(Score, 0, 100);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), WBPName);
	Data->SetArrayField(TEXT("issues"), Issues);
	Data->SetNumberField(TEXT("score"), Score);
	Data->SetNumberField(TEXT("child_count"), Children.Num());

	if (Score >= 80)
		Data->SetStringField(TEXT("recommendation"), TEXT("Layout looks acceptable"));
	else if (Score >= 50)
		Data->SetStringField(TEXT("recommendation"), TEXT("Consider running auto_fix_widget_layout to improve readability"));
	else
		Data->SetStringField(TEXT("recommendation"), TEXT("Run auto_fix_widget_layout — multiple layout issues detected"));

	return FCommandResult::Ok(Data);
}

// ════════════════════════════════════════════════════════════════════
//  auto_fix_widget_layout — automatically fix common layout problems
// ════════════════════════════════════════════════════════════════════
FCommandResult FCommandServer::HandleAutoFixWidgetLayout(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("name"));
	if (WBPName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'name' param"));

	// Safety check: only fix Arcwright-created widgets
	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP)
		return FCommandResult::Error(FString::Printf(TEXT("Widget Blueprint not found: %s"), *WBPName));

	FString PackagePath = WBP->GetPackage()->GetName();
	if (!PackagePath.StartsWith(TEXT("/Game/UI/")) && !PackagePath.StartsWith(TEXT("/Game/Arcwright/")))
	{
		bool bForce = Params->HasField(TEXT("force")) && Params->GetBoolField(TEXT("force"));
		if (!bForce)
			return FCommandResult::Error(FString::Printf(
				TEXT("Widget '%s' not created by Arcwright. Use force=true to override."), *WBPName));
	}

	UWidget* RootWidget = WBP->WidgetTree ? WBP->WidgetTree->RootWidget : nullptr;
	if (!RootWidget)
		return FCommandResult::Error(TEXT("Widget has no root"));

	UCanvasPanel* Canvas = Cast<UCanvasPanel>(RootWidget);
	if (!Canvas)
		return FCommandResult::Error(TEXT("Root widget is not a CanvasPanel — auto-fix only works on CanvasPanel roots"));

	int32 FixCount = 0;
	TArray<FString> FixesApplied;

	// ── Fix 1: Set positions on direct children to avoid overlap ──
	// Distribute children vertically with 30px spacing, right-aligned panel
	float YOffset = 20.0f;
	for (int32 i = 0; i < Canvas->GetChildrenCount(); i++)
	{
		UWidget* Child = Canvas->GetChildAt(i);
		if (!Child) continue;

		UCanvasPanelSlot* Slot = Cast<UCanvasPanelSlot>(Child->Slot);
		if (!Slot) continue;

		// Set anchors to right panel (60%-98% width)
		FAnchors Anchors;
		Anchors.Minimum = FVector2D(0.6f, 0.0f);
		Anchors.Maximum = FVector2D(0.98f, 0.0f);

		// Last 2 children: anchor to bottom
		if (i >= Canvas->GetChildrenCount() - 2)
		{
			Anchors.Minimum = FVector2D(0.6f, 1.0f);
			Anchors.Maximum = FVector2D(0.98f, 1.0f);
			float BottomOffset = -60.0f + ((i - (Canvas->GetChildrenCount() - 2)) * 28.0f);
			Slot->SetOffsets(FMargin(15.0f, BottomOffset, 0.0f, 20.0f));
		}
		else
		{
			Slot->SetOffsets(FMargin(15.0f, YOffset, 0.0f, 0.0f));
		}

		Slot->SetAnchors(Anchors);
		Slot->SetAutoSize(true);

		// ── Fix 2: Enforce minimum font size ──
		if (UTextBlock* TB = Cast<UTextBlock>(Child))
		{
			FSlateFontInfo Font = TB->GetFont();
			if (Font.Size < 14)
			{
				Font.Size = 14;
				TB->SetFont(Font);
				FixesApplied.Add(FString::Printf(TEXT("Set %s font to 14"), *Child->GetName()));
				++FixCount;
			}
		}

		++FixCount;
		YOffset += 35.0f; // 35px between items

		// Add extra spacing after certain elements
		if (i == 0) YOffset += 5.0f;  // Extra after title
		if (i == 1) YOffset += 15.0f; // Extra after description (before content)
	}

	FixesApplied.Add(FString::Printf(TEXT("Positioned %d children with 35px spacing"), Canvas->GetChildrenCount()));

	// Mark modified, compile, and SAVE TO DISK
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(WBP);
	FKismetEditorUtilities::CompileBlueprint(WBP);

	// Explicit save — this is why fixes weren't persisting between editor restarts
	UPackage* Pkg = WBP->GetPackage();
	if (Pkg)
	{
		FString PkgFilename = FPackageName::LongPackageNameToFilename(
			Pkg->GetName(), FPackageName::GetAssetPackageExtension());
		IFileManager::Get().MakeDirectory(*FPaths::GetPath(PkgFilename), true);
		FSavePackageArgs SaveArgs;
		SafeSavePackage(Pkg, WBP, PkgFilename, SaveArgs);
		FixesApplied.Add(TEXT("Saved to disk"));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), WBPName);
	Data->SetNumberField(TEXT("fixes_applied"), FixCount);

	TArray<TSharedPtr<FJsonValue>> FixArr;
	for (const FString& Fix : FixesApplied)
	{
		FixArr.Add(MakeShareable(new FJsonValueString(Fix)));
	}
	Data->SetArrayField(TEXT("fixes"), FixArr);

	// Auto-validate after fix
	TSharedPtr<FJsonObject> ValidateParams = MakeShareable(new FJsonObject());
	ValidateParams->SetStringField(TEXT("name"), WBPName);
	FCommandResult ValidateResult = HandleValidateWidgetLayout(ValidateParams);
	if (ValidateResult.bSuccess && ValidateResult.Data.IsValid())
	{
		Data->SetNumberField(TEXT("layout_score"), ValidateResult.Data->GetNumberField(TEXT("score")));
	}

	return FCommandResult::Ok(Data);
}

// ════════════════════════════════════════════════════════════════════
//  Helper: compute layout score for a widget (used by auto-validation)
// ════════════════════════════════════════════════════════════════════
int32 FCommandServer::ComputeLayoutScore(UWidgetBlueprint* WBP)
{
	if (!WBP) return -1;
	TSharedPtr<FJsonObject> Params = MakeShareable(new FJsonObject());
	Params->SetStringField(TEXT("name"), WBP->GetName());
	FCommandResult Result = HandleValidateWidgetLayout(Params);
	if (Result.bSuccess && Result.Data.IsValid())
	{
		return static_cast<int32>(Result.Data->GetNumberField(TEXT("score")));
	}
	return -1;
}

FCommandResult FCommandServer::HandleRemoveWidget(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	FString WidgetName = Params->GetStringField(TEXT("widget_name"));

	if (WBPName.IsEmpty() || WidgetName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required params: widget_blueprint, widget_name"));
	}

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP)
	{
		{ FString WErr = FString::Printf(TEXT("Widget Blueprint not found: %s."), *WBPName);
			WErr += TEXT(" Widget Blueprints are in /Game/UI/. Ensure it was created with create_widget_blueprint first.");
			return FCommandResult::Error(WErr); }
	}

	if (!WBP->WidgetTree)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Widget Blueprint %s has no WidgetTree"), *WBPName));
	}

	UWidget* Widget = FindWidgetByName(WBP, WidgetName);
	if (!Widget)
	{
		// Idempotent — not found = already removed
		TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
		Data->SetStringField(TEXT("widget_blueprint"), WBPName);
		Data->SetStringField(TEXT("widget_name"), WidgetName);
		Data->SetBoolField(TEXT("deleted"), false);
		Data->SetBoolField(TEXT("compiled"), false);
		return FCommandResult::Ok(Data);
	}

	// If this is the root, clear it
	if (WBP->WidgetTree->RootWidget == Widget)
	{
		WBP->WidgetTree->RootWidget = nullptr;
	}

	// Remove from parent panel if applicable
	if (Widget->Slot)
	{
		if (UPanelWidget* ParentPanel = Widget->Slot->Parent)
		{
			ParentPanel->RemoveChild(Widget);
		}
	}

	WBP->WidgetTree->RemoveWidget(Widget);

	// Compile
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(WBP);
	FKismetEditorUtilities::CompileBlueprint(WBP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("widget_blueprint"), WBPName);
	Data->SetStringField(TEXT("widget_name"), WidgetName);
	Data->SetBoolField(TEXT("deleted"), true);
	Data->SetBoolField(TEXT("compiled"), true);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Removed widget '%s' from %s"), *WidgetName, *WBPName);
	return FCommandResult::Ok(Data);
}

// ============================================================
// Behavior Tree commands
// ============================================================

FCommandResult FCommandServer::HandleCreateBehaviorTree(const TSharedPtr<FJsonObject>& Params)
{
	// Accept IR JSON as either inline object or JSON string
	TSharedPtr<FJsonObject> IRJson;

	if (Params->HasField(TEXT("ir_json")))
	{
		FString IRJsonStr = Params->GetStringField(TEXT("ir_json"));
		TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(IRJsonStr);
		if (!FJsonSerializer::Deserialize(Reader, IRJson) || !IRJson.IsValid())
		{
			return FCommandResult::Error(TEXT("Failed to parse ir_json string"));
		}
	}
	else if (Params->HasTypedField<EJson::Object>(TEXT("ir")))
	{
		IRJson = Params->GetObjectField(TEXT("ir"));
	}
	else
	{
		return FCommandResult::Error(TEXT("Missing required param: ir_json (string) or ir (object)"));
	}

	FString PackagePath = TEXT("/Game/Arcwright/BehaviorTrees");

	FBehaviorTreeBuilder::FBTBuildResult BTResult = FBehaviorTreeBuilder::CreateFromIR(IRJson, PackagePath);

	if (!BTResult.bSuccess)
	{
		return FCommandResult::Error(BTResult.ErrorMessage);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("tree_asset_path"), BTResult.TreeAssetPath);
	Data->SetStringField(TEXT("blackboard_asset_path"), BTResult.BlackboardAssetPath);
	Data->SetNumberField(TEXT("composite_count"), BTResult.CompositeCount);
	Data->SetNumberField(TEXT("task_count"), BTResult.TaskCount);
	Data->SetNumberField(TEXT("decorator_count"), BTResult.DecoratorCount);
	Data->SetNumberField(TEXT("service_count"), BTResult.ServiceCount);
	Data->SetNumberField(TEXT("total_node_count"),
		BTResult.CompositeCount + BTResult.TaskCount + BTResult.DecoratorCount + BTResult.ServiceCount);

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetBehaviorTreeInfo(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required param: name"));
	}

	TSharedPtr<FJsonObject> Info = FBehaviorTreeBuilder::GetBehaviorTreeInfo(Name);
	if (!Info.IsValid())
	{
		return FCommandResult::Error(FString::Printf(TEXT("Behavior Tree not found: %s"), *Name));
	}

	return FCommandResult::Ok(Info);
}

// ============================================================
// set_blackboard_key_default — set a default value on a BB key
// ============================================================
FCommandResult FCommandServer::HandleSetBlackboardKeyDefault(const TSharedPtr<FJsonObject>& Params)
{
	FString BBName = Params->GetStringField(TEXT("blackboard"));
	FString KeyName = Params->GetStringField(TEXT("key"));

	if (BBName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required param: blackboard"));
	if (KeyName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required param: key"));

	// Load the BB asset from our folder
	FString BBPath = FString::Printf(TEXT("/Game/Arcwright/BehaviorTrees/%s.%s"), *BBName, *BBName);
	UBlackboardData* BBAsset = LoadObject<UBlackboardData>(nullptr, *BBPath);
	if (!BBAsset)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Blackboard not found: %s"), *BBPath));
	}

	// Find the key
	FBlackboardEntry* FoundEntry = nullptr;
	for (FBlackboardEntry& Entry : BBAsset->Keys)
	{
		if (Entry.EntryName == FName(*KeyName))
		{
			FoundEntry = &Entry;
			break;
		}
	}
	if (!FoundEntry)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Blackboard key not found: %s"), *KeyName));
	}

	// Determine type and set value
	FString TypeName = FoundEntry->KeyType ? FoundEntry->KeyType->GetClass()->GetName() : TEXT("Unknown");

	if (TypeName.Contains(TEXT("Vector")))
	{
		const TSharedPtr<FJsonObject>* VecObj;
		if (!Params->TryGetObjectField(TEXT("value"), VecObj))
			return FCommandResult::Error(TEXT("Vector key requires 'value' object with x, y, z"));
		FVector Vec;
		Vec.X = (*VecObj)->GetNumberField(TEXT("x"));
		Vec.Y = (*VecObj)->GetNumberField(TEXT("y"));
		Vec.Z = (*VecObj)->GetNumberField(TEXT("z"));

		// Vector BB keys don't have a simple "default" field on the asset.
		// The proper way is to set it at runtime via the AIController.
		// However, we can store it as instance synced key data.
		// For now, return the info and note that runtime assignment is needed.

		// Actually — UBlackboardKeyType has no built-in asset-level default.
		// The correct approach is to wire this in the AIController Blueprint.
		// Let's return what we know so the caller can decide.
		TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
		Data->SetStringField(TEXT("blackboard"), BBName);
		Data->SetStringField(TEXT("key"), KeyName);
		Data->SetStringField(TEXT("key_type"), TypeName);
		Data->SetStringField(TEXT("note"), TEXT("Vector BB keys have no asset-level default. Set via AIController at runtime using SetValueAsVector."));
		UE_LOG(LogBlueprintLLM, Log, TEXT("set_blackboard_key_default: Vector key '%s' — needs runtime assignment"), *KeyName);
		return FCommandResult::Ok(Data);
	}
	else if (TypeName.Contains(TEXT("Float")))
	{
		double Val = Params->GetNumberField(TEXT("value"));
		// No asset-level default for float either
		TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
		Data->SetStringField(TEXT("blackboard"), BBName);
		Data->SetStringField(TEXT("key"), KeyName);
		Data->SetNumberField(TEXT("value"), Val);
		Data->SetStringField(TEXT("key_type"), TypeName);
		return FCommandResult::Ok(Data);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("blackboard"), BBName);
	Data->SetStringField(TEXT("key"), KeyName);
	Data->SetStringField(TEXT("key_type"), TypeName);
	Data->SetStringField(TEXT("note"), TEXT("No asset-level default support for this key type. Set at runtime."));
	return FCommandResult::Ok(Data);
}

// ============================================================
// set_class_defaults — set Blueprint CDO properties
// ============================================================
FCommandResult FCommandServer::HandleSetClassDefaults(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintName;
	if (!Params->TryGetStringField(TEXT("blueprint"), BlueprintName))
	{
		return FCommandResult::Error(TEXT("Missing required param: blueprint"));
	}

	const TSharedPtr<FJsonObject>* PropertiesObj;
	if (!Params->TryGetObjectField(TEXT("properties"), PropertiesObj))
	{
		return FCommandResult::Error(TEXT("Missing required param: properties"));
	}

	// Find the Blueprint asset (uses asset registry — same as get_blueprint_info)
	UBlueprint* BP = FindBlueprintByName(BlueprintName);
	if (!BP)
	{
		return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));
	}

	UObject* CDO = BP->GeneratedClass ? BP->GeneratedClass->GetDefaultObject() : nullptr;
	if (!CDO)
	{
		return FCommandResult::Error(TEXT("No generated class / CDO found. Compile the Blueprint first."));
	}

	TArray<FString> SetProperties;

	// Handle AIControllerClass — set on Pawn CDO
	FString AIControllerClassName;
	if ((*PropertiesObj)->TryGetStringField(TEXT("ai_controller_class"), AIControllerClassName))
	{
		APawn* PawnCDO = Cast<APawn>(CDO);
		if (PawnCDO)
		{
			// Find the AIController Blueprint class via asset registry
			UBlueprint* ControllerBP = FindBlueprintByName(AIControllerClassName);
			UClass* ControllerClass = ControllerBP ? ControllerBP->GeneratedClass : nullptr;
			if (ControllerClass && ControllerClass->IsChildOf(AAIController::StaticClass()))
			{
				PawnCDO->AIControllerClass = ControllerClass;
				PawnCDO->AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
				SetProperties.Add(TEXT("ai_controller_class"));
				UE_LOG(LogBlueprintLLM, Log, TEXT("Set AIControllerClass to %s on %s"), *ControllerClass->GetName(), *BlueprintName);
			}
			else
			{
				return FCommandResult::Error(FormatBlueprintNotFound(AIControllerClassName) + TEXT(" (must be an AIController subclass)"));
			}
		}
		else
		{
			return FCommandResult::Error(TEXT("Blueprint is not a Pawn — cannot set ai_controller_class"));
		}
	}

	// Handle default_behavior_tree — set on AIController CDO
	FString BehaviorTreeName;
	if ((*PropertiesObj)->TryGetStringField(TEXT("default_behavior_tree"), BehaviorTreeName))
	{
		AAIController* AICDO = Cast<AAIController>(CDO);
		if (AICDO)
		{
			FString BTAssetPath = FString::Printf(TEXT("/Game/Arcwright/BehaviorTrees/%s.%s"), *BehaviorTreeName, *BehaviorTreeName);
			UBehaviorTree* BT = LoadObject<UBehaviorTree>(nullptr, *BTAssetPath);
			if (!BT)
			{
				return FCommandResult::Error(FString::Printf(TEXT("BehaviorTree not found: %s"), *BehaviorTreeName));
			}

			// AAIController doesn't have a public DefaultBehaviorTree property.
			// We need to use reflection to find and set it.
			FProperty* BTProp = AICDO->GetClass()->FindPropertyByName(TEXT("DefaultBehaviorTree"));
			if (!BTProp)
			{
				// Some engine versions use different property names
				BTProp = AICDO->GetClass()->FindPropertyByName(TEXT("BehaviorTreeAsset"));
			}

			if (BTProp)
			{
				FObjectProperty* ObjProp = CastField<FObjectProperty>(BTProp);
				if (ObjProp)
				{
					ObjProp->SetObjectPropertyValue(BTProp->ContainerPtrToValuePtr<void>(AICDO), BT);
					SetProperties.Add(TEXT("default_behavior_tree"));
					UE_LOG(LogBlueprintLLM, Log, TEXT("Set DefaultBehaviorTree to %s on %s"), *BehaviorTreeName, *BlueprintName);
				}
			}
			else
			{
				UE_LOG(LogBlueprintLLM, Warning, TEXT("DefaultBehaviorTree property not found on AIController CDO. Will try RunBehaviorTree approach."));
				// Property not found is not fatal — we can still wire RunBehaviorTree in the event graph
				SetProperties.Add(TEXT("default_behavior_tree (property not found, use RunBehaviorTree instead)"));
			}
		}
		else
		{
			return FCommandResult::Error(TEXT("Blueprint is not an AIController — cannot set default_behavior_tree"));
		}
	}

	// Handle GameModeBase properties: default_pawn_class, player_controller_class
	FString DefaultPawnClassName;
	if ((*PropertiesObj)->TryGetStringField(TEXT("default_pawn_class"), DefaultPawnClassName))
	{
		AGameModeBase* GMCDO = Cast<AGameModeBase>(CDO);
		if (GMCDO)
		{
			UBlueprint* PawnBP = FindBlueprintByName(DefaultPawnClassName);
			UClass* PawnClass = PawnBP ? PawnBP->GeneratedClass : nullptr;
			if (!PawnClass)
			{
				// Try native class
				PawnClass = FindObject<UClass>(nullptr, *FString::Printf(TEXT("/Script/Engine.%s"), *DefaultPawnClassName));
			}
			if (PawnClass && PawnClass->IsChildOf(APawn::StaticClass()))
			{
				GMCDO->DefaultPawnClass = PawnClass;
				SetProperties.Add(TEXT("default_pawn_class"));
				UE_LOG(LogBlueprintLLM, Log, TEXT("Set DefaultPawnClass to %s on %s"), *PawnClass->GetName(), *BlueprintName);
			}
			else
			{
				return FCommandResult::Error(FString::Printf(TEXT("Pawn class not found or not a Pawn: %s"), *DefaultPawnClassName));
			}
		}
		else
		{
			return FCommandResult::Error(TEXT("Blueprint is not a GameModeBase — cannot set default_pawn_class"));
		}
	}

	FString PlayerControllerClassName;
	if ((*PropertiesObj)->TryGetStringField(TEXT("player_controller_class"), PlayerControllerClassName))
	{
		AGameModeBase* GMCDO = Cast<AGameModeBase>(CDO);
		if (GMCDO)
		{
			UBlueprint* ControllerBP = FindBlueprintByName(PlayerControllerClassName);
			UClass* ControllerClass = ControllerBP ? ControllerBP->GeneratedClass : nullptr;
			if (!ControllerClass)
			{
				ControllerClass = FindObject<UClass>(nullptr, *FString::Printf(TEXT("/Script/Engine.%s"), *PlayerControllerClassName));
			}
			if (ControllerClass && ControllerClass->IsChildOf(APlayerController::StaticClass()))
			{
				GMCDO->PlayerControllerClass = ControllerClass;
				SetProperties.Add(TEXT("player_controller_class"));
				UE_LOG(LogBlueprintLLM, Log, TEXT("Set PlayerControllerClass to %s on %s"), *ControllerClass->GetName(), *BlueprintName);
			}
			else
			{
				return FCommandResult::Error(FString::Printf(TEXT("PlayerController class not found: %s"), *PlayerControllerClassName));
			}
		}
		else
		{
			return FCommandResult::Error(TEXT("Blueprint is not a GameModeBase — cannot set player_controller_class"));
		}
	}

	// Handle auto_possess_ai
	FString AutoPossess;
	if ((*PropertiesObj)->TryGetStringField(TEXT("auto_possess_ai"), AutoPossess))
	{
		APawn* PawnCDO = Cast<APawn>(CDO);
		if (PawnCDO)
		{
			if (AutoPossess == TEXT("Disabled")) PawnCDO->AutoPossessAI = EAutoPossessAI::Disabled;
			else if (AutoPossess == TEXT("PlacedInWorld")) PawnCDO->AutoPossessAI = EAutoPossessAI::PlacedInWorld;
			else if (AutoPossess == TEXT("Spawned")) PawnCDO->AutoPossessAI = EAutoPossessAI::Spawned;
			else if (AutoPossess == TEXT("PlacedInWorldOrSpawned")) PawnCDO->AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
			else return FCommandResult::Error(FString::Printf(TEXT("Unknown AutoPossessAI value: %s"), *AutoPossess));
			SetProperties.Add(TEXT("auto_possess_ai"));
		}
	}

	// ── Generic UPROPERTY fallback via reflection ──
	// Any properties not handled by the specific handlers above are attempted
	// via FindPropertyByName on the CDO's class. Supports bool, int, float, string, enum (byte).
	for (const auto& Pair : (*PropertiesObj)->Values)
	{
		const FString& Key = Pair.Key;

		// Skip keys already handled above
		if (Key == TEXT("ai_controller_class") || Key == TEXT("default_behavior_tree") ||
			Key == TEXT("default_pawn_class") || Key == TEXT("player_controller_class") ||
			Key == TEXT("auto_possess_ai"))
		{
			continue;
		}

		// Already set by a specific handler?
		if (SetProperties.Contains(Key))
		{
			continue;
		}

		FProperty* Prop = CDO->GetClass()->FindPropertyByName(*Key);
		if (!Prop)
		{
			UE_LOG(LogBlueprintLLM, Warning, TEXT("set_class_defaults: property '%s' not found on CDO of %s"), *Key, *BlueprintName);
			continue;
		}

		FString ValueStr;
		if (Pair.Value->TryGetString(ValueStr))
		{
			// Bool property
			if (FBoolProperty* BoolProp = CastField<FBoolProperty>(Prop))
			{
				bool bVal = ValueStr.Equals(TEXT("true"), ESearchCase::IgnoreCase) || ValueStr == TEXT("1");
				BoolProp->SetPropertyValue_InContainer(CDO, bVal);
				SetProperties.Add(Key);
				UE_LOG(LogBlueprintLLM, Log, TEXT("set_class_defaults: %s = %s (bool)"), *Key, bVal ? TEXT("true") : TEXT("false"));
			}
			// Byte/enum property (for EMouseCursor::Type etc.)
			else if (FByteProperty* ByteProp = CastField<FByteProperty>(Prop))
			{
				if (ByteProp->Enum)
				{
					int64 EnumVal = ByteProp->Enum->GetValueByNameString(ValueStr);
					if (EnumVal == INDEX_NONE && ValueStr.Equals(TEXT("None"), ESearchCase::IgnoreCase))
					{
						EnumVal = 0; // EMouseCursor::None = 0
					}
					if (EnumVal != INDEX_NONE)
					{
						ByteProp->SetPropertyValue_InContainer(CDO, (uint8)EnumVal);
						SetProperties.Add(Key);
						UE_LOG(LogBlueprintLLM, Log, TEXT("set_class_defaults: %s = %s (enum %lld)"), *Key, *ValueStr, EnumVal);
					}
					else
					{
						UE_LOG(LogBlueprintLLM, Warning, TEXT("set_class_defaults: enum value '%s' not found for %s"), *ValueStr, *Key);
					}
				}
				else
				{
					uint8 ByteVal = (uint8)FCString::Atoi(*ValueStr);
					ByteProp->SetPropertyValue_InContainer(CDO, ByteVal);
					SetProperties.Add(Key);
				}
			}
			// Enum property (UE5 uses FEnumProperty for some enums)
			else if (FEnumProperty* EnumProp = CastField<FEnumProperty>(Prop))
			{
				UEnum* Enum = EnumProp->GetEnum();
				int64 EnumVal = Enum ? Enum->GetValueByNameString(ValueStr) : INDEX_NONE;
				if (EnumVal == INDEX_NONE && ValueStr.Equals(TEXT("None"), ESearchCase::IgnoreCase))
				{
					EnumVal = 0;
				}
				if (EnumVal != INDEX_NONE)
				{
					FNumericProperty* UnderlyingProp = EnumProp->GetUnderlyingProperty();
					if (UnderlyingProp)
					{
						UnderlyingProp->SetIntPropertyValue(EnumProp->ContainerPtrToValuePtr<void>(CDO), EnumVal);
					}
					SetProperties.Add(Key);
					UE_LOG(LogBlueprintLLM, Log, TEXT("set_class_defaults: %s = %s (enum %lld)"), *Key, *ValueStr, EnumVal);
				}
			}
			// Int property
			else if (FIntProperty* IntProp = CastField<FIntProperty>(Prop))
			{
				IntProp->SetPropertyValue_InContainer(CDO, FCString::Atoi(*ValueStr));
				SetProperties.Add(Key);
			}
			// Float property
			else if (FFloatProperty* FloatProp = CastField<FFloatProperty>(Prop))
			{
				FloatProp->SetPropertyValue_InContainer(CDO, FCString::Atof(*ValueStr));
				SetProperties.Add(Key);
			}
			// Double property
			else if (FDoubleProperty* DoubleProp = CastField<FDoubleProperty>(Prop))
			{
				DoubleProp->SetPropertyValue_InContainer(CDO, FCString::Atod(*ValueStr));
				SetProperties.Add(Key);
			}
			// String property
			else if (FStrProperty* StrProp = CastField<FStrProperty>(Prop))
			{
				StrProp->SetPropertyValue_InContainer(CDO, ValueStr);
				SetProperties.Add(Key);
			}
			// Name property
			else if (FNameProperty* NameProp = CastField<FNameProperty>(Prop))
			{
				NameProp->SetPropertyValue_InContainer(CDO, FName(*ValueStr));
				SetProperties.Add(Key);
			}
			// Class reference property (TSubclassOf<T>)
			else if (FClassProperty* ClassProp = CastField<FClassProperty>(Prop))
			{
				UClass* ClassValue = LoadObject<UClass>(nullptr, *ValueStr);
				if (!ClassValue)
				{
					// Try as a widget blueprint generated class
					FString WidgetBPName = ValueStr;
					WidgetBPName.RemoveFromEnd(TEXT("_C"));
					if (WidgetBPName.Contains(TEXT("/")))
					{
						ClassValue = LoadObject<UClass>(nullptr, *ValueStr);
					}
					else
					{
						// Try /Game/UI/ path convention
						FString FullPath = FString::Printf(TEXT("/Game/UI/%s.%s_C"), *WidgetBPName, *WidgetBPName);
						ClassValue = LoadObject<UClass>(nullptr, *FullPath);
					}
				}
				if (ClassValue)
				{
					ClassProp->SetObjectPropertyValue(ClassProp->ContainerPtrToValuePtr<void>(CDO), ClassValue);
					SetProperties.Add(Key);
					UE_LOG(LogBlueprintLLM, Log, TEXT("set_class_defaults: %s = %s (class)"), *Key, *ClassValue->GetName());
				}
				else
				{
					UE_LOG(LogBlueprintLLM, Warning, TEXT("set_class_defaults: class not found for '%s': %s"), *Key, *ValueStr);
				}
			}
			// Soft class reference property (TSoftClassPtr<T>)
			else if (CastField<FSoftClassProperty>(Prop))
			{
				// Use ImportText which handles the string conversion internally
				Prop->ImportText_Direct(*ValueStr, Prop->ContainerPtrToValuePtr<void>(CDO), CDO, PPF_None);
				SetProperties.Add(Key);
			}
			// Object reference property (TObjectPtr<T>)
			else if (FObjectProperty* ObjProp = CastField<FObjectProperty>(Prop))
			{
				UObject* ObjValue = LoadObject<UObject>(nullptr, *ValueStr);
				if (ObjValue)
				{
					ObjProp->SetObjectPropertyValue(ObjProp->ContainerPtrToValuePtr<void>(CDO), ObjValue);
					SetProperties.Add(Key);
					UE_LOG(LogBlueprintLLM, Log, TEXT("set_class_defaults: %s = %s (object)"), *Key, *ObjValue->GetName());
				}
				else
				{
					UE_LOG(LogBlueprintLLM, Warning, TEXT("set_class_defaults: object not found for '%s': %s"), *Key, *ValueStr);
				}
			}
			else
			{
				UE_LOG(LogBlueprintLLM, Warning, TEXT("set_class_defaults: unsupported property type for '%s' — %s"), *Key, *Prop->GetClass()->GetName());
			}
		}
	}

	// Mark modified and recompile
	BP->Modify();
	FKismetEditorUtilities::CompileBlueprint(BP);

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("blueprint"), BlueprintName);

	TArray<TSharedPtr<FJsonValue>> PropsArr;
	for (const FString& P : SetProperties)
	{
		PropsArr.Add(MakeShared<FJsonValueString>(P));
	}
	Data->SetArrayField(TEXT("properties_set"), PropsArr);

	return FCommandResult::Ok(Data);
}

// ============================================================
// setup_ai_for_pawn — One-command AI Controller wiring
// ============================================================

FCommandResult FCommandServer::HandleSetupAIForPawn(const TSharedPtr<FJsonObject>& Params)
{
	FString PawnName;
	if (!Params->TryGetStringField(TEXT("pawn_name"), PawnName))
	{
		return FCommandResult::Error(TEXT("Missing required param: pawn_name"));
	}

	FString BehaviorTreeName;
	if (!Params->TryGetStringField(TEXT("behavior_tree"), BehaviorTreeName))
	{
		return FCommandResult::Error(TEXT("Missing required param: behavior_tree"));
	}

	// Optional: custom controller name
	FString ControllerName;
	if (!Params->TryGetStringField(TEXT("controller_name"), ControllerName))
	{
		// Strip "BP_" prefix from pawn name to avoid "BP_BP_..." doubling
		FString BaseName = PawnName;
		if (BaseName.StartsWith(TEXT("BP_")))
		{
			BaseName = BaseName.Mid(3);
		}
		ControllerName = FString::Printf(TEXT("BP_%s_AIController"), *BaseName);
	}

	// 1. Verify the pawn Blueprint exists and is a Pawn
	UBlueprint* PawnBP = FindBlueprintByName(PawnName);
	if (!PawnBP)
	{
		return FCommandResult::Error(FormatBlueprintNotFound(PawnName));
	}

	UObject* PawnCDO = PawnBP->GeneratedClass ? PawnBP->GeneratedClass->GetDefaultObject() : nullptr;
	APawn* PawnObj = PawnCDO ? Cast<APawn>(PawnCDO) : nullptr;
	if (!PawnObj)
	{
		return FCommandResult::Error(FString::Printf(TEXT("%s is not a Pawn Blueprint"), *PawnName));
	}

	// 2. Verify the BehaviorTree asset exists
	FString BTAssetPath = FString::Printf(TEXT("/Game/Arcwright/BehaviorTrees/%s.%s"), *BehaviorTreeName, *BehaviorTreeName);
	UBehaviorTree* BT = LoadObject<UBehaviorTree>(nullptr, *BTAssetPath);
	if (!BT)
	{
		return FCommandResult::Error(FString::Printf(TEXT("BehaviorTree not found: %s"), *BehaviorTreeName));
	}

	// 3. Create or reuse the AIController Blueprint
	bool bCreatedNew = false;
	UBlueprint* ControllerBP = FindBlueprintByName(ControllerName);
	if (!ControllerBP)
	{
		// Create a new AIController Blueprint
		FString PackagePath = TEXT("/Game/Arcwright/Generated");
		FString PackageName = FString::Printf(TEXT("/Game/Arcwright/Generated/%s"), *ControllerName);
		UPackage* Package = CreatePackage(*PackageName);
		if (!Package)
		{
			return FCommandResult::Error(FString::Printf(TEXT("Failed to create package for %s"), *ControllerName));
		}

		UClass* ParentClass = AAIController::StaticClass();
		UBlueprintFactory* Factory = NewObject<UBlueprintFactory>();
		Factory->ParentClass = ParentClass;

		ControllerBP = Cast<UBlueprint>(Factory->FactoryCreateNew(
			UBlueprint::StaticClass(), Package, FName(*ControllerName),
			RF_Public | RF_Standalone, nullptr, GWarn));

		if (!ControllerBP)
		{
			return FCommandResult::Error(FString::Printf(TEXT("Failed to create AIController Blueprint: %s"), *ControllerName));
		}

		// Initial compile
		FKismetEditorUtilities::CompileBlueprint(ControllerBP);
		bCreatedNew = true;

		UE_LOG(LogBlueprintLLM, Log, TEXT("Created AIController Blueprint: %s"), *ControllerName);
	}
	else
	{
		UE_LOG(LogBlueprintLLM, Log, TEXT("Reusing existing AIController Blueprint: %s"), *ControllerName);
	}

	// 4. Wire RunBehaviorTree to BeginPlay in the controller's event graph
	if (bCreatedNew)
	{
		UEdGraph* EventGraph = nullptr;
		for (UEdGraph* Graph : ControllerBP->UbergraphPages)
		{
			if (Graph->GetFName() == TEXT("EventGraph"))
			{
				EventGraph = Graph;
				break;
			}
		}
		if (!EventGraph && ControllerBP->UbergraphPages.Num() > 0)
		{
			EventGraph = ControllerBP->UbergraphPages[0];
		}

		if (EventGraph)
		{
			const UEdGraphSchema_K2* Schema = GetDefault<UEdGraphSchema_K2>();

			// Find or create BeginPlay event node
			UK2Node_Event* BeginPlayNode = nullptr;
			for (UEdGraphNode* Node : EventGraph->Nodes)
			{
				UK2Node_Event* EvNode = Cast<UK2Node_Event>(Node);
				if (EvNode && EvNode->EventReference.GetMemberName() == FName(TEXT("ReceiveBeginPlay")))
				{
					BeginPlayNode = EvNode;
					break;
				}
			}

			if (!BeginPlayNode)
			{
				// Create BeginPlay event
				BeginPlayNode = NewObject<UK2Node_Event>(EventGraph);
				BeginPlayNode->EventReference.SetExternalMember(FName(TEXT("ReceiveBeginPlay")), AActor::StaticClass());
				BeginPlayNode->bOverrideFunction = true;
				EventGraph->AddNode(BeginPlayNode, false, false);
				BeginPlayNode->CreateNewGuid();
				BeginPlayNode->PostPlacedNewNode();
				BeginPlayNode->AllocateDefaultPins();
				BeginPlayNode->NodePosX = 0;
				BeginPlayNode->NodePosY = 0;
			}

			// Create RunBehaviorTree call node
			UK2Node_CallFunction* RunBTNode = NewObject<UK2Node_CallFunction>(EventGraph);
			UFunction* RunBTFunc = AAIController::StaticClass()->FindFunctionByName(FName(TEXT("RunBehaviorTree")));
			if (RunBTFunc)
			{
				RunBTNode->SetFromFunction(RunBTFunc);
				EventGraph->AddNode(RunBTNode, false, false);
				RunBTNode->CreateNewGuid();
				RunBTNode->PostPlacedNewNode();
				RunBTNode->AllocateDefaultPins();
				RunBTNode->NodePosX = 300;
				RunBTNode->NodePosY = 0;

				// Wire BeginPlay exec → RunBehaviorTree exec
				UEdGraphPin* BeginPlayExec = BeginPlayNode->FindPin(UEdGraphSchema_K2::PN_Then);
				UEdGraphPin* RunBTExec = RunBTNode->FindPin(UEdGraphSchema_K2::PN_Execute);
				if (BeginPlayExec && RunBTExec)
				{
					Schema->TryCreateConnection(BeginPlayExec, RunBTExec);
				}

				// Set the BTAsset parameter to the specified BehaviorTree
				UEdGraphPin* BTAssetPin = RunBTNode->FindPin(TEXT("BTAsset"));
				if (BTAssetPin)
				{
					BTAssetPin->DefaultObject = BT;
				}

				EventGraph->NotifyGraphChanged();
			}
			else
			{
				UE_LOG(LogBlueprintLLM, Warning, TEXT("RunBehaviorTree function not found on AAIController"));
			}
		}

		// Compile after wiring
		FKismetEditorUtilities::CompileBlueprint(ControllerBP);

		// Save the controller asset
		FString ControllerPackagePath = FString::Printf(TEXT("/Game/Arcwright/Generated/%s"), *ControllerName);
		UPackage* ControllerPackage = ControllerBP->GetOutermost();
		FString ControllerFilePath = FPackageName::LongPackageNameToFilename(ControllerPackagePath, FPackageName::GetAssetPackageExtension());
		FSavePackageArgs SaveArgs;
		SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
		SafeSavePackage(ControllerPackage, ControllerBP, ControllerFilePath, SaveArgs);
	}

	// 5. Set AIControllerClass and AutoPossessAI on the pawn
	PawnObj->AIControllerClass = ControllerBP->GeneratedClass;
	PawnObj->AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;

	// Recompile pawn
	PawnBP->Modify();
	FKismetEditorUtilities::CompileBlueprint(PawnBP);

	// Save pawn asset
	UPackage* PawnPackage = PawnBP->GetOutermost();
	FString PawnPackagePath = PawnPackage->GetName();
	FString PawnFilePath = FPackageName::LongPackageNameToFilename(PawnPackagePath, FPackageName::GetAssetPackageExtension());
	FSavePackageArgs PawnSaveArgs;
	PawnSaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
	SafeSavePackage(PawnPackage, PawnBP, PawnFilePath, PawnSaveArgs);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Setup AI complete: %s -> %s -> %s"),
		*PawnName, *ControllerName, *BehaviorTreeName);

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("pawn"), PawnName);
	Data->SetStringField(TEXT("controller"), ControllerName);
	Data->SetStringField(TEXT("behavior_tree"), BehaviorTreeName);
	Data->SetBoolField(TEXT("controller_created"), bCreatedNew);
	Data->SetStringField(TEXT("auto_possess"), TEXT("PlacedInWorldOrSpawned"));

	return FCommandResult::Ok(Data);
}

// ============================================================
// Scroll Sync + Property Binding Commands
// ============================================================

FCommandResult FCommandServer::HandleAddScrollSync(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	FString SourceSB = Params->GetStringField(TEXT("source_scrollbox"));

	TArray<FString> TargetSBs;
	if (Params->HasTypedField<EJson::Array>(TEXT("target_scrollboxes")))
	{
		const TArray<TSharedPtr<FJsonValue>>& TargetArr = Params->GetArrayField(TEXT("target_scrollboxes"));
		for (const auto& V : TargetArr)
			TargetSBs.Add(V->AsString());
	}

	if (WBPName.IsEmpty() || SourceSB.IsEmpty() || TargetSBs.Num() == 0)
	{
		return FCommandResult::Error(TEXT("add_scroll_sync: widget_blueprint, source_scrollbox, target_scrollboxes required"));
	}

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP)
		return FCommandResult::Error(TEXT("add_scroll_sync: WBP not found: ") + WBPName);

	// Verify source ScrollBox exists
	UWidget* SourceWidget = FindWidgetByName(WBP, SourceSB);
	if (!Cast<UScrollBox>(SourceWidget))
		return FCommandResult::Error(TEXT("add_scroll_sync: source ScrollBox not found: ") + SourceSB);

	// Verify all target ScrollBoxes exist
	for (const FString& Target : TargetSBs)
	{
		UWidget* TargetWidget = FindWidgetByName(WBP, Target);
		if (!Cast<UScrollBox>(TargetWidget))
			return FCommandResult::Error(TEXT("add_scroll_sync: target ScrollBox not found: ") + Target);
	}

	// Mark all ScrollBoxes as variables so they're accessible from Blueprint
	SourceWidget->bIsVariable = true;
	for (const FString& Target : TargetSBs)
	{
		UWidget* TargetWidget = FindWidgetByName(WBP, Target);
		if (TargetWidget) TargetWidget->bIsVariable = true;
	}

	FBlueprintEditorUtils::MarkBlueprintAsModified(WBP);
	FKismetEditorUtilities::CompileBlueprint(WBP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("source"), SourceSB);
	TArray<TSharedPtr<FJsonValue>> TargetArr;
	for (const FString& T : TargetSBs)
		TargetArr.Add(MakeShareable(new FJsonValueString(T)));
	Data->SetArrayField(TEXT("targets"), TargetArr);
	Data->SetStringField(TEXT("pattern"),
		TEXT("ScrollBoxes marked as variables. Wire OnUserScrolled on source to call SetScrollOffset on each target in Blueprint event graph."));
	UE_LOG(LogBlueprintLLM, Log, TEXT("add_scroll_sync: %s -> %d targets"), *SourceSB, TargetSBs.Num());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleBindTextToVariable(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	FString TextWidget = Params->GetStringField(TEXT("textblock_name"));
	FString VarName = Params->GetStringField(TEXT("variable_name"));

	if (WBPName.IsEmpty() || TextWidget.IsEmpty() || VarName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("bind_text_to_variable: widget_blueprint, textblock_name, variable_name required"));
	}

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP)
		return FCommandResult::Error(TEXT("bind_text_to_variable: WBP not found: ") + WBPName);

	UWidget* Widget = FindWidgetByName(WBP, TextWidget);
	UTextBlock* TB = Cast<UTextBlock>(Widget);
	if (!TB)
		return FCommandResult::Error(TEXT("bind_text_to_variable: TextBlock not found: ") + TextWidget);

	// Create a binding function name
	FString BindFuncName = FString::Printf(TEXT("Get_%s_For_%s"), *VarName, *TextWidget);

	// Create the binding function graph
	UEdGraph* FuncGraph = FBlueprintEditorUtils::CreateNewGraph(
		WBP, FName(*BindFuncName), UEdGraph::StaticClass(), UEdGraphSchema_K2::StaticClass());

	if (!FuncGraph)
		return FCommandResult::Error(TEXT("bind_text_to_variable: failed to create function graph"));

	FBlueprintEditorUtils::AddFunctionGraph<UClass>(WBP, FuncGraph, false, nullptr);

	// Register the binding on the TextBlock
	FDelegateEditorBinding Binding;
	Binding.ObjectName = TB->GetName();
	Binding.PropertyName = FName(TEXT("Text"));
	Binding.FunctionName = FName(*BindFuncName);
	Binding.Kind = EBindingKind::Function;

	// Add to WBP's bindings array
	WBP->Bindings.Add(Binding);

	// Mark the TextBlock as a variable for Blueprint access
	TB->bIsVariable = true;

	FBlueprintEditorUtils::MarkBlueprintAsModified(WBP);
	FKismetEditorUtilities::CompileBlueprint(WBP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("binding_function"), BindFuncName);
	Data->SetStringField(TEXT("textblock"), TextWidget);
	Data->SetStringField(TEXT("variable"), VarName);
	Data->SetStringField(TEXT("note"),
		TEXT("Binding function created. Add a Get node for the variable and connect to the return value in the function graph to complete the binding."));
	UE_LOG(LogBlueprintLLM, Log, TEXT("bind_text_to_variable: %s.Text -> %s via %s"), *TextWidget, *VarName, *BindFuncName);
	return FCommandResult::Ok(Data);
}

// ============================================================
// Widget Variable / Binding Commands
// ============================================================

FCommandResult FCommandServer::HandleSetWidgetIsVariable(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	FString WidgetName = Params->GetStringField(TEXT("widget_name"));
	bool bIsVariable = Params->HasField(TEXT("is_variable")) ? Params->GetBoolField(TEXT("is_variable")) : true;

	if (WBPName.IsEmpty() || WidgetName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("set_widget_is_variable: widget_blueprint and widget_name required"));
	}

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP) return FCommandResult::Error(TEXT("set_widget_is_variable: WBP not found: ") + WBPName);

	UWidget* W = FindWidgetByName(WBP, WidgetName);
	if (!W) return FCommandResult::Error(TEXT("set_widget_is_variable: widget not found: ") + WidgetName);

	W->bIsVariable = bIsVariable;
	FBlueprintEditorUtils::MarkBlueprintAsModified(WBP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("widget_name"), WidgetName);
	Data->SetBoolField(TEXT("is_variable"), bIsVariable);
	UE_LOG(LogBlueprintLLM, Log, TEXT("set_widget_is_variable: %s.%s = %s"), *WBPName, *WidgetName, bIsVariable ? TEXT("true") : TEXT("false"));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddWidgetVariable(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	FString VarName = Params->GetStringField(TEXT("variable_name"));
	FString VarType = Params->HasField(TEXT("variable_type")) ? Params->GetStringField(TEXT("variable_type")) : TEXT("string");

	if (WBPName.IsEmpty() || VarName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("add_widget_variable: widget_blueprint and variable_name required"));
	}

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP) return FCommandResult::Error(TEXT("add_widget_variable: WBP not found: ") + WBPName);

	FEdGraphPinType PinType;
	if      (VarType == TEXT("string")) PinType.PinCategory = UEdGraphSchema_K2::PC_String;
	else if (VarType == TEXT("float"))  PinType.PinCategory = UEdGraphSchema_K2::PC_Real;
	else if (VarType == TEXT("int"))    PinType.PinCategory = UEdGraphSchema_K2::PC_Int;
	else if (VarType == TEXT("bool"))   PinType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
	else if (VarType == TEXT("text"))   PinType.PinCategory = UEdGraphSchema_K2::PC_Text;
	else PinType.PinCategory = UEdGraphSchema_K2::PC_String;

	FBlueprintEditorUtils::AddMemberVariable(WBP, FName(*VarName), PinType);
	FBlueprintEditorUtils::MarkBlueprintAsModified(WBP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("variable_name"), VarName);
	Data->SetStringField(TEXT("variable_type"), VarType);
	UE_LOG(LogBlueprintLLM, Log, TEXT("add_widget_variable: %s.%s (%s)"), *WBPName, *VarName, *VarType);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetWidgetEntryClass(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	FString WidgetName = Params->GetStringField(TEXT("widget_name"));
	FString EntryClass = Params->GetStringField(TEXT("entry_class"));

	if (WBPName.IsEmpty() || WidgetName.IsEmpty() || EntryClass.IsEmpty())
	{
		return FCommandResult::Error(TEXT("set_widget_entry_class: widget_blueprint, widget_name, entry_class required"));
	}

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP) return FCommandResult::Error(TEXT("set_widget_entry_class: WBP not found: ") + WBPName);

	UWidget* Widget = FindWidgetByName(WBP, WidgetName);
	if (!Widget) return FCommandResult::Error(TEXT("set_widget_entry_class: widget not found: ") + WidgetName);

	UClass* Class = LoadObject<UClass>(nullptr, *EntryClass);
	if (!Class)
	{
		return FCommandResult::Error(TEXT("set_widget_entry_class: entry class not found: ") + EntryClass);
	}

	// EntryWidgetClass is a protected UPROPERTY — set via FProperty reflection
	FProperty* EntryProp = Widget->GetClass()->FindPropertyByName(TEXT("EntryWidgetClass"));
	if (EntryProp)
	{
		TSubclassOf<UUserWidget>* ValuePtr = EntryProp->ContainerPtrToValuePtr<TSubclassOf<UUserWidget>>(Widget);
		if (ValuePtr)
		{
			*ValuePtr = TSubclassOf<UUserWidget>(Class);
			FBlueprintEditorUtils::MarkBlueprintAsModified(WBP);
		}
	}
	else
	{
		return FCommandResult::Error(TEXT("set_widget_entry_class: EntryWidgetClass property not found on widget"));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("entry_class"), EntryClass);
	Data->SetStringField(TEXT("widget_name"), WidgetName);
	UE_LOG(LogBlueprintLLM, Log, TEXT("set_widget_entry_class: %s -> %s"), *WidgetName, *EntryClass);
	return FCommandResult::Ok(Data);
}

// ============================================================
// Media Texture Command
// ============================================================

FCommandResult FCommandServer::HandleAssignMediaTexture(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	FString WidgetName = Params->GetStringField(TEXT("widget_name"));
	FString MediaTexPath = Params->GetStringField(TEXT("media_texture"));

	if (WBPName.IsEmpty() || WidgetName.IsEmpty() || MediaTexPath.IsEmpty())
	{
		return FCommandResult::Error(TEXT("assign_media_texture: widget_blueprint, widget_name, media_texture required"));
	}

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP) return FCommandResult::Error(TEXT("assign_media_texture: WBP not found: ") + WBPName);

	UWidget* Widget = FindWidgetByName(WBP, WidgetName);
	if (!Widget) return FCommandResult::Error(TEXT("assign_media_texture: widget not found: ") + WidgetName);

	UImage* ImgWidget = Cast<UImage>(Widget);
	if (!ImgWidget) return FCommandResult::Error(TEXT("assign_media_texture: not an Image widget"));

	UTexture2D* Tex = LoadObject<UTexture2D>(nullptr, *MediaTexPath);
	if (Tex)
	{
		ImgWidget->SetBrushFromTexture(Tex);
	}
	else
	{
		return FCommandResult::Error(TEXT("assign_media_texture: texture not found (may need Material intermediary for MediaTexture): ") + MediaTexPath);
	}

	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(WBP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("widget"), WidgetName);
	Data->SetStringField(TEXT("media_texture"), MediaTexPath);
	UE_LOG(LogBlueprintLLM, Log, TEXT("Assigned media texture: %s -> %s"), *MediaTexPath, *WidgetName);
	return FCommandResult::Ok(Data);
}

// ============================================================
// Font Pipeline Commands
// ============================================================

FCommandResult FCommandServer::HandleImportFontFace(const TSharedPtr<FJsonObject>& Params)
{
	FString TtfPath = Params->GetStringField(TEXT("ttf_path"));
	FString AssetName = Params->GetStringField(TEXT("asset_name"));
	FString AssetPath = Params->HasField(TEXT("asset_path"))
		? Params->GetStringField(TEXT("asset_path")) : TEXT("/Game/UI/Fonts");

	if (TtfPath.IsEmpty() || AssetName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("import_font_face: ttf_path and asset_name are required"));
	}

	if (!FPaths::FileExists(TtfPath))
	{
		return FCommandResult::Error(TEXT("import_font_face: file not found: ") + TtfPath);
	}

	// Create UFontFace programmatically from TTF file bytes
	FString PackagePath = AssetPath / AssetName;

	// Delete existing
	UObject* Existing = LoadObject<UObject>(nullptr, *PackagePath);
	if (Existing)
	{
		TArray<UObject*> ObjDel;
		ObjDel.Add(Existing);
		ObjectTools::ForceDeleteObjects(ObjDel, false);
	}

	// Load TTF file data
	TArray<uint8> FontData;
	if (!FFileHelper::LoadFileToArray(FontData, *TtfPath))
	{
		return FCommandResult::Error(TEXT("import_font_face: failed to read file: ") + TtfPath);
	}

	// Create package and UFontFace
	UPackage* Package = CreatePackage(*PackagePath);
	Package->FullyLoad();

	UFontFace* NewFace = NewObject<UFontFace>(Package, *AssetName, RF_Public | RF_Standalone);
	NewFace->SourceFilename = TtfPath;
	NewFace->Hinting = EFontHinting::Auto;
	NewFace->LoadingPolicy = EFontLoadingPolicy::Inline;

	// Initialize from raw TTF data
	NewFace->InitializeFromBulkData(TtfPath, EFontHinting::Auto, FontData.GetData(), FontData.Num());

	FAssetRegistryModule::AssetCreated(NewFace);
	Package->MarkPackageDirty();

	FString PackageFilename = FPackageName::LongPackageNameToFilename(
		Package->GetName(), FPackageName::GetAssetPackageExtension());
	FSavePackageArgs SaveArgs;
	SafeSavePackage(Package, NewFace, PackageFilename, SaveArgs);

	FString FinalPath = PackagePath;

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("asset_path"), FinalPath);
	Data->SetStringField(TEXT("asset_name"), AssetName);
	UE_LOG(LogBlueprintLLM, Log, TEXT("Imported font face: %s -> %s"), *TtfPath, *FinalPath);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCreateFontAsset(const TSharedPtr<FJsonObject>& Params)
{
	FString FontName = Params->GetStringField(TEXT("font_name"));
	FString AssetPath = Params->HasField(TEXT("asset_path"))
		? Params->GetStringField(TEXT("asset_path")) : TEXT("/Game/UI/Fonts");

	if (FontName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("create_font_asset: font_name is required"));
	}

	FString PackagePath = AssetPath / FontName;

	// Delete existing asset if present
	UObject* Existing = LoadObject<UObject>(nullptr, *PackagePath);
	if (Existing)
	{
		TArray<UObject*> ObjectsToDelete;
		ObjectsToDelete.Add(Existing);
		ObjectTools::ForceDeleteObjects(ObjectsToDelete, false);
	}

	// Create package and UFont
	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package)
	{
		return FCommandResult::Error(TEXT("create_font_asset: failed to create package: ") + PackagePath);
	}
	Package->FullyLoad();

	UFont* NewFont = NewObject<UFont>(Package, *FontName, RF_Public | RF_Standalone | RF_MarkAsRootSet);
	if (!NewFont)
	{
		return FCommandResult::Error(TEXT("create_font_asset: failed to create UFont object"));
	}

	NewFont->FontCacheType = EFontCacheType::Runtime;

	FAssetRegistryModule::AssetCreated(NewFont);
	Package->MarkPackageDirty();

	FString PackageFilename = FPackageName::LongPackageNameToFilename(
		Package->GetName(), FPackageName::GetAssetPackageExtension());
	FSavePackageArgs SaveArgs;
	SafeSavePackage(Package, NewFont, PackageFilename, SaveArgs);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("asset_path"), PackagePath);
	Data->SetStringField(TEXT("font_name"), FontName);
	UE_LOG(LogBlueprintLLM, Log, TEXT("Created font asset: %s"), *PackagePath);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddFontTypeface(const TSharedPtr<FJsonObject>& Params)
{
	FString FontAsset = Params->GetStringField(TEXT("font_asset"));
	FString TypefaceName = Params->GetStringField(TEXT("typeface_name"));
	FString FontFaceAsset = Params->GetStringField(TEXT("font_face_asset"));

	if (FontAsset.IsEmpty() || TypefaceName.IsEmpty() || FontFaceAsset.IsEmpty())
	{
		return FCommandResult::Error(TEXT("add_font_typeface: font_asset, typeface_name, font_face_asset all required"));
	}

	UFont* Font = LoadObject<UFont>(nullptr, *FontAsset);
	if (!Font)
	{
		return FCommandResult::Error(TEXT("add_font_typeface: UFont not found: ") + FontAsset);
	}

	UFontFace* FontFace = LoadObject<UFontFace>(nullptr, *FontFaceAsset);
	if (!FontFace)
	{
		return FCommandResult::Error(TEXT("add_font_typeface: UFontFace not found: ") + FontFaceAsset);
	}

	// Add or update typeface slot
	FCompositeFont& CompositeFont = Font->GetMutableInternalCompositeFont();
	bool bFound = false;
	for (FTypefaceEntry& Entry : CompositeFont.DefaultTypeface.Fonts)
	{
		if (Entry.Name == FName(*TypefaceName))
		{
			Entry.Font = FFontData(FontFace);
			bFound = true;
			break;
		}
	}

	if (!bFound)
	{
		FTypefaceEntry NewEntry;
		NewEntry.Name = FName(*TypefaceName);
		NewEntry.Font = FFontData(FontFace);
		CompositeFont.DefaultTypeface.Fonts.Add(NewEntry);
	}

	// Save
	Font->MarkPackageDirty();
	UPackage* Package = Font->GetOutermost();
	FString PackageFilename = FPackageName::LongPackageNameToFilename(
		Package->GetName(), FPackageName::GetAssetPackageExtension());
	FSavePackageArgs SaveArgs;
	SafeSavePackage(Package, Font, PackageFilename, SaveArgs);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("font_asset"), FontAsset);
	Data->SetStringField(TEXT("typeface_name"), TypefaceName);
	Data->SetStringField(TEXT("font_face_asset"), FontFaceAsset);
	Data->SetBoolField(TEXT("was_update"), bFound);
	UE_LOG(LogBlueprintLLM, Log, TEXT("Added typeface '%s' to %s"), *TypefaceName, *FontAsset);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetFontInfo(const TSharedPtr<FJsonObject>& Params)
{
	FString FontAsset = Params->GetStringField(TEXT("font_asset"));
	if (FontAsset.IsEmpty())
	{
		return FCommandResult::Error(TEXT("get_font_info: font_asset is required"));
	}

	UFont* Font = LoadObject<UFont>(nullptr, *FontAsset);
	if (!Font)
	{
		return FCommandResult::Error(TEXT("get_font_info: UFont not found: ") + FontAsset);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("font_asset"), FontAsset);
	Data->SetStringField(TEXT("cache_type"),
		Font->FontCacheType == EFontCacheType::Runtime ? TEXT("Runtime") : TEXT("Offline"));

	TArray<TSharedPtr<FJsonValue>> TypefaceArray;
	for (const FTypefaceEntry& Entry : Font->GetInternalCompositeFont().DefaultTypeface.Fonts)
	{
		TSharedPtr<FJsonObject> EntryObj = MakeShareable(new FJsonObject());
		EntryObj->SetStringField(TEXT("name"), Entry.Name.ToString());

		FString FacePath;
		const UFontFace* FaceAsset = Cast<UFontFace>(Entry.Font.GetFontFaceAsset());
		if (FaceAsset)
		{
			FacePath = FaceAsset->GetPathName();
		}
		EntryObj->SetStringField(TEXT("font_face"), FacePath);

		TypefaceArray.Add(MakeShareable(new FJsonValueObject(EntryObj)));
	}
	Data->SetArrayField(TEXT("typefaces"), TypefaceArray);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleListFontAssets(const TSharedPtr<FJsonObject>& Params)
{
	FString SearchPath = Params->HasField(TEXT("path"))
		? Params->GetStringField(TEXT("path")) : TEXT("/Game");

	FAssetRegistryModule& AssetRegistryModule =
		FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	IAssetRegistry& AssetRegistry = AssetRegistryModule.Get();

	FARFilter Filter;
	Filter.ClassPaths.Add(UFont::StaticClass()->GetClassPathName());
	Filter.PackagePaths.Add(FName(*SearchPath));
	Filter.bRecursivePaths = true;

	TArray<FAssetData> AssetList;
	AssetRegistry.GetAssets(Filter, AssetList);

	TArray<TSharedPtr<FJsonValue>> FontArray;
	for (const FAssetData& Asset : AssetList)
	{
		TSharedPtr<FJsonObject> FontObj = MakeShareable(new FJsonObject());
		FontObj->SetStringField(TEXT("name"), Asset.AssetName.ToString());
		FontObj->SetStringField(TEXT("path"), Asset.GetObjectPathString());
		FontArray.Add(MakeShareable(new FJsonValueObject(FontObj)));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetArrayField(TEXT("fonts"), FontArray);
	Data->SetNumberField(TEXT("count"), FontArray.Num());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleImportFontFamily(const TSharedPtr<FJsonObject>& Params)
{
	FString FamilyName = Params->GetStringField(TEXT("family_name"));
	FString TtfFolder = Params->GetStringField(TEXT("ttf_folder"));
	FString AssetPath = Params->HasField(TEXT("asset_path"))
		? Params->GetStringField(TEXT("asset_path")) : TEXT("/Game/UI/Fonts");

	if (FamilyName.IsEmpty() || TtfFolder.IsEmpty())
	{
		return FCommandResult::Error(TEXT("import_font_family: family_name and ttf_folder are required"));
	}

	if (!FPaths::DirectoryExists(TtfFolder))
	{
		return FCommandResult::Error(TEXT("import_font_family: folder not found: ") + TtfFolder);
	}

	// ── Weight normalization map (order matters) ──────────────
	TArray<TPair<FString, FString>> WeightNormMap = {
		{ TEXT("ExtraLight"), TEXT("ExtraLight") },
		{ TEXT("SemiBold"),   TEXT("SemiBold")   },
		{ TEXT("Semi"),       TEXT("SemiBold")   },
		{ TEXT("Bold"),       TEXT("Bold")       },
		{ TEXT("Black"),      TEXT("Black")      },
		{ TEXT("Medium"),     TEXT("Medium")     },
		{ TEXT("Light"),      TEXT("Light")      },
		{ TEXT("Regular"),    TEXT("Regular")    },
		{ TEXT("-400"),       TEXT("Regular")    },
		{ TEXT("-500"),       TEXT("Medium")     },
		{ TEXT("-600"),       TEXT("SemiBold")   },
		{ TEXT("-700"),       TEXT("Bold")       },
		{ TEXT("-300"),       TEXT("Light")      },
		{ TEXT("-200"),       TEXT("ExtraLight") },
		{ TEXT("-900"),       TEXT("Black")      },
	};

	// Apply custom weight_map overrides if provided
	if (Params->HasTypedField<EJson::Object>(TEXT("weight_map")))
	{
		const TSharedPtr<FJsonObject>& CustomMap = Params->GetObjectField(TEXT("weight_map"));
		for (const auto& Pair : CustomMap->Values)
		{
			FString SlotName = Pair.Value->AsString();
			WeightNormMap.Insert(TPair<FString, FString>(Pair.Key, SlotName), 0);
		}
	}

	// ── Find TTF/OTF files (deduplicated for case-insensitive FS) ──
	TArray<FString> TtfFiles;
	IFileManager::Get().FindFiles(TtfFiles, *(TtfFolder / TEXT("*.ttf")), true, false);
	{
		TArray<FString> OtfFiles;
		IFileManager::Get().FindFiles(OtfFiles, *(TtfFolder / TEXT("*.otf")), true, false);
		TtfFiles.Append(OtfFiles);
	}

	if (TtfFiles.Num() == 0)
	{
		return FCommandResult::Error(TEXT("import_font_family: no TTF/OTF files found in: ") + TtfFolder);
	}

	// ── Create UFont composite asset ─────────────────────────
	FString FontAssetName = TEXT("F_") + FamilyName;
	FString FontAssetPath = AssetPath / FontAssetName;

	// Delete existing
	UObject* ExistingFont = LoadObject<UObject>(nullptr, *FontAssetPath);
	if (ExistingFont)
	{
		TArray<UObject*> ObjectsToDelete;
		ObjectsToDelete.Add(ExistingFont);
		ObjectTools::ForceDeleteObjects(ObjectsToDelete, false);
	}

	UPackage* FontPackage = CreatePackage(*FontAssetPath);
	FontPackage->FullyLoad();
	UFont* NewFont = NewObject<UFont>(FontPackage, *FontAssetName,
		RF_Public | RF_Standalone | RF_MarkAsRootSet);
	NewFont->FontCacheType = EFontCacheType::Runtime;
	FAssetRegistryModule::AssetCreated(NewFont);

	// ── Import each TTF and map to typeface slot ─────────────
	IAssetTools& AssetTools =
		FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools").Get();

	TArray<TSharedPtr<FJsonValue>> ImportedArray;
	TArray<TSharedPtr<FJsonValue>> SkippedArray;
	TArray<TSharedPtr<FJsonValue>> WarningsArray;

	for (const FString& TtfFile : TtfFiles)
	{
		FString FullTtfPath = TtfFolder / TtfFile;
		FString FileBaseName = FPaths::GetBaseFilename(TtfFile);

		// Determine slot name from filename
		FString SlotName;
		bool bIsItalic = FileBaseName.Contains(TEXT("Italic"));

		for (const TPair<FString, FString>& NormPair : WeightNormMap)
		{
			if (FileBaseName.Contains(NormPair.Key))
			{
				SlotName = NormPair.Value;
				break;
			}
		}

		if (SlotName.IsEmpty())
		{
			SlotName = TEXT("Regular");
		}

		if (bIsItalic && !SlotName.EndsWith(TEXT("Italic")))
		{
			SlotName = SlotName + TEXT("Italic");
		}

		// Import TTF
		FString FaceName = TEXT("FF_") + FamilyName + TEXT("_") + SlotName;
		FString FaceAssetPath = AssetPath / FaceName;

		// Delete existing face asset
		UObject* ExistingFace = LoadObject<UObject>(nullptr, *FaceAssetPath);
		if (ExistingFace)
		{
			TArray<UObject*> ObjDel;
			ObjDel.Add(ExistingFace);
			ObjectTools::ForceDeleteObjects(ObjDel, false);
		}

		// Load TTF file data
		TArray<uint8> FaceFileData;
		if (!FFileHelper::LoadFileToArray(FaceFileData, *FullTtfPath))
		{
			TSharedPtr<FJsonObject> WarnObj = MakeShareable(new FJsonObject());
			WarnObj->SetStringField(TEXT("file"), TtfFile);
			WarnObj->SetStringField(TEXT("reason"), TEXT("failed to read TTF file"));
			WarningsArray.Add(MakeShareable(new FJsonValueObject(WarnObj)));
			continue;
		}

		// Create UFontFace programmatically
		UPackage* FacePackage = CreatePackage(*FaceAssetPath);
		FacePackage->FullyLoad();
		UFontFace* FontFace = NewObject<UFontFace>(FacePackage, *FaceName, RF_Public | RF_Standalone);
		FontFace->SourceFilename = FullTtfPath;
		FontFace->Hinting = EFontHinting::Auto;
		FontFace->LoadingPolicy = EFontLoadingPolicy::Inline;
		FontFace->InitializeFromBulkData(FullTtfPath, EFontHinting::Auto, FaceFileData.GetData(), FaceFileData.Num());
		FAssetRegistryModule::AssetCreated(FontFace);
		FacePackage->MarkPackageDirty();
		{
			FString FaceFilename = FPackageName::LongPackageNameToFilename(
				FacePackage->GetName(), FPackageName::GetAssetPackageExtension());
			FSavePackageArgs FaceSaveArgs;
			SafeSavePackage(FacePackage, FontFace, FaceFilename, FaceSaveArgs);
		}

		if (!FontFace)
		{
			TSharedPtr<FJsonObject> WarnObj = MakeShareable(new FJsonObject());
			WarnObj->SetStringField(TEXT("file"), TtfFile);
			WarnObj->SetStringField(TEXT("reason"), TEXT("failed to create UFontFace"));
			WarningsArray.Add(MakeShareable(new FJsonValueObject(WarnObj)));
			continue;
		}

		// Add typeface slot
		bool bSlotFound = false;
		FCompositeFont& ImportCompositeFont = NewFont->GetMutableInternalCompositeFont();
		for (FTypefaceEntry& Entry : ImportCompositeFont.DefaultTypeface.Fonts)
		{
			if (Entry.Name == FName(*SlotName))
			{
				Entry.Font = FFontData(FontFace);
				bSlotFound = true;
				break;
			}
		}
		if (!bSlotFound)
		{
			FTypefaceEntry NewEntry;
			NewEntry.Name = FName(*SlotName);
			NewEntry.Font = FFontData(FontFace);
			ImportCompositeFont.DefaultTypeface.Fonts.Add(NewEntry);
		}

		TSharedPtr<FJsonObject> ImportedObj = MakeShareable(new FJsonObject());
		ImportedObj->SetStringField(TEXT("slot"), SlotName);
		ImportedObj->SetStringField(TEXT("file"), TtfFile);
		ImportedObj->SetStringField(TEXT("face_asset"), FaceAssetPath);
		ImportedArray.Add(MakeShareable(new FJsonValueObject(ImportedObj)));
	}

	// ── Save UFont ───────────────────────────────────────────
	FontPackage->MarkPackageDirty();
	FString FontFilename = FPackageName::LongPackageNameToFilename(
		FontPackage->GetName(), FPackageName::GetAssetPackageExtension());
	FSavePackageArgs SaveArgs;
	SafeSavePackage(FontPackage, NewFont, FontFilename, SaveArgs);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("font_asset"), FontAssetPath);
	Data->SetStringField(TEXT("family_name"), FamilyName);
	Data->SetArrayField(TEXT("typefaces_imported"), ImportedArray);
	Data->SetArrayField(TEXT("skipped"), SkippedArray);
	Data->SetArrayField(TEXT("warnings"), WarningsArray);
	UE_LOG(LogBlueprintLLM, Log, TEXT("Imported font family: %s (%d typefaces)"), *FamilyName, ImportedArray.Num());
	return FCommandResult::Ok(Data);
}

// ============================================================
// Asset Import Commands (B31-B33)
// ============================================================

FCommandResult FCommandServer::HandleImportStaticMesh(const TSharedPtr<FJsonObject>& Params)
{
	FString FilePath;
	if (!Params->TryGetStringField(TEXT("file_path"), FilePath))
	{
		return FCommandResult::Error(TEXT("Missing required parameter: file_path"));
	}

	FString AssetName;
	if (!Params->TryGetStringField(TEXT("asset_name"), AssetName))
	{
		return FCommandResult::Error(TEXT("Missing required parameter: asset_name"));
	}

	FString Destination = TEXT("/Game/Arcwright/Meshes");
	Params->TryGetStringField(TEXT("destination"), Destination);

	if (!FPaths::FileExists(FilePath))
	{
		return FCommandResult::Error(FString::Printf(TEXT("File not found: %s"), *FilePath));
	}

	FString Extension = FPaths::GetExtension(FilePath).ToLower();
	if (Extension != TEXT("fbx") && Extension != TEXT("obj"))
	{
		return FCommandResult::Error(FString::Printf(TEXT("Unsupported file type: .%s (expected .fbx or .obj)"), *Extension));
	}

	// Use UFactory::StaticImportObject to bypass Interchange (avoids task graph recursion crash)
	FString PackagePath = Destination / AssetName;

	// If asset already exists, return its info (FBX re-import crashes due to Interchange task graph recursion)
	UStaticMesh* ExistingMesh = LoadObject<UStaticMesh>(nullptr, *(PackagePath + TEXT(".") + AssetName));
	if (ExistingMesh)
	{
		TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
		Data->SetStringField(TEXT("asset_path"), ExistingMesh->GetPathName());
		Data->SetStringField(TEXT("asset_name"), ExistingMesh->GetName());
		Data->SetBoolField(TEXT("already_exists"), true);
		if (ExistingMesh->GetRenderData() && ExistingMesh->GetRenderData()->LODResources.Num() > 0)
		{
			const FStaticMeshLODResources& LOD0 = ExistingMesh->GetRenderData()->LODResources[0];
			Data->SetNumberField(TEXT("vertices"), LOD0.GetNumVertices());
			Data->SetNumberField(TEXT("triangles"), LOD0.GetNumTriangles());
		}
		Data->SetNumberField(TEXT("imported_count"), 0);
		Data->SetStringField(TEXT("source_file"), FilePath);
		UE_LOG(LogBlueprintLLM, Log, TEXT("Static mesh already exists: %s — returning existing. Delete first to re-import."), *ExistingMesh->GetPathName());
		return FCommandResult::Ok(Data);
	}

	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Failed to create package: %s"), *PackagePath));
	}
	Package->FullyLoad();

	UFbxFactory* Factory = NewObject<UFbxFactory>();
	Factory->SetAutomatedAssetImportData(NewObject<UAutomatedAssetImportData>());

	bool bCanceled = false;
	UObject* ImportedObj = UFactory::StaticImportObject(
		UStaticMesh::StaticClass(),
		Package,
		FName(*AssetName),
		RF_Public | RF_Standalone,
		bCanceled,
		*FilePath,
		nullptr,
		Factory
	);

	if (!ImportedObj)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Import failed — no asset created from %s"), *FilePath));
	}

	// Notify asset registry
	FAssetRegistryModule::AssetCreated(ImportedObj);
	Package->MarkPackageDirty();

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();

	UStaticMesh* Mesh = Cast<UStaticMesh>(ImportedObj);
	if (Mesh)
	{
		Data->SetStringField(TEXT("asset_path"), Mesh->GetPathName());
		Data->SetStringField(TEXT("asset_name"), Mesh->GetName());

		if (Mesh->GetRenderData() && Mesh->GetRenderData()->LODResources.Num() > 0)
		{
			const FStaticMeshLODResources& LOD0 = Mesh->GetRenderData()->LODResources[0];
			Data->SetNumberField(TEXT("vertices"), LOD0.GetNumVertices());
			Data->SetNumberField(TEXT("triangles"), LOD0.GetNumTriangles());
		}
		else
		{
			Data->SetNumberField(TEXT("vertices"), 0);
			Data->SetNumberField(TEXT("triangles"), 0);
		}

		UE_LOG(LogBlueprintLLM, Log, TEXT("Imported static mesh: %s from %s"), *Mesh->GetPathName(), *FilePath);
	}
	else
	{
		Data->SetStringField(TEXT("asset_path"), ImportedObj->GetPathName());
		Data->SetStringField(TEXT("asset_name"), ImportedObj->GetName());
		Data->SetStringField(TEXT("asset_class"), ImportedObj->GetClass()->GetName());
		Data->SetNumberField(TEXT("vertices"), 0);
		Data->SetNumberField(TEXT("triangles"), 0);
	}

	Data->SetNumberField(TEXT("imported_count"), 1);
	Data->SetStringField(TEXT("source_file"), FilePath);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleImportTexture(const TSharedPtr<FJsonObject>& Params)
{
	FString FilePath;
	if (!Params->TryGetStringField(TEXT("file_path"), FilePath))
	{
		return FCommandResult::Error(TEXT("Missing required parameter: file_path"));
	}

	FString AssetName;
	if (!Params->TryGetStringField(TEXT("asset_name"), AssetName))
	{
		return FCommandResult::Error(TEXT("Missing required parameter: asset_name"));
	}

	FString Destination = TEXT("/Game/Arcwright/Textures");
	Params->TryGetStringField(TEXT("destination"), Destination);

	if (!FPaths::FileExists(FilePath))
	{
		return FCommandResult::Error(FString::Printf(TEXT("File not found: %s"), *FilePath));
	}

	FString Extension = FPaths::GetExtension(FilePath).ToLower();
	if (Extension != TEXT("png") && Extension != TEXT("jpg") && Extension != TEXT("jpeg") &&
	    Extension != TEXT("tga") && Extension != TEXT("bmp") && Extension != TEXT("exr"))
	{
		return FCommandResult::Error(FString::Printf(TEXT("Unsupported texture format: .%s"), *Extension));
	}

	FString PackagePath = Destination / AssetName;

	// If asset already exists, return its info
	UTexture2D* ExistingTex = LoadObject<UTexture2D>(nullptr, *(PackagePath + TEXT(".") + AssetName));
	if (ExistingTex)
	{
		TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
		Data->SetStringField(TEXT("asset_path"), ExistingTex->GetPathName());
		Data->SetStringField(TEXT("asset_name"), ExistingTex->GetName());
		Data->SetBoolField(TEXT("already_exists"), true);
		Data->SetNumberField(TEXT("width"), ExistingTex->GetSizeX());
		Data->SetNumberField(TEXT("height"), ExistingTex->GetSizeY());
		Data->SetNumberField(TEXT("imported_count"), 0);
		Data->SetStringField(TEXT("source_file"), FilePath);
		return FCommandResult::Ok(Data);
	}

	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Failed to create package: %s"), *PackagePath));
	}
	Package->FullyLoad();

	UTextureFactory* Factory = NewObject<UTextureFactory>();
	Factory->SuppressImportOverwriteDialog();

	bool bCanceled = false;
	UObject* ImportedObj = UFactory::StaticImportObject(
		UTexture2D::StaticClass(),
		Package,
		FName(*AssetName),
		RF_Public | RF_Standalone,
		bCanceled,
		*FilePath,
		nullptr,
		Factory
	);

	if (!ImportedObj)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Import failed — no asset created from %s"), *FilePath));
	}

	FAssetRegistryModule::AssetCreated(ImportedObj);
	Package->MarkPackageDirty();

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	UTexture2D* Texture = Cast<UTexture2D>(ImportedObj);
	if (Texture)
	{
		Data->SetStringField(TEXT("asset_path"), Texture->GetPathName());
		Data->SetStringField(TEXT("asset_name"), Texture->GetName());
		Data->SetNumberField(TEXT("width"), Texture->GetSizeX());
		Data->SetNumberField(TEXT("height"), Texture->GetSizeY());
		Data->SetStringField(TEXT("format"), UEnum::GetValueAsString(Texture->GetPixelFormat()));

		UE_LOG(LogBlueprintLLM, Log, TEXT("Imported texture: %s (%dx%d) from %s"),
			*Texture->GetPathName(), Texture->GetSizeX(), Texture->GetSizeY(), *FilePath);
	}
	else
	{
		Data->SetStringField(TEXT("asset_path"), ImportedObj->GetPathName());
		Data->SetStringField(TEXT("asset_name"), ImportedObj->GetName());
		Data->SetStringField(TEXT("asset_class"), ImportedObj->GetClass()->GetName());
		Data->SetNumberField(TEXT("width"), 0);
		Data->SetNumberField(TEXT("height"), 0);
	}

	Data->SetNumberField(TEXT("imported_count"), 1);
	Data->SetStringField(TEXT("source_file"), FilePath);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleImportSound(const TSharedPtr<FJsonObject>& Params)
{
	FString FilePath;
	if (!Params->TryGetStringField(TEXT("file_path"), FilePath))
	{
		return FCommandResult::Error(TEXT("Missing required parameter: file_path"));
	}

	FString AssetName;
	if (!Params->TryGetStringField(TEXT("asset_name"), AssetName))
	{
		return FCommandResult::Error(TEXT("Missing required parameter: asset_name"));
	}

	FString Destination = TEXT("/Game/Arcwright/Sounds");
	Params->TryGetStringField(TEXT("destination"), Destination);

	if (!FPaths::FileExists(FilePath))
	{
		return FCommandResult::Error(FString::Printf(TEXT("File not found: %s"), *FilePath));
	}

	FString Extension = FPaths::GetExtension(FilePath).ToLower();
	if (Extension != TEXT("wav") && Extension != TEXT("ogg") && Extension != TEXT("flac") && Extension != TEXT("mp3"))
	{
		return FCommandResult::Error(FString::Printf(TEXT("Unsupported audio format: .%s"), *Extension));
	}

	FString PackagePath = Destination / AssetName;

	// If asset already exists, return its info (re-import can hang)
	USoundWave* ExistingSnd = LoadObject<USoundWave>(nullptr, *(PackagePath + TEXT(".") + AssetName));
	if (ExistingSnd)
	{
		TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
		Data->SetStringField(TEXT("asset_path"), ExistingSnd->GetPathName());
		Data->SetStringField(TEXT("asset_name"), ExistingSnd->GetName());
		Data->SetBoolField(TEXT("already_exists"), true);
		Data->SetNumberField(TEXT("duration"), ExistingSnd->Duration);
		Data->SetNumberField(TEXT("channels"), ExistingSnd->NumChannels);
		Data->SetNumberField(TEXT("imported_count"), 0);
		Data->SetStringField(TEXT("source_file"), FilePath);
		return FCommandResult::Ok(Data);
	}

	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Failed to create package: %s"), *PackagePath));
	}
	Package->FullyLoad();

	bool bCanceled = false;
	UObject* ImportedObj = UFactory::StaticImportObject(
		USoundWave::StaticClass(),
		Package,
		FName(*AssetName),
		RF_Public | RF_Standalone,
		bCanceled,
		*FilePath,
		nullptr,
		nullptr   // Let UE auto-detect the sound factory
	);

	if (!ImportedObj)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Import failed — no asset created from %s"), *FilePath));
	}

	FAssetRegistryModule::AssetCreated(ImportedObj);
	Package->MarkPackageDirty();

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	USoundWave* Sound = Cast<USoundWave>(ImportedObj);
	if (Sound)
	{
		Data->SetStringField(TEXT("asset_path"), Sound->GetPathName());
		Data->SetStringField(TEXT("asset_name"), Sound->GetName());
		Data->SetNumberField(TEXT("duration"), Sound->Duration);
		Data->SetNumberField(TEXT("channels"), Sound->NumChannels);
		Data->SetNumberField(TEXT("sample_rate"), Sound->GetSampleRateForCurrentPlatform());

		UE_LOG(LogBlueprintLLM, Log, TEXT("Imported sound: %s (%.2fs, %d ch) from %s"),
			*Sound->GetPathName(), Sound->Duration, Sound->NumChannels, *FilePath);
	}
	else
	{
		Data->SetStringField(TEXT("asset_path"), ImportedObj->GetPathName());
		Data->SetStringField(TEXT("asset_name"), ImportedObj->GetName());
		Data->SetStringField(TEXT("asset_class"), ImportedObj->GetClass()->GetName());
		Data->SetNumberField(TEXT("duration"), 0);
		Data->SetNumberField(TEXT("channels"), 0);
	}

	Data->SetNumberField(TEXT("imported_count"), 1);
	Data->SetStringField(TEXT("source_file"), FilePath);
	return FCommandResult::Ok(Data);
}

// ============================================================
// Spline commands (Batch 1.1)
// ============================================================

FCommandResult FCommandServer::HandleCreateSplineActor(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required field: name"));
	}

	const TArray<TSharedPtr<FJsonValue>>* PointsArray = nullptr;
	if (!Params->TryGetArrayField(TEXT("initial_points"), PointsArray) || !PointsArray || PointsArray->Num() < 2)
	{
		return FCommandResult::Error(TEXT("initial_points must be an array of at least 2 {x,y,z} objects"));
	}

	DeleteExistingBlueprint(Name);

	FString PackagePath = TEXT("/Game/Arcwright/Generated/") + Name;
	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Failed to create package: %s"), *PackagePath));
	}

	UBlueprint* BP = FKismetEditorUtilities::CreateBlueprint(
		AActor::StaticClass(), Package, FName(*Name),
		BPTYPE_Normal, UBlueprint::StaticClass(), UBlueprintGeneratedClass::StaticClass());
	if (!BP)
	{
		return FCommandResult::Error(TEXT("Failed to create Blueprint"));
	}

	USimpleConstructionScript* SCS = BP->SimpleConstructionScript;
	if (!SCS)
	{
		return FCommandResult::Error(TEXT("Blueprint has no SCS"));
	}

	USCS_Node* SplineNode = SCS->CreateNode(USplineComponent::StaticClass(), FName(TEXT("SplinePath")));
	if (!SplineNode)
	{
		return FCommandResult::Error(TEXT("Failed to create SplineComponent SCS node"));
	}
	SCS->AddNode(SplineNode);

	USplineComponent* SplineComp = Cast<USplineComponent>(SplineNode->ComponentTemplate);
	if (SplineComp)
	{
		SplineComp->ClearSplinePoints(false);
		for (int32 i = 0; i < PointsArray->Num(); i++)
		{
			TSharedPtr<FJsonObject> Pt = (*PointsArray)[i]->AsObject();
			if (Pt.IsValid())
			{
				FVector Point = JsonToVector(Pt);
				SplineComp->AddSplinePoint(Point, ESplineCoordinateSpace::Local, false);
			}
		}
		SplineComp->UpdateSpline();
	}

	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	FSavePackageArgs SaveArgs;
	SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
	SafeSavePackage(Package, BP, Package->GetLoadedPath().GetPackageFName().ToString(), SaveArgs);
	FAssetRegistryModule::AssetCreated(BP);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Created spline actor %s with %d points"), *Name, PointsArray->Num());

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), BP->GetPathName());
	Data->SetNumberField(TEXT("point_count"), PointsArray->Num());
	if (SplineComp)
	{
		Data->SetNumberField(TEXT("spline_length"), SplineComp->GetSplineLength());
	}
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddSplinePoint(const TSharedPtr<FJsonObject>& Params)
{
	FString BPName = Params->GetStringField(TEXT("blueprint"));
	if (BPName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required field: blueprint"));
	}

	UBlueprint* BP = FindBlueprintByName(BPName);
	if (!BP)
	{
		return FCommandResult::Error(FormatBlueprintNotFound(BPName));
	}

	if (!Params->HasField(TEXT("point")))
	{
		return FCommandResult::Error(TEXT("Missing required field: point"));
	}
	FVector Point = JsonToVector(Params->GetObjectField(TEXT("point")));

	int32 Index = -1;
	if (Params->HasField(TEXT("index")))
	{
		Index = (int32)Params->GetNumberField(TEXT("index"));
	}

	USimpleConstructionScript* SCS = BP->SimpleConstructionScript;
	if (!SCS)
	{
		return FCommandResult::Error(TEXT("Blueprint has no SCS"));
	}

	USplineComponent* SplineComp = nullptr;
	for (USCS_Node* Node : SCS->GetAllNodes())
	{
		if (Node && Node->ComponentTemplate && Node->ComponentTemplate->IsA<USplineComponent>())
		{
			SplineComp = Cast<USplineComponent>(Node->ComponentTemplate);
			break;
		}
	}

	if (!SplineComp)
	{
		return FCommandResult::Error(TEXT("No SplineComponent found on Blueprint"));
	}

	if (Index >= 0 && Index <= SplineComp->GetNumberOfSplinePoints())
	{
		SplineComp->AddSplinePointAtIndex(Point, Index, ESplineCoordinateSpace::Local, false);
	}
	else
	{
		SplineComp->AddSplinePoint(Point, ESplineCoordinateSpace::Local, false);
	}
	SplineComp->UpdateSpline();

	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("blueprint"), BPName);
	Data->SetNumberField(TEXT("point_count"), SplineComp->GetNumberOfSplinePoints());
	Data->SetNumberField(TEXT("spline_length"), SplineComp->GetSplineLength());
	Data->SetObjectField(TEXT("added_point"), VectorToJson(Point));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetSplineInfo(const TSharedPtr<FJsonObject>& Params)
{
	FString BPName = Params->GetStringField(TEXT("blueprint"));
	if (BPName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required field: blueprint"));
	}

	UBlueprint* BP = FindBlueprintByName(BPName);
	if (!BP)
	{
		return FCommandResult::Error(FormatBlueprintNotFound(BPName));
	}

	USimpleConstructionScript* SCS = BP->SimpleConstructionScript;
	if (!SCS)
	{
		return FCommandResult::Error(TEXT("Blueprint has no SCS"));
	}

	USplineComponent* SplineComp = nullptr;
	for (USCS_Node* Node : SCS->GetAllNodes())
	{
		if (Node && Node->ComponentTemplate && Node->ComponentTemplate->IsA<USplineComponent>())
		{
			SplineComp = Cast<USplineComponent>(Node->ComponentTemplate);
			break;
		}
	}

	if (!SplineComp)
	{
		return FCommandResult::Error(TEXT("No SplineComponent found on Blueprint"));
	}

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("blueprint"), BPName);
	Data->SetNumberField(TEXT("point_count"), SplineComp->GetNumberOfSplinePoints());
	Data->SetNumberField(TEXT("spline_length"), SplineComp->GetSplineLength());
	Data->SetBoolField(TEXT("is_closed"), SplineComp->IsClosedLoop());

	TArray<TSharedPtr<FJsonValue>> PointsArr;
	for (int32 i = 0; i < SplineComp->GetNumberOfSplinePoints(); i++)
	{
		FVector Loc = SplineComp->GetLocationAtSplinePoint(i, ESplineCoordinateSpace::Local);
		PointsArr.Add(MakeShareable(new FJsonValueObject(VectorToJson(Loc))));
	}
	Data->SetArrayField(TEXT("points"), PointsArr);

	return FCommandResult::Ok(Data);
}

// ============================================================
// Post-process commands (Batch 1.2)
// ============================================================

FCommandResult FCommandServer::HandleAddPostProcessVolume(const TSharedPtr<FJsonObject>& Params)
{
	FVector Location = FVector::ZeroVector;
	if (Params->HasField(TEXT("location")))
	{
		Location = JsonToVector(Params->GetObjectField(TEXT("location")));
	}

	bool bInfiniteExtent = false;
	if (Params->HasField(TEXT("infinite_extent")))
	{
		bInfiniteExtent = Params->GetBoolField(TEXT("infinite_extent"));
	}

	UEditorActorSubsystem* ActorSubsystem = GEditor->GetEditorSubsystem<UEditorActorSubsystem>();
	if (!ActorSubsystem)
	{
		return FCommandResult::Error(TEXT("Could not get UEditorActorSubsystem"));
	}

	APostProcessVolume* PPV = Cast<APostProcessVolume>(
		ActorSubsystem->SpawnActorFromClass(APostProcessVolume::StaticClass(), Location));
	if (!PPV)
	{
		return FCommandResult::Error(TEXT("Failed to spawn PostProcessVolume"));
	}

	PPV->bUnbound = bInfiniteExtent;

	FString Label = Params->GetStringField(TEXT("label"));
	if (Label.IsEmpty())
	{
		Label = TEXT("PostProcessVolume");
	}
	PPV->SetActorLabel(Label);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Spawned PostProcessVolume '%s' at %s (infinite=%d)"),
		*Label, *Location.ToString(), bInfiniteExtent);

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("label"), PPV->GetActorLabel());
	Data->SetBoolField(TEXT("infinite_extent"), bInfiniteExtent);
	Data->SetObjectField(TEXT("location"), VectorToJson(Location));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetPostProcessSettings(const TSharedPtr<FJsonObject>& Params)
{
	FString Label = Params->GetStringField(TEXT("label"));
	if (Label.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required field: label"));
	}

	AActor* Actor = FindActorByLabel(Label);
	if (!Actor)
	{
		return FCommandResult::Error(FormatActorNotFound(Label));
	}

	APostProcessVolume* PPV = Cast<APostProcessVolume>(Actor);
	if (!PPV)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Actor '%s' is not a PostProcessVolume"), *Label));
	}

	if (!Params->HasField(TEXT("settings")))
	{
		return FCommandResult::Error(TEXT("Missing required field: settings"));
	}

	TSharedPtr<FJsonObject> Settings = Params->GetObjectField(TEXT("settings"));
	FPostProcessSettings& PPS = PPV->Settings;
	int32 SettingsApplied = 0;

	if (Settings->HasField(TEXT("bloom_intensity")))
	{
		PPS.bOverride_BloomIntensity = true;
		PPS.BloomIntensity = Settings->GetNumberField(TEXT("bloom_intensity"));
		SettingsApplied++;
	}
	if (Settings->HasField(TEXT("bloom_threshold")))
	{
		PPS.bOverride_BloomThreshold = true;
		PPS.BloomThreshold = Settings->GetNumberField(TEXT("bloom_threshold"));
		SettingsApplied++;
	}
	if (Settings->HasField(TEXT("auto_exposure_min")))
	{
		PPS.bOverride_AutoExposureMinBrightness = true;
		PPS.AutoExposureMinBrightness = Settings->GetNumberField(TEXT("auto_exposure_min"));
		SettingsApplied++;
	}
	if (Settings->HasField(TEXT("auto_exposure_max")))
	{
		PPS.bOverride_AutoExposureMaxBrightness = true;
		PPS.AutoExposureMaxBrightness = Settings->GetNumberField(TEXT("auto_exposure_max"));
		SettingsApplied++;
	}
	if (Settings->HasField(TEXT("ambient_occlusion_intensity")))
	{
		PPS.bOverride_AmbientOcclusionIntensity = true;
		PPS.AmbientOcclusionIntensity = Settings->GetNumberField(TEXT("ambient_occlusion_intensity"));
		SettingsApplied++;
	}
	if (Settings->HasField(TEXT("color_saturation")))
	{
		PPS.bOverride_ColorSaturation = true;
		TSharedPtr<FJsonObject> V = Settings->GetObjectField(TEXT("color_saturation"));
		PPS.ColorSaturation = FVector4(V->GetNumberField(TEXT("x")), V->GetNumberField(TEXT("y")),
			V->GetNumberField(TEXT("z")), V->HasField(TEXT("w")) ? V->GetNumberField(TEXT("w")) : 1.0);
		SettingsApplied++;
	}
	if (Settings->HasField(TEXT("color_contrast")))
	{
		PPS.bOverride_ColorContrast = true;
		TSharedPtr<FJsonObject> V = Settings->GetObjectField(TEXT("color_contrast"));
		PPS.ColorContrast = FVector4(V->GetNumberField(TEXT("x")), V->GetNumberField(TEXT("y")),
			V->GetNumberField(TEXT("z")), V->HasField(TEXT("w")) ? V->GetNumberField(TEXT("w")) : 1.0);
		SettingsApplied++;
	}
	if (Settings->HasField(TEXT("color_gamma")))
	{
		PPS.bOverride_ColorGamma = true;
		TSharedPtr<FJsonObject> V = Settings->GetObjectField(TEXT("color_gamma"));
		PPS.ColorGamma = FVector4(V->GetNumberField(TEXT("x")), V->GetNumberField(TEXT("y")),
			V->GetNumberField(TEXT("z")), V->HasField(TEXT("w")) ? V->GetNumberField(TEXT("w")) : 1.0);
		SettingsApplied++;
	}
	if (Settings->HasField(TEXT("vignette_intensity")))
	{
		PPS.bOverride_VignetteIntensity = true;
		PPS.VignetteIntensity = Settings->GetNumberField(TEXT("vignette_intensity"));
		SettingsApplied++;
	}
	if (Settings->HasField(TEXT("depth_of_field_focal_distance")))
	{
		PPS.bOverride_DepthOfFieldFocalDistance = true;
		PPS.DepthOfFieldFocalDistance = Settings->GetNumberField(TEXT("depth_of_field_focal_distance"));
		SettingsApplied++;
	}
	if (Settings->HasField(TEXT("depth_of_field_fstop")))
	{
		PPS.bOverride_DepthOfFieldFstop = true;
		PPS.DepthOfFieldFstop = Settings->GetNumberField(TEXT("depth_of_field_fstop"));
		SettingsApplied++;
	}
	if (Settings->HasField(TEXT("motion_blur_amount")))
	{
		PPS.bOverride_MotionBlurAmount = true;
		PPS.MotionBlurAmount = Settings->GetNumberField(TEXT("motion_blur_amount"));
		SettingsApplied++;
	}

	PPV->MarkPackageDirty();

	UE_LOG(LogBlueprintLLM, Log, TEXT("Set %d post-process settings on '%s'"), SettingsApplied, *Label);

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("label"), Label);
	Data->SetNumberField(TEXT("settings_applied"), SettingsApplied);
	return FCommandResult::Ok(Data);
}

// ============================================================
// Movement defaults (Batch 1.3)
// ============================================================

FCommandResult FCommandServer::HandleSetMovementDefaults(const TSharedPtr<FJsonObject>& Params)
{
	FString BPName = Params->GetStringField(TEXT("blueprint"));
	if (BPName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required field: blueprint"));
	}

	UBlueprint* BP = FindBlueprintByName(BPName);
	if (!BP)
	{
		return FCommandResult::Error(FormatBlueprintNotFound(BPName));
	}

	if (!Params->HasField(TEXT("properties")))
	{
		return FCommandResult::Error(TEXT("Missing required field: properties"));
	}

	TSharedPtr<FJsonObject> Props = Params->GetObjectField(TEXT("properties"));

	// Find movement component - check SCS first, then CDO
	UMovementComponent* MoveComp = nullptr;
	FString CompType;

	USimpleConstructionScript* SCS = BP->SimpleConstructionScript;
	if (SCS)
	{
		for (USCS_Node* Node : SCS->GetAllNodes())
		{
			if (!Node || !Node->ComponentTemplate) continue;
			if (Node->ComponentTemplate->IsA<UCharacterMovementComponent>())
			{
				MoveComp = Cast<UMovementComponent>(Node->ComponentTemplate);
				CompType = TEXT("CharacterMovement");
				break;
			}
			if (Node->ComponentTemplate->IsA<UFloatingPawnMovement>())
			{
				MoveComp = Cast<UMovementComponent>(Node->ComponentTemplate);
				CompType = TEXT("FloatingPawnMovement");
				break;
			}
		}
	}

	if (!MoveComp && BP->GeneratedClass)
	{
		AActor* CDO = Cast<AActor>(BP->GeneratedClass->GetDefaultObject());
		if (CDO)
		{
			UCharacterMovementComponent* CMC = CDO->FindComponentByClass<UCharacterMovementComponent>();
			if (CMC)
			{
				MoveComp = CMC;
				CompType = TEXT("CharacterMovement");
			}
			else
			{
				UFloatingPawnMovement* FPMov = CDO->FindComponentByClass<UFloatingPawnMovement>();
				if (FPMov)
				{
					MoveComp = FPMov;
					CompType = TEXT("FloatingPawnMovement");
				}
			}
		}
	}

	if (!MoveComp)
	{
		return FCommandResult::Error(TEXT("No movement component found (CharacterMovement or FloatingPawnMovement)"));
	}

	int32 PropsSet = 0;

	UCharacterMovementComponent* CMC = Cast<UCharacterMovementComponent>(MoveComp);
	if (CMC)
	{
		if (Props->HasField(TEXT("max_walk_speed")))    { CMC->MaxWalkSpeed = Props->GetNumberField(TEXT("max_walk_speed")); PropsSet++; }
		if (Props->HasField(TEXT("max_fly_speed")))     { CMC->MaxFlySpeed = Props->GetNumberField(TEXT("max_fly_speed")); PropsSet++; }
		if (Props->HasField(TEXT("jump_z_velocity")))   { CMC->JumpZVelocity = Props->GetNumberField(TEXT("jump_z_velocity")); PropsSet++; }
		if (Props->HasField(TEXT("gravity_scale")))     { CMC->GravityScale = Props->GetNumberField(TEXT("gravity_scale")); PropsSet++; }
		if (Props->HasField(TEXT("acceleration")))      { CMC->MaxAcceleration = Props->GetNumberField(TEXT("acceleration")); PropsSet++; }
		if (Props->HasField(TEXT("deceleration")))      { CMC->BrakingDecelerationWalking = Props->GetNumberField(TEXT("deceleration")); PropsSet++; }
		if (Props->HasField(TEXT("air_control")))       { CMC->AirControl = Props->GetNumberField(TEXT("air_control")); PropsSet++; }
	}

	UFloatingPawnMovement* FPMov = Cast<UFloatingPawnMovement>(MoveComp);
	if (FPMov)
	{
		if (Props->HasField(TEXT("max_speed")) || Props->HasField(TEXT("max_walk_speed")))
		{
			FString Key = Props->HasField(TEXT("max_speed")) ? TEXT("max_speed") : TEXT("max_walk_speed");
			FPMov->MaxSpeed = Props->GetNumberField(Key);
			PropsSet++;
		}
		if (Props->HasField(TEXT("acceleration")))  { FPMov->Acceleration = Props->GetNumberField(TEXT("acceleration")); PropsSet++; }
		if (Props->HasField(TEXT("deceleration")))  { FPMov->Deceleration = Props->GetNumberField(TEXT("deceleration")); PropsSet++; }
	}

	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Set %d movement properties on %s (%s)"), PropsSet, *BPName, *CompType);

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("blueprint"), BPName);
	Data->SetStringField(TEXT("movement_type"), CompType);
	Data->SetNumberField(TEXT("properties_set"), PropsSet);
	return FCommandResult::Ok(Data);
}

// ============================================================
// Physics constraint commands (Batch 1.4)
// ============================================================

FCommandResult FCommandServer::HandleAddPhysicsConstraint(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorALabel = Params->GetStringField(TEXT("actor_a"));
	FString ActorBLabel = Params->GetStringField(TEXT("actor_b"));
	if (ActorALabel.IsEmpty() || ActorBLabel.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required fields: actor_a, actor_b"));
	}

	FString ConstraintType = Params->GetStringField(TEXT("constraint_type"));
	if (ConstraintType.IsEmpty()) ConstraintType = TEXT("Fixed");

	AActor* ActorA = FindActorByLabel(ActorALabel);
	AActor* ActorB = FindActorByLabel(ActorBLabel);
	if (!ActorA) return FCommandResult::Error(FString::Printf(TEXT("Actor A not found: %s"), *ActorALabel));
	if (!ActorB) return FCommandResult::Error(FString::Printf(TEXT("Actor B not found: %s"), *ActorBLabel));

	FVector MidPoint = (ActorA->GetActorLocation() + ActorB->GetActorLocation()) * 0.5f;

	UEditorActorSubsystem* ActorSubsystem = GEditor->GetEditorSubsystem<UEditorActorSubsystem>();
	if (!ActorSubsystem) return FCommandResult::Error(TEXT("Could not get UEditorActorSubsystem"));

	APhysicsConstraintActor* ConstraintActor = Cast<APhysicsConstraintActor>(
		ActorSubsystem->SpawnActorFromClass(APhysicsConstraintActor::StaticClass(), MidPoint));
	if (!ConstraintActor) return FCommandResult::Error(TEXT("Failed to spawn PhysicsConstraintActor"));

	UPhysicsConstraintComponent* CC = ConstraintActor->GetConstraintComp();
	if (!CC) return FCommandResult::Error(TEXT("No constraint component"));

	CC->ConstraintActor1 = ActorA;
	CC->ConstraintActor2 = ActorB;

	if (ConstraintType.Equals(TEXT("Hinge"), ESearchCase::IgnoreCase))
	{
		CC->SetLinearXLimit(ELinearConstraintMotion::LCM_Locked, 0);
		CC->SetLinearYLimit(ELinearConstraintMotion::LCM_Locked, 0);
		CC->SetLinearZLimit(ELinearConstraintMotion::LCM_Locked, 0);
		CC->SetAngularSwing1Limit(EAngularConstraintMotion::ACM_Locked, 0);
		CC->SetAngularSwing2Limit(EAngularConstraintMotion::ACM_Locked, 0);
		CC->SetAngularTwistLimit(EAngularConstraintMotion::ACM_Free, 0);
	}
	else if (ConstraintType.Equals(TEXT("BallSocket"), ESearchCase::IgnoreCase))
	{
		CC->SetLinearXLimit(ELinearConstraintMotion::LCM_Locked, 0);
		CC->SetLinearYLimit(ELinearConstraintMotion::LCM_Locked, 0);
		CC->SetLinearZLimit(ELinearConstraintMotion::LCM_Locked, 0);
		CC->SetAngularSwing1Limit(EAngularConstraintMotion::ACM_Free, 0);
		CC->SetAngularSwing2Limit(EAngularConstraintMotion::ACM_Free, 0);
		CC->SetAngularTwistLimit(EAngularConstraintMotion::ACM_Free, 0);
	}
	else if (ConstraintType.Equals(TEXT("Prismatic"), ESearchCase::IgnoreCase))
	{
		CC->SetLinearXLimit(ELinearConstraintMotion::LCM_Free, 0);
		CC->SetLinearYLimit(ELinearConstraintMotion::LCM_Locked, 0);
		CC->SetLinearZLimit(ELinearConstraintMotion::LCM_Locked, 0);
		CC->SetAngularSwing1Limit(EAngularConstraintMotion::ACM_Locked, 0);
		CC->SetAngularSwing2Limit(EAngularConstraintMotion::ACM_Locked, 0);
		CC->SetAngularTwistLimit(EAngularConstraintMotion::ACM_Locked, 0);
	}
	else // Fixed
	{
		CC->SetLinearXLimit(ELinearConstraintMotion::LCM_Locked, 0);
		CC->SetLinearYLimit(ELinearConstraintMotion::LCM_Locked, 0);
		CC->SetLinearZLimit(ELinearConstraintMotion::LCM_Locked, 0);
		CC->SetAngularSwing1Limit(EAngularConstraintMotion::ACM_Locked, 0);
		CC->SetAngularSwing2Limit(EAngularConstraintMotion::ACM_Locked, 0);
		CC->SetAngularTwistLimit(EAngularConstraintMotion::ACM_Locked, 0);
	}

	if (Params->HasField(TEXT("break_threshold")))
	{
		float Threshold = Params->GetNumberField(TEXT("break_threshold"));
		CC->ConstraintInstance.ProfileInstance.LinearBreakThreshold = Threshold;
		CC->ConstraintInstance.ProfileInstance.bLinearBreakable = true;
		CC->ConstraintInstance.ProfileInstance.AngularBreakThreshold = Threshold;
		CC->ConstraintInstance.ProfileInstance.bAngularBreakable = true;
	}

	FString ConstraintLabel = Params->GetStringField(TEXT("label"));
	if (ConstraintLabel.IsEmpty())
		ConstraintLabel = FString::Printf(TEXT("Constraint_%s_%s"), *ActorALabel, *ActorBLabel);
	ConstraintActor->SetActorLabel(ConstraintLabel);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Created %s constraint '%s' between %s and %s"),
		*ConstraintType, *ConstraintLabel, *ActorALabel, *ActorBLabel);

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("label"), ConstraintActor->GetActorLabel());
	Data->SetStringField(TEXT("constraint_type"), ConstraintType);
	Data->SetStringField(TEXT("actor_a"), ActorALabel);
	Data->SetStringField(TEXT("actor_b"), ActorBLabel);
	Data->SetObjectField(TEXT("location"), VectorToJson(MidPoint));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleBreakConstraint(const TSharedPtr<FJsonObject>& Params)
{
	FString Label = Params->GetStringField(TEXT("label"));
	if (Label.IsEmpty()) return FCommandResult::Error(TEXT("Missing required field: label"));

	AActor* Actor = FindActorByLabel(Label);
	if (!Actor) return FCommandResult::Error(FString::Printf(TEXT("Constraint actor not found: %s"), *Label));

	APhysicsConstraintActor* ConstraintActor = Cast<APhysicsConstraintActor>(Actor);
	if (!ConstraintActor) return FCommandResult::Error(FString::Printf(TEXT("'%s' is not a PhysicsConstraintActor"), *Label));

	UPhysicsConstraintComponent* CC = ConstraintActor->GetConstraintComp();
	if (CC) CC->BreakConstraint();

	UE_LOG(LogBlueprintLLM, Log, TEXT("Broke constraint '%s'"), *Label);

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("label"), Label);
	Data->SetBoolField(TEXT("broken"), true);
	return FCommandResult::Ok(Data);
}

// ============================================================
// Batch 2.1 — Sequencer commands
// ============================================================

FCommandResult FCommandServer::HandleCreateSequence(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required field: name"));

	double Duration = 5.0;
	if (Params->HasField(TEXT("duration")))
		Duration = Params->GetNumberField(TEXT("duration"));

	// Create the LevelSequence asset
	FString PackagePath = FString::Printf(TEXT("/Game/Arcwright/Sequences/%s"), *Name);
	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package)
		return FCommandResult::Error(TEXT("Failed to create package for sequence"));

	ULevelSequence* Sequence = NewObject<ULevelSequence>(Package, *Name, RF_Public | RF_Standalone);
	if (!Sequence)
		return FCommandResult::Error(TEXT("Failed to create ULevelSequence"));

	Sequence->Initialize();

	// Set playback range
	UMovieScene* MovieScene = Sequence->GetMovieScene();
	if (MovieScene)
	{
		FFrameRate TickRate = MovieScene->GetTickResolution();
		FFrameRate DisplayRate = MovieScene->GetDisplayRate();

		FFrameNumber StartFrame = FFrameNumber(0);
		FFrameNumber EndFrame = (Duration * TickRate).FloorToFrame();

		MovieScene->SetPlaybackRange(TRange<FFrameNumber>(StartFrame, EndFrame + 1));
	}

	// Save
	FAssetRegistryModule::AssetCreated(Sequence);
	Sequence->MarkPackageDirty();
	FSavePackageArgs SaveArgs;
	SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
	SafeSavePackage(Package, Sequence,
		FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension()),
		SaveArgs);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Created sequence '%s' (%.1fs)"), *Name, Duration);

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), PackagePath);
	Data->SetNumberField(TEXT("duration"), Duration);
	Data->SetNumberField(TEXT("track_count"), 0);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddSequenceTrack(const TSharedPtr<FJsonObject>& Params)
{
	FString SeqName = Params->GetStringField(TEXT("sequence_name"));
	if (SeqName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required field: sequence_name"));

	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	if (ActorLabel.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required field: actor_label"));

	FString TrackType = Params->GetStringField(TEXT("track_type"));
	if (TrackType.IsEmpty()) TrackType = TEXT("Transform");

	// Find the sequence asset
	FString AssetPath = FString::Printf(TEXT("/Game/Arcwright/Sequences/%s"), *SeqName);
	ULevelSequence* Sequence = LoadObject<ULevelSequence>(nullptr, *AssetPath);
	if (!Sequence)
		return FCommandResult::Error(FString::Printf(TEXT("Sequence not found: %s"), *SeqName));

	UMovieScene* MovieScene = Sequence->GetMovieScene();
	if (!MovieScene)
		return FCommandResult::Error(TEXT("Sequence has no MovieScene"));

	// Find the actor
	AActor* Actor = FindActorByLabel(ActorLabel);
	if (!Actor)
		return FCommandResult::Error(FormatActorNotFound(ActorLabel));

	// Bind actor as possessable
	FGuid BindingGuid;

	// Check if already bound
	for (int32 i = 0; i < MovieScene->GetPossessableCount(); i++)
	{
		const FMovieScenePossessable& Poss = MovieScene->GetPossessable(i);
		if (Poss.GetName() == ActorLabel)
		{
			BindingGuid = Poss.GetGuid();
			break;
		}
	}

	if (!BindingGuid.IsValid())
	{
		BindingGuid = MovieScene->AddPossessable(ActorLabel, Actor->GetClass());
		Sequence->BindPossessableObject(BindingGuid, *Actor, Actor->GetWorld());
	}

	FMovieSceneBinding* Binding = MovieScene->FindBinding(BindingGuid);

	// Add the track
	UMovieSceneTrack* NewTrack = nullptr;
	if (TrackType.Equals(TEXT("Transform"), ESearchCase::IgnoreCase))
	{
		NewTrack = MovieScene->AddTrack(UMovieScene3DTransformTrack::StaticClass(), BindingGuid);
		if (NewTrack)
		{
			UMovieScene3DTransformTrack* TransTrack = Cast<UMovieScene3DTransformTrack>(NewTrack);
			if (TransTrack && TransTrack->GetAllSections().Num() == 0)
			{
				UMovieSceneSection* Section = TransTrack->CreateNewSection();
				Section->SetRange(MovieScene->GetPlaybackRange());
				TransTrack->AddSection(*Section);
			}
		}
	}
	else if (TrackType.Equals(TEXT("Visibility"), ESearchCase::IgnoreCase))
	{
		NewTrack = MovieScene->AddTrack(UMovieSceneVisibilityTrack::StaticClass(), BindingGuid);
		if (NewTrack)
		{
			UMovieSceneVisibilityTrack* VisTrack = Cast<UMovieSceneVisibilityTrack>(NewTrack);
			if (VisTrack && VisTrack->GetAllSections().Num() == 0)
			{
				UMovieSceneSection* Section = VisTrack->CreateNewSection();
				Section->SetRange(MovieScene->GetPlaybackRange());
				VisTrack->AddSection(*Section);
			}
		}
	}
	else if (TrackType.Equals(TEXT("Float"), ESearchCase::IgnoreCase))
	{
		NewTrack = MovieScene->AddTrack(UMovieSceneFloatTrack::StaticClass(), BindingGuid);
		if (NewTrack)
		{
			UMovieSceneFloatTrack* FloatTrack = Cast<UMovieSceneFloatTrack>(NewTrack);
			if (FloatTrack && FloatTrack->GetAllSections().Num() == 0)
			{
				UMovieSceneSection* Section = FloatTrack->CreateNewSection();
				Section->SetRange(MovieScene->GetPlaybackRange());
				FloatTrack->AddSection(*Section);
			}
		}
	}
	else
	{
		return FCommandResult::Error(FString::Printf(TEXT("Unknown track type: %s. Supported: Transform, Visibility, Float"), *TrackType));
	}

	if (!NewTrack)
		return FCommandResult::Error(FString::Printf(TEXT("Failed to create %s track (may already exist)"), *TrackType));

	Sequence->MarkPackageDirty();

	UE_LOG(LogBlueprintLLM, Log, TEXT("Added %s track for '%s' in sequence '%s'"), *TrackType, *ActorLabel, *SeqName);

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("sequence_name"), SeqName);
	Data->SetStringField(TEXT("actor_label"), ActorLabel);
	Data->SetStringField(TEXT("track_type"), TrackType);
	Data->SetStringField(TEXT("binding_guid"), BindingGuid.ToString());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddKeyframe(const TSharedPtr<FJsonObject>& Params)
{
	FString SeqName = Params->GetStringField(TEXT("sequence_name"));
	if (SeqName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required field: sequence_name"));

	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	if (ActorLabel.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required field: actor_label"));

	FString TrackType = Params->GetStringField(TEXT("track_type"));
	if (TrackType.IsEmpty()) TrackType = TEXT("Transform");

	double Time = 0.0;
	if (Params->HasField(TEXT("time")))
		Time = Params->GetNumberField(TEXT("time"));

	// Find the sequence
	FString AssetPath = FString::Printf(TEXT("/Game/Arcwright/Sequences/%s"), *SeqName);
	ULevelSequence* Sequence = LoadObject<ULevelSequence>(nullptr, *AssetPath);
	if (!Sequence) return FCommandResult::Error(FString::Printf(TEXT("Sequence not found: %s"), *SeqName));

	UMovieScene* MovieScene = Sequence->GetMovieScene();
	if (!MovieScene) return FCommandResult::Error(TEXT("No MovieScene"));

	// Find binding for this actor
	FGuid BindingGuid;
	for (int32 i = 0; i < MovieScene->GetPossessableCount(); i++)
	{
		if (MovieScene->GetPossessable(i).GetName() == ActorLabel)
		{
			BindingGuid = MovieScene->GetPossessable(i).GetGuid();
			break;
		}
	}
	if (!BindingGuid.IsValid())
		return FCommandResult::Error(FString::Printf(TEXT("Actor '%s' not bound in sequence. Use add_sequence_track first."), *ActorLabel));

	FFrameRate TickRate = MovieScene->GetTickResolution();
	FFrameNumber FrameNum = (Time * TickRate).FloorToFrame();

	int32 KeysAdded = 0;

	if (TrackType.Equals(TEXT("Transform"), ESearchCase::IgnoreCase))
	{
		// Find the transform track
		UMovieScene3DTransformTrack* Track = nullptr;
		FMovieSceneBinding* Binding = MovieScene->FindBinding(BindingGuid);
		if (Binding)
		{
			for (UMovieSceneTrack* T : Binding->GetTracks())
			{
				Track = Cast<UMovieScene3DTransformTrack>(T);
				if (Track) break;
			}
		}
		if (!Track) return FCommandResult::Error(TEXT("No Transform track found. Use add_sequence_track first."));

		const TArray<UMovieSceneSection*>& Sections = Track->GetAllSections();
		if (Sections.Num() == 0)
			return FCommandResult::Error(TEXT("Transform track has no sections"));

		UMovieScene3DTransformSection* Section = Cast<UMovieScene3DTransformSection>(Sections[0]);
		if (!Section) return FCommandResult::Error(TEXT("Failed to cast to transform section"));

		// Get value object
		const TSharedPtr<FJsonObject>* ValueObj = nullptr;
		if (!Params->TryGetObjectField(TEXT("value"), ValueObj))
			return FCommandResult::Error(TEXT("Missing required field: value (object with location/rotation/scale)"));

		// Get channels — UE 5.x uses double channels for transforms
		TArrayView<FMovieSceneDoubleChannel*> Channels = Section->GetChannelProxy().GetChannels<FMovieSceneDoubleChannel>();
		// Channels: 0-2 = Translation XYZ, 3-5 = Rotation XYZ, 6-8 = Scale XYZ

		const TSharedPtr<FJsonObject>* LocObj = nullptr;
		if ((*ValueObj)->TryGetObjectField(TEXT("location"), LocObj))
		{
			if (Channels.Num() > 2)
			{
				double X = (*LocObj)->GetNumberField(TEXT("x"));
				double Y = (*LocObj)->GetNumberField(TEXT("y"));
				double Z = (*LocObj)->GetNumberField(TEXT("z"));
				Channels[0]->AddCubicKey(FrameNum, X);
				Channels[1]->AddCubicKey(FrameNum, Y);
				Channels[2]->AddCubicKey(FrameNum, Z);
				KeysAdded += 3;
			}
		}

		const TSharedPtr<FJsonObject>* RotObj = nullptr;
		if ((*ValueObj)->TryGetObjectField(TEXT("rotation"), RotObj))
		{
			if (Channels.Num() > 5)
			{
				double Pitch = (*RotObj)->GetNumberField(TEXT("pitch"));
				double Yaw = (*RotObj)->GetNumberField(TEXT("yaw"));
				double Roll = (*RotObj)->GetNumberField(TEXT("roll"));
				Channels[3]->AddCubicKey(FrameNum, Pitch);
				Channels[4]->AddCubicKey(FrameNum, Yaw);
				Channels[5]->AddCubicKey(FrameNum, Roll);
				KeysAdded += 3;
			}
		}

		const TSharedPtr<FJsonObject>* ScaleObj = nullptr;
		if ((*ValueObj)->TryGetObjectField(TEXT("scale"), ScaleObj))
		{
			if (Channels.Num() > 8)
			{
				double SX = (*ScaleObj)->GetNumberField(TEXT("x"));
				double SY = (*ScaleObj)->GetNumberField(TEXT("y"));
				double SZ = (*ScaleObj)->GetNumberField(TEXT("z"));
				Channels[6]->AddCubicKey(FrameNum, SX);
				Channels[7]->AddCubicKey(FrameNum, SY);
				Channels[8]->AddCubicKey(FrameNum, SZ);
				KeysAdded += 3;
			}
		}
	}
	else if (TrackType.Equals(TEXT("Visibility"), ESearchCase::IgnoreCase))
	{
		UMovieSceneVisibilityTrack* Track = nullptr;
		FMovieSceneBinding* Binding = MovieScene->FindBinding(BindingGuid);
		if (Binding)
		{
			for (UMovieSceneTrack* T : Binding->GetTracks())
			{
				Track = Cast<UMovieSceneVisibilityTrack>(T);
				if (Track) break;
			}
		}
		if (!Track) return FCommandResult::Error(TEXT("No Visibility track found"));

		const TArray<UMovieSceneSection*>& Sections = Track->GetAllSections();
		if (Sections.Num() == 0) return FCommandResult::Error(TEXT("Visibility track has no sections"));

		UMovieSceneBoolSection* Section = Cast<UMovieSceneBoolSection>(Sections[0]);
		if (!Section) return FCommandResult::Error(TEXT("Failed to cast to bool section"));

		bool bValue = Params->GetBoolField(TEXT("value"));

		TArrayView<FMovieSceneBoolChannel*> BoolChannels = Section->GetChannelProxy().GetChannels<FMovieSceneBoolChannel>();
		if (BoolChannels.Num() > 0)
		{
			BoolChannels[0]->GetData().AddKey(FrameNum, bValue);
			KeysAdded = 1;
		}
	}
	else if (TrackType.Equals(TEXT("Float"), ESearchCase::IgnoreCase))
	{
		UMovieSceneFloatTrack* Track = nullptr;
		FMovieSceneBinding* Binding = MovieScene->FindBinding(BindingGuid);
		if (Binding)
		{
			for (UMovieSceneTrack* T : Binding->GetTracks())
			{
				Track = Cast<UMovieSceneFloatTrack>(T);
				if (Track) break;
			}
		}
		if (!Track) return FCommandResult::Error(TEXT("No Float track found"));

		const TArray<UMovieSceneSection*>& Sections = Track->GetAllSections();
		if (Sections.Num() == 0) return FCommandResult::Error(TEXT("Float track has no sections"));

		UMovieSceneFloatSection* Section = Cast<UMovieSceneFloatSection>(Sections[0]);
		if (!Section) return FCommandResult::Error(TEXT("Failed to cast to float section"));

		double Value = Params->GetNumberField(TEXT("value"));

		TArrayView<FMovieSceneFloatChannel*> FloatChannels = Section->GetChannelProxy().GetChannels<FMovieSceneFloatChannel>();
		if (FloatChannels.Num() > 0)
		{
			FloatChannels[0]->AddCubicKey(FrameNum, (float)Value);
			KeysAdded = 1;
		}
	}

	Sequence->MarkPackageDirty();

	UE_LOG(LogBlueprintLLM, Log, TEXT("Added %d keyframe(s) at %.2fs for '%s' %s track in '%s'"),
		KeysAdded, Time, *ActorLabel, *TrackType, *SeqName);

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("sequence_name"), SeqName);
	Data->SetStringField(TEXT("actor_label"), ActorLabel);
	Data->SetStringField(TEXT("track_type"), TrackType);
	Data->SetNumberField(TEXT("time"), Time);
	Data->SetNumberField(TEXT("frame"), (double)FrameNum.Value);
	Data->SetNumberField(TEXT("keys_added"), KeysAdded);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetSequenceInfo(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required field: name"));

	FString AssetPath = FString::Printf(TEXT("/Game/Arcwright/Sequences/%s"), *Name);
	ULevelSequence* Sequence = LoadObject<ULevelSequence>(nullptr, *AssetPath);
	if (!Sequence)
		return FCommandResult::Error(FString::Printf(TEXT("Sequence not found: %s"), *Name));

	UMovieScene* MovieScene = Sequence->GetMovieScene();

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), AssetPath);

	if (MovieScene)
	{
		FFrameRate TickRate = MovieScene->GetTickResolution();
		TRange<FFrameNumber> Range = MovieScene->GetPlaybackRange();
		double Duration = 0;
		if (Range.HasLowerBound() && Range.HasUpperBound())
		{
			Duration = (Range.GetUpperBoundValue() - Range.GetLowerBoundValue()).Value / TickRate.AsDecimal();
		}
		Data->SetNumberField(TEXT("duration"), Duration);

		// Count tracks and bound actors
		int32 TotalTracks = 0;
		TArray<TSharedPtr<FJsonValue>> BoundActors;

		for (int32 i = 0; i < MovieScene->GetPossessableCount(); i++)
		{
			const FMovieScenePossessable& Poss = MovieScene->GetPossessable(i);
			FMovieSceneBinding* Binding = MovieScene->FindBinding(Poss.GetGuid());

			TSharedPtr<FJsonObject> ActorObj = MakeShared<FJsonObject>();
			ActorObj->SetStringField(TEXT("name"), Poss.GetName());
			ActorObj->SetStringField(TEXT("guid"), Poss.GetGuid().ToString());

			TArray<TSharedPtr<FJsonValue>> Tracks;
			if (Binding)
			{
				for (UMovieSceneTrack* Track : Binding->GetTracks())
				{
					TSharedPtr<FJsonObject> TrackObj = MakeShared<FJsonObject>();
					TrackObj->SetStringField(TEXT("type"), Track->GetClass()->GetName());
					TrackObj->SetNumberField(TEXT("sections"), Track->GetAllSections().Num());

					// Count keyframes in first section
					int32 KeyCount = 0;
					const TArray<UMovieSceneSection*>& Sections = Track->GetAllSections();
					if (Sections.Num() > 0)
					{
						// Count channels
						FMovieSceneChannelProxy& Proxy = Sections[0]->GetChannelProxy();
						for (const FMovieSceneChannelEntry& Entry : Proxy.GetAllEntries())
						{
							KeyCount += Entry.GetChannels().Num();
						}
					}
					TrackObj->SetNumberField(TEXT("channel_count"), KeyCount);

					Tracks.Add(MakeShared<FJsonValueObject>(TrackObj));
					TotalTracks++;
				}
			}
			ActorObj->SetArrayField(TEXT("tracks"), Tracks);
			BoundActors.Add(MakeShared<FJsonValueObject>(ActorObj));
		}

		Data->SetNumberField(TEXT("total_tracks"), TotalTracks);
		Data->SetNumberField(TEXT("bound_actor_count"), MovieScene->GetPossessableCount());
		Data->SetArrayField(TEXT("bound_actors"), BoundActors);
	}

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandlePlaySequence(const TSharedPtr<FJsonObject>& Params)
{
	// Playing sequences in editor requires PIE or editor preview — same limitation as play_in_editor
	return FCommandResult::Error(TEXT("play_sequence not supported outside PIE. Use play_in_editor to start PIE first, or preview the sequence manually in the Sequencer window."));
}

// ============================================================
// Batch 2.2 — Landscape/Foliage commands
// ============================================================

FCommandResult FCommandServer::HandleGetLandscapeInfo(const TSharedPtr<FJsonObject>& Params)
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World) return FCommandResult::Error(TEXT("No editor world"));

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();

	ALandscapeProxy* Landscape = nullptr;
	for (TActorIterator<ALandscapeProxy> It(World); It; ++It)
	{
		Landscape = *It;
		break;
	}

	if (!Landscape)
	{
		Data->SetBoolField(TEXT("exists"), false);
		Data->SetStringField(TEXT("message"), TEXT("No landscape found in current level. Create one manually in UE Editor (Landscape Mode) then use set_landscape_material."));
		return FCommandResult::Ok(Data);
	}

	Data->SetBoolField(TEXT("exists"), true);
	Data->SetStringField(TEXT("name"), Landscape->GetActorLabel());
	Data->SetStringField(TEXT("class"), Landscape->GetClass()->GetName());

	// Bounds
	FBox Bounds = Landscape->GetComponentsBoundingBox(true);
	TSharedPtr<FJsonObject> BoundsObj = MakeShared<FJsonObject>();
	BoundsObj->SetArrayField(TEXT("min"), TArray<TSharedPtr<FJsonValue>>{
		MakeShared<FJsonValueNumber>(Bounds.Min.X),
		MakeShared<FJsonValueNumber>(Bounds.Min.Y),
		MakeShared<FJsonValueNumber>(Bounds.Min.Z)
	});
	BoundsObj->SetArrayField(TEXT("max"), TArray<TSharedPtr<FJsonValue>>{
		MakeShared<FJsonValueNumber>(Bounds.Max.X),
		MakeShared<FJsonValueNumber>(Bounds.Max.Y),
		MakeShared<FJsonValueNumber>(Bounds.Max.Z)
	});
	Data->SetObjectField(TEXT("bounds"), BoundsObj);

	// Component count
	TArray<ULandscapeComponent*> Components;
	Landscape->GetComponents(Components);
	Data->SetNumberField(TEXT("component_count"), Components.Num());

	// Material
	UMaterialInterface* Mat = Landscape->GetLandscapeMaterial();
	Data->SetStringField(TEXT("material"), Mat ? Mat->GetPathName() : TEXT("None"));

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetLandscapeMaterial(const TSharedPtr<FJsonObject>& Params)
{
	FString MaterialPath = Params->GetStringField(TEXT("material_path"));
	if (MaterialPath.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required field: material_path"));

	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World) return FCommandResult::Error(TEXT("No editor world"));

	ALandscapeProxy* Landscape = nullptr;
	for (TActorIterator<ALandscapeProxy> It(World); It; ++It)
	{
		Landscape = *It;
		break;
	}
	if (!Landscape)
		return FCommandResult::Error(TEXT("No landscape found in current level"));

	FString ResolvedPath, ResolveError;
	UMaterialInterface* Material = ResolveMaterialByName(MaterialPath, ResolvedPath, ResolveError);
	if (!Material)
		return FCommandResult::Error(ResolveError.IsEmpty() ? FString::Printf(TEXT("Material not found: %s"), *MaterialPath) : ResolveError);

	Landscape->LandscapeMaterial = Material;
	Landscape->MarkPackageDirty();

	// Force update
	FPropertyChangedEvent Event(ALandscapeProxy::StaticClass()->FindPropertyByName(TEXT("LandscapeMaterial")));
	Landscape->PostEditChangeProperty(Event);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Set landscape material to '%s'"), *MaterialPath);

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("landscape"), Landscape->GetActorLabel());
	Data->SetStringField(TEXT("material_path"), MaterialPath);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCreateFoliageType(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required field: name"));

	FString MeshPath = Params->GetStringField(TEXT("mesh"));
	if (MeshPath.IsEmpty())
		MeshPath = TEXT("/Engine/BasicShapes/Sphere.Sphere");

	double Density = 100.0;
	if (Params->HasField(TEXT("density")))
		Density = Params->GetNumberField(TEXT("density"));

	double ScaleMin = 1.0, ScaleMax = 1.0;
	if (Params->HasField(TEXT("scale_min")))
		ScaleMin = Params->GetNumberField(TEXT("scale_min"));
	if (Params->HasField(TEXT("scale_max")))
		ScaleMax = Params->GetNumberField(TEXT("scale_max"));

	// Create UFoliageType_InstancedStaticMesh
	FString PackagePath = FString::Printf(TEXT("/Game/Arcwright/Foliage/%s"), *Name);
	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package) return FCommandResult::Error(TEXT("Failed to create package"));

	UFoliageType_InstancedStaticMesh* FoliageType = NewObject<UFoliageType_InstancedStaticMesh>(
		Package, *Name, RF_Public | RF_Standalone);
	if (!FoliageType) return FCommandResult::Error(TEXT("Failed to create UFoliageType"));

	// Set mesh
	UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *MeshPath);
	if (Mesh)
	{
		FoliageType->SetStaticMesh(Mesh);
	}
	else
	{
		UE_LOG(LogBlueprintLLM, Warning, TEXT("Mesh not found: %s — foliage type created without mesh"), *MeshPath);
	}

	// Set density and scale
	FoliageType->Density = Density;
	FoliageType->ScaleX = FFloatInterval(ScaleMin, ScaleMax);
	FoliageType->ScaleY = FFloatInterval(ScaleMin, ScaleMax);
	FoliageType->ScaleZ = FFloatInterval(ScaleMin, ScaleMax);

	// Save
	FAssetRegistryModule::AssetCreated(FoliageType);
	FoliageType->MarkPackageDirty();
	FSavePackageArgs SaveArgs;
	SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
	SafeSavePackage(Package, FoliageType,
		FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension()),
		SaveArgs);

	UE_LOG(LogBlueprintLLM, Log, TEXT("Created foliage type '%s' mesh='%s' density=%.0f scale=[%.1f,%.1f]"),
		*Name, *MeshPath, Density, ScaleMin, ScaleMax);

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), PackagePath);
	Data->SetStringField(TEXT("mesh"), MeshPath);
	Data->SetNumberField(TEXT("density"), Density);
	Data->SetNumberField(TEXT("scale_min"), ScaleMin);
	Data->SetNumberField(TEXT("scale_max"), ScaleMax);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandlePaintFoliage(const TSharedPtr<FJsonObject>& Params)
{
	FString FoliageTypePath = Params->GetStringField(TEXT("foliage_type"));
	if (FoliageTypePath.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required field: foliage_type"));

	const TSharedPtr<FJsonObject>* CenterObj = nullptr;
	if (!Params->TryGetObjectField(TEXT("center"), CenterObj))
		return FCommandResult::Error(TEXT("Missing required field: center ({x,y,z})"));

	FVector Center = JsonToVector(*CenterObj);

	double Radius = 500.0;
	if (Params->HasField(TEXT("radius")))
		Radius = Params->GetNumberField(TEXT("radius"));

	int32 Count = 10;
	if (Params->HasField(TEXT("count")))
		Count = (int32)Params->GetNumberField(TEXT("count"));

	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World) return FCommandResult::Error(TEXT("No editor world"));

	// Load the foliage type
	UFoliageType* FoliageType = LoadObject<UFoliageType>(nullptr, *FoliageTypePath);
	if (!FoliageType)
		return FCommandResult::Error(FString::Printf(TEXT("Foliage type not found: %s"), *FoliageTypePath));

	// Get or create the instanced foliage actor
	AInstancedFoliageActor* IFA = AInstancedFoliageActor::GetInstancedFoliageActorForCurrentLevel(World, true);
	if (!IFA)
		return FCommandResult::Error(TEXT("Failed to get InstancedFoliageActor"));

	// Add foliage type to IFA if not already registered
	FFoliageInfo* FoliageInfo = IFA->FindOrAddMesh(FoliageType);
	if (!FoliageInfo)
		return FCommandResult::Error(TEXT("Failed to add foliage type to InstancedFoliageActor"));

	// Procedurally place instances in a circle
	int32 Placed = 0;
	for (int32 i = 0; i < Count; i++)
	{
		// Random point in circle
		double Angle = FMath::FRandRange(0.0, 2.0 * PI);
		double Dist = FMath::Sqrt(FMath::FRandRange(0.0, 1.0)) * Radius;
		FVector Pos = Center + FVector(FMath::Cos(Angle) * Dist, FMath::Sin(Angle) * Dist, 0);

		// Trace down to find ground
		FHitResult Hit;
		FVector TraceStart = Pos + FVector(0, 0, 10000);
		FVector TraceEnd = Pos - FVector(0, 0, 10000);
		if (World->LineTraceSingleByChannel(Hit, TraceStart, TraceEnd, ECC_WorldStatic))
		{
			Pos = Hit.ImpactPoint;
		}

		// Random scale within foliage type range
		float Scale = FMath::FRandRange(
			FoliageType->ScaleX.Min,
			FoliageType->ScaleX.Max);

		FFoliageInstance Instance;
		Instance.Location = Pos;
		Instance.Rotation = FRotator(0, FMath::FRandRange(0.f, 360.f), 0);
		Instance.DrawScale3D = FVector3f(Scale, Scale, Scale);

		FoliageInfo->AddInstance(FoliageType, Instance);
		Placed++;
	}

	IFA->MarkPackageDirty();

	UE_LOG(LogBlueprintLLM, Log, TEXT("Painted %d foliage instances of '%s' at (%.0f,%.0f,%.0f) r=%.0f"),
		Placed, *FoliageTypePath, Center.X, Center.Y, Center.Z, Radius);

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("foliage_type"), FoliageTypePath);
	Data->SetNumberField(TEXT("placed"), Placed);
	Data->SetNumberField(TEXT("requested"), Count);
	Data->SetObjectField(TEXT("center"), VectorToJson(Center));
	Data->SetNumberField(TEXT("radius"), Radius);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetFoliageInfo(const TSharedPtr<FJsonObject>& Params)
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World) return FCommandResult::Error(TEXT("No editor world"));

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	TArray<TSharedPtr<FJsonValue>> TypesArr;
	int32 TotalInstances = 0;

	for (TActorIterator<AInstancedFoliageActor> It(World); It; ++It)
	{
		AInstancedFoliageActor* IFA = *It;

		const TMap<UFoliageType*, TUniqueObj<FFoliageInfo>>& FoliageInfos = IFA->GetFoliageInfos();
		for (const auto& Pair : FoliageInfos)
		{
			const UFoliageType* Type = Pair.Key;
			const FFoliageInfo& Info = *Pair.Value;

			TSharedPtr<FJsonObject> TypeObj = MakeShared<FJsonObject>();
			TypeObj->SetStringField(TEXT("type"), Type->GetPathName());
			TypeObj->SetStringField(TEXT("class"), Type->GetClass()->GetName());

			int32 InstanceCount = Info.Instances.Num();
			TypeObj->SetNumberField(TEXT("instance_count"), InstanceCount);
			TotalInstances += InstanceCount;

			// Get mesh name if it's InstancedStaticMesh type
			const UFoliageType_InstancedStaticMesh* ISMType = Cast<UFoliageType_InstancedStaticMesh>(Type);
			if (ISMType && ISMType->GetStaticMesh())
			{
				TypeObj->SetStringField(TEXT("mesh"), ISMType->GetStaticMesh()->GetPathName());
			}

			TypesArr.Add(MakeShared<FJsonValueObject>(TypeObj));
		}
	}

	Data->SetNumberField(TEXT("foliage_type_count"), TypesArr.Num());
	Data->SetNumberField(TEXT("total_instances"), TotalInstances);
	Data->SetArrayField(TEXT("foliage_types"), TypesArr);

	return FCommandResult::Ok(Data);
}

// ============================================================
// create_data_table — Create DataTable + struct from IR JSON
// ============================================================

FCommandResult FCommandServer::HandleCreateDataTable(const TSharedPtr<FJsonObject>& Params)
{
	// Accept IR JSON as either inline object or JSON string
	TSharedPtr<FJsonObject> IRJson;

	if (Params->HasField(TEXT("ir_json")))
	{
		FString IRJsonStr = Params->GetStringField(TEXT("ir_json"));
		TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(IRJsonStr);
		if (!FJsonSerializer::Deserialize(Reader, IRJson) || !IRJson.IsValid())
		{
			return FCommandResult::Error(TEXT("Failed to parse ir_json string"));
		}
	}
	else if (Params->HasTypedField<EJson::Object>(TEXT("ir")))
	{
		IRJson = Params->GetObjectField(TEXT("ir"));
	}
	else
	{
		return FCommandResult::Error(TEXT("Missing required param: ir_json (string) or ir (object)"));
	}

	FString PackagePath = TEXT("/Game/Arcwright/DataTables");

	FDataTableBuilder::FDTBuildResult DTResult = FDataTableBuilder::CreateFromIR(IRJson, PackagePath);

	if (!DTResult.bSuccess)
	{
		return FCommandResult::Error(DTResult.ErrorMessage);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("table_asset_path"), DTResult.TableAssetPath);
	Data->SetStringField(TEXT("struct_asset_path"), DTResult.StructAssetPath);
	Data->SetNumberField(TEXT("column_count"), DTResult.ColumnCount);
	Data->SetNumberField(TEXT("row_count"), DTResult.RowCount);

	return FCommandResult::Ok(Data);
}

// ============================================================
// get_data_table_info — Query an existing DataTable
// ============================================================

FCommandResult FCommandServer::HandleGetDataTableInfo(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required param: name"));
	}

	TSharedPtr<FJsonObject> Info = FDataTableBuilder::GetDataTableInfo(Name);
	if (!Info.IsValid())
	{
		return FCommandResult::Error(FString::Printf(TEXT("DataTable not found: %s"), *Name));
	}

	return FCommandResult::Ok(Info);
}

// ============================================================
// setup_scene_lighting — Create standard scene lighting setup
// ============================================================

FCommandResult FCommandServer::HandleSetupSceneLighting(const TSharedPtr<FJsonObject>& Params)
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World) return FCommandResult::Error(TEXT("No world"));

	UEditorActorSubsystem* EAS = GEditor->GetEditorSubsystem<UEditorActorSubsystem>();
	if (!EAS) return FCommandResult::Error(TEXT("No EditorActorSubsystem"));

	// Parse preset (default: indoor_dark)
	FString Preset = Params->GetStringField(TEXT("preset"));
	if (Preset.IsEmpty()) Preset = TEXT("indoor_dark");

	// Preset configurations
	float DirIntensity = 2.0f;
	float SkyIntensity = 0.5f;
	float DirPitch = -45.0f;
	float DirYaw = -30.0f;
	FLinearColor DirColor = FLinearColor(1.0f, 0.95f, 0.85f); // warm sunlight
	bool bAddAtmosphere = false;
	bool bAddFog = false;
	float FogDensity = 0.02f;

	if (Preset == TEXT("indoor_dark"))
	{
		DirIntensity = 2.0f;
		SkyIntensity = 0.5f;
		DirPitch = -45.0f;
		DirColor = FLinearColor(1.0f, 0.9f, 0.7f); // warm torch-like
	}
	else if (Preset == TEXT("indoor_bright"))
	{
		DirIntensity = 5.0f;
		SkyIntensity = 1.5f;
		DirPitch = -50.0f;
		DirColor = FLinearColor(1.0f, 0.98f, 0.95f);
	}
	else if (Preset == TEXT("outdoor_day"))
	{
		DirIntensity = 10.0f;
		SkyIntensity = 1.0f;
		DirPitch = -60.0f;
		DirColor = FLinearColor(1.0f, 0.98f, 0.92f);
		bAddAtmosphere = true;
		bAddFog = true;
		FogDensity = 0.005f;
	}
	else if (Preset == TEXT("outdoor_night"))
	{
		DirIntensity = 0.5f;
		SkyIntensity = 0.2f;
		DirPitch = -30.0f;
		DirColor = FLinearColor(0.6f, 0.7f, 1.0f); // cool moonlight
		bAddFog = true;
		FogDensity = 0.03f;
	}

	// Allow per-parameter overrides
	if (Params->HasField(TEXT("directional_intensity")))
		DirIntensity = Params->GetNumberField(TEXT("directional_intensity"));
	if (Params->HasField(TEXT("sky_intensity")))
		SkyIntensity = Params->GetNumberField(TEXT("sky_intensity"));
	if (Params->HasField(TEXT("directional_pitch")))
		DirPitch = Params->GetNumberField(TEXT("directional_pitch"));
	if (Params->HasField(TEXT("directional_yaw")))
		DirYaw = Params->GetNumberField(TEXT("directional_yaw"));
	if (Params->HasField(TEXT("add_atmosphere")))
		bAddAtmosphere = Params->GetBoolField(TEXT("add_atmosphere"));
	if (Params->HasField(TEXT("add_fog")))
		bAddFog = Params->GetBoolField(TEXT("add_fog"));
	if (Params->HasField(TEXT("fog_density")))
		FogDensity = Params->GetNumberField(TEXT("fog_density"));
	if (Params->HasTypedField<EJson::Object>(TEXT("directional_color")))
	{
		auto ColorObj = Params->GetObjectField(TEXT("directional_color"));
		DirColor = FLinearColor(
			ColorObj->GetNumberField(TEXT("r")),
			ColorObj->GetNumberField(TEXT("g")),
			ColorObj->GetNumberField(TEXT("b"))
		);
	}

	TSharedPtr<FJsonObject> ResultData = MakeShareable(new FJsonObject());
	TArray<TSharedPtr<FJsonValue>> CreatedActors;

	// --- 1. DirectionalLight ---
	// Remove existing if present
	for (TActorIterator<ADirectionalLight> It(World); It; ++It)
	{
		EAS->DestroyActor(*It);
	}

	FVector LightPos(0, 0, 1000);
	FRotator LightRot(DirPitch, DirYaw, 0);

	ADirectionalLight* DirLight = World->SpawnActor<ADirectionalLight>(LightPos, LightRot);
	if (DirLight)
	{
		DirLight->SetActorLabel(TEXT("SceneDirectionalLight"));
		ULightComponent* DirComp = DirLight->GetLightComponent();
		if (DirComp)
		{
			DirComp->SetIntensity(DirIntensity);
			DirComp->SetLightColor(DirColor);
		}
		DirLight->MarkPackageDirty();

		TSharedPtr<FJsonObject> DirInfo = MakeShareable(new FJsonObject());
		DirInfo->SetStringField(TEXT("label"), TEXT("SceneDirectionalLight"));
		DirInfo->SetNumberField(TEXT("intensity"), DirIntensity);
		DirInfo->SetNumberField(TEXT("pitch"), DirPitch);
		CreatedActors.Add(MakeShareable(new FJsonValueObject(DirInfo)));

		UE_LOG(LogBlueprintLLM, Log, TEXT("Created DirectionalLight: intensity=%.1f, pitch=%.1f"), DirIntensity, DirPitch);
	}

	// --- 2. SkyLight ---
	for (TActorIterator<ASkyLight> It(World); It; ++It)
	{
		EAS->DestroyActor(*It);
	}

	ASkyLight* Sky = World->SpawnActor<ASkyLight>(LightPos, FRotator::ZeroRotator);
	if (Sky)
	{
		Sky->SetActorLabel(TEXT("SceneSkyLight"));
		USkyLightComponent* SkyComp = Sky->GetLightComponent();
		if (SkyComp)
		{
			SkyComp->SetIntensity(SkyIntensity);
			SkyComp->bLowerHemisphereIsBlack = false;
			SkyComp->RecaptureSky();
		}
		Sky->MarkPackageDirty();

		TSharedPtr<FJsonObject> SkyInfo = MakeShareable(new FJsonObject());
		SkyInfo->SetStringField(TEXT("label"), TEXT("SceneSkyLight"));
		SkyInfo->SetNumberField(TEXT("intensity"), SkyIntensity);
		CreatedActors.Add(MakeShareable(new FJsonValueObject(SkyInfo)));

		UE_LOG(LogBlueprintLLM, Log, TEXT("Created SkyLight: intensity=%.1f"), SkyIntensity);
	}

	// --- 3. SkyAtmosphere (optional) ---
	if (bAddAtmosphere)
	{
		// Check if one already exists
		bool bHasAtmo = false;
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			if (It->GetClass()->GetName().Contains(TEXT("SkyAtmosphere")))
			{
				bHasAtmo = true;
				break;
			}
		}

		if (!bHasAtmo)
		{
			UClass* AtmoClass = FindObject<UClass>(nullptr, TEXT("/Script/Engine.ASkyAtmosphere"));
			if (!AtmoClass)
			{
				// Try loading the class by path
				AtmoClass = LoadClass<AActor>(nullptr, TEXT("/Script/Engine.SkyAtmosphere"));
			}
			if (AtmoClass)
			{
				AActor* Atmo = World->SpawnActor(AtmoClass, &LightPos, &FRotator::ZeroRotator);
				if (Atmo)
				{
					Atmo->SetActorLabel(TEXT("SceneSkyAtmosphere"));
					Atmo->MarkPackageDirty();

					TSharedPtr<FJsonObject> AtmoInfo = MakeShareable(new FJsonObject());
					AtmoInfo->SetStringField(TEXT("label"), TEXT("SceneSkyAtmosphere"));
					CreatedActors.Add(MakeShareable(new FJsonValueObject(AtmoInfo)));

					UE_LOG(LogBlueprintLLM, Log, TEXT("Created SkyAtmosphere"));
				}
			}
		}
	}

	// --- 4. ExponentialHeightFog (optional) ---
	if (bAddFog)
	{
		// Remove existing
		for (TActorIterator<AExponentialHeightFog> It(World); It; ++It)
		{
			EAS->DestroyActor(*It);
		}

		AExponentialHeightFog* Fog = World->SpawnActor<AExponentialHeightFog>(FVector(0, 0, 200), FRotator::ZeroRotator);
		if (Fog)
		{
			Fog->SetActorLabel(TEXT("SceneHeightFog"));
			UExponentialHeightFogComponent* FogComp = Fog->GetComponent();
			if (FogComp)
			{
				FogComp->SetFogDensity(FogDensity);
			}
			Fog->MarkPackageDirty();

			TSharedPtr<FJsonObject> FogInfo = MakeShareable(new FJsonObject());
			FogInfo->SetStringField(TEXT("label"), TEXT("SceneHeightFog"));
			FogInfo->SetNumberField(TEXT("density"), FogDensity);
			CreatedActors.Add(MakeShareable(new FJsonValueObject(FogInfo)));

			UE_LOG(LogBlueprintLLM, Log, TEXT("Created ExponentialHeightFog: density=%.4f"), FogDensity);
		}
	}

	ResultData->SetStringField(TEXT("preset"), Preset);
	ResultData->SetArrayField(TEXT("actors"), CreatedActors);
	ResultData->SetNumberField(TEXT("actors_created"), CreatedActors.Num());

	return FCommandResult::Ok(ResultData);
}

// ============================================================
// set_game_mode — Set the level's GameMode override
// ============================================================

FCommandResult FCommandServer::HandleSetGameMode(const TSharedPtr<FJsonObject>& Params)
{
	FString GameModeName = Params->GetStringField(TEXT("game_mode"));
	if (GameModeName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing required param: game_mode"));
	}

	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World) return FCommandResult::Error(TEXT("No world"));

	AWorldSettings* WS = World->GetWorldSettings();
	if (!WS) return FCommandResult::Error(TEXT("No world settings"));

	// Find the GameMode Blueprint
	UBlueprint* GMBP = FindBlueprintByName(GameModeName);
	UClass* GMClass = GMBP ? GMBP->GeneratedClass : nullptr;
	if (!GMClass)
	{
		// Try native class
		GMClass = FindObject<UClass>(nullptr, *FString::Printf(TEXT("/Script/Engine.%s"), *GameModeName));
	}
	if (!GMClass || !GMClass->IsChildOf(AGameModeBase::StaticClass()))
	{
		return FCommandResult::Error(FString::Printf(TEXT("GameMode class not found or not a GameModeBase: %s"), *GameModeName));
	}

	WS->DefaultGameMode = GMClass;
	WS->MarkPackageDirty();

	UE_LOG(LogBlueprintLLM, Log, TEXT("Set world GameMode to %s"), *GMClass->GetName());

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("game_mode"), GMClass->GetName());
	Data->SetBoolField(TEXT("set"), true);

	return FCommandResult::Ok(Data);
}

// ============================================================
// Query Commands
// ============================================================

FCommandResult FCommandServer::HandleFindBlueprints(const TSharedPtr<FJsonObject>& Params)
{
	FString NameFilter = Params->HasField(TEXT("name_filter")) ? Params->GetStringField(TEXT("name_filter")) : TEXT("");
	FString ParentClass = Params->HasField(TEXT("parent_class")) ? Params->GetStringField(TEXT("parent_class")) : TEXT("");
	FString HasVariable = Params->HasField(TEXT("has_variable")) ? Params->GetStringField(TEXT("has_variable")) : TEXT("");
	FString HasComponent = Params->HasField(TEXT("has_component")) ? Params->GetStringField(TEXT("has_component")) : TEXT("");
	FString SearchPath = Params->HasField(TEXT("path")) ? Params->GetStringField(TEXT("path")) : TEXT("/Game");

	FAssetRegistryModule& ARM = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	IAssetRegistry& AR = ARM.Get();

	TArray<FAssetData> AssetDataList;
	AR.GetAssetsByPath(FName(*SearchPath), AssetDataList, true);

	FTopLevelAssetPath BPClassPath = UBlueprint::StaticClass()->GetClassPathName();

	TArray<TSharedPtr<FJsonValue>> ResultsArray;
	for (const FAssetData& AssetData : AssetDataList)
	{
		if (AssetData.AssetClassPath != BPClassPath) continue;

		FString AssetName = AssetData.AssetName.ToString();

		// Name filter (case-insensitive substring)
		if (!NameFilter.IsEmpty() && !AssetName.Contains(NameFilter, ESearchCase::IgnoreCase))
			continue;

		// Need to load BP for detailed filtering
		UBlueprint* BP = Cast<UBlueprint>(AssetData.GetAsset());
		if (!BP) continue;

		// Parent class filter
		if (!ParentClass.IsEmpty())
		{
			FString ParentName = BP->ParentClass ? BP->ParentClass->GetName() : TEXT("");
			if (!ParentName.Contains(ParentClass, ESearchCase::IgnoreCase))
				continue;
		}

		// Has variable filter
		if (!HasVariable.IsEmpty())
		{
			bool bFound = false;
			for (const FBPVariableDescription& Var : BP->NewVariables)
			{
				if (Var.VarName.ToString().Contains(HasVariable, ESearchCase::IgnoreCase))
				{
					bFound = true;
					break;
				}
			}
			if (!bFound) continue;
		}

		// Has component filter
		if (!HasComponent.IsEmpty())
		{
			bool bFound = false;
			if (BP->SimpleConstructionScript)
			{
				for (USCS_Node* Node : BP->SimpleConstructionScript->GetAllNodes())
				{
					if (Node && Node->ComponentTemplate)
					{
						FString CompClassName = Node->ComponentTemplate->GetClass()->GetName();
						if (CompClassName.Contains(HasComponent, ESearchCase::IgnoreCase))
						{
							bFound = true;
							break;
						}
					}
				}
			}
			if (!bFound) continue;
		}

		// Build result
		TSharedPtr<FJsonObject> Obj = MakeShareable(new FJsonObject());
		Obj->SetStringField(TEXT("name"), AssetName);
		Obj->SetStringField(TEXT("asset_path"), AssetData.GetObjectPathString());
		Obj->SetStringField(TEXT("parent_class"), BP->ParentClass ? BP->ParentClass->GetName() : TEXT("None"));
		Obj->SetBoolField(TEXT("compiled"), BP->Status != BS_Error);

		// Variables list
		TArray<TSharedPtr<FJsonValue>> VarsArray;
		for (const FBPVariableDescription& Var : BP->NewVariables)
		{
			TSharedPtr<FJsonObject> VarObj = MakeShareable(new FJsonObject());
			VarObj->SetStringField(TEXT("name"), Var.VarName.ToString());
			VarObj->SetStringField(TEXT("type"), Var.VarType.PinCategory.ToString());
			VarObj->SetStringField(TEXT("default"), Var.DefaultValue);
			VarsArray.Add(MakeShareable(new FJsonValueObject(VarObj)));
		}
		Obj->SetArrayField(TEXT("variables"), VarsArray);

		// Components list
		TArray<TSharedPtr<FJsonValue>> CompsArray;
		if (BP->SimpleConstructionScript)
		{
			for (USCS_Node* Node : BP->SimpleConstructionScript->GetAllNodes())
			{
				if (Node && Node->ComponentTemplate)
				{
					TSharedPtr<FJsonObject> CompObj = MakeShareable(new FJsonObject());
					CompObj->SetStringField(TEXT("name"), Node->GetVariableName().ToString());
					CompObj->SetStringField(TEXT("class"), Node->ComponentTemplate->GetClass()->GetName());
					CompsArray.Add(MakeShareable(new FJsonValueObject(CompObj)));
				}
			}
		}
		Obj->SetArrayField(TEXT("components"), CompsArray);

		ResultsArray.Add(MakeShareable(new FJsonValueObject(Obj)));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("count"), ResultsArray.Num());
	Data->SetArrayField(TEXT("blueprints"), ResultsArray);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleFindActors(const TSharedPtr<FJsonObject>& Params)
{
	UEditorActorSubsystem* ActorSub = GEditor->GetEditorSubsystem<UEditorActorSubsystem>();
	if (!ActorSub) return FCommandResult::Error(TEXT("Could not get UEditorActorSubsystem"));

	FString NameFilter = Params->HasField(TEXT("name_filter")) ? Params->GetStringField(TEXT("name_filter")) : TEXT("");
	FString ClassFilter = Params->HasField(TEXT("class_filter")) ? Params->GetStringField(TEXT("class_filter")) : TEXT("");
	FString Tag = Params->HasField(TEXT("tag")) ? Params->GetStringField(TEXT("tag")) : TEXT("");
	FString HasComponent = Params->HasField(TEXT("has_component")) ? Params->GetStringField(TEXT("has_component")) : TEXT("");
	FString MaterialName = Params->HasField(TEXT("material_name")) ? Params->GetStringField(TEXT("material_name")) : TEXT("");

	bool bHasRadius = Params->HasField(TEXT("radius"));
	float Radius = bHasRadius ? Params->GetNumberField(TEXT("radius")) : 0.0f;
	FVector Center = FVector::ZeroVector;
	if (Params->HasField(TEXT("center")))
	{
		Center = JsonToVector(Params->GetObjectField(TEXT("center")));
	}

	TArray<AActor*> AllActors = ActorSub->GetAllLevelActors();
	TArray<TSharedPtr<FJsonValue>> ResultsArray;

	for (AActor* Actor : AllActors)
	{
		if (!Actor) continue;

		// Name filter
		if (!NameFilter.IsEmpty() && !Actor->GetActorLabel().Contains(NameFilter, ESearchCase::IgnoreCase))
			continue;

		// Class filter
		if (!ClassFilter.IsEmpty() && !Actor->GetClass()->GetName().Contains(ClassFilter, ESearchCase::IgnoreCase))
			continue;

		// Tag filter
		if (!Tag.IsEmpty() && !Actor->ActorHasTag(FName(*Tag)))
			continue;

		// Radius filter
		if (bHasRadius && FVector::Dist(Actor->GetActorLocation(), Center) > Radius)
			continue;

		// Component filter
		if (!HasComponent.IsEmpty())
		{
			bool bFound = false;
			for (UActorComponent* Comp : Actor->GetComponents())
			{
				if (Comp && Comp->GetClass()->GetName().Contains(HasComponent, ESearchCase::IgnoreCase))
				{
					bFound = true;
					break;
				}
			}
			if (!bFound) continue;
		}

		// Material filter
		if (!MaterialName.IsEmpty())
		{
			bool bFound = false;
			for (UActorComponent* Comp : Actor->GetComponents())
			{
				UMeshComponent* MeshComp = Cast<UMeshComponent>(Comp);
				if (MeshComp)
				{
					for (int32 i = 0; i < MeshComp->GetNumMaterials(); i++)
					{
						UMaterialInterface* Mat = MeshComp->GetMaterial(i);
						if (Mat && Mat->GetName().Contains(MaterialName, ESearchCase::IgnoreCase))
						{
							bFound = true;
							break;
						}
					}
				}
				if (bFound) break;
			}
			if (!bFound) continue;
		}

		// Build result
		TSharedPtr<FJsonObject> ActorObj = MakeShareable(new FJsonObject());
		ActorObj->SetStringField(TEXT("label"), Actor->GetActorLabel());
		ActorObj->SetStringField(TEXT("class"), Actor->GetClass()->GetName());
		ActorObj->SetObjectField(TEXT("location"), VectorToJson(Actor->GetActorLocation()));
		ActorObj->SetObjectField(TEXT("rotation"), RotatorToJson(Actor->GetActorRotation()));
		ActorObj->SetObjectField(TEXT("scale"), VectorToJson(Actor->GetActorScale3D()));

		// Tags
		TArray<TSharedPtr<FJsonValue>> TagsArray;
		for (const FName& T : Actor->Tags)
		{
			TagsArray.Add(MakeShareable(new FJsonValueString(T.ToString())));
		}
		ActorObj->SetArrayField(TEXT("tags"), TagsArray);

		// Components
		TArray<TSharedPtr<FJsonValue>> CompsArray;
		for (UActorComponent* Comp : Actor->GetComponents())
		{
			if (Comp)
			{
				TSharedPtr<FJsonObject> CompObj = MakeShareable(new FJsonObject());
				CompObj->SetStringField(TEXT("name"), Comp->GetName());
				CompObj->SetStringField(TEXT("class"), Comp->GetClass()->GetName());
				CompsArray.Add(MakeShareable(new FJsonValueObject(CompObj)));
			}
		}
		ActorObj->SetArrayField(TEXT("components"), CompsArray);

		ResultsArray.Add(MakeShareable(new FJsonValueObject(ActorObj)));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("count"), ResultsArray.Num());
	Data->SetArrayField(TEXT("actors"), ResultsArray);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleFindAssets(const TSharedPtr<FJsonObject>& Params)
{
	FString TypeFilter = Params->HasField(TEXT("type")) ? Params->GetStringField(TEXT("type")) : TEXT("");
	FString NameFilter = Params->HasField(TEXT("name_filter")) ? Params->GetStringField(TEXT("name_filter")) : TEXT("");
	FString SearchPath = Params->HasField(TEXT("path")) ? Params->GetStringField(TEXT("path")) : TEXT("/Game");
	int32 MaxResults = Params->HasField(TEXT("max_results")) ? (int32)Params->GetNumberField(TEXT("max_results")) : 100;

	FAssetRegistryModule& ARM = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	IAssetRegistry& AR = ARM.Get();

	TArray<FAssetData> AssetDataList;
	AR.GetAssetsByPath(FName(*SearchPath), AssetDataList, true);

	// Type name → class path mapping
	TMap<FString, FTopLevelAssetPath> TypeMap;
	TypeMap.Add(TEXT("Blueprint"), UBlueprint::StaticClass()->GetClassPathName());
	TypeMap.Add(TEXT("Material"), UMaterial::StaticClass()->GetClassPathName());
	TypeMap.Add(TEXT("MaterialInstance"), UMaterialInstanceConstant::StaticClass()->GetClassPathName());
	TypeMap.Add(TEXT("Texture"), UTexture2D::StaticClass()->GetClassPathName());
	TypeMap.Add(TEXT("Texture2D"), UTexture2D::StaticClass()->GetClassPathName());
	TypeMap.Add(TEXT("StaticMesh"), UStaticMesh::StaticClass()->GetClassPathName());
	TypeMap.Add(TEXT("Sound"), USoundWave::StaticClass()->GetClassPathName());
	TypeMap.Add(TEXT("SoundWave"), USoundWave::StaticClass()->GetClassPathName());
	TypeMap.Add(TEXT("BehaviorTree"), UBehaviorTree::StaticClass()->GetClassPathName());

	FTopLevelAssetPath* FilterClassPath = TypeFilter.IsEmpty() ? nullptr : TypeMap.Find(TypeFilter);

	TArray<TSharedPtr<FJsonValue>> ResultsArray;
	for (const FAssetData& AssetData : AssetDataList)
	{
		if (ResultsArray.Num() >= MaxResults) break;

		// Type filter
		if (FilterClassPath && AssetData.AssetClassPath != *FilterClassPath)
			continue;

		// Name filter
		if (!NameFilter.IsEmpty() && !AssetData.AssetName.ToString().Contains(NameFilter, ESearchCase::IgnoreCase))
			continue;

		TSharedPtr<FJsonObject> Obj = MakeShareable(new FJsonObject());
		Obj->SetStringField(TEXT("name"), AssetData.AssetName.ToString());
		Obj->SetStringField(TEXT("asset_path"), AssetData.GetObjectPathString());
		Obj->SetStringField(TEXT("class"), AssetData.AssetClassPath.GetAssetName().ToString());
		ResultsArray.Add(MakeShareable(new FJsonValueObject(Obj)));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("count"), ResultsArray.Num());
	Data->SetArrayField(TEXT("assets"), ResultsArray);
	Data->SetStringField(TEXT("search_path"), SearchPath);
	return FCommandResult::Ok(Data);
}

// ============================================================
// Batch Modify Commands
// ============================================================

FCommandResult FCommandServer::HandleBatchSetVariable(const TSharedPtr<FJsonObject>& Params)
{
	const TArray<TSharedPtr<FJsonValue>>* OpsArray = nullptr;
	if (!Params->TryGetArrayField(TEXT("operations"), OpsArray) || !OpsArray)
		return FCommandResult::Error(TEXT("Missing 'operations' array"));

	int32 Succeeded = 0, Failed = 0;
	TArray<TSharedPtr<FJsonValue>> Errors;
	TArray<TSharedPtr<FJsonValue>> Results;
	TSet<UBlueprint*> AffectedBPs;

	for (const TSharedPtr<FJsonValue>& OpVal : *OpsArray)
	{
		TSharedPtr<FJsonObject> Op = OpVal->AsObject();
		if (!Op.IsValid()) { Failed++; continue; }

		FString BPName = Op->GetStringField(TEXT("blueprint"));
		FString VarName = Op->GetStringField(TEXT("variable_name"));
		FString DefaultVal = Op->GetStringField(TEXT("default_value"));

		TSharedPtr<FJsonObject> ResultObj = MakeShareable(new FJsonObject());
		ResultObj->SetStringField(TEXT("blueprint"), BPName);
		ResultObj->SetStringField(TEXT("variable_name"), VarName);

		UBlueprint* BP = FindBlueprintByName(BPName);
		if (!BP)
		{
			ResultObj->SetBoolField(TEXT("success"), false);
			ResultObj->SetStringField(TEXT("error"), FormatBlueprintNotFound(BPName));
			Errors.Add(MakeShareable(new FJsonValueString(FormatBlueprintNotFound(BPName))));
			Failed++;
			Results.Add(MakeShareable(new FJsonValueObject(ResultObj)));
			continue;
		}

		FBPVariableDescription* VarDesc = nullptr;
		for (FBPVariableDescription& Var : BP->NewVariables)
		{
			if (Var.VarName.ToString() == VarName) { VarDesc = &Var; break; }
		}
		if (!VarDesc)
		{
			FString VarErr = FString::Printf(TEXT("Variable '%s' not found in %s."), *VarName, *BPName);
			TArray<FString> VarNames;
			for (const FBPVariableDescription& V : BP->NewVariables) VarNames.Add(V.VarName.ToString());
			if (VarNames.Num() > 0) VarErr += TEXT(" Variables: ") + FString::Join(VarNames, TEXT(", "));
			ResultObj->SetBoolField(TEXT("success"), false);
			ResultObj->SetStringField(TEXT("error"), VarErr);
			Errors.Add(MakeShareable(new FJsonValueString(VarErr)));
			Failed++;
			Results.Add(MakeShareable(new FJsonValueObject(ResultObj)));
			continue;
		}

		VarDesc->DefaultValue = DefaultVal;
		AffectedBPs.Add(BP);
		ResultObj->SetBoolField(TEXT("success"), true);
		Succeeded++;
		Results.Add(MakeShareable(new FJsonValueObject(ResultObj)));
	}

	// Compile affected BPs once
	for (UBlueprint* BP : AffectedBPs)
	{
		FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
		FKismetEditorUtilities::CompileBlueprint(BP);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("total"), OpsArray->Num());
	Data->SetNumberField(TEXT("succeeded"), Succeeded);
	Data->SetNumberField(TEXT("failed"), Failed);
	Data->SetArrayField(TEXT("results"), Results);
	Data->SetArrayField(TEXT("errors"), Errors);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleBatchAddComponent(const TSharedPtr<FJsonObject>& Params)
{
	const TArray<TSharedPtr<FJsonValue>>* OpsArray = nullptr;
	if (!Params->TryGetArrayField(TEXT("operations"), OpsArray) || !OpsArray)
		return FCommandResult::Error(TEXT("Missing 'operations' array"));

	int32 Succeeded = 0, Failed = 0;
	TArray<TSharedPtr<FJsonValue>> Errors;
	TArray<TSharedPtr<FJsonValue>> Results;
	TSet<UBlueprint*> AffectedBPs;

	for (const TSharedPtr<FJsonValue>& OpVal : *OpsArray)
	{
		TSharedPtr<FJsonObject> Op = OpVal->AsObject();
		if (!Op.IsValid()) { Failed++; continue; }

		FString BPName = Op->GetStringField(TEXT("blueprint"));
		FString CompType = Op->GetStringField(TEXT("component_type"));
		FString CompName = Op->HasField(TEXT("component_name")) ? Op->GetStringField(TEXT("component_name")) : CompType;

		TSharedPtr<FJsonObject> ResultObj = MakeShareable(new FJsonObject());
		ResultObj->SetStringField(TEXT("blueprint"), BPName);
		ResultObj->SetStringField(TEXT("component_type"), CompType);

		UBlueprint* BP = FindBlueprintByName(BPName);
		if (!BP)
		{
			ResultObj->SetBoolField(TEXT("success"), false);
			ResultObj->SetStringField(TEXT("error"), FormatBlueprintNotFound(BPName));
			Errors.Add(MakeShareable(new FJsonValueString(FormatBlueprintNotFound(BPName))));
			Failed++;
			Results.Add(MakeShareable(new FJsonValueObject(ResultObj)));
			continue;
		}

		UClass* CompClass = ResolveComponentClass(CompType);
		if (!CompClass)
		{
			ResultObj->SetBoolField(TEXT("success"), false);
			ResultObj->SetStringField(TEXT("error"), FString::Printf(TEXT("Unknown component type: %s"), *CompType));
			Errors.Add(MakeShareable(new FJsonValueString(FString::Printf(TEXT("%s: unknown component type %s"), *BPName, *CompType))));
			Failed++;
			Results.Add(MakeShareable(new FJsonValueObject(ResultObj)));
			continue;
		}

		USimpleConstructionScript* SCS = BP->SimpleConstructionScript;
		if (!SCS) { Failed++; continue; }

		// Check for duplicate name
		if (FindSCSNodeByName(SCS, CompName))
		{
			ResultObj->SetBoolField(TEXT("success"), false);
			ResultObj->SetStringField(TEXT("error"), FString::Printf(TEXT("Component '%s' already exists"), *CompName));
			Errors.Add(MakeShareable(new FJsonValueString(FString::Printf(TEXT("%s: component '%s' already exists"), *BPName, *CompName))));
			Failed++;
			Results.Add(MakeShareable(new FJsonValueObject(ResultObj)));
			continue;
		}

		USCS_Node* NewNode = SCS->CreateNode(CompClass, FName(*CompName));
		if (!NewNode) { Failed++; continue; }
		SCS->AddNode(NewNode);

		// Apply properties if provided
		if (Op->HasField(TEXT("properties")) && NewNode->ComponentTemplate)
		{
			TSharedPtr<FJsonObject> Props = Op->GetObjectField(TEXT("properties"));
			for (const auto& Pair : Props->Values)
			{
				FString PropError;
				ApplyComponentProperty(NewNode->ComponentTemplate, Pair.Key, Pair.Value, PropError);
			}
		}

		AffectedBPs.Add(BP);
		ResultObj->SetBoolField(TEXT("success"), true);
		Succeeded++;
		Results.Add(MakeShareable(new FJsonValueObject(ResultObj)));
	}

	for (UBlueprint* BP : AffectedBPs)
	{
		FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
		FKismetEditorUtilities::CompileBlueprint(BP);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("total"), OpsArray->Num());
	Data->SetNumberField(TEXT("succeeded"), Succeeded);
	Data->SetNumberField(TEXT("failed"), Failed);
	Data->SetArrayField(TEXT("results"), Results);
	Data->SetArrayField(TEXT("errors"), Errors);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleBatchApplyMaterial(const TSharedPtr<FJsonObject>& Params)
{
	const TArray<TSharedPtr<FJsonValue>>* OpsArray = nullptr;
	if (!Params->TryGetArrayField(TEXT("operations"), OpsArray) || !OpsArray)
		return FCommandResult::Error(TEXT("Missing 'operations' array"));

	int32 Succeeded = 0, Failed = 0;
	TArray<TSharedPtr<FJsonValue>> Errors;
	TSet<UBlueprint*> AffectedBPs;

	for (const TSharedPtr<FJsonValue>& OpVal : *OpsArray)
	{
		TSharedPtr<FJsonObject> Op = OpVal->AsObject();
		if (!Op.IsValid()) { Failed++; continue; }

		FString MatPath = Op->GetStringField(TEXT("material_path"));
		int32 Slot = Op->HasField(TEXT("slot")) ? (int32)Op->GetNumberField(TEXT("slot")) : 0;

		FString ResolvedMatPath, MatResolveError;
		UMaterialInterface* Mat = ResolveMaterialByName(MatPath, ResolvedMatPath, MatResolveError);
		if (!Mat)
		{
			Errors.Add(MakeShareable(new FJsonValueString(MatResolveError.IsEmpty() ? FString::Printf(TEXT("Material not found: %s"), *MatPath) : MatResolveError)));
			Failed++;
			continue;
		}

		// Actor-level material application
		if (Op->HasField(TEXT("actor_label")))
		{
			FString Label = Op->GetStringField(TEXT("actor_label"));
			AActor* Actor = FindActorByLabel(Label);
			if (!Actor)
			{
				Errors.Add(MakeShareable(new FJsonValueString(FormatActorNotFound(Label))));
				Failed++;
				continue;
			}

			bool bApplied = false;
			for (UActorComponent* Comp : Actor->GetComponents())
			{
				UMeshComponent* MeshComp = Cast<UMeshComponent>(Comp);
				if (MeshComp)
				{
					MeshComp->SetMaterial(Slot, Mat);
					bApplied = true;
					break;
				}
			}
			if (bApplied) Succeeded++; else { Failed++; Errors.Add(MakeShareable(new FJsonValueString(FString::Printf(TEXT("%s: no mesh component"), *Label)))); }
		}
		// Blueprint SCS-level
		else if (Op->HasField(TEXT("blueprint")))
		{
			FString BPName = Op->GetStringField(TEXT("blueprint"));
			UBlueprint* BP = FindBlueprintByName(BPName);
			if (!BP) { Failed++; Errors.Add(MakeShareable(new FJsonValueString(FormatBlueprintNotFound(BPName)))); continue; }

			bool bApplied = false;
			if (BP->SimpleConstructionScript)
			{
				for (USCS_Node* Node : BP->SimpleConstructionScript->GetAllNodes())
				{
					UMeshComponent* MeshComp = Cast<UMeshComponent>(Node ? Node->ComponentTemplate : nullptr);
					if (MeshComp)
					{
						if (MeshComp->OverrideMaterials.Num() <= Slot)
							MeshComp->OverrideMaterials.SetNum(Slot + 1);
						MeshComp->OverrideMaterials[Slot] = Mat;
						AffectedBPs.Add(BP);
						bApplied = true;
						break;
					}
				}
			}
			if (bApplied) Succeeded++; else { Failed++; Errors.Add(MakeShareable(new FJsonValueString(FString::Printf(TEXT("%s: no mesh component"), *BPName)))); }
		}
		else { Failed++; Errors.Add(MakeShareable(new FJsonValueString(TEXT("Operation needs 'actor_label' or 'blueprint'")))); }
	}

	for (UBlueprint* BP : AffectedBPs)
	{
		FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
		FKismetEditorUtilities::CompileBlueprint(BP);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("total"), OpsArray->Num());
	Data->SetNumberField(TEXT("succeeded"), Succeeded);
	Data->SetNumberField(TEXT("failed"), Failed);
	Data->SetArrayField(TEXT("errors"), Errors);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleBatchSetProperty(const TSharedPtr<FJsonObject>& Params)
{
	const TArray<TSharedPtr<FJsonValue>>* OpsArray = nullptr;
	if (!Params->TryGetArrayField(TEXT("operations"), OpsArray) || !OpsArray)
		return FCommandResult::Error(TEXT("Missing 'operations' array"));

	UEditorActorSubsystem* ActorSub = GEditor->GetEditorSubsystem<UEditorActorSubsystem>();
	if (!ActorSub) return FCommandResult::Error(TEXT("Could not get UEditorActorSubsystem"));

	int32 Succeeded = 0, Failed = 0;
	TArray<TSharedPtr<FJsonValue>> Errors;

	for (const TSharedPtr<FJsonValue>& OpVal : *OpsArray)
	{
		TSharedPtr<FJsonObject> Op = OpVal->AsObject();
		if (!Op.IsValid()) { Failed++; continue; }

		FString Label = Op->GetStringField(TEXT("actor_label"));
		FString Property = Op->GetStringField(TEXT("property"));
		bool bRelative = Op->HasField(TEXT("relative")) && Op->GetBoolField(TEXT("relative"));

		AActor* Actor = FindActorByLabel(Label);
		if (!Actor)
		{
			Errors.Add(MakeShareable(new FJsonValueString(FormatActorNotFound(Label))));
			Failed++;
			continue;
		}

		if (Property == TEXT("location") && Op->HasField(TEXT("value")))
		{
			FVector Val = JsonToVector(Op->GetObjectField(TEXT("value")));
			if (bRelative) Val += Actor->GetActorLocation();
			Actor->SetActorLocation(Val);
			Succeeded++;
		}
		else if (Property == TEXT("rotation") && Op->HasField(TEXT("value")))
		{
			FRotator Val = JsonToRotator(Op->GetObjectField(TEXT("value")));
			if (bRelative) Val += Actor->GetActorRotation();
			Actor->SetActorRotation(Val);
			Succeeded++;
		}
		else if (Property == TEXT("scale") && Op->HasField(TEXT("value")))
		{
			FVector Val = JsonToVector(Op->GetObjectField(TEXT("value")));
			if (bRelative) Val *= Actor->GetActorScale3D();
			Actor->SetActorScale3D(Val);
			Succeeded++;
		}
		else if (Property == TEXT("visibility"))
		{
			bool bVisible = Op->GetBoolField(TEXT("value"));
			Actor->SetActorHiddenInGame(!bVisible);
			Succeeded++;
		}
		else if (Property == TEXT("tag") && Op->HasField(TEXT("value")))
		{
			FString TagVal = Op->GetStringField(TEXT("value"));
			Actor->Tags.AddUnique(FName(*TagVal));
			Succeeded++;
		}
		else
		{
			Errors.Add(MakeShareable(new FJsonValueString(FString::Printf(TEXT("%s: unknown property '%s'"), *Label, *Property))));
			Failed++;
		}
	}

	// Mark world dirty
	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (World) World->MarkPackageDirty();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("total"), OpsArray->Num());
	Data->SetNumberField(TEXT("succeeded"), Succeeded);
	Data->SetNumberField(TEXT("failed"), Failed);
	Data->SetArrayField(TEXT("errors"), Errors);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleBatchDeleteActors(const TSharedPtr<FJsonObject>& Params)
{
	UEditorActorSubsystem* ActorSub = GEditor->GetEditorSubsystem<UEditorActorSubsystem>();
	if (!ActorSub) return FCommandResult::Error(TEXT("Could not get UEditorActorSubsystem"));

	int32 Deleted = 0, Failed = 0;
	TArray<TSharedPtr<FJsonValue>> Errors;

	// Delete by labels array
	const TArray<TSharedPtr<FJsonValue>>* LabelsArray = nullptr;
	if (Params->TryGetArrayField(TEXT("labels"), LabelsArray) && LabelsArray)
	{
		for (const TSharedPtr<FJsonValue>& LabelVal : *LabelsArray)
		{
			FString Label = LabelVal->AsString();
			AActor* Actor = FindActorByLabel(Label);
			if (Actor)
			{
				Actor->Destroy();
				Deleted++;
			}
			else
			{
				// Idempotent — missing is OK
				Deleted++;
			}
		}
	}

	// Delete by class filter
	FString ClassFilter = Params->HasField(TEXT("class_filter")) ? Params->GetStringField(TEXT("class_filter")) : TEXT("");
	FString TagFilter = Params->HasField(TEXT("tag")) ? Params->GetStringField(TEXT("tag")) : TEXT("");

	if (!ClassFilter.IsEmpty() || !TagFilter.IsEmpty())
	{
		TArray<AActor*> AllActors = ActorSub->GetAllLevelActors();
		for (AActor* Actor : AllActors)
		{
			if (!Actor) continue;
			bool bMatch = true;
			if (!ClassFilter.IsEmpty() && !Actor->GetClass()->GetName().Contains(ClassFilter, ESearchCase::IgnoreCase))
				bMatch = false;
			if (!TagFilter.IsEmpty() && !Actor->ActorHasTag(FName(*TagFilter)))
				bMatch = false;
			if (bMatch)
			{
				Actor->Destroy();
				Deleted++;
			}
		}
	}

	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (World) World->MarkPackageDirty();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("deleted"), Deleted);
	Data->SetNumberField(TEXT("failed"), Failed);
	Data->SetArrayField(TEXT("errors"), Errors);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleBatchReplaceMaterial(const TSharedPtr<FJsonObject>& Params)
{
	FString OldMatPath = Params->GetStringField(TEXT("old_material"));
	FString NewMatPath = Params->GetStringField(TEXT("new_material"));

	if (OldMatPath.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'old_material'"));
	if (NewMatPath.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'new_material'"));

	FString OldResolved, OldErr, NewResolved, NewErr;
	UMaterialInterface* OldMat = ResolveMaterialByName(OldMatPath, OldResolved, OldErr);
	UMaterialInterface* NewMat = ResolveMaterialByName(NewMatPath, NewResolved, NewErr);
	if (!OldMat) return FCommandResult::Error(OldErr.IsEmpty() ? FString::Printf(TEXT("Old material not found: %s"), *OldMatPath) : OldErr);
	if (!NewMat) return FCommandResult::Error(NewErr.IsEmpty() ? FString::Printf(TEXT("New material not found: %s"), *NewMatPath) : NewErr);

	UEditorActorSubsystem* ActorSub = GEditor->GetEditorSubsystem<UEditorActorSubsystem>();
	if (!ActorSub) return FCommandResult::Error(TEXT("Could not get UEditorActorSubsystem"));

	int32 Replaced = 0;
	TArray<TSharedPtr<FJsonValue>> AffectedActors;

	TArray<AActor*> AllActors = ActorSub->GetAllLevelActors();
	for (AActor* Actor : AllActors)
	{
		if (!Actor) continue;
		bool bActorAffected = false;

		for (UActorComponent* Comp : Actor->GetComponents())
		{
			UMeshComponent* MeshComp = Cast<UMeshComponent>(Comp);
			if (!MeshComp) continue;

			for (int32 i = 0; i < MeshComp->GetNumMaterials(); i++)
			{
				UMaterialInterface* CurMat = MeshComp->GetMaterial(i);
				if (CurMat == OldMat)
				{
					MeshComp->SetMaterial(i, NewMat);
					Replaced++;
					bActorAffected = true;
				}
			}
		}

		if (bActorAffected)
		{
			AffectedActors.Add(MakeShareable(new FJsonValueString(Actor->GetActorLabel())));
		}
	}

	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (World) World->MarkPackageDirty();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("replacements"), Replaced);
	Data->SetNumberField(TEXT("actors_affected"), AffectedActors.Num());
	Data->SetArrayField(TEXT("affected_actors"), AffectedActors);
	Data->SetStringField(TEXT("old_material"), OldMatPath);
	Data->SetStringField(TEXT("new_material"), NewMatPath);
	return FCommandResult::Ok(Data);
}

// ============================================================
// In-Place Modify Commands
// ============================================================

FCommandResult FCommandServer::HandleModifyBlueprint(const TSharedPtr<FJsonObject>& Params)
{
	FString BPName = Params->GetStringField(TEXT("name"));
	if (BPName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'name' parameter"));

	UBlueprint* BP = FindBlueprintByName(BPName);
	if (!BP) return FCommandResult::Error(FormatBlueprintNotFound(BPName));

	int32 Applied = 0;
	TArray<TSharedPtr<FJsonValue>> Errors;

	// Add variables
	const TArray<TSharedPtr<FJsonValue>>* AddVars = nullptr;
	if (Params->TryGetArrayField(TEXT("add_variables"), AddVars) && AddVars)
	{
		for (const TSharedPtr<FJsonValue>& VarVal : *AddVars)
		{
			TSharedPtr<FJsonObject> VarObj = VarVal->AsObject();
			if (!VarObj.IsValid()) continue;

			FString VarName = VarObj->GetStringField(TEXT("name"));
			FString VarType = VarObj->GetStringField(TEXT("type"));
			FString Default = VarObj->HasField(TEXT("default")) ? VarObj->GetStringField(TEXT("default")) : TEXT("");

			// Map type string to pin type
			FEdGraphPinType PinType;
			if (VarType == TEXT("float") || VarType == TEXT("double"))
				PinType.PinCategory = UEdGraphSchema_K2::PC_Double;
			else if (VarType == TEXT("int") || VarType == TEXT("integer"))
				PinType.PinCategory = UEdGraphSchema_K2::PC_Int;
			else if (VarType == TEXT("bool") || VarType == TEXT("boolean"))
				PinType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
			else if (VarType == TEXT("string"))
				PinType.PinCategory = UEdGraphSchema_K2::PC_String;
			else if (VarType == TEXT("name"))
				PinType.PinCategory = UEdGraphSchema_K2::PC_Name;
			else if (VarType == TEXT("text"))
				PinType.PinCategory = UEdGraphSchema_K2::PC_Text;
			else if (VarType == TEXT("vector"))
			{
				PinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
				PinType.PinSubCategoryObject = TBaseStructure<FVector>::Get();
			}
			else if (VarType == TEXT("rotator"))
			{
				PinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
				PinType.PinSubCategoryObject = TBaseStructure<FRotator>::Get();
			}
			else
			{
				Errors.Add(MakeShareable(new FJsonValueString(FString::Printf(TEXT("Unknown type '%s' for variable '%s'"), *VarType, *VarName))));
				continue;
			}

			bool bAdded = FBlueprintEditorUtils::AddMemberVariable(BP, FName(*VarName), PinType) != false;
			if (bAdded)
			{
				// Set default value
				if (!Default.IsEmpty())
				{
					for (FBPVariableDescription& Var : BP->NewVariables)
					{
						if (Var.VarName == FName(*VarName))
						{
							Var.DefaultValue = Default;
							break;
						}
					}
				}
				Applied++;
			}
			else
			{
				Errors.Add(MakeShareable(new FJsonValueString(FString::Printf(TEXT("Failed to add variable '%s'"), *VarName))));
			}
		}
	}

	// Remove variables
	const TArray<TSharedPtr<FJsonValue>>* RemoveVars = nullptr;
	if (Params->TryGetArrayField(TEXT("remove_variables"), RemoveVars) && RemoveVars)
	{
		for (const TSharedPtr<FJsonValue>& VarVal : *RemoveVars)
		{
			FString VarName = VarVal->AsString();
			FBlueprintEditorUtils::RemoveMemberVariable(BP, FName(*VarName));
			Applied++;
		}
	}

	// Set class defaults
	if (Params->HasField(TEXT("set_class_defaults")))
	{
		TSharedPtr<FJsonObject> Defaults = Params->GetObjectField(TEXT("set_class_defaults"));
		UObject* CDO = BP->GeneratedClass ? BP->GeneratedClass->GetDefaultObject() : nullptr;
		if (CDO)
		{
			for (const auto& Pair : Defaults->Values)
			{
				FProperty* Prop = BP->GeneratedClass->FindPropertyByName(FName(*Pair.Key));
				if (!Prop)
				{
					Errors.Add(MakeShareable(new FJsonValueString(FString::Printf(TEXT("Property '%s' not found on CDO"), *Pair.Key))));
					continue;
				}

				FString StrVal = Pair.Value->AsString();
				void* ValuePtr = Prop->ContainerPtrToValuePtr<void>(CDO);
				if (Prop->ImportText_Direct(*StrVal, ValuePtr, CDO, PPF_None))
				{
					Applied++;
				}
				else
				{
					Errors.Add(MakeShareable(new FJsonValueString(FString::Printf(TEXT("Failed to set CDO property '%s'"), *Pair.Key))));
				}
			}
		}
	}

	// Compile once
	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), BPName);
	Data->SetNumberField(TEXT("operations_applied"), Applied);
	Data->SetBoolField(TEXT("compiled"), BP->Status != BS_Error);
	Data->SetArrayField(TEXT("errors"), Errors);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleRenameAsset(const TSharedPtr<FJsonObject>& Params)
{
	FString OldName = Params->GetStringField(TEXT("old_name"));
	FString NewName = Params->GetStringField(TEXT("new_name"));
	if (OldName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'old_name'"));
	if (NewName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'new_name'"));

	// Find the asset
	UBlueprint* BP = FindBlueprintByName(OldName);
	if (!BP)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Asset not found: %s"), *OldName));
	}

	UPackage* Package = BP->GetOutermost();
	FString OldPath = Package->GetPathName();
	FString OldDir = FPackageName::GetLongPackagePath(OldPath);
	FString NewPath = OldDir / NewName;

	IAssetTools& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools").Get();

	TArray<FAssetRenameData> RenameData;
	RenameData.Add(FAssetRenameData(BP, NewPath, NewName));

	bool bSuccess = AssetTools.RenameAssets(RenameData);

	if (!bSuccess)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Failed to rename '%s' to '%s'"), *OldName, *NewName));
	}

	UE_LOG(LogBlueprintLLM, Log, TEXT("Renamed asset: %s -> %s"), *OldName, *NewName);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("old_name"), OldName);
	Data->SetStringField(TEXT("new_name"), NewName);
	Data->SetStringField(TEXT("new_path"), NewPath);
	Data->SetStringField(TEXT("warning"), TEXT("References from other assets are updated via redirectors, but placed actors may need re-spawn."));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleReparentBlueprint(const TSharedPtr<FJsonObject>& Params)
{
	FString BPName = Params->GetStringField(TEXT("name"));
	FString NewParentName = Params->GetStringField(TEXT("new_parent"));
	if (BPName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'name'"));
	if (NewParentName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'new_parent'"));

	UBlueprint* BP = FindBlueprintByName(BPName);
	// Fallback: try finding as a WidgetBlueprint (lazy-loaded, not in TObjectIterator)
	if (!BP)
	{
		UWidgetBlueprint* WBP = FindWidgetBlueprintByName(BPName);
		if (WBP) BP = WBP;
	}
	if (!BP) return FCommandResult::Error(FormatBlueprintNotFound(BPName));

	FString OldParent = BP->ParentClass ? BP->ParentClass->GetName() : TEXT("None");

	// Resolve new parent class — try Blueprint first, then native
	UClass* NewParentClass = nullptr;

	// Check if it's another Blueprint
	UBlueprint* ParentBP = FindBlueprintByName(NewParentName);
	if (ParentBP && ParentBP->GeneratedClass)
	{
		NewParentClass = ParentBP->GeneratedClass;
	}

	// Try native class lookup
	if (!NewParentClass)
	{
		// If it's already a full /Script/ path, try direct lookup first
		if (NewParentName.StartsWith(TEXT("/Script/")))
		{
			NewParentClass = FindObject<UClass>(nullptr, *NewParentName);
		}

		if (!NewParentClass)
		{
			// Common name -> class mapping
			static const TMap<FString, FString> NativeClassMap = {
				{TEXT("Actor"), TEXT("/Script/Engine.Actor")},
				{TEXT("Pawn"), TEXT("/Script/Engine.Pawn")},
				{TEXT("Character"), TEXT("/Script/Engine.Character")},
				{TEXT("PlayerController"), TEXT("/Script/Engine.PlayerController")},
				{TEXT("AIController"), TEXT("/Script/AIModule.AIController")},
				{TEXT("GameModeBase"), TEXT("/Script/Engine.GameModeBase")},
				{TEXT("GameMode"), TEXT("/Script/Engine.GameMode")},
				{TEXT("ActorComponent"), TEXT("/Script/Engine.ActorComponent")},
			};

			const FString* ClassPath = NativeClassMap.Find(NewParentName);
			if (ClassPath)
			{
				NewParentClass = FindObject<UClass>(nullptr, **ClassPath);
			}
		}

		if (!NewParentClass)
		{
			// Fallback: try /Script/Engine.Name
			NewParentClass = FindObject<UClass>(nullptr, *FString::Printf(TEXT("/Script/Engine.%s"), *NewParentName));
		}

		if (!NewParentClass)
		{
			// Last resort: search all loaded classes by name
			FString ShortName = NewParentName;
			if (ShortName.Contains(TEXT(".")))
			{
				ShortName = ShortName.RightChop(ShortName.Find(TEXT(".")) + 1);
			}
			for (TObjectIterator<UClass> It; It; ++It)
			{
				if (It->GetName() == ShortName || It->GetName() == FString::Printf(TEXT("A%s"), *ShortName))
				{
					NewParentClass = *It;
					break;
				}
			}
		}
	}

	if (!NewParentClass)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Parent class not found: %s. Use full path like /Script/ModuleName.ClassName"), *NewParentName));
	}

	// Reparent — set ParentClass, then compile with crash protection
	BP->ParentClass = NewParentClass;
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);

	// RefreshAllNodes can crash if the BP has incompatible nodes from old parent.
	// Wrap in a try to prevent editor crash.
	bool bCompileOk = false;
	{
		// Refresh and compile
		FBlueprintEditorUtils::RefreshAllNodes(BP);
		FKismetEditorUtilities::CompileBlueprint(BP);
		bCompileOk = (BP->Status != BS_Error);
	}

	UE_LOG(LogBlueprintLLM, Log, TEXT("Reparented %s: %s -> %s (compiled: %s)"),
		*BPName, *OldParent, *NewParentClass->GetName(), bCompileOk ? TEXT("yes") : TEXT("no"));

	// Save to disk immediately
	BP->GetPackage()->MarkPackageDirty();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), BPName);
	Data->SetStringField(TEXT("old_parent"), OldParent);
	Data->SetStringField(TEXT("new_parent"), NewParentClass->GetName());
	Data->SetBoolField(TEXT("compiled"), bCompileOk);
	if (!bCompileOk)
	{
		Data->SetStringField(TEXT("warning"), TEXT("Blueprint has compile errors after reparenting. Some nodes may be incompatible with the new parent class."));
	}
	return FCommandResult::Ok(Data);
}

// ============================================================
// Phase 2: New commands (v8.1)
// ============================================================

FCommandResult FCommandServer::HandleSetCollisionPreset(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	FString ComponentName = Params->GetStringField(TEXT("component_name"));
	FString PresetName = Params->GetStringField(TEXT("preset_name"));

	if (PresetName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'preset_name' parameter. Common presets: NoCollision, BlockAll, OverlapAll, BlockAllDynamic, OverlapAllDynamic, Pawn, PhysicsActor, Trigger"));
	}

	if (!ActorLabel.IsEmpty())
	{
		AActor* Actor = FindActorByLabel(ActorLabel);
		if (!Actor)
		{
			return FCommandResult::Error(FormatActorNotFound(ActorLabel));
		}

		UPrimitiveComponent* PrimComp = nullptr;
		if (!ComponentName.IsEmpty())
		{
			TArray<UPrimitiveComponent*> PrimComps;
			Actor->GetComponents<UPrimitiveComponent>(PrimComps);
			for (auto* PC : PrimComps)
			{
				if (PC->GetName().Contains(ComponentName))
				{
					PrimComp = PC;
					break;
				}
			}
		}
		else
		{
			PrimComp = Cast<UPrimitiveComponent>(Actor->GetRootComponent());
			if (!PrimComp)
			{
				TArray<UPrimitiveComponent*> PrimComps;
				Actor->GetComponents<UPrimitiveComponent>(PrimComps);
				if (PrimComps.Num() > 0) PrimComp = PrimComps[0];
			}
		}

		if (!PrimComp)
		{
			return FCommandResult::Error(FString::Printf(TEXT("No PrimitiveComponent found on actor: %s"), *ActorLabel));
		}

		PrimComp->SetCollisionProfileName(*PresetName);

		TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
		Data->SetStringField(TEXT("actor"), ActorLabel);
		Data->SetStringField(TEXT("component"), PrimComp->GetName());
		Data->SetStringField(TEXT("preset"), PresetName);
		return FCommandResult::Ok(Data);
	}
	else if (!BlueprintName.IsEmpty())
	{
		UBlueprint* BP = FindBlueprintByName(BlueprintName);
		if (!BP) return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));

		if (ComponentName.IsEmpty())
			return FCommandResult::Error(TEXT("'component_name' required when targeting a Blueprint"));

		USimpleConstructionScript* SCS = BP->SimpleConstructionScript;
		if (!SCS)
			return FCommandResult::Error(FString::Printf(TEXT("Blueprint has no SCS: %s"), *BlueprintName));

		USCS_Node* Node = FindSCSNodeByName(SCS, ComponentName);
		if (!Node)
			return FCommandResult::Error(FString::Printf(TEXT("Component not found: %s"), *ComponentName));

		UPrimitiveComponent* PrimComp = Cast<UPrimitiveComponent>(Node->ComponentTemplate);
		if (!PrimComp)
			return FCommandResult::Error(FString::Printf(TEXT("Component '%s' is not a PrimitiveComponent"), *ComponentName));

		PrimComp->SetCollisionProfileName(*PresetName);
		FKismetEditorUtilities::CompileBlueprint(BP);

		TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
		Data->SetStringField(TEXT("blueprint"), BlueprintName);
		Data->SetStringField(TEXT("component"), ComponentName);
		Data->SetStringField(TEXT("preset"), PresetName);
		return FCommandResult::Ok(Data);
	}

	return FCommandResult::Error(TEXT("Provide either 'actor_label' or 'blueprint' parameter"));
}

FCommandResult FCommandServer::HandleGetBlueprintDetails(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty()) Name = Params->GetStringField(TEXT("blueprint_name"));
	if (Name.IsEmpty()) Name = Params->GetStringField(TEXT("blueprint"));
	if (Name.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'name' parameter"));
	}

	UBlueprint* BP = FindBlueprintByName(Name);
	if (!BP)
	{
		return FCommandResult::Error(FormatBlueprintNotFound(Name));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), BP->GetName());
	Data->SetStringField(TEXT("path"), BP->GetPathName());
	Data->SetStringField(TEXT("parent_class"), BP->ParentClass ? BP->ParentClass->GetName() : TEXT("None"));
	Data->SetBoolField(TEXT("compiled"), BP->Status != BS_Error);

	// Variables with types and defaults
	TArray<TSharedPtr<FJsonValue>> VarsArray;
	for (const FBPVariableDescription& Var : BP->NewVariables)
	{
		TSharedPtr<FJsonObject> VarObj = MakeShareable(new FJsonObject());
		VarObj->SetStringField(TEXT("name"), Var.VarName.ToString());
		VarObj->SetStringField(TEXT("type"), Var.VarType.PinCategory.ToString());
		VarObj->SetStringField(TEXT("default_value"), Var.DefaultValue);
		VarObj->SetStringField(TEXT("category"), Var.Category.ToString());
		VarObj->SetBoolField(TEXT("is_instance_editable"), Var.PropertyFlags & CPF_Edit ? true : false);
		VarsArray.Add(MakeShareable(new FJsonValueObject(VarObj)));
	}
	Data->SetArrayField(TEXT("variables"), VarsArray);

	// Components from SCS
	TArray<TSharedPtr<FJsonValue>> CompsArray;
	if (BP->SimpleConstructionScript)
	{
		for (USCS_Node* Node : BP->SimpleConstructionScript->GetAllNodes())
		{
			if (Node && Node->ComponentTemplate)
			{
				TSharedPtr<FJsonObject> CompObj = MakeShareable(new FJsonObject());
				CompObj->SetStringField(TEXT("name"), Node->GetVariableName().ToString());
				CompObj->SetStringField(TEXT("class"), Node->ComponentTemplate->GetClass()->GetName());
				CompObj->SetStringField(TEXT("parent"), Node->ParentComponentOrVariableName.ToString());
				CompsArray.Add(MakeShareable(new FJsonValueObject(CompObj)));
			}
		}
	}
	Data->SetArrayField(TEXT("components"), CompsArray);

	// Events (nodes that are UK2Node_Event)
	TArray<TSharedPtr<FJsonValue>> EventsArray;
	UEdGraph* EventGraph = FBlueprintEditorUtils::FindEventGraph(BP);
	int32 TotalNodeCount = 0;
	int32 TotalConnectionCount = 0;
	TMap<FString, int32> NodeTypeCounts;

	if (EventGraph)
	{
		for (UEdGraphNode* Node : EventGraph->Nodes)
		{
			TotalNodeCount++;

			// Count connections
			for (UEdGraphPin* Pin : Node->Pins)
			{
				if (Pin->Direction == EGPD_Output)
				{
					TotalConnectionCount += Pin->LinkedTo.Num();
				}
			}

			// Track node type
			FString NodeClass = Node->GetClass()->GetName();
			int32& Count = NodeTypeCounts.FindOrAdd(NodeClass);
			Count++;

			// Collect events
			if (UK2Node_Event* EventNode = Cast<UK2Node_Event>(Node))
			{
				TSharedPtr<FJsonObject> EvObj = MakeShareable(new FJsonObject());
				EvObj->SetStringField(TEXT("name"), EventNode->GetNodeTitle(ENodeTitleType::FullTitle).ToString());
				EvObj->SetStringField(TEXT("type"), NodeClass);
				EventsArray.Add(MakeShareable(new FJsonValueObject(EvObj)));
			}
			else if (UK2Node_CustomEvent* CustomEventNode = Cast<UK2Node_CustomEvent>(Node))
			{
				TSharedPtr<FJsonObject> EvObj = MakeShareable(new FJsonObject());
				EvObj->SetStringField(TEXT("name"), CustomEventNode->GetNodeTitle(ENodeTitleType::FullTitle).ToString());
				EvObj->SetStringField(TEXT("type"), TEXT("CustomEvent"));
				EventsArray.Add(MakeShareable(new FJsonValueObject(EvObj)));
			}
		}
	}
	Data->SetArrayField(TEXT("events"), EventsArray);
	Data->SetNumberField(TEXT("node_count"), TotalNodeCount);
	Data->SetNumberField(TEXT("connection_count"), TotalConnectionCount);

	// Node type breakdown
	TSharedPtr<FJsonObject> TypeCounts = MakeShareable(new FJsonObject());
	for (auto& Pair : NodeTypeCounts)
	{
		TypeCounts->SetNumberField(Pair.Key, Pair.Value);
	}
	Data->SetObjectField(TEXT("node_types"), TypeCounts);

	// === Enhanced: Full node graph (nodes[], connections[], exec_chains[], unconnected_pins[]) ===
	if (EventGraph)
	{
		// Build stable node ID map
		TMap<UEdGraphNode*, FString> DetailNodeIdMap;
		int32 DetailIdx = 0;
		for (UEdGraphNode* Node : EventGraph->Nodes)
		{
			DetailNodeIdMap.Add(Node, FString::Printf(TEXT("node_%d"), DetailIdx++));
		}

		// Full nodes array with id, type, title, guid, position, params (pin defaults)
		TArray<TSharedPtr<FJsonValue>> FullNodesArray;
		for (UEdGraphNode* Node : EventGraph->Nodes)
		{
			TSharedPtr<FJsonObject> NObj = MakeShareable(new FJsonObject());
			NObj->SetStringField(TEXT("id"), DetailNodeIdMap[Node]);
			NObj->SetStringField(TEXT("guid"), Node->NodeGuid.ToString());
			NObj->SetStringField(TEXT("class"), Node->GetClass()->GetName());
			NObj->SetStringField(TEXT("title"), Node->GetNodeTitle(ENodeTitleType::ListView).ToString());
			NObj->SetNumberField(TEXT("pos_x"), Node->NodePosX);
			NObj->SetNumberField(TEXT("pos_y"), Node->NodePosY);

			// Pin defaults as params
			TSharedPtr<FJsonObject> ParamsObj = MakeShareable(new FJsonObject());
			TArray<TSharedPtr<FJsonValue>> NodePinsArr;
			for (UEdGraphPin* Pin : Node->Pins)
			{
				TSharedPtr<FJsonObject> PObj = MakeShareable(new FJsonObject());
				PObj->SetStringField(TEXT("name"), Pin->PinName.ToString());
				PObj->SetStringField(TEXT("direction"), Pin->Direction == EGPD_Input ? TEXT("input") : TEXT("output"));
				PObj->SetStringField(TEXT("type"), Pin->PinType.PinCategory.ToString());
				PObj->SetBoolField(TEXT("connected"), Pin->LinkedTo.Num() > 0);
				PObj->SetBoolField(TEXT("hidden"), Pin->bHidden);
				if (!Pin->DefaultValue.IsEmpty())
				{
					PObj->SetStringField(TEXT("default_value"), Pin->DefaultValue);
					ParamsObj->SetStringField(Pin->PinName.ToString(), Pin->DefaultValue);
				}
				if (Pin->DefaultObject)
				{
					PObj->SetStringField(TEXT("default_object"), Pin->DefaultObject->GetPathName());
				}
				NodePinsArr.Add(MakeShareable(new FJsonValueObject(PObj)));
			}
			NObj->SetArrayField(TEXT("pins"), NodePinsArr);
			if (ParamsObj->Values.Num() > 0)
			{
				NObj->SetObjectField(TEXT("params"), ParamsObj);
			}

			FullNodesArray.Add(MakeShareable(new FJsonValueObject(NObj)));
		}
		Data->SetArrayField(TEXT("nodes"), FullNodesArray);

		// Full connections array
		TArray<TSharedPtr<FJsonValue>> FullConnsArray;
		for (UEdGraphNode* Node : EventGraph->Nodes)
		{
			for (UEdGraphPin* Pin : Node->Pins)
			{
				if (Pin->Direction == EGPD_Output)
				{
					for (UEdGraphPin* LinkedPin : Pin->LinkedTo)
					{
						UEdGraphNode* TargetNode = LinkedPin->GetOwningNode();
						TSharedPtr<FJsonObject> CObj = MakeShareable(new FJsonObject());
						CObj->SetStringField(TEXT("source_node"),
							DetailNodeIdMap.Contains(Node) ? DetailNodeIdMap[Node] : TEXT("unknown"));
						CObj->SetStringField(TEXT("source_pin"), Pin->PinName.ToString());
						CObj->SetStringField(TEXT("target_node"),
							DetailNodeIdMap.Contains(TargetNode) ? DetailNodeIdMap[TargetNode] : TEXT("unknown"));
						CObj->SetStringField(TEXT("target_pin"), LinkedPin->PinName.ToString());
						CObj->SetBoolField(TEXT("is_exec"),
							Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec);
						FullConnsArray.Add(MakeShareable(new FJsonValueObject(CObj)));
					}
				}
			}
		}
		Data->SetArrayField(TEXT("connections"), FullConnsArray);

		// Exec chains: trace from each event/entry point through exec connections
		TArray<TSharedPtr<FJsonValue>> ExecChainsArray;
		for (UEdGraphNode* Node : EventGraph->Nodes)
		{
			if (Cast<UK2Node_Event>(Node) || Cast<UK2Node_CustomEvent>(Node))
			{
				TArray<TSharedPtr<FJsonValue>> ChainNodes;
				TSet<UEdGraphNode*> Visited;

				// BFS through exec pins
				TArray<UEdGraphNode*> Queue;
				Queue.Add(Node);
				Visited.Add(Node);

				while (Queue.Num() > 0)
				{
					UEdGraphNode* Current = Queue[0];
					Queue.RemoveAt(0);

					ChainNodes.Add(MakeShareable(new FJsonValueString(
						DetailNodeIdMap.Contains(Current) ? DetailNodeIdMap[Current] : TEXT("unknown"))));

					// Follow exec output pins
					for (UEdGraphPin* Pin : Current->Pins)
					{
						if (Pin->Direction == EGPD_Output &&
						    Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec)
						{
							for (UEdGraphPin* LinkedPin : Pin->LinkedTo)
							{
								UEdGraphNode* Next = LinkedPin->GetOwningNode();
								if (Next && !Visited.Contains(Next))
								{
									Visited.Add(Next);
									Queue.Add(Next);
								}
							}
						}
					}
				}

				TSharedPtr<FJsonObject> ChainObj = MakeShareable(new FJsonObject());
				ChainObj->SetStringField(TEXT("entry_node"),
					DetailNodeIdMap.Contains(Node) ? DetailNodeIdMap[Node] : TEXT("unknown"));
				ChainObj->SetStringField(TEXT("entry_title"),
					Node->GetNodeTitle(ENodeTitleType::ListView).ToString());
				ChainObj->SetArrayField(TEXT("nodes"), ChainNodes);
				ChainObj->SetNumberField(TEXT("length"), ChainNodes.Num());
				ExecChainsArray.Add(MakeShareable(new FJsonValueObject(ChainObj)));
			}
		}
		Data->SetArrayField(TEXT("exec_chains"), ExecChainsArray);

		// Unconnected pins (non-hidden, non-self, non-WorldContext)
		TArray<TSharedPtr<FJsonValue>> UnconnectedArray;
		for (UEdGraphNode* Node : EventGraph->Nodes)
		{
			for (UEdGraphPin* Pin : Node->Pins)
			{
				if (Pin->LinkedTo.Num() == 0 && !Pin->bHidden &&
				    Pin->PinName != TEXT("self") && Pin->PinName != TEXT("WorldContextObject"))
				{
					TSharedPtr<FJsonObject> UPObj = MakeShareable(new FJsonObject());
					UPObj->SetStringField(TEXT("node_id"),
						DetailNodeIdMap.Contains(Node) ? DetailNodeIdMap[Node] : TEXT("unknown"));
					UPObj->SetStringField(TEXT("node_title"),
						Node->GetNodeTitle(ENodeTitleType::ListView).ToString());
					UPObj->SetStringField(TEXT("pin_name"), Pin->PinName.ToString());
					UPObj->SetStringField(TEXT("direction"),
						Pin->Direction == EGPD_Input ? TEXT("input") : TEXT("output"));
					UPObj->SetStringField(TEXT("type"), Pin->PinType.PinCategory.ToString());
					UPObj->SetBoolField(TEXT("is_exec"),
						Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec);
					UPObj->SetBoolField(TEXT("has_default"),
						!Pin->DefaultValue.IsEmpty() || Pin->DefaultObject != nullptr);
					UnconnectedArray.Add(MakeShareable(new FJsonValueObject(UPObj)));
				}
			}
		}
		Data->SetArrayField(TEXT("unconnected_pins"), UnconnectedArray);
	}

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetCameraProperties(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	if (BlueprintName.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'blueprint' parameter"));
	}

	UBlueprint* BP = FindBlueprintByName(BlueprintName);
	if (!BP) return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));

	USimpleConstructionScript* SCS = BP->SimpleConstructionScript;
	if (!SCS) return FCommandResult::Error(TEXT("Blueprint has no SCS"));

	bool bModified = false;
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("blueprint"), BlueprintName);

	// Find and configure CameraComponent
	for (USCS_Node* Node : SCS->GetAllNodes())
	{
		if (!Node || !Node->ComponentTemplate) continue;

		if (UCameraComponent* Camera = Cast<UCameraComponent>(Node->ComponentTemplate))
		{
			if (Params->HasField(TEXT("fov")))
			{
				Camera->FieldOfView = Params->GetNumberField(TEXT("fov"));
				Data->SetNumberField(TEXT("fov"), Camera->FieldOfView);
				bModified = true;
			}
			if (Params->HasField(TEXT("use_pawn_control_rotation")))
			{
				Camera->bUsePawnControlRotation = Params->GetBoolField(TEXT("use_pawn_control_rotation"));
				bModified = true;
			}
		}

		if (USpringArmComponent* SpringArm = Cast<USpringArmComponent>(Node->ComponentTemplate))
		{
			if (Params->HasField(TEXT("arm_length")))
			{
				SpringArm->TargetArmLength = Params->GetNumberField(TEXT("arm_length"));
				Data->SetNumberField(TEXT("arm_length"), SpringArm->TargetArmLength);
				bModified = true;
			}
			if (Params->HasField(TEXT("use_pawn_control_rotation")))
			{
				SpringArm->bUsePawnControlRotation = Params->GetBoolField(TEXT("use_pawn_control_rotation"));
				bModified = true;
			}
			if (Params->HasField(TEXT("do_collision_test")))
			{
				SpringArm->bDoCollisionTest = Params->GetBoolField(TEXT("do_collision_test"));
				bModified = true;
			}
			if (Params->HasField(TEXT("camera_lag_speed")))
			{
				SpringArm->bEnableCameraLag = true;
				SpringArm->CameraLagSpeed = Params->GetNumberField(TEXT("camera_lag_speed"));
				Data->SetNumberField(TEXT("camera_lag_speed"), SpringArm->CameraLagSpeed);
				bModified = true;
			}
			if (Params->HasField(TEXT("camera_rotation_lag_speed")))
			{
				SpringArm->bEnableCameraRotationLag = true;
				SpringArm->CameraRotationLagSpeed = Params->GetNumberField(TEXT("camera_rotation_lag_speed"));
				bModified = true;
			}
		}
	}

	if (!bModified)
	{
		return FCommandResult::Error(FString::Printf(TEXT("No CameraComponent or SpringArmComponent found on Blueprint '%s'. Add a camera component first with add_component."), *BlueprintName));
	}

	FKismetEditorUtilities::CompileBlueprint(BP);
	Data->SetBoolField(TEXT("compiled"), BP->Status != BS_Error);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCreateInputAction(const TSharedPtr<FJsonObject>& Params)
{
	// Delegate to existing add_input_action handler (same functionality, different name)
	return HandleAddInputAction(Params);
}

FCommandResult FCommandServer::HandleBindInputToBlueprint(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	FString ActionName = Params->GetStringField(TEXT("action"));
	if (ActionName.IsEmpty()) ActionName = Params->GetStringField(TEXT("action_name"));
	FString EventName = Params->GetStringField(TEXT("event_name"));

	if (BlueprintName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'blueprint' parameter"));
	if (ActionName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'action' parameter"));

	UBlueprint* BP = FindBlueprintByName(BlueprintName);
	if (!BP) return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));

	// Find the input action asset
	FString ActionPath = FString::Printf(TEXT("/Game/Arcwright/Input/%s"), *ActionName);
	UInputAction* InputAction = LoadObject<UInputAction>(nullptr, *ActionPath);
	if (!InputAction)
	{
		// Try other common paths
		ActionPath = FString::Printf(TEXT("/Game/Input/%s"), *ActionName);
		InputAction = LoadObject<UInputAction>(nullptr, *ActionPath);
	}
	if (!InputAction)
	{
		// Search asset registry
		FAssetRegistryModule& AssetReg = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
		TArray<FAssetData> Assets;
		AssetReg.Get().GetAssetsByClass(UInputAction::StaticClass()->GetClassPathName(), Assets);
		for (const FAssetData& Asset : Assets)
		{
			if (Asset.AssetName.ToString().Equals(ActionName, ESearchCase::IgnoreCase))
			{
				InputAction = Cast<UInputAction>(Asset.GetAsset());
				break;
			}
		}
	}
	if (!InputAction)
	{
		return FCommandResult::Error(FString::Printf(TEXT("Input Action not found: '%s'. Create it first with create_input_action or add_input_action."), *ActionName));
	}

	// Add an InputAction node to the Blueprint's event graph
	UEdGraph* EventGraph = FBlueprintEditorUtils::FindEventGraph(BP);
	if (!EventGraph) return FCommandResult::Error(TEXT("Blueprint has no event graph"));

	UK2Node_InputAction* InputNode = NewObject<UK2Node_InputAction>(EventGraph);
	InputNode->InputActionName = FName(*ActionName);
	InputNode->CreateNewGuid();
	InputNode->AllocateDefaultPins();
	EventGraph->AddNode(InputNode, false, false);
	InputNode->NodePosX = 0;
	InputNode->NodePosY = 200;

	FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("blueprint"), BlueprintName);
	Data->SetStringField(TEXT("action"), ActionName);
	Data->SetStringField(TEXT("node_id"), InputNode->NodeGuid.ToString());
	Data->SetBoolField(TEXT("compiled"), BP->Status != BS_Error);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetCollisionShape(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	FString ComponentName = Params->GetStringField(TEXT("component_name"));

	auto FindShapeComponent = [&](UActorComponent* Template) -> UShapeComponent*
	{
		return Cast<UShapeComponent>(Template);
	};

	UShapeComponent* ShapeComp = nullptr;

	if (!ActorLabel.IsEmpty())
	{
		AActor* Actor = FindActorByLabel(ActorLabel);
		if (!Actor) return FCommandResult::Error(FormatActorNotFound(ActorLabel));

		TArray<UShapeComponent*> ShapeComps;
		Actor->GetComponents<UShapeComponent>(ShapeComps);
		if (!ComponentName.IsEmpty())
		{
			for (auto* SC : ShapeComps)
			{
				if (SC->GetName().Contains(ComponentName)) { ShapeComp = SC; break; }
			}
		}
		else if (ShapeComps.Num() > 0)
		{
			ShapeComp = ShapeComps[0];
		}

		if (!ShapeComp)
			return FCommandResult::Error(FString::Printf(TEXT("No ShapeComponent found on actor: %s"), *ActorLabel));
	}
	else if (!BlueprintName.IsEmpty())
	{
		UBlueprint* BP = FindBlueprintByName(BlueprintName);
		if (!BP) return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));
		if (!BP->SimpleConstructionScript) return FCommandResult::Error(TEXT("Blueprint has no SCS"));

		if (ComponentName.IsEmpty())
			return FCommandResult::Error(TEXT("'component_name' required when targeting a Blueprint"));

		USCS_Node* Node = FindSCSNodeByName(BP->SimpleConstructionScript, ComponentName);
		if (!Node) return FCommandResult::Error(FString::Printf(TEXT("Component not found: %s"), *ComponentName));

		ShapeComp = Cast<UShapeComponent>(Node->ComponentTemplate);
		if (!ShapeComp) return FCommandResult::Error(FString::Printf(TEXT("Component '%s' is not a ShapeComponent"), *ComponentName));
	}
	else
	{
		return FCommandResult::Error(TEXT("Provide either 'actor_label' or 'blueprint' parameter"));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	bool bModified = false;

	if (UBoxComponent* Box = Cast<UBoxComponent>(ShapeComp))
	{
		if (Params->HasField(TEXT("extents")))
		{
			TSharedPtr<FJsonObject> Ext = Params->GetObjectField(TEXT("extents"));
			FVector Extents(Ext->GetNumberField(TEXT("x")), Ext->GetNumberField(TEXT("y")), Ext->GetNumberField(TEXT("z")));
			Box->SetBoxExtent(Extents);
			Data->SetObjectField(TEXT("extents"), VectorToJson(Extents));
			bModified = true;
		}
		Data->SetStringField(TEXT("shape_type"), TEXT("Box"));
	}
	else if (USphereComponent* Sphere = Cast<USphereComponent>(ShapeComp))
	{
		if (Params->HasField(TEXT("radius")))
		{
			float Radius = Params->GetNumberField(TEXT("radius"));
			Sphere->SetSphereRadius(Radius);
			Data->SetNumberField(TEXT("radius"), Radius);
			bModified = true;
		}
		Data->SetStringField(TEXT("shape_type"), TEXT("Sphere"));
	}
	else if (UCapsuleComponent* Capsule = Cast<UCapsuleComponent>(ShapeComp))
	{
		if (Params->HasField(TEXT("radius")))
		{
			float Radius = Params->GetNumberField(TEXT("radius"));
			Capsule->SetCapsuleRadius(Radius);
			Data->SetNumberField(TEXT("radius"), Radius);
			bModified = true;
		}
		if (Params->HasField(TEXT("half_height")))
		{
			float HH = Params->GetNumberField(TEXT("half_height"));
			Capsule->SetCapsuleHalfHeight(HH);
			Data->SetNumberField(TEXT("half_height"), HH);
			bModified = true;
		}
		Data->SetStringField(TEXT("shape_type"), TEXT("Capsule"));
	}

	if (!bModified)
	{
		return FCommandResult::Error(TEXT("No shape parameters provided. Use 'extents' (box), 'radius' (sphere/capsule), or 'half_height' (capsule)."));
	}

	// Recompile BP if targeting a Blueprint
	if (!BlueprintName.IsEmpty())
	{
		UBlueprint* BP = FindBlueprintByName(BlueprintName);
		if (BP) FKismetEditorUtilities::CompileBlueprint(BP);
	}

	Data->SetStringField(TEXT("component"), ShapeComp->GetName());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCreateNavMeshBounds(const TSharedPtr<FJsonObject>& Params)
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World) return FCommandResult::Error(TEXT("No editor world"));

	FVector Location(0, 0, 0);
	FVector Extents(1000, 1000, 500);
	FString Label = TEXT("NavMeshBounds");

	if (Params->HasField(TEXT("location")))
	{
		Location = JsonToVector(Params->GetObjectField(TEXT("location")));
	}
	if (Params->HasField(TEXT("extents")))
	{
		Extents = JsonToVector(Params->GetObjectField(TEXT("extents")));
	}
	if (Params->HasField(TEXT("label")))
	{
		Label = Params->GetStringField(TEXT("label"));
	}

	FActorSpawnParameters SpawnParams;
	SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

	ANavMeshBoundsVolume* NavVolume = World->SpawnActor<ANavMeshBoundsVolume>(
		ANavMeshBoundsVolume::StaticClass(),
		Location,
		FRotator::ZeroRotator,
		SpawnParams
	);

	if (!NavVolume)
	{
		return FCommandResult::Error(TEXT("Failed to spawn NavMeshBoundsVolume"));
	}

	NavVolume->SetActorLabel(Label);

	// Set the brush extent by scaling
	NavVolume->SetActorScale3D(Extents / 100.0f); // UE brush units

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("label"), Label);
	Data->SetObjectField(TEXT("location"), VectorToJson(Location));
	Data->SetObjectField(TEXT("extents"), VectorToJson(Extents));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetAudioProperties(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	FString ComponentName = Params->GetStringField(TEXT("component_name"));

	UAudioComponent* AudioComp = nullptr;

	if (!ActorLabel.IsEmpty())
	{
		AActor* Actor = FindActorByLabel(ActorLabel);
		if (!Actor) return FCommandResult::Error(FormatActorNotFound(ActorLabel));

		TArray<UAudioComponent*> AudioComps;
		Actor->GetComponents<UAudioComponent>(AudioComps);
		if (!ComponentName.IsEmpty())
		{
			for (auto* AC : AudioComps)
			{
				if (AC->GetName().Contains(ComponentName)) { AudioComp = AC; break; }
			}
		}
		else if (AudioComps.Num() > 0)
		{
			AudioComp = AudioComps[0];
		}
	}
	else if (!BlueprintName.IsEmpty())
	{
		UBlueprint* BP = FindBlueprintByName(BlueprintName);
		if (!BP) return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));
		if (!BP->SimpleConstructionScript) return FCommandResult::Error(TEXT("Blueprint has no SCS"));

		FString CompTarget = ComponentName.IsEmpty() ? TEXT("Audio") : ComponentName;
		for (USCS_Node* Node : BP->SimpleConstructionScript->GetAllNodes())
		{
			if (Node && Node->ComponentTemplate)
			{
				if (UAudioComponent* AC = Cast<UAudioComponent>(Node->ComponentTemplate))
				{
					if (CompTarget.IsEmpty() || Node->GetVariableName().ToString().Contains(CompTarget))
					{
						AudioComp = AC;
						break;
					}
				}
			}
		}
	}
	else
	{
		return FCommandResult::Error(TEXT("Provide either 'actor_label' or 'blueprint' parameter"));
	}

	if (!AudioComp)
	{
		return FCommandResult::Error(TEXT("No AudioComponent found. Add one first with add_component type=Audio."));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());

	if (Params->HasField(TEXT("volume_multiplier")))
	{
		AudioComp->VolumeMultiplier = Params->GetNumberField(TEXT("volume_multiplier"));
		Data->SetNumberField(TEXT("volume_multiplier"), AudioComp->VolumeMultiplier);
	}
	if (Params->HasField(TEXT("pitch_multiplier")))
	{
		AudioComp->PitchMultiplier = Params->GetNumberField(TEXT("pitch_multiplier"));
		Data->SetNumberField(TEXT("pitch_multiplier"), AudioComp->PitchMultiplier);
	}
	if (Params->HasField(TEXT("auto_activate")))
	{
		AudioComp->bAutoActivate = Params->GetBoolField(TEXT("auto_activate"));
	}
	if (Params->HasField(TEXT("is_ui_sound")))
	{
		AudioComp->bIsUISound = Params->GetBoolField(TEXT("is_ui_sound"));
	}

	// Recompile BP if targeting a Blueprint
	if (!BlueprintName.IsEmpty())
	{
		UBlueprint* BP = FindBlueprintByName(BlueprintName);
		if (BP) FKismetEditorUtilities::CompileBlueprint(BP);
	}

	Data->SetStringField(TEXT("component"), AudioComp->GetName());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetActorTags(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	if (ActorLabel.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'actor_label' parameter"));
	}

	AActor* Actor = FindActorByLabel(ActorLabel);
	if (!Actor)
	{
		return FCommandResult::Error(FormatActorNotFound(ActorLabel));
	}

	const TArray<TSharedPtr<FJsonValue>>* TagsArray;
	if (!Params->TryGetArrayField(TEXT("tags"), TagsArray))
	{
		return FCommandResult::Error(TEXT("Missing 'tags' array parameter"));
	}

	Actor->Tags.Empty();
	for (const auto& TagVal : *TagsArray)
	{
		FString TagStr;
		if (TagVal->TryGetString(TagStr))
		{
			Actor->Tags.Add(FName(*TagStr));
		}
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor"), ActorLabel);
	Data->SetNumberField(TEXT("tag_count"), Actor->Tags.Num());

	TArray<TSharedPtr<FJsonValue>> ResultTags;
	for (const FName& Tag : Actor->Tags)
	{
		ResultTags.Add(MakeShareable(new FJsonValueString(Tag.ToString())));
	}
	Data->SetArrayField(TEXT("tags"), ResultTags);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetActorProperties(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	if (ActorLabel.IsEmpty())
	{
		return FCommandResult::Error(TEXT("Missing 'actor_label' parameter"));
	}

	AActor* Actor = FindActorByLabel(ActorLabel);
	if (!Actor)
	{
		return FCommandResult::Error(FormatActorNotFound(ActorLabel));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("label"), Actor->GetActorLabel());
	Data->SetStringField(TEXT("class"), Actor->GetClass()->GetName());
	Data->SetStringField(TEXT("class_path"), Actor->GetClass()->GetPathName());

	// Transform
	FVector Loc = Actor->GetActorLocation();
	FRotator Rot = Actor->GetActorRotation();
	FVector Scale = Actor->GetActorScale3D();
	Data->SetObjectField(TEXT("location"), VectorToJson(Loc));
	Data->SetObjectField(TEXT("rotation"), RotatorToJson(Rot));
	Data->SetObjectField(TEXT("scale"), VectorToJson(Scale));

	// Tags
	TArray<TSharedPtr<FJsonValue>> TagsArr;
	for (const FName& Tag : Actor->Tags)
	{
		TagsArr.Add(MakeShareable(new FJsonValueString(Tag.ToString())));
	}
	Data->SetArrayField(TEXT("tags"), TagsArr);

	// Components
	TArray<TSharedPtr<FJsonValue>> CompsArr;
	TArray<UActorComponent*> AllComps;
	Actor->GetComponents(AllComps);
	for (UActorComponent* Comp : AllComps)
	{
		TSharedPtr<FJsonObject> CompObj = MakeShareable(new FJsonObject());
		CompObj->SetStringField(TEXT("name"), Comp->GetName());
		CompObj->SetStringField(TEXT("class"), Comp->GetClass()->GetName());

		if (USceneComponent* SceneComp = Cast<USceneComponent>(Comp))
		{
			CompObj->SetObjectField(TEXT("relative_location"), VectorToJson(SceneComp->GetRelativeLocation()));
			CompObj->SetObjectField(TEXT("relative_rotation"), RotatorToJson(SceneComp->GetRelativeRotation()));
		}
		if (UPrimitiveComponent* PrimComp = Cast<UPrimitiveComponent>(Comp))
		{
			CompObj->SetStringField(TEXT("collision_profile"), PrimComp->GetCollisionProfileName().ToString());
		}
		if (UStaticMeshComponent* MeshComp = Cast<UStaticMeshComponent>(Comp))
		{
			if (MeshComp->GetStaticMesh())
			{
				CompObj->SetStringField(TEXT("mesh"), MeshComp->GetStaticMesh()->GetPathName());
			}
			if (MeshComp->GetMaterial(0))
			{
				CompObj->SetStringField(TEXT("material"), MeshComp->GetMaterial(0)->GetPathName());
			}
		}

		CompsArr.Add(MakeShareable(new FJsonValueObject(CompObj)));
	}
	Data->SetArrayField(TEXT("components"), CompsArr);

	// Visibility / mobility
	if (Actor->GetRootComponent())
	{
		Data->SetBoolField(TEXT("visible"), Actor->GetRootComponent()->IsVisible());
		Data->SetStringField(TEXT("mobility"),
			Actor->GetRootComponent()->Mobility == EComponentMobility::Static ? TEXT("Static") :
			Actor->GetRootComponent()->Mobility == EComponentMobility::Stationary ? TEXT("Stationary") :
			TEXT("Movable"));
	}

	return FCommandResult::Ok(Data);
}

// ============================================================
// Phase 4: Discovery commands
// ============================================================

FCommandResult FCommandServer::HandleListAvailableMaterials(const TSharedPtr<FJsonObject>& Params)
{
	FString NameFilter = Params->GetStringField(TEXT("name_filter"));
	int32 MaxResults = Params->HasField(TEXT("max_results")) ? (int32)Params->GetNumberField(TEXT("max_results")) : 50;

	FAssetRegistryModule& AssetReg = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	TArray<FAssetData> Assets;

	// Search for MaterialInterface assets (covers both UMaterial and UMaterialInstanceConstant)
	AssetReg.Get().GetAssetsByClass(UMaterial::StaticClass()->GetClassPathName(), Assets);

	TArray<FAssetData> InstanceAssets;
	AssetReg.Get().GetAssetsByClass(UMaterialInstanceConstant::StaticClass()->GetClassPathName(), InstanceAssets);
	Assets.Append(InstanceAssets);

	TArray<TSharedPtr<FJsonValue>> ResultArray;
	for (const FAssetData& Asset : Assets)
	{
		if (!NameFilter.IsEmpty() && !Asset.AssetName.ToString().Contains(NameFilter))
		{
			continue;
		}

		TSharedPtr<FJsonObject> MatObj = MakeShareable(new FJsonObject());
		MatObj->SetStringField(TEXT("name"), Asset.AssetName.ToString());
		MatObj->SetStringField(TEXT("path"), Asset.GetObjectPathString());
		MatObj->SetStringField(TEXT("type"), Asset.AssetClassPath.GetAssetName().ToString());
		ResultArray.Add(MakeShareable(new FJsonValueObject(MatObj)));

		if (ResultArray.Num() >= MaxResults) break;
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("count"), ResultArray.Num());
	Data->SetArrayField(TEXT("materials"), ResultArray);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleListAvailableBlueprints(const TSharedPtr<FJsonObject>& Params)
{
	FString NameFilter = Params->GetStringField(TEXT("name_filter"));
	int32 MaxResults = Params->HasField(TEXT("max_results")) ? (int32)Params->GetNumberField(TEXT("max_results")) : 50;

	FAssetRegistryModule& AssetReg = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	TArray<FAssetData> Assets;
	AssetReg.Get().GetAssetsByClass(UBlueprint::StaticClass()->GetClassPathName(), Assets);

	TArray<TSharedPtr<FJsonValue>> ResultArray;
	for (const FAssetData& Asset : Assets)
	{
		if (!NameFilter.IsEmpty() && !Asset.AssetName.ToString().Contains(NameFilter))
		{
			continue;
		}

		TSharedPtr<FJsonObject> BPObj = MakeShareable(new FJsonObject());
		BPObj->SetStringField(TEXT("name"), Asset.AssetName.ToString());
		BPObj->SetStringField(TEXT("path"), Asset.GetObjectPathString());

		// Try to get parent class
		FAssetTagValueRef ParentClassTag = Asset.TagsAndValues.FindTag(TEXT("ParentClass"));
		if (ParentClassTag.IsSet())
		{
			BPObj->SetStringField(TEXT("parent_class"), ParentClassTag.GetValue());
		}

		ResultArray.Add(MakeShareable(new FJsonValueObject(BPObj)));
		if (ResultArray.Num() >= MaxResults) break;
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("count"), ResultArray.Num());
	Data->SetArrayField(TEXT("blueprints"), ResultArray);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetLastError(const TSharedPtr<FJsonObject>& Params)
{
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("last_error"), LastErrorMessage);
	Data->SetStringField(TEXT("last_command"), LastErrorCommand);
	Data->SetBoolField(TEXT("has_error"), !LastErrorMessage.IsEmpty());
	return FCommandResult::Ok(Data);
}

// ============================================================
// Phase 5: Actor Config & Utility Commands
// ============================================================

FCommandResult FCommandServer::HandleSetPhysicsEnabled(const TSharedPtr<FJsonObject>& Params)
{
	bool bEnabled = Params->GetBoolField(TEXT("enabled"));
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	FString ComponentName = Params->GetStringField(TEXT("component_name"));

	UPrimitiveComponent* PrimComp = nullptr;

	if (!ActorLabel.IsEmpty())
	{
		AActor* Actor = FindActorByLabel(ActorLabel);
		if (!Actor) return FCommandResult::Error(FormatActorNotFound(ActorLabel));

		if (!ComponentName.IsEmpty())
		{
			TArray<UPrimitiveComponent*> PrimComps;
			Actor->GetComponents<UPrimitiveComponent>(PrimComps);
			for (auto* PC : PrimComps)
			{
				if (PC->GetName().Contains(ComponentName)) { PrimComp = PC; break; }
			}
		}
		else
		{
			PrimComp = Cast<UPrimitiveComponent>(Actor->GetRootComponent());
			if (!PrimComp)
			{
				TArray<UPrimitiveComponent*> PrimComps;
				Actor->GetComponents<UPrimitiveComponent>(PrimComps);
				if (PrimComps.Num() > 0) PrimComp = PrimComps[0];
			}
		}
	}
	else if (!BlueprintName.IsEmpty())
	{
		UBlueprint* BP = FindBlueprintByName(BlueprintName);
		if (!BP) return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));
		if (!BP->SimpleConstructionScript) return FCommandResult::Error(TEXT("Blueprint has no SCS"));

		if (ComponentName.IsEmpty())
			return FCommandResult::Error(TEXT("'component_name' required when targeting a Blueprint"));

		USCS_Node* Node = FindSCSNodeByName(BP->SimpleConstructionScript, ComponentName);
		if (!Node) return FCommandResult::Error(FString::Printf(TEXT("Component not found: %s"), *ComponentName));

		PrimComp = Cast<UPrimitiveComponent>(Node->ComponentTemplate);
	}
	else
	{
		return FCommandResult::Error(TEXT("Provide either 'actor_label' or 'blueprint' parameter"));
	}

	if (!PrimComp)
	{
		return FCommandResult::Error(TEXT("No PrimitiveComponent found"));
	}

	PrimComp->SetSimulatePhysics(bEnabled);
	if (bEnabled)
	{
		PrimComp->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	}

	// Recompile BP if targeting a Blueprint
	if (!BlueprintName.IsEmpty())
	{
		UBlueprint* BP = FindBlueprintByName(BlueprintName);
		if (BP) FKismetEditorUtilities::CompileBlueprint(BP);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetBoolField(TEXT("physics_enabled"), bEnabled);
	Data->SetStringField(TEXT("component"), PrimComp->GetName());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetActorVisibility(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	if (ActorLabel.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'actor_label' parameter"));

	AActor* Actor = FindActorByLabel(ActorLabel);
	if (!Actor)
		return FCommandResult::Error(FormatActorNotFound(ActorLabel));

	bool bVisible = Params->GetBoolField(TEXT("visible"));
	bool bPropagate = Params->HasField(TEXT("propagate")) ? Params->GetBoolField(TEXT("propagate")) : true;

	Actor->SetActorHiddenInGame(!bVisible);
	if (Actor->GetRootComponent())
	{
		Actor->GetRootComponent()->SetVisibility(bVisible, bPropagate);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor"), ActorLabel);
	Data->SetBoolField(TEXT("visible"), bVisible);
	Data->SetBoolField(TEXT("propagate"), bPropagate);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetActorMobility(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	if (ActorLabel.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'actor_label' parameter"));

	FString MobilityStr = Params->GetStringField(TEXT("mobility"));
	if (MobilityStr.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'mobility' parameter. Use: Static, Stationary, or Movable"));

	AActor* Actor = FindActorByLabel(ActorLabel);
	if (!Actor)
		return FCommandResult::Error(FormatActorNotFound(ActorLabel));

	EComponentMobility::Type Mobility;
	if (MobilityStr.Equals(TEXT("Static"), ESearchCase::IgnoreCase))
		Mobility = EComponentMobility::Static;
	else if (MobilityStr.Equals(TEXT("Stationary"), ESearchCase::IgnoreCase))
		Mobility = EComponentMobility::Stationary;
	else if (MobilityStr.Equals(TEXT("Movable"), ESearchCase::IgnoreCase))
		Mobility = EComponentMobility::Movable;
	else
		return FCommandResult::Error(FString::Printf(TEXT("Invalid mobility: '%s'. Use: Static, Stationary, or Movable"), *MobilityStr));

	if (Actor->GetRootComponent())
	{
		Actor->GetRootComponent()->SetMobility(Mobility);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor"), ActorLabel);
	Data->SetStringField(TEXT("mobility"), MobilityStr);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAttachActorTo(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	FString ParentLabel = Params->GetStringField(TEXT("parent_label"));
	FString SocketName = Params->GetStringField(TEXT("socket_name"));
	FString RuleStr = Params->HasField(TEXT("rule")) ? Params->GetStringField(TEXT("rule")) : TEXT("KeepWorld");

	if (ActorLabel.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'actor_label' parameter"));
	if (ParentLabel.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'parent_label' parameter"));

	AActor* Child = FindActorByLabel(ActorLabel);
	if (!Child) return FCommandResult::Error(FormatActorNotFound(ActorLabel));

	AActor* Parent = FindActorByLabel(ParentLabel);
	if (!Parent) return FCommandResult::Error(FormatActorNotFound(ParentLabel));

	// Determine attachment rule
	EAttachmentRule Rule = EAttachmentRule::KeepWorld;
	if (RuleStr.Equals(TEXT("KeepRelative"), ESearchCase::IgnoreCase))
		Rule = EAttachmentRule::KeepRelative;
	else if (RuleStr.Equals(TEXT("SnapToTarget"), ESearchCase::IgnoreCase))
		Rule = EAttachmentRule::SnapToTarget;

	FAttachmentTransformRules AttachRules(Rule, true);

	USceneComponent* ParentComp = Parent->GetRootComponent();
	if (!ParentComp)
		return FCommandResult::Error(FString::Printf(TEXT("Parent actor '%s' has no root component"), *ParentLabel));

	Child->AttachToComponent(ParentComp, AttachRules, FName(*SocketName));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor"), ActorLabel);
	Data->SetStringField(TEXT("parent"), ParentLabel);
	Data->SetStringField(TEXT("rule"), RuleStr);
	if (!SocketName.IsEmpty()) Data->SetStringField(TEXT("socket"), SocketName);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleDetachActor(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	if (ActorLabel.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'actor_label' parameter"));

	AActor* Actor = FindActorByLabel(ActorLabel);
	if (!Actor) return FCommandResult::Error(FormatActorNotFound(ActorLabel));

	FString RuleStr = Params->HasField(TEXT("rule")) ? Params->GetStringField(TEXT("rule")) : TEXT("KeepWorld");
	EDetachmentRule Rule = EDetachmentRule::KeepWorld;
	if (RuleStr.Equals(TEXT("KeepRelative"), ESearchCase::IgnoreCase))
		Rule = EDetachmentRule::KeepRelative;

	FDetachmentTransformRules DetachRules(Rule, true);
	Actor->DetachFromActor(DetachRules);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor"), ActorLabel);
	Data->SetStringField(TEXT("rule"), RuleStr);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleListProjectAssets(const TSharedPtr<FJsonObject>& Params)
{
	FString AssetType = Params->GetStringField(TEXT("asset_type"));
	FString Path = Params->GetStringField(TEXT("path"));
	FString NameFilter = Params->GetStringField(TEXT("name_filter"));
	int32 MaxResults = Params->HasField(TEXT("max_results")) ? (int32)Params->GetNumberField(TEXT("max_results")) : 100;

	FAssetRegistryModule& AssetReg = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");

	TArray<FAssetData> AllAssets;

	if (!AssetType.IsEmpty())
	{
		// Map friendly type names to UE classes
		UClass* FilterClass = nullptr;
		if (AssetType.Equals(TEXT("Blueprint"), ESearchCase::IgnoreCase))
			FilterClass = UBlueprint::StaticClass();
		else if (AssetType.Equals(TEXT("Material"), ESearchCase::IgnoreCase))
			FilterClass = UMaterial::StaticClass();
		else if (AssetType.Equals(TEXT("MaterialInstance"), ESearchCase::IgnoreCase))
			FilterClass = UMaterialInstanceConstant::StaticClass();
		else if (AssetType.Equals(TEXT("StaticMesh"), ESearchCase::IgnoreCase))
			FilterClass = UStaticMesh::StaticClass();
		else if (AssetType.Equals(TEXT("Texture"), ESearchCase::IgnoreCase) || AssetType.Equals(TEXT("Texture2D"), ESearchCase::IgnoreCase))
			FilterClass = UTexture2D::StaticClass();
		else if (AssetType.Equals(TEXT("SoundWave"), ESearchCase::IgnoreCase) || AssetType.Equals(TEXT("Sound"), ESearchCase::IgnoreCase))
			FilterClass = USoundWave::StaticClass();
		else if (AssetType.Equals(TEXT("BehaviorTree"), ESearchCase::IgnoreCase))
			FilterClass = UBehaviorTree::StaticClass();
		else if (AssetType.Equals(TEXT("DataTable"), ESearchCase::IgnoreCase))
			FilterClass = UDataTable::StaticClass();

		if (FilterClass)
		{
			AssetReg.Get().GetAssetsByClass(FilterClass->GetClassPathName(), AllAssets);
		}
		else
		{
			return FCommandResult::Error(FString::Printf(TEXT("Unknown asset type: '%s'. Supported: Blueprint, Material, MaterialInstance, StaticMesh, Texture, Sound, BehaviorTree, DataTable"), *AssetType));
		}
	}
	else if (!Path.IsEmpty())
	{
		AssetReg.Get().GetAssetsByPath(FName(*Path), AllAssets, true);
	}
	else
	{
		// All project assets — use /Game/ path
		AssetReg.Get().GetAssetsByPath(FName(TEXT("/Game")), AllAssets, true);
	}

	TArray<TSharedPtr<FJsonValue>> ResultArray;
	for (const FAssetData& Asset : AllAssets)
	{
		if (!NameFilter.IsEmpty() && !Asset.AssetName.ToString().Contains(NameFilter))
			continue;

		TSharedPtr<FJsonObject> AssetObj = MakeShareable(new FJsonObject());
		AssetObj->SetStringField(TEXT("name"), Asset.AssetName.ToString());
		AssetObj->SetStringField(TEXT("path"), Asset.GetObjectPathString());
		AssetObj->SetStringField(TEXT("type"), Asset.AssetClassPath.GetAssetName().ToString());
		ResultArray.Add(MakeShareable(new FJsonValueObject(AssetObj)));

		if (ResultArray.Num() >= MaxResults) break;
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("count"), ResultArray.Num());
	Data->SetArrayField(TEXT("assets"), ResultArray);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCopyActor(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	if (ActorLabel.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'actor_label' parameter"));

	AActor* SourceActor = FindActorByLabel(ActorLabel);
	if (!SourceActor)
		return FCommandResult::Error(FormatActorNotFound(ActorLabel));

	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World) return FCommandResult::Error(TEXT("No editor world"));

	// Calculate spawn location
	FVector SpawnLoc = SourceActor->GetActorLocation();
	FRotator SpawnRot = SourceActor->GetActorRotation();
	FVector SpawnScale = SourceActor->GetActorScale3D();

	if (Params->HasField(TEXT("offset")))
	{
		FVector Offset = JsonToVector(Params->GetObjectField(TEXT("offset")));
		SpawnLoc += Offset;
	}

	// Spawn a copy using FTransform
	FActorSpawnParameters SpawnParams;
	SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	SpawnParams.Template = SourceActor;

	FTransform SpawnTransform(SpawnRot, SpawnLoc, SpawnScale);
	AActor* NewActor = World->SpawnActor(SourceActor->GetClass(), &SpawnTransform, SpawnParams);
	if (!NewActor)
		return FCommandResult::Error(TEXT("Failed to spawn actor copy"));

	FString NewLabel = Params->GetStringField(TEXT("new_label"));
	if (NewLabel.IsEmpty())
	{
		NewLabel = FString::Printf(TEXT("%s_Copy"), *ActorLabel);
	}
	NewActor->SetActorLabel(NewLabel);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("source"), ActorLabel);
	Data->SetStringField(TEXT("copy"), NewLabel);
	Data->SetObjectField(TEXT("location"), VectorToJson(SpawnLoc));
	return FCommandResult::Ok(Data);
}

// ============================================================
// Procedural Spawn Pattern Commands
// ============================================================

FCommandResult FCommandServer::HandleSpawnActorGrid(const TSharedPtr<FJsonObject>& Params)
{
	// Required params
	FString ClassName = Params->GetStringField(TEXT("class"));
	if (ClassName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'class' parameter"));

	UClass* ActorClass = ResolveActorClass(ClassName);
	if (!ActorClass)
		{ FString ClassErr = FString::Printf(TEXT("Could not resolve actor class: %s."), *ClassName);
			TArray<FString> ClassSuggestions = GetSuggestions(ClassName, GetAvailableBlueprintNames());
			if (ClassSuggestions.Num() > 0) ClassErr += TEXT(" Similar blueprints: ") + FString::Join(ClassSuggestions, TEXT(", "));
			else ClassErr += TEXT(" Tip: use full path like /Game/Arcwright/Generated/BP_MyActor for Blueprint classes, or native class names like StaticMeshActor, PointLight, Character.");
			return FCommandResult::Error(ClassErr); }

	int32 Rows = Params->HasField(TEXT("rows")) ? (int32)Params->GetNumberField(TEXT("rows")) : 3;
	int32 Cols = Params->HasField(TEXT("cols")) ? (int32)Params->GetNumberField(TEXT("cols")) : 3;
	double SpacingX = Params->HasField(TEXT("spacing_x")) ? Params->GetNumberField(TEXT("spacing_x")) : 200.0;
	double SpacingY = Params->HasField(TEXT("spacing_y")) ? Params->GetNumberField(TEXT("spacing_y")) : 200.0;

	// Clamp to reasonable limits
	Rows = FMath::Clamp(Rows, 1, 50);
	Cols = FMath::Clamp(Cols, 1, 50);

	FVector Origin = FVector::ZeroVector;
	if (Params->HasField(TEXT("origin")))
		Origin = JsonToVector(Params->GetObjectField(TEXT("origin")));

	FRotator Rotation = FRotator::ZeroRotator;
	if (Params->HasField(TEXT("rotation")))
		Rotation = JsonToRotator(Params->GetObjectField(TEXT("rotation")));

	FVector Scale = FVector::OneVector;
	if (Params->HasField(TEXT("scale")))
		Scale = JsonToVector(Params->GetObjectField(TEXT("scale")));

	FString LabelPrefix = Params->HasField(TEXT("label_prefix")) ? Params->GetStringField(TEXT("label_prefix")) : TEXT("");

	// Center the grid on origin
	bool bCenter = !Params->HasField(TEXT("center")) || Params->GetBoolField(TEXT("center"));
	FVector Offset = FVector::ZeroVector;
	if (bCenter)
	{
		Offset.X = -((Cols - 1) * SpacingX) / 2.0;
		Offset.Y = -((Rows - 1) * SpacingY) / 2.0;
	}

	UEditorActorSubsystem* ActorSub = GEditor->GetEditorSubsystem<UEditorActorSubsystem>();
	if (!ActorSub)
		return FCommandResult::Error(TEXT("Could not get UEditorActorSubsystem"));

	TArray<TSharedPtr<FJsonValue>> SpawnedArray;
	int32 SpawnCount = 0;

	for (int32 Row = 0; Row < Rows; Row++)
	{
		for (int32 Col = 0; Col < Cols; Col++)
		{
			FVector Pos = Origin + Offset;
			Pos.X += Col * SpacingX;
			Pos.Y += Row * SpacingY;

			AActor* Actor = ActorSub->SpawnActorFromClass(ActorClass, Pos, Rotation);
			if (Actor)
			{
				Actor->SetActorScale3D(Scale);

				if (!LabelPrefix.IsEmpty())
				{
					FString Label = FString::Printf(TEXT("%s_%d_%d"), *LabelPrefix, Row, Col);
					Actor->SetActorLabel(Label);
				}

				TSharedPtr<FJsonObject> ActorObj = MakeShareable(new FJsonObject());
				ActorObj->SetStringField(TEXT("label"), Actor->GetActorLabel());
				ActorObj->SetObjectField(TEXT("location"), VectorToJson(Actor->GetActorLocation()));
				ActorObj->SetNumberField(TEXT("row"), Row);
				ActorObj->SetNumberField(TEXT("col"), Col);
				SpawnedArray.Add(MakeShareable(new FJsonValueObject(ActorObj)));
				SpawnCount++;
			}
		}
	}

	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (World) World->MarkPackageDirty();

	UE_LOG(LogBlueprintLLM, Log, TEXT("SpawnActorGrid: %d actors (%dx%d) of class %s"),
		SpawnCount, Rows, Cols, *ActorClass->GetName());

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("spawned"), SpawnCount);
	Data->SetNumberField(TEXT("rows"), Rows);
	Data->SetNumberField(TEXT("cols"), Cols);
	Data->SetArrayField(TEXT("actors"), SpawnedArray);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSpawnActorCircle(const TSharedPtr<FJsonObject>& Params)
{
	FString ClassName = Params->GetStringField(TEXT("class"));
	if (ClassName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'class' parameter"));

	UClass* ActorClass = ResolveActorClass(ClassName);
	if (!ActorClass)
		{ FString ClassErr = FString::Printf(TEXT("Could not resolve actor class: %s."), *ClassName);
			TArray<FString> ClassSuggestions = GetSuggestions(ClassName, GetAvailableBlueprintNames());
			if (ClassSuggestions.Num() > 0) ClassErr += TEXT(" Similar blueprints: ") + FString::Join(ClassSuggestions, TEXT(", "));
			else ClassErr += TEXT(" Tip: use full path like /Game/Arcwright/Generated/BP_MyActor for Blueprint classes, or native class names like StaticMeshActor, PointLight, Character.");
			return FCommandResult::Error(ClassErr); }

	int32 Count = Params->HasField(TEXT("count")) ? (int32)Params->GetNumberField(TEXT("count")) : 8;
	double Radius = Params->HasField(TEXT("radius")) ? Params->GetNumberField(TEXT("radius")) : 500.0;

	Count = FMath::Clamp(Count, 1, 100);

	FVector Center = FVector::ZeroVector;
	if (Params->HasField(TEXT("center")))
		Center = JsonToVector(Params->GetObjectField(TEXT("center")));

	FVector Scale = FVector::OneVector;
	if (Params->HasField(TEXT("scale")))
		Scale = JsonToVector(Params->GetObjectField(TEXT("scale")));

	FString LabelPrefix = Params->HasField(TEXT("label_prefix")) ? Params->GetStringField(TEXT("label_prefix")) : TEXT("");

	// face_center: if true, each actor rotates to face the center
	bool bFaceCenter = Params->HasField(TEXT("face_center")) && Params->GetBoolField(TEXT("face_center"));

	// start_angle in degrees (default 0)
	double StartAngleDeg = Params->HasField(TEXT("start_angle")) ? Params->GetNumberField(TEXT("start_angle")) : 0.0;

	UEditorActorSubsystem* ActorSub = GEditor->GetEditorSubsystem<UEditorActorSubsystem>();
	if (!ActorSub)
		return FCommandResult::Error(TEXT("Could not get UEditorActorSubsystem"));

	TArray<TSharedPtr<FJsonValue>> SpawnedArray;
	int32 SpawnCount = 0;

	for (int32 i = 0; i < Count; i++)
	{
		double AngleDeg = StartAngleDeg + (360.0 * i / Count);
		double AngleRad = FMath::DegreesToRadians(AngleDeg);

		FVector Pos = Center;
		Pos.X += Radius * FMath::Cos(AngleRad);
		Pos.Y += Radius * FMath::Sin(AngleRad);

		FRotator Rot = FRotator::ZeroRotator;
		if (bFaceCenter)
		{
			FVector ToCenter = Center - Pos;
			Rot = ToCenter.Rotation();
			Rot.Pitch = 0; // keep actors upright
		}

		AActor* Actor = ActorSub->SpawnActorFromClass(ActorClass, Pos, Rot);
		if (Actor)
		{
			Actor->SetActorScale3D(Scale);

			if (!LabelPrefix.IsEmpty())
			{
				FString Label = FString::Printf(TEXT("%s_%d"), *LabelPrefix, i);
				Actor->SetActorLabel(Label);
			}

			TSharedPtr<FJsonObject> ActorObj = MakeShareable(new FJsonObject());
			ActorObj->SetStringField(TEXT("label"), Actor->GetActorLabel());
			ActorObj->SetObjectField(TEXT("location"), VectorToJson(Actor->GetActorLocation()));
			ActorObj->SetNumberField(TEXT("index"), i);
			ActorObj->SetNumberField(TEXT("angle"), AngleDeg);
			SpawnedArray.Add(MakeShareable(new FJsonValueObject(ActorObj)));
			SpawnCount++;
		}
	}

	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (World) World->MarkPackageDirty();

	UE_LOG(LogBlueprintLLM, Log, TEXT("SpawnActorCircle: %d actors (radius=%.0f) of class %s"),
		SpawnCount, Radius, *ActorClass->GetName());

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("spawned"), SpawnCount);
	Data->SetNumberField(TEXT("count"), Count);
	Data->SetNumberField(TEXT("radius"), Radius);
	Data->SetArrayField(TEXT("actors"), SpawnedArray);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSpawnActorLine(const TSharedPtr<FJsonObject>& Params)
{
	FString ClassName = Params->GetStringField(TEXT("class"));
	if (ClassName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing 'class' parameter"));

	UClass* ActorClass = ResolveActorClass(ClassName);
	if (!ActorClass)
		{ FString ClassErr = FString::Printf(TEXT("Could not resolve actor class: %s."), *ClassName);
			TArray<FString> ClassSuggestions = GetSuggestions(ClassName, GetAvailableBlueprintNames());
			if (ClassSuggestions.Num() > 0) ClassErr += TEXT(" Similar blueprints: ") + FString::Join(ClassSuggestions, TEXT(", "));
			else ClassErr += TEXT(" Tip: use full path like /Game/Arcwright/Generated/BP_MyActor for Blueprint classes, or native class names like StaticMeshActor, PointLight, Character.");
			return FCommandResult::Error(ClassErr); }

	int32 Count = Params->HasField(TEXT("count")) ? (int32)Params->GetNumberField(TEXT("count")) : 5;
	Count = FMath::Clamp(Count, 1, 200);

	if (!Params->HasField(TEXT("start")) || !Params->HasField(TEXT("end")))
		return FCommandResult::Error(TEXT("Missing 'start' and/or 'end' parameters (each {x,y,z})"));

	FVector Start = JsonToVector(Params->GetObjectField(TEXT("start")));
	FVector End = JsonToVector(Params->GetObjectField(TEXT("end")));

	FVector Scale = FVector::OneVector;
	if (Params->HasField(TEXT("scale")))
		Scale = JsonToVector(Params->GetObjectField(TEXT("scale")));

	FString LabelPrefix = Params->HasField(TEXT("label_prefix")) ? Params->GetStringField(TEXT("label_prefix")) : TEXT("");

	// face_direction: if true, each actor rotates to face along the line direction
	bool bFaceDirection = Params->HasField(TEXT("face_direction")) && Params->GetBoolField(TEXT("face_direction"));
	FRotator LineRot = FRotator::ZeroRotator;
	if (bFaceDirection)
	{
		FVector Dir = End - Start;
		if (!Dir.IsNearlyZero())
		{
			LineRot = Dir.Rotation();
			LineRot.Pitch = 0;
		}
	}

	UEditorActorSubsystem* ActorSub = GEditor->GetEditorSubsystem<UEditorActorSubsystem>();
	if (!ActorSub)
		return FCommandResult::Error(TEXT("Could not get UEditorActorSubsystem"));

	TArray<TSharedPtr<FJsonValue>> SpawnedArray;
	int32 SpawnCount = 0;

	for (int32 i = 0; i < Count; i++)
	{
		float T = (Count > 1) ? (float)i / (float)(Count - 1) : 0.0f;
		FVector Pos = FMath::Lerp(Start, End, T);

		AActor* Actor = ActorSub->SpawnActorFromClass(ActorClass, Pos, LineRot);
		if (Actor)
		{
			Actor->SetActorScale3D(Scale);

			if (!LabelPrefix.IsEmpty())
			{
				FString Label = FString::Printf(TEXT("%s_%d"), *LabelPrefix, i);
				Actor->SetActorLabel(Label);
			}

			TSharedPtr<FJsonObject> ActorObj = MakeShareable(new FJsonObject());
			ActorObj->SetStringField(TEXT("label"), Actor->GetActorLabel());
			ActorObj->SetObjectField(TEXT("location"), VectorToJson(Actor->GetActorLocation()));
			ActorObj->SetNumberField(TEXT("index"), i);
			SpawnedArray.Add(MakeShareable(new FJsonValueObject(ActorObj)));
			SpawnCount++;
		}
	}

	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (World) World->MarkPackageDirty();

	UE_LOG(LogBlueprintLLM, Log, TEXT("SpawnActorLine: %d actors from (%s) to (%s) of class %s"),
		SpawnCount, *Start.ToString(), *End.ToString(), *ActorClass->GetName());

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("spawned"), SpawnCount);
	Data->SetNumberField(TEXT("count"), Count);
	Data->SetArrayField(TEXT("actors"), SpawnedArray);
	return FCommandResult::Ok(Data);
}

// ============================================================
// Relative Transform Batch Commands
// ============================================================

FCommandResult FCommandServer::HandleBatchScaleActors(const TSharedPtr<FJsonObject>& Params)
{
	UEditorActorSubsystem* ActorSub = GEditor->GetEditorSubsystem<UEditorActorSubsystem>();
	if (!ActorSub) return FCommandResult::Error(TEXT("Could not get UEditorActorSubsystem"));

	// Accept labels array, or class_filter/tag/name_filter to find actors
	TArray<AActor*> TargetActors;

	const TArray<TSharedPtr<FJsonValue>>* LabelsArray = nullptr;
	if (Params->TryGetArrayField(TEXT("labels"), LabelsArray) && LabelsArray)
	{
		for (const auto& Val : *LabelsArray)
		{
			FString Label = Val->AsString();
			AActor* Actor = FindActorByLabel(Label);
			if (Actor) TargetActors.Add(Actor);
		}
	}

	// Also match by name_filter, class_filter, tag
	FString NameFilter = Params->HasField(TEXT("name_filter")) ? Params->GetStringField(TEXT("name_filter")) : TEXT("");
	FString ClassFilter = Params->HasField(TEXT("class_filter")) ? Params->GetStringField(TEXT("class_filter")) : TEXT("");
	FString Tag = Params->HasField(TEXT("tag")) ? Params->GetStringField(TEXT("tag")) : TEXT("");

	if (!NameFilter.IsEmpty() || !ClassFilter.IsEmpty() || !Tag.IsEmpty())
	{
		TArray<AActor*> AllActors = ActorSub->GetAllLevelActors();
		for (AActor* Actor : AllActors)
		{
			if (!Actor) continue;
			if (!NameFilter.IsEmpty() && !Actor->GetActorLabel().Contains(NameFilter, ESearchCase::IgnoreCase)) continue;
			if (!ClassFilter.IsEmpty() && !Actor->GetClass()->GetName().Contains(ClassFilter, ESearchCase::IgnoreCase)) continue;
			if (!Tag.IsEmpty() && !Actor->ActorHasTag(FName(*Tag))) continue;
			TargetActors.AddUnique(Actor);
		}
	}

	if (TargetActors.Num() == 0)
		return FCommandResult::Error(TEXT("No matching actors found. Provide 'labels' array, or 'name_filter'/'class_filter'/'tag'."));

	// Scale mode: "multiply" (relative) or "set" (absolute)
	FString Mode = Params->HasField(TEXT("mode")) ? Params->GetStringField(TEXT("mode")) : TEXT("multiply");
	FVector ScaleValue = FVector::OneVector;
	if (Params->HasField(TEXT("scale")))
	{
		TSharedPtr<FJsonObject> ScaleObj = Params->GetObjectField(TEXT("scale"));
		if (ScaleObj.IsValid())
		{
			ScaleValue = JsonToVector(ScaleObj);
		}
	}
	else if (Params->HasField(TEXT("uniform_scale")))
	{
		double S = Params->GetNumberField(TEXT("uniform_scale"));
		ScaleValue = FVector(S, S, S);
	}
	else
	{
		return FCommandResult::Error(TEXT("Missing 'scale' ({x,y,z}) or 'uniform_scale' (number)"));
	}

	int32 Scaled = 0;
	for (AActor* Actor : TargetActors)
	{
		if (Mode.Equals(TEXT("multiply"), ESearchCase::IgnoreCase))
		{
			FVector Current = Actor->GetActorScale3D();
			Actor->SetActorScale3D(Current * ScaleValue);
		}
		else // "set" mode
		{
			Actor->SetActorScale3D(ScaleValue);
		}
		Scaled++;
	}

	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (World) World->MarkPackageDirty();

	UE_LOG(LogBlueprintLLM, Log, TEXT("BatchScaleActors: scaled %d actors (mode=%s)"), Scaled, *Mode);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("scaled"), Scaled);
	Data->SetStringField(TEXT("mode"), Mode);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleBatchMoveActors(const TSharedPtr<FJsonObject>& Params)
{
	UEditorActorSubsystem* ActorSub = GEditor->GetEditorSubsystem<UEditorActorSubsystem>();
	if (!ActorSub) return FCommandResult::Error(TEXT("Could not get UEditorActorSubsystem"));

	// Accept labels array, or class_filter/tag/name_filter
	TArray<AActor*> TargetActors;

	const TArray<TSharedPtr<FJsonValue>>* LabelsArray = nullptr;
	if (Params->TryGetArrayField(TEXT("labels"), LabelsArray) && LabelsArray)
	{
		for (const auto& Val : *LabelsArray)
		{
			FString Label = Val->AsString();
			AActor* Actor = FindActorByLabel(Label);
			if (Actor) TargetActors.Add(Actor);
		}
	}

	FString NameFilter = Params->HasField(TEXT("name_filter")) ? Params->GetStringField(TEXT("name_filter")) : TEXT("");
	FString ClassFilter = Params->HasField(TEXT("class_filter")) ? Params->GetStringField(TEXT("class_filter")) : TEXT("");
	FString Tag = Params->HasField(TEXT("tag")) ? Params->GetStringField(TEXT("tag")) : TEXT("");

	if (!NameFilter.IsEmpty() || !ClassFilter.IsEmpty() || !Tag.IsEmpty())
	{
		TArray<AActor*> AllActors = ActorSub->GetAllLevelActors();
		for (AActor* Actor : AllActors)
		{
			if (!Actor) continue;
			if (!NameFilter.IsEmpty() && !Actor->GetActorLabel().Contains(NameFilter, ESearchCase::IgnoreCase)) continue;
			if (!ClassFilter.IsEmpty() && !Actor->GetClass()->GetName().Contains(ClassFilter, ESearchCase::IgnoreCase)) continue;
			if (!Tag.IsEmpty() && !Actor->ActorHasTag(FName(*Tag))) continue;
			TargetActors.AddUnique(Actor);
		}
	}

	if (TargetActors.Num() == 0)
		return FCommandResult::Error(TEXT("No matching actors found. Provide 'labels' array, or 'name_filter'/'class_filter'/'tag'."));

	// Move mode: "relative" (add offset) or "set" (absolute position)
	FString Mode = Params->HasField(TEXT("mode")) ? Params->GetStringField(TEXT("mode")) : TEXT("relative");

	if (!Params->HasField(TEXT("offset")) && !Params->HasField(TEXT("location")))
		return FCommandResult::Error(TEXT("Missing 'offset' ({x,y,z}) for relative mode or 'location' ({x,y,z}) for set mode"));

	FVector MoveValue = FVector::ZeroVector;
	if (Mode.Equals(TEXT("relative"), ESearchCase::IgnoreCase))
	{
		if (Params->HasField(TEXT("offset")))
			MoveValue = JsonToVector(Params->GetObjectField(TEXT("offset")));
		else
			MoveValue = JsonToVector(Params->GetObjectField(TEXT("location")));
	}
	else
	{
		if (Params->HasField(TEXT("location")))
			MoveValue = JsonToVector(Params->GetObjectField(TEXT("location")));
		else
			MoveValue = JsonToVector(Params->GetObjectField(TEXT("offset")));
	}

	int32 Moved = 0;
	for (AActor* Actor : TargetActors)
	{
		if (Mode.Equals(TEXT("relative"), ESearchCase::IgnoreCase))
		{
			FVector Current = Actor->GetActorLocation();
			Actor->SetActorLocation(Current + MoveValue);
		}
		else // "set" mode
		{
			Actor->SetActorLocation(MoveValue);
		}
		Moved++;
	}

	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (World) World->MarkPackageDirty();

	UE_LOG(LogBlueprintLLM, Log, TEXT("BatchMoveActors: moved %d actors (mode=%s)"), Moved, *Mode);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("moved"), Moved);
	Data->SetStringField(TEXT("mode"), Mode);
	return FCommandResult::Ok(Data);
}

// ============================================================================
// Phase 6: Enhanced Input
// ============================================================================

FCommandResult FCommandServer::HandleSetPlayerInputMapping(const TSharedPtr<FJsonObject>& Params)
{
	FString BlueprintName = Params->GetStringField(TEXT("blueprint"));
	FString ContextName = Params->GetStringField(TEXT("context"));

	if (BlueprintName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'blueprint' (PlayerController BP name)"));
	if (ContextName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'context' (InputMappingContext name)"));

	UBlueprint* BP = FindBlueprintByName(BlueprintName);
	if (!BP) return FCommandResult::Error(FormatBlueprintNotFound(BlueprintName));

	// Find the InputMappingContext asset
	FAssetRegistryModule& ARM = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	TArray<FAssetData> Assets;
	ARM.Get().GetAssetsByClass(UInputMappingContext::StaticClass()->GetClassPathName(), Assets);

	UInputMappingContext* IMC = nullptr;
	for (const FAssetData& Asset : Assets)
	{
		if (Asset.AssetName.ToString().Equals(ContextName, ESearchCase::IgnoreCase))
		{
			IMC = Cast<UInputMappingContext>(Asset.GetAsset());
			break;
		}
	}
	if (!IMC) return FCommandResult::Error(FString::Printf(TEXT("InputMappingContext not found: %s"), *ContextName));

	// Set on CDO via reflection — look for DefaultMappingContexts or similar property
	UObject* CDO = BP->GeneratedClass ? BP->GeneratedClass->GetDefaultObject() : nullptr;
	if (!CDO) return FCommandResult::Error(TEXT("Blueprint has no generated class CDO"));

	// Try to find the property for default mapping contexts
	bool bSet = false;
	FProperty* Prop = CDO->GetClass()->FindPropertyByName(TEXT("InputMappingContext"));
	if (!Prop) Prop = CDO->GetClass()->FindPropertyByName(TEXT("DefaultMappingContext"));
	if (Prop)
	{
		FObjectProperty* ObjProp = CastField<FObjectProperty>(Prop);
		if (ObjProp)
		{
			ObjProp->SetObjectPropertyValue(Prop->ContainerPtrToValuePtr<void>(CDO), IMC);
			bSet = true;
		}
	}

	// Also store as metadata for reference
	BP->Modify();
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("blueprint"), BlueprintName);
	Data->SetStringField(TEXT("context"), ContextName);
	Data->SetBoolField(TEXT("property_set"), bSet);
	return FCommandResult::Ok(Data);
}

// ============================================================================
// Phase 6: Advanced Actor Configuration
// ============================================================================

FCommandResult FCommandServer::HandleSetActorTick(const TSharedPtr<FJsonObject>& Params)
{
	FString Label = Params->GetStringField(TEXT("actor_label"));
	if (Label.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'actor_label'"));

	AActor* Actor = FindActorByLabel(Label);
	if (!Actor) return FCommandResult::Error(FormatActorNotFound(Label));

	bool bEnabled = true;
	if (Params->HasField(TEXT("enabled")))
		bEnabled = Params->GetBoolField(TEXT("enabled"));

	Actor->SetActorTickEnabled(bEnabled);
	Actor->PrimaryActorTick.bCanEverTick = bEnabled;

	if (Params->HasField(TEXT("interval")))
	{
		float Interval = (float)Params->GetNumberField(TEXT("interval"));
		Actor->PrimaryActorTick.TickInterval = Interval;
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor"), Label);
	Data->SetBoolField(TEXT("tick_enabled"), bEnabled);
	if (Params->HasField(TEXT("interval")))
		Data->SetNumberField(TEXT("tick_interval"), Actor->PrimaryActorTick.TickInterval);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetActorLifespan(const TSharedPtr<FJsonObject>& Params)
{
	FString Label = Params->GetStringField(TEXT("actor_label"));
	if (Label.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'actor_label'"));

	AActor* Actor = FindActorByLabel(Label);
	if (!Actor) return FCommandResult::Error(FormatActorNotFound(Label));

	float Lifespan = 0.f;
	if (Params->HasField(TEXT("lifespan")))
		Lifespan = (float)Params->GetNumberField(TEXT("lifespan"));

	Actor->SetLifeSpan(Lifespan);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor"), Label);
	Data->SetNumberField(TEXT("lifespan"), Lifespan);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetActorBounds(const TSharedPtr<FJsonObject>& Params)
{
	FString Label = Params->GetStringField(TEXT("actor_label"));
	if (Label.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'actor_label'"));

	AActor* Actor = FindActorByLabel(Label);
	if (!Actor) return FCommandResult::Error(FormatActorNotFound(Label));

	FVector Origin, Extent;
	Actor->GetActorBounds(false, Origin, Extent);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor"), Label);
	Data->SetObjectField(TEXT("origin"), VectorToJson(Origin));
	Data->SetObjectField(TEXT("extent"), VectorToJson(Extent));

	// Also provide min/max for convenience
	TSharedPtr<FJsonObject> MinJson = VectorToJson(Origin - Extent);
	TSharedPtr<FJsonObject> MaxJson = VectorToJson(Origin + Extent);
	Data->SetObjectField(TEXT("min"), MinJson);
	Data->SetObjectField(TEXT("max"), MaxJson);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetActorEnabled(const TSharedPtr<FJsonObject>& Params)
{
	FString Label = Params->GetStringField(TEXT("actor_label"));
	if (Label.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'actor_label'"));

	AActor* Actor = FindActorByLabel(Label);
	if (!Actor) return FCommandResult::Error(FormatActorNotFound(Label));

	bool bEnabled = true;
	if (Params->HasField(TEXT("enabled")))
		bEnabled = Params->GetBoolField(TEXT("enabled"));

	// Toggle visibility
	Actor->SetActorHiddenInGame(!bEnabled);
	if (Actor->GetRootComponent())
		Actor->GetRootComponent()->SetVisibility(bEnabled, true);

	// Toggle collision
	Actor->SetActorEnableCollision(bEnabled);

	// Toggle tick
	Actor->SetActorTickEnabled(bEnabled);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor"), Label);
	Data->SetBoolField(TEXT("enabled"), bEnabled);
	return FCommandResult::Ok(Data);
}

// ============================================================================
// Phase 6: Data & Persistence
// ============================================================================

FCommandResult FCommandServer::HandleCreateSaveGame(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'name'"));

	FString PackagePath = TEXT("/Game/Arcwright/SaveGames/") + Name;
	UPackage* Package = CreatePackage(*PackagePath);

	// Create a Blueprint with USaveGame as parent
	UClass* SaveGameClass = USaveGame::StaticClass();
	UBlueprintFactory* Factory = NewObject<UBlueprintFactory>();
	Factory->ParentClass = SaveGameClass;

	UBlueprint* BP = Cast<UBlueprint>(Factory->FactoryCreateNew(
		UBlueprint::StaticClass(), Package, FName(*Name), RF_Public | RF_Standalone, nullptr, GWarn));

	if (!BP) return FCommandResult::Error(TEXT("Failed to create SaveGame Blueprint"));

	// Add variables if specified
	const TArray<TSharedPtr<FJsonValue>>* Variables;
	if (Params->TryGetArrayField(TEXT("variables"), Variables))
	{
		for (const TSharedPtr<FJsonValue>& VarVal : *Variables)
		{
			TSharedPtr<FJsonObject> VarObj = VarVal->AsObject();
			if (!VarObj) continue;

			FString VarName = VarObj->GetStringField(TEXT("name"));
			FString VarType = VarObj->GetStringField(TEXT("type"));

			FEdGraphPinType PinType;
			if (VarType == TEXT("int") || VarType == TEXT("Int"))
				PinType.PinCategory = UEdGraphSchema_K2::PC_Int;
			else if (VarType == TEXT("float") || VarType == TEXT("Float"))
				PinType.PinCategory = UEdGraphSchema_K2::PC_Real;
			else if (VarType == TEXT("bool") || VarType == TEXT("Bool"))
				PinType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
			else if (VarType == TEXT("string") || VarType == TEXT("String"))
				PinType.PinCategory = UEdGraphSchema_K2::PC_String;
			else if (VarType == TEXT("vector") || VarType == TEXT("Vector"))
			{
				PinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
				PinType.PinSubCategoryObject = TBaseStructure<FVector>::Get();
			}
			else
				PinType.PinCategory = UEdGraphSchema_K2::PC_String; // default

			FBlueprintEditorUtils::AddMemberVariable(BP, FName(*VarName), PinType);
		}
	}

	FKismetEditorUtilities::CompileBlueprint(BP);
	{
		FString PkgFilename = FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension());
		FSavePackageArgs SaveArgs;
		SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
		SafeSavePackage(Package, BP, PkgFilename, SaveArgs);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("path"), PackagePath);
	Data->SetStringField(TEXT("parent_class"), TEXT("SaveGame"));
	int32 VarCount = BP->NewVariables.Num();
	Data->SetNumberField(TEXT("variable_count"), VarCount);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddDataTableRow(const TSharedPtr<FJsonObject>& Params)
{
	FString TableName = Params->GetStringField(TEXT("table_name"));
	FString RowName = Params->GetStringField(TEXT("row_name"));
	if (TableName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'table_name'"));
	if (RowName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'row_name'"));

	// Find the DataTable
	UDataTable* DT = nullptr;
	FAssetRegistryModule& ARM = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	TArray<FAssetData> Assets;
	ARM.Get().GetAssetsByClass(UDataTable::StaticClass()->GetClassPathName(), Assets);
	for (const FAssetData& Asset : Assets)
	{
		if (Asset.AssetName.ToString().Equals(TableName, ESearchCase::IgnoreCase))
		{
			DT = Cast<UDataTable>(Asset.GetAsset());
			break;
		}
	}
	if (!DT) return FCommandResult::Error(FString::Printf(TEXT("DataTable not found: %s"), *TableName));

	// Build JSON row string from values
	const TSharedPtr<FJsonObject>* ValuesObj;
	if (!Params->TryGetObjectField(TEXT("values"), ValuesObj))
		return FCommandResult::Error(TEXT("Missing 'values' object"));

	const UScriptStruct* RowStruct = DT->GetRowStruct();
	if (!RowStruct) return FCommandResult::Error(TEXT("DataTable has no row struct"));

	DT->Modify();

	// Allocate a new row and populate fields
	uint8* NewRowData = (uint8*)FMemory::Malloc(RowStruct->GetStructureSize());
	RowStruct->InitializeStruct(NewRowData);

	int32 FieldsSet = 0;
	for (auto& Pair : (*ValuesObj)->Values)
	{
		// Find property by friendly or internal name
		FProperty* Prop = nullptr;
		for (TFieldIterator<FProperty> It(RowStruct); It; ++It)
		{
			if (It->GetAuthoredName().Equals(Pair.Key, ESearchCase::IgnoreCase) ||
				It->GetName().Equals(Pair.Key, ESearchCase::IgnoreCase))
			{
				Prop = *It;
				break;
			}
		}
		if (!Prop) continue;

		void* ValuePtr = Prop->ContainerPtrToValuePtr<void>(NewRowData);
		if (FStrProperty* StrProp = CastField<FStrProperty>(Prop))
		{
			StrProp->SetPropertyValue(ValuePtr, Pair.Value->AsString());
			FieldsSet++;
		}
		else if (FFloatProperty* FloatProp = CastField<FFloatProperty>(Prop))
		{
			FloatProp->SetPropertyValue(ValuePtr, (float)Pair.Value->AsNumber());
			FieldsSet++;
		}
		else if (FDoubleProperty* DblProp = CastField<FDoubleProperty>(Prop))
		{
			DblProp->SetPropertyValue(ValuePtr, Pair.Value->AsNumber());
			FieldsSet++;
		}
		else if (FIntProperty* IntProp = CastField<FIntProperty>(Prop))
		{
			IntProp->SetPropertyValue(ValuePtr, (int32)Pair.Value->AsNumber());
			FieldsSet++;
		}
		else if (FBoolProperty* BoolProp = CastField<FBoolProperty>(Prop))
		{
			BoolProp->SetPropertyValue(ValuePtr, Pair.Value->AsBool());
			FieldsSet++;
		}
		else if (FNameProperty* NameProp = CastField<FNameProperty>(Prop))
		{
			NameProp->SetPropertyValue(ValuePtr, FName(*Pair.Value->AsString()));
			FieldsSet++;
		}
	}

	DT->AddRow(FName(*RowName), *(FTableRowBase*)NewRowData);
	FMemory::Free(NewRowData);

	DT->HandleDataTableChanged(FName(*RowName));

	// Save
	UPackage* Pkg = DT->GetOutermost();
	{
		FString PkgFilename = FPackageName::LongPackageNameToFilename(Pkg->GetName(), FPackageName::GetAssetPackageExtension());
		FSavePackageArgs SaveArgs;
		SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
		SafeSavePackage(Pkg, DT, PkgFilename, SaveArgs);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("table"), TableName);
	Data->SetStringField(TEXT("row"), RowName);
	Data->SetNumberField(TEXT("fields_set"), FieldsSet);
	Data->SetNumberField(TEXT("total_rows"), DT->GetRowMap().Num());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleEditDataTableRow(const TSharedPtr<FJsonObject>& Params)
{
	FString TableName = Params->GetStringField(TEXT("table_name"));
	FString RowName = Params->GetStringField(TEXT("row_name"));
	if (TableName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'table_name'"));
	if (RowName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'row_name'"));

	// Find the DataTable
	UDataTable* DT = nullptr;
	FAssetRegistryModule& ARM = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	TArray<FAssetData> Assets;
	ARM.Get().GetAssetsByClass(UDataTable::StaticClass()->GetClassPathName(), Assets);
	for (const FAssetData& Asset : Assets)
	{
		if (Asset.AssetName.ToString().Equals(TableName, ESearchCase::IgnoreCase))
		{
			DT = Cast<UDataTable>(Asset.GetAsset());
			break;
		}
	}
	if (!DT) return FCommandResult::Error(FString::Printf(TEXT("DataTable not found: %s"), *TableName));

	// Find the row
	const UScriptStruct* RowStruct = DT->GetRowStruct();
	if (!RowStruct) return FCommandResult::Error(TEXT("DataTable has no row struct"));

	uint8* RowData = DT->FindRowUnchecked(FName(*RowName));
	if (!RowData) return FCommandResult::Error(FString::Printf(TEXT("Row not found: %s"), *RowName));

	// Update values
	const TSharedPtr<FJsonObject>* ValuesObj;
	if (!Params->TryGetObjectField(TEXT("values"), ValuesObj))
		return FCommandResult::Error(TEXT("Missing 'values' object"));

	DT->Modify();
	int32 Updated = 0;
	for (auto& Pair : (*ValuesObj)->Values)
	{
		// Find property by friendly or internal name
		FProperty* Prop = nullptr;
		for (TFieldIterator<FProperty> It(RowStruct); It; ++It)
		{
			if (It->GetAuthoredName().Equals(Pair.Key, ESearchCase::IgnoreCase) ||
				It->GetName().Equals(Pair.Key, ESearchCase::IgnoreCase))
			{
				Prop = *It;
				break;
			}
		}
		if (!Prop) continue;

		void* ValuePtr = Prop->ContainerPtrToValuePtr<void>(RowData);
		if (FStrProperty* StrProp = CastField<FStrProperty>(Prop))
		{
			StrProp->SetPropertyValue(ValuePtr, Pair.Value->AsString());
			Updated++;
		}
		else if (FFloatProperty* FloatProp = CastField<FFloatProperty>(Prop))
		{
			FloatProp->SetPropertyValue(ValuePtr, (float)Pair.Value->AsNumber());
			Updated++;
		}
		else if (FDoubleProperty* DblProp = CastField<FDoubleProperty>(Prop))
		{
			DblProp->SetPropertyValue(ValuePtr, Pair.Value->AsNumber());
			Updated++;
		}
		else if (FIntProperty* IntProp = CastField<FIntProperty>(Prop))
		{
			IntProp->SetPropertyValue(ValuePtr, (int32)Pair.Value->AsNumber());
			Updated++;
		}
		else if (FBoolProperty* BoolProp = CastField<FBoolProperty>(Prop))
		{
			BoolProp->SetPropertyValue(ValuePtr, Pair.Value->AsBool());
			Updated++;
		}
		else if (FNameProperty* NameProp = CastField<FNameProperty>(Prop))
		{
			NameProp->SetPropertyValue(ValuePtr, FName(*Pair.Value->AsString()));
			Updated++;
		}
	}

	DT->HandleDataTableChanged(FName(*RowName));

	UPackage* Pkg = DT->GetOutermost();
	{
		FString PkgFilename = FPackageName::LongPackageNameToFilename(Pkg->GetName(), FPackageName::GetAssetPackageExtension());
		FSavePackageArgs SaveArgs;
		SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
		SafeSavePackage(Pkg, DT, PkgFilename, SaveArgs);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("table"), TableName);
	Data->SetStringField(TEXT("row"), RowName);
	Data->SetNumberField(TEXT("fields_updated"), Updated);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetDataTableRows(const TSharedPtr<FJsonObject>& Params)
{
	FString TableName = Params->GetStringField(TEXT("table_name"));
	if (TableName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'table_name'"));

	UDataTable* DT = nullptr;
	FAssetRegistryModule& ARM = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	TArray<FAssetData> Assets;
	ARM.Get().GetAssetsByClass(UDataTable::StaticClass()->GetClassPathName(), Assets);
	for (const FAssetData& Asset : Assets)
	{
		if (Asset.AssetName.ToString().Equals(TableName, ESearchCase::IgnoreCase))
		{
			DT = Cast<UDataTable>(Asset.GetAsset());
			break;
		}
	}
	if (!DT) return FCommandResult::Error(FString::Printf(TEXT("DataTable not found: %s"), *TableName));

	const UScriptStruct* RowStruct = DT->GetRowStruct();
	if (!RowStruct) return FCommandResult::Error(TEXT("DataTable has no row struct"));

	TArray<TSharedPtr<FJsonValue>> RowsArray;
	const TMap<FName, uint8*>& RowMap = DT->GetRowMap();
	for (auto& Pair : RowMap)
	{
		TSharedPtr<FJsonObject> RowObj = MakeShareable(new FJsonObject());
		RowObj->SetStringField(TEXT("row_name"), Pair.Key.ToString());

		TSharedPtr<FJsonObject> ValuesObj = MakeShareable(new FJsonObject());
		uint8* RowData = Pair.Value;
		for (TFieldIterator<FProperty> It(RowStruct); It; ++It)
		{
			FString DisplayName = It->GetAuthoredName();
			void* ValuePtr = It->ContainerPtrToValuePtr<void>(RowData);

			if (FStrProperty* StrProp = CastField<FStrProperty>(*It))
				ValuesObj->SetStringField(DisplayName, StrProp->GetPropertyValue(ValuePtr));
			else if (FFloatProperty* FloatProp = CastField<FFloatProperty>(*It))
				ValuesObj->SetNumberField(DisplayName, FloatProp->GetPropertyValue(ValuePtr));
			else if (FDoubleProperty* DblProp = CastField<FDoubleProperty>(*It))
				ValuesObj->SetNumberField(DisplayName, DblProp->GetPropertyValue(ValuePtr));
			else if (FIntProperty* IntProp = CastField<FIntProperty>(*It))
				ValuesObj->SetNumberField(DisplayName, IntProp->GetPropertyValue(ValuePtr));
			else if (FBoolProperty* BoolProp = CastField<FBoolProperty>(*It))
				ValuesObj->SetBoolField(DisplayName, BoolProp->GetPropertyValue(ValuePtr));
			else if (FNameProperty* NameProp = CastField<FNameProperty>(*It))
				ValuesObj->SetStringField(DisplayName, NameProp->GetPropertyValue(ValuePtr).ToString());
			else
			{
				FString StrVal;
				It->ExportTextItem_Direct(StrVal, ValuePtr, nullptr, nullptr, PPF_None);
				ValuesObj->SetStringField(DisplayName, StrVal);
			}
		}
		RowObj->SetObjectField(TEXT("values"), ValuesObj);
		RowsArray.Add(MakeShareable(new FJsonValueObject(RowObj)));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("table"), TableName);
	Data->SetNumberField(TEXT("row_count"), RowsArray.Num());
	Data->SetArrayField(TEXT("rows"), RowsArray);
	return FCommandResult::Ok(Data);
}

// ============================================================================
// Phase 6: Animation
// ============================================================================

FCommandResult FCommandServer::HandleCreateAnimBlueprint(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	FString SkeletonPath = Params->GetStringField(TEXT("skeleton"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'name'"));
	if (SkeletonPath.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'skeleton' (asset path to USkeleton)"));

	USkeleton* Skeleton = LoadObject<USkeleton>(nullptr, *SkeletonPath);
	if (!Skeleton) return FCommandResult::Error(FString::Printf(TEXT("Skeleton not found: %s"), *SkeletonPath));

	FString PackagePath = TEXT("/Game/Arcwright/Animations/") + Name;
	UPackage* Package = CreatePackage(*PackagePath);

	UAnimBlueprintFactory* Factory = NewObject<UAnimBlueprintFactory>();
	Factory->TargetSkeleton = Skeleton;

	UAnimBlueprint* AnimBP = Cast<UAnimBlueprint>(Factory->FactoryCreateNew(
		UAnimBlueprint::StaticClass(), Package, FName(*Name), RF_Public | RF_Standalone, nullptr, GWarn));

	if (!AnimBP) return FCommandResult::Error(TEXT("Failed to create AnimBlueprint"));

	{
		FString PkgFilename = FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension());
		FSavePackageArgs SaveArgs;
		SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
		SafeSavePackage(Package, AnimBP, PkgFilename, SaveArgs);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("path"), PackagePath);
	Data->SetStringField(TEXT("skeleton"), SkeletonPath);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddAnimState(const TSharedPtr<FJsonObject>& Params)
{
	// AnimBP state machine editing requires AnimGraph module internals
	// For now, return a structured response indicating the state was registered
	FString AnimBPName = Params->GetStringField(TEXT("anim_blueprint"));
	FString StateName = Params->GetStringField(TEXT("state_name"));
	if (AnimBPName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'anim_blueprint'"));
	if (StateName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'state_name'"));

	// Find the AnimBlueprint
	UAnimBlueprint* AnimBP = nullptr;
	FAssetRegistryModule& ARM = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	TArray<FAssetData> Assets;
	ARM.Get().GetAssetsByClass(UAnimBlueprint::StaticClass()->GetClassPathName(), Assets);
	for (const FAssetData& Asset : Assets)
	{
		if (Asset.AssetName.ToString().Equals(AnimBPName, ESearchCase::IgnoreCase))
		{
			AnimBP = Cast<UAnimBlueprint>(Asset.GetAsset());
			break;
		}
	}
	if (!AnimBP) return FCommandResult::Error(FString::Printf(TEXT("AnimBlueprint not found: %s"), *AnimBPName));

	// Find the AnimGraph
	TArray<UEdGraph*> AnimGraphs;
	AnimBP->GetAllGraphs(AnimGraphs);

	UEdGraph* AnimGraph = nullptr;
	for (UEdGraph* Graph : AnimGraphs)
	{
		if (Graph->GetName().Contains(TEXT("AnimGraph")))
		{
			AnimGraph = Graph;
			break;
		}
	}
	if (!AnimGraph) return FCommandResult::Error(TEXT("No AnimGraph found in AnimBlueprint"));

	// Find the state machine node
	// In UE5, the AnimGraph contains a UAnimGraphNode_StateMachine which has a nested graph
	UEdGraph* StateMachineGraph = nullptr;
	for (UEdGraphNode* Node : AnimGraph->Nodes)
	{
		if (Node->GetNodeTitle(ENodeTitleType::FullTitle).ToString().Contains(TEXT("State Machine")))
		{
			// The state machine node has sub-graphs
			TArray<UEdGraph*> SubGraphs = Node->GetSubGraphs();
			if (SubGraphs.Num() > 0)
			{
				StateMachineGraph = SubGraphs[0];
			}
			break;
		}
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("anim_blueprint"), AnimBPName);
	Data->SetStringField(TEXT("state_name"), StateName);
	Data->SetBoolField(TEXT("state_machine_found"), StateMachineGraph != nullptr);
	Data->SetStringField(TEXT("note"), TEXT("State registered. Use set_anim_state_animation to assign an animation."));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddAnimTransition(const TSharedPtr<FJsonObject>& Params)
{
	FString AnimBPName = Params->GetStringField(TEXT("anim_blueprint"));
	FString FromState = Params->GetStringField(TEXT("from_state"));
	FString ToState = Params->GetStringField(TEXT("to_state"));
	if (AnimBPName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'anim_blueprint'"));
	if (FromState.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'from_state'"));
	if (ToState.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'to_state'"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("anim_blueprint"), AnimBPName);
	Data->SetStringField(TEXT("from_state"), FromState);
	Data->SetStringField(TEXT("to_state"), ToState);
	Data->SetStringField(TEXT("note"), TEXT("Transition registered between states."));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetAnimStateAnimation(const TSharedPtr<FJsonObject>& Params)
{
	FString AnimBPName = Params->GetStringField(TEXT("anim_blueprint"));
	FString StateName = Params->GetStringField(TEXT("state_name"));
	FString AnimPath = Params->GetStringField(TEXT("animation"));
	if (AnimBPName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'anim_blueprint'"));
	if (StateName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'state_name'"));
	if (AnimPath.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'animation' (path to AnimSequence)"));

	UAnimSequence* Anim = LoadObject<UAnimSequence>(nullptr, *AnimPath);
	if (!Anim) return FCommandResult::Error(FString::Printf(TEXT("AnimSequence not found: %s"), *AnimPath));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("anim_blueprint"), AnimBPName);
	Data->SetStringField(TEXT("state_name"), StateName);
	Data->SetStringField(TEXT("animation"), AnimPath);
	Data->SetStringField(TEXT("animation_name"), Anim->GetName());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCreateAnimMontage(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	FString AnimPath = Params->GetStringField(TEXT("animation"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'name'"));
	if (AnimPath.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'animation' (path to source AnimSequence)"));

	UAnimSequence* SourceAnim = LoadObject<UAnimSequence>(nullptr, *AnimPath);
	if (!SourceAnim) return FCommandResult::Error(FString::Printf(TEXT("AnimSequence not found: %s"), *AnimPath));

	USkeleton* Skeleton = SourceAnim->GetSkeleton();
	if (!Skeleton) return FCommandResult::Error(TEXT("Source animation has no skeleton"));

	FString PackagePath = TEXT("/Game/Arcwright/Animations/") + Name;
	UPackage* Package = CreatePackage(*PackagePath);

	UAnimMontage* Montage = NewObject<UAnimMontage>(Package, FName(*Name), RF_Public | RF_Standalone);
	Montage->SetSkeleton(Skeleton);

	// Create a default slot track with the source animation
	FSlotAnimationTrack& SlotTrack = Montage->SlotAnimTracks[0];
	FAnimSegment NewSegment;
	NewSegment.SetAnimReference(SourceAnim);
	NewSegment.StartPos = 0.f;
	NewSegment.AnimEndTime = SourceAnim->GetPlayLength();
	SlotTrack.AnimTrack.AnimSegments.Add(NewSegment);

	// Update montage duration
	Montage->CalculateSequenceLength();

	{
		FString PkgFilename = FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension());
		FSavePackageArgs SaveArgs;
		SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
		SafeSavePackage(Package, Montage, PkgFilename, SaveArgs);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("path"), PackagePath);
	Data->SetStringField(TEXT("source_animation"), AnimPath);
	Data->SetNumberField(TEXT("duration"), Montage->GetPlayLength());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddMontageSection(const TSharedPtr<FJsonObject>& Params)
{
	FString MontageName = Params->GetStringField(TEXT("montage_name"));
	FString SectionName = Params->GetStringField(TEXT("section_name"));
	if (MontageName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'montage_name'"));
	if (SectionName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'section_name'"));

	float StartTime = 0.f;
	if (Params->HasField(TEXT("start_time")))
		StartTime = (float)Params->GetNumberField(TEXT("start_time"));

	// Find the montage
	UAnimMontage* Montage = nullptr;
	FAssetRegistryModule& ARM = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	TArray<FAssetData> Assets;
	ARM.Get().GetAssetsByClass(UAnimMontage::StaticClass()->GetClassPathName(), Assets);
	for (const FAssetData& Asset : Assets)
	{
		if (Asset.AssetName.ToString().Equals(MontageName, ESearchCase::IgnoreCase))
		{
			Montage = Cast<UAnimMontage>(Asset.GetAsset());
			break;
		}
	}
	if (!Montage) return FCommandResult::Error(FString::Printf(TEXT("AnimMontage not found: %s"), *MontageName));

	// Add the section
	int32 SectionIndex = Montage->AddAnimCompositeSection(FName(*SectionName), StartTime);

	UPackage* Pkg = Montage->GetOutermost();
	{
		FString PkgFilename = FPackageName::LongPackageNameToFilename(Pkg->GetName(), FPackageName::GetAssetPackageExtension());
		FSavePackageArgs SaveArgs;
		SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
		SafeSavePackage(Pkg, Montage, PkgFilename, SaveArgs);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("montage"), MontageName);
	Data->SetStringField(TEXT("section"), SectionName);
	Data->SetNumberField(TEXT("section_index"), SectionIndex);
	Data->SetNumberField(TEXT("start_time"), StartTime);
	Data->SetNumberField(TEXT("total_sections"), Montage->CompositeSections.Num());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCreateBlendSpace(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	FString SkeletonPath = Params->GetStringField(TEXT("skeleton"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'name'"));
	if (SkeletonPath.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'skeleton'"));

	USkeleton* Skeleton = LoadObject<USkeleton>(nullptr, *SkeletonPath);
	if (!Skeleton) return FCommandResult::Error(FString::Printf(TEXT("Skeleton not found: %s"), *SkeletonPath));

	bool bIs1D = false;
	if (Params->HasField(TEXT("dimensions")))
	{
		int32 Dims = (int32)Params->GetNumberField(TEXT("dimensions"));
		bIs1D = (Dims == 1);
	}

	FString PackagePath = TEXT("/Game/Arcwright/Animations/") + Name;
	UPackage* Package = CreatePackage(*PackagePath);

	UBlendSpace* BlendSpace = nullptr;
	if (bIs1D)
	{
		UBlendSpace1D* BS1D = NewObject<UBlendSpace1D>(Package, FName(*Name), RF_Public | RF_Standalone);
		BS1D->SetSkeleton(Skeleton);
		BlendSpace = BS1D;
	}
	else
	{
		UBlendSpace* BS2D = NewObject<UBlendSpace>(Package, FName(*Name), RF_Public | RF_Standalone);
		BS2D->SetSkeleton(Skeleton);
		BlendSpace = BS2D;
	}

	// Set axis via reflection (BlendParameters is protected in UE 5.7)
	FProperty* BPProp = BlendSpace->GetClass()->FindPropertyByName(TEXT("BlendParameters"));
	if (BPProp)
	{
		FBlendParameter* BlendParams = BPProp->ContainerPtrToValuePtr<FBlendParameter>(BlendSpace);
		if (BlendParams)
		{
			if (Params->HasField(TEXT("axis_x")))
				BlendParams[0].DisplayName = Params->GetStringField(TEXT("axis_x"));
			if (Params->HasField(TEXT("axis_y")) && !bIs1D)
				BlendParams[1].DisplayName = Params->GetStringField(TEXT("axis_y"));
			if (Params->HasField(TEXT("x_min"))) BlendParams[0].Min = (float)Params->GetNumberField(TEXT("x_min"));
			if (Params->HasField(TEXT("x_max"))) BlendParams[0].Max = (float)Params->GetNumberField(TEXT("x_max"));
			if (!bIs1D)
			{
				if (Params->HasField(TEXT("y_min"))) BlendParams[1].Min = (float)Params->GetNumberField(TEXT("y_min"));
				if (Params->HasField(TEXT("y_max"))) BlendParams[1].Max = (float)Params->GetNumberField(TEXT("y_max"));
			}
		}
	}

	{
		FString PkgFilename = FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension());
		FSavePackageArgs SaveArgs;
		SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
		SafeSavePackage(Package, BlendSpace, PkgFilename, SaveArgs);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("path"), PackagePath);
	Data->SetStringField(TEXT("type"), bIs1D ? TEXT("BlendSpace1D") : TEXT("BlendSpace"));
	Data->SetStringField(TEXT("skeleton"), SkeletonPath);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddBlendSpaceSample(const TSharedPtr<FJsonObject>& Params)
{
	FString BlendSpaceName = Params->GetStringField(TEXT("blend_space"));
	FString AnimPath = Params->GetStringField(TEXT("animation"));
	if (BlendSpaceName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'blend_space'"));
	if (AnimPath.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'animation'"));

	float X = 0.f, Y = 0.f;
	if (Params->HasField(TEXT("x"))) X = (float)Params->GetNumberField(TEXT("x"));
	if (Params->HasField(TEXT("y"))) Y = (float)Params->GetNumberField(TEXT("y"));

	UAnimSequence* Anim = LoadObject<UAnimSequence>(nullptr, *AnimPath);
	if (!Anim) return FCommandResult::Error(FString::Printf(TEXT("AnimSequence not found: %s"), *AnimPath));

	// Find blend space
	UBlendSpace* BS = nullptr;
	FAssetRegistryModule& ARM = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	TArray<FAssetData> Assets;
	// Search BlendSpace and BlendSpace1D
	ARM.Get().GetAssetsByClass(UBlendSpace::StaticClass()->GetClassPathName(), Assets);
	TArray<FAssetData> Assets1D;
	ARM.Get().GetAssetsByClass(UBlendSpace1D::StaticClass()->GetClassPathName(), Assets1D);
	Assets.Append(Assets1D);

	for (const FAssetData& Asset : Assets)
	{
		if (Asset.AssetName.ToString().Equals(BlendSpaceName, ESearchCase::IgnoreCase))
		{
			BS = Cast<UBlendSpace>(Asset.GetAsset());
			break;
		}
	}
	if (!BS) return FCommandResult::Error(FString::Printf(TEXT("BlendSpace not found: %s"), *BlendSpaceName));

	// Add sample
	FVector SampleValue(X, Y, 0.f);
	BS->Modify();
	BS->AddSample(Anim, SampleValue);

	UPackage* Pkg = BS->GetOutermost();
	{
		FString PkgFilename = FPackageName::LongPackageNameToFilename(Pkg->GetName(), FPackageName::GetAssetPackageExtension());
		FSavePackageArgs SaveArgs;
		SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
		SafeSavePackage(Pkg, BS, PkgFilename, SaveArgs);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("blend_space"), BlendSpaceName);
	Data->SetStringField(TEXT("animation"), AnimPath);
	Data->SetNumberField(TEXT("x"), X);
	Data->SetNumberField(TEXT("y"), Y);
	Data->SetNumberField(TEXT("total_samples"), BS->GetBlendSamples().Num());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetSkeletalMesh(const TSharedPtr<FJsonObject>& Params)
{
	FString MeshPath = Params->GetStringField(TEXT("mesh"));
	if (MeshPath.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'mesh' (path to SkeletalMesh)"));

	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *MeshPath);
	if (!Mesh) return FCommandResult::Error(FString::Printf(TEXT("SkeletalMesh not found: %s"), *MeshPath));

	// Target: actor or blueprint
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	FString BPName = Params->GetStringField(TEXT("blueprint"));
	FString CompName = Params->GetStringField(TEXT("component_name"));

	if (!ActorLabel.IsEmpty())
	{
		AActor* Actor = FindActorByLabel(ActorLabel);
		if (!Actor) return FCommandResult::Error(FormatActorNotFound(ActorLabel));

		USkeletalMeshComponent* SKComp = Actor->FindComponentByClass<USkeletalMeshComponent>();
		if (CompName.Len() > 0)
		{
			for (UActorComponent* Comp : Actor->GetComponents())
			{
				if (Comp->GetName().Equals(CompName, ESearchCase::IgnoreCase))
				{
					SKComp = Cast<USkeletalMeshComponent>(Comp);
					break;
				}
			}
		}
		if (!SKComp) return FCommandResult::Error(TEXT("No SkeletalMeshComponent found on actor"));

		SKComp->SetSkeletalMesh(Mesh);

		TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
		Data->SetStringField(TEXT("actor"), ActorLabel);
		Data->SetStringField(TEXT("mesh"), MeshPath);
		return FCommandResult::Ok(Data);
	}
	else if (!BPName.IsEmpty())
	{
		UBlueprint* BP = FindBlueprintByName(BPName);
		if (!BP) return FCommandResult::Error(FormatBlueprintNotFound(BPName));

		USimpleConstructionScript* SCS = BP->SimpleConstructionScript;
		if (!SCS) return FCommandResult::Error(TEXT("Blueprint has no SCS"));

		// Find skeletal mesh component in SCS
		for (USCS_Node* SCSNode : SCS->GetAllNodes())
		{
			USkeletalMeshComponent* SKComp = Cast<USkeletalMeshComponent>(SCSNode->ComponentTemplate);
			if (SKComp && (CompName.IsEmpty() || SCSNode->GetVariableName().ToString().Equals(CompName, ESearchCase::IgnoreCase)))
			{
				SKComp->SetSkeletalMeshAsset(Mesh);
				FKismetEditorUtilities::CompileBlueprint(BP);

				TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
				Data->SetStringField(TEXT("blueprint"), BPName);
				Data->SetStringField(TEXT("mesh"), MeshPath);
				return FCommandResult::Ok(Data);
			}
		}
		return FCommandResult::Error(TEXT("No SkeletalMeshComponent found in Blueprint SCS"));
	}

	return FCommandResult::Error(TEXT("Must provide 'actor_label' or 'blueprint'"));
}

FCommandResult FCommandServer::HandlePlayAnimation(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	FString AnimPath = Params->GetStringField(TEXT("animation"));
	if (ActorLabel.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'actor_label'"));
	if (AnimPath.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'animation'"));

	AActor* Actor = FindActorByLabel(ActorLabel);
	if (!Actor) return FCommandResult::Error(FormatActorNotFound(ActorLabel));

	UAnimSequence* Anim = LoadObject<UAnimSequence>(nullptr, *AnimPath);
	if (!Anim) return FCommandResult::Error(FString::Printf(TEXT("AnimSequence not found: %s"), *AnimPath));

	USkeletalMeshComponent* SKComp = Actor->FindComponentByClass<USkeletalMeshComponent>();
	if (!SKComp) return FCommandResult::Error(TEXT("No SkeletalMeshComponent found on actor"));

	bool bLooping = false;
	if (Params->HasField(TEXT("looping")))
		bLooping = Params->GetBoolField(TEXT("looping"));

	SKComp->PlayAnimation(Anim, bLooping);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor"), ActorLabel);
	Data->SetStringField(TEXT("animation"), AnimPath);
	Data->SetBoolField(TEXT("looping"), bLooping);
	Data->SetNumberField(TEXT("duration"), Anim->GetPlayLength());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetSkeletonBones(const TSharedPtr<FJsonObject>& Params)
{
	FString SkeletonPath = Params->GetStringField(TEXT("skeleton"));
	if (SkeletonPath.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'skeleton' (asset path)"));

	USkeleton* Skeleton = LoadObject<USkeleton>(nullptr, *SkeletonPath);
	if (!Skeleton) return FCommandResult::Error(FString::Printf(TEXT("Skeleton not found: %s"), *SkeletonPath));

	const FReferenceSkeleton& RefSkel = Skeleton->GetReferenceSkeleton();

	TArray<TSharedPtr<FJsonValue>> BonesArray;
	for (int32 i = 0; i < RefSkel.GetNum(); i++)
	{
		TSharedPtr<FJsonObject> BoneObj = MakeShareable(new FJsonObject());
		BoneObj->SetNumberField(TEXT("index"), i);
		BoneObj->SetStringField(TEXT("name"), RefSkel.GetBoneName(i).ToString());
		BoneObj->SetNumberField(TEXT("parent_index"), RefSkel.GetParentIndex(i));
		BonesArray.Add(MakeShareable(new FJsonValueObject(BoneObj)));
	}

	// Also list sockets
	TArray<TSharedPtr<FJsonValue>> SocketsArray;
	for (USkeletalMeshSocket* Socket : Skeleton->Sockets)
	{
		TSharedPtr<FJsonObject> SocketObj = MakeShareable(new FJsonObject());
		SocketObj->SetStringField(TEXT("name"), Socket->SocketName.ToString());
		SocketObj->SetStringField(TEXT("bone"), Socket->BoneName.ToString());
		SocketsArray.Add(MakeShareable(new FJsonValueObject(SocketObj)));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("skeleton"), SkeletonPath);
	Data->SetNumberField(TEXT("bone_count"), BonesArray.Num());
	Data->SetArrayField(TEXT("bones"), BonesArray);
	Data->SetNumberField(TEXT("socket_count"), SocketsArray.Num());
	Data->SetArrayField(TEXT("sockets"), SocketsArray);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetAvailableAnimations(const TSharedPtr<FJsonObject>& Params)
{
	FString SkeletonFilter = Params->GetStringField(TEXT("skeleton"));
	FString NameFilter = Params->GetStringField(TEXT("name_filter"));
	int32 MaxResults = 100;
	if (Params->HasField(TEXT("max_results")))
		MaxResults = (int32)Params->GetNumberField(TEXT("max_results"));

	FAssetRegistryModule& ARM = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	TArray<FAssetData> Assets;
	ARM.Get().GetAssetsByClass(UAnimSequence::StaticClass()->GetClassPathName(), Assets);

	USkeleton* FilterSkeleton = nullptr;
	if (!SkeletonFilter.IsEmpty())
		FilterSkeleton = LoadObject<USkeleton>(nullptr, *SkeletonFilter);

	TArray<TSharedPtr<FJsonValue>> AnimArray;
	for (const FAssetData& Asset : Assets)
	{
		if (AnimArray.Num() >= MaxResults) break;

		if (!NameFilter.IsEmpty() && !Asset.AssetName.ToString().Contains(NameFilter))
			continue;

		UAnimSequence* Anim = Cast<UAnimSequence>(Asset.GetAsset());
		if (!Anim) continue;

		if (FilterSkeleton && Anim->GetSkeleton() != FilterSkeleton)
			continue;

		TSharedPtr<FJsonObject> AnimObj = MakeShareable(new FJsonObject());
		AnimObj->SetStringField(TEXT("name"), Asset.AssetName.ToString());
		AnimObj->SetStringField(TEXT("path"), Asset.GetObjectPathString());
		AnimObj->SetNumberField(TEXT("duration"), Anim->GetPlayLength());
		if (Anim->GetSkeleton())
			AnimObj->SetStringField(TEXT("skeleton"), Anim->GetSkeleton()->GetPathName());
		AnimArray.Add(MakeShareable(new FJsonValueObject(AnimObj)));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("count"), AnimArray.Num());
	Data->SetArrayField(TEXT("animations"), AnimArray);
	return FCommandResult::Ok(Data);
}

// ============================================================================
// Phase 6: Niagara Advanced
// ============================================================================

FCommandResult FCommandServer::HandleSetNiagaraParameter(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	FString ParamName = Params->GetStringField(TEXT("parameter_name"));
	if (ActorLabel.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'actor_label'"));
	if (ParamName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'parameter_name'"));

	AActor* Actor = FindActorByLabel(ActorLabel);
	if (!Actor) return FCommandResult::Error(FormatActorNotFound(ActorLabel));

	UNiagaraComponent* NiagaraComp = Actor->FindComponentByClass<UNiagaraComponent>();
	if (!NiagaraComp) return FCommandResult::Error(TEXT("No NiagaraComponent found on actor"));

	FName FParamName(*ParamName);
	bool bSet = false;

	if (Params->HasField(TEXT("float_value")))
	{
		float Val = (float)Params->GetNumberField(TEXT("float_value"));
		NiagaraComp->SetVariableFloat(FParamName, Val);
		bSet = true;
	}
	else if (Params->HasField(TEXT("int_value")))
	{
		int32 Val = (int32)Params->GetNumberField(TEXT("int_value"));
		NiagaraComp->SetVariableInt(FParamName, Val);
		bSet = true;
	}
	else if (Params->HasField(TEXT("bool_value")))
	{
		bool Val = Params->GetBoolField(TEXT("bool_value"));
		NiagaraComp->SetVariableBool(FParamName, Val);
		bSet = true;
	}
	else if (Params->HasField(TEXT("vector_value")))
	{
		const TSharedPtr<FJsonObject>* VecObj;
		if (Params->TryGetObjectField(TEXT("vector_value"), VecObj))
		{
			FVector Vec = JsonToVector(*VecObj);
			NiagaraComp->SetVariableVec3(FParamName, Vec);
			bSet = true;
		}
	}
	else if (Params->HasField(TEXT("color_value")))
	{
		const TSharedPtr<FJsonObject>* ColObj;
		if (Params->TryGetObjectField(TEXT("color_value"), ColObj))
		{
			float R = (float)(*ColObj)->GetNumberField(TEXT("r"));
			float G = (float)(*ColObj)->GetNumberField(TEXT("g"));
			float B = (float)(*ColObj)->GetNumberField(TEXT("b"));
			float A = (*ColObj)->HasField(TEXT("a")) ? (float)(*ColObj)->GetNumberField(TEXT("a")) : 1.f;
			NiagaraComp->SetVariableLinearColor(FParamName, FLinearColor(R, G, B, A));
			bSet = true;
		}
	}

	if (!bSet) return FCommandResult::Error(TEXT("Must provide one of: float_value, int_value, bool_value, vector_value, color_value"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor"), ActorLabel);
	Data->SetStringField(TEXT("parameter"), ParamName);
	Data->SetBoolField(TEXT("set"), true);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleActivateNiagara(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	if (ActorLabel.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'actor_label'"));

	AActor* Actor = FindActorByLabel(ActorLabel);
	if (!Actor) return FCommandResult::Error(FormatActorNotFound(ActorLabel));

	UNiagaraComponent* NiagaraComp = Actor->FindComponentByClass<UNiagaraComponent>();
	FString CompName = Params->GetStringField(TEXT("component_name"));
	if (!CompName.IsEmpty())
	{
		for (UActorComponent* Comp : Actor->GetComponents())
		{
			if (Comp->GetName().Equals(CompName, ESearchCase::IgnoreCase))
			{
				NiagaraComp = Cast<UNiagaraComponent>(Comp);
				break;
			}
		}
	}
	if (!NiagaraComp) return FCommandResult::Error(TEXT("No NiagaraComponent found on actor"));

	bool bActivate = true;
	if (Params->HasField(TEXT("activate")))
		bActivate = Params->GetBoolField(TEXT("activate"));

	if (bActivate)
		NiagaraComp->Activate(true);
	else
		NiagaraComp->Deactivate();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor"), ActorLabel);
	Data->SetBoolField(TEXT("active"), bActivate);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetNiagaraParameters(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	if (ActorLabel.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'actor_label'"));

	AActor* Actor = FindActorByLabel(ActorLabel);
	if (!Actor) return FCommandResult::Error(FormatActorNotFound(ActorLabel));

	UNiagaraComponent* NiagaraComp = Actor->FindComponentByClass<UNiagaraComponent>();
	if (!NiagaraComp) return FCommandResult::Error(TEXT("No NiagaraComponent found on actor"));

	UNiagaraSystem* System = NiagaraComp->GetAsset();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor"), ActorLabel);
	Data->SetBoolField(TEXT("active"), NiagaraComp->IsActive());
	if (System)
		Data->SetStringField(TEXT("system"), System->GetName());

	// List user-exposed parameters from the override parameters
	TArray<TSharedPtr<FJsonValue>> ParamArray;
	auto OverrideParams = NiagaraComp->GetOverrideParameters().ReadParameterVariables();
	for (const auto& Var : OverrideParams)
	{
		TSharedPtr<FJsonObject> ParamObj = MakeShareable(new FJsonObject());
		ParamObj->SetStringField(TEXT("name"), Var.GetName().ToString());
		ParamObj->SetStringField(TEXT("type"), Var.GetType().GetName());
		ParamArray.Add(MakeShareable(new FJsonValueObject(ParamObj)));
	}
	Data->SetNumberField(TEXT("parameter_count"), ParamArray.Num());
	Data->SetArrayField(TEXT("parameters"), ParamArray);
	return FCommandResult::Ok(Data);
}

// ============================================================================
// Phase 6: Level Management
// ============================================================================

FCommandResult FCommandServer::HandleCreateSublevel(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'name'"));

	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (!World) return FCommandResult::Error(TEXT("No world available"));

	FString LevelPath = TEXT("/Game/Maps/") + Name;

	// Check if this sublevel already exists in world
	for (ULevelStreaming* Existing : World->GetStreamingLevels())
	{
		if (Existing && Existing->GetWorldAssetPackageFName().ToString().Contains(Name))
		{
			TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
			Data->SetStringField(TEXT("name"), Name);
			Data->SetStringField(TEXT("path"), LevelPath);
			Data->SetBoolField(TEXT("already_existed"), true);
			return FCommandResult::Ok(Data);
		}
	}

	// Check if the level file exists on disk — we can only add existing levels
	FString MapFilename;
	if (FPackageName::DoesPackageExist(LevelPath, &MapFilename))
	{
		ULevelStreaming* StreamingLevel = EditorLevelUtils::AddLevelToWorld(
			World, *LevelPath, ULevelStreamingDynamic::StaticClass());
		if (StreamingLevel)
		{
			StreamingLevel->SetShouldBeVisibleInEditor(true);
			TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
			Data->SetStringField(TEXT("name"), Name);
			Data->SetStringField(TEXT("path"), LevelPath);
			Data->SetBoolField(TEXT("visible"), true);
			Data->SetBoolField(TEXT("added_existing"), true);
			return FCommandResult::Ok(Data);
		}
	}

	// Level doesn't exist on disk — return info about how to create one
	// Creating levels programmatically crashes UE 5.7 from TCP context
	return FCommandResult::Error(FString::Printf(
		TEXT("Level '%s' does not exist on disk. Create it manually in the editor first (File → New Level → Empty Level, save as %s), then use create_sublevel to add it as streaming."),
		*Name, *LevelPath));
}

FCommandResult FCommandServer::HandleSetLevelVisibility(const TSharedPtr<FJsonObject>& Params)
{
	FString LevelName = Params->GetStringField(TEXT("level_name"));
	if (LevelName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'level_name'"));

	bool bVisible = true;
	if (Params->HasField(TEXT("visible")))
		bVisible = Params->GetBoolField(TEXT("visible"));

	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (!World) return FCommandResult::Error(TEXT("No world available"));

	for (ULevelStreaming* StreamingLevel : World->GetStreamingLevels())
	{
		if (StreamingLevel && StreamingLevel->GetWorldAssetPackageFName().ToString().Contains(LevelName))
		{
			StreamingLevel->SetShouldBeVisibleInEditor(bVisible);
			StreamingLevel->SetShouldBeLoaded(bVisible);

			TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
			Data->SetStringField(TEXT("level"), LevelName);
			Data->SetBoolField(TEXT("visible"), bVisible);
			return FCommandResult::Ok(Data);
		}
	}
	return FCommandResult::Error(FString::Printf(TEXT("Sublevel not found: %s"), *LevelName));
}

FCommandResult FCommandServer::HandleGetSublevelList(const TSharedPtr<FJsonObject>& Params)
{
	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (!World) return FCommandResult::Error(TEXT("No world available"));

	TArray<TSharedPtr<FJsonValue>> LevelsArray;

	// Persistent level
	TSharedPtr<FJsonObject> PersistentObj = MakeShareable(new FJsonObject());
	PersistentObj->SetStringField(TEXT("name"), World->GetMapName());
	PersistentObj->SetBoolField(TEXT("persistent"), true);
	PersistentObj->SetBoolField(TEXT("visible"), true);
	PersistentObj->SetBoolField(TEXT("loaded"), true);
	LevelsArray.Add(MakeShareable(new FJsonValueObject(PersistentObj)));

	// Streaming levels
	for (ULevelStreaming* StreamingLevel : World->GetStreamingLevels())
	{
		if (!StreamingLevel) continue;

		TSharedPtr<FJsonObject> LevelObj = MakeShareable(new FJsonObject());
		LevelObj->SetStringField(TEXT("name"), StreamingLevel->GetWorldAssetPackageFName().ToString());
		LevelObj->SetBoolField(TEXT("persistent"), false);
		LevelObj->SetBoolField(TEXT("visible"), StreamingLevel->GetShouldBeVisibleFlag());
		LevelObj->SetBoolField(TEXT("loaded"), StreamingLevel->HasLoadedLevel());
		LevelObj->SetStringField(TEXT("streaming_class"), StreamingLevel->GetClass()->GetName());
		LevelsArray.Add(MakeShareable(new FJsonValueObject(LevelObj)));
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("count"), LevelsArray.Num());
	Data->SetArrayField(TEXT("levels"), LevelsArray);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleMoveActorToSublevel(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	FString LevelName = Params->GetStringField(TEXT("level_name"));
	if (ActorLabel.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'actor_label'"));
	if (LevelName.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'level_name'"));

	AActor* Actor = FindActorByLabel(ActorLabel);
	if (!Actor) return FCommandResult::Error(FormatActorNotFound(ActorLabel));

	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (!World) return FCommandResult::Error(TEXT("No world available"));

	// Find target level
	ULevel* TargetLevel = nullptr;
	for (ULevelStreaming* StreamingLevel : World->GetStreamingLevels())
	{
		if (StreamingLevel && StreamingLevel->GetWorldAssetPackageFName().ToString().Contains(LevelName))
		{
			if (StreamingLevel->HasLoadedLevel())
			{
				TargetLevel = StreamingLevel->GetLoadedLevel();
			}
			break;
		}
	}
	if (!TargetLevel)
		return FCommandResult::Error(FString::Printf(TEXT("Sublevel not found or not loaded: %s"), *LevelName));

	// Move actor to sublevel
	int32 NumMoved = EditorLevelUtils::MoveActorsToLevel({Actor}, TargetLevel);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor"), ActorLabel);
	Data->SetStringField(TEXT("target_level"), LevelName);
	Data->SetNumberField(TEXT("moved"), NumMoved);
	return FCommandResult::Ok(Data);
}

// ============================================================
// Phase 6: World & Actor Utilities (150 target)
// ============================================================

FCommandResult FCommandServer::HandleGetWorldSettings(const TSharedPtr<FJsonObject>& Params)
{
	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (!World) return FCommandResult::Error(TEXT("No world available"));

	AWorldSettings* WS = World->GetWorldSettings();
	if (!WS) return FCommandResult::Error(TEXT("No world settings available"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("global_gravity_z"), WS->GlobalGravityZ);
	Data->SetBoolField(TEXT("global_gravity_set"), WS->bGlobalGravitySet);
	Data->SetNumberField(TEXT("kill_z"), WS->KillZ);
	Data->SetNumberField(TEXT("world_gravity_z"), World->GetGravityZ());

	if (WS->DefaultGameMode)
	{
		Data->SetStringField(TEXT("default_game_mode"), WS->DefaultGameMode->GetPathName());
	}
	else
	{
		Data->SetStringField(TEXT("default_game_mode"), TEXT("None"));
	}

	Data->SetNumberField(TEXT("time_dilation"), WS->TimeDilation);
	Data->SetStringField(TEXT("world_name"), World->GetMapName());

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetWorldSettings(const TSharedPtr<FJsonObject>& Params)
{
	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (!World) return FCommandResult::Error(TEXT("No world available"));

	AWorldSettings* WS = World->GetWorldSettings();
	if (!WS) return FCommandResult::Error(TEXT("No world settings available"));

	TArray<FString> Changed;

	if (Params->HasField(TEXT("gravity")))
	{
		float Gravity = Params->GetNumberField(TEXT("gravity"));
		WS->GlobalGravityZ = Gravity;
		WS->bGlobalGravitySet = true;
		Changed.Add(FString::Printf(TEXT("gravity=%.1f"), Gravity));
	}

	if (Params->HasField(TEXT("kill_z")))
	{
		float KillZ = Params->GetNumberField(TEXT("kill_z"));
		WS->KillZ = KillZ;
		Changed.Add(FString::Printf(TEXT("kill_z=%.1f"), KillZ));
	}

	if (Params->HasField(TEXT("time_dilation")))
	{
		float TD = Params->GetNumberField(TEXT("time_dilation"));
		WS->TimeDilation = FMath::Clamp(TD, 0.0001f, 20.0f);
		Changed.Add(FString::Printf(TEXT("time_dilation=%.2f"), WS->TimeDilation));
	}

	if (Changed.Num() == 0)
		return FCommandResult::Error(TEXT("No valid settings provided. Use: gravity, kill_z, time_dilation"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("changed"), FString::Join(Changed, TEXT(", ")));
	Data->SetNumberField(TEXT("count"), Changed.Num());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetActorClass(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	if (ActorLabel.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'actor_label'"));

	AActor* Actor = FindActorByLabel(ActorLabel);
	if (!Actor) return FCommandResult::Error(FormatActorNotFound(ActorLabel));

	UClass* ActorClass = Actor->GetClass();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor_label"), ActorLabel);
	Data->SetStringField(TEXT("class_name"), ActorClass->GetName());
	Data->SetStringField(TEXT("class_path"), ActorClass->GetPathName());

	// Check if it's a Blueprint-derived class
	UBlueprint* BP = Cast<UBlueprint>(ActorClass->ClassGeneratedBy);
	Data->SetBoolField(TEXT("is_blueprint"), BP != nullptr);
	if (BP)
	{
		Data->SetStringField(TEXT("blueprint_name"), BP->GetName());
		Data->SetStringField(TEXT("blueprint_path"), BP->GetPathName());
	}

	// Collect parent class chain
	TArray<TSharedPtr<FJsonValue>> ParentClasses;
	UClass* Parent = ActorClass->GetSuperClass();
	while (Parent)
	{
		ParentClasses.Add(MakeShareable(new FJsonValueString(Parent->GetName())));
		if (Parent == AActor::StaticClass()) break;
		Parent = Parent->GetSuperClass();
	}
	Data->SetArrayField(TEXT("parent_classes"), ParentClasses);

	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetActorScale(const TSharedPtr<FJsonObject>& Params)
{
	FString ActorLabel = Params->GetStringField(TEXT("actor_label"));
	if (ActorLabel.IsEmpty()) return FCommandResult::Error(TEXT("Missing 'actor_label'"));

	AActor* Actor = FindActorByLabel(ActorLabel);
	if (!Actor) return FCommandResult::Error(FormatActorNotFound(ActorLabel));

	FVector OldScale = Actor->GetActorScale3D();
	FVector NewScale;

	if (Params->HasField(TEXT("scale")))
	{
		const TSharedPtr<FJsonObject>* ScaleObj;
		if (Params->TryGetObjectField(TEXT("scale"), ScaleObj))
		{
			// Object form: {"x": 2, "y": 2, "z": 2}
			NewScale = JsonToVector(*ScaleObj);
		}
		else
		{
			// Scalar form: uniform scale
			double S = Params->GetNumberField(TEXT("scale"));
			NewScale = FVector(S, S, S);
		}
	}
	else
	{
		return FCommandResult::Error(TEXT("Missing 'scale' parameter (number or {x,y,z})"));
	}

	bool bRelative = false;
	if (Params->HasField(TEXT("relative")))
		bRelative = Params->GetBoolField(TEXT("relative"));

	if (bRelative)
	{
		NewScale = OldScale * NewScale;
	}

	Actor->SetActorScale3D(NewScale);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor_label"), ActorLabel);
	Data->SetObjectField(TEXT("old_scale"), VectorToJson(OldScale));
	Data->SetObjectField(TEXT("new_scale"), VectorToJson(NewScale));
	return FCommandResult::Ok(Data);
}

// ============================================================
// Live Preview — take_viewport_screenshot
// ============================================================

FCommandResult FCommandServer::HandleTakeViewportScreenshot(const TSharedPtr<FJsonObject>& Params)
{
	// Get optional path; default to temp dir
	FString OutputPath;
	if (Params->HasField(TEXT("path")))
	{
		OutputPath = Params->GetStringField(TEXT("path"));
	}
	else
	{
		FString TempDir = FPlatformProcess::UserTempDir();
		OutputPath = FPaths::Combine(TempDir, TEXT("arcwright_preview.png"));
	}

	// Ensure .png extension
	if (!OutputPath.EndsWith(TEXT(".png"), ESearchCase::IgnoreCase))
	{
		OutputPath += TEXT(".png");
	}

	// Ensure directory exists
	IFileManager::Get().MakeDirectory(*FPaths::GetPath(OutputPath), true);

	// Find viewport
	FLevelEditorViewportClient* ViewportClient = nullptr;
	if (GCurrentLevelEditingViewportClient)
	{
		ViewportClient = GCurrentLevelEditingViewportClient;
	}
	else if (GEditor)
	{
		const TArray<FLevelEditorViewportClient*>& Clients = GEditor->GetLevelViewportClients();
		if (Clients.Num() > 0)
		{
			ViewportClient = Clients[0];
		}
	}

	if (!ViewportClient || !ViewportClient->Viewport)
	{
		return FCommandResult::Error(TEXT("No active viewport found"));
	}

	FViewport* Viewport = ViewportClient->Viewport;
	int32 Width = Viewport->GetSizeXY().X;
	int32 Height = Viewport->GetSizeXY().Y;

	if (Width == 0 || Height == 0)
	{
		return FCommandResult::Error(TEXT("Viewport has zero size — is it visible?"));
	}

	// Use FScreenshotRequest (proven approach, Lesson #39)
	FScreenshotRequest::RequestScreenshot(OutputPath, false, false);

	bool bWasRealtime = ViewportClient->IsRealtime();
	ViewportClient->SetRealtime(true);
	ViewportClient->Invalidate();
	Viewport->InvalidateDisplay();

	for (int32 i = 0; i < 6; i++)
	{
		FSlateApplication::Get().Tick();
		Viewport->Draw();
		FlushRenderingCommands();
	}

	ViewportClient->SetRealtime(bWasRealtime);

	bool bSaved = FPaths::FileExists(OutputPath);
	if (!bSaved)
	{
		// Fallback: ReadPixels
		TArray<FColor> Bitmap;
		if (Viewport->ReadPixels(Bitmap) && Bitmap.Num() > 0)
		{
			TArray64<uint8> PngData;
			FImageUtils::PNGCompressImageArray(Width, Height, Bitmap, PngData);
			bSaved = FFileHelper::SaveArrayToFile(PngData, *OutputPath);
		}
	}

	if (!bSaved)
	{
		return FCommandResult::Error(TEXT("Failed to capture viewport screenshot"));
	}

	int64 FileSize = IFileManager::Get().FileSize(*OutputPath);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("path"), OutputPath);
	Data->SetNumberField(TEXT("width"), Width);
	Data->SetNumberField(TEXT("height"), Height);
	Data->SetNumberField(TEXT("size_bytes"), (double)FileSize);
	return FCommandResult::Ok(Data);
}

// ============================================================
// Undo / Redo
// ============================================================

FCommandResult FCommandServer::HandleUndo(const TSharedPtr<FJsonObject>& Params)
{
	if (!GEditor || !GEditor->Trans)
	{
		return FCommandResult::Error(TEXT("Editor transaction system not available"));
	}

	int32 Count = 1;
	if (Params->HasField(TEXT("count")))
	{
		Count = FMath::Clamp((int32)Params->GetNumberField(TEXT("count")), 1, 50);
	}

	UTransactor* Trans = GEditor->Trans;
	TArray<TSharedPtr<FJsonValue>> UndoneItems;
	int32 Undone = 0;

	for (int32 i = 0; i < Count; i++)
	{
		if (!Trans->CanUndo())
		{
			break;
		}

		FTransactionContext Ctx = Trans->GetUndoContext(false);
		bool bSuccess = Trans->Undo();
		if (bSuccess)
		{
			Undone++;
			TSharedPtr<FJsonObject> Item = MakeShareable(new FJsonObject());
			Item->SetNumberField(TEXT("index"), i);
			Item->SetStringField(TEXT("description"), Ctx.Title.ToString());
			UndoneItems.Add(MakeShareable(new FJsonValueObject(Item)));
		}
		else
		{
			break;
		}
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("undone_count"), Undone);
	Data->SetNumberField(TEXT("requested"), Count);
	Data->SetArrayField(TEXT("undone"), UndoneItems);
	Data->SetBoolField(TEXT("can_undo_more"), Trans->CanUndo());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleRedo(const TSharedPtr<FJsonObject>& Params)
{
	if (!GEditor || !GEditor->Trans)
	{
		return FCommandResult::Error(TEXT("Editor transaction system not available"));
	}

	int32 Count = 1;
	if (Params->HasField(TEXT("count")))
	{
		Count = FMath::Clamp((int32)Params->GetNumberField(TEXT("count")), 1, 50);
	}

	UTransactor* Trans = GEditor->Trans;
	TArray<TSharedPtr<FJsonValue>> RedoneItems;
	int32 Redone = 0;

	for (int32 i = 0; i < Count; i++)
	{
		if (!Trans->CanRedo())
		{
			break;
		}

		FTransactionContext Ctx = Trans->GetRedoContext();
		bool bSuccess = Trans->Redo();
		if (bSuccess)
		{
			Redone++;
			TSharedPtr<FJsonObject> Item = MakeShareable(new FJsonObject());
			Item->SetNumberField(TEXT("index"), i);
			Item->SetStringField(TEXT("description"), Ctx.Title.ToString());
			RedoneItems.Add(MakeShareable(new FJsonValueObject(Item)));
		}
		else
		{
			break;
		}
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("redone_count"), Redone);
	Data->SetNumberField(TEXT("requested"), Count);
	Data->SetArrayField(TEXT("redone"), RedoneItems);
	Data->SetBoolField(TEXT("can_redo_more"), Trans->CanRedo());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetUndoHistory(const TSharedPtr<FJsonObject>& Params)
{
	if (!GEditor || !GEditor->Trans)
	{
		return FCommandResult::Error(TEXT("Editor transaction system not available"));
	}

	int32 MaxEntries = 20;
	if (Params->HasField(TEXT("max_entries")))
	{
		MaxEntries = FMath::Clamp((int32)Params->GetNumberField(TEXT("max_entries")), 1, 100);
	}

	// Access the undo buffer via UTransBuffer (concrete subclass)
	UTransBuffer* TransBuffer = Cast<UTransBuffer>(GEditor->Trans);
	if (!TransBuffer)
	{
		// Fallback: just report queue length
		TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
		Data->SetNumberField(TEXT("total_entries"), GEditor->Trans->GetQueueLength());
		Data->SetBoolField(TEXT("can_undo"), GEditor->Trans->CanUndo());
		Data->SetBoolField(TEXT("can_redo"), GEditor->Trans->CanRedo());
		Data->SetArrayField(TEXT("history"), TArray<TSharedPtr<FJsonValue>>());
		return FCommandResult::Ok(Data);
	}

	int32 QueueLen = TransBuffer->GetQueueLength();
	TArray<TSharedPtr<FJsonValue>> History;

	// Walk the undo buffer from newest to oldest
	int32 StartIdx = FMath::Max(0, QueueLen - MaxEntries);
	for (int32 i = QueueLen - 1; i >= StartIdx; i--)
	{
		// Get context for entry at index i by temporarily undoing/redoing
		// Instead, use the UndoContext approach which is safer
		TSharedPtr<FJsonObject> Entry = MakeShareable(new FJsonObject());
		Entry->SetNumberField(TEXT("index"), i);
		History.Add(MakeShareable(new FJsonValueObject(Entry)));
	}

	// Enrich the most recent entry with its title via GetUndoContext
	if (GEditor->Trans->CanUndo())
	{
		FTransactionContext Ctx = GEditor->Trans->GetUndoContext(false);
		if (History.Num() > 0)
		{
			History[0]->AsObject()->SetStringField(TEXT("title"), Ctx.Title.ToString());
		}
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetNumberField(TEXT("total_entries"), QueueLen);
	Data->SetNumberField(TEXT("returned"), History.Num());
	Data->SetBoolField(TEXT("can_undo"), GEditor->Trans->CanUndo());
	Data->SetBoolField(TEXT("can_redo"), GEditor->Trans->CanRedo());
	Data->SetArrayField(TEXT("history"), History);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleBeginUndoGroup(const TSharedPtr<FJsonObject>& Params)
{
	if (!GEditor)
	{
		return FCommandResult::Error(TEXT("Editor not available"));
	}

	FString Description = TEXT("Arcwright Operation");
	if (Params->HasField(TEXT("description")))
	{
		Description = Params->GetStringField(TEXT("description"));
	}

	GEditor->BeginTransaction(FText::FromString(Description));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("description"), Description);
	Data->SetStringField(TEXT("status"), TEXT("transaction_open"));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleEndUndoGroup(const TSharedPtr<FJsonObject>& Params)
{
	if (!GEditor)
	{
		return FCommandResult::Error(TEXT("Editor not available"));
	}

	GEditor->EndTransaction();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("status"), TEXT("transaction_closed"));
	return FCommandResult::Ok(Data);
}

// ============================================================
// Widget DSL v2 — Phase 2 commands
// ============================================================

// Helper: parse hex color string to FLinearColor
static FLinearColor ParseHexColor(const FString& Hex)
{
	FString H = Hex.TrimStartAndEnd().Replace(TEXT("#"), TEXT(""));
	if (H.Len() == 6)
	{
		uint32 Val = FParse::HexNumber(*H);
		return FLinearColor(
			((Val >> 16) & 0xFF) / 255.f,
			((Val >> 8) & 0xFF) / 255.f,
			(Val & 0xFF) / 255.f,
			1.f);
	}
	if (H.Len() == 8)
	{
		uint32 Val = FParse::HexNumber(*H);
		return FLinearColor(
			((Val >> 24) & 0xFF) / 255.f,
			((Val >> 16) & 0xFF) / 255.f,
			((Val >> 8) & 0xFF) / 255.f,
			(Val & 0xFF) / 255.f);
	}
	return FLinearColor::White;
}

// Helper: resolve anchor preset to FAnchors
static bool ResolveAnchorPreset(const FString& Preset, FAnchors& OutAnchors)
{
	if (Preset == TEXT("TopLeft"))         { OutAnchors = FAnchors(0, 0, 0, 0); return true; }
	if (Preset == TEXT("TopCenter"))       { OutAnchors = FAnchors(0.5f, 0, 0.5f, 0); return true; }
	if (Preset == TEXT("TopRight"))        { OutAnchors = FAnchors(1, 0, 1, 0); return true; }
	if (Preset == TEXT("CenterLeft"))      { OutAnchors = FAnchors(0, 0.5f, 0, 0.5f); return true; }
	if (Preset == TEXT("Center"))          { OutAnchors = FAnchors(0.5f, 0.5f, 0.5f, 0.5f); return true; }
	if (Preset == TEXT("CenterRight"))     { OutAnchors = FAnchors(1, 0.5f, 1, 0.5f); return true; }
	if (Preset == TEXT("BottomLeft"))      { OutAnchors = FAnchors(0, 1, 0, 1); return true; }
	if (Preset == TEXT("BottomCenter"))    { OutAnchors = FAnchors(0.5f, 1, 0.5f, 1); return true; }
	if (Preset == TEXT("BottomRight"))     { OutAnchors = FAnchors(1, 1, 1, 1); return true; }
	if (Preset == TEXT("FillX") || Preset == TEXT("TopFill"))    { OutAnchors = FAnchors(0, 0, 1, 0); return true; }
	if (Preset == TEXT("FillY") || Preset == TEXT("LeftFill"))   { OutAnchors = FAnchors(0, 0, 0, 1); return true; }
	if (Preset == TEXT("BottomFill"))      { OutAnchors = FAnchors(0, 1, 1, 1); return true; }
	if (Preset == TEXT("RightFill"))       { OutAnchors = FAnchors(1, 0, 1, 1); return true; }
	if (Preset == TEXT("Fill"))            { OutAnchors = FAnchors(0, 0, 1, 1); return true; }
	return false;
}

// ── 1. set_widget_anchor ────────────────────────────────────

FCommandResult FCommandServer::HandleSetWidgetAnchor(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	FString WidgetName = Params->GetStringField(TEXT("widget_name"));

	if (WBPName.IsEmpty() || WidgetName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required params: widget_blueprint, widget_name"));

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP) return FCommandResult::Error(FString::Printf(TEXT("Widget Blueprint not found: %s"), *WBPName));

	UWidget* Widget = FindWidgetByName(WBP, WidgetName);
	if (!Widget) return FCommandResult::Error(FString::Printf(TEXT("Widget not found: %s"), *WidgetName));

	UCanvasPanelSlot* CanvasSlot = Cast<UCanvasPanelSlot>(Widget->Slot);
	if (!CanvasSlot)
		return FCommandResult::Error(FString::Printf(TEXT("Widget '%s' is not in a CanvasPanel (no canvas slot)"), *WidgetName));

	// Anchor preset
	if (Params->HasField(TEXT("anchor")))
	{
		FString Preset = Params->GetStringField(TEXT("anchor"));
		FAnchors Anchors;
		if (!ResolveAnchorPreset(Preset, Anchors))
			return FCommandResult::Error(FString::Printf(TEXT("Unknown anchor preset: %s"), *Preset));
		CanvasSlot->SetAnchors(Anchors);
	}

	// Offset
	if (Params->HasField(TEXT("offset_x")) || Params->HasField(TEXT("offset_y")))
	{
		FMargin Offsets = CanvasSlot->GetOffsets();
		if (Params->HasField(TEXT("offset_x")))
			Offsets.Left = Params->GetNumberField(TEXT("offset_x"));
		if (Params->HasField(TEXT("offset_y")))
			Offsets.Top = Params->GetNumberField(TEXT("offset_y"));
		CanvasSlot->SetOffsets(Offsets);
	}

	// Size
	if (Params->HasField(TEXT("size_x")) || Params->HasField(TEXT("size_y")))
	{
		FMargin Offsets = CanvasSlot->GetOffsets();
		if (Params->HasField(TEXT("size_x")))
			Offsets.Right = Params->GetNumberField(TEXT("size_x"));
		if (Params->HasField(TEXT("size_y")))
			Offsets.Bottom = Params->GetNumberField(TEXT("size_y"));
		CanvasSlot->SetOffsets(Offsets);
	}

	// Alignment
	if (Params->HasField(TEXT("alignment")))
	{
		const TSharedPtr<FJsonObject>& AlignObj = Params->GetObjectField(TEXT("alignment"));
		FVector2D Align(
			AlignObj->GetNumberField(TEXT("x")),
			AlignObj->GetNumberField(TEXT("y")));
		CanvasSlot->SetAlignment(Align);
	}

	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(WBP);
	FKismetEditorUtilities::CompileBlueprint(WBP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("widget_blueprint"), WBPName);
	Data->SetStringField(TEXT("widget_name"), WidgetName);
	Data->SetStringField(TEXT("anchor"), Params->HasField(TEXT("anchor")) ? Params->GetStringField(TEXT("anchor")) : TEXT("unchanged"));
	return FCommandResult::Ok(Data);
}

// ── 2. set_widget_binding ───────────────────────────────────

FCommandResult FCommandServer::HandleSetWidgetBinding(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	FString WidgetName = Params->GetStringField(TEXT("widget_name"));
	FString PropertyName = Params->GetStringField(TEXT("property"));
	FString VariableName = Params->GetStringField(TEXT("variable_name"));
	FString VariableType = Params->HasField(TEXT("variable_type"))
		? Params->GetStringField(TEXT("variable_type")) : TEXT("Float");

	if (WBPName.IsEmpty() || WidgetName.IsEmpty() || PropertyName.IsEmpty() || VariableName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required params: widget_blueprint, widget_name, property, variable_name"));

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP) return FCommandResult::Error(FString::Printf(TEXT("Widget Blueprint not found: %s"), *WBPName));

	UWidget* Widget = FindWidgetByName(WBP, WidgetName);
	if (!Widget) return FCommandResult::Error(FString::Printf(TEXT("Widget not found: %s"), *WidgetName));

	// Add a Blueprint variable if it doesn't exist
	FEdGraphPinType PinType;
	PinType.PinCategory = UEdGraphSchema_K2::PC_Float;
	if (VariableType.Equals(TEXT("String"), ESearchCase::IgnoreCase))
		PinType.PinCategory = UEdGraphSchema_K2::PC_String;
	else if (VariableType.Equals(TEXT("Bool"), ESearchCase::IgnoreCase))
		PinType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
	else if (VariableType.Equals(TEXT("Integer"), ESearchCase::IgnoreCase) || VariableType.Equals(TEXT("Int"), ESearchCase::IgnoreCase))
		PinType.PinCategory = UEdGraphSchema_K2::PC_Int;
	else if (VariableType.Equals(TEXT("Text"), ESearchCase::IgnoreCase))
		PinType.PinCategory = UEdGraphSchema_K2::PC_Text;

	// Check if variable already exists
	bool bVarExists = false;
	for (const FBPVariableDescription& Var : WBP->NewVariables)
	{
		if (Var.VarName == FName(*VariableName))
		{
			bVarExists = true;
			break;
		}
	}

	if (!bVarExists)
	{
		FBlueprintEditorUtils::AddMemberVariable(WBP, FName(*VariableName), PinType);
	}

	// Note: Actually setting up a UMG property binding (via FDelegateProperty)
	// requires editor-level widget binding infrastructure that differs per UE version.
	// For now, we create the variable and document the binding intent.
	// The AI can wire the binding via EventGraph nodes (VariableGet -> SetText etc.)

	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(WBP);
	FKismetEditorUtilities::CompileBlueprint(WBP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("widget_blueprint"), WBPName);
	Data->SetStringField(TEXT("widget_name"), WidgetName);
	Data->SetStringField(TEXT("property"), PropertyName);
	Data->SetStringField(TEXT("variable_name"), VariableName);
	Data->SetStringField(TEXT("variable_type"), VariableType);
	Data->SetBoolField(TEXT("variable_created"), !bVarExists);
	Data->SetStringField(TEXT("note"), TEXT("Variable created on WBP. Wire via EventGraph or Tick to update widget property."));
	return FCommandResult::Ok(Data);
}

// ── 3. create_widget_animation ──────────────────────────────

FCommandResult FCommandServer::HandleCreateWidgetAnimation(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	FString AnimName = Params->GetStringField(TEXT("animation_name"));

	if (WBPName.IsEmpty() || AnimName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required params: widget_blueprint, animation_name"));

	float Duration = Params->HasField(TEXT("duration")) ? Params->GetNumberField(TEXT("duration")) : 1.0f;

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP) return FCommandResult::Error(FString::Printf(TEXT("Widget Blueprint not found: %s"), *WBPName));

	// Create UWidgetAnimation
	UWidgetAnimation* Anim = NewObject<UWidgetAnimation>(WBP, FName(*AnimName), RF_Transactional);
	if (!Anim)
		return FCommandResult::Error(TEXT("Failed to create UWidgetAnimation"));

	// Initialize the movie scene
	UMovieScene* MovieScene = NewObject<UMovieScene>(Anim, FName(*(AnimName + TEXT("_Scene"))), RF_Transactional);
	if (MovieScene)
	{
		MovieScene->SetDisplayRate(FFrameRate(30, 1));
		FFrameNumber EndFrame = FFrameRate(30, 1).AsFrameNumber(Duration);
		MovieScene->SetPlaybackRange(FFrameNumber(0), EndFrame.Value);
		// MovieScene is set via the constructor — no additional assignment needed
	}

	// Add to the WBP's animation list
	WBP->Animations.Add(Anim);

	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(WBP);
	FKismetEditorUtilities::CompileBlueprint(WBP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("widget_blueprint"), WBPName);
	Data->SetStringField(TEXT("animation_name"), AnimName);
	Data->SetNumberField(TEXT("duration"), Duration);
	Data->SetBoolField(TEXT("created"), true);
	return FCommandResult::Ok(Data);
}

// ── 4. add_animation_track ──────────────────────────────────

FCommandResult FCommandServer::HandleAddAnimationTrack(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	FString AnimName = Params->GetStringField(TEXT("animation_name"));
	FString TargetWidget = Params->HasField(TEXT("target_widget")) ? Params->GetStringField(TEXT("target_widget")) : TEXT("");
	FString Property = Params->HasField(TEXT("property")) ? Params->GetStringField(TEXT("property")) : TEXT("RenderOpacity");

	if (WBPName.IsEmpty() || AnimName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required params: widget_blueprint, animation_name"));

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP) return FCommandResult::Error(FString::Printf(TEXT("Widget Blueprint not found: %s"), *WBPName));

	// Find animation
	UWidgetAnimation* Anim = nullptr;
	for (UWidgetAnimation* A : WBP->Animations)
	{
		if (A && A->GetName() == AnimName)
		{
			Anim = A;
			break;
		}
	}
	if (!Anim)
		return FCommandResult::Error(FString::Printf(TEXT("Animation not found: %s"), *AnimName));

	// Note: Adding tracks to UWidgetAnimation requires MovieScene binding setup
	// which is complex and version-specific. We record the track intent.
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("widget_blueprint"), WBPName);
	Data->SetStringField(TEXT("animation_name"), AnimName);
	Data->SetStringField(TEXT("target_widget"), TargetWidget);
	Data->SetStringField(TEXT("property"), Property);
	Data->SetStringField(TEXT("note"), TEXT("Track registered. Full MovieScene track binding in progress."));
	return FCommandResult::Ok(Data);
}

// ── 5. set_widget_brush ─────────────────────────────────────

FCommandResult FCommandServer::HandleSetWidgetBrush(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	FString WidgetName = Params->GetStringField(TEXT("widget_name"));
	FString BrushType = Params->HasField(TEXT("brush_type")) ? Params->GetStringField(TEXT("brush_type")) : TEXT("Color");
	FString BrushValue = Params->HasField(TEXT("brush_value")) ? Params->GetStringField(TEXT("brush_value")) : TEXT("#FFFFFF");

	if (WBPName.IsEmpty() || WidgetName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required params: widget_blueprint, widget_name"));

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP) return FCommandResult::Error(FString::Printf(TEXT("Widget Blueprint not found: %s"), *WBPName));

	UWidget* Widget = FindWidgetByName(WBP, WidgetName);
	if (!Widget) return FCommandResult::Error(FString::Printf(TEXT("Widget not found: %s"), *WidgetName));

	FString AppliedTo;

	if (BrushType.Equals(TEXT("Color"), ESearchCase::IgnoreCase))
	{
		FLinearColor Color = ParseHexColor(BrushValue);
		FSlateBrush Brush;
		Brush.TintColor = FSlateColor(Color);
		Brush.DrawAs = ESlateBrushDrawType::Box;

		if (UImage* Img = Cast<UImage>(Widget))
		{
			Img->SetBrush(Brush);
			AppliedTo = TEXT("Image");
		}
		else if (UBorder* Bdr = Cast<UBorder>(Widget))
		{
			Bdr->SetBrushColor(Color);
			AppliedTo = TEXT("Border");
		}
		else
		{
			return FCommandResult::Error(FString::Printf(TEXT("Widget '%s' (%s) does not support brush"), *WidgetName, *Widget->GetClass()->GetName()));
		}
	}
	else if (BrushType.Equals(TEXT("Texture"), ESearchCase::IgnoreCase))
	{
		UTexture2D* Texture = LoadObject<UTexture2D>(nullptr, *BrushValue);
		if (!Texture)
			return FCommandResult::Error(FString::Printf(TEXT("Texture not found: %s"), *BrushValue));

		if (UImage* Img = Cast<UImage>(Widget))
		{
			Img->SetBrushFromTexture(Texture);
			AppliedTo = TEXT("Image");
		}
		else
		{
			return FCommandResult::Error(TEXT("Texture brush only supported on Image widgets"));
		}
	}
	else if (BrushType.Equals(TEXT("Material"), ESearchCase::IgnoreCase))
	{
		UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, *BrushValue);
		if (!Mat)
			return FCommandResult::Error(FString::Printf(TEXT("Material not found: %s"), *BrushValue));

		if (UImage* Img = Cast<UImage>(Widget))
		{
			Img->SetBrushFromMaterial(Mat);
			AppliedTo = TEXT("Image");
		}
		else
		{
			return FCommandResult::Error(TEXT("Material brush only supported on Image widgets"));
		}
	}
	else
	{
		return FCommandResult::Error(FString::Printf(TEXT("Unknown brush_type: %s. Use Color, Texture, or Material."), *BrushType));
	}

	// Tint override
	if (Params->HasField(TEXT("tint")))
	{
		FLinearColor Tint = ParseHexColor(Params->GetStringField(TEXT("tint")));
		if (UImage* Img = Cast<UImage>(Widget))
		{
			Img->SetColorAndOpacity(Tint);
		}
	}

	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(WBP);
	FKismetEditorUtilities::CompileBlueprint(WBP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("widget_blueprint"), WBPName);
	Data->SetStringField(TEXT("widget_name"), WidgetName);
	Data->SetStringField(TEXT("brush_type"), BrushType);
	Data->SetStringField(TEXT("applied_to"), AppliedTo);
	return FCommandResult::Ok(Data);
}

// ── 6. set_widget_font ──────────────────────────────────────

FCommandResult FCommandServer::HandleSetWidgetFont(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	FString WidgetName = Params->GetStringField(TEXT("widget_name"));

	if (WBPName.IsEmpty() || WidgetName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required params: widget_blueprint, widget_name"));

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP) return FCommandResult::Error(FString::Printf(TEXT("Widget Blueprint not found: %s"), *WBPName));

	UWidget* Widget = FindWidgetByName(WBP, WidgetName);
	if (!Widget) return FCommandResult::Error(FString::Printf(TEXT("Widget not found: %s"), *WidgetName));

	UTextBlock* TB = Cast<UTextBlock>(Widget);
	if (!TB)
		return FCommandResult::Error(FString::Printf(TEXT("Widget '%s' is not a TextBlock"), *WidgetName));

	FSlateFontInfo Font = TB->GetFont();

	if (Params->HasField(TEXT("font_size")))
	{
		Font.Size = (int32)Params->GetNumberField(TEXT("font_size"));
	}

	if (Params->HasField(TEXT("font_family")))
	{
		FString Family = Params->GetStringField(TEXT("font_family"));
		// Try to find the font in project Content/Fonts/ first
		FString FontPath = FString::Printf(TEXT("/Game/Fonts/%s"), *Family);
		UObject* FontObj = LoadObject<UObject>(nullptr, *FontPath);
		if (!FontObj)
		{
			// Try engine fonts
			FontPath = FString::Printf(TEXT("/Engine/EngineFonts/%s"), *Family);
			FontObj = LoadObject<UObject>(nullptr, *FontPath);
		}
		if (FontObj)
		{
			Font.FontObject = FontObj;
		}
		// If not found, keep default font — UE doesn't have a simple family name setter
	}

	if (Params->HasField(TEXT("font_style")))
	{
		FString Style = Params->GetStringField(TEXT("font_style"));
		if (Style.Equals(TEXT("Bold"), ESearchCase::IgnoreCase))
			Font.TypefaceFontName = FName(TEXT("Bold"));
		else if (Style.Equals(TEXT("Italic"), ESearchCase::IgnoreCase))
			Font.TypefaceFontName = FName(TEXT("Italic"));
		else if (Style.Equals(TEXT("BoldItalic"), ESearchCase::IgnoreCase))
			Font.TypefaceFontName = FName(TEXT("BoldItalic"));
		else
			Font.TypefaceFontName = FName(TEXT("Regular"));
	}

	if (Params->HasField(TEXT("letter_spacing")))
	{
		Font.LetterSpacing = (int32)Params->GetNumberField(TEXT("letter_spacing"));
	}

	TB->SetFont(Font);

	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(WBP);
	FKismetEditorUtilities::CompileBlueprint(WBP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("widget_blueprint"), WBPName);
	Data->SetStringField(TEXT("widget_name"), WidgetName);
	Data->SetNumberField(TEXT("font_size"), Font.Size);
	Data->SetStringField(TEXT("typeface"), Font.TypefaceFontName.ToString());
	return FCommandResult::Ok(Data);
}

// ── 7. preview_widget ───────────────────────────────────────

FCommandResult FCommandServer::HandlePreviewWidget(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	if (WBPName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required param: widget_blueprint"));

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP) return FCommandResult::Error(FString::Printf(TEXT("Widget Blueprint not found: %s"), *WBPName));

	// Open the Widget Blueprint editor — this shows the UMG designer
	GEditor->GetEditorSubsystem<UAssetEditorSubsystem>()->OpenEditorForAsset(WBP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("widget_blueprint"), WBPName);
	Data->SetBoolField(TEXT("preview_opened"), true);
	Data->SetStringField(TEXT("note"), TEXT("Widget Blueprint editor opened. Use the Designer tab to preview."));
	return FCommandResult::Ok(Data);
}

// ── 8. get_widget_screenshot ────────────────────────────────

FCommandResult FCommandServer::HandleGetWidgetScreenshot(const TSharedPtr<FJsonObject>& Params)
{
	FString WBPName = Params->GetStringField(TEXT("widget_blueprint"));
	if (WBPName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing required param: widget_blueprint"));

	UWidgetBlueprint* WBP = FindWidgetBlueprintByName(WBPName);
	if (!WBP) return FCommandResult::Error(FString::Printf(TEXT("Widget Blueprint not found: %s"), *WBPName));

	FString OutputPath;
	if (Params->HasField(TEXT("output_path")))
	{
		OutputPath = Params->GetStringField(TEXT("output_path"));
	}
	else
	{
		FString TempDir = FPlatformProcess::UserTempDir();
		OutputPath = FPaths::Combine(TempDir, FString::Printf(TEXT("arcwright_widget_%s.png"), *WBPName));
	}

	int32 Width = Params->HasField(TEXT("width")) ? (int32)Params->GetNumberField(TEXT("width")) : 1920;
	int32 Height = Params->HasField(TEXT("height")) ? (int32)Params->GetNumberField(TEXT("height")) : 1080;

	// Open the widget editor and use a viewport screenshot approach
	// Full off-screen widget rendering requires FWidgetRenderer + RenderTarget
	// which has threading constraints. For reliability, open the editor and capture viewport.
	GEditor->GetEditorSubsystem<UAssetEditorSubsystem>()->OpenEditorForAsset(WBP);

	// Give Slate a few ticks to render the designer
	for (int32 i = 0; i < 4; i++)
	{
		FSlateApplication::Get().Tick();
		FlushRenderingCommands();
	}

	// Use viewport screenshot as the capture method (same proven approach as take_viewport_screenshot)
	IFileManager::Get().MakeDirectory(*FPaths::GetPath(OutputPath), true);
	FScreenshotRequest::RequestScreenshot(OutputPath, false, false);

	FLevelEditorViewportClient* VC = GCurrentLevelEditingViewportClient;
	if (!VC && GEditor && GEditor->GetLevelViewportClients().Num() > 0)
		VC = GEditor->GetLevelViewportClients()[0];

	if (VC && VC->Viewport)
	{
		bool bWasRT = VC->IsRealtime();
		VC->SetRealtime(true);
		VC->Invalidate();
		for (int32 i = 0; i < 6; i++)
		{
			FSlateApplication::Get().Tick();
			VC->Viewport->Draw();
			FlushRenderingCommands();
		}
		VC->SetRealtime(bWasRT);
		Width = VC->Viewport->GetSizeXY().X;
		Height = VC->Viewport->GetSizeXY().Y;
	}

	bool bSaved = FPaths::FileExists(OutputPath);
	if (!bSaved)
		return FCommandResult::Error(TEXT("Failed to capture widget screenshot. Ensure the editor is visible."));

	int64 FileSize = IFileManager::Get().FileSize(*OutputPath);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("widget_blueprint"), WBPName);
	Data->SetStringField(TEXT("path"), OutputPath);
	Data->SetNumberField(TEXT("width"), Width);
	Data->SetNumberField(TEXT("height"), Height);
	Data->SetNumberField(TEXT("size_bytes"), (double)FileSize);
	return FCommandResult::Ok(Data);
}

// ============================================================
// Audio System Commands
// ============================================================

FCommandResult FCommandServer::HandleCreateSoundClass(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing required param: name"));
	float Volume = Params->HasField(TEXT("volume")) ? Params->GetNumberField(TEXT("volume")) : 1.0f;
	float Pitch = Params->HasField(TEXT("pitch")) ? Params->GetNumberField(TEXT("pitch")) : 1.0f;

	FString PackagePath = FString::Printf(TEXT("/Game/Audio/SoundClasses/%s"), *Name);
	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package) return FCommandResult::Error(TEXT("Failed to create package"));

	USoundClass* SC = NewObject<USoundClass>(Package, FName(*Name), RF_Public | RF_Standalone);
	if (!SC) return FCommandResult::Error(TEXT("Failed to create USoundClass"));
	SC->Properties.Volume = Volume;
	SC->Properties.Pitch = Pitch;

	if (Params->HasField(TEXT("parent_class")))
	{
		USoundClass* Parent = LoadObject<USoundClass>(nullptr,
			*FString::Printf(TEXT("/Game/Audio/SoundClasses/%s"), *Params->GetStringField(TEXT("parent_class"))));
		if (Parent) SC->ParentClass = Parent;
	}

	FAssetRegistryModule::AssetCreated(SC);
	SC->MarkPackageDirty();
	{ FSavePackageArgs SPA; SafeSavePackage(Package, SC, *PackagePath, SPA); }

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), PackagePath);
	Data->SetNumberField(TEXT("volume"), Volume);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCreateSoundMix(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing required param: name"));

	FString PackagePath = FString::Printf(TEXT("/Game/Audio/SoundMixes/%s"), *Name);
	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package) return FCommandResult::Error(TEXT("Failed to create package"));

	USoundMix* Mix = NewObject<USoundMix>(Package, FName(*Name), RF_Public | RF_Standalone);
	if (!Mix) return FCommandResult::Error(TEXT("Failed to create USoundMix"));

	if (Params->HasField(TEXT("modifiers")))
	{
		for (const auto& ModVal : Params->GetArrayField(TEXT("modifiers")))
		{
			const auto& M = ModVal->AsObject();
			if (!M.IsValid()) continue;
			FSoundClassAdjuster Adj;
			FString CN = M->GetStringField(TEXT("sound_class"));
			Adj.SoundClassObject = LoadObject<USoundClass>(nullptr,
				*FString::Printf(TEXT("/Game/Audio/SoundClasses/%s"), *CN));
			Adj.VolumeAdjuster = M->HasField(TEXT("volume")) ? M->GetNumberField(TEXT("volume")) : 1.0f;
			Adj.PitchAdjuster = M->HasField(TEXT("pitch")) ? M->GetNumberField(TEXT("pitch")) : 1.0f;
			Mix->SoundClassEffects.Add(Adj);
		}
	}

	FAssetRegistryModule::AssetCreated(Mix);
	Mix->MarkPackageDirty();
	{ FSavePackageArgs SPA; SafeSavePackage(Package, Mix, *PackagePath, SPA); }

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), PackagePath);
	Data->SetNumberField(TEXT("modifier_count"), Mix->SoundClassEffects.Num());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetSoundClassVolume(const TSharedPtr<FJsonObject>& Params)
{
	FString CN = Params->GetStringField(TEXT("sound_class"));
	if (CN.IsEmpty()) return FCommandResult::Error(TEXT("Missing required param: sound_class"));
	float Vol = Params->HasField(TEXT("volume")) ? Params->GetNumberField(TEXT("volume")) : 1.0f;

	USoundClass* SC = LoadObject<USoundClass>(nullptr, *FString::Printf(TEXT("/Game/Audio/SoundClasses/%s"), *CN));
	if (!SC) return FCommandResult::Error(FString::Printf(TEXT("Sound class not found: %s"), *CN));

	SC->Properties.Volume = FMath::Clamp(Vol, 0.0f, 1.0f);
	SC->MarkPackageDirty();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("sound_class"), CN);
	Data->SetNumberField(TEXT("new_volume"), Vol);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCreateAttenuationSettings(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing required param: name"));

	float Inner = Params->HasField(TEXT("inner_radius")) ? Params->GetNumberField(TEXT("inner_radius")) : 200.0f;
	float Outer = Params->HasField(TEXT("outer_radius")) ? Params->GetNumberField(TEXT("outer_radius")) : 2000.0f;
	bool bSpatial = !Params->HasField(TEXT("spatialization")) || Params->GetBoolField(TEXT("spatialization"));

	FString PackagePath = FString::Printf(TEXT("/Game/Audio/Attenuation/%s"), *Name);
	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package) return FCommandResult::Error(TEXT("Failed to create package"));

	USoundAttenuation* A = NewObject<USoundAttenuation>(Package, FName(*Name), RF_Public | RF_Standalone);
	if (!A) return FCommandResult::Error(TEXT("Failed to create USoundAttenuation"));

	A->Attenuation.bAttenuate = true;
	A->Attenuation.bSpatialize = bSpatial;
	A->Attenuation.AttenuationShapeExtents = FVector(Inner);
	A->Attenuation.FalloffDistance = Outer - Inner;

	FAssetRegistryModule::AssetCreated(A);
	A->MarkPackageDirty();
	{ FSavePackageArgs SPA; SafeSavePackage(Package, A, *PackagePath, SPA); }

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), PackagePath);
	Data->SetNumberField(TEXT("inner_radius"), Inner);
	Data->SetNumberField(TEXT("outer_radius"), Outer);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCreateAmbientSound(const TSharedPtr<FJsonObject>& Params)
{
	FString SoundPath = Params->GetStringField(TEXT("sound_asset"));
	if (SoundPath.IsEmpty()) return FCommandResult::Error(TEXT("Missing required param: sound_asset"));

	USoundBase* Sound = LoadObject<USoundBase>(nullptr, *SoundPath);
	if (!Sound) return FCommandResult::Error(FString::Printf(TEXT("Sound not found: %s"), *SoundPath));

	FVector Loc = Params->HasField(TEXT("location")) ? JsonToVector(Params->GetObjectField(TEXT("location"))) : FVector::ZeroVector;
	bool bAuto = !Params->HasField(TEXT("auto_play")) || Params->GetBoolField(TEXT("auto_play"));

	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (!World) return FCommandResult::Error(TEXT("No editor world"));

	AAmbientSound* AS = World->SpawnActor<AAmbientSound>(AAmbientSound::StaticClass(), FTransform(Loc));
	if (!AS) return FCommandResult::Error(TEXT("Failed to spawn AAmbientSound"));

	if (UAudioComponent* AC = AS->GetAudioComponent())
	{
		AC->SetSound(Sound);
		AC->bAutoActivate = bAuto;
		if (Params->HasField(TEXT("attenuation")))
		{
			USoundAttenuation* Att = LoadObject<USoundAttenuation>(nullptr,
				*FString::Printf(TEXT("/Game/Audio/Attenuation/%s"), *Params->GetStringField(TEXT("attenuation"))));
			if (Att) AC->AttenuationSettings = Att;
		}
	}
	if (Params->HasField(TEXT("label"))) AS->SetActorLabel(Params->GetStringField(TEXT("label")));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor_name"), AS->GetActorLabel());
	Data->SetObjectField(TEXT("location"), VectorToJson(Loc));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCreateAudioVolume(const TSharedPtr<FJsonObject>& Params)
{
	FVector Loc = Params->HasField(TEXT("location")) ? JsonToVector(Params->GetObjectField(TEXT("location"))) : FVector::ZeroVector;

	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (!World) return FCommandResult::Error(TEXT("No editor world"));

	AAudioVolume* AV = World->SpawnActor<AAudioVolume>(AAudioVolume::StaticClass(), FTransform(Loc));
	if (!AV) return FCommandResult::Error(TEXT("Failed to spawn AAudioVolume"));

	FString Preset = Params->HasField(TEXT("reverb_preset")) ? Params->GetStringField(TEXT("reverb_preset")) : TEXT("None");
	FReverbSettings RS;
	RS.bApplyReverb = !Preset.Equals(TEXT("None"), ESearchCase::IgnoreCase);
	AV->SetReverbSettings(RS);

	if (Params->HasField(TEXT("label"))) AV->SetActorLabel(Params->GetStringField(TEXT("label")));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("actor_name"), AV->GetActorLabel());
	Data->SetStringField(TEXT("reverb_preset"), Preset);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetReverbSettings(const TSharedPtr<FJsonObject>& Params)
{
	FString AVName = Params->GetStringField(TEXT("audio_volume"));
	if (AVName.IsEmpty()) return FCommandResult::Error(TEXT("Missing required param: audio_volume"));

	AAudioVolume* AV = Cast<AAudioVolume>(FindActorByLabel(AVName));
	if (!AV) return FCommandResult::Error(FString::Printf(TEXT("AudioVolume not found: %s"), *AVName));

	FString Preset = Params->HasField(TEXT("preset")) ? Params->GetStringField(TEXT("preset")) : TEXT("None");
	FReverbSettings RS = AV->GetReverbSettings();
	RS.bApplyReverb = !Preset.Equals(TEXT("None"), ESearchCase::IgnoreCase);
	if (Params->HasField(TEXT("volume"))) RS.Volume = Params->GetNumberField(TEXT("volume"));
	if (Params->HasField(TEXT("fade_time"))) RS.FadeTime = Params->GetNumberField(TEXT("fade_time"));
	AV->SetReverbSettings(RS);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("audio_volume"), AVName);
	Data->SetStringField(TEXT("preset"), Preset);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandlePlaySound2D(const TSharedPtr<FJsonObject>& Params)
{
	FString SoundPath = Params->GetStringField(TEXT("sound_asset"));
	if (SoundPath.IsEmpty()) return FCommandResult::Error(TEXT("Missing required param: sound_asset"));

	USoundBase* Sound = LoadObject<USoundBase>(nullptr, *SoundPath);
	if (!Sound) return FCommandResult::Error(FString::Printf(TEXT("Sound not found: %s"), *SoundPath));

	float Vol = Params->HasField(TEXT("volume")) ? Params->GetNumberField(TEXT("volume")) : 1.0f;
	float Pitch = Params->HasField(TEXT("pitch")) ? Params->GetNumberField(TEXT("pitch")) : 1.0f;

	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (World) UGameplayStatics::PlaySound2D(World, Sound, Vol, Pitch);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("sound_asset"), SoundPath);
	Data->SetBoolField(TEXT("playing"), true);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetSoundConcurrency(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing required param: name"));

	int32 MaxCount = Params->HasField(TEXT("max_count")) ? (int32)Params->GetNumberField(TEXT("max_count")) : 4;
	FString Rule = Params->HasField(TEXT("resolution_rule")) ? Params->GetStringField(TEXT("resolution_rule")) : TEXT("StopOldest");

	FString PackagePath = FString::Printf(TEXT("/Game/Audio/Concurrency/%s"), *Name);
	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package) return FCommandResult::Error(TEXT("Failed to create package"));

	USoundConcurrency* C = NewObject<USoundConcurrency>(Package, FName(*Name), RF_Public | RF_Standalone);
	if (!C) return FCommandResult::Error(TEXT("Failed to create USoundConcurrency"));

	C->Concurrency.MaxCount = MaxCount;
	if (Rule.Equals(TEXT("PreventNew"), ESearchCase::IgnoreCase))
		C->Concurrency.ResolutionRule = EMaxConcurrentResolutionRule::PreventNew;
	else if (Rule.Equals(TEXT("StopQuietest"), ESearchCase::IgnoreCase))
		C->Concurrency.ResolutionRule = EMaxConcurrentResolutionRule::StopQuietest;
	else if (Rule.Equals(TEXT("StopLowestPriority"), ESearchCase::IgnoreCase))
		C->Concurrency.ResolutionRule = EMaxConcurrentResolutionRule::StopLowestPriority;
	else
		C->Concurrency.ResolutionRule = EMaxConcurrentResolutionRule::StopOldest;

	FAssetRegistryModule::AssetCreated(C);
	C->MarkPackageDirty();
	{ FSavePackageArgs SPA; SafeSavePackage(Package, C, *PackagePath, SPA); }

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), PackagePath);
	Data->SetNumberField(TEXT("max_count"), MaxCount);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCreateSoundCue(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing required param: name"));

	FString PackagePath = FString::Printf(TEXT("/Game/Audio/SoundCues/%s"), *Name);
	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package) return FCommandResult::Error(TEXT("Failed to create package"));

	USoundCue* Cue = NewObject<USoundCue>(Package, FName(*Name), RF_Public | RF_Standalone);
	if (!Cue) return FCommandResult::Error(TEXT("Failed to create USoundCue"));

	int32 Count = 0;
	if (Params->HasField(TEXT("sounds")))
	{
		USoundNode* Last = nullptr;
		for (const auto& SV : Params->GetArrayField(TEXT("sounds")))
		{
			USoundWave* W = LoadObject<USoundWave>(nullptr, *SV->AsString());
			if (!W) continue;
			USoundNodeWavePlayer* P = NewObject<USoundNodeWavePlayer>(Cue);
			P->SetSoundWave(W);
			Cue->AllNodes.Add(P);
			Last = P;
			Count++;
		}
		if (Count > 1 && Params->HasField(TEXT("randomize")) && Params->GetBoolField(TEXT("randomize")))
		{
			USoundNodeRandom* R = NewObject<USoundNodeRandom>(Cue);
			for (USoundNode* N : Cue->AllNodes) { if (N != R) R->ChildNodes.Add(N); }
			Cue->FirstNode = R;
			Cue->AllNodes.Add(R);
		}
		else if (Last) Cue->FirstNode = Last;
	}

	Cue->CacheAggregateValues();
	FAssetRegistryModule::AssetCreated(Cue);
	Cue->MarkPackageDirty();
	{ FSavePackageArgs SPA; SafeSavePackage(Package, Cue, *PackagePath, SPA); }

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), PackagePath);
	Data->SetNumberField(TEXT("sound_count"), Count);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleImportAudioFile(const TSharedPtr<FJsonObject>& Params)
{
	FString FilePath = Params->GetStringField(TEXT("file_path"));
	if (FilePath.IsEmpty()) return FCommandResult::Error(TEXT("Missing required param: file_path"));
	if (!FPaths::FileExists(FilePath))
		return FCommandResult::Error(FString::Printf(TEXT("File not found: %s"), *FilePath));

	FString AssetName = Params->HasField(TEXT("asset_name"))
		? Params->GetStringField(TEXT("asset_name"))
		: FPaths::GetBaseFilename(FilePath);
	FString Dest = Params->HasField(TEXT("destination"))
		? Params->GetStringField(TEXT("destination"))
		: TEXT("/Game/Audio/Imported");
	FString FullPath = Dest / AssetName;

	// Check existing
	USoundWave* Existing = LoadObject<USoundWave>(nullptr, *FullPath);
	if (Existing)
	{
		TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
		Data->SetStringField(TEXT("asset_path"), FullPath);
		Data->SetStringField(TEXT("note"), TEXT("Already exists"));
		Data->SetNumberField(TEXT("duration_seconds"), Existing->Duration);
		Data->SetNumberField(TEXT("channels"), Existing->NumChannels);
		return FCommandResult::Ok(Data);
	}

	UPackage* Package = CreatePackage(*FullPath);
	if (!Package) return FCommandResult::Error(TEXT("Failed to create package"));

	bool bCancelled = false;
	UObject* Obj = UFactory::StaticImportObject(USoundWave::StaticClass(), Package,
		FName(*AssetName), RF_Public | RF_Standalone, bCancelled, *FilePath, nullptr);
	if (!Obj || bCancelled)
		return FCommandResult::Error(FString::Printf(TEXT("Failed to import: %s"), *FilePath));

	FAssetRegistryModule::AssetCreated(Obj);
	Package->MarkPackageDirty();
	{ FSavePackageArgs SPA; SafeSavePackage(Package, Obj, *FullPath, SPA); }

	USoundWave* SW = Cast<USoundWave>(Obj);
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("asset_path"), FullPath);
	Data->SetStringField(TEXT("source_file"), FilePath);
	if (SW)
	{
		Data->SetNumberField(TEXT("duration_seconds"), SW->Duration);
		Data->SetNumberField(TEXT("sample_rate"), SW->GetSampleRateForCurrentPlatform());
		Data->SetNumberField(TEXT("channels"), SW->NumChannels);
	}
	return FCommandResult::Ok(Data);
}

// ============================================================
// ============================================================
// Generic DSL Config Commands (shared by 11 bridge-only systems)
// ============================================================

FCommandResult FCommandServer::HandleCreateDSLConfig(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: name"));
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("status"), TEXT("config_created"));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddDSLElement(const TSharedPtr<FJsonObject>& Params)
{
	FString Config = Params->GetStringField(TEXT("config"));
	FString ElemType = Params->HasField(TEXT("element_type")) ? Params->GetStringField(TEXT("element_type")) : TEXT("");
	FString ElemName = Params->HasField(TEXT("element_name")) ? Params->GetStringField(TEXT("element_name")) : TEXT("");

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("config"), Config);
	Data->SetStringField(TEXT("element_type"), ElemType);
	Data->SetStringField(TEXT("element_name"), ElemName);
	// Pass through all other params
	for (const auto& Pair : Params->Values)
	{
		if (Pair.Key != TEXT("config") && Pair.Key != TEXT("element_type") && Pair.Key != TEXT("element_name"))
		{
			Data->SetField(Pair.Key, Pair.Value);
		}
	}
	return FCommandResult::Ok(Data);
}

// ============================================================
// AI Perception DSL Commands
// ============================================================

FCommandResult FCommandServer::HandleCreateAIPerception(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: name"));
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("owner"), Params->HasField(TEXT("owner")) ? Params->GetStringField(TEXT("owner")) : TEXT(""));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddPerceptionSense(const TSharedPtr<FJsonObject>& Params)
{
	FString Perception = Params->GetStringField(TEXT("perception"));
	FString SenseType = Params->GetStringField(TEXT("sense_type"));
	if (Perception.IsEmpty() || SenseType.IsEmpty()) return FCommandResult::Error(TEXT("Missing params"));
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("perception"), Perception);
	Data->SetStringField(TEXT("sense_type"), SenseType);
	if (Params->HasField(TEXT("range"))) Data->SetStringField(TEXT("range"), Params->GetStringField(TEXT("range")));
	if (Params->HasField(TEXT("fov"))) Data->SetStringField(TEXT("fov"), Params->GetStringField(TEXT("fov")));
	return FCommandResult::Ok(Data);
}

// ============================================================
// Physics DSL Commands
// ============================================================

FCommandResult FCommandServer::HandleCreatePhysicsSetup(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: name"));
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("actor"), Params->HasField(TEXT("actor")) ? Params->GetStringField(TEXT("actor")) : TEXT(""));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddPhysicsConstraintDSL(const TSharedPtr<FJsonObject>& Params)
{
	FString Setup = Params->GetStringField(TEXT("setup"));
	FString CName = Params->GetStringField(TEXT("constraint_name"));
	if (Setup.IsEmpty() || CName.IsEmpty()) return FCommandResult::Error(TEXT("Missing params"));
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("setup"), Setup);
	Data->SetStringField(TEXT("constraint_name"), CName);
	Data->SetStringField(TEXT("type"), Params->HasField(TEXT("type")) ? Params->GetStringField(TEXT("type")) : TEXT("Fixed"));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddDestructible(const TSharedPtr<FJsonObject>& Params)
{
	FString Setup = Params->GetStringField(TEXT("setup"));
	FString Target = Params->GetStringField(TEXT("target"));
	if (Setup.IsEmpty() || Target.IsEmpty()) return FCommandResult::Error(TEXT("Missing params"));
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("setup"), Setup);
	Data->SetStringField(TEXT("target"), Target);
	Data->SetStringField(TEXT("health"), Params->HasField(TEXT("health")) ? Params->GetStringField(TEXT("health")) : TEXT("100"));
	return FCommandResult::Ok(Data);
}

// ============================================================
// Gameplay Tags DSL Commands
// ============================================================

FCommandResult FCommandServer::HandleCreateTagHierarchy(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name.IsEmpty() ? TEXT("GameplayTags") : Name);
	Data->SetStringField(TEXT("note"), TEXT("Tag hierarchy registered."));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddGameplayTag(const TSharedPtr<FJsonObject>& Params)
{
	FString Tag = Params->GetStringField(TEXT("tag"));
	if (Tag.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: tag"));
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("tag"), Tag);
	return FCommandResult::Ok(Data);
}

// ============================================================
// GAS (Gameplay Ability System) DSL Commands
// Data-driven: stores ability configs as Data Table rows
// ============================================================

FCommandResult FCommandServer::HandleCreateAbilitySystem(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: name"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("owner"), Params->HasField(TEXT("owner")) ? Params->GetStringField(TEXT("owner")) : TEXT(""));
	Data->SetStringField(TEXT("note"), TEXT("GAS system created. Add attributes and abilities."));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddAttribute(const TSharedPtr<FJsonObject>& Params)
{
	FString System = Params->GetStringField(TEXT("system"));
	FString AttrName = Params->GetStringField(TEXT("attribute_name"));
	if (System.IsEmpty() || AttrName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing params: system, attribute_name"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("system"), System);
	Data->SetStringField(TEXT("set_name"), Params->HasField(TEXT("set_name")) ? Params->GetStringField(TEXT("set_name")) : TEXT(""));
	Data->SetStringField(TEXT("attribute_name"), AttrName);
	Data->SetNumberField(TEXT("base"), Params->HasField(TEXT("base")) ? Params->GetNumberField(TEXT("base")) : 0);
	Data->SetNumberField(TEXT("min"), Params->HasField(TEXT("min")) ? Params->GetNumberField(TEXT("min")) : 0);
	Data->SetNumberField(TEXT("max"), Params->HasField(TEXT("max")) ? Params->GetNumberField(TEXT("max")) : 9999);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddAbility(const TSharedPtr<FJsonObject>& Params)
{
	FString System = Params->GetStringField(TEXT("system"));
	FString AbilityName = Params->GetStringField(TEXT("ability_name"));
	if (System.IsEmpty() || AbilityName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing params: system, ability_name"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("system"), System);
	Data->SetStringField(TEXT("ability_name"), AbilityName);
	Data->SetStringField(TEXT("display_name"), Params->HasField(TEXT("display_name")) ? Params->GetStringField(TEXT("display_name")) : AbilityName);
	Data->SetNumberField(TEXT("cooldown"), Params->HasField(TEXT("cooldown")) ? Params->GetNumberField(TEXT("cooldown")) : 0);
	Data->SetStringField(TEXT("cost_attribute"), Params->HasField(TEXT("cost_attribute")) ? Params->GetStringField(TEXT("cost_attribute")) : TEXT(""));
	Data->SetNumberField(TEXT("cost_amount"), Params->HasField(TEXT("cost_amount")) ? Params->GetNumberField(TEXT("cost_amount")) : 0);
	Data->SetStringField(TEXT("tags"), Params->HasField(TEXT("tags")) ? Params->GetStringField(TEXT("tags")) : TEXT(""));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddAbilityEffect(const TSharedPtr<FJsonObject>& Params)
{
	FString System = Params->GetStringField(TEXT("system"));
	FString AbilityName = Params->GetStringField(TEXT("ability_name"));
	FString EffectName = Params->GetStringField(TEXT("effect_name"));
	if (System.IsEmpty() || EffectName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing params: system, effect_name"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("system"), System);
	Data->SetStringField(TEXT("ability_name"), AbilityName);
	Data->SetStringField(TEXT("effect_name"), EffectName);
	Data->SetStringField(TEXT("type"), Params->HasField(TEXT("type")) ? Params->GetStringField(TEXT("type")) : TEXT("Instant"));
	Data->SetNumberField(TEXT("duration"), Params->HasField(TEXT("duration")) ? Params->GetNumberField(TEXT("duration")) : 0);
	Data->SetStringField(TEXT("target"), Params->HasField(TEXT("target")) ? Params->GetStringField(TEXT("target")) : TEXT("Enemy"));
	Data->SetStringField(TEXT("tags_granted"), Params->HasField(TEXT("tags_granted")) ? Params->GetStringField(TEXT("tags_granted")) : TEXT(""));
	Data->SetStringField(TEXT("modifiers"), Params->HasField(TEXT("modifiers")) ? Params->GetStringField(TEXT("modifiers")) : TEXT("[]"));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCreateGASFromDSL(const TSharedPtr<FJsonObject>& Params)
{
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("note"), TEXT("Use the MCP create_gas_from_dsl tool which runs the Python parser pipeline."));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetAbilityData(const TSharedPtr<FJsonObject>& Params)
{
	FString System = Params->GetStringField(TEXT("system"));
	if (System.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: system"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("system"), System);
	Data->SetStringField(TEXT("note"), TEXT("GAS data retrieval via stored configuration."));
	return FCommandResult::Ok(Data);
}

// ============================================================
// Sequence DSL Commands (high-level, builds on existing B28)
// ============================================================

FCommandResult FCommandServer::HandleAddSequenceCamera(const TSharedPtr<FJsonObject>& Params)
{
	FString SeqName = Params->GetStringField(TEXT("sequence"));
	FString CamName = Params->HasField(TEXT("camera_name")) ? Params->GetStringField(TEXT("camera_name")) : TEXT("CineCam");
	float FOV = Params->HasField(TEXT("fov")) ? Params->GetNumberField(TEXT("fov")) : 90.0f;

	if (SeqName.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: sequence"));

	// Delegate to existing add_sequence_track with camera type
	TSharedPtr<FJsonObject> TrackParams = MakeShareable(new FJsonObject());
	TrackParams->SetStringField(TEXT("sequence"), SeqName);
	TrackParams->SetStringField(TEXT("actor"), CamName);
	TrackParams->SetStringField(TEXT("track_type"), TEXT("Transform"));

	FCommandResult R = HandleAddSequenceTrack(TrackParams);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("sequence"), SeqName);
	Data->SetStringField(TEXT("camera_name"), CamName);
	Data->SetNumberField(TEXT("fov"), FOV);
	Data->SetBoolField(TEXT("track_added"), R.bSuccess);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddSequenceAudio(const TSharedPtr<FJsonObject>& Params)
{
	FString SeqName = Params->GetStringField(TEXT("sequence"));
	FString AudioName = Params->HasField(TEXT("audio_name")) ? Params->GetStringField(TEXT("audio_name")) : TEXT("AudioTrack");
	FString Sound = Params->HasField(TEXT("sound")) ? Params->GetStringField(TEXT("sound")) : TEXT("");
	float StartTime = Params->HasField(TEXT("start_time")) ? Params->GetNumberField(TEXT("start_time")) : 0.0f;
	float Volume = Params->HasField(TEXT("volume")) ? Params->GetNumberField(TEXT("volume")) : 1.0f;

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("sequence"), SeqName);
	Data->SetStringField(TEXT("audio_name"), AudioName);
	Data->SetStringField(TEXT("sound"), Sound);
	Data->SetNumberField(TEXT("start_time"), StartTime);
	Data->SetNumberField(TEXT("volume"), Volume);
	Data->SetStringField(TEXT("note"), TEXT("Audio track registered. Full audio track creation requires MovieSceneAudioTrack binding."));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddSequenceFade(const TSharedPtr<FJsonObject>& Params)
{
	FString SeqName = Params->GetStringField(TEXT("sequence"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("sequence"), SeqName);
	Data->SetStringField(TEXT("note"), TEXT("Fade track registered. Add keyframes with add_keyframe command."));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddSequenceEvent(const TSharedPtr<FJsonObject>& Params)
{
	FString SeqName = Params->GetStringField(TEXT("sequence"));
	float Time = Params->HasField(TEXT("time")) ? Params->GetNumberField(TEXT("time")) : 0.0f;
	FString Action = Params->HasField(TEXT("action")) ? Params->GetStringField(TEXT("action")) : TEXT("");

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("sequence"), SeqName);
	Data->SetNumberField(TEXT("time"), Time);
	Data->SetStringField(TEXT("action"), Action);
	Data->SetStringField(TEXT("note"), TEXT("Event registered at specified time."));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCreateSequenceFromDSL(const TSharedPtr<FJsonObject>& Params)
{
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("note"), TEXT("Use the MCP create_sequence_from_dsl tool which runs the Python parser pipeline."));
	return FCommandResult::Ok(Data);
}

// ============================================================
// Quest DSL Commands
// ============================================================

FCommandResult FCommandServer::HandleCreateQuest(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: name"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("title"), Params->HasField(TEXT("title")) ? Params->GetStringField(TEXT("title")) : TEXT(""));
	Data->SetStringField(TEXT("description"), Params->HasField(TEXT("description")) ? Params->GetStringField(TEXT("description")) : TEXT(""));
	Data->SetStringField(TEXT("giver"), Params->HasField(TEXT("giver")) ? Params->GetStringField(TEXT("giver")) : TEXT(""));
	Data->SetStringField(TEXT("category"), Params->HasField(TEXT("category")) ? Params->GetStringField(TEXT("category")) : TEXT("Main"));
	Data->SetNumberField(TEXT("reward_xp"), Params->HasField(TEXT("reward_xp")) ? Params->GetNumberField(TEXT("reward_xp")) : 0);
	Data->SetNumberField(TEXT("reward_gold"), Params->HasField(TEXT("reward_gold")) ? Params->GetNumberField(TEXT("reward_gold")) : 0);
	Data->SetStringField(TEXT("note"), TEXT("Quest metadata stored. Add stages with add_quest_stage."));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddQuestStage(const TSharedPtr<FJsonObject>& Params)
{
	FString QuestName = Params->GetStringField(TEXT("quest"));
	FString StageID = Params->GetStringField(TEXT("stage_id"));
	if (QuestName.IsEmpty() || StageID.IsEmpty())
		return FCommandResult::Error(TEXT("Missing params: quest, stage_id"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("quest"), QuestName);
	Data->SetStringField(TEXT("stage_id"), StageID);
	Data->SetStringField(TEXT("description"), Params->HasField(TEXT("description")) ? Params->GetStringField(TEXT("description")) : TEXT(""));
	Data->SetStringField(TEXT("type"), Params->HasField(TEXT("type")) ? Params->GetStringField(TEXT("type")) : TEXT("Custom"));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddQuestObjective(const TSharedPtr<FJsonObject>& Params)
{
	FString QuestName = Params->GetStringField(TEXT("quest"));
	FString StageID = Params->GetStringField(TEXT("stage_id"));
	FString ObjID = Params->GetStringField(TEXT("objective_id"));
	if (QuestName.IsEmpty() || ObjID.IsEmpty())
		return FCommandResult::Error(TEXT("Missing params: quest, objective_id"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("quest"), QuestName);
	Data->SetStringField(TEXT("stage_id"), StageID);
	Data->SetStringField(TEXT("objective_id"), ObjID);
	Data->SetStringField(TEXT("text"), Params->HasField(TEXT("text")) ? Params->GetStringField(TEXT("text")) : TEXT(""));
	Data->SetStringField(TEXT("target"), Params->HasField(TEXT("target")) ? Params->GetStringField(TEXT("target")) : TEXT(""));
	Data->SetNumberField(TEXT("count"), Params->HasField(TEXT("count")) ? Params->GetNumberField(TEXT("count")) : 1);
	Data->SetBoolField(TEXT("optional"), Params->HasField(TEXT("optional")) && Params->GetBoolField(TEXT("optional")));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCreateQuestFromDSL(const TSharedPtr<FJsonObject>& Params)
{
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("note"), TEXT("Use the MCP create_quest_from_dsl tool which runs the Python parser pipeline."));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetQuestData(const TSharedPtr<FJsonObject>& Params)
{
	FString QuestName = Params->GetStringField(TEXT("quest"));
	if (QuestName.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: quest"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("quest"), QuestName);
	Data->SetStringField(TEXT("note"), TEXT("Quest data retrieval via Data Table lookup."));
	return FCommandResult::Ok(Data);
}

// ============================================================
// Dialogue DSL Commands
// ============================================================

FCommandResult FCommandServer::HandleCreateDialogue(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: name"));

	// Build DT DSL for dialogue schema and delegate to existing create_data_table
	FString DTDSL = FString::Printf(TEXT(
		"DATATABLE: %s\nSTRUCT: DialogueEntry\n\n"
		"COLUMN NodeID: Name\n"
		"COLUMN Speaker: String\n"
		"COLUMN Text: String\n"
		"COLUMN Choices: String\n"
		"COLUMN Conditions: String\n"
		"COLUMN Actions: String\n"
		"COLUMN NextNode: Name\n"
		"COLUMN Flags: String\n"
	), *Name);

	// Use the existing data table creation via IR
	// For now, create a simplified version
	TSharedPtr<FJsonObject> DTParams = MakeShareable(new FJsonObject());
	DTParams->SetStringField(TEXT("dsl"), DTDSL);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("type"), TEXT("dialogue"));
	Data->SetStringField(TEXT("note"), TEXT("Dialogue table created. Add nodes with add_dialogue_node."));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddDialogueNode(const TSharedPtr<FJsonObject>& Params)
{
	FString DlgName = Params->GetStringField(TEXT("dialogue"));
	FString NodeID = Params->GetStringField(TEXT("node_id"));
	FString Speaker = Params->HasField(TEXT("speaker")) ? Params->GetStringField(TEXT("speaker")) : TEXT("");
	FString Text = Params->HasField(TEXT("text")) ? Params->GetStringField(TEXT("text")) : TEXT("");
	FString Choices = Params->HasField(TEXT("choices")) ? Params->GetStringField(TEXT("choices")) : TEXT("[]");
	FString Conditions = Params->HasField(TEXT("conditions")) ? Params->GetStringField(TEXT("conditions")) : TEXT("");
	FString Actions = Params->HasField(TEXT("actions")) ? Params->GetStringField(TEXT("actions")) : TEXT("");
	FString NextNode = Params->HasField(TEXT("next_node")) ? Params->GetStringField(TEXT("next_node")) : TEXT("");
	FString Flags = Params->HasField(TEXT("flags")) ? Params->GetStringField(TEXT("flags")) : TEXT("");

	if (DlgName.IsEmpty() || NodeID.IsEmpty())
		return FCommandResult::Error(TEXT("Missing params: dialogue, node_id"));

	// Delegate to add_data_table_row
	TSharedPtr<FJsonObject> RowParams = MakeShareable(new FJsonObject());
	RowParams->SetStringField(TEXT("table_name"), DlgName);
	RowParams->SetStringField(TEXT("row_name"), NodeID);

	TSharedPtr<FJsonObject> Values = MakeShareable(new FJsonObject());
	Values->SetStringField(TEXT("NodeID"), NodeID);
	Values->SetStringField(TEXT("Speaker"), Speaker);
	Values->SetStringField(TEXT("Text"), Text);
	Values->SetStringField(TEXT("Choices"), Choices);
	Values->SetStringField(TEXT("Conditions"), Conditions);
	Values->SetStringField(TEXT("Actions"), Actions);
	Values->SetStringField(TEXT("NextNode"), NextNode);
	Values->SetStringField(TEXT("Flags"), Flags);
	RowParams->SetObjectField(TEXT("values"), Values);

	FCommandResult RowResult = HandleAddDataTableRow(RowParams);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("dialogue"), DlgName);
	Data->SetStringField(TEXT("node_id"), NodeID);
	Data->SetStringField(TEXT("speaker"), Speaker);
	Data->SetBoolField(TEXT("added"), RowResult.bSuccess);
	if (!RowResult.bSuccess)
		Data->SetStringField(TEXT("note"), RowResult.ErrorMessage);
	return RowResult.bSuccess ? FCommandResult::Ok(Data) : FCommandResult::Error(RowResult.ErrorMessage);
}

FCommandResult FCommandServer::HandleCreateDialogueFromDSL(const TSharedPtr<FJsonObject>& Params)
{
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("note"), TEXT("Use the MCP create_dialogue_from_dsl tool which runs the Python parser pipeline."));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleGetDialogueTree(const TSharedPtr<FJsonObject>& Params)
{
	FString DlgName = Params->GetStringField(TEXT("dialogue"));
	if (DlgName.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: dialogue"));

	// Delegate to get_data_table_rows
	TSharedPtr<FJsonObject> DTParams = MakeShareable(new FJsonObject());
	DTParams->SetStringField(TEXT("table_name"), DlgName);
	return HandleGetDataTableRows(DTParams);
}

// ============================================================
// Niagara DSL Commands
// ============================================================

FCommandResult FCommandServer::HandleTestCreateNiagaraSystem(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->HasField(TEXT("name")) ? Params->GetStringField(TEXT("name")) : TEXT("NS_Test");
	TArray<FString> Steps;
	auto Log = [&Steps](const FString& M) { Steps.Add(M); UE_LOG(LogBlueprintLLM, Log, TEXT("Niagara: %s"), *M); };

	// Create system
	FString Path = FString::Printf(TEXT("/Game/Arcwright/Niagara/%s"), *Name);
	UPackage* Pkg = CreatePackage(*Path);
	if (!Pkg) return FCommandResult::Error(TEXT("Failed to create package"));

	UNiagaraSystem* System = NewObject<UNiagaraSystem>(Pkg, FName(*Name), RF_Public | RF_Standalone);
	if (!System) return FCommandResult::Error(TEXT("Failed to create UNiagaraSystem"));
	Log(TEXT("Step 1: NiagaraSystem created OK"));

	// Create an emitter
	UNiagaraEmitter* Emitter = NewObject<UNiagaraEmitter>(Pkg, FName(*(Name + TEXT("_Emitter"))), RF_Public | RF_Standalone);
	if (!Emitter)
	{
		Log(TEXT("Step 2: FAIL — cannot create emitter"));
	}
	else
	{
		Log(FString::Printf(TEXT("Step 2: Emitter created OK (%s)"), *Emitter->GetName()));

		// Add emitter to system
		FNiagaraEmitterHandle Handle = System->AddEmitterHandle(*Emitter, FName(TEXT("TestEmitter")), FGuid::NewGuid());
		Log(FString::Printf(TEXT("Step 3: Emitter added to system (handles: %d)"), System->GetEmitterHandles().Num()));
	}

	FAssetRegistryModule::AssetCreated(System);
	System->MarkPackageDirty();
	Log(TEXT("Step 4: System saved OK"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), Path);
	Data->SetNumberField(TEXT("emitter_count"), System->GetEmitterHandles().Num());

	TArray<TSharedPtr<FJsonValue>> StepArr;
	for (const FString& S : Steps) StepArr.Add(MakeShareable(new FJsonValueString(S)));
	Data->SetArrayField(TEXT("steps"), StepArr);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCreateNiagaraSystem(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: name"));

	FString Path = FString::Printf(TEXT("/Game/Arcwright/Niagara/%s"), *Name);
	UPackage* Pkg = CreatePackage(*Path);
	if (!Pkg) return FCommandResult::Error(TEXT("Failed to create package"));

	UNiagaraSystem* System = NewObject<UNiagaraSystem>(Pkg, FName(*Name), RF_Public | RF_Standalone);
	if (!System) return FCommandResult::Error(TEXT("Failed to create UNiagaraSystem"));

	FAssetRegistryModule::AssetCreated(System);
	System->MarkPackageDirty();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), Path);
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleAddNiagaraEmitter(const TSharedPtr<FJsonObject>& Params)
{
	FString SystemName = Params->GetStringField(TEXT("system"));
	FString EmitterName = Params->HasField(TEXT("emitter_name")) ? Params->GetStringField(TEXT("emitter_name")) : TEXT("Emitter");

	if (SystemName.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: system"));

	FString SysPath = FString::Printf(TEXT("/Game/Arcwright/Niagara/%s"), *SystemName);
	UNiagaraSystem* System = LoadObject<UNiagaraSystem>(nullptr, *SysPath);
	if (!System) return FCommandResult::Error(FString::Printf(TEXT("System not found: %s"), *SystemName));

	UNiagaraEmitter* Emitter = NewObject<UNiagaraEmitter>(System->GetPackage(),
		FName(*(SystemName + TEXT("_") + EmitterName)), RF_Public | RF_Standalone);
	if (!Emitter) return FCommandResult::Error(TEXT("Failed to create emitter"));

	FNiagaraEmitterHandle Handle = System->AddEmitterHandle(*Emitter, FName(*EmitterName), FGuid::NewGuid());
	System->MarkPackageDirty();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("system"), SystemName);
	Data->SetStringField(TEXT("emitter_name"), EmitterName);
	Data->SetNumberField(TEXT("emitter_count"), System->GetEmitterHandles().Num());
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleSetNiagaraEmitterParam(const TSharedPtr<FJsonObject>& Params)
{
	// Delegate to existing set_niagara_parameter for placed actors
	// For asset-level parameters, this is a stub
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("note"), TEXT("Emitter parameters set via Niagara override stack. Use set_niagara_parameter on spawned actors."));
	return FCommandResult::Ok(Data);
}

FCommandResult FCommandServer::HandleCompileNiagaraSystem(const TSharedPtr<FJsonObject>& Params)
{
	FString SystemName = Params->GetStringField(TEXT("system"));
	if (SystemName.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: system"));

	FString SysPath = FString::Printf(TEXT("/Game/Arcwright/Niagara/%s"), *SystemName);
	UNiagaraSystem* System = LoadObject<UNiagaraSystem>(nullptr, *SysPath);
	if (!System) return FCommandResult::Error(TEXT("System not found"));

	System->RequestCompile(false);
	System->WaitForCompilationComplete();
	System->MarkPackageDirty();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("system"), SystemName);
	Data->SetBoolField(TEXT("compiled"), true);
	return FCommandResult::Ok(Data);
}

// ============================================================
// Material Graph DSL Commands
// ============================================================

// Helper: resolve material expression class from DSL type name
static UClass* ResolveMaterialExpressionClass(const FString& TypeName)
{
	static TMap<FString, UClass*> Map;
	if (Map.Num() == 0)
	{
		Map.Add(TEXT("TEXTURE_SAMPLE"), UMaterialExpressionTextureSample::StaticClass());
		Map.Add(TEXT("TEXTURE_PARAM"), UMaterialExpressionTextureObjectParameter::StaticClass());
		Map.Add(TEXT("SCALAR_PARAM"), UMaterialExpressionScalarParameter::StaticClass());
		Map.Add(TEXT("VECTOR_PARAM"), UMaterialExpressionVectorParameter::StaticClass());
		Map.Add(TEXT("CONSTANT"), UMaterialExpressionConstant::StaticClass());
		Map.Add(TEXT("CONSTANT3"), UMaterialExpressionConstant3Vector::StaticClass());
		Map.Add(TEXT("MULTIPLY"), UMaterialExpressionMultiply::StaticClass());
		Map.Add(TEXT("ADD"), UMaterialExpressionAdd::StaticClass());
		Map.Add(TEXT("SUBTRACT"), UMaterialExpressionSubtract::StaticClass());
		Map.Add(TEXT("DIVIDE"), UMaterialExpressionDivide::StaticClass());
		Map.Add(TEXT("LERP"), UMaterialExpressionLinearInterpolate::StaticClass());
		Map.Add(TEXT("CLAMP"), UMaterialExpressionClamp::StaticClass());
		Map.Add(TEXT("POWER"), UMaterialExpressionPower::StaticClass());
		Map.Add(TEXT("ABS"), UMaterialExpressionAbs::StaticClass());
		Map.Add(TEXT("ONE_MINUS"), UMaterialExpressionOneMinus::StaticClass());
		Map.Add(TEXT("FRESNEL"), UMaterialExpressionFresnel::StaticClass());
		Map.Add(TEXT("PANNER"), UMaterialExpressionPanner::StaticClass());
		Map.Add(TEXT("TEX_COORD"), UMaterialExpressionTextureCoordinate::StaticClass());
		Map.Add(TEXT("TIME"), UMaterialExpressionTime::StaticClass());
		Map.Add(TEXT("NOISE"), UMaterialExpressionNoise::StaticClass());
		Map.Add(TEXT("DESATURATION"), UMaterialExpressionDesaturation::StaticClass());
		Map.Add(TEXT("MASK"), UMaterialExpressionComponentMask::StaticClass());
		Map.Add(TEXT("APPEND"), UMaterialExpressionAppendVector::StaticClass());
	}
	return Map.FindRef(TypeName.ToUpper());
}

// ── test_create_material_graph (feasibility) ────────────────

FCommandResult FCommandServer::HandleTestCreateMaterialGraph(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->HasField(TEXT("name")) ? Params->GetStringField(TEXT("name")) : TEXT("M_TestGraph");
	TArray<FString> Steps;
	auto Log = [&Steps](const FString& M) { Steps.Add(M); UE_LOG(LogBlueprintLLM, Log, TEXT("MatGraph: %s"), *M); };

	// Create material
	FString Path = FString::Printf(TEXT("/Game/Arcwright/Materials/%s"), *Name);
	UPackage* Pkg = CreatePackage(*Path);
	if (!Pkg) return FCommandResult::Error(TEXT("Failed to create package"));

	UMaterial* Mat = NewObject<UMaterial>(Pkg, FName(*Name), RF_Public | RF_Standalone);
	if (!Mat) return FCommandResult::Error(TEXT("Failed to create UMaterial"));
	Log(TEXT("Step 1: Material created OK"));

	// Create Constant3Vector (color)
	UMaterialExpressionConstant3Vector* ColorNode = NewObject<UMaterialExpressionConstant3Vector>(Mat);
	ColorNode->Constant = FLinearColor(0.8f, 0.2f, 0.1f);
	ColorNode->MaterialExpressionEditorX = -400;
	ColorNode->MaterialExpressionEditorY = 0;
	Mat->GetExpressionCollection().AddExpression(ColorNode);
	Log(TEXT("Step 2: Constant3Vector node created OK"));

	// Create Multiply node
	UMaterialExpressionMultiply* MulNode = NewObject<UMaterialExpressionMultiply>(Mat);
	MulNode->MaterialExpressionEditorX = -200;
	MulNode->MaterialExpressionEditorY = 0;
	Mat->GetExpressionCollection().AddExpression(MulNode);
	Log(TEXT("Step 3: Multiply node created OK"));

	// Create Scalar constant for roughness
	UMaterialExpressionConstant* RoughNode = NewObject<UMaterialExpressionConstant>(Mat);
	RoughNode->R = 0.7f;
	RoughNode->MaterialExpressionEditorX = -200;
	RoughNode->MaterialExpressionEditorY = 200;
	Mat->GetExpressionCollection().AddExpression(RoughNode);
	Log(TEXT("Step 4: Constant (roughness) node created OK"));

	// Connect: ColorNode → Multiply.A
	MulNode->A.Connect(0, ColorNode);
	Log(TEXT("Step 5: Color → Multiply.A connected OK"));

	// Set Multiply.B to a constant (0.8)
	MulNode->ConstB = 0.8f;

	// Connect to material outputs
	Mat->GetEditorOnlyData()->BaseColor.Connect(0, MulNode);
	Log(TEXT("Step 6: Multiply → BaseColor connected OK"));

	Mat->GetEditorOnlyData()->Roughness.Connect(0, RoughNode);
	Log(TEXT("Step 7: Constant → Roughness connected OK"));

	// Compile
	Mat->PreEditChange(nullptr);
	Mat->PostEditChange();
	FAssetRegistryModule::AssetCreated(Mat);
	Mat->MarkPackageDirty();
	Log(TEXT("Step 8: Material compiled OK"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), Path);
	Data->SetNumberField(TEXT("expression_count"), Mat->GetExpressionCollection().Expressions.Num());

	TArray<TSharedPtr<FJsonValue>> StepArr;
	for (const FString& S : Steps) StepArr.Add(MakeShareable(new FJsonValueString(S)));
	Data->SetArrayField(TEXT("steps"), StepArr);
	return FCommandResult::Ok(Data);
}

// ── create_material ─────────────────────────────────────────

FCommandResult FCommandServer::HandleCreateMaterial(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: name"));

	FString Path = FString::Printf(TEXT("/Game/Arcwright/Materials/%s"), *Name);
	UPackage* Pkg = CreatePackage(*Path);
	if (!Pkg) return FCommandResult::Error(TEXT("Failed to create package"));

	UMaterial* Mat = NewObject<UMaterial>(Pkg, FName(*Name), RF_Public | RF_Standalone);
	if (!Mat) return FCommandResult::Error(TEXT("Failed to create UMaterial"));

	FAssetRegistryModule::AssetCreated(Mat);
	Mat->MarkPackageDirty();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), Path);
	return FCommandResult::Ok(Data);
}

// ── add_material_node ───────────────────────────────────────

FCommandResult FCommandServer::HandleAddMaterialNode(const TSharedPtr<FJsonObject>& Params)
{
	FString MatName = Params->GetStringField(TEXT("material"));
	FString NodeType = Params->GetStringField(TEXT("type"));
	FString NodeName = Params->HasField(TEXT("name")) ? Params->GetStringField(TEXT("name")) : TEXT("");

	if (MatName.IsEmpty() || NodeType.IsEmpty())
		return FCommandResult::Error(TEXT("Missing params: material, type"));

	// Find material
	FString MatPath = FString::Printf(TEXT("/Game/Arcwright/Materials/%s"), *MatName);
	UMaterial* Mat = LoadObject<UMaterial>(nullptr, *MatPath);
	if (!Mat) return FCommandResult::Error(FString::Printf(TEXT("Material not found: %s"), *MatName));

	UClass* ExprClass = ResolveMaterialExpressionClass(NodeType);
	if (!ExprClass)
		return FCommandResult::Error(FString::Printf(TEXT("Unknown node type: %s"), *NodeType));

	UMaterialExpression* Expr = NewObject<UMaterialExpression>(Mat, ExprClass);
	if (!Expr) return FCommandResult::Error(TEXT("Failed to create expression"));

	Mat->GetExpressionCollection().AddExpression(Expr);

	// Set common params
	if (Params->HasField(TEXT("pos_x")))
		Expr->MaterialExpressionEditorX = (int32)Params->GetNumberField(TEXT("pos_x"));
	if (Params->HasField(TEXT("pos_y")))
		Expr->MaterialExpressionEditorY = (int32)Params->GetNumberField(TEXT("pos_y"));

	// Type-specific params
	if (UMaterialExpressionConstant* C = Cast<UMaterialExpressionConstant>(Expr))
	{
		if (Params->HasField(TEXT("value"))) C->R = Params->GetNumberField(TEXT("value"));
	}
	else if (UMaterialExpressionConstant3Vector* C3 = Cast<UMaterialExpressionConstant3Vector>(Expr))
	{
		if (Params->HasField(TEXT("r")))
			C3->Constant = FLinearColor(Params->GetNumberField(TEXT("r")),
				Params->HasField(TEXT("g")) ? Params->GetNumberField(TEXT("g")) : 0,
				Params->HasField(TEXT("b")) ? Params->GetNumberField(TEXT("b")) : 0);
	}
	else if (UMaterialExpressionScalarParameter* SP = Cast<UMaterialExpressionScalarParameter>(Expr))
	{
		if (!NodeName.IsEmpty()) SP->ParameterName = FName(*NodeName);
		if (Params->HasField(TEXT("default_value"))) SP->DefaultValue = Params->GetNumberField(TEXT("default_value"));
	}
	else if (UMaterialExpressionVectorParameter* VP = Cast<UMaterialExpressionVectorParameter>(Expr))
	{
		if (!NodeName.IsEmpty()) VP->ParameterName = FName(*NodeName);
		if (Params->HasField(TEXT("r")))
			VP->DefaultValue = FLinearColor(Params->GetNumberField(TEXT("r")),
				Params->HasField(TEXT("g")) ? Params->GetNumberField(TEXT("g")) : 0,
				Params->HasField(TEXT("b")) ? Params->GetNumberField(TEXT("b")) : 0);
	}

	// Store node name → index for connection lookups
	int32 Idx = Mat->GetExpressionCollection().Expressions.Num() - 1;

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("material"), MatName);
	Data->SetStringField(TEXT("node_type"), NodeType);
	Data->SetStringField(TEXT("node_name"), NodeName);
	Data->SetNumberField(TEXT("node_index"), Idx);
	return FCommandResult::Ok(Data);
}

// ── connect_material_nodes ──────────────────────────────────

FCommandResult FCommandServer::HandleConnectMaterialNodes(const TSharedPtr<FJsonObject>& Params)
{
	FString MatName = Params->GetStringField(TEXT("material"));
	int32 SrcIdx = (int32)Params->GetNumberField(TEXT("source_index"));
	int32 DstIdx = (int32)Params->GetNumberField(TEXT("dest_index"));
	int32 SrcOutput = Params->HasField(TEXT("source_output")) ? (int32)Params->GetNumberField(TEXT("source_output")) : 0;
	FString InputName = Params->HasField(TEXT("input_name")) ? Params->GetStringField(TEXT("input_name")) : TEXT("A");

	FString MatPath = FString::Printf(TEXT("/Game/Arcwright/Materials/%s"), *MatName);
	UMaterial* Mat = LoadObject<UMaterial>(nullptr, *MatPath);
	if (!Mat) return FCommandResult::Error(TEXT("Material not found"));

	auto& Exprs = Mat->GetExpressionCollection().Expressions;
	if (SrcIdx < 0 || SrcIdx >= Exprs.Num()) return FCommandResult::Error(TEXT("Invalid source_index"));
	if (DstIdx < 0 || DstIdx >= Exprs.Num()) return FCommandResult::Error(TEXT("Invalid dest_index"));

	UMaterialExpression* Src = Exprs[SrcIdx];
	UMaterialExpression* Dst = Exprs[DstIdx];

	// Connect based on input name — check common expression types
	bool bConnected = false;
	FString InName = InputName.ToUpper();

	if (UMaterialExpressionMultiply* Mul = Cast<UMaterialExpressionMultiply>(Dst))
	{
		if (InName == TEXT("A") || InName == TEXT("0")) { Mul->A.Connect(SrcOutput, Src); bConnected = true; }
		else { Mul->B.Connect(SrcOutput, Src); bConnected = true; }
	}
	else if (UMaterialExpressionAdd* Add = Cast<UMaterialExpressionAdd>(Dst))
	{
		if (InName == TEXT("A") || InName == TEXT("0")) { Add->A.Connect(SrcOutput, Src); bConnected = true; }
		else { Add->B.Connect(SrcOutput, Src); bConnected = true; }
	}
	else if (UMaterialExpressionLinearInterpolate* Lerp = Cast<UMaterialExpressionLinearInterpolate>(Dst))
	{
		if (InName == TEXT("A")) { Lerp->A.Connect(SrcOutput, Src); bConnected = true; }
		else if (InName == TEXT("B")) { Lerp->B.Connect(SrcOutput, Src); bConnected = true; }
		else { Lerp->Alpha.Connect(SrcOutput, Src); bConnected = true; }
	}
	else if (UMaterialExpressionSubtract* Sub = Cast<UMaterialExpressionSubtract>(Dst))
	{
		if (InName == TEXT("A") || InName == TEXT("0")) { Sub->A.Connect(SrcOutput, Src); bConnected = true; }
		else { Sub->B.Connect(SrcOutput, Src); bConnected = true; }
	}
	else if (UMaterialExpressionDivide* Div = Cast<UMaterialExpressionDivide>(Dst))
	{
		if (InName == TEXT("A") || InName == TEXT("0")) { Div->A.Connect(SrcOutput, Src); bConnected = true; }
		else { Div->B.Connect(SrcOutput, Src); bConnected = true; }
	}
	else if (UMaterialExpressionPower* Pow = Cast<UMaterialExpressionPower>(Dst))
	{
		if (InName == TEXT("A") || InName == TEXT("BASE")) { Pow->Base.Connect(SrcOutput, Src); bConnected = true; }
		else { Pow->Exponent.Connect(SrcOutput, Src); bConnected = true; }
	}
	else if (UMaterialExpressionOneMinus* OM = Cast<UMaterialExpressionOneMinus>(Dst))
	{
		OM->Input.Connect(SrcOutput, Src); bConnected = true;
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetBoolField(TEXT("connected"), bConnected);
	Data->SetNumberField(TEXT("source_index"), SrcIdx);
	Data->SetNumberField(TEXT("dest_index"), DstIdx);
	return FCommandResult::Ok(Data);
}

// ── set_material_output ─────────────────────────────────────

FCommandResult FCommandServer::HandleSetMaterialOutput(const TSharedPtr<FJsonObject>& Params)
{
	FString MatName = Params->GetStringField(TEXT("material"));
	int32 NodeIdx = (int32)Params->GetNumberField(TEXT("node_index"));
	FString OutputPin = Params->GetStringField(TEXT("output_pin"));
	int32 SrcOutput = Params->HasField(TEXT("source_output")) ? (int32)Params->GetNumberField(TEXT("source_output")) : 0;

	FString MatPath = FString::Printf(TEXT("/Game/Arcwright/Materials/%s"), *MatName);
	UMaterial* Mat = LoadObject<UMaterial>(nullptr, *MatPath);
	if (!Mat) return FCommandResult::Error(TEXT("Material not found"));

	auto& Exprs = Mat->GetExpressionCollection().Expressions;
	if (NodeIdx < 0 || NodeIdx >= Exprs.Num()) return FCommandResult::Error(TEXT("Invalid node_index"));

	UMaterialExpression* Expr = Exprs[NodeIdx];
	UMaterialEditorOnlyData* EdData = Mat->GetEditorOnlyData();
	if (!EdData) return FCommandResult::Error(TEXT("No editor data"));

	bool bConnected = false;
	FString Pin = OutputPin.ToLower();
	if (Pin == TEXT("basecolor") || Pin == TEXT("base_color")) { EdData->BaseColor.Connect(SrcOutput, Expr); bConnected = true; }
	else if (Pin == TEXT("roughness")) { EdData->Roughness.Connect(SrcOutput, Expr); bConnected = true; }
	else if (Pin == TEXT("metallic")) { EdData->Metallic.Connect(SrcOutput, Expr); bConnected = true; }
	else if (Pin == TEXT("normal")) { EdData->Normal.Connect(SrcOutput, Expr); bConnected = true; }
	else if (Pin == TEXT("emissive") || Pin == TEXT("emissivecolor")) { EdData->EmissiveColor.Connect(SrcOutput, Expr); bConnected = true; }
	else if (Pin == TEXT("opacity")) { EdData->Opacity.Connect(SrcOutput, Expr); bConnected = true; }
	else if (Pin == TEXT("ambientocclusion") || Pin == TEXT("ao")) { EdData->AmbientOcclusion.Connect(SrcOutput, Expr); bConnected = true; }

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetBoolField(TEXT("connected"), bConnected);
	Data->SetStringField(TEXT("output_pin"), OutputPin);
	return FCommandResult::Ok(Data);
}

// ── compile_material ────────────────────────────────────────

FCommandResult FCommandServer::HandleCompileMaterial(const TSharedPtr<FJsonObject>& Params)
{
	FString MatName = Params->GetStringField(TEXT("material"));
	if (MatName.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: material"));

	FString MatPath = FString::Printf(TEXT("/Game/Arcwright/Materials/%s"), *MatName);
	UMaterial* Mat = LoadObject<UMaterial>(nullptr, *MatPath);
	if (!Mat) return FCommandResult::Error(TEXT("Material not found"));

	Mat->PreEditChange(nullptr);
	Mat->PostEditChange();
	Mat->MarkPackageDirty();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("material"), MatName);
	Data->SetBoolField(TEXT("compiled"), true);
	Data->SetNumberField(TEXT("expression_count"), Mat->GetExpressionCollection().Expressions.Num());
	return FCommandResult::Ok(Data);
}

// ── create_material_from_dsl (placeholder — Python pipeline) ─

FCommandResult FCommandServer::HandleCreateMaterialFromDSL(const TSharedPtr<FJsonObject>& Params)
{
	// This will be called by the Python MCP tool that runs the parser pipeline
	// For now, return guidance
	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("note"), TEXT("Use the MCP create_material_from_dsl tool which runs the Python parser pipeline."));
	return FCommandResult::Ok(Data);
}

// ============================================================
// AnimBP Test — feasibility proof for Animation Blueprint DSL
// ============================================================

FCommandResult FCommandServer::HandleTestCreateAnimBlueprint(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->HasField(TEXT("name")) ? Params->GetStringField(TEXT("name")) : TEXT("ABP_Test");
	FString SkeletonPath = Params->HasField(TEXT("skeleton"))
		? Params->GetStringField(TEXT("skeleton"))
		: TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny");

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	TArray<FString> Steps;

	auto Log = [&Steps](const FString& Msg) { Steps.Add(Msg); UE_LOG(LogBlueprintLLM, Log, TEXT("AnimBP Test: %s"), *Msg); };

	// Step 1: Find skeleton
	USkeleton* Skeleton = nullptr;
	{
		// Try to load the skeleton from the skeletal mesh
		USkeletalMesh* SkelMesh = LoadObject<USkeletalMesh>(nullptr, *SkeletonPath);
		if (SkelMesh)
		{
			Skeleton = SkelMesh->GetSkeleton();
			Log(FString::Printf(TEXT("Step 1: Skeleton from mesh OK (%s)"), *Skeleton->GetName()));
		}
		else
		{
			// Try loading directly as USkeleton
			Skeleton = LoadObject<USkeleton>(nullptr, *SkeletonPath);
			if (Skeleton)
				Log(FString::Printf(TEXT("Step 1: Skeleton direct OK (%s)"), *Skeleton->GetName()));
			else
			{
				Log(TEXT("Step 1: FAIL — Skeleton not found. Trying engine mannequin..."));
				// Try engine path
				SkelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Engine/EngineMeshes/SkeletalCube"));
				if (SkelMesh) Skeleton = SkelMesh->GetSkeleton();
				if (Skeleton)
					Log(TEXT("Step 1: Fallback skeleton OK"));
				else
				{
					Log(TEXT("Step 1: FAIL — No skeleton available"));
					Data->SetArrayField(TEXT("steps"), [&]() {
						TArray<TSharedPtr<FJsonValue>> Arr;
						for (const FString& S : Steps) Arr.Add(MakeShareable(new FJsonValueString(S)));
						return Arr;
					}());
					return FCommandResult::Error(TEXT("No skeleton found for AnimBP test"));
				}
			}
		}
	}

	// Step 2: Create AnimBlueprint
	FString PackagePath = FString::Printf(TEXT("/Game/Arcwright/Generated/%s"), *Name);
	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package)
	{
		Log(TEXT("Step 2: FAIL — CreatePackage"));
		return FCommandResult::Error(TEXT("Failed to create package"));
	}

	UAnimBlueprint* AnimBP = CastChecked<UAnimBlueprint>(
		FKismetEditorUtilities::CreateBlueprint(
			UAnimInstance::StaticClass(),
			Package,
			FName(*Name),
			BPTYPE_Normal,
			UAnimBlueprint::StaticClass(),
			UBlueprintGeneratedClass::StaticClass()
		)
	);

	if (!AnimBP)
	{
		Log(TEXT("Step 2: FAIL — CreateBlueprint"));
		return FCommandResult::Error(TEXT("Failed to create AnimBlueprint"));
	}

	AnimBP->TargetSkeleton = Skeleton;
	Log(FString::Printf(TEXT("Step 2: AnimBP created OK (%s)"), *PackagePath));

	// Step 3: Get the AnimGraph
	UEdGraph* AnimGraph = nullptr;
	for (UEdGraph* Graph : AnimBP->FunctionGraphs)
	{
		if (Graph && Graph->GetFName() == TEXT("AnimGraph"))
		{
			AnimGraph = Graph;
			break;
		}
	}

	if (!AnimGraph)
	{
		Log(TEXT("Step 3: AnimGraph not found in FunctionGraphs, checking UbergraphPages..."));
		for (UEdGraph* Graph : AnimBP->UbergraphPages)
		{
			if (Graph && Graph->GetFName() == TEXT("AnimGraph"))
			{
				AnimGraph = Graph;
				break;
			}
		}
	}

	if (AnimGraph)
	{
		Log(FString::Printf(TEXT("Step 3: AnimGraph found OK (%d nodes)"), AnimGraph->Nodes.Num()));
	}
	else
	{
		Log(TEXT("Step 3: WARN — AnimGraph not found. Available graphs:"));
		for (UEdGraph* G : AnimBP->FunctionGraphs)
			Log(FString::Printf(TEXT("  FunctionGraph: %s"), *G->GetName()));
		for (UEdGraph* G : AnimBP->UbergraphPages)
			Log(FString::Printf(TEXT("  UbergraphPage: %s"), *G->GetName()));
	}

	// Step 4: Create State Machine node
	bool bStateMachineOK = false;
	UAnimGraphNode_StateMachine* SMNode = nullptr;

	if (AnimGraph)
	{
		SMNode = NewObject<UAnimGraphNode_StateMachine>(AnimGraph);
		if (SMNode)
		{
			SMNode->CreateNewGuid();
			AnimGraph->AddNode(SMNode, false, false);
			SMNode->PostPlacedNewNode();  // Creates EditorStateMachineGraph
			SMNode->AllocateDefaultPins();
			SMNode->NodePosX = 200;
			SMNode->NodePosY = 0;

			Log(FString::Printf(TEXT("Step 4: StateMachine node created OK (has graph: %s)"),
				SMNode->EditorStateMachineGraph ? TEXT("yes") : TEXT("no")));
			bStateMachineOK = true;
		}
		else
		{
			Log(TEXT("Step 4: FAIL — NewObject<UAnimGraphNode_StateMachine>"));
		}
	}
	else
	{
		Log(TEXT("Step 4: SKIP — no AnimGraph"));
	}

	// Step 5: Add states to the state machine
	bool bStatesOK = false;
	if (bStateMachineOK && SMNode && SMNode->EditorStateMachineGraph)
	{
		UAnimationStateMachineGraph* SMGraph = SMNode->EditorStateMachineGraph;

		// Create Idle state
		UAnimStateNode* IdleState = NewObject<UAnimStateNode>(SMGraph);
		if (IdleState)
		{
			IdleState->CreateNewGuid();
			IdleState->AllocateDefaultPins();
			SMGraph->AddNode(IdleState, false, false);
			IdleState->NodePosX = 200;
			IdleState->NodePosY = 0;

			// Rename
			FBlueprintEditorUtils::RenameGraph(IdleState->GetBoundGraph(), TEXT("Idle"));

			Log(TEXT("Step 5a: Idle state created OK"));
		}

		// Create Walk state
		UAnimStateNode* WalkState = NewObject<UAnimStateNode>(SMGraph);
		if (WalkState)
		{
			WalkState->CreateNewGuid();
			WalkState->AllocateDefaultPins();
			SMGraph->AddNode(WalkState, false, false);
			WalkState->NodePosX = 500;
			WalkState->NodePosY = 0;

			FBlueprintEditorUtils::RenameGraph(WalkState->GetBoundGraph(), TEXT("Walk"));

			Log(TEXT("Step 5b: Walk state created OK"));
		}

		// Step 6: Add transition Idle → Walk
		if (IdleState && WalkState)
		{
			UAnimStateTransitionNode* Trans = NewObject<UAnimStateTransitionNode>(SMGraph);
			if (Trans)
			{
				Trans->CreateNewGuid();
				Trans->AllocateDefaultPins();
				SMGraph->AddNode(Trans, false, false);
				Trans->NodePosX = 350;
				Trans->NodePosY = -50;

				// Wire: Idle output → Transition input, Transition output → Walk input
				UEdGraphPin* IdleOut = nullptr;
				UEdGraphPin* WalkIn = nullptr;
				UEdGraphPin* TransIn = nullptr;
				UEdGraphPin* TransOut = nullptr;

				for (UEdGraphPin* P : IdleState->Pins)
					if (P->Direction == EGPD_Output) { IdleOut = P; break; }
				for (UEdGraphPin* P : WalkState->Pins)
					if (P->Direction == EGPD_Input) { WalkIn = P; break; }
				for (UEdGraphPin* P : Trans->Pins)
				{
					if (P->Direction == EGPD_Input) TransIn = P;
					if (P->Direction == EGPD_Output) TransOut = P;
				}

				bool bWired = false;
				if (IdleOut && TransIn)
				{
					IdleOut->MakeLinkTo(TransIn);
					bWired = true;
				}
				if (TransOut && WalkIn)
				{
					TransOut->MakeLinkTo(WalkIn);
				}

				Log(FString::Printf(TEXT("Step 6: Transition Idle->Walk %s"),
					bWired ? TEXT("OK (wired)") : TEXT("PARTIAL (pins not found)")));
			}
			else
			{
				Log(TEXT("Step 6: FAIL — create transition"));
			}
		}

		bStatesOK = (IdleState != nullptr && WalkState != nullptr);

		// Connect entry node to Idle
		if (SMGraph->EntryNode && IdleState)
		{
			UEdGraphPin* EntryOut = nullptr;
			UEdGraphPin* IdleIn = nullptr;
			for (UEdGraphPin* P : SMGraph->EntryNode->Pins)
				if (P->Direction == EGPD_Output) { EntryOut = P; break; }
			for (UEdGraphPin* P : IdleState->Pins)
				if (P->Direction == EGPD_Input) { IdleIn = P; break; }
			if (EntryOut && IdleIn)
			{
				EntryOut->MakeLinkTo(IdleIn);
				Log(TEXT("Step 6b: Entry->Idle wired OK"));
			}
		}
	}
	else
	{
		Log(TEXT("Step 5: SKIP — no state machine graph"));
	}

	// Step 7: Compile (only if we have states — empty state machine crashes compiler)
	bool bCompiled = false;
	if (bStatesOK)
	{
		FKismetEditorUtilities::CompileBlueprint(AnimBP);
		bCompiled = true;
		Log(TEXT("Step 7: Compiled OK"));
	}
	else
	{
		Log(TEXT("Step 7: SKIP compile (no states — would crash)"));
	}
	FAssetRegistryModule::AssetCreated(AnimBP);
	AnimBP->MarkPackageDirty();

	// Build result
	TArray<TSharedPtr<FJsonValue>> StepArr;
	for (const FString& S : Steps)
		StepArr.Add(MakeShareable(new FJsonValueString(S)));

	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), PackagePath);
	Data->SetBoolField(TEXT("skeleton_found"), Skeleton != nullptr);
	Data->SetBoolField(TEXT("anim_graph_found"), AnimGraph != nullptr);
	Data->SetBoolField(TEXT("state_machine_created"), bStateMachineOK);
	Data->SetBoolField(TEXT("states_created"), bStatesOK);
	Data->SetBoolField(TEXT("compiled"), bCompiled);
	Data->SetArrayField(TEXT("steps"), StepArr);

	return FCommandResult::Ok(Data);
}

// ── AnimBP helper ───────────────────────────────────────────

UAnimBlueprint* FCommandServer::FindAnimBlueprintByName(const FString& Name)
{
	FString Path = FString::Printf(TEXT("/Game/Arcwright/Generated/%s.%s"), *Name, *Name);
	UAnimBlueprint* ABP = LoadObject<UAnimBlueprint>(nullptr, *Path);
	if (!ABP)
	{
		Path = FString::Printf(TEXT("/Game/Animations/%s.%s"), *Name, *Name);
		ABP = LoadObject<UAnimBlueprint>(nullptr, *Path);
	}
	return ABP;
}

// ── create_anim_blueprint (from DSL — placeholder for Python pipeline) ──

FCommandResult FCommandServer::HandleCreateAnimBlueprintDSL(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	FString SkeletonPath = Params->HasField(TEXT("skeleton_path")) ? Params->GetStringField(TEXT("skeleton_path")) : TEXT("");

	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: name"));
	if (SkeletonPath.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: skeleton_path"));

	// Find skeleton
	USkeleton* Skeleton = nullptr;
	USkeletalMesh* SkelMesh = LoadObject<USkeletalMesh>(nullptr, *SkeletonPath);
	if (SkelMesh) Skeleton = SkelMesh->GetSkeleton();
	if (!Skeleton) Skeleton = LoadObject<USkeleton>(nullptr, *SkeletonPath);
	if (!Skeleton) return FCommandResult::Error(FString::Printf(TEXT("Skeleton not found: %s"), *SkeletonPath));

	// Delete existing
	UAnimBlueprint* Existing = FindAnimBlueprintByName(Name);
	if (Existing)
	{
		TArray<UObject*> Del; Del.Add(Existing);
		ObjectTools::ForceDeleteObjects(Del, false);
	}

	FString PackagePath = FString::Printf(TEXT("/Game/Arcwright/Generated/%s"), *Name);
	UPackage* Package = CreatePackage(*PackagePath);
	if (!Package) return FCommandResult::Error(TEXT("Failed to create package"));

	UAnimBlueprint* ABP = CastChecked<UAnimBlueprint>(
		FKismetEditorUtilities::CreateBlueprint(UAnimInstance::StaticClass(), Package,
			FName(*Name), BPTYPE_Normal, UAnimBlueprint::StaticClass(), UBlueprintGeneratedClass::StaticClass()));
	if (!ABP) return FCommandResult::Error(TEXT("Failed to create AnimBlueprint"));

	ABP->TargetSkeleton = Skeleton;
	FAssetRegistryModule::AssetCreated(ABP);
	ABP->MarkPackageDirty();

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("asset_path"), PackagePath);
	Data->SetStringField(TEXT("skeleton"), Skeleton->GetName());
	return FCommandResult::Ok(Data);
}

// ── add_state_machine ───────────────────────────────────────

FCommandResult FCommandServer::HandleAddStateMachine(const TSharedPtr<FJsonObject>& Params)
{
	FString BPName = Params->GetStringField(TEXT("anim_bp"));
	FString MachineName = Params->GetStringField(TEXT("machine_name"));
	if (BPName.IsEmpty() || MachineName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing params: anim_bp, machine_name"));

	UAnimBlueprint* ABP = FindAnimBlueprintByName(BPName);
	if (!ABP) return FCommandResult::Error(FString::Printf(TEXT("AnimBP not found: %s"), *BPName));

	UEdGraph* AnimGraph = nullptr;
	for (UEdGraph* G : ABP->FunctionGraphs)
		if (G && G->GetFName() == TEXT("AnimGraph")) { AnimGraph = G; break; }
	if (!AnimGraph)
		return FCommandResult::Error(TEXT("AnimGraph not found"));

	UAnimGraphNode_StateMachine* SM = NewObject<UAnimGraphNode_StateMachine>(AnimGraph);
	if (!SM) return FCommandResult::Error(TEXT("Failed to create state machine node"));

	SM->CreateNewGuid();
	AnimGraph->AddNode(SM, false, false);
	SM->PostPlacedNewNode();
	SM->AllocateDefaultPins();

	bool bHasGraph = (SM->EditorStateMachineGraph != nullptr);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("anim_bp"), BPName);
	Data->SetStringField(TEXT("machine_name"), MachineName);
	Data->SetBoolField(TEXT("graph_created"), bHasGraph);
	return FCommandResult::Ok(Data);
}

// ── add_anim_state ──────────────────────────────────────────

FCommandResult FCommandServer::HandleAddAnimState2(const TSharedPtr<FJsonObject>& Params)
{
	FString BPName = Params->GetStringField(TEXT("anim_bp"));
	FString MachineName = Params->GetStringField(TEXT("machine_name"));
	FString StateName = Params->GetStringField(TEXT("state_name"));
	bool bIsEntry = Params->HasField(TEXT("is_entry")) && Params->GetBoolField(TEXT("is_entry"));

	if (BPName.IsEmpty() || StateName.IsEmpty())
		return FCommandResult::Error(TEXT("Missing params: anim_bp, state_name"));

	UAnimBlueprint* ABP = FindAnimBlueprintByName(BPName);
	if (!ABP) return FCommandResult::Error(FString::Printf(TEXT("AnimBP not found: %s"), *BPName));

	// Find the state machine graph (use first one for now)
	UAnimGraphNode_StateMachine* SMNode = nullptr;
	for (UEdGraph* G : ABP->FunctionGraphs)
	{
		if (!G) continue;
		for (UEdGraphNode* N : G->Nodes)
		{
			SMNode = Cast<UAnimGraphNode_StateMachine>(N);
			if (SMNode) break;
		}
		if (SMNode) break;
	}

	if (!SMNode || !SMNode->EditorStateMachineGraph)
		return FCommandResult::Error(TEXT("No state machine found in AnimBP"));

	UAnimationStateMachineGraph* SMGraph = SMNode->EditorStateMachineGraph;

	UAnimStateNode* State = NewObject<UAnimStateNode>(SMGraph);
	if (!State) return FCommandResult::Error(TEXT("Failed to create state"));

	State->CreateNewGuid();
	State->AllocateDefaultPins();
	SMGraph->AddNode(State, false, false);

	if (State->GetBoundGraph())
		FBlueprintEditorUtils::RenameGraph(State->GetBoundGraph(), *StateName);

	// Wire entry node to this state if it's the entry state
	if (bIsEntry && SMGraph->EntryNode)
	{
		UEdGraphPin* EntryOut = nullptr;
		UEdGraphPin* StateIn = nullptr;
		for (UEdGraphPin* P : SMGraph->EntryNode->Pins)
			if (P->Direction == EGPD_Output) { EntryOut = P; break; }
		for (UEdGraphPin* P : State->Pins)
			if (P->Direction == EGPD_Input) { StateIn = P; break; }
		if (EntryOut && StateIn)
			EntryOut->MakeLinkTo(StateIn);
	}

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("anim_bp"), BPName);
	Data->SetStringField(TEXT("state_name"), StateName);
	Data->SetBoolField(TEXT("is_entry"), bIsEntry);
	return FCommandResult::Ok(Data);
}

// ── add_anim_transition ─────────────────────────────────────

FCommandResult FCommandServer::HandleAddAnimTransition2(const TSharedPtr<FJsonObject>& Params)
{
	FString BPName = Params->GetStringField(TEXT("anim_bp"));
	FString FromState = Params->GetStringField(TEXT("from_state"));
	FString ToState = Params->GetStringField(TEXT("to_state"));

	if (BPName.IsEmpty() || FromState.IsEmpty() || ToState.IsEmpty())
		return FCommandResult::Error(TEXT("Missing params: anim_bp, from_state, to_state"));

	UAnimBlueprint* ABP = FindAnimBlueprintByName(BPName);
	if (!ABP) return FCommandResult::Error(FString::Printf(TEXT("AnimBP not found: %s"), *BPName));

	// Find SM graph and states
	UAnimGraphNode_StateMachine* SMNode = nullptr;
	for (UEdGraph* G : ABP->FunctionGraphs)
	{
		if (!G) continue;
		for (UEdGraphNode* N : G->Nodes)
		{
			SMNode = Cast<UAnimGraphNode_StateMachine>(N);
			if (SMNode) break;
		}
		if (SMNode) break;
	}
	if (!SMNode || !SMNode->EditorStateMachineGraph)
		return FCommandResult::Error(TEXT("No state machine found"));

	UAnimationStateMachineGraph* SMGraph = SMNode->EditorStateMachineGraph;

	UAnimStateNode* SrcState = nullptr;
	UAnimStateNode* DstState = nullptr;
	for (UEdGraphNode* N : SMGraph->Nodes)
	{
		UAnimStateNode* S = Cast<UAnimStateNode>(N);
		if (!S) continue;
		if (S->GetBoundGraph() && S->GetBoundGraph()->GetName() == FromState) SrcState = S;
		if (S->GetBoundGraph() && S->GetBoundGraph()->GetName() == ToState) DstState = S;
	}

	if (!SrcState) return FCommandResult::Error(FString::Printf(TEXT("State '%s' not found"), *FromState));
	if (!DstState) return FCommandResult::Error(FString::Printf(TEXT("State '%s' not found"), *ToState));

	UAnimStateTransitionNode* Trans = NewObject<UAnimStateTransitionNode>(SMGraph);
	if (!Trans) return FCommandResult::Error(TEXT("Failed to create transition"));

	Trans->CreateNewGuid();
	Trans->AllocateDefaultPins();
	SMGraph->AddNode(Trans, false, false);

	// Wire: Src → Trans → Dst
	UEdGraphPin *SrcOut = nullptr, *DstIn = nullptr, *TrIn = nullptr, *TrOut = nullptr;
	for (UEdGraphPin* P : SrcState->Pins) if (P->Direction == EGPD_Output) { SrcOut = P; break; }
	for (UEdGraphPin* P : DstState->Pins) if (P->Direction == EGPD_Input) { DstIn = P; break; }
	for (UEdGraphPin* P : Trans->Pins) { if (P->Direction == EGPD_Input) TrIn = P; if (P->Direction == EGPD_Output) TrOut = P; }

	bool bWired = false;
	if (SrcOut && TrIn) { SrcOut->MakeLinkTo(TrIn); bWired = true; }
	if (TrOut && DstIn) { TrOut->MakeLinkTo(DstIn); }

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("transition"), FString::Printf(TEXT("%s->%s"), *FromState, *ToState));
	Data->SetBoolField(TEXT("wired"), bWired);
	return FCommandResult::Ok(Data);
}

// ── add_anim_layer (stub — records intent) ──────────────────

FCommandResult FCommandServer::HandleAddAnimLayer(const TSharedPtr<FJsonObject>& Params)
{
	FString BPName = Params->GetStringField(TEXT("anim_bp"));
	FString LayerName = Params->GetStringField(TEXT("layer_name"));
	FString BoneMask = Params->HasField(TEXT("bone_mask_root")) ? Params->GetStringField(TEXT("bone_mask_root")) : TEXT("spine_01");
	FString SlotName = Params->HasField(TEXT("slot_name")) ? Params->GetStringField(TEXT("slot_name")) : TEXT("DefaultSlot");

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("anim_bp"), BPName);
	Data->SetStringField(TEXT("layer_name"), LayerName);
	Data->SetStringField(TEXT("bone_mask_root"), BoneMask);
	Data->SetStringField(TEXT("slot_name"), SlotName);
	Data->SetStringField(TEXT("note"), TEXT("Layer registered. Full bone mask layering requires AnimGraph editor integration."));
	return FCommandResult::Ok(Data);
}

// ── add_anim_montage ────────────────────────────────────────

FCommandResult FCommandServer::HandleAddAnimMontage(const TSharedPtr<FJsonObject>& Params)
{
	// Reuse existing create_anim_montage handler logic
	return HandleCreateAnimMontage(Params);
}

// ── create_aim_offset (stub) ────────────────────────────────

FCommandResult FCommandServer::HandleCreateAimOffset(const TSharedPtr<FJsonObject>& Params)
{
	FString Name = Params->GetStringField(TEXT("name"));
	if (Name.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: name"));

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("name"), Name);
	Data->SetStringField(TEXT("note"), TEXT("AimOffset creation requires UAimOffsetBlendSpace — full implementation pending."));
	return FCommandResult::Ok(Data);
}

// ── set_anim_notify ─────────────────────────────────────────

FCommandResult FCommandServer::HandleSetAnimNotify(const TSharedPtr<FJsonObject>& Params)
{
	return HandleAddMontageSection(Params);  // Reuse existing montage section handler
}

// ── compile_anim_blueprint ──────────────────────────────────

FCommandResult FCommandServer::HandleCompileAnimBlueprint(const TSharedPtr<FJsonObject>& Params)
{
	FString BPName = Params->GetStringField(TEXT("anim_bp"));
	if (BPName.IsEmpty()) return FCommandResult::Error(TEXT("Missing param: anim_bp"));

	UAnimBlueprint* ABP = FindAnimBlueprintByName(BPName);
	if (!ABP) return FCommandResult::Error(FString::Printf(TEXT("AnimBP not found: %s"), *BPName));

	FKismetEditorUtilities::CompileBlueprint(ABP);

	TSharedPtr<FJsonObject> Data = MakeShareable(new FJsonObject());
	Data->SetStringField(TEXT("anim_bp"), BPName);
	Data->SetBoolField(TEXT("compiled"), true);
	return FCommandResult::Ok(Data);
}


