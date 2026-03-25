#include "ArcwrightModule.h"
#include "CommandServer.h"
#include "TierGating.h"
#include "DSLImporter.h"
#include "BlueprintBuilder.h"
#include "ArcwrightGeneratorPanel.h"
#include "ArcwrightDashboardPanel.h"
#include "ArcwrightUIBuilderPanel.h"

#include "Interfaces/IPluginManager.h"
#include "SocketSubsystem.h"
#include "ToolMenus.h"
#include "DesktopPlatformModule.h"
#include "IDesktopPlatform.h"
#include "Framework/Application/SlateApplication.h"
#include "Framework/Docking/TabManager.h"
#include "Misc/MessageDialog.h"
#include "Misc/Paths.h"
#include "Styling/SlateStyleRegistry.h"

#define LOCTEXT_NAMESPACE "FArcwrightModule"

// CVar to enable the Generator Panel (dev/testing tool, hidden by default)
// Set in DefaultEngine.ini: [SystemSettings] Arcwright.EnableGeneratorPanel=true
static TAutoConsoleVariable<bool> CVarEnableGeneratorPanel(
	TEXT("Arcwright.EnableGeneratorPanel"),
	false,
	TEXT("Enable the Arcwright Generator Panel in the Tools menu. The Generator Panel is a development/testing tool, not the primary product interface. Default: disabled."),
	ECVF_Default
);

void FArcwrightModule::StartupModule()
{
	// Register brand icon style set (must be before tab registration)
	RegisterBrandStyle();

	UToolMenus::RegisterStartupCallback(
		FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FArcwrightModule::RegisterMenus));

	// Always register the Dashboard tab (the default user-facing panel)
	SArcwrightDashboardPanel::RegisterTab();

	// Register UI Builder tab (Pro feature)
	SArcwrightUIBuilderPanel::RegisterTab();

	// Register the Arcwright Generator Panel tab only if enabled via CVar
	if (CVarEnableGeneratorPanel.GetValueOnGameThread())
	{
		SArcwrightGeneratorPanel::RegisterTab();
		UE_LOG(LogArcwright, Log, TEXT("Arcwright: Generator Panel enabled (Arcwright.EnableGeneratorPanel=true)"));
	}

	// Auto-start the command server
	CommandServer = MakeUnique<FCommandServer>();
	if (!CommandServer->Start())
	{
		UE_LOG(LogArcwright, Warning, TEXT("Command server failed to start on plugin load"));
	}

	// Check license and revalidate if needed
	FTierGating::CheckOnStartup();

	// Auto-launch MCP server using embedded Python
	LaunchMCPServer();
}

void FArcwrightModule::LaunchMCPServer()
{
	TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("Arcwright"));
	if (!Plugin.IsValid()) return;

	FString PluginDir = Plugin->GetBaseDir();
	FString PythonExe = FPaths::Combine(PluginDir, TEXT("scripts"), TEXT("python_embedded"), TEXT("python.exe"));
	FString ServerScript = FPaths::Combine(PluginDir, TEXT("scripts"), TEXT("mcp_server"), TEXT("server.py"));

	PythonExe = FPaths::ConvertRelativePathToFull(PythonExe);
	ServerScript = FPaths::ConvertRelativePathToFull(ServerScript);

	if (!FPaths::FileExists(PythonExe))
	{
		UE_LOG(LogArcwright, Log, TEXT("Embedded Python not found at %s — MCP server requires manual start."), *PythonExe);
		return;
	}

	if (!FPaths::FileExists(ServerScript))
	{
		UE_LOG(LogArcwright, Warning, TEXT("MCP server script not found at %s"), *ServerScript);
		return;
	}

	FString Args = FString::Printf(TEXT("\"%s\""), *ServerScript);
	FString WorkingDir = FPaths::GetPath(ServerScript);

	MCPServerProcHandle = FPlatformProcess::CreateProc(
		*PythonExe, *Args,
		false, false, true,
		nullptr, 0, *WorkingDir, nullptr);

	if (MCPServerProcHandle.IsValid())
	{
		bMCPServerAutoLaunched = true;
		UE_LOG(LogArcwright, Log, TEXT("MCP server auto-launched via embedded Python"));
	}
	else
	{
		UE_LOG(LogArcwright, Warning, TEXT("Failed to auto-launch MCP server"));
	}
}

