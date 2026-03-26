// Copyright 2026 Divinity Alpha. All Rights Reserved.
#include "ArcwrightStats.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/PlatformFileManager.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

DECLARE_LOG_CATEGORY_EXTERN(LogArcwright, Log, All);

// ── Time saved estimates (seconds per successful command) ────

static const TMap<FString, int32> TimeSavedMap = {
	// Blueprint creation
	{TEXT("import_from_ir"), 600},
	{TEXT("create_blueprint_from_dsl"), 600},
	{TEXT("create_save_game"), 120},

	// BT / DT
	{TEXT("create_behavior_tree"), 480},
	{TEXT("create_data_table"), 300},

	// Actor spawn/delete
	{TEXT("spawn_actor_at"), 15},
	{TEXT("copy_actor"), 15},
	{TEXT("delete_actor"), 5},

	// Materials
	{TEXT("create_simple_material"), 120},
	{TEXT("create_material_instance"), 120},
	{TEXT("create_textured_material"), 180},
	{TEXT("apply_material"), 10},
	{TEXT("set_actor_material"), 10},

	// Nodes / connections
	{TEXT("add_node"), 20},
	{TEXT("add_connection"), 8},

	// Components
	{TEXT("add_component"), 30},

	// AI / Scene
	{TEXT("setup_ai_for_pawn"), 300},
	{TEXT("setup_scene_lighting"), 120},
	{TEXT("set_game_mode"), 30},

	// Widgets
	{TEXT("create_widget_blueprint"), 180},
	{TEXT("add_widget_child"), 20},

	// Sequencer
	{TEXT("create_sequence"), 120},
	{TEXT("add_sequence_track"), 30},
	{TEXT("add_keyframe"), 15},

	// Import
	{TEXT("import_static_mesh"), 60},
	{TEXT("import_texture"), 30},
	{TEXT("import_sound"), 30},

	// Batch (per-op, affected count multiplied separately)
	{TEXT("batch_set_variable"), 15},
	{TEXT("batch_add_component"), 30},
	{TEXT("batch_apply_material"), 10},
	{TEXT("batch_set_property"), 10},
	{TEXT("batch_delete_actors"), 5},
	{TEXT("batch_replace_material"), 10},
	{TEXT("batch_scale_actors"), 10},
	{TEXT("batch_move_actors"), 10},

	// Spawn patterns (count multiplied separately)
	{TEXT("spawn_actor_grid"), 15},
	{TEXT("spawn_actor_circle"), 15},
	{TEXT("spawn_actor_line"), 15},

	// Save / misc
	{TEXT("save_all"), 5},
	{TEXT("save_level"), 5},
};

// Commands that need their count extracted from results for time saved
static const TSet<FString> BatchCommands = {
	TEXT("batch_set_variable"), TEXT("batch_add_component"), TEXT("batch_apply_material"),
	TEXT("batch_set_property"), TEXT("batch_delete_actors"), TEXT("batch_replace_material"),
	TEXT("batch_scale_actors"), TEXT("batch_move_actors"),
	TEXT("spawn_actor_grid"), TEXT("spawn_actor_circle"), TEXT("spawn_actor_line"),
};

// ── Construction / destruction ───────────────────────────────

FArcwrightStats::FArcwrightStats()
{
	SessionStartTime = FDateTime::UtcNow();
}

FArcwrightStats::~FArcwrightStats()
{
	Shutdown();
}

void FArcwrightStats::Initialize()
{
	if (bInitialized) return;

	LoadFromDisk();

	SessionStartTime = FDateTime::UtcNow();
	TotalSessions++;

	if (FirstUseDate.IsEmpty())
	{
		FirstUseDate = FDateTime::UtcNow().ToIso8601();
	}

	bDirty = true;
	SaveToDisk();

	// Auto-save every 60 seconds
	AutoSaveHandle = FTSTicker::GetCoreTicker().AddTicker(
		FTickerDelegate::CreateRaw(this, &FArcwrightStats::OnAutoSaveTick),
		60.0f
	);

	bInitialized = true;
	UE_LOG(LogArcwright, Log, TEXT("Arcwright Stats initialized (session %lld, %lld lifetime commands)"), TotalSessions, TotalCommands);
}

void FArcwrightStats::Shutdown()
{
	if (!bInitialized) return;

	if (AutoSaveHandle.IsValid())
	{
		FTSTicker::GetCoreTicker().RemoveTicker(AutoSaveHandle);
		AutoSaveHandle.Reset();
	}

	SaveToDisk();
	bInitialized = false;
}

