// Copyright 2026 Divinity Alpha. All Rights Reserved.
#include "BlueprintBuilder.h"
#include "SafeSavePackage.h"

#include "Engine/Blueprint.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "K2Node_Event.h"
#include "K2Node_CustomEvent.h"
#include "K2Node_CallFunction.h"
#include "K2Node_IfThenElse.h"
#include "K2Node_ExecutionSequence.h"
#include "K2Node_InputAction.h"
#include "K2Node_InputAxisEvent.h"
#include "K2Node_DynamicCast.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "K2Node_SpawnActorFromClass.h"
#include "K2Node_SwitchInteger.h"
#include "K2Node_SwitchString.h"
#include "K2Node_BreakStruct.h"
#include "EdGraphSchema_K2.h"
#include "Factories/BlueprintFactory.h"
#include "AssetRegistry/AssetRegistryModule.h"
// UObject/SavePackage.h included via SafeSavePackage.h
#include "GameFramework/Actor.h"
#include "GameFramework/Character.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "AIController.h"
#include "GameFramework/GameModeBase.h"
#include "K2Node_MacroInstance.h"
#include "K2Node_MultiGate.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Kismet/KismetMathLibrary.h"
#include "Blueprint/UserWidget.h"
#include "UObject/ObjectRedirector.h"

UBlueprint* FBlueprintBuilder::CreateBlueprint(const FDSLBlueprint& DSL, const FString& PackagePath)
{
	// 1. Resolve parent class
	UClass* ParentClass = FindParentClass(DSL.ParentClass);
	if (!ParentClass)
	{
		UE_LOG(LogTemp, Error, TEXT("Arcwright: Unknown parent class: %s, defaulting to AActor"), *DSL.ParentClass);
		ParentClass = AActor::StaticClass();
	}

	// 2. Create package
	const FString AssetName = DSL.Name.IsEmpty() ? TEXT("BP_Generated") : DSL.Name;
	const FString FullPath = PackagePath / AssetName;
	UPackage* Package = CreatePackage(*FullPath);
	if (!Package)
	{
		UE_LOG(LogTemp, Error, TEXT("Arcwright: Failed to create package: %s"), *FullPath);
		return nullptr;
	}

	// 2.5 Remove any existing ObjectRedirector left by ForceDeleteObjects
	// When delete_blueprint is called, UE replaces the asset with an ObjectRedirector.
	// FactoryCreateNew fatally crashes if it finds a redirector at the target path.
	UObject* ExistingObj = StaticFindObject(UObject::StaticClass(), Package, *AssetName);
	if (ExistingObj)
	{
		if (Cast<UObjectRedirector>(ExistingObj))
		{
			UE_LOG(LogTemp, Warning, TEXT("Arcwright: Removing ObjectRedirector at %s before creating Blueprint"), *FullPath);
			ExistingObj->Rename(nullptr, GetTransientPackage(), REN_DontCreateRedirectors | REN_NonTransactional);
			ExistingObj->MarkAsGarbage();
		}
		else if (UBlueprint* ExistingBP = Cast<UBlueprint>(ExistingObj))
		{
			UE_LOG(LogTemp, Warning, TEXT("Arcwright: Removing existing Blueprint at %s before recreation"), *FullPath);
			ExistingBP->Rename(nullptr, GetTransientPackage(), REN_DontCreateRedirectors | REN_NonTransactional);
			ExistingBP->MarkAsGarbage();
		}
	}

	// 3. Create Blueprint via factory
	UBlueprintFactory* Factory = NewObject<UBlueprintFactory>();
	Factory->ParentClass = ParentClass;

	UBlueprint* Blueprint = Cast<UBlueprint>(
		Factory->FactoryCreateNew(
			UBlueprint::StaticClass(),
			Package,
			FName(*AssetName),
			RF_Public | RF_Standalone,
			nullptr,
			GWarn
		)
	);

	if (!Blueprint)
	{
		UE_LOG(LogTemp, Error, TEXT("Arcwright: Failed to create Blueprint"));
		return nullptr;
	}

	// 4. Create variables
	CreateBlueprintVariables(Blueprint, DSL.Variables);

	// 4.5 Compile skeleton so VariableGet/VariableSet nodes can resolve typed pins
	// (without this, variable pins stay as wildcard and KismetArrayLibrary functions fail)
	if (DSL.Variables.Num() > 0)
	{
		FKismetEditorUtilities::CompileBlueprint(Blueprint);
	}

	// 5. Get or create EventGraph
	UEdGraph* EventGraph = FBlueprintEditorUtils::FindEventGraph(Blueprint);
	if (!EventGraph)
	{
		UE_LOG(LogTemp, Error, TEXT("Arcwright: No EventGraph found"));
		return nullptr;
	}

	// 5.5 Pre-scan: identify CustomEvent nodes that should be calls (not definitions)
	// When the same CustomEvent name appears twice, one is the definition (has outgoing exec)
	// and the other is the call (receives incoming exec from another node).
	TSet<FString> CustomEventCallNodeIDs;
	{
		TMap<FString, TArray<FString>> EventNameToNodeIDs;
		for (const FDSLNode& NodeDef : DSL.Nodes)
		{
			if (NodeDef.UEClass == TEXT("UK2Node_CustomEvent"))
			{
				FString EvtName = TEXT("CustomEvent");
				if (!NodeDef.ParamKey.IsEmpty() && NodeDef.Params.Contains(NodeDef.ParamKey))
					EvtName = NodeDef.Params[NodeDef.ParamKey];
				else if (NodeDef.Params.Contains(TEXT("EventName")))
					EvtName = NodeDef.Params[TEXT("EventName")];
				EventNameToNodeIDs.FindOrAdd(EvtName).Add(NodeDef.ID);
			}
		}
		for (auto& KV : EventNameToNodeIDs)
		{
			if (KV.Value.Num() < 2) continue;
			for (const FString& NodeID : KV.Value)
			{
				for (const FDSLConnection& Conn : DSL.Connections)
				{
					if (Conn.TargetNode == NodeID && Conn.Type == TEXT("exec"))
					{
						CustomEventCallNodeIDs.Add(NodeID);
						break;
					}
				}
			}
		}
	}

	// 6. Create all nodes (two passes if CustomEvent calls exist)
	// Pass 1: create all nodes EXCEPT CustomEvent calls (definitions must exist first)
	TMap<FString, UEdGraphNode*> NodeMap;
	for (const FDSLNode& NodeDef : DSL.Nodes)
	{
		if (CustomEventCallNodeIDs.Contains(NodeDef.ID)) continue;

		UK2Node* NewNode = CreateNodeFromDef(Blueprint, EventGraph, NodeDef);
		if (NewNode)
		{
			NewNode->CreateNewGuid();
			SetNodePosition(NewNode, NodeDef.Position);
			NodeMap.Add(NodeDef.ID, NewNode);
		}
		else
		{
			UE_LOG(LogTemp, Warning, TEXT("Arcwright: Failed to create node %s (%s / %s)"),
				*NodeDef.ID, *NodeDef.DSLType, *NodeDef.UEClass);
		}
	}

	// Pass 1.5: compile so CustomEvent functions are registered for CallFunction resolution
	if (CustomEventCallNodeIDs.Num() > 0)
	{
		FKismetEditorUtilities::CompileBlueprint(Blueprint);
	}

	// Pass 2: create CustomEvent call nodes (now the function is registered)
	for (const FDSLNode& NodeDef : DSL.Nodes)
	{
		if (!CustomEventCallNodeIDs.Contains(NodeDef.ID)) continue;

		FString EventName = TEXT("CustomEvent");
		if (!NodeDef.ParamKey.IsEmpty() && NodeDef.Params.Contains(NodeDef.ParamKey))
			EventName = NodeDef.Params[NodeDef.ParamKey];
		else if (NodeDef.Params.Contains(TEXT("EventName")))
			EventName = NodeDef.Params[TEXT("EventName")];

		UK2Node_CallFunction* CallNode = NewObject<UK2Node_CallFunction>(EventGraph);
		CallNode->FunctionReference.SetSelfMember(FName(*EventName));
		CallNode->AllocateDefaultPins();
		EventGraph->AddNode(CallNode, false, false);

		UE_LOG(LogTemp, Log, TEXT("Arcwright: CustomEvent '%s' node %s created as call (exec pins: %d)"),
			*EventName, *NodeDef.ID, CallNode->Pins.Num());

		CallNode->CreateNewGuid();
		SetNodePosition(CallNode, NodeDef.Position);
		NodeMap.Add(NodeDef.ID, CallNode);
	}

	// 7. Wire connections
	ConnectPins(NodeMap, DSL.Connections);

	// 7.5 Post-wiring: propagate wildcard pin types from connected typed pins
	// KismetArrayLibrary functions (Array_Add, Array_Contains, etc.) use wildcard pins
	// that must be resolved to concrete types for compilation to succeed.
	// Iterate all nodes: if a wildcard pin has a typed connection, adopt that type
	// and propagate to ALL wildcard pins on the same node (same wildcard group).
	for (auto& Pair : NodeMap)
	{
		UEdGraphNode* Node = Pair.Value;

		// First pass: find a resolved type from any connected wildcard pin
		FEdGraphPinType ResolvedType;
		bool bHasResolvedType = false;
		for (UEdGraphPin* Pin : Node->Pins)
		{
			if (Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Wildcard && Pin->LinkedTo.Num() > 0)
			{
				for (UEdGraphPin* LinkedPin : Pin->LinkedTo)
				{
					if (LinkedPin->PinType.PinCategory != UEdGraphSchema_K2::PC_Wildcard
						&& !LinkedPin->PinType.PinCategory.IsNone())
					{
						ResolvedType = LinkedPin->PinType;
						bHasResolvedType = true;
						break;
					}
				}
				if (bHasResolvedType) break;
			}
		}

		// Second pass: apply resolved type to all wildcard pins
		if (bHasResolvedType)
		{
			// Determine the element type (non-array version) for non-container pins
			FEdGraphPinType ElementType = ResolvedType;
			ElementType.ContainerType = EPinContainerType::None;

			for (UEdGraphPin* Pin : Node->Pins)
			{
				if (Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Wildcard)
				{
					// Array-typed wildcard pins keep container type, non-array get element type
					if (Pin->PinType.ContainerType == EPinContainerType::Array)
					{
						Pin->PinType = ResolvedType;
						// Ensure it stays an array
						Pin->PinType.ContainerType = EPinContainerType::Array;
					}
					else
					{
						Pin->PinType = ElementType;
					}
					UE_LOG(LogTemp, Log, TEXT("Arcwright: Resolved wildcard pin '%s' on '%s' to %s (container=%d)"),
						*Pin->PinName.ToString(), *Node->GetNodeTitle(ENodeTitleType::ListView).ToString(),
						*Pin->PinType.PinCategory.ToString(), (int32)Pin->PinType.ContainerType);
				}
			}

			// Notify the node that pin types changed
			Node->GetGraph()->NotifyGraphChanged();
		}
	}

	// 8. Compile
	FBlueprintEditorUtils::MarkBlueprintAsModified(Blueprint);
	FKismetEditorUtilities::CompileBlueprint(Blueprint);

	// 9. Save
	Package->MarkPackageDirty();
	FAssetRegistryModule::AssetCreated(Blueprint);

	const FString PackageFilename = FPackageName::LongPackageNameToFilename(FullPath, FPackageName::GetAssetPackageExtension());
	FSavePackageArgs SaveArgs;
	SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
	SafeSavePackage(Package, Blueprint, PackageFilename, SaveArgs);

	UE_LOG(LogTemp, Log, TEXT("Arcwright: Successfully created %s with %d nodes"),
		*AssetName, NodeMap.Num());

	return Blueprint;
}

