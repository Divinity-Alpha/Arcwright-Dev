#pragma once

#include "CoreMinimal.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

/**
 * Arcwright tier gating with API key validation.
 *
 * Free: 57 commands, no key needed.
 * Pro: All 263 commands + 335 MCP tools — validated via Zuplo gateway.
 * Key format: any non-empty string (zpka_ from Zuplo, validated server-side)
 */

enum class EArcwrightTier : uint8 { Free, Pro };

enum class ELicenseState : uint8
{
	None,          // No key
	Validating,    // API call in progress
	Valid,         // Pro active
	Invalid,       // Key rejected
	OfflineGrace,  // Cache valid, can't reach API
	Expired        // Subscription expired
};

DECLARE_MULTICAST_DELEGATE_TwoParams(FOnLicenseStateChanged, ELicenseState, const FString&);

class FTierGating
{
public:
	static FOnLicenseStateChanged OnLicenseStateChanged;

	static ELicenseState GetLicenseState() { return CurrentState(); }

	static bool IsCommandAllowed(const FString& CommandName)
	{
		return (GetCurrentTier() == EArcwrightTier::Pro) || GetFreeCommands().Contains(CommandName);
	}

	static EArcwrightTier GetCurrentTier()
	{
		static double LastCheck = 0.0;
		static EArcwrightTier Cached = EArcwrightTier::Free;
		double Now = FPlatformTime::Seconds();
		if (Now - LastCheck > 30.0 || LastCheck == 0.0)
		{
			LastCheck = Now;
			Cached = ReadTierFromDisk();
		}
		return Cached;
	}

	static void InvalidateCache() { CachedTierRef() = ReadTierFromDisk(); }

	// ── File paths ──────────────────────────────────────────

	static FString GetArcwrightDir()
	{
		return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Arcwright"));
	}

	static FString GetApiKeyPath()
	{
		return FPaths::Combine(GetArcwrightDir(), TEXT("api_key.txt"));
	}

	static FString GetValidationCachePath()
	{
		return FPaths::Combine(GetArcwrightDir(), TEXT("validation_cache.json"));
	}

	// ── Validation endpoint ─────────────────────────────────

	static FString GetValidationEndpoint()
	{
		// Read from config, fall back to default
		FString Endpoint;
		if (GConfig)
		{
			GConfig->GetString(TEXT("/Script/Arcwright.ArcwrightSettings"),
				TEXT("ValidationEndpoint"), Endpoint, GEngineIni);
		}
		if (Endpoint.IsEmpty())
		{
			Endpoint = TEXT("https://arcwright-main-e0691cb.d2.zuplo.dev/v1/validate_key");
		}
		return Endpoint;
	}

	// ── Key I/O ─────────────────────────────────────────────

	static bool SaveApiKey(const FString& Key)
	{
		EnsureDir();
		return FFileHelper::SaveStringToFile(Key, *GetApiKeyPath());
	}

	static FString ReadApiKey()
	{
		FString Key;
		FFileHelper::LoadFileToString(Key, *GetApiKeyPath());
		Key.TrimStartAndEndInline();
		return Key;
	}

	static void RemoveKeyFiles()
	{
		IPlatformFile& PF = FPlatformFileManager::Get().GetPlatformFile();
		PF.DeleteFile(*GetApiKeyPath());
		PF.DeleteFile(*GetValidationCachePath());
		CurrentState() = ELicenseState::None;
		InvalidateCache();
	}

	// ── Validation cache I/O ────────────────────────────────

	static bool SaveValidationCache(const FString& ApiKey, const FString& Tier,
		const FString& ExpiresAt, const TArray<FString>& Features)
	{
		EnsureDir();
		TSharedPtr<FJsonObject> Obj = MakeShareable(new FJsonObject());
		Obj->SetStringField(TEXT("api_key"), ApiKey);
		Obj->SetBoolField(TEXT("valid"), true);
		Obj->SetStringField(TEXT("tier"), Tier);
		Obj->SetStringField(TEXT("validated_at"), FDateTime::UtcNow().ToIso8601());
		Obj->SetStringField(TEXT("expires_at"), ExpiresAt);

		TArray<TSharedPtr<FJsonValue>> FeatArr;
		for (const FString& F : Features)
			FeatArr.Add(MakeShareable(new FJsonValueString(F)));
		Obj->SetArrayField(TEXT("features"), FeatArr);

		FString Json;
		auto Writer = TJsonWriterFactory<>::Create(&Json);
		FJsonSerializer::Serialize(Obj.ToSharedRef(), Writer);
		return FFileHelper::SaveStringToFile(Json, *GetValidationCachePath());
	}