// ── Recording ────────────────────────────────────────────────

void FArcwrightStats::RecordCommand(const FString& CommandName, bool bSuccess, const TSharedPtr<FJsonObject>& ResultData)
{
	FScopeLock Lock(&StatsLock);

	SessionCommands++;
	TotalCommands++;

	if (bSuccess)
	{
		SessionSuccesses++;
		TotalSuccesses++;
	}
	else
	{
		SessionErrors++;
		TotalErrors++;
	}

	if (bSuccess)
	{
		IncrementForCommand(CommandName, bSuccess, ResultData);
	}

	// Append to rolling command log
	FArcwrightCommandLogEntry Entry;
	Entry.Timestamp   = FDateTime::Now();
	Entry.CommandName = CommandName;
	Entry.bSuccess    = bSuccess;
	if (!bSuccess && ResultData.IsValid())
	{
		ResultData->TryGetStringField(TEXT("message"), Entry.ErrorMessage);
	}
	CommandLog.Add(Entry);
	if (CommandLog.Num() > MaxCommandLogEntries)
	{
		CommandLog.RemoveAt(0, CommandLog.Num() - MaxCommandLogEntries, EAllowShrinking::No);
	}

	bDirty = true;
}

void FArcwrightStats::IncrementForCommand(const FString& CommandName, bool bSuccess, const TSharedPtr<FJsonObject>& ResultData)
{
	// Blueprint creation
	if (CommandName == TEXT("import_from_ir") || CommandName == TEXT("create_blueprint_from_dsl") || CommandName == TEXT("create_save_game"))
	{
		SessionBlueprintsCreated++;
		TotalBlueprintsCreated++;
	}

	// BT
	if (CommandName == TEXT("create_behavior_tree"))
	{
		TotalBTsCreated++;
	}

	// DT
	if (CommandName == TEXT("create_data_table"))
	{
		TotalDTsCreated++;
	}

	// Actor spawning
	if (CommandName == TEXT("spawn_actor_at") || CommandName == TEXT("copy_actor"))
	{
		SessionActorsSpawned++;
		TotalActorsSpawned++;
	}

	// Spawn patterns — extract count from result
	if (CommandName == TEXT("spawn_actor_grid") || CommandName == TEXT("spawn_actor_circle") || CommandName == TEXT("spawn_actor_line"))
	{
		int32 Count = 1;
		if (ResultData.IsValid() && ResultData->HasField(TEXT("spawned")))
		{
			Count = (int32)ResultData->GetNumberField(TEXT("spawned"));
		}
		else if (ResultData.IsValid() && ResultData->HasField(TEXT("actors_spawned")))
		{
			Count = (int32)ResultData->GetNumberField(TEXT("actors_spawned"));
		}
		SessionActorsSpawned += Count;
		TotalActorsSpawned += Count;
	}

	// Actor deletion
	if (CommandName == TEXT("delete_actor"))
	{
		TotalActorsDeleted++;
	}
	if (CommandName == TEXT("batch_delete_actors"))
	{
		int32 Count = 1;
		if (ResultData.IsValid() && ResultData->HasField(TEXT("succeeded")))
		{
			Count = (int32)ResultData->GetNumberField(TEXT("succeeded"));
		}
		TotalActorsDeleted += Count;
	}

	// Materials
	if (CommandName == TEXT("apply_material") || CommandName == TEXT("set_actor_material") ||
		CommandName == TEXT("create_simple_material") || CommandName == TEXT("create_material_instance") ||
		CommandName == TEXT("create_textured_material"))
	{
		TotalMaterialsApplied++;
	}

	// Batch operations
	if (BatchCommands.Contains(CommandName) && !CommandName.StartsWith(TEXT("spawn_")))
	{
		TotalBatchOps++;
		int32 Affected = 1;
		if (ResultData.IsValid() && ResultData->HasField(TEXT("succeeded")))
		{
			Affected = (int32)ResultData->GetNumberField(TEXT("succeeded"));
		}
		TotalBatchAffected += Affected;
	}

	// Nodes
	if (CommandName == TEXT("add_node"))
	{
		TotalNodesCreated++;
	}
	if (CommandName == TEXT("add_nodes_batch"))
	{
		int32 Count = 1;
		if (ResultData.IsValid() && ResultData->HasField(TEXT("succeeded")))
		{
			Count = (int32)ResultData->GetNumberField(TEXT("succeeded"));
		}
		TotalNodesCreated += Count;
	}

	// Connections
	if (CommandName == TEXT("add_connection"))
	{
		TotalConnectionsWired++;
	}
	if (CommandName == TEXT("add_connections_batch"))
	{
		int32 Count = 1;
		if (ResultData.IsValid() && ResultData->HasField(TEXT("succeeded")))
		{
			Count = (int32)ResultData->GetNumberField(TEXT("succeeded"));
		}
		TotalConnectionsWired += Count;
	}

	// Time saved estimate
	const int32* BaseTime = TimeSavedMap.Find(CommandName);
	if (BaseTime)
	{
		if (BatchCommands.Contains(CommandName))
		{
			// Batch: multiply by affected count
			int32 Affected = 1;
			if (ResultData.IsValid())
			{
				if (ResultData->HasField(TEXT("succeeded")))
					Affected = FMath::Max(1, (int32)ResultData->GetNumberField(TEXT("succeeded")));
				else if (ResultData->HasField(TEXT("spawned")))
					Affected = FMath::Max(1, (int32)ResultData->GetNumberField(TEXT("spawned")));
				else if (ResultData->HasField(TEXT("actors_spawned")))
					Affected = FMath::Max(1, (int32)ResultData->GetNumberField(TEXT("actors_spawned")));
			}
			TimeSavedSeconds += (*BaseTime) * Affected;
		}
		else
		{
			TimeSavedSeconds += *BaseTime;
		}
	}
	else
	{
		// Default: 10 seconds for any other successful command
		TimeSavedSeconds += 10;
	}
}