// ============================================================
// Node creation dispatch
// ============================================================

UK2Node* FBlueprintBuilder::CreateNodeFromDef(UBlueprint* BP, UEdGraph* Graph, const FDSLNode& NodeDef)
{
	const FString& UEClass = NodeDef.UEClass;

	if (UEClass == TEXT("UK2Node_Event"))
	{
		return CreateEventNode(BP, Graph, NodeDef);
	}
	if (UEClass == TEXT("UK2Node_CustomEvent"))
	{
		return CreateCustomEventNode(BP, Graph, NodeDef);
	}
	if (UEClass == TEXT("UK2Node_CallFunction"))
	{
		return CreateCallFunctionNode(BP, Graph, NodeDef);
	}
	if (UEClass == TEXT("UK2Node_IfThenElse"))
	{
		return CreateBranchNode(BP, Graph, NodeDef);
	}
	if (UEClass == TEXT("UK2Node_ExecutionSequence"))
	{
		return CreateSequenceNode(BP, Graph, NodeDef);
	}
	if (UEClass == TEXT("UK2Node_ForLoop") || UEClass == TEXT("UK2Node_ForEachLoop") || UEClass == TEXT("UK2Node_WhileLoop"))
	{
		return CreateLoopNode(BP, Graph, NodeDef);
	}
	if (UEClass == TEXT("UK2Node_DynamicCast"))
	{
		return CreateCastNode(BP, Graph, NodeDef);
	}
	if (UEClass == TEXT("UK2Node_VariableGet") || UEClass == TEXT("UK2Node_VariableSet"))
	{
		return CreateVariableNode(BP, Graph, NodeDef);
	}
	if (UEClass == TEXT("UK2Node_SpawnActorFromClass"))
	{
		return CreateSpawnActorNode(BP, Graph, NodeDef);
	}
	if (UEClass == TEXT("UK2Node_SwitchInteger") || UEClass == TEXT("UK2Node_SwitchString"))
	{
		return CreateSwitchNode(BP, Graph, NodeDef);
	}
	if (UEClass == TEXT("UK2Node_BreakStruct"))
	{
		return CreateBreakStructNode(BP, Graph, NodeDef);
	}
	if (UEClass == TEXT("UK2Node_InputAction"))
	{
		// Input action events
		UK2Node_InputAction* Node = NewObject<UK2Node_InputAction>(Graph);
		if (NodeDef.Params.Contains(TEXT("ActionName")))
		{
			Node->InputActionName = FName(*NodeDef.Params[TEXT("ActionName")]);
		}
		Node->AllocateDefaultPins();
		Graph->AddNode(Node, false, false);
		return Node;
	}
	if (UEClass == TEXT("UK2Node_InputAxisEvent"))
	{
		// Input axis events — fire every frame with axis value (for WASD movement, mouse look)
		UK2Node_InputAxisEvent* Node = NewObject<UK2Node_InputAxisEvent>(Graph);
		if (NodeDef.Params.Contains(TEXT("InputAxisName")))
		{
			Node->InputAxisName = FName(*NodeDef.Params[TEXT("InputAxisName")]);
		}
		Node->bConsumeInput = true;
		Node->bOverrideParentBinding = true;
		Node->AllocateDefaultPins();
		Graph->AddNode(Node, false, false);

		UE_LOG(LogTemp, Log, TEXT("Arcwright: Created InputAxisEvent '%s' with pins:"), *Node->InputAxisName.ToString());
		for (UEdGraphPin* P : Node->Pins)
		{
			FString PDir = (P->Direction == EGPD_Input) ? TEXT("IN") : TEXT("OUT");
			UE_LOG(LogTemp, Log, TEXT("  [%s] '%s' (%s)"), *PDir, *P->PinName.ToString(), *P->PinType.PinCategory.ToString());
		}
		return Node;
	}

	// Flow control nodes (FlipFlop, DoOnce, Gate, MultiGate)
	if (UEClass == TEXT("UK2Node_FlipFlop") || UEClass == TEXT("UK2Node_DoOnce") ||
		UEClass == TEXT("UK2Node_Gate") || UEClass == TEXT("UK2Node_MultiGate"))
	{
		return CreateFlowControlNode(BP, Graph, NodeDef);
	}

	UE_LOG(LogTemp, Warning, TEXT("Arcwright: Unhandled UE class: %s"), *UEClass);
	return nullptr;
}

