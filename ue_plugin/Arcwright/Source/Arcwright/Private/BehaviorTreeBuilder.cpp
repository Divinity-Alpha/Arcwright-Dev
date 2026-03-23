#include "BehaviorTreeBuilder.h"
#include "SafeSavePackage.h"

#include "BehaviorTree/BehaviorTree.h"
#include "BehaviorTree/BlackboardData.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Object.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Vector.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Float.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Int.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Bool.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_String.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Rotator.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Name.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Class.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Enum.h"
#include "BehaviorTree/Composites/BTComposite_Selector.h"
#include "BehaviorTree/Composites/BTComposite_Sequence.h"
#include "BehaviorTree/Composites/BTComposite_SimpleParallel.h"
#include "BehaviorTree/Tasks/BTTask_MoveTo.h"
#include "BehaviorTree/Tasks/BTTask_Wait.h"
#include "BehaviorTree/Tasks/BTTask_PlaySound.h"
#include "BehaviorTree/Tasks/BTTask_PlayAnimation.h"
#include "BehaviorTree/Tasks/BTTask_RunBehavior.h"
#include "BehaviorTree/Tasks/BTTask_RotateToFaceBBEntry.h"
#include "BehaviorTree/Tasks/BTTask_BlueprintBase.h"
#include "BehaviorTree/Tasks/BTTask_WaitBlackboardTime.h"
#include "BehaviorTree/Tasks/BTTask_FinishWithResult.h"
#include "BehaviorTree/Tasks/BTTask_SetTagCooldown.h"
#include "BehaviorTree/Decorators/BTDecorator_Blackboard.h"
#include "BehaviorTree/Decorators/BTDecorator_Cooldown.h"
#include "BehaviorTree/Decorators/BTDecorator_Loop.h"
#include "BehaviorTree/Decorators/BTDecorator_TimeLimit.h"
#include "BehaviorTree/Decorators/BTDecorator_ForceSuccess.h"
#include "BehaviorTree/Decorators/BTDecorator_CompareBBEntries.h"
#include "BehaviorTree/Decorators/BTDecorator_ConeCheck.h"
#include "BehaviorTree/Decorators/BTDecorator_DoesPathExist.h"
#include "BehaviorTree/Decorators/BTDecorator_IsAtLocation.h"
#include "BehaviorTree/Decorators/BTDecorator_IsBBEntryOfClass.h"
#include "BehaviorTree/Decorators/BTDecorator_KeepInCone.h"
#include "BehaviorTree/Decorators/BTDecorator_TagCooldown.h"
#include "BehaviorTree/Services/BTService_DefaultFocus.h"
#include "BehaviorTree/Services/BTService_RunEQS.h"
#include "BehaviorTree/Services/BTService_BlueprintBase.h"
#include "BehaviorTree/BehaviorTreeTypes.h"

#include "AssetRegistry/AssetRegistryModule.h"
// UObject/SavePackage.h included via SafeSavePackage.h
#include "Misc/PackageName.h"

DECLARE_LOG_CATEGORY_EXTERN(LogArcwright, Log, All);

// Helper: Set BlackboardKey.SelectedKeyName on any BT node via UProperty reflection.
// BlackboardKey is protected on UBTTask_BlackboardBase, UBTDecorator_BlackboardBase, UBTService_BlackboardBase,
// but is a UPROPERTY(EditAnywhere) so we can access it via the property system.
static void SetBlackboardKeyName(UObject* Node, const FName& KeyName)
{
	FStructProperty* BBKeyProp = nullptr;
	for (TFieldIterator<FStructProperty> It(Node->GetClass()); It; ++It)
	{
		if (It->GetFName() == TEXT("BlackboardKey"))
		{
			BBKeyProp = *It;
			break;
		}
	}
	if (BBKeyProp)
	{
		FBlackboardKeySelector* KeySelector = BBKeyProp->ContainerPtrToValuePtr<FBlackboardKeySelector>(Node);
		if (KeySelector)
		{
			KeySelector->SelectedKeyName = KeyName;
		}
	}
}