// ── JSON output ──────────────────────────────────────────────

TSharedPtr<FJsonObject> FArcwrightStats::GetStatsJson() const
{
	FScopeLock Lock(&StatsLock);

	TSharedPtr<FJsonObject> Root = MakeShareable(new FJsonObject());

	// Session stats
	TSharedPtr<FJsonObject> Session = MakeShareable(new FJsonObject());
	double DurationSec = (FDateTime::UtcNow() - SessionStartTime).GetTotalSeconds();
	Session->SetNumberField(TEXT("commands"), SessionCommands);
	Session->SetNumberField(TEXT("blueprints_created"), SessionBlueprintsCreated);
	Session->SetNumberField(TEXT("actors_spawned"), SessionActorsSpawned);
	Session->SetNumberField(TEXT("errors"), SessionErrors);
	Session->SetNumberField(TEXT("successes"), SessionSuccesses);
	if (SessionCommands > 0)
	{
		double Rate = (double)SessionSuccesses / (double)SessionCommands * 100.0;
		Session->SetNumberField(TEXT("success_rate"), FMath::RoundToDouble(Rate * 100.0) / 100.0);
	}
	else
	{
		Session->SetNumberField(TEXT("success_rate"), 100.0);
	}
	Session->SetNumberField(TEXT("duration_seconds"), (int64)DurationSec);
	Session->SetStringField(TEXT("duration_human"), FormatDuration(DurationSec));
	Root->SetObjectField(TEXT("session"), Session);

	// Lifetime stats
	TSharedPtr<FJsonObject> Lifetime = MakeShareable(new FJsonObject());
	Lifetime->SetNumberField(TEXT("total_commands"), TotalCommands);
	Lifetime->SetNumberField(TEXT("blueprints_created"), TotalBlueprintsCreated);
	Lifetime->SetNumberField(TEXT("behavior_trees_created"), TotalBTsCreated);
	Lifetime->SetNumberField(TEXT("data_tables_created"), TotalDTsCreated);
	Lifetime->SetNumberField(TEXT("actors_spawned"), TotalActorsSpawned);
	Lifetime->SetNumberField(TEXT("actors_deleted"), TotalActorsDeleted);
	Lifetime->SetNumberField(TEXT("materials_applied"), TotalMaterialsApplied);
	Lifetime->SetNumberField(TEXT("batch_operations"), TotalBatchOps);
	Lifetime->SetNumberField(TEXT("batch_affected_count"), TotalBatchAffected);
	Lifetime->SetNumberField(TEXT("ai_generations"), TotalAIGenerations);
	Lifetime->SetNumberField(TEXT("nodes_created"), TotalNodesCreated);
	Lifetime->SetNumberField(TEXT("connections_wired"), TotalConnectionsWired);
	Lifetime->SetNumberField(TEXT("errors"), TotalErrors);
	Lifetime->SetNumberField(TEXT("successes"), TotalSuccesses);
	if (TotalCommands > 0)
	{
		double Rate = (double)TotalSuccesses / (double)TotalCommands * 100.0;
		Lifetime->SetNumberField(TEXT("success_rate"), FMath::RoundToDouble(Rate * 100.0) / 100.0);
	}
	else
	{
		Lifetime->SetNumberField(TEXT("success_rate"), 100.0);
	}
	Lifetime->SetNumberField(TEXT("total_sessions"), TotalSessions);
	Lifetime->SetStringField(TEXT("first_use_date"), FirstUseDate);
	Lifetime->SetNumberField(TEXT("estimated_time_saved_minutes"), TimeSavedSeconds / 60);
	Lifetime->SetStringField(TEXT("estimated_time_saved_human"), FormatTimeSaved(TimeSavedSeconds));
	Root->SetObjectField(TEXT("lifetime"), Lifetime);

	return Root;
}