void FArcwrightModule::StopMCPServer()
{
	if (bMCPServerAutoLaunched && MCPServerProcHandle.IsValid())
	{
		FPlatformProcess::TerminateProc(MCPServerProcHandle, true);
		FPlatformProcess::CloseProc(MCPServerProcHandle);
		bMCPServerAutoLaunched = false;
		UE_LOG(LogArcwright, Log, TEXT("MCP server stopped"));
	}
}

bool FArcwrightModule::IsMCPServerRunning()
{
	if (bMCPServerAutoLaunched && MCPServerProcHandle.IsValid())
	{
		return FPlatformProcess::IsProcRunning(MCPServerProcHandle);
	}
	return false;
}

void FArcwrightModule::ShutdownModule()
{
	StopMCPServer();
	SArcwrightDashboardPanel::UnregisterTab();
	SArcwrightUIBuilderPanel::UnregisterTab();

	if (CVarEnableGeneratorPanel.GetValueOnGameThread())
	{
		SArcwrightGeneratorPanel::UnregisterTab();
	}

	if (CommandServer)
	{
		CommandServer->Stop();
		CommandServer.Reset();
	}

	UnregisterBrandStyle();

	UToolMenus::UnRegisterStartupCallback(this);
	UToolMenus::UnregisterOwner(this);
}

void FArcwrightModule::RegisterBrandStyle()
{
	FString ResourcesDir = FPaths::Combine(FPaths::ProjectPluginsDir(), TEXT("Arcwright"), TEXT("Resources"));

	BrandStyleSet = MakeShareable(new FSlateStyleSet(TEXT("ArcwrightStyle")));
	BrandStyleSet->SetContentRoot(ResourcesDir);

	// Register icon brushes for tab and menu
	FString Icon16Path = FPaths::Combine(ResourcesDir, TEXT("ArcwrightIcon16.png"));
	FString Icon40Path = FPaths::Combine(ResourcesDir, TEXT("ArcwrightIcon40.png"));

	if (FPaths::FileExists(Icon16Path))
	{
		BrandStyleSet->Set("Arcwright.Icon16", new FSlateImageBrush(Icon16Path, FVector2D(16, 16)));
	}
	if (FPaths::FileExists(Icon40Path))
	{
		BrandStyleSet->Set("Arcwright.Icon40", new FSlateImageBrush(Icon40Path, FVector2D(40, 40)));
	}

	FSlateStyleRegistry::RegisterSlateStyle(*BrandStyleSet);
}

void FArcwrightModule::UnregisterBrandStyle()
{
	if (BrandStyleSet.IsValid())
	{
		FSlateStyleRegistry::UnRegisterSlateStyle(*BrandStyleSet);
		BrandStyleSet.Reset();
	}
}

void FArcwrightModule::RegisterMenus()
{
	FToolMenuOwnerScoped OwnerScoped(this);

	// Add to Tools menu
	UToolMenu* ToolsMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu.Tools");
	FToolMenuSection& Section = ToolsMenu->FindOrAddSection("Arcwright");
	Section.Label = LOCTEXT("ArcwrightSection", "Arcwright");

	// Dashboard — the primary user-facing panel (always visible)
	Section.AddMenuEntry(
		"Dashboard",
		LOCTEXT("DashboardLabel", "Dashboard"),
		LOCTEXT("DashboardTooltip", "Open the Arcwright Dashboard: connection status, session stats, and lifetime counters"),
		FSlateIcon(TEXT("ArcwrightStyle"), TEXT("Arcwright.Icon16")),
		FUIAction(FExecuteAction::CreateRaw(this, &FArcwrightModule::OnOpenDashboard))
	);

	// UI Builder — Pro feature
	Section.AddMenuEntry(
		"UIBuilder",
		LOCTEXT("UIBuilderLabel", "UI Builder"),
		LOCTEXT("UIBuilderTooltip", "Design game UIs with themes and components (Pro)"),
		FSlateIcon(TEXT("ArcwrightStyle"), TEXT("Arcwright.Icon16")),
		FUIAction(FExecuteAction::CreateLambda([]() {
			FGlobalTabmanager::Get()->TryInvokeTab(SArcwrightUIBuilderPanel::TabId);
		}))
	);

	Section.AddMenuEntry(
		"ImportDSL",
		LOCTEXT("ImportDSLLabel", "Import DSL Blueprint..."),
		LOCTEXT("ImportDSLTooltip", "Import a .blueprint.json file generated by the Arcwright DSL parser"),
		FSlateIcon(),
		FUIAction(FExecuteAction::CreateRaw(this, &FArcwrightModule::OnImportDSLClicked))
	);

	// Generator Panel is a dev/testing tool, hidden by default.
	// Enable via CVar: Arcwright.EnableGeneratorPanel=true
	if (CVarEnableGeneratorPanel.GetValueOnGameThread())
	{
		Section.AddMenuEntry(
			"GeneratorPanel",
			LOCTEXT("GeneratorPanelLabel", "Generator Panel"),
			LOCTEXT("GeneratorPanelTooltip", "Open the Arcwright Generator panel to create assets from DSL"),
			FSlateIcon(TEXT("ArcwrightStyle"), TEXT("Arcwright.Icon16")),
			FUIAction(FExecuteAction::CreateRaw(this, &FArcwrightModule::OnOpenGeneratorPanel))
		);
	}

	Section.AddMenuEntry(
		"ToggleCommandServer",
		LOCTEXT("ToggleServerLabel", "Toggle Command Server"),
		LOCTEXT("ToggleServerTooltip", "Start/stop the TCP command server on port 13377"),
		FSlateIcon(),
		FUIAction(
			FExecuteAction::CreateRaw(this, &FArcwrightModule::OnToggleCommandServer),
			FCanExecuteAction(),
			FIsActionChecked::CreateRaw(this, &FArcwrightModule::IsCommandServerRunning)),
		EUserInterfaceActionType::ToggleButton
	);
}