// Helper: Set FlowAbortMode on a UBTDecorator via reflection.
static void SetFlowAbortMode(UBTDecorator* Dec, EBTFlowAbortMode::Type Mode)
{
	FByteProperty* AbortProp = nullptr;
	for (TFieldIterator<FByteProperty> It(Dec->GetClass()); It; ++It)
	{
		if (It->GetFName() == TEXT("FlowAbortMode"))
		{
			AbortProp = *It;
			break;
		}
	}
	if (AbortProp)
	{
		AbortProp->SetPropertyValue_InContainer(Dec, (uint8)Mode);
	}
}

// Helper: Set the Interval float property on a UBTService via reflection.
static void SetServiceInterval(UBTService* Svc, float NewInterval)
{
	FFloatProperty* IntervalProp = nullptr;
	for (TFieldIterator<FFloatProperty> It(Svc->GetClass()); It; ++It)
	{
		if (It->GetFName() == TEXT("Interval"))
		{
			IntervalProp = *It;
			break;
		}
	}
	if (IntervalProp)
	{
		IntervalProp->SetPropertyValue_InContainer(Svc, NewInterval);
	}
}

// ============================================================
// CreateFromIR — Main entry point
// ============================================================

FBehaviorTreeBuilder::FBTBuildResult FBehaviorTreeBuilder::CreateFromIR(
	const TSharedPtr<FJsonObject>& IRJson, const FString& PackagePath)
{
	FBTBuildResult Result;

	if (!IRJson.IsValid())
	{
		Result.ErrorMessage = TEXT("IR JSON is null");
		return Result;
	}

	// Parse metadata
	const TSharedPtr<FJsonObject>* MetadataPtr;
	if (!IRJson->TryGetObjectField(TEXT("metadata"), MetadataPtr))
	{
		Result.ErrorMessage = TEXT("Missing 'metadata' in IR");
		return Result;
	}

	FString TreeName = (*MetadataPtr)->GetStringField(TEXT("name"));
	FString BBName = (*MetadataPtr)->GetStringField(TEXT("blackboard"));

	if (TreeName.IsEmpty())
	{
		Result.ErrorMessage = TEXT("Missing tree name in metadata");
		return Result;
	}
	if (BBName.IsEmpty())
	{
		BBName = TreeName.Replace(TEXT("BT_"), TEXT("BB_"));
		if (BBName == TreeName)
		{
			BBName = FString::Printf(TEXT("BB_%s"), *TreeName);
		}
	}

	// Get blackboard keys
	const TArray<TSharedPtr<FJsonValue>>* KeysArray;
	TArray<TSharedPtr<FJsonValue>> EmptyKeys;
	if (!IRJson->TryGetArrayField(TEXT("blackboard_keys"), KeysArray))
	{
		KeysArray = &EmptyKeys;
	}

	// Get tree structure
	const TSharedPtr<FJsonObject>* TreeJsonPtr;
	if (!IRJson->TryGetObjectField(TEXT("tree"), TreeJsonPtr))
	{
		Result.ErrorMessage = TEXT("Missing 'tree' in IR");
		return Result;
	}

	// ── Step 1: Create Blackboard asset ──
	UBlackboardData* BBAsset = CreateBlackboard(BBName, *KeysArray, PackagePath);
	if (!BBAsset)
	{
		Result.ErrorMessage = FString::Printf(TEXT("Failed to create Blackboard: %s"), *BBName);
		return Result;
	}
	Result.BlackboardAssetPath = BBAsset->GetPathName();

	// ── Step 2: Create BehaviorTree asset ──
	FString TreePackagePath = PackagePath / TreeName;
	UPackage* TreePackage = CreatePackage(*TreePackagePath);
	TreePackage->FullyLoad();

	UBehaviorTree* TreeAsset = NewObject<UBehaviorTree>(TreePackage, FName(*TreeName),
		RF_Public | RF_Standalone);
	TreeAsset->BlackboardAsset = BBAsset;

	// ── Step 3: Build node tree ──
	if (!BuildNodeTree(TreeAsset, BBAsset, *TreeJsonPtr, Result))
	{
		Result.ErrorMessage = FString::Printf(TEXT("Failed to build node tree: %s"), *Result.ErrorMessage);
		return Result;
	}

	// ── Step 4: Save assets ──
	FAssetRegistryModule::AssetCreated(TreeAsset);
	TreePackage->MarkPackageDirty();

	FString TreeFilePath = FPackageName::LongPackageNameToFilename(TreePackagePath, FPackageName::GetAssetPackageExtension());
	FSavePackageArgs SaveArgs;
	SaveArgs.TopLevelFlags = RF_Standalone;
	SafeSavePackage(TreePackage, TreeAsset, TreeFilePath, SaveArgs);

	Result.bSuccess = true;
	Result.TreeAssetPath = TreeAsset->GetPathName();

	UE_LOG(LogArcwright, Log, TEXT("BehaviorTree created: %s (%d composites, %d tasks, %d decorators, %d services)"),
		*TreeName, Result.CompositeCount, Result.TaskCount, Result.DecoratorCount, Result.ServiceCount);

	return Result;
}

