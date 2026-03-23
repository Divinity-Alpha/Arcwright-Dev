#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "Containers/Ticker.h"

/** One entry in the rolling command log shown on the dashboard */
struct FArcwrightCommandLogEntry
{
	FDateTime Timestamp;
	FString   CommandName;
	bool      bSuccess = true;
	FString   ErrorMessage;
};

/**
 * Tracks Arcwright usage statistics — session and lifetime.
 * Persists lifetime stats to Saved/Arcwright/stats.json.
 * Auto-saves every 60 seconds via FTSTicker.
 */
class FArcwrightStats
{
public:
	FArcwrightStats();
	~FArcwrightStats();

	/** Load from disk, start session, begin auto-save timer */
	void Initialize();

	/** Save to disk, stop timer */
	void Shutdown();

	/** Record a command execution with its result data */
	void RecordCommand(const FString& CommandName, bool bSuccess, const TSharedPtr<FJsonObject>& ResultData = nullptr);

	/** Get all stats as JSON (session + lifetime) */
	TSharedPtr<FJsonObject> GetStatsJson() const;

	/** Reset session stats */
	void ResetSession();

	/** Reset lifetime stats */
	void ResetLifetime();

	/** Force save to disk immediately */
	void SaveToDisk();

	/** Returns a copy of the last-N command log entries (thread-safe) */
	TArray<FArcwrightCommandLogEntry> GetCommandLog() const
	{
		FScopeLock Lock(&StatsLock);
		return CommandLog;
	}

	// Expose key session values for direct polling from the dashboard panel
	int32 GetSessionCommands()  const { FScopeLock L(&StatsLock); return SessionCommands;  }
	int32 GetSessionSuccesses() const { FScopeLock L(&StatsLock); return SessionSuccesses; }
	int32 GetSessionErrors()    const { FScopeLock L(&StatsLock); return SessionErrors;    }
	FDateTime GetSessionStartTime() const { return SessionStartTime; }

	int64 GetTotalCommands()     const { FScopeLock L(&StatsLock); return TotalCommands;          }
	int64 GetTotalBlueprints()   const { FScopeLock L(&StatsLock); return TotalBlueprintsCreated; }
	int64 GetTotalBTs()          const { FScopeLock L(&StatsLock); return TotalBTsCreated;        }
	int64 GetTotalDTs()          const { FScopeLock L(&StatsLock); return TotalDTsCreated;        }
	int64 GetTotalActors()       const { FScopeLock L(&StatsLock); return TotalActorsSpawned;     }
	int64 GetTotalMaterials()    const { FScopeLock L(&StatsLock); return TotalMaterialsApplied;  }
	int64 GetTotalSessions()     const { FScopeLock L(&StatsLock); return TotalSessions;          }
	int64 GetTimeSavedSeconds()  const { FScopeLock L(&StatsLock); return TimeSavedSeconds;       }
	FString GetFirstUseDate()    const { FScopeLock L(&StatsLock); return FirstUseDate;           }

private:
	void LoadFromDisk();
	bool OnAutoSaveTick(float DeltaTime);
	FString GetStatsFilePath() const;
	void IncrementForCommand(const FString& CommandName, bool bSuccess, const TSharedPtr<FJsonObject>& ResultData);
	FString FormatDuration(double Seconds) const;
	FString FormatTimeSaved(int64 Seconds) const;

	// Session stats (reset each editor launch)
	int32 SessionCommands = 0;
	int32 SessionBlueprintsCreated = 0;
	int32 SessionActorsSpawned = 0;
	int32 SessionErrors = 0;
	int32 SessionSuccesses = 0;
	FDateTime SessionStartTime;

	// Lifetime stats (persisted to disk)
	int64 TotalCommands = 0;
	int64 TotalBlueprintsCreated = 0;
	int64 TotalBTsCreated = 0;
	int64 TotalDTsCreated = 0;
	int64 TotalActorsSpawned = 0;
	int64 TotalActorsDeleted = 0;
	int64 TotalMaterialsApplied = 0;
	int64 TotalBatchOps = 0;
	int64 TotalBatchAffected = 0;
	int64 TotalAIGenerations = 0;
	int64 TotalNodesCreated = 0;
	int64 TotalConnectionsWired = 0;
	int64 TotalErrors = 0;
	int64 TotalSuccesses = 0;
	int64 TotalSessions = 0;
	int64 TimeSavedSeconds = 0;
	FString FirstUseDate;

	// Rolling command log (last 10 entries)
	TArray<FArcwrightCommandLogEntry> CommandLog;
	static constexpr int32 MaxCommandLogEntries = 10;

	// Auto-save
	FTSTicker::FDelegateHandle AutoSaveHandle;
	bool bDirty = false;
	bool bInitialized = false;

	mutable FCriticalSection StatsLock;
};
