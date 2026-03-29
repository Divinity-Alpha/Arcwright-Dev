// Copyright 2026 Divinity Alpha. All Rights Reserved.
#pragma once

#include "CoreMinimal.h"
#include "Common/TcpListener.h"
#include "Sockets.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include <atomic>

class USimpleConstructionScript;
class USCS_Node;
class FArcwrightStats;
class UBlueprint;
class UAnimBlueprint;
class UEdGraph;
class UEdGraphNode;
class AActor;
class UActorComponent;
class UMaterialInterface;
class UWidget;
class UEdGraphPin;
struct FAssetData;

DECLARE_LOG_CATEGORY_EXTERN(LogArcwright, Log, All);

struct FCommandResult
{
	bool bSuccess = false;
	TSharedPtr<FJsonObject> Data;
	FString ErrorMessage;

	static FCommandResult Ok(TSharedPtr<FJsonObject> InData = nullptr)
	{
		FCommandResult R;
		R.bSuccess = true;
		R.Data = InData;
		return R;
	}

	static FCommandResult Error(const FString& Message)
	{
		FCommandResult R;
		R.bSuccess = false;
		R.ErrorMessage = Message;
		return R;
	}
};

/**
 * TCP command server for Arcwright.
 * Listens on localhost:13377 for JSON commands.
 * Dispatches to handlers on the game thread.
 */
class FCommandServer
{
public:
	FCommandServer();
	~FCommandServer();

	/** Start listening. Returns true if the listener bound successfully. */
	bool Start(int32 Port = 13377);

	/** Stop the server and close all connections. */
	void Stop();

	/** Is the server currently listening? */
	bool IsRunning() const { return bRunning; }

	/** Number of currently connected TCP clients */
	int32 GetConnectedClientCount() const
	{
		FScopeLock Lock(const_cast<FCriticalSection*>(&ClientsMutex));
		return ActiveClients.Num();
	}

	/** Seconds since server started listening (0 if not running) */
	double GetServerUptimeSeconds() const
	{
		if (!bRunning || ServerStartTime == FDateTime()) return 0.0;
		return (FDateTime::UtcNow() - ServerStartTime).GetTotalSeconds();
	}

	/** Dispatch a command (public for in-process panel access) */
	FCommandResult DispatchCommand(const FString& Command, const TSharedPtr<FJsonObject>& Params);

	/** Safe dispatch — catches SEH exceptions to prevent editor crash on bad input */
	FCommandResult SafeDispatchCommand(const FString& Command, const TSharedPtr<FJsonObject>& Params);

private:
	// Connection handling
	bool OnConnectionAccepted(FSocket* ClientSocket, const FIPv4Endpoint& ClientEndpoint);
	void ProcessClient(FSocket* ClientSocket);
	FString ReadLine(FSocket* Socket);
	void SendResponse(FSocket* Socket, const FCommandResult& Result);