// ============================================================
// Blackboard Creation
// ============================================================

UBlackboardData* FBehaviorTreeBuilder::CreateBlackboard(
	const FString& Name,
	const TArray<TSharedPtr<FJsonValue>>& Keys,
	const FString& PackagePath)
{
	FString BBPackagePath = PackagePath / Name;
	UPackage* BBPackage = CreatePackage(*BBPackagePath);
	BBPackage->FullyLoad();

	UBlackboardData* BBAsset = NewObject<UBlackboardData>(BBPackage, FName(*Name),
		RF_Public | RF_Standalone);

	// Add keys
	for (const TSharedPtr<FJsonValue>& KeyVal : Keys)
	{
		const TSharedPtr<FJsonObject>& KeyObj = KeyVal->AsObject();
		if (!KeyObj.IsValid()) continue;

		FString KeyName = KeyObj->GetStringField(TEXT("name"));
		FString KeyType = KeyObj->GetStringField(TEXT("type"));

		if (KeyName.IsEmpty()) continue;

		// Resolve key type class
		TSubclassOf<UBlackboardKeyType> KeyTypeClass = nullptr;

		if (KeyType == TEXT("Object"))
			KeyTypeClass = UBlackboardKeyType_Object::StaticClass();
		else if (KeyType == TEXT("Vector"))
			KeyTypeClass = UBlackboardKeyType_Vector::StaticClass();
		else if (KeyType == TEXT("Float"))
			KeyTypeClass = UBlackboardKeyType_Float::StaticClass();
		else if (KeyType == TEXT("Int"))
			KeyTypeClass = UBlackboardKeyType_Int::StaticClass();
		else if (KeyType == TEXT("Bool"))
			KeyTypeClass = UBlackboardKeyType_Bool::StaticClass();
		else if (KeyType == TEXT("String"))
			KeyTypeClass = UBlackboardKeyType_String::StaticClass();
		else if (KeyType == TEXT("Rotator"))
			KeyTypeClass = UBlackboardKeyType_Rotator::StaticClass();
		else if (KeyType == TEXT("Name"))
			KeyTypeClass = UBlackboardKeyType_Name::StaticClass();
		else if (KeyType == TEXT("Class"))
			KeyTypeClass = UBlackboardKeyType_Class::StaticClass();
		else if (KeyType == TEXT("Enum"))
			KeyTypeClass = UBlackboardKeyType_Enum::StaticClass();
		else
		{
			UE_LOG(LogArcwright, Warning, TEXT("Unknown blackboard key type: %s for key %s, defaulting to Object"), *KeyType, *KeyName);
			KeyTypeClass = UBlackboardKeyType_Object::StaticClass();
		}

		FBlackboardEntry NewKey;
		NewKey.EntryName = FName(*KeyName);
		NewKey.KeyType = NewObject<UBlackboardKeyType>(BBAsset, KeyTypeClass);

		BBAsset->Keys.Add(NewKey);

		UE_LOG(LogArcwright, Log, TEXT("  Blackboard key: %s (%s)"), *KeyName, *KeyType);
	}

	// Add the standard "SelfActor" key that AI controllers expect
	{
		FBlackboardEntry SelfKey;
		SelfKey.EntryName = FName(TEXT("SelfActor"));
		SelfKey.KeyType = NewObject<UBlackboardKeyType>(BBAsset, UBlackboardKeyType_Object::StaticClass());
		BBAsset->Keys.Add(SelfKey);
	}

	// Save
	FAssetRegistryModule::AssetCreated(BBAsset);
	BBPackage->MarkPackageDirty();

	FString BBFilePath = FPackageName::LongPackageNameToFilename(BBPackagePath, FPackageName::GetAssetPackageExtension());
	FSavePackageArgs SaveArgs;
	SaveArgs.TopLevelFlags = RF_Standalone;
	SafeSavePackage(BBPackage, BBAsset, BBFilePath, SaveArgs);

	UE_LOG(LogArcwright, Log, TEXT("Blackboard created: %s with %d keys"), *Name, BBAsset->Keys.Num());

	return BBAsset;
}

