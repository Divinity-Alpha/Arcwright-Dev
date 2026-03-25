#pragma once

#include "CoreMinimal.h"

/**
 * Arcwright — all commands available to all users.
 * $49.99 one-time purchase via FAB Marketplace.
 * No tiers, no API keys, no remote validation.
 */

class FTierGating
{
public:
	/** Every command is always allowed. */
	static bool IsCommandAllowed(const FString& CommandName) { return true; }

	static constexpr int32 TotalCommands = 275;
	static constexpr int32 TotalMCPTools = 287;
};