	static bool ReadValidationCache(FString& OutKey, FDateTime& OutValidatedAt,
		FString& OutTier, FString& OutExpiresAt)
	{
		FString Json;
		if (!FFileHelper::LoadFileToString(Json, *GetValidationCachePath())) return false;

		TSharedPtr<FJsonObject> Obj;
		auto Reader = TJsonReaderFactory<>::Create(Json);
		if (!FJsonSerializer::Deserialize(Reader, Obj) || !Obj.IsValid()) return false;
		if (!Obj->GetBoolField(TEXT("valid"))) return false;

		OutKey = Obj->GetStringField(TEXT("api_key"));
		OutTier = Obj->GetStringField(TEXT("tier"));
		OutExpiresAt = Obj->GetStringField(TEXT("expires_at"));
		FString DateStr = Obj->GetStringField(TEXT("validated_at"));
		return FDateTime::ParseIso8601(*DateStr, OutValidatedAt);
	}

	static int32 GetGraceDaysRemaining()
	{
		FString Key, Tier, Expires;
		FDateTime ValidatedAt;
		if (!ReadValidationCache(Key, ValidatedAt, Tier, Expires)) return -1;
		return FMath::Max(0, 30 - (int32)(FDateTime::UtcNow() - ValidatedAt).GetTotalDays());
	}

	static FString GetMaskedKey()
	{
		FString Key = ReadApiKey();
		if (Key.Len() < 8) return TEXT("****");
		return Key.Left(8) + TEXT("...") + Key.Right(4);
	}

	// ── API validation (async) ──────────────────────────────

	static void ValidateKeyAsync(const FString& Key)
	{
		CurrentState() = ELicenseState::Validating;
		OnLicenseStateChanged.Broadcast(ELicenseState::Validating, TEXT("Validating..."));

		auto Request = FHttpModule::Get().CreateRequest();
		Request->SetURL(GetValidationEndpoint());
		Request->SetVerb(TEXT("POST"));
		Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
		// Key sent as Bearer token in Authorization header (Zuplo API Key Service format)
		Request->SetHeader(TEXT("Authorization"), FString::Printf(TEXT("Bearer %s"), *Key));

		FString KeyCopy = Key;
		Request->OnProcessRequestComplete().BindLambda(
			[KeyCopy](FHttpRequestPtr Req, FHttpResponsePtr Resp, bool bOk)
			{
				HandleValidateResponse(KeyCopy, Resp, bOk);
			});
		Request->ProcessRequest();
	}

	static void DeactivateKeyAsync()
	{
		FString Key = ReadApiKey();
		RemoveKeyFiles();
		OnLicenseStateChanged.Broadcast(ELicenseState::None, TEXT("Key deactivated."));

		// Fire-and-forget deactivate call
		if (!Key.IsEmpty())
		{
			auto Request = FHttpModule::Get().CreateRequest();
			FString Endpoint = GetValidationEndpoint().Replace(TEXT("validate_key"), TEXT("deactivate_key"));
			Request->SetURL(Endpoint);
			Request->SetVerb(TEXT("POST"));
			Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
			Request->SetHeader(TEXT("Authorization"), FString::Printf(TEXT("Bearer %s"), *Key));
			Request->ProcessRequest();
		}
	}

	static void CheckOnStartup()
	{
		FString Key = ReadApiKey();
		if (Key.IsEmpty()) { CurrentState() = ELicenseState::None; return; }

		FString CachedKey, Tier, Expires;
		FDateTime ValidatedAt;
		if (!ReadValidationCache(CachedKey, ValidatedAt, Tier, Expires))
		{
			CurrentState() = ELicenseState::None;
			return;
		}

		FTimespan Age = FDateTime::UtcNow() - ValidatedAt;
		if (Age.GetTotalDays() < 7.0)
			CurrentState() = ELicenseState::Valid;
		else if (Age.GetTotalDays() < 30.0)
		{
			CurrentState() = ELicenseState::OfflineGrace;
			ValidateKeyAsync(Key);  // silent background revalidation
		}
		else
		{
			CurrentState() = ELicenseState::Expired;
			ValidateKeyAsync(Key);
		}
		InvalidateCache();
	}

	// ── Free command set ────────────────────────────────────

	static const TSet<FString>& GetFreeCommands()
	{
		static TSet<FString> Commands = {
			TEXT("health_check"), TEXT("get_server_info"), TEXT("get_version"),
			TEXT("create_blueprint"), TEXT("create_blueprint_from_dsl"),
			TEXT("delete_blueprint"), TEXT("get_blueprint_details"), TEXT("get_blueprint_info"),
			TEXT("find_blueprints"), TEXT("get_all_blueprints"),
			TEXT("spawn_actor_at"), TEXT("delete_actor"), TEXT("find_actors"), TEXT("get_actor_properties"),
			TEXT("set_actor_location"), TEXT("set_actor_rotation"), TEXT("set_actor_scale"),
			TEXT("apply_material"), TEXT("get_all_materials"),
			TEXT("setup_scene_lighting"),
			TEXT("get_level_info"), TEXT("list_project_assets"),
			TEXT("set_variable"), TEXT("get_variable"),
			TEXT("set_game_mode"),
			TEXT("spawn_template"), TEXT("setup_game_base"),
			TEXT("find_actors_by_class"), TEXT("find_actors_by_tag"), TEXT("get_actor_bounds"),
			TEXT("set_actor_visibility"), TEXT("set_actor_mobility"), TEXT("set_actor_tags"),
			TEXT("set_camera_properties"), TEXT("compile_blueprint"),
			TEXT("save_all"), TEXT("compile_project"),
			TEXT("play_in_editor"), TEXT("stop_pie"), TEXT("quit_editor"),
			TEXT("get_blueprint_node_types"), TEXT("create_nav_mesh_bounds"),
			TEXT("play_sound_at_location"), TEXT("set_collision_preset"), TEXT("set_physics_enabled"),
			TEXT("set_fog_settings"), TEXT("set_post_process"), TEXT("set_sky_atmosphere"),
			TEXT("create_widget_blueprint"), TEXT("import_from_ir"),
			TEXT("take_viewport_screenshot"),
			TEXT("undo"), TEXT("redo"), TEXT("get_undo_history"),
			TEXT("begin_undo_group"), TEXT("end_undo_group"),
		};
		return Commands;
	}