// ============================================================
// Build Node Tree
// ============================================================

bool FBehaviorTreeBuilder::BuildNodeTree(
	UBehaviorTree* TreeAsset,
	UBlackboardData* BBAsset,
	const TSharedPtr<FJsonObject>& TreeJson,
	FBTBuildResult& OutResult)
{
	// Root must be a composite
	FString RootType = TreeJson->GetStringField(TEXT("dsl_type"));
	if (RootType != TEXT("Selector") && RootType != TEXT("Sequence") && RootType != TEXT("SimpleParallel"))
	{
		OutResult.ErrorMessage = FString::Printf(TEXT("Root must be a composite, got: %s"), *RootType);
		return false;
	}

	UBTCompositeNode* RootNode = CreateCompositeNode(TreeAsset, TreeJson, OutResult);
	if (!RootNode)
	{
		if (OutResult.ErrorMessage.IsEmpty())
			OutResult.ErrorMessage = TEXT("Failed to create root composite node");
		return false;
	}

	TreeAsset->RootNode = RootNode;

	// Root-level services attach directly to the root composite
	const TArray<TSharedPtr<FJsonValue>>* RootServices;
	if (TreeJson->TryGetArrayField(TEXT("services"), RootServices))
	{
		for (const auto& SvcVal : *RootServices)
		{
			UBTService* Svc = CreateServiceNode(TreeAsset, SvcVal->AsObject(), OutResult);
			if (Svc)
			{
				RootNode->Services.Add(Svc);
			}
		}
	}
	// Note: root-level decorators are skipped — decorators live on FBTCompositeChild
	// entries, and the root node has no parent child entry.

	// Process children recursively
	const TArray<TSharedPtr<FJsonValue>>* ChildrenArray;
	if (TreeJson->TryGetArrayField(TEXT("children"), ChildrenArray))
	{
		for (int32 ChildIdx = 0; ChildIdx < ChildrenArray->Num(); ChildIdx++)
		{
			const TSharedPtr<FJsonObject>& ChildJson = (*ChildrenArray)[ChildIdx]->AsObject();
			if (!ChildJson.IsValid()) continue;

			FString ChildCategory = ChildJson->GetStringField(TEXT("dsl_type"));
			FString ChildUEClass = ChildJson->GetStringField(TEXT("ue_class"));

			// Determine if child is composite or task
			bool bIsComposite = ChildUEClass.Contains(TEXT("Composite")) ||
				ChildCategory == TEXT("Selector") ||
				ChildCategory == TEXT("Sequence") ||
				ChildCategory == TEXT("SimpleParallel");

			if (bIsComposite)
			{
				UBTCompositeNode* ChildComposite = CreateCompositeNode(TreeAsset, ChildJson, OutResult);
				if (!ChildComposite) continue;

				// Create the child entry in parent
				FBTCompositeChild& NewChild = RootNode->Children.AddDefaulted_GetRef();
				NewChild.ChildComposite = ChildComposite;

				// Attach decorators to this child entry
				const TArray<TSharedPtr<FJsonValue>>* ChildDecorators;
				if (ChildJson->TryGetArrayField(TEXT("decorators"), ChildDecorators))
				{
					for (const auto& DecVal : *ChildDecorators)
					{
						UBTDecorator* Dec = CreateDecoratorNode(TreeAsset, DecVal->AsObject(), OutResult);
						if (Dec)
						{
							NewChild.Decorators.Add(Dec);
						}
					}
				}

				// Attach services to composite
				const TArray<TSharedPtr<FJsonValue>>* ChildServices;
				if (ChildJson->TryGetArrayField(TEXT("services"), ChildServices))
				{
					for (const auto& SvcVal : *ChildServices)
					{
						UBTService* Svc = CreateServiceNode(TreeAsset, SvcVal->AsObject(), OutResult);
						if (Svc)
						{
							ChildComposite->Services.Add(Svc);
						}
					}
				}

				// Recurse into grandchildren
				const TArray<TSharedPtr<FJsonValue>>* GrandChildren;
				if (ChildJson->TryGetArrayField(TEXT("children"), GrandChildren))
				{
					for (int32 GCIdx = 0; GCIdx < GrandChildren->Num(); GCIdx++)
					{
						const TSharedPtr<FJsonObject>& GCJson = (*GrandChildren)[GCIdx]->AsObject();
						if (!GCJson.IsValid()) continue;

						FString GCUEClass = GCJson->GetStringField(TEXT("ue_class"));
						FString GCType = GCJson->GetStringField(TEXT("dsl_type"));
						bool bGCComposite = GCUEClass.Contains(TEXT("Composite")) ||
							GCType == TEXT("Selector") || GCType == TEXT("Sequence") || GCType == TEXT("SimpleParallel");

						FBTCompositeChild& GCEntry = ChildComposite->Children.AddDefaulted_GetRef();

						if (bGCComposite)
						{
							UBTCompositeNode* GCComposite = CreateCompositeNode(TreeAsset, GCJson, OutResult);
							if (GCComposite)
							{
								GCEntry.ChildComposite = GCComposite;
							}
						}
						else
						{
							UBTTaskNode* GCTask = CreateTaskNode(TreeAsset, GCJson, OutResult);
							if (GCTask)
							{
								GCEntry.ChildTask = GCTask;
							}
						}

						// Attach decorators to grandchild entry
						const TArray<TSharedPtr<FJsonValue>>* GCDecorators;
						if (GCJson->TryGetArrayField(TEXT("decorators"), GCDecorators))
						{
							for (const auto& DecVal : *GCDecorators)
							{
								UBTDecorator* Dec = CreateDecoratorNode(TreeAsset, DecVal->AsObject(), OutResult);
								if (Dec)
								{
									GCEntry.Decorators.Add(Dec);
								}
							}
						}
					}
				}
			}
			else
			{
				// Task child
				UBTTaskNode* ChildTask = CreateTaskNode(TreeAsset, ChildJson, OutResult);
				if (!ChildTask) continue;

				FBTCompositeChild& NewChild = RootNode->Children.AddDefaulted_GetRef();
				NewChild.ChildTask = ChildTask;

				// Attach decorators to this child entry
				const TArray<TSharedPtr<FJsonValue>>* ChildDecorators;
				if (ChildJson->TryGetArrayField(TEXT("decorators"), ChildDecorators))
				{
					for (const auto& DecVal : *ChildDecorators)
					{
						UBTDecorator* Dec = CreateDecoratorNode(TreeAsset, DecVal->AsObject(), OutResult);
						if (Dec)
						{
							NewChild.Decorators.Add(Dec);
						}
					}
				}
			}
		}
	}

	return true;
}