void FArcwrightModule::OnImportDSLClicked()
{
	// Open file dialog
	IDesktopPlatform* DesktopPlatform = FDesktopPlatformModule::Get();
	if (!DesktopPlatform)
	{
		return;
	}

	TArray<FString> OutFiles;
	const bool bOpened = DesktopPlatform->OpenFileDialog(
		FSlateApplication::Get().FindBestParentWindowHandleForDialogs(nullptr),
		TEXT("Select Blueprint JSON IR"),
		FPaths::ProjectContentDir(),
		TEXT(""),
		TEXT("Blueprint JSON (*.blueprint.json)|*.blueprint.json|JSON Files (*.json)|*.json"),
		EFileDialogFlags::None,
		OutFiles
	);

	if (!bOpened || OutFiles.Num() == 0)
	{
		return;
	}

	const FString& JsonPath = OutFiles[0];

	// Parse IR
	FDSLBlueprint DSL;
	if (!FDSLImporter::ParseIR(JsonPath, DSL))
	{
		FMessageDialog::Open(EAppMsgType::Ok,
			FText::Format(LOCTEXT("ParseError", "Failed to parse: {0}"), FText::FromString(JsonPath)));
		return;
	}

	// Build Blueprint
	const FString PackagePath = TEXT("/Game/Arcwright/Generated");
	UBlueprint* NewBP = FBlueprintBuilder::CreateBlueprint(DSL, PackagePath);

	if (NewBP)
	{
		FMessageDialog::Open(EAppMsgType::Ok,
			FText::Format(LOCTEXT("ImportSuccess", "Created Blueprint: {0}\nNodes: {1}, Connections: {2}"),
				FText::FromString(DSL.Name),
				FText::AsNumber(DSL.Nodes.Num()),
				FText::AsNumber(DSL.Connections.Num())));
	}
	else
	{
		FMessageDialog::Open(EAppMsgType::Ok,
			LOCTEXT("BuildError", "Failed to build Blueprint from IR. Check Output Log for details."));
	}
}

void FArcwrightModule::OnToggleCommandServer()
{
	if (!CommandServer)
	{
		CommandServer = MakeUnique<FCommandServer>();
	}

	if (CommandServer->IsRunning())
	{
		CommandServer->Stop();
		UE_LOG(LogArcwright, Log, TEXT("Command server stopped via menu"));
	}
	else
	{
		if (CommandServer->Start())
		{
			UE_LOG(LogArcwright, Log, TEXT("Command server started via menu"));
		}
	}
}

void FArcwrightModule::OnOpenGeneratorPanel()
{
	FGlobalTabmanager::Get()->TryInvokeTab(SArcwrightGeneratorPanel::TabId);
}

void FArcwrightModule::OnOpenDashboard()
{
	FGlobalTabmanager::Get()->TryInvokeTab(SArcwrightDashboardPanel::TabId);
}

bool FArcwrightModule::IsCommandServerRunning() const
{
	return CommandServer && CommandServer->IsRunning();
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FArcwrightModule, Arcwright)
