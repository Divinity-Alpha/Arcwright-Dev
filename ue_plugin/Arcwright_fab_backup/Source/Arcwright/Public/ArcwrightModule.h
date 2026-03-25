#pragma once

#include "Modules/ModuleManager.h"
#include "Styling/SlateStyleRegistry.h"
#include "Styling/SlateStyle.h"

class FCommandServer;

class FArcwrightModule : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

	/** Get the command server (for panel to dispatch batch commands) */
	FCommandServer* GetCommandServer() const { return CommandServer.Get(); }

private:
	void RegisterMenus();
	void RegisterBrandStyle();
	void UnregisterBrandStyle();
	void OnImportDSLClicked();
	void OnToggleCommandServer();
	void OnOpenGeneratorPanel();
	void OnOpenDashboard();
	bool IsCommandServerRunning() const;

	// MCP server auto-launch
	void LaunchMCPServer();
	void StopMCPServer();
	bool IsMCPServerRunning();

	TSharedPtr<class FUICommandList> PluginCommands;
	TUniquePtr<FCommandServer> CommandServer;
	TSharedPtr<FSlateStyleSet> BrandStyleSet;

	FProcHandle MCPServerProcHandle;
	bool bMCPServerAutoLaunched = false;
};