// ============================================================
// Node Creation
// ============================================================

UBTCompositeNode* FBehaviorTreeBuilder::CreateCompositeNode(
	UBehaviorTree* TreeAsset,
	const TSharedPtr<FJsonObject>& NodeJson,
	FBTBuildResult& OutResult)
{
	FString DslType = NodeJson->GetStringField(TEXT("dsl_type"));
	FString NodeName = NodeJson->GetStringField(TEXT("name"));

	UBTCompositeNode* Node = nullptr;

	if (DslType == TEXT("Selector"))
	{
		Node = NewObject<UBTComposite_Selector>(TreeAsset);
	}
	else if (DslType == TEXT("Sequence"))
	{
		Node = NewObject<UBTComposite_Sequence>(TreeAsset);
	}
	else if (DslType == TEXT("SimpleParallel"))
	{
		Node = NewObject<UBTComposite_SimpleParallel>(TreeAsset);
	}

	if (Node)
	{
		Node->NodeName = NodeName;
		OutResult.CompositeCount++;
		UE_LOG(LogArcwright, Log, TEXT("  Composite: %s (%s)"), *NodeName, *DslType);
	}

	return Node;
}

UBTTaskNode* FBehaviorTreeBuilder::CreateTaskNode(
	UBehaviorTree* TreeAsset,
	const TSharedPtr<FJsonObject>& NodeJson,
	FBTBuildResult& OutResult)
{
	FString DslType = NodeJson->GetStringField(TEXT("dsl_type"));
	const TSharedPtr<FJsonObject>* ParamsPtr;
	TSharedPtr<FJsonObject> Params;
	if (NodeJson->TryGetObjectField(TEXT("params"), ParamsPtr))
	{
		Params = *ParamsPtr;
	}
	else
	{
		Params = MakeShareable(new FJsonObject());
	}

	UBTTaskNode* Node = nullptr;

	if (DslType == TEXT("MoveTo"))
	{
		UBTTask_MoveTo* MoveNode = NewObject<UBTTask_MoveTo>(TreeAsset);
		if (Params->HasField(TEXT("AcceptableRadius")))
		{
			MoveNode->AcceptableRadius = (float)Params->GetNumberField(TEXT("AcceptableRadius"));
		}
		Node = MoveNode;
	}
	else if (DslType == TEXT("Wait"))
	{
		UBTTask_Wait* WaitNode = NewObject<UBTTask_Wait>(TreeAsset);
		if (Params->HasField(TEXT("Duration")))
		{
			WaitNode->WaitTime = (float)Params->GetNumberField(TEXT("Duration"));
		}
		if (Params->HasField(TEXT("RandomDeviation")))
		{
			WaitNode->RandomDeviation = (float)Params->GetNumberField(TEXT("RandomDeviation"));
		}
		Node = WaitNode;
	}
	else if (DslType == TEXT("RotateToFaceBBEntry"))
	{
		Node = NewObject<UBTTask_RotateToFaceBBEntry>(TreeAsset);
	}
	else if (DslType == TEXT("WaitBlackboardTime"))
	{
		Node = NewObject<UBTTask_WaitBlackboardTime>(TreeAsset);
	}
	else if (DslType == TEXT("FinishWithResult"))
	{
		Node = NewObject<UBTTask_FinishWithResult>(TreeAsset);
	}
	else
	{
		// Custom or unknown task — use BlueprintBase as placeholder
		Node = NewObject<UBTTask_Wait>(TreeAsset);
		UE_LOG(LogArcwright, Warning, TEXT("  Task '%s' mapped to Wait (custom tasks need Blueprint implementation)"), *DslType);
	}

	if (Node)
	{
		Node->NodeName = DslType;

		// Set blackboard key for tasks that use them (via property reflection)
		if (Params->HasField(TEXT("Key")))
		{
			SetBlackboardKeyName(Node, FName(*Params->GetStringField(TEXT("Key"))));
		}

		OutResult.TaskCount++;
		UE_LOG(LogArcwright, Log, TEXT("  Task: %s"), *DslType);
	}

	return Node;
}