// ============================================================
// Individual node creators
// ============================================================

UK2Node* FBlueprintBuilder::CreateEventNode(UBlueprint* BP, UEdGraph* Graph, const FDSLNode& NodeDef)
{
	// Check if this event already exists in the graph (BeginPlay, Tick, etc.)
	FName EventName = FName(*NodeDef.UEEvent);

	for (UEdGraphNode* ExistingNode : Graph->Nodes)
	{
		UK2Node_Event* ExistingEvent = Cast<UK2Node_Event>(ExistingNode);
		if (ExistingEvent && ExistingEvent->EventReference.GetMemberName() == EventName)
		{
			return ExistingEvent;
		}
	}

	// Create new event node
	UK2Node_Event* EventNode = NewObject<UK2Node_Event>(Graph);
	UClass* ParentClass = BP->ParentClass;

	// Find the function in the parent class
	UFunction* EventFunc = ParentClass->FindFunctionByName(EventName);
	if (EventFunc)
	{
		EventNode->EventReference.SetFromField<UFunction>(EventFunc, false);
		EventNode->bOverrideFunction = true;
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("Arcwright: Event function not found: %s"), *NodeDef.UEEvent);
	}

	EventNode->AllocateDefaultPins();
	Graph->AddNode(EventNode, false, false);

	return EventNode;
}

UK2Node* FBlueprintBuilder::CreateCustomEventNode(UBlueprint* BP, UEdGraph* Graph, const FDSLNode& NodeDef)
{
	FString EventName = TEXT("CustomEvent");
	if (!NodeDef.ParamKey.IsEmpty() && NodeDef.Params.Contains(NodeDef.ParamKey))
	{
		EventName = NodeDef.Params[NodeDef.ParamKey];
	}
	else if (NodeDef.Params.Contains(TEXT("EventName")))
	{
		EventName = NodeDef.Params[TEXT("EventName")];
	}

	// Check if a CustomEvent with this name already exists — if so, create a CallFunction
	// to call it instead of duplicating the event definition
	for (UEdGraphNode* ExistingNode : Graph->Nodes)
	{
		UK2Node_CustomEvent* ExistingEvent = Cast<UK2Node_CustomEvent>(ExistingNode);
		if (ExistingEvent && ExistingEvent->CustomFunctionName == FName(*EventName))
		{
			UK2Node_CallFunction* CallNode = NewObject<UK2Node_CallFunction>(Graph);
			CallNode->FunctionReference.SetSelfMember(FName(*EventName));
			CallNode->AllocateDefaultPins();
			Graph->AddNode(CallNode, false, false);
			UE_LOG(LogTemp, Log, TEXT("Arcwright: CustomEvent '%s' already exists, created CallFunction instead"), *EventName);
			return CallNode;
		}
	}

	UK2Node_CustomEvent* Node = NewObject<UK2Node_CustomEvent>(Graph);
	Node->CustomFunctionName = FName(*EventName);
	Node->AllocateDefaultPins();
	Graph->AddNode(Node, false, false);

	// Add typed output pins for event parameters (e.g., Amount:Float, Points:Int)
	for (const FDSLEventParam& Param : NodeDef.EventParams)
	{
		FEdGraphPinType PinType;
		FString TypeUpper = Param.Type.ToUpper();
		if (TypeUpper == TEXT("FLOAT") || TypeUpper == TEXT("DOUBLE") || TypeUpper == TEXT("REAL"))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_Real;
			PinType.PinSubCategory = UEdGraphSchema_K2::PC_Double;
		}
		else if (TypeUpper == TEXT("INT") || TypeUpper == TEXT("INTEGER") || TypeUpper == TEXT("INT32"))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_Int;
		}
		else if (TypeUpper == TEXT("BOOL") || TypeUpper == TEXT("BOOLEAN"))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
		}
		else if (TypeUpper == TEXT("STRING"))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_String;
		}
		else if (TypeUpper == TEXT("NAME"))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_Name;
		}
		else if (TypeUpper == TEXT("VECTOR"))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
			PinType.PinSubCategoryObject = TBaseStructure<FVector>::Get();
		}
		else if (TypeUpper == TEXT("ROTATOR"))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
			PinType.PinSubCategoryObject = TBaseStructure<FRotator>::Get();
		}
		else if (TypeUpper == TEXT("TEXT"))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_Text;
		}
		else
		{
			// Default to string for unknown types
			PinType.PinCategory = UEdGraphSchema_K2::PC_String;
			UE_LOG(LogTemp, Warning, TEXT("Arcwright: Unknown event param type '%s' for '%s', defaulting to String"), *Param.Type, *Param.Name);
		}

		Node->CreateUserDefinedPin(FName(*Param.Name), PinType, EGPD_Output);
		UE_LOG(LogTemp, Log, TEXT("Arcwright: Added event param '%s' (%s) to CustomEvent '%s'"), *Param.Name, *Param.Type, *EventName);
	}

	return Node;
}

UK2Node* FBlueprintBuilder::CreateCallFunctionNode(UBlueprint* BP, UEdGraph* Graph, const FDSLNode& NodeDef)
{
	UK2Node_CallFunction* FuncNode = NewObject<UK2Node_CallFunction>(Graph);

	// Find the UFunction from the path
	UFunction* Func = FindFunctionByPath(NodeDef.UEFunction);
	if (Func)
	{
		FuncNode->SetFromFunction(Func);
	}
	else
	{
		// Try setting by member reference
		FString ClassName, FuncName;
		if (NodeDef.UEFunction.Split(TEXT(":"), &ClassName, &FuncName))
		{
			FuncNode->FunctionReference.SetExternalMember(FName(*FuncName), nullptr);
		}
		UE_LOG(LogTemp, Warning, TEXT("Arcwright: Function not found: %s"), *NodeDef.UEFunction);
	}

	FuncNode->AllocateDefaultPins();
	Graph->AddNode(FuncNode, false, false);

	// Set parameter defaults
	for (const auto& Param : NodeDef.Params)
	{
		SetPinDefaultValue(FuncNode, Param.Key, Param.Value);
	}

	return FuncNode;
}

UK2Node* FBlueprintBuilder::CreateBranchNode(UBlueprint* BP, UEdGraph* Graph, const FDSLNode& NodeDef)
{
	UK2Node_IfThenElse* Node = NewObject<UK2Node_IfThenElse>(Graph);
	Node->AllocateDefaultPins();
	Graph->AddNode(Node, false, false);
	return Node;
}

