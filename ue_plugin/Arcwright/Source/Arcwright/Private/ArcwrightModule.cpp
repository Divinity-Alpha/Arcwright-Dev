// Copyright 2026 Divinity Alpha. All Rights Reserved.
#include "ArcwrightModule.h"
#include "CommandServer.h"
#include "TierGating.h"
#include "ArcwrightDashboardPanel.h"

#include "ToolMenus.h"
#include "Framework/Docking/TabManager.h"
#include "Misc/Paths.h"
#include "Styling/SlateStyleRegistry.h"

#define LOCTEXT_NAMESPACE "FArcwrightModule"

void FArcwrightModule::StartupModule()
{
	RegisterBrandStyle();

	UToolMenus::RegisterStartupCallback(
		FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FArcwrightModule::RegisterMenus));

	SArcwrightDashboardPanel::RegisterTab();

	// Auto-start the command server
	CommandServer = MakeUnique<FCommandServer>();
	if (!CommandServer->Start())
	{
		UE_LOG(LogArcwright, Warning, TEXT("Command server failed to start on plugin load"));
	}

	// All commands available — no tier gating
}

void FArcwrightModule::ShutdownModule()
{
	SArcwrightDashboardPanel::UnregisterTab();

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

	if (!FSlateStyleRegistry::FindSlateStyle(TEXT("ArcwrightStyle")))
	{
		FSlateStyleRegistry::RegisterSlateStyle(*BrandStyleSet);
	}
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