UBTDecorator* FBehaviorTreeBuilder::CreateDecoratorNode(
	UBehaviorTree* TreeAsset,
	const TSharedPtr<FJsonObject>& NodeJson,
	FBTBuildResult& OutResult)
{
	if (!NodeJson.IsValid()) return nullptr;

	FString DslType = NodeJson->GetStringField(TEXT("dsl_type"));
	const TSharedPtr<FJsonObject>* ParamsPtr;
	TSharedPtr<FJsonObject> Params;
	if (NodeJson->TryGetObjectField(TEXT("params"), ParamsPtr))
	{
		Params = *ParamsPtr;
	}
	else
	{
		Params = MakeShareable(new FJsonObject());
	}

	UBTDecorator* Node = nullptr;

	if (DslType == TEXT("BlackboardBased"))
	{
		UBTDecorator_Blackboard* BBDec = NewObject<UBTDecorator_Blackboard>(TreeAsset);

		if (Params->HasField(TEXT("Key")))
		{
			SetBlackboardKeyName(BBDec, FName(*Params->GetStringField(TEXT("Key"))));
		}

		// Set flow abort mode via reflection (protected property)
		FString AbortStr = Params->GetStringField(TEXT("AbortMode"));
		if (AbortStr == TEXT("LowerPriority"))
			SetFlowAbortMode(BBDec, EBTFlowAbortMode::LowerPriority);
		else if (AbortStr == TEXT("Self"))
			SetFlowAbortMode(BBDec, EBTFlowAbortMode::Self);
		else if (AbortStr == TEXT("Both"))
			SetFlowAbortMode(BBDec, EBTFlowAbortMode::Both);
		else
			SetFlowAbortMode(BBDec, EBTFlowAbortMode::None);

		Node = BBDec;
	}
	else if (DslType == TEXT("Cooldown"))
	{
		UBTDecorator_Cooldown* CoolDec = NewObject<UBTDecorator_Cooldown>(TreeAsset);
		if (Params->HasField(TEXT("Duration")))
		{
			CoolDec->CoolDownTime = (float)Params->GetNumberField(TEXT("Duration"));
		}
		Node = CoolDec;
	}
	else if (DslType == TEXT("Loop"))
	{
		UBTDecorator_Loop* LoopDec = NewObject<UBTDecorator_Loop>(TreeAsset);
		if (Params->HasField(TEXT("NumLoops")))
		{
			LoopDec->NumLoops = (int32)Params->GetNumberField(TEXT("NumLoops"));
		}
		if (Params->HasField(TEXT("InfiniteLoop")))
		{
			LoopDec->bInfiniteLoop = Params->GetBoolField(TEXT("InfiniteLoop"));
		}
		Node = LoopDec;
	}
	else if (DslType == TEXT("TimeLimit"))
	{
		UBTDecorator_TimeLimit* TimeDec = NewObject<UBTDecorator_TimeLimit>(TreeAsset);
		if (Params->HasField(TEXT("Duration")))
		{
			TimeDec->TimeLimit = (float)Params->GetNumberField(TEXT("Duration"));
		}
		Node = TimeDec;
	}
	else if (DslType == TEXT("ForceSuccess"))
	{
		Node = NewObject<UBTDecorator_ForceSuccess>(TreeAsset);
	}
	else if (DslType == TEXT("IsAtLocation"))
	{
		UBTDecorator_IsAtLocation* LocDec = NewObject<UBTDecorator_IsAtLocation>(TreeAsset);
		if (Params->HasField(TEXT("Key")))
		{
			SetBlackboardKeyName(LocDec, FName(*Params->GetStringField(TEXT("Key"))));
		}
		if (Params->HasField(TEXT("AcceptableRadius")))
		{
			LocDec->AcceptableRadius = (float)Params->GetNumberField(TEXT("AcceptableRadius"));
		}
		Node = LocDec;
	}
	else
	{
		// Unknown decorator — create a ForceSuccess placeholder
		Node = NewObject<UBTDecorator_ForceSuccess>(TreeAsset);
		UE_LOG(LogArcwright, Warning, TEXT("  Decorator '%s' not mapped — using ForceSuccess placeholder"), *DslType);
	}

	if (Node)
	{
		Node->NodeName = DslType;
		OutResult.DecoratorCount++;
		UE_LOG(LogArcwright, Log, TEXT("  Decorator: %s"), *DslType);
	}

	return Node;
}