UK2Node* FBlueprintBuilder::CreateSequenceNode(UBlueprint* BP, UEdGraph* Graph, const FDSLNode& NodeDef)
{
	UK2Node_ExecutionSequence* Node = NewObject<UK2Node_ExecutionSequence>(Graph);
	Node->AllocateDefaultPins();
	Graph->AddNode(Node, false, false);
	// AllocateDefaultPins creates 2 outputs (then 0, then 1). Add more for typical usage.
	for (int32 i = 0; i < 4; i++) { Node->AddInputPin(); }

	// Debug: log actual pin names
	UE_LOG(LogTemp, Log, TEXT("Arcwright: Sequence node pins after creation:"));
	for (UEdGraphPin* P : Node->Pins)
	{
		FString PDir = (P->Direction == EGPD_Input) ? TEXT("IN") : TEXT("OUT");
		UE_LOG(LogTemp, Log, TEXT("  [%s] '%s'"), *PDir, *P->PinName.ToString());
	}
	return Node;
}

UK2Node* FBlueprintBuilder::CreateFlowControlNode(UBlueprint* BP, UEdGraph* Graph, const FDSLNode& NodeDef)
{
	// MultiGate is a native node, not a macro
	if (NodeDef.UEClass == TEXT("UK2Node_MultiGate"))
	{
		UK2Node_MultiGate* Node = NewObject<UK2Node_MultiGate>(Graph);
		Node->AllocateDefaultPins();
		Graph->AddNode(Node, false, false);
		// Add extra output pins — default gives 2, we add more
		for (int32 i = 0; i < 4; i++) { Node->AddInputPin(); }

		UE_LOG(LogTemp, Log, TEXT("Arcwright: MultiGate native pins:"));
		for (UEdGraphPin* P : Node->Pins)
		{
			FString PDir = (P->Direction == EGPD_Input) ? TEXT("IN") : TEXT("OUT");
			UE_LOG(LogTemp, Log, TEXT("  [%s] '%s'"), *PDir, *P->PinName.ToString());
		}
		return Node;
	}

	// FlipFlop, DoOnce, Gate are macros in StandardMacros library
	FString MacroName;
	if (NodeDef.UEClass == TEXT("UK2Node_FlipFlop")) MacroName = TEXT("FlipFlop");
	else if (NodeDef.UEClass == TEXT("UK2Node_DoOnce")) MacroName = TEXT("Do Once");
	else if (NodeDef.UEClass == TEXT("UK2Node_Gate")) MacroName = TEXT("Gate");

	UK2Node_MacroInstance* Node = NewObject<UK2Node_MacroInstance>(Graph);
	UBlueprint* MacroLib = LoadObject<UBlueprint>(nullptr,
		TEXT("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros"));
	if (MacroLib)
	{
		for (UEdGraph* MacroGraph : MacroLib->MacroGraphs)
		{
			if (MacroGraph->GetFName() == FName(*MacroName))
			{
				Node->SetMacroGraph(MacroGraph);
				break;
			}
		}
	}
	Node->AllocateDefaultPins();
	Graph->AddNode(Node, false, false);

	UE_LOG(LogTemp, Log, TEXT("Arcwright: %s MacroInstance pins:"), *MacroName);
	for (UEdGraphPin* P : Node->Pins)
	{
		FString PDir = (P->Direction == EGPD_Input) ? TEXT("IN") : TEXT("OUT");
		UE_LOG(LogTemp, Log, TEXT("  [%s] '%s'"), *PDir, *P->PinName.ToString());
	}

	return Node;
}

UK2Node* FBlueprintBuilder::CreateLoopNode(UBlueprint* BP, UEdGraph* Graph, const FDSLNode& NodeDef)
{
	if (NodeDef.UEClass == TEXT("UK2Node_ForLoop"))
	{
		UK2Node_MacroInstance* Node = NewObject<UK2Node_MacroInstance>(Graph);
		UBlueprint* MacroLib = LoadObject<UBlueprint>(nullptr,
			TEXT("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros"));
		if (MacroLib)
		{
			for (UEdGraph* MacroGraph : MacroLib->MacroGraphs)
			{
				if (MacroGraph->GetFName() == FName(TEXT("ForLoop")))
				{
					Node->SetMacroGraph(MacroGraph);
					break;
				}
			}
		}
		Node->AllocateDefaultPins();
		Graph->AddNode(Node, false, false);

		// Set loop bounds from params
		if (NodeDef.Params.Contains(TEXT("FirstIndex")))
			SetPinDefaultValue(Node, TEXT("FirstIndex"), NodeDef.Params[TEXT("FirstIndex")]);
		if (NodeDef.Params.Contains(TEXT("LastIndex")))
			SetPinDefaultValue(Node, TEXT("LastIndex"), NodeDef.Params[TEXT("LastIndex")]);

		return Node;
	}

	// ForEachLoop and WhileLoop — load from StandardMacros
	FString MacroName;
	if (NodeDef.UEClass == TEXT("UK2Node_ForEachLoop")) MacroName = TEXT("ForEachLoop");
	else if (NodeDef.UEClass == TEXT("UK2Node_WhileLoop")) MacroName = TEXT("WhileLoop");

	if (!MacroName.IsEmpty())
	{
		UK2Node_MacroInstance* Node = NewObject<UK2Node_MacroInstance>(Graph);
		UBlueprint* MacroLib = LoadObject<UBlueprint>(nullptr,
			TEXT("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros"));
		if (MacroLib)
		{
			for (UEdGraph* MacroGraph : MacroLib->MacroGraphs)
			{
				if (MacroGraph->GetFName() == FName(*MacroName))
				{
					Node->SetMacroGraph(MacroGraph);
					break;
				}
			}
		}
		Node->AllocateDefaultPins();
		Graph->AddNode(Node, false, false);
		return Node;
	}

	// Fallback — unknown loop type
	UK2Node_CallFunction* Node = NewObject<UK2Node_CallFunction>(Graph);
	Node->AllocateDefaultPins();
	Graph->AddNode(Node, false, false);
	return Node;
}

UK2Node* FBlueprintBuilder::CreateCastNode(UBlueprint* BP, UEdGraph* Graph, const FDSLNode& NodeDef)
{
	UK2Node_DynamicCast* CastNode = NewObject<UK2Node_DynamicCast>(Graph);

	// Resolve target class from cast_class path
	UClass* TargetClass = nullptr;
	if (NodeDef.CastClass.StartsWith(TEXT("/Script/")))
	{
		TargetClass = FindObject<UClass>(nullptr, *NodeDef.CastClass);
	}
	if (!TargetClass)
	{
		// Try common class names
		if (NodeDef.CastClass.Contains(TEXT("Character"))) TargetClass = ACharacter::StaticClass();
		else if (NodeDef.CastClass.Contains(TEXT("Pawn"))) TargetClass = APawn::StaticClass();
		else TargetClass = AActor::StaticClass();
	}

	CastNode->TargetType = TargetClass;
	CastNode->AllocateDefaultPins();
	Graph->AddNode(CastNode, false, false);

	return CastNode;
}

