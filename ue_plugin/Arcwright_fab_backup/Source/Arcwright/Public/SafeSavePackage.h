#pragma once

#include "CoreMinimal.h"
#include "UObject/SavePackage.h"

/**
 * Safe wrapper around UPackage::SavePackage that fully loads
 * partially-loaded packages before saving. This prevents the
 * "Asset cannot be saved as it has only been partially loaded" crash
 * that occurs when recreating assets that previously existed on disk.
 */
inline bool SafeSavePackage(UPackage* Package, UObject* Asset, const FString& Filename, const FSavePackageArgs& SaveArgs)
{
	if (!Package)
	{
		UE_LOG(LogTemp, Error, TEXT("SafeSavePackage: null package"));
		return false;
	}

	// If the package is only partially loaded, fully load it before saving
	if (!Package->IsFullyLoaded())
	{
		UE_LOG(LogTemp, Warning, TEXT("SafeSavePackage: Package '%s' is partially loaded - fully loading before save"), *Package->GetName());
		Package->FullyLoad();
	}

	// Double-check after full load
	if (!Package->IsFullyLoaded())
	{
		UE_LOG(LogTemp, Error, TEXT("SafeSavePackage: Package '%s' still not fully loaded after FullyLoad() - skipping save"), *Package->GetName());
		return false;
	}

	return UPackage::SavePackage(Package, Asset, *Filename, SaveArgs);
}