UBTService* FBehaviorTreeBuilder::CreateServiceNode(
	UBehaviorTree* TreeAsset,
	const TSharedPtr<FJsonObject>& NodeJson,
	FBTBuildResult& OutResult)
{
	if (!NodeJson.IsValid()) return nullptr;

	FString DslType = NodeJson->GetStringField(TEXT("dsl_type"));
	const TSharedPtr<FJsonObject>* ParamsPtr;
	TSharedPtr<FJsonObject> Params;
	if (NodeJson->TryGetObjectField(TEXT("params"), ParamsPtr))
	{
		Params = *ParamsPtr;
	}
	else
	{
		Params = MakeShareable(new FJsonObject());
	}

	UBTService* Node = nullptr;

	if (DslType == TEXT("DefaultFocus"))
	{
		UBTService_DefaultFocus* FocusSvc = NewObject<UBTService_DefaultFocus>(TreeAsset);
		if (Params->HasField(TEXT("Key")))
		{
			SetBlackboardKeyName(FocusSvc, FName(*Params->GetStringField(TEXT("Key"))));
		}
		Node = FocusSvc;
	}
	else
	{
		// Unknown service — create a DefaultFocus placeholder
		Node = NewObject<UBTService_DefaultFocus>(TreeAsset);
		UE_LOG(LogArcwright, Warning, TEXT("  Service '%s' not mapped — using DefaultFocus placeholder"), *DslType);
	}

	if (Node)
	{
		Node->NodeName = DslType;

		if (Params->HasField(TEXT("Interval")))
		{
			SetServiceInterval(Node, (float)Params->GetNumberField(TEXT("Interval")));
		}

		OutResult.ServiceCount++;
		UE_LOG(LogArcwright, Log, TEXT("  Service: %s"), *DslType);
	}

	return Node;
}