UK2Node* FBlueprintBuilder::CreateVariableNode(UBlueprint* BP, UEdGraph* Graph, const FDSLNode& NodeDef)
{
	// Get the variable name from params
	FString VarName;
	if (!NodeDef.ParamKey.IsEmpty() && NodeDef.Params.Contains(NodeDef.ParamKey))
	{
		VarName = NodeDef.Params[NodeDef.ParamKey];
	}

	if (VarName.IsEmpty())
	{
		UE_LOG(LogTemp, Warning, TEXT("Arcwright: Variable node %s has no variable name"), *NodeDef.ID);
		return nullptr;
	}

	FName VarFName = FName(*VarName);

	// Auto-create variable if it doesn't exist yet
	bool bFound = false;
	for (const FBPVariableDescription& Desc : BP->NewVariables)
	{
		if (Desc.VarName == VarFName)
		{
			bFound = true;
			break;
		}
	}
	if (!bFound)
	{
		// Infer type from DSL type hint in params, or default to Object (AActor)
		FEdGraphPinType PinType;
		FString TypeHint;
		if (NodeDef.Params.Contains(TEXT("Type")))
		{
			TypeHint = NodeDef.Params[TEXT("Type")];
		}

		if (TypeHint.Contains(TEXT("Array")))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_String;
			PinType.ContainerType = EPinContainerType::Array;
		}
		else if (TypeHint == TEXT("Int") || TypeHint == TEXT("int"))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_Int;
		}
		else if (TypeHint == TEXT("Float") || TypeHint == TEXT("float"))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_Real;
			PinType.PinSubCategory = UEdGraphSchema_K2::PC_Float;
		}
		else if (TypeHint == TEXT("Bool") || TypeHint == TEXT("bool"))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
		}
		else if (TypeHint == TEXT("String") || TypeHint == TEXT("string"))
		{
			PinType.PinCategory = UEdGraphSchema_K2::PC_String;
		}
		else
		{
			// Default: Object (AActor)
			PinType.PinCategory = UEdGraphSchema_K2::PC_Object;
			PinType.PinSubCategoryObject = AActor::StaticClass();
		}

		FBlueprintEditorUtils::AddMemberVariable(BP, VarFName, PinType);
		UE_LOG(LogTemp, Log, TEXT("Arcwright: Auto-created variable '%s' (type hint: '%s')"), *VarName, *TypeHint);
	}

	// Look up actual variable type from BP for pin type forcing
	FEdGraphPinType VarPinType;
	bool bFoundVarType = false;
	for (const FBPVariableDescription& Var : BP->NewVariables)
	{
		if (Var.VarName == VarFName)
		{
			VarPinType = Var.VarType;
			bFoundVarType = true;
			break;
		}
	}

	if (NodeDef.UEClass == TEXT("UK2Node_VariableGet"))
	{
		UK2Node_VariableGet* Node = NewObject<UK2Node_VariableGet>(Graph);
		Node->VariableReference.SetSelfMember(VarFName);
		Graph->AddNode(Node, false, false);
		Node->AllocateDefaultPins();

		// Force pin types from BP->NewVariables if still wildcard
		if (bFoundVarType)
		{
			for (UEdGraphPin* Pin : Node->Pins)
			{
				if (Pin->Direction == EGPD_Output && !UEdGraphSchema_K2::IsExecPin(*Pin) && Pin->PinName != UEdGraphSchema_K2::PN_Self)
				{
					if (Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Wildcard || Pin->PinType.PinCategory.IsNone())
					{
						Pin->PinType = VarPinType;
						UE_LOG(LogTemp, Log, TEXT("Arcwright: Forced VariableGet '%s' pin '%s' to type %s (container=%d)"),
							*VarName, *Pin->PinName.ToString(), *Pin->PinType.PinCategory.ToString(), (int32)Pin->PinType.ContainerType);
					}
				}
			}
		}
		return Node;
	}
	else // UK2Node_VariableSet
	{
		UK2Node_VariableSet* Node = NewObject<UK2Node_VariableSet>(Graph);
		Node->VariableReference.SetSelfMember(VarFName);
		Graph->AddNode(Node, false, false);
		Node->AllocateDefaultPins();

		// Force pin types from BP->NewVariables if still wildcard
		if (bFoundVarType)
		{
			for (UEdGraphPin* Pin : Node->Pins)
			{
				if (!UEdGraphSchema_K2::IsExecPin(*Pin) && Pin->PinName != UEdGraphSchema_K2::PN_Self && Pin->PinName != TEXT("WorldContextObject"))
				{
					if (Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Wildcard || Pin->PinType.PinCategory.IsNone())
					{
						Pin->PinType = VarPinType;
						UE_LOG(LogTemp, Log, TEXT("Arcwright: Forced VariableSet '%s' pin '%s' to type %s (container=%d)"),
							*VarName, *Pin->PinName.ToString(), *Pin->PinType.PinCategory.ToString(), (int32)Pin->PinType.ContainerType);
					}
				}
			}
		}
		return Node;
	}
}

UK2Node* FBlueprintBuilder::CreateSpawnActorNode(UBlueprint* BP, UEdGraph* Graph, const FDSLNode& NodeDef)
{
	UK2Node_SpawnActorFromClass* Node = NewObject<UK2Node_SpawnActorFromClass>(Graph);
	Node->AllocateDefaultPins();
	Graph->AddNode(Node, false, false);
	return Node;
}

UK2Node* FBlueprintBuilder::CreateSwitchNode(UBlueprint* BP, UEdGraph* Graph, const FDSLNode& NodeDef)
{
	if (NodeDef.UEClass == TEXT("UK2Node_SwitchInteger"))
	{
		UK2Node_SwitchInteger* Node = NewObject<UK2Node_SwitchInteger>(Graph);
		Node->AllocateDefaultPins();
		// Create case pins — AllocateDefaultPins only creates Default, we need Case_0..Case_N
		for (int32 i = 0; i < 5; i++) { Node->AddPinToSwitchNode(); }
		Graph->AddNode(Node, false, false);
		return Node;
	}
	else
	{
		UK2Node_SwitchString* Node = NewObject<UK2Node_SwitchString>(Graph);
		Node->AllocateDefaultPins();
		Graph->AddNode(Node, false, false);
		return Node;
	}
}

UK2Node* FBlueprintBuilder::CreateBreakStructNode(UBlueprint* BP, UEdGraph* Graph, const FDSLNode& NodeDef)
{
	UK2Node_BreakStruct* Node = NewObject<UK2Node_BreakStruct>(Graph);
	// TODO: Set the struct type based on DSL type (HitResult, Vector, etc.)
	Node->AllocateDefaultPins();
	Graph->AddNode(Node, false, false);
	return Node;
}

// ============================================================
// Variable creation
// ============================================================

void FBlueprintBuilder::CreateBlueprintVariables(UBlueprint* BP, const TArray<FDSLVariable>& Variables)
{
	for (const FDSLVariable& Var : Variables)
	{
		FEdGraphPinType PinType = GetPinTypeFromString(Var.Type);
		const bool bSuccess = FBlueprintEditorUtils::AddMemberVariable(BP, FName(*Var.Name), PinType);

		if (bSuccess && !Var.DefaultValue.IsEmpty())
		{
			// Set default value
			FProperty* Prop = BP->GeneratedClass->FindPropertyByName(FName(*Var.Name));
			if (Prop)
			{
				UE_LOG(LogTemp, Verbose, TEXT("Arcwright: Created variable %s : %s = %s"),
					*Var.Name, *Var.Type, *Var.DefaultValue);
			}
		}
	}
}

// ============================================================
// Pin resolution
// ============================================================