	static int32 GetFreeCommandCount() { return GetFreeCommands().Num(); }
	static constexpr int32 TotalCommands = 263;
	static constexpr int32 TotalMCPTools = 335;

private:
	static EArcwrightTier& CachedTierRef() { static EArcwrightTier C = EArcwrightTier::Free; return C; }
	static ELicenseState& CurrentState() { static ELicenseState S = ELicenseState::None; return S; }

	static void EnsureDir()
	{
		IPlatformFile& PF = FPlatformFileManager::Get().GetPlatformFile();
		PF.CreateDirectoryTree(*GetArcwrightDir());
	}

	static EArcwrightTier ReadTierFromDisk()
	{
		FString Key = ReadApiKey();
		if (Key.IsEmpty()) return EArcwrightTier::Free;

		FString CachedKey, Tier, Expires;
		FDateTime ValidatedAt;
		if (!ReadValidationCache(CachedKey, ValidatedAt, Tier, Expires)) return EArcwrightTier::Free;
		if (CachedKey != Key) return EArcwrightTier::Free;
		if ((FDateTime::UtcNow() - ValidatedAt).GetTotalDays() >= 30.0) return EArcwrightTier::Free;
		return (Tier == TEXT("pro")) ? EArcwrightTier::Pro : EArcwrightTier::Free;
	}

	static void HandleValidateResponse(const FString& Key, FHttpResponsePtr Response, bool bSuccess)
	{
		if (!bSuccess || !Response.IsValid())
		{
			// Offline — check grace
			FString CKey, Tier, Expires;
			FDateTime ValidAt;
			if (ReadValidationCache(CKey, ValidAt, Tier, Expires) && CKey == Key)
			{
				if ((FDateTime::UtcNow() - ValidAt).GetTotalDays() < 30.0)
				{
					CurrentState() = ELicenseState::OfflineGrace;
					InvalidateCache();
					int32 Days = 30 - (int32)(FDateTime::UtcNow() - ValidAt).GetTotalDays();
					OnLicenseStateChanged.Broadcast(ELicenseState::OfflineGrace,
						FString::Printf(TEXT("Offline — Pro active for %d more days."), Days));
					return;
				}
			}
			CurrentState() = ELicenseState::Invalid;
			OnLicenseStateChanged.Broadcast(ELicenseState::Invalid,
				TEXT("Unable to validate. Connect to the internet."));
			return;
		}

		FString Body = Response->GetContentAsString();
		TSharedPtr<FJsonObject> Json;
		auto Reader = TJsonReaderFactory<>::Create(Body);
		if (!FJsonSerializer::Deserialize(Reader, Json) || !Json.IsValid())
		{
			CurrentState() = ELicenseState::Invalid;
			OnLicenseStateChanged.Broadcast(ELicenseState::Invalid, TEXT("Invalid server response."));
			return;
		}

		bool bValid = Json->GetBoolField(TEXT("valid"));
		FString Tier = Json->GetStringField(TEXT("tier"));
		FString Status = Json->GetStringField(TEXT("status"));

		if (bValid && Tier == TEXT("pro"))
		{
			FString ExpiresAt = Json->HasField(TEXT("expires_at")) ? Json->GetStringField(TEXT("expires_at")) : TEXT("");
			TArray<FString> Features;
			if (Json->HasField(TEXT("features")))
			{
				for (const auto& F : Json->GetArrayField(TEXT("features")))
					Features.Add(F->AsString());
			}

			SaveApiKey(Key);
			SaveValidationCache(Key, Tier, ExpiresAt, Features);
			CurrentState() = ELicenseState::Valid;
			InvalidateCache();
			OnLicenseStateChanged.Broadcast(ELicenseState::Valid,
				TEXT("Pro activated! All commands unlocked."));
		}
		else
		{
			FString Msg = Json->HasField(TEXT("message"))
				? Json->GetStringField(TEXT("message"))
				: TEXT("Invalid or expired key.");
			CurrentState() = (Status == TEXT("expired")) ? ELicenseState::Expired : ELicenseState::Invalid;
			OnLicenseStateChanged.Broadcast(CurrentState(), Msg);
		}
	}
};