// ============================================================
// GetBehaviorTreeInfo
// ============================================================

UBehaviorTree* FBehaviorTreeBuilder::FindBehaviorTreeByName(const FString& Name)
{
	// Search common paths
	TArray<FString> SearchPaths = {
		FString::Printf(TEXT("/Game/BlueprintLLM/BehaviorTrees/%s.%s"), *Name, *Name),
		FString::Printf(TEXT("/Game/BehaviorTrees/%s.%s"), *Name, *Name),
		FString::Printf(TEXT("/Game/AI/%s.%s"), *Name, *Name),
	};

	for (const FString& Path : SearchPaths)
	{
		UBehaviorTree* BT = LoadObject<UBehaviorTree>(nullptr, *Path);
		if (BT) return BT;
	}

	// Fallback: asset registry search
	FAssetRegistryModule& ARM = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	TArray<FAssetData> AssetList;
	ARM.Get().GetAssetsByClass(UBehaviorTree::StaticClass()->GetClassPathName(), AssetList);

	for (const FAssetData& Asset : AssetList)
	{
		if (Asset.AssetName.ToString() == Name)
		{
			return Cast<UBehaviorTree>(Asset.GetAsset());
		}
	}

	return nullptr;
}

TSharedPtr<FJsonObject> FBehaviorTreeBuilder::GetBehaviorTreeInfo(const FString& Name)
{
	UBehaviorTree* BT = FindBehaviorTreeByName(Name);
	if (!BT)
	{
		return nullptr;
	}

	TSharedPtr<FJsonObject> Info = MakeShareable(new FJsonObject());
	Info->SetStringField(TEXT("name"), BT->GetName());
	Info->SetStringField(TEXT("asset_path"), BT->GetPathName());

	// Blackboard info
	if (BT->BlackboardAsset)
	{
		Info->SetStringField(TEXT("blackboard_name"), BT->BlackboardAsset->GetName());
		Info->SetStringField(TEXT("blackboard_path"), BT->BlackboardAsset->GetPathName());

		TArray<TSharedPtr<FJsonValue>> KeysArray;
		for (const FBlackboardEntry& Key : BT->BlackboardAsset->Keys)
		{
			TSharedPtr<FJsonObject> KeyObj = MakeShareable(new FJsonObject());
			KeyObj->SetStringField(TEXT("name"), Key.EntryName.ToString());
			KeyObj->SetStringField(TEXT("type"), Key.KeyType ? Key.KeyType->GetClass()->GetName() : TEXT("Unknown"));
			KeysArray.Add(MakeShareable(new FJsonValueObject(KeyObj)));
		}
		Info->SetArrayField(TEXT("blackboard_keys"), KeysArray);
		Info->SetNumberField(TEXT("blackboard_key_count"), BT->BlackboardAsset->Keys.Num());
	}

	// Node counts
	int32 Composites = 0, Tasks = 0, Decorators = 0, Services = 0;

	TFunction<void(UBTCompositeNode*)> CountNodes = [&](UBTCompositeNode* Composite)
	{
		if (!Composite) return;
		Composites++;
		Services += Composite->Services.Num();

		for (const FBTCompositeChild& Child : Composite->Children)
		{
			Decorators += Child.Decorators.Num();

			if (Child.ChildComposite)
			{
				CountNodes(Child.ChildComposite);
			}
			else if (Child.ChildTask)
			{
				Tasks++;
				Services += Child.ChildTask->Services.Num();
			}
		}
	};

	CountNodes(BT->RootNode);

	Info->SetNumberField(TEXT("composite_count"), Composites);
	Info->SetNumberField(TEXT("task_count"), Tasks);
	Info->SetNumberField(TEXT("decorator_count"), Decorators);
	Info->SetNumberField(TEXT("service_count"), Services);
	Info->SetNumberField(TEXT("total_node_count"), Composites + Tasks + Decorators + Services);
	Info->SetBoolField(TEXT("has_root"), BT->RootNode != nullptr);

	return Info;
}