// ── Reset ────────────────────────────────────────────────────

void FArcwrightStats::ResetSession()
{
	FScopeLock Lock(&StatsLock);
	SessionCommands = 0;
	SessionBlueprintsCreated = 0;
	SessionActorsSpawned = 0;
	SessionErrors = 0;
	SessionSuccesses = 0;
	SessionStartTime = FDateTime::UtcNow();
}

void FArcwrightStats::ResetLifetime()
{
	FScopeLock Lock(&StatsLock);
	TotalCommands = 0;
	TotalBlueprintsCreated = 0;
	TotalBTsCreated = 0;
	TotalDTsCreated = 0;
	TotalActorsSpawned = 0;
	TotalActorsDeleted = 0;
	TotalMaterialsApplied = 0;
	TotalBatchOps = 0;
	TotalBatchAffected = 0;
	TotalAIGenerations = 0;
	TotalNodesCreated = 0;
	TotalConnectionsWired = 0;
	TotalErrors = 0;
	TotalSuccesses = 0;
	TotalSessions = 0;
	TimeSavedSeconds = 0;
	FirstUseDate = FDateTime::UtcNow().ToIso8601();
	bDirty = true;
	SaveToDisk();
}

// ── Persistence ──────────────────────────────────────────────

FString FArcwrightStats::GetStatsFilePath() const
{
	return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Arcwright"), TEXT("stats.json"));
}

void FArcwrightStats::LoadFromDisk()
{
	FString FilePath = GetStatsFilePath();
	FString JsonStr;

	if (!FFileHelper::LoadFileToString(JsonStr, *FilePath))
	{
		UE_LOG(LogArcwright, Log, TEXT("No existing stats file at %s — starting fresh"), *FilePath);
		return;
	}

	TSharedPtr<FJsonObject> Root;
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonStr);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		UE_LOG(LogArcwright, Warning, TEXT("Failed to parse stats.json — starting fresh"));
		return;
	}

	const TSharedPtr<FJsonObject>* LT = nullptr;
	if (Root->TryGetObjectField(TEXT("lifetime"), LT) && LT->IsValid())
	{
		TotalCommands = (int64)(*LT)->GetNumberField(TEXT("total_commands"));
		TotalBlueprintsCreated = (int64)(*LT)->GetNumberField(TEXT("blueprints_created"));
		TotalBTsCreated = (int64)(*LT)->GetNumberField(TEXT("behavior_trees_created"));
		TotalDTsCreated = (int64)(*LT)->GetNumberField(TEXT("data_tables_created"));
		TotalActorsSpawned = (int64)(*LT)->GetNumberField(TEXT("actors_spawned"));
		TotalActorsDeleted = (int64)(*LT)->GetNumberField(TEXT("actors_deleted"));
		TotalMaterialsApplied = (int64)(*LT)->GetNumberField(TEXT("materials_applied"));
		TotalBatchOps = (int64)(*LT)->GetNumberField(TEXT("batch_operations"));
		TotalBatchAffected = (int64)(*LT)->GetNumberField(TEXT("batch_affected_count"));
		TotalAIGenerations = (int64)(*LT)->GetNumberField(TEXT("ai_generations"));
		TotalNodesCreated = (int64)(*LT)->GetNumberField(TEXT("nodes_created"));
		TotalConnectionsWired = (int64)(*LT)->GetNumberField(TEXT("connections_wired"));
		TotalErrors = (int64)(*LT)->GetNumberField(TEXT("errors"));
		TotalSuccesses = (int64)(*LT)->GetNumberField(TEXT("successes"));
		TotalSessions = (int64)(*LT)->GetNumberField(TEXT("total_sessions"));
		TimeSavedSeconds = (int64)(*LT)->GetNumberField(TEXT("time_saved_seconds"));
		FirstUseDate = (*LT)->GetStringField(TEXT("first_use_date"));
	}

	UE_LOG(LogArcwright, Log, TEXT("Loaded stats: %lld commands, %lld sessions, first use %s"), TotalCommands, TotalSessions, *FirstUseDate);
}

