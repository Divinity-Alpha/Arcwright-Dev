// Copyright 2026 Divinity Alpha. All Rights Reserved.
using UnrealBuildTool;

public class Arcwright : ModuleRules
{
	public Arcwright(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"Networking",
			"Sockets"
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"UnrealEd",
			"BlueprintGraph",
			"KismetCompiler",
			"Kismet",
			"GraphEditor",
			"Json",
			"JsonUtilities",
			"Slate",
			"SlateCore",
			"EditorStyle",
			"ToolMenus",
			"AssetTools",
			"ContentBrowser",
			"UMG",
			"UMGEditor",
			"EnhancedInput",
			"LevelEditor",
			"Niagara",
			"NiagaraCore",
			"AIModule",
			"GameplayTasks",
			"LevelSequence",
			"MovieScene",
			"MovieSceneTracks",
			"Landscape",
			"Foliage",
			"DataTableEditor",
			"RenderCore",
			"ApplicationCore",
			"NavigationSystem",
			"AnimGraph",
			"AnimGraphRuntime",
			"AnimationBlueprintLibrary",
			"HTTP",
			"Projects",
			"AppFramework"
		});
	}
}