	// Command handlers
	FCommandResult HandleHealthCheck(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateBlueprint(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleImportFromIR(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetBlueprintInfo(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCompileBlueprint(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleDeleteBlueprint(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateBlueprintFromDSL(const TSharedPtr<FJsonObject>& Params);

	// Level actor commands
	FCommandResult HandleSpawnActorAt(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetActors(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetActorTransform(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleDeleteActor(const TSharedPtr<FJsonObject>& Params);

	// Individual node/connection editing (B5+B6)
	FCommandResult HandleAddNode(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleRemoveNode(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddConnection(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleRemoveConnection(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetNodeParam(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetVariableDefault(const TSharedPtr<FJsonObject>& Params);

	// Component management commands
	FCommandResult HandleAddComponent(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetComponents(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleRemoveComponent(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetComponentProperty(const TSharedPtr<FJsonObject>& Params);

	// Material commands
	FCommandResult HandleCreateMaterialInstance(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateSimpleMaterial(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateTexturedMaterial(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleApplyMaterial(const TSharedPtr<FJsonObject>& Params);

	// Save / level info commands
	FCommandResult HandleSaveAll(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSaveLevel(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetLevelInfo(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleDuplicateBlueprint(const TSharedPtr<FJsonObject>& Params);

	// PIE + log commands
	FCommandResult HandlePlayInEditor(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleStopPlay(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetOutputLog(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandlePlayAndCapture(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleVerifyAllBlueprints(const TSharedPtr<FJsonObject>& Params);

	// Message/diagnosis commands
	FCommandResult HandleGetMessageLog(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleRunMapCheck(const TSharedPtr<FJsonObject>& Params);

	// PIE player control
	FCommandResult HandleTeleportPlayer(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetPlayerLocation(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleLookAt(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetPlayerView(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleTeleportToActor(const TSharedPtr<FJsonObject>& Params);

	// Input mapping commands (B29)
	FCommandResult HandleAddInputAction(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddInputMapping(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetupInputContext(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetInputActions(const TSharedPtr<FJsonObject>& Params);

	// Audio commands (B24)
	FCommandResult HandlePlaySoundAtLocation(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddAudioComponent(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetSoundAssets(const TSharedPtr<FJsonObject>& Params);

	// Viewport commands (B30)
	FCommandResult HandleSetViewportCamera(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleTakeScreenshot(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetPirWidget(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetViewportInfo(const TSharedPtr<FJsonObject>& Params);

	// Niagara commands (B25)
	FCommandResult HandleSpawnNiagaraAtLocation(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddNiagaraComponent(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetNiagaraAssets(const TSharedPtr<FJsonObject>& Params);

	// Behavior Tree commands
	FCommandResult HandleCreateBehaviorTree(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetBehaviorTreeInfo(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetBlackboardKeyDefault(const TSharedPtr<FJsonObject>& Params);

	// Class default properties
	FCommandResult HandleSetClassDefaults(const TSharedPtr<FJsonObject>& Params);

	// Editor lifecycle
	FCommandResult HandleQuitEditor(const TSharedPtr<FJsonObject>& Params);

	// Widget commands (B11)
	FCommandResult HandleCreateWidgetBlueprint(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddWidgetChild(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetWidgetProperty(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetWidgetProperty(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetWidgetTree(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleRemoveWidget(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetViewportWidgets(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleReparentWidgetBlueprint(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleValidateWidgetLayout(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAutoFixWidgetLayout(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetWidgetDesignSize(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleProtectWidgetLayout(const TSharedPtr<FJsonObject>& Params);

	// Widget DSL v2 commands (Phase 2)
	FCommandResult HandleSetWidgetAnchor(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetWidgetBinding(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateWidgetAnimation(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddAnimationTrack(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetWidgetBrush(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetWidgetFont(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandlePreviewWidget(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetWidgetScreenshot(const TSharedPtr<FJsonObject>& Params);

	// Media texture command
	FCommandResult HandleAssignMediaTexture(const TSharedPtr<FJsonObject>& Params);

	// Widget variable / binding commands
	FCommandResult HandleSetWidgetIsVariable(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddWidgetVariable(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetWidgetEntryClass(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddScrollSync(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleBindTextToVariable(const TSharedPtr<FJsonObject>& Params);

	// Font pipeline commands
	FCommandResult HandleImportFontFace(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateFontAsset(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddFontTypeface(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetFontInfo(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleListFontAssets(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleImportFontFamily(const TSharedPtr<FJsonObject>& Params);

	// Asset import commands (B31-B33)
	FCommandResult HandleImportStaticMesh(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleImportTexture(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleImportSound(const TSharedPtr<FJsonObject>& Params);

	// Spline commands (Batch 1.1)
	FCommandResult HandleCreateSplineActor(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddSplinePoint(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetSplineInfo(const TSharedPtr<FJsonObject>& Params);

	// Post-process commands (Batch 1.2)
	FCommandResult HandleAddPostProcessVolume(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetPostProcessSettings(const TSharedPtr<FJsonObject>& Params);

	// Movement defaults (Batch 1.3)
	FCommandResult HandleSetMovementDefaults(const TSharedPtr<FJsonObject>& Params);

	// Physics constraint commands (Batch 1.4)
	FCommandResult HandleAddPhysicsConstraint(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleBreakConstraint(const TSharedPtr<FJsonObject>& Params);

	// Sequencer commands (Batch 2.1)
	FCommandResult HandleCreateSequence(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddSequenceTrack(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddKeyframe(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetSequenceInfo(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandlePlaySequence(const TSharedPtr<FJsonObject>& Params);

	// Landscape/Foliage commands (Batch 2.2)
	FCommandResult HandleGetLandscapeInfo(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetLandscapeMaterial(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateFoliageType(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandlePaintFoliage(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetFoliageInfo(const TSharedPtr<FJsonObject>& Params);

	// AI setup helper
	FCommandResult HandleSetupAIForPawn(const TSharedPtr<FJsonObject>& Params);

	// Data Table commands
	FCommandResult HandleCreateDataTable(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetDataTableInfo(const TSharedPtr<FJsonObject>& Params);

	// Actor-level material (operates on placed actors, not BP templates)
	FCommandResult HandleSetActorMaterial(const TSharedPtr<FJsonObject>& Params);

	// Scene lighting
	FCommandResult HandleSetupSceneLighting(const TSharedPtr<FJsonObject>& Params);

	// Game mode
	FCommandResult HandleSetGameMode(const TSharedPtr<FJsonObject>& Params);

	// Query commands
	FCommandResult HandleFindBlueprints(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleFindActors(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleFindAssets(const TSharedPtr<FJsonObject>& Params);

	// Batch modify commands
	FCommandResult HandleBatchSetVariable(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleBatchAddComponent(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleBatchApplyMaterial(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleBatchSetProperty(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleBatchDeleteActors(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleBatchReplaceMaterial(const TSharedPtr<FJsonObject>& Params);

	// In-place modify commands
	FCommandResult HandleModifyBlueprint(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleRenameAsset(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleReparentBlueprint(const TSharedPtr<FJsonObject>& Params);

	// Phase 2: New commands (v8.1)
	FCommandResult HandleSetCollisionPreset(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetBlueprintDetails(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetCameraProperties(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateInputAction(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleBindInputToBlueprint(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetCollisionShape(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateNavMeshBounds(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetAudioProperties(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetActorTags(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetActorProperties(const TSharedPtr<FJsonObject>& Params);

	// Phase 4: Discovery commands
	FCommandResult HandleListAvailableMaterials(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleListAvailableBlueprints(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetLastError(const TSharedPtr<FJsonObject>& Params);

	// Procedural spawn pattern commands
	FCommandResult HandleSpawnActorGrid(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSpawnActorCircle(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSpawnActorLine(const TSharedPtr<FJsonObject>& Params);

	// Relative transform batch commands
	FCommandResult HandleBatchScaleActors(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleBatchMoveActors(const TSharedPtr<FJsonObject>& Params);

	// Phase 5: Actor config & utility commands
	FCommandResult HandleSetPhysicsEnabled(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetActorVisibility(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetActorMobility(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAttachActorTo(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleDetachActor(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleListProjectAssets(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCopyActor(const TSharedPtr<FJsonObject>& Params);

	// Phase 6: Enhanced Input
	FCommandResult HandleSetPlayerInputMapping(const TSharedPtr<FJsonObject>& Params);

	// Phase 6: Advanced Actor Configuration
	FCommandResult HandleSetActorTick(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetActorLifespan(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetActorBounds(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetActorEnabled(const TSharedPtr<FJsonObject>& Params);

	// Phase 6: Data & Persistence
	FCommandResult HandleCreateSaveGame(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddDataTableRow(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleEditDataTableRow(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetDataTableRows(const TSharedPtr<FJsonObject>& Params);

	// Phase 6: Animation
	FCommandResult HandleCreateAnimBlueprint(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddAnimState(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddAnimTransition(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetAnimStateAnimation(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateAnimMontage(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddMontageSection(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateBlendSpace(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddBlendSpaceSample(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetSkeletalMesh(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandlePlayAnimation(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetSkeletonBones(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetAvailableAnimations(const TSharedPtr<FJsonObject>& Params);

	// Phase 6: Niagara Advanced
	FCommandResult HandleSetNiagaraParameter(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleActivateNiagara(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetNiagaraParameters(const TSharedPtr<FJsonObject>& Params);

	// Phase 6: Level Management
	FCommandResult HandleCreateSublevel(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetLevelVisibility(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetSublevelList(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleMoveActorToSublevel(const TSharedPtr<FJsonObject>& Params);

	// Phase 6: World & Actor Utilities (150 target)
	FCommandResult HandleGetWorldSettings(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetWorldSettings(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetActorClass(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetActorScale(const TSharedPtr<FJsonObject>& Params);

	// Step-by-step Blueprint construction (batch + validation)
	FCommandResult HandleAddNodesBatch(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddConnectionsBatch(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleValidateBlueprint(const TSharedPtr<FJsonObject>& Params);

	// Capability discovery
	FCommandResult HandleGetCapabilities(const TSharedPtr<FJsonObject>& Params);

	// Stats commands
	FCommandResult HandleGetStats(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleResetStats(const TSharedPtr<FJsonObject>& Params);

	// Live preview
	FCommandResult HandleTakeViewportScreenshot(const TSharedPtr<FJsonObject>& Params);

	// Undo/redo
	FCommandResult HandleUndo(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleRedo(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetUndoHistory(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleBeginUndoGroup(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleEndUndoGroup(const TSharedPtr<FJsonObject>& Params);

	// Perception DSL commands
	FCommandResult HandleCreateAIPerception(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddPerceptionSense(const TSharedPtr<FJsonObject>& Params);
	// Physics DSL commands
	FCommandResult HandleCreatePhysicsSetup(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddPhysicsConstraintDSL(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddDestructible(const TSharedPtr<FJsonObject>& Params);
	// Tags DSL commands
	FCommandResult HandleCreateTagHierarchy(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddGameplayTag(const TSharedPtr<FJsonObject>& Params);

	// Generic DSL config commands (shared by 11 systems)
	FCommandResult HandleCreateDSLConfig(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddDSLElement(const TSharedPtr<FJsonObject>& Params);

	// GAS DSL commands
	FCommandResult HandleCreateAbilitySystem(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddAttribute(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddAbility(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddAbilityEffect(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateGASFromDSL(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetAbilityData(const TSharedPtr<FJsonObject>& Params);

	// Sequence DSL commands (builds on existing B28 sequence commands)
	FCommandResult HandleAddSequenceCamera(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddSequenceAudio(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddSequenceFade(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddSequenceEvent(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateSequenceFromDSL(const TSharedPtr<FJsonObject>& Params);

	// Quest DSL commands
	FCommandResult HandleCreateQuest(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddQuestStage(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddQuestObjective(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateQuestFromDSL(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetQuestData(const TSharedPtr<FJsonObject>& Params);

	// Dialogue DSL commands
	FCommandResult HandleCreateDialogue(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddDialogueNode(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateDialogueFromDSL(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetDialogueTree(const TSharedPtr<FJsonObject>& Params);

	// Niagara DSL commands
	FCommandResult HandleTestCreateNiagaraSystem(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateNiagaraSystem(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddNiagaraEmitter(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetNiagaraEmitterParam(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCompileNiagaraSystem(const TSharedPtr<FJsonObject>& Params);

	// Material Graph DSL commands
	FCommandResult HandleTestCreateMaterialGraph(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateMaterial(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddMaterialNode(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleConnectMaterialNodes(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetMaterialOutput(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCompileMaterial(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateMaterialFromDSL(const TSharedPtr<FJsonObject>& Params);

	// Animation Blueprint DSL commands
	FCommandResult HandleTestCreateAnimBlueprint(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateAnimBlueprintDSL(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddStateMachine(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddAnimState2(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddAnimTransition2(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddAnimLayer(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleAddAnimMontage(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateAimOffset(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetAnimNotify(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCompileAnimBlueprint(const TSharedPtr<FJsonObject>& Params);
	// AnimBP helpers
	UAnimBlueprint* FindAnimBlueprintByName(const FString& Name);

	// Full-screen capture (includes UMG/HUD)
	FCommandResult HandleCaptureFullScreen(const TSharedPtr<FJsonObject>& Params);

	// Input simulation for PIE play-testing
	FCommandResult HandleSimulateInput(const TSharedPtr<FJsonObject>& Params);

	// Movement simulation for PIE play-testing
	FCommandResult HandleSimulateWalkTo(const TSharedPtr<FJsonObject>& Params);

	// Audio system commands
	FCommandResult HandleCreateSoundClass(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateSoundMix(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetSoundClassVolume(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateAttenuationSettings(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateAmbientSound(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateAudioVolume(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetReverbSettings(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandlePlaySound2D(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetSoundConcurrency(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreateSoundCue(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleImportAudioFile(const TSharedPtr<FJsonObject>& Params);

	// Blueprint helpers
	UBlueprint* FindBlueprintByName(const FString& Name);
	bool DeleteExistingBlueprint(const FString& Name);
	FCommandResult BuildBlueprintFromIR(struct FDSLBlueprint& DSL);

	// Node/graph helpers
	UEdGraphNode* FindNodeInGraph(UEdGraph* Graph, const FString& NodeId);

	// Component helpers
	UClass* ResolveComponentClass(const FString& FriendlyName);
	USCS_Node* FindSCSNodeByName(USimpleConstructionScript* SCS, const FString& ComponentName);
	bool ApplyComponentProperty(UActorComponent* Template, const FString& PropertyName, const TSharedPtr<FJsonValue>& Value, FString& OutError);

	// Widget helpers
	int32 ComputeLayoutScore(class UWidgetBlueprint* WBP);
	class UWidgetBlueprint* FindWidgetBlueprintByName(const FString& Name);
	class UWidget* FindWidgetByName(class UWidgetBlueprint* WBP, const FString& WidgetName);
	UClass* ResolveWidgetClass(const FString& FriendlyName);
	TSharedPtr<FJsonObject> WidgetToJson(class UWidget* Widget);
	void CollectWidgetChildren(class UWidget* Widget, TArray<TSharedPtr<FJsonValue>>& OutArray, int32 Depth = 0);

	// Material helpers
	UMaterialInterface* ResolveMaterialByName(const FString& NameOrPath, FString& OutResolvedPath, FString& OutError);

	// Level actor helpers
	AActor* FindActorByLabel(const FString& Label);
	UClass* ResolveActorClass(const FString& ClassName);
	FVector JsonToVector(const TSharedPtr<FJsonObject>& Obj);
	FRotator JsonToRotator(const TSharedPtr<FJsonObject>& Obj);
	TSharedPtr<FJsonObject> VectorToJson(const FVector& V);
	TSharedPtr<FJsonObject> RotatorToJson(const FRotator& R);

	// v1.0.4 commands
	FCommandResult HandleBatchSpawnActors(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleApplyMaterialByName(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetLevelPostProcess(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleSetTimeOfDay(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleTeleportPlayerSmooth(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCreatePostProcessVolume(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetActorScreenshot(const TSharedPtr<FJsonObject>& Params);

	// Last error tracking (Phase 4)
	FString LastErrorMessage;
	FString LastErrorCommand;

	FTcpListener* Listener = nullptr;
	bool bRunning = false;
	TArray<FSocket*> ActiveClients;
	FCriticalSection ClientsMutex;
	FDateTime ServerStartTime;

	// PIE atomic flags — checked from Slate OnPostTick callback
	std::atomic<bool> bPIERequested{false};
	FDelegateHandle SlatePostTickHandle;

	// Usage statistics
	TUniquePtr<FArcwrightStats> Stats;

public:
	/** Access stats for panel display */
	FArcwrightStats* GetStats() const { return Stats.Get(); }

private:
	static constexpr int32 DEFAULT_PORT = 13377;
	static const FString SERVER_VERSION;
};
