#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

class UBehaviorTree;
class UBlackboardData;

/**
 * Creates UBehaviorTree + UBlackboardData assets from BT IR JSON.
 * Called by the TCP command server for create_behavior_tree and
 * get_behavior_tree_info commands.
 */
class FBehaviorTreeBuilder
{
public:
	struct FBTBuildResult
	{
		bool bSuccess = false;
		FString ErrorMessage;
		FString TreeAssetPath;
		FString BlackboardAssetPath;
		int32 CompositeCount = 0;
		int32 TaskCount = 0;
		int32 DecoratorCount = 0;
		int32 ServiceCount = 0;
	};

	/**
	 * Create a BehaviorTree + Blackboard from parsed IR JSON.
	 * @param IRJson - The root IR object (metadata, blackboard_keys, tree)
	 * @param PackagePath - Content Browser path (e.g. "/Game/Arcwright/BehaviorTrees")
	 * @return Build result with asset paths and node counts
	 */
	static FBTBuildResult CreateFromIR(const TSharedPtr<FJsonObject>& IRJson, const FString& PackagePath);

	/**
	 * Query an existing BehaviorTree asset.
	 * @param Name - Asset name (e.g. "BT_PatrolGuard")
	 * @return JSON object with tree info, or nullptr if not found
	 */
	static TSharedPtr<FJsonObject> GetBehaviorTreeInfo(const FString& Name);

private:
	// Blackboard creation
	static UBlackboardData* CreateBlackboard(
		const FString& Name,
		const TArray<TSharedPtr<FJsonValue>>& Keys,
		const FString& PackagePath);

	// Tree building
	static bool BuildNodeTree(
		UBehaviorTree* TreeAsset,
		UBlackboardData* BBAsset,
		const TSharedPtr<FJsonObject>& TreeJson,
		FBTBuildResult& OutResult);

	// Recursive node creation
	static class UBTCompositeNode* CreateCompositeNode(
		UBehaviorTree* TreeAsset,
		const TSharedPtr<FJsonObject>& NodeJson,
		FBTBuildResult& OutResult);

	static class UBTTaskNode* CreateTaskNode(
		UBehaviorTree* TreeAsset,
		const TSharedPtr<FJsonObject>& NodeJson,
		FBTBuildResult& OutResult);

	static class UBTDecorator* CreateDecoratorNode(
		UBehaviorTree* TreeAsset,
		const TSharedPtr<FJsonObject>& NodeJson,
		FBTBuildResult& OutResult);

	static class UBTService* CreateServiceNode(
		UBehaviorTree* TreeAsset,
		const TSharedPtr<FJsonObject>& NodeJson,
		FBTBuildResult& OutResult);

	// Helpers
	static UBehaviorTree* FindBehaviorTreeByName(const FString& Name);
	static void CollectTreeInfo(class UBTCompositeNode* Node, TSharedPtr<FJsonObject>& OutInfo, int32 Depth = 0);
};