UEdGraphPin* FBlueprintBuilder::FindPinByDSLName(UEdGraphNode* Node, const FString& DSLName, EEdGraphPinDirection Direction)
{
	if (!Node) return nullptr;

	// ---------- Layer 1: Exact match ----------
	UEdGraphPin* Pin = Node->FindPin(FName(*DSLName), Direction);
	if (Pin) return Pin;

	// Try without direction constraint
	Pin = Node->FindPin(FName(*DSLName));
	if (Pin) return Pin;

	// ---------- Layer 2: Static alias table ----------
	static TMap<FString, FString> Aliases;
	if (Aliases.Num() == 0)
	{
		Aliases.Add(TEXT("C"), TEXT("Condition"));
		Aliases.Add(TEXT("O"), TEXT("Object"));
		Aliases.Add(TEXT("A"), TEXT("TargetArray"));
		Aliases.Add(TEXT("LoopBody"), TEXT("Loop Body"));
		Aliases.Add(TEXT("ArrayElement"), TEXT("Array Element"));
		Aliases.Add(TEXT("ArrayIndex"), TEXT("Array Index"));
		Aliases.Add(TEXT("Completed"), TEXT("Completed"));
	}

	if (const FString* Mapped = Aliases.Find(DSLName))
	{
		Pin = Node->FindPin(FName(**Mapped), Direction);
		if (Pin) return Pin;
		Pin = Node->FindPin(FName(**Mapped));
		if (Pin) return Pin;
	}

	// "I" — try InString first, then fall back to first non-exec non-self input
	if (DSLName == TEXT("I"))
	{
		Pin = Node->FindPin(TEXT("InString"), Direction);
		if (Pin) return Pin;
		Pin = Node->FindPin(TEXT("InString"));
		if (Pin) return Pin;
		// Fallback: first non-exec, non-self, non-WorldContextObject input
		for (UEdGraphPin* P : Node->Pins)
		{
			if (P->Direction == EGPD_Input && P->PinType.PinCategory != UEdGraphSchema_K2::PC_Exec
				&& P->PinName != TEXT("self") && P->PinName != TEXT("WorldContextObject"))
				return P;
		}
	}

	// ---------- Layer 3: UE schema constants ----------
	if (DSLName == TEXT("Execute"))
	{
		Pin = Node->FindPin(UEdGraphSchema_K2::PN_Execute, EGPD_Input);
		if (Pin) return Pin;
		// Fallback: first exec input pin
		for (UEdGraphPin* P : Node->Pins)
		{
			if (P->Direction == EGPD_Input && P->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec)
				return P;
		}
	}
	if (DSLName == TEXT("Then"))
	{
		Pin = Node->FindPin(UEdGraphSchema_K2::PN_Then, EGPD_Output);
		if (Pin) return Pin;
		// Fallback: first exec output pin
		for (UEdGraphPin* P : Node->Pins)
		{
			if (P->Direction == EGPD_Output && P->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec)
				return P;
		}
	}
	if (DSLName == TEXT("True"))
	{
		return Node->FindPin(UEdGraphSchema_K2::PN_Then); // Branch True = PN_Then
	}
	if (DSLName == TEXT("False"))
	{
		return Node->FindPin(UEdGraphSchema_K2::PN_Else);
	}
	if (DSLName == TEXT("ReturnValue"))
	{
		return Node->FindPin(UEdGraphSchema_K2::PN_ReturnValue);
	}

	// ---------- Layer 4: Cast exec pins ----------
	UK2Node_DynamicCast* CastNode = Cast<UK2Node_DynamicCast>(Node);
	if (CastNode)
	{
		if (DSLName == TEXT("CastSucceeded"))
		{
			// First exec output
			for (UEdGraphPin* P : Node->Pins)
			{
				if (P->Direction == EGPD_Output && P->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec)
					return P;
			}
		}
		if (DSLName == TEXT("CastFailed"))
		{
			// Second exec output
			int32 ExecIdx = 0;
			for (UEdGraphPin* P : Node->Pins)
			{
				if (P->Direction == EGPD_Output && P->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec)
				{
					if (ExecIdx == 1) return P;
					ExecIdx++;
				}
			}
		}
		if (DSLName.StartsWith(TEXT("As")))
		{
			// AsCharacter, AsPawn, etc. — first non-exec output after cast outputs
			for (UEdGraphPin* P : Node->Pins)
			{
				if (P->Direction == EGPD_Output && P->PinType.PinCategory != UEdGraphSchema_K2::PC_Exec
					&& P->PinName != TEXT("bSuccess"))
					return P;
			}
		}
	}

	// ---------- Layer 5: Dynamic patterns ----------
	// Then_N → "then_N" (Sequence nodes — UE5 uses underscore not space)
	if (DSLName.StartsWith(TEXT("Then_")))
	{
		FString NumStr = DSLName.Mid(5);
		// Try underscore variant first (UE 5.7 actual)
		FString UEPinName = FString::Printf(TEXT("then_%s"), *NumStr);
		Pin = Node->FindPin(FName(*UEPinName));
		if (Pin) return Pin;
		// Try space variant (some UE versions)
		UEPinName = FString::Printf(TEXT("then %s"), *NumStr);
		Pin = Node->FindPin(FName(*UEPinName));
		if (Pin) return Pin;
	}

	// Out_N → "Out_N" or "Out N" (MultiGate nodes)
	if (DSLName.StartsWith(TEXT("Out_")))
	{
		FString NumStr = DSLName.Mid(4);
		// Try exact "Out_N" first
		Pin = Node->FindPin(FName(*DSLName));
		if (Pin) return Pin;
		// Try "Out N" (space variant)
		FString UEPinName = FString::Printf(TEXT("Out %s"), *NumStr);
		Pin = Node->FindPin(FName(*UEPinName));
		if (Pin) return Pin;
		// Fallback: Nth exec output pin
		int32 TargetIdx = FCString::Atoi(*NumStr);
		int32 ExecIdx = 0;
		for (UEdGraphPin* P : Node->Pins)
		{
			if (P->Direction == EGPD_Output && P->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec)
			{
				if (ExecIdx == TargetIdx) return P;
				ExecIdx++;
			}
		}
	}

	// Case_N → Nth non-Default exec output (Switch nodes)
	if (DSLName.StartsWith(TEXT("Case_")))
	{
		FString NumStr = DSLName.Mid(5);
		int32 CaseIndex = FCString::Atoi(*NumStr);
		int32 ExecIdx = 0;
		for (UEdGraphPin* P : Node->Pins)
		{
			if (P->Direction == EGPD_Output && P->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec
				&& P->PinName != TEXT("Default"))
			{
				if (ExecIdx == CaseIndex) return P;
				ExecIdx++;
			}
		}
	}

	// Default pin (Switch nodes)
	if (DSLName == TEXT("Default"))
	{
		Pin = Node->FindPin(TEXT("Default"), EGPD_Output);
		if (Pin) return Pin;
	}

	// A/B/C/D/E/F → "then_0"/"then_1"/... (Sequence letter mapping)
	if (DSLName.Len() == 1 && Direction == EGPD_Output)
	{
		TCHAR Ch = DSLName[0];
		if (Ch >= 'A' && Ch <= 'F')
		{
			int32 Idx = Ch - 'A';
			// Try underscore variant (UE 5.7 actual)
			FString UEPinName = FString::Printf(TEXT("then_%d"), Idx);
			Pin = Node->FindPin(FName(*UEPinName));
			if (Pin) return Pin;
			// Try space variant
			UEPinName = FString::Printf(TEXT("then %d"), Idx);
			Pin = Node->FindPin(FName(*UEPinName));
			if (Pin) return Pin;
			// Fallback: Nth exec output pin (for any node type)
			int32 ExecIdx = 0;
			for (UEdGraphPin* P : Node->Pins)
			{
				if (P->Direction == EGPD_Output && P->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec)
				{
					if (ExecIdx == Idx) return P;
					ExecIdx++;
				}
			}
		}
	}

	// ---------- Layer 6: Variable pins ----------
	if (DSLName == TEXT("Value"))
	{
		// VariableGet: first non-exec non-self output
		if (Cast<UK2Node_VariableGet>(Node))
		{
			for (UEdGraphPin* P : Node->Pins)
			{
				if (P->Direction == EGPD_Output && P->PinType.PinCategory != UEdGraphSchema_K2::PC_Exec
					&& P->PinName != TEXT("self"))
					return P;
			}
		}
		// VariableSet or other: try exact match was already tried above
	}

	if ((DSLName == TEXT("V") || DSLName == TEXT("Value")) && Cast<UK2Node_VariableSet>(Node))
	{
		// VariableSet: match direction — input for setting value, output for reading set value
		EEdGraphPinDirection TargetDir = (Direction == EGPD_Output) ? EGPD_Output : EGPD_Input;
		for (UEdGraphPin* P : Node->Pins)
		{
			if (P->Direction == TargetDir && P->PinType.PinCategory != UEdGraphSchema_K2::PC_Exec
				&& P->PinName != TEXT("self") && P->PinName != TEXT("WorldContextObject"))
				return P;
		}
	}

	// T → Target/Object pin
	// Try explicit parameter names first (for static library functions like GetDisplayName
	// where "Object" is the actual parameter, not the library's "self" pin).
	// Then fall back to "self" (for instance methods like AddToViewport where self IS the target).
	if (DSLName == TEXT("T"))
	{
		Pin = Node->FindPin(TEXT("Object"), Direction);
		if (Pin) return Pin;
		Pin = Node->FindPin(TEXT("Target"), Direction);
		if (Pin) return Pin;
		Pin = Node->FindPin(TEXT("self"), Direction);
		if (Pin) return Pin;
		Pin = Node->FindPin(TEXT("self"));
		if (Pin) return Pin;
	}

	// S → Selection (Switch) or SpawnTransform, context-dependent
	if (DSLName == TEXT("S"))
	{
		Pin = Node->FindPin(TEXT("Selection"), Direction);
		if (Pin) return Pin;
		Pin = Node->FindPin(TEXT("SpawnTransform"), Direction);
		if (Pin) return Pin;
	}

	// A → TargetArray or Array (for array operations and ForEachLoop)
	if (DSLName == TEXT("A"))
	{
		Pin = Node->FindPin(TEXT("TargetArray"), Direction);
		if (Pin) return Pin;
		Pin = Node->FindPin(TEXT("Array"), Direction);
		if (Pin) return Pin;
		Pin = Node->FindPin(TEXT("Array"));
		if (Pin) return Pin;
	}

	// ---------- Layer 7: Pressed/Released on InputAction ----------
	if (Cast<UK2Node_InputAction>(Node))
	{
		if (DSLName == TEXT("Pressed"))
		{
			// First exec output
			for (UEdGraphPin* P : Node->Pins)
			{
				if (P->Direction == EGPD_Output && P->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec)
					return P;
			}
		}
		if (DSLName == TEXT("Released"))
		{
			// Second exec output
			int32 ExecIdx = 0;
			for (UEdGraphPin* P : Node->Pins)
			{
				if (P->Direction == EGPD_Output && P->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec)
				{
					if (ExecIdx == 1) return P;
					ExecIdx++;
				}
			}
		}
	}

	// ---------- Layer 8: V as first non-exec non-self input (generic fallback) ----------
	if (DSLName == TEXT("V"))
	{
		for (UEdGraphPin* P : Node->Pins)
		{
			if (P->Direction == EGPD_Input && P->PinType.PinCategory != UEdGraphSchema_K2::PC_Exec
				&& P->PinName != TEXT("self") && P->PinName != TEXT("WorldContextObject"))
				return P;
		}
	}

	// ---------- Layer 9: Case-insensitive fallback ----------
	for (UEdGraphPin* P : Node->Pins)
	{
		if (P->PinName.ToString().Equals(DSLName, ESearchCase::IgnoreCase))
		{
			if (P->Direction == Direction || Direction == EGPD_MAX)
				return P;
		}
	}
	// Without direction
	for (UEdGraphPin* P : Node->Pins)
	{
		if (P->PinName.ToString().Equals(DSLName, ESearchCase::IgnoreCase))
			return P;
	}

	// Debug: dump all pins on this node when resolution fails
	FString DirStr = (Direction == EGPD_Input) ? TEXT("INPUT") : TEXT("OUTPUT");
	UE_LOG(LogTemp, Warning, TEXT("Arcwright: PIN MISS — DSL '%s' (%s) on node %s (%s). Available pins:"),
		*DSLName, *DirStr, *Node->GetNodeTitle(ENodeTitleType::ListView).ToString(), *Node->GetClass()->GetName());
	for (UEdGraphPin* P : Node->Pins)
	{
		FString PDir = (P->Direction == EGPD_Input) ? TEXT("IN") : TEXT("OUT");
		FString PType = P->PinType.PinCategory.ToString();
		UE_LOG(LogTemp, Warning, TEXT("  [%s] '%s' (type: %s)"), *PDir, *P->PinName.ToString(), *PType);
	}

	return nullptr;
}

