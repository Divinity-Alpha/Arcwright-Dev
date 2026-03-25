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
	void OnToggleCommandServer();
	void OnOpenDashboard();
	bool IsCommandServerRunning() const;

	TSharedPtr<class FUICommandList> PluginCommands;
	TUniquePtr<FCommandServer> CommandServer;
	TSharedPtr<FSlateStyleSet> BrandStyleSet;
};
