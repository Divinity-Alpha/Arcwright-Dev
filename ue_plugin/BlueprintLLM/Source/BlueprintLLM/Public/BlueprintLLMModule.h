#pragma once

#include "Modules/ModuleManager.h"

class FCommandServer;

class FBlueprintLLMModule : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

private:
	void RegisterMenus();
	void OnImportDSLClicked();
	void OnToggleCommandServer();
	bool IsCommandServerRunning() const;

	TSharedPtr<class FUICommandList> PluginCommands;
	TUniquePtr<FCommandServer> CommandServer;
};