// ============================================================
// Connection wiring
// ============================================================

bool FBlueprintBuilder::ConnectPins(
	const TMap<FString, UEdGraphNode*>& NodeMap,
	const TArray<FDSLConnection>& Connections)
{
	int32 SuccessCount = 0;
	int32 FailCount = 0;

	const UEdGraphSchema_K2* Schema = GetDefault<UEdGraphSchema_K2>();

	for (const FDSLConnection& Conn : Connections)
	{
		// Handle literal data connections — set pin default values
		if (Conn.Type == TEXT("data_literal"))
		{
			UEdGraphNode* const* DstNodePtr = NodeMap.Find(Conn.TargetNode);
			if (!DstNodePtr)
			{
				UE_LOG(LogTemp, Warning, TEXT("Arcwright: data_literal target node not found: %s"), *Conn.TargetNode);
				FailCount++;
				continue;
			}
			UEdGraphPin* DstPin = FindPinByDSLName(*DstNodePtr, Conn.TargetPin, EGPD_Input);
			if (!DstPin)
			{
				UE_LOG(LogTemp, Warning, TEXT("Arcwright: data_literal pin not found: %s.%s"), *Conn.TargetNode, *Conn.TargetPin);
				FailCount++;
				continue;
			}
			DstPin->DefaultValue = Conn.Value;
			SuccessCount++;
			continue;
		}

		UEdGraphNode* const* SrcNodePtr = NodeMap.Find(Conn.SourceNode);
		UEdGraphNode* const* DstNodePtr = NodeMap.Find(Conn.TargetNode);

		if (!SrcNodePtr || !DstNodePtr)
		{
			UE_LOG(LogTemp, Warning, TEXT("Arcwright: Connection refs unknown node: %s -> %s"),
				*Conn.SourceNode, *Conn.TargetNode);
			FailCount++;
			continue;
		}

		UEdGraphNode* SrcNode = *SrcNodePtr;
		UEdGraphNode* DstNode = *DstNodePtr;

		// Use FindPinByDSLName for smart resolution
		UEdGraphPin* SrcPin = FindPinByDSLName(SrcNode, Conn.SourcePin, EGPD_Output);
		UEdGraphPin* DstPin = FindPinByDSLName(DstNode, Conn.TargetPin, EGPD_Input);

		if (SrcPin && DstPin)
		{
			// Try TryCreateConnection first — auto-inserts conversion nodes (Int→Float, etc.)
			bool bConnected = Schema->TryCreateConnection(SrcPin, DstPin);
			if (!bConnected)
			{
				// Fallback to MakeLinkTo (works for compatible types, returns void)
				SrcPin->MakeLinkTo(DstPin);
				bConnected = SrcPin->LinkedTo.Contains(DstPin);
			}

			if (bConnected)
			{
				// Notify nodes of connection — triggers wildcard pin type resolution
				// (critical for KismetArrayLibrary functions like Array_Add, Array_Contains)
				if (Conn.Type == TEXT("data"))
				{
					SrcNode->PinConnectionListChanged(SrcPin);
					DstNode->PinConnectionListChanged(DstPin);
				}
				SuccessCount++;
			}
			else
			{
				UE_LOG(LogTemp, Warning, TEXT("Arcwright: Connection failed: %s.%s(%s) -> %s.%s(%s)"),
					*Conn.SourceNode, *Conn.SourcePin, *SrcPin->PinName.ToString(),
					*Conn.TargetNode, *Conn.TargetPin, *DstPin->PinName.ToString());
				FailCount++;
			}
		}
		else
		{
			UE_LOG(LogTemp, Warning, TEXT("Arcwright: Pin not found: %s.%s(%s) -> %s.%s(%s)"),
				*Conn.SourceNode, *Conn.SourcePin, SrcPin ? TEXT("OK") : TEXT("MISSING"),
				*Conn.TargetNode, *Conn.TargetPin, DstPin ? TEXT("OK") : TEXT("MISSING"));
			FailCount++;
		}
	}

	UE_LOG(LogTemp, Log, TEXT("Arcwright: Wired %d/%d connections (%d failed)"),
		SuccessCount, SuccessCount + FailCount, FailCount);

	return FailCount == 0;
}