void FArcwrightStats::SaveToDisk()
{
	if (!bDirty) return;

	FString FilePath = GetStatsFilePath();

	// Ensure directory exists
	FString Dir = FPaths::GetPath(FilePath);
	IPlatformFile& PlatformFile = FPlatformFileManager::Get().GetPlatformFile();
	if (!PlatformFile.DirectoryExists(*Dir))
	{
		PlatformFile.CreateDirectoryTree(*Dir);
	}

	TSharedPtr<FJsonObject> Root = MakeShareable(new FJsonObject());
	Root->SetNumberField(TEXT("version"), 1);

	TSharedPtr<FJsonObject> LT = MakeShareable(new FJsonObject());
	{
		FScopeLock Lock(&StatsLock);
		LT->SetNumberField(TEXT("total_commands"), TotalCommands);
		LT->SetNumberField(TEXT("blueprints_created"), TotalBlueprintsCreated);
		LT->SetNumberField(TEXT("behavior_trees_created"), TotalBTsCreated);
		LT->SetNumberField(TEXT("data_tables_created"), TotalDTsCreated);
		LT->SetNumberField(TEXT("actors_spawned"), TotalActorsSpawned);
		LT->SetNumberField(TEXT("actors_deleted"), TotalActorsDeleted);
		LT->SetNumberField(TEXT("materials_applied"), TotalMaterialsApplied);
		LT->SetNumberField(TEXT("batch_operations"), TotalBatchOps);
		LT->SetNumberField(TEXT("batch_affected_count"), TotalBatchAffected);
		LT->SetNumberField(TEXT("ai_generations"), TotalAIGenerations);
		LT->SetNumberField(TEXT("nodes_created"), TotalNodesCreated);
		LT->SetNumberField(TEXT("connections_wired"), TotalConnectionsWired);
		LT->SetNumberField(TEXT("errors"), TotalErrors);
		LT->SetNumberField(TEXT("successes"), TotalSuccesses);
		LT->SetNumberField(TEXT("total_sessions"), TotalSessions);
		LT->SetNumberField(TEXT("time_saved_seconds"), TimeSavedSeconds);
		LT->SetStringField(TEXT("first_use_date"), FirstUseDate);
	}
	Root->SetObjectField(TEXT("lifetime"), LT);

	FString OutputStr;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutputStr);
	FJsonSerializer::Serialize(Root.ToSharedRef(), Writer);

	if (FFileHelper::SaveStringToFile(OutputStr, *FilePath))
	{
		bDirty = false;
	}
	else
	{
		UE_LOG(LogArcwright, Warning, TEXT("Failed to save stats to %s"), *FilePath);
	}
}

bool FArcwrightStats::OnAutoSaveTick(float DeltaTime)
{
	SaveToDisk();
	return true; // Keep ticking
}

// ── Formatting helpers ───────────────────────────────────────

FString FArcwrightStats::FormatDuration(double Seconds) const
{
	int32 S = (int32)Seconds;
	int32 H = S / 3600;
	int32 M = (S % 3600) / 60;
	int32 Sec = S % 60;

	if (H > 0)
		return FString::Printf(TEXT("%dh %dm %ds"), H, M, Sec);
	if (M > 0)
		return FString::Printf(TEXT("%dm %ds"), M, Sec);
	return FString::Printf(TEXT("%ds"), Sec);
}

FString FArcwrightStats::FormatTimeSaved(int64 Seconds) const
{
	double Minutes = (double)Seconds / 60.0;
	if (Minutes < 120.0)
		return FString::Printf(TEXT("%.0f minutes"), Minutes);

	double Hours = Minutes / 60.0;
	if (Hours < 48.0)
		return FString::Printf(TEXT("%.1f hours"), Hours);

	double Days = Hours / 24.0;
	return FString::Printf(TEXT("%.1f days"), Days);
}