// ============================================================
// Helpers
// ============================================================

UClass* FBlueprintBuilder::FindParentClass(const FString& ClassName)
{
	if (ClassName == TEXT("Actor") || ClassName == TEXT("AActor")) return AActor::StaticClass();
	if (ClassName == TEXT("Character") || ClassName == TEXT("ACharacter")) return ACharacter::StaticClass();
	if (ClassName == TEXT("Pawn") || ClassName == TEXT("APawn")) return APawn::StaticClass();
	if (ClassName == TEXT("PlayerController") || ClassName == TEXT("APlayerController")) return APlayerController::StaticClass();
	if (ClassName == TEXT("AIController") || ClassName == TEXT("AAIController")) return AAIController::StaticClass();
	if (ClassName == TEXT("GameModeBase") || ClassName == TEXT("AGameModeBase")) return AGameModeBase::StaticClass();
	if (ClassName == TEXT("GameMode") || ClassName == TEXT("AGameMode")) return AGameModeBase::StaticClass();

	// Try finding by path
	UClass* Found = FindObject<UClass>(nullptr, *ClassName);
	return Found;
}

UFunction* FBlueprintBuilder::FindFunctionByPath(const FString& FunctionPath)
{
	// Format: "/Script/Engine.KismetSystemLibrary:PrintString"
	FString ClassPath, FuncName;
	if (!FunctionPath.Split(TEXT(":"), &ClassPath, &FuncName))
	{
		return nullptr;
	}

	UClass* OwnerClass = FindObject<UClass>(nullptr, *ClassPath);
	if (!OwnerClass)
	{
		// Try loading
		OwnerClass = LoadObject<UClass>(nullptr, *ClassPath);
	}

	// Fallback: KismetMathLibrary class resolution
	if (!OwnerClass && ClassPath.Contains(TEXT("KismetMathLibrary")))
	{
		OwnerClass = UKismetMathLibrary::StaticClass();
	}

	if (!OwnerClass)
	{
		return nullptr;
	}

	// Try exact name first
	UFunction* Func = OwnerClass->FindFunctionByName(FName(*FuncName));
	if (Func) return Func;

	// UE5 Float→Double function rename: Add_FloatFloat → Add_DoubleDouble, etc.
	if (FuncName.Contains(TEXT("Float")))
	{
		FString DoubleName = FuncName.Replace(TEXT("Float"), TEXT("Double"));
		Func = OwnerClass->FindFunctionByName(FName(*DoubleName));
		if (Func)
		{
			UE_LOG(LogTemp, Verbose, TEXT("Arcwright: Float→Double remap: %s → %s"), *FuncName, *DoubleName);
			return Func;
		}
	}

	return nullptr;
}

FEdGraphPinType FBlueprintBuilder::GetPinTypeFromString(const FString& TypeName)
{
	FEdGraphPinType PinType;

	if (TypeName == TEXT("Int") || TypeName == TEXT("int"))
	{
		PinType.PinCategory = UEdGraphSchema_K2::PC_Int;
	}
	else if (TypeName == TEXT("Float") || TypeName == TEXT("float"))
	{
		PinType.PinCategory = UEdGraphSchema_K2::PC_Real;
		PinType.PinSubCategory = UEdGraphSchema_K2::PC_Float;
	}
	else if (TypeName == TEXT("Bool") || TypeName == TEXT("bool"))
	{
		PinType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
	}
	else if (TypeName == TEXT("String") || TypeName == TEXT("string"))
	{
		PinType.PinCategory = UEdGraphSchema_K2::PC_String;
	}
	else if (TypeName == TEXT("Vector") || TypeName == TEXT("vector"))
	{
		PinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
		PinType.PinSubCategoryObject = TBaseStructure<FVector>::Get();
	}
	else if (TypeName == TEXT("Rotator") || TypeName == TEXT("rotator"))
	{
		PinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
		PinType.PinSubCategoryObject = TBaseStructure<FRotator>::Get();
	}
	else if (TypeName == TEXT("Object") || TypeName == TEXT("object") ||
			 TypeName == TEXT("Actor"))
	{
		PinType.PinCategory = UEdGraphSchema_K2::PC_Object;
		PinType.PinSubCategoryObject = AActor::StaticClass();
	}
	else if (TypeName == TEXT("Widget") || TypeName == TEXT("UserWidget") ||
			 TypeName == TEXT("UUserWidget"))
	{
		PinType.PinCategory = UEdGraphSchema_K2::PC_Object;
		PinType.PinSubCategoryObject = UUserWidget::StaticClass();
	}
	else if (TypeName.Contains(TEXT("Array")))
	{
		// Array of strings by default — specific element type can be refined later
		PinType.PinCategory = UEdGraphSchema_K2::PC_String;
		PinType.ContainerType = EPinContainerType::Array;
	}
	else
	{
		// Default to wildcard
		PinType.PinCategory = UEdGraphSchema_K2::PC_Wildcard;
	}

	return PinType;
}

void FBlueprintBuilder::SetNodePosition(UEdGraphNode* Node, const FVector2D& Position)
{
	if (Node)
	{
		Node->NodePosX = Position.X;
		Node->NodePosY = Position.Y;
	}
}

void FBlueprintBuilder::SetPinDefaultValue(UEdGraphNode* Node, const FString& PinName, const FString& Value)
{
	if (!Node) return;

	UEdGraphPin* Pin = Node->FindPin(FName(*PinName));
	if (Pin)
	{
		Pin->DefaultValue = Value;
	}
}
