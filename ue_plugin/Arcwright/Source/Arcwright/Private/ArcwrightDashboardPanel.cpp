#include "ArcwrightDashboardPanel.h"
#include "TierGating.h"
#include "ArcwrightModule.h"
#include "CommandServer.h"
#include "ArcwrightStats.h"

#include "Framework/Docking/TabManager.h"
#include "Widgets/Docking/SDockTab.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/Layout/SSeparator.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/Input/SButton.h"
#include "Styling/AppStyle.h"
#include "Modules/ModuleManager.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/PlatformApplicationMisc.h"
#include "Interfaces/IPluginManager.h"
#include "Serialization/JsonWriter.h"
#include "Serialization/JsonSerializer.h"

#define LOCTEXT_NAMESPACE "ArcwrightDashboard"

// ── Tab ID ──────────────────────────────────────────────────
const FName SArcwrightDashboardPanel::TabId = FName("ArcwrightDashboardTab");

// ── Tab registration ────────────────────────────────────────

void SArcwrightDashboardPanel::RegisterTab()
{
	FGlobalTabmanager::Get()->RegisterNomadTabSpawner(
		TabId,
		FOnSpawnTab::CreateStatic(&SArcwrightDashboardPanel::SpawnTab))
		.SetDisplayName(LOCTEXT("DashboardTabTitle", "Arcwright Dashboard"))
		.SetTooltipText(LOCTEXT("DashboardTabTooltip", "Arcwright connection status, session stats, and lifetime counters"))
		.SetMenuType(ETabSpawnerMenuType::Hidden);
}

void SArcwrightDashboardPanel::UnregisterTab()
{
	FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(TabId);
}

TSharedRef<SDockTab> SArcwrightDashboardPanel::SpawnTab(const FSpawnTabArgs& Args)
{
	return SNew(SDockTab)
		.TabRole(ETabRole::NomadTab)
		[
			SNew(SArcwrightDashboardPanel)
		];
}

// ── Construct ───────────────────────────────────────────────

void SArcwrightDashboardPanel::Construct(const FArguments& InArgs)
{
	ChildSlot
	[
		SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("NoBrush"))
		.Padding(0.f)
		[
			SNew(SVerticalBox)

			// ── Fixed header ─────────────────────────────
			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				BuildHeader()
			]

			// ── Scrollable body ──────────────────────────
			+ SVerticalBox::Slot()
			.FillHeight(1.f)
			[
				SNew(SScrollBox)
				.Orientation(Orient_Vertical)

				// Setup: Connect Your AI (top section)
				+ SScrollBox::Slot()
				.Padding(8.f, 8.f, 8.f, 0.f)
				[
					BuildSetupSection()
				]

				// Connection status card
				+ SScrollBox::Slot()
				.Padding(8.f, 8.f, 8.f, 0.f)
				[
					BuildConnectionSection()
				]

				// Session stats card
				+ SScrollBox::Slot()
				.Padding(8.f, 8.f, 8.f, 0.f)
				[
					BuildSessionSection()
				]

				// Assets this session card
				+ SScrollBox::Slot()
				.Padding(8.f, 8.f, 8.f, 0.f)
				[
					BuildAssetsSection()
				]

				// Lifetime stats card
				+ SScrollBox::Slot()
				.Padding(8.f, 8.f, 8.f, 0.f)
				[
					BuildLifetimeSection()
				]

				// Account / tier card
				+ SScrollBox::Slot()
				.Padding(8.f, 8.f, 8.f, 0.f)
				[
					BuildTierSection()
				]

				// 3D Providers card
				+ SScrollBox::Slot()
				.Padding(8.f, 8.f, 8.f, 0.f)
				[
					Build3DProvidersSection()
				]

				// Feedback / feature request card
				+ SScrollBox::Slot()
				.Padding(8.f, 8.f, 8.f, 16.f)
				[
					BuildFeedbackSection()
				]
			]
		]
	];

	// Register the 2-second refresh timer
	RegisterActiveTimer(2.0f,
		FWidgetActiveTimerDelegate::CreateSP(this, &SArcwrightDashboardPanel::OnRefreshTimer));
}

// ── Timer ───────────────────────────────────────────────────

EActiveTimerReturnType SArcwrightDashboardPanel::OnRefreshTimer(double /*InCurrentTime*/, float /*InDeltaTime*/)
{
	RefreshCommandLog();

	// Clear feedback confirmation after 5 seconds
	if (FeedbackConfirmText.IsValid() && ConfirmShownTime.GetTicks() > 0)
	{
		double Elapsed = (FDateTime::UtcNow() - ConfirmShownTime).GetTotalSeconds();
		if (Elapsed >= 5.0)
		{
			FeedbackConfirmText->SetText(FText::GetEmpty());
			ConfirmShownTime = FDateTime(0);
		}
	}

	// Reset copy button text after 3 seconds
	if (CopyConfirmTime > 0.0 && CopyButtonLabel.IsValid())
	{
		double Elapsed = FPlatformTime::Seconds() - CopyConfirmTime;
		if (Elapsed >= 3.0)
		{
			CopyButtonLabel->SetText(LOCTEXT("CopySetupReset", "Copy to Clipboard"));
			CopyButtonLabel->SetColorAndOpacity(FLinearColor::White);
			CopyConfirmTime = 0.0;
		}
	}

	return EActiveTimerReturnType::Continue;
}

// ── Header ──────────────────────────────────────────────────

TSharedRef<SWidget> SArcwrightDashboardPanel::BuildHeader()
{
	return SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("NoBrush"))
		.BorderBackgroundColor(ArcwrightColors::HeaderBg)
		.Padding(FMargin(16.f, 12.f))
		[
			SNew(SHorizontalBox)

			// Logo text
			+ SHorizontalBox::Slot()
			.AutoWidth()
			.VAlign(VAlign_Center)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("HeaderLogo", "A R C W R I G H T"))
				.ColorAndOpacity(ArcwrightColors::AccentBlue)
				.Font(FCoreStyle::GetDefaultFontStyle("Bold", 22))
			]

			// Spacer
			+ SHorizontalBox::Slot()
			.FillWidth(1.f)
			[
				SNew(SSpacer)
			]

			// Subtitle
			+ SHorizontalBox::Slot()
			.AutoWidth()
			.VAlign(VAlign_Center)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("HeaderSubtitle", "The Bridge Between AI and Unreal Engine"))
				.ColorAndOpacity(ArcwrightColors::DimText)
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 11))
			]
		];
}

// ── Card helper ─────────────────────────────────────────────

TSharedRef<SWidget> SArcwrightDashboardPanel::BuildCard(const FText& Title,
                                                         FLinearColor AccentColor,
                                                         TSharedRef<SWidget> Content)
{
	return SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("NoBrush"))
		.BorderBackgroundColor(ArcwrightColors::CardBg)
		.Padding(0.f)
		[
			SNew(SHorizontalBox)

			// 3-px accent border on the left
			+ SHorizontalBox::Slot()
			.AutoWidth()
			[
				SNew(SBorder)
				.BorderImage(FAppStyle::GetBrush("WhiteBrush"))
				.BorderBackgroundColor(AccentColor)
				.Padding(FMargin(3.f, 0.f, 0.f, 0.f))
				[
					SNew(SSpacer).Size(FVector2D(3.f, 1.f))
				]
			]

			// Card body
			+ SHorizontalBox::Slot()
			.FillWidth(1.f)
			[
				SNew(SVerticalBox)

				// Title row
				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(FMargin(12.f, 10.f, 12.f, 4.f))
				[
					SNew(STextBlock)
					.Text(Title)
					.ColorAndOpacity(AccentColor)
					.Font(FCoreStyle::GetDefaultFontStyle("Bold", 16))
				]

				// Thin separator
				+ SVerticalBox::Slot()
				.AutoHeight()
				[
					SNew(SBorder)
					.BorderImage(FAppStyle::GetBrush("WhiteBrush"))
					.BorderBackgroundColor(ArcwrightColors::BorderLine)
					.Padding(FMargin(12.f, 0.f, 12.f, 0.f))
					[
						SNew(SBox).HeightOverride(1.f)
					]
				]

				// Content
				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(FMargin(12.f, 8.f, 12.f, 12.f))
				[
					Content
				]
			]
		];
}

// ── Stat row helper ─────────────────────────────────────────

TSharedRef<SWidget> SArcwrightDashboardPanel::BuildStatRow(const FText& Label,
                                                            TAttribute<FText> Value,
                                                            FLinearColor ValueColor)
{
	return SNew(SHorizontalBox)
		.Clipping(EWidgetClipping::OnDemand)

		+ SHorizontalBox::Slot()
		.FillWidth(1.f)
		.VAlign(VAlign_Center)
		[
			SNew(STextBlock)
			.Text(Label)
			.ColorAndOpacity(ArcwrightColors::DimText)
			.Font(FCoreStyle::GetDefaultFontStyle("Regular", 13))
		]

		+ SHorizontalBox::Slot()
		.AutoWidth()
		.VAlign(VAlign_Center)
		[
			SNew(STextBlock)
			.Text(Value)
			.ColorAndOpacity(ValueColor)
			.Font(FCoreStyle::GetDefaultFontStyle("Bold", 18))
		];
}

// ── Section 0: Setup — Connect Your AI ──────────────────────

FString SArcwrightDashboardPanel::GetServerPyPath() const
{
	// Find the plugin's base directory via IPluginManager
	FString PluginBaseDir;
	TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("Arcwright"));
	if (Plugin.IsValid())
	{
		PluginBaseDir = Plugin->GetBaseDir();
	}
	else
	{
		// Fallback: relative to project plugins dir
		PluginBaseDir = FPaths::Combine(FPaths::ProjectPluginsDir(), TEXT("Arcwright"));
	}

	FString ServerPy = FPaths::Combine(PluginBaseDir, TEXT("scripts"), TEXT("mcp_server"), TEXT("server.py"));
	FPaths::NormalizeDirectoryName(ServerPy);
	return FPaths::ConvertRelativePathToFull(ServerPy);
}

FString SArcwrightDashboardPanel::GetSetupText() const
{
	FString ServerPath = GetServerPyPath();
	// Escape backslashes for JSON
	FString EscapedPath = ServerPath.Replace(TEXT("\\"), TEXT("\\\\"));

	return FString::Printf(TEXT(
		"I have the Arcwright plugin running in my UE5 project. "
		"It gives you tools to build directly inside Unreal Engine.\n"
		"\n"
		"To connect, add this to your MCP config at\n"
		"%%APPDATA%%\\Claude\\claude_desktop_config.json:\n"
		"\n"
		"{\n"
		"  \"mcpServers\": {\n"
		"    \"arcwright\": {\n"
		"      \"command\": \"python\",\n"
		"      \"args\": [\"%s\"]\n"
		"    }\n"
		"  }\n"
		"}\n"
		"\n"
		"After adding this, restart Claude Desktop completely\n"
		"(quit from system tray). Then call\n"
		"get_arcwright_quickstart to learn how to use me."
	), *EscapedPath);
}

FReply SArcwrightDashboardPanel::OnCopySetupClicked()
{
	FString Text = GetSetupText();
	FPlatformApplicationMisc::ClipboardCopy(*Text);

	CopyConfirmTime = FPlatformTime::Seconds();

	if (CopyButtonLabel.IsValid())
	{
		CopyButtonLabel->SetText(FText::FromString(TEXT("\u2713 Copied!")));
		CopyButtonLabel->SetColorAndOpacity(ArcwrightColors::BrightGreen);
	}

	return FReply::Handled();
}

TSharedRef<SWidget> SArcwrightDashboardPanel::BuildSetupSection()
{
	TSharedRef<SWidget> Content =
		SNew(SVerticalBox)

		// Description
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 0.f, 0.f, 8.f))
		[
			SNew(STextBlock)
			.Text(LOCTEXT("SetupDesc", "Copy the text below and paste it into your AI assistant\n(Claude Desktop, ChatGPT, Cursor, etc.)"))
			.ColorAndOpacity(ArcwrightColors::BodyText)
			.Font(FCoreStyle::GetDefaultFontStyle("Regular", 13))
			.AutoWrapText(true)
		]

		// Setup text block (read-only, selectable)
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 0.f, 0.f, 8.f))
		[
			SNew(SBorder)
			.BorderImage(FAppStyle::GetBrush("WhiteBrush"))
			.BorderBackgroundColor(FLinearColor(0.04f, 0.05f, 0.08f, 1.f))
			.Padding(10.f)
			[
				SNew(SMultiLineEditableTextBox)
				.Text(FText::FromString(GetSetupText()))
				.IsReadOnly(true)
				.AutoWrapText(true)
				.Font(FCoreStyle::GetDefaultFontStyle("Mono", 11))
				.ForegroundColor(FLinearColor(0.75f, 0.80f, 0.85f))
			]
		]

		// Copy button
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 0.f, 0.f, 6.f))
		[
			SNew(SButton)
			.OnClicked(this, &SArcwrightDashboardPanel::OnCopySetupClicked)
			[
				SNew(SBorder)
				.BorderImage(FAppStyle::GetBrush("WhiteBrush"))
				.BorderBackgroundColor(ArcwrightColors::AccentBlue)
				.Padding(FMargin(16.f, 6.f))
				[
					SAssignNew(CopyButtonLabel, STextBlock)
					.Text(LOCTEXT("CopySetup", "Copy to Clipboard"))
					.ColorAndOpacity(FLinearColor::White)
					.Font(FCoreStyle::GetDefaultFontStyle("Bold", 13))
				]
			]
		]

		// Compatibility note
		+ SVerticalBox::Slot()
		.AutoHeight()
		[
			SNew(STextBlock)
			.Text(LOCTEXT("SetupCompat", "Works with Claude Desktop, ChatGPT, Cursor, Windsurf, and any MCP-compatible AI"))
			.ColorAndOpacity(ArcwrightColors::DimText)
			.Font(FCoreStyle::GetDefaultFontStyle("Regular", 11))
			.AutoWrapText(true)
		];

	return BuildCard(LOCTEXT("SetupTitle", "SETUP: CONNECT YOUR AI"), ArcwrightColors::AccentBlue, Content);
}

// ── Section 1: Connection ────────────────────────────────────

TSharedRef<SWidget> SArcwrightDashboardPanel::BuildConnectionSection()
{
	TSharedRef<SWidget> Content =
		SNew(SVerticalBox)

		// Status row: dot + label + spacer + toggle button
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 0.f, 0.f, 8.f))
		[
			SNew(SHorizontalBox)

			// Status dot
			+ SHorizontalBox::Slot()
			.AutoWidth()
			.VAlign(VAlign_Center)
			.Padding(FMargin(0.f, 0.f, 6.f, 0.f))
			[
				SNew(STextBlock)
				.Text(LOCTEXT("Dot", "\u25CF"))   // ●
				.ColorAndOpacity_Raw(this, &SArcwrightDashboardPanel::GetStatusDotColor)
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 14))
			]

			// Status label
			+ SHorizontalBox::Slot()
			.FillWidth(1.f)
			.VAlign(VAlign_Center)
			[
				SNew(STextBlock)
				.Text_Raw(this, &SArcwrightDashboardPanel::GetServerStatusText)
				.ColorAndOpacity(ArcwrightColors::BodyText)
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 13))
			]

			// Toggle button
			+ SHorizontalBox::Slot()
			.AutoWidth()
			.VAlign(VAlign_Center)
			[
				SNew(SButton)
				.Text_Raw(this, &SArcwrightDashboardPanel::GetToggleButtonText)
				.OnClicked(this, &SArcwrightDashboardPanel::OnToggleServerClicked)
				.ButtonColorAndOpacity(ArcwrightColors::AccentBlue)
				.ForegroundColor(FLinearColor::White)
			]
		]

		// Connected clients
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("ConnectedClients", "Connected clients"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetConnectedClients))
			)
		]

		// Uptime
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("Uptime", "Server uptime"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetUptimeText))
			)
		];

	return BuildCard(LOCTEXT("ConnTitle", "CONNECTION STATUS"), ArcwrightColors::DeepBlue, Content);
}

// ── Section 2: Session Stats ─────────────────────────────────

TSharedRef<SWidget> SArcwrightDashboardPanel::BuildSessionSection()
{
	TSharedRef<SWidget> Content =
		SNew(SVerticalBox)

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("SessCommands", "Commands received"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetSessionCommandsText))
			)
		]

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("SessOK", "Succeeded"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetSessionSuccessText)),
				ArcwrightColors::SuccessGreen
			)
		]

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("SessFail", "Failed"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetSessionFailText)),
				ArcwrightColors::ErrorRed
			)
		]

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("SessRate", "Success rate"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetSessionSuccessRateText)),
				ArcwrightColors::WarningAmber
			)
		]

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("SessDur", "Session duration"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetSessionDurationText))
			)
		]

		// Command log heading
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 10.f, 0.f, 4.f))
		[
			SNew(STextBlock)
			.Text(LOCTEXT("LogHeading", "Recent commands"))
			.ColorAndOpacity(ArcwrightColors::DimText)
			.Font(FCoreStyle::GetDefaultFontStyle("Regular", 12))
		]

		// Scrolling command log
		+ SVerticalBox::Slot()
		.AutoHeight()
		[
			SNew(SBox)
			.HeightOverride(140.f)
			[
				SAssignNew(CommandLogBox, SMultiLineEditableTextBox)
				.IsReadOnly(true)
				.Text(FText::GetEmpty())
				.BackgroundColor(ArcwrightColors::LogBg)
				.ForegroundColor(ArcwrightColors::DimText)
				.Font(FCoreStyle::GetDefaultFontStyle("Mono", 12))
				.AutoWrapText(false)
			]
		];

	return BuildCard(LOCTEXT("SessTitle", "SESSION STATS"), ArcwrightColors::DeepBlue, Content);
}

// ── Section 3: Assets This Session ──────────────────────────

TSharedRef<SWidget> SArcwrightDashboardPanel::BuildAssetsSection()
{
	TSharedRef<SWidget> Content =
		SNew(SVerticalBox)

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("AssBP", "Blueprints created"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetSessionBlueprintsText)),
				ArcwrightColors::AccentBlue
			)
		]

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("AssBT", "Behavior Trees created"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetSessionBTsText)),
				ArcwrightColors::PurpleAccent
			)
		]

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("AssDT", "Data Tables created"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetSessionDTsText)),
				ArcwrightColors::PinkAccent
			)
		]

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("AssActors", "Actors spawned"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetSessionActorsText))
			)
		]

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("AssMat", "Materials created / applied"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetSessionMaterialsText))
			)
		];

	return BuildCard(LOCTEXT("AssTitle", "ASSETS CREATED THIS SESSION"), ArcwrightColors::DeepBlue, Content);
}

// ── Section 4: Lifetime Stats ────────────────────────────────

TSharedRef<SWidget> SArcwrightDashboardPanel::BuildLifetimeSection()
{
	TSharedRef<SWidget> Content =
		SNew(SVerticalBox)

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("LTCommands", "All-time commands"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetLifetimeCommandsText))
			)
		]

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("LTBlue", "Blueprints created"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetLifetimeBlueprintsText)),
				ArcwrightColors::AccentBlue
			)
		]

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("LTBT", "Behavior Trees created"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetLifetimeBTsText)),
				ArcwrightColors::PurpleAccent
			)
		]

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("LTDT", "Data Tables created"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetLifetimeDTsText)),
				ArcwrightColors::PinkAccent
			)
		]

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("LTActors", "Actors spawned"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetLifetimeActorsText))
			)
		]

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("LTMat", "Materials created / applied"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetLifetimeMaterialsText))
			)
		]

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("LTSessions", "Total editor sessions"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetLifetimeSessionsText))
			)
		]

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 2.f))
		[
			BuildStatRow(
				LOCTEXT("LTFirst", "First used"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetFirstUseDateText))
			)
		]

		+ SVerticalBox::Slot().AutoHeight().Padding(FMargin(0.f, 8.f, 0.f, 0.f))
		[
			BuildStatRow(
				LOCTEXT("LTTime", "Estimated time saved"),
				TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(this, &SArcwrightDashboardPanel::GetTimeSavedText)),
				ArcwrightColors::GoldAccent
			)
		];

	return BuildCard(LOCTEXT("LTTitle", "LIFETIME STATS"), ArcwrightColors::GoldAccent, Content);
}

// ── Section 5: Account & Tier ────────────────────────────────

TSharedRef<SWidget> SArcwrightDashboardPanel::BuildTierSection()
{
	// Read tier at build time for initial state
	bool bIsPro = (FTierGating::GetCurrentTier() == EArcwrightTier::Pro);

	TSharedRef<SWidget> Content =
		SNew(SVerticalBox)

		// Tier badge row
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 0.f, 0.f, 8.f))
		[
			SNew(SHorizontalBox)

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.VAlign(VAlign_Center)
			[
				SNew(SBorder)
				.BorderImage(FAppStyle::GetBrush("WhiteBrush"))
				.BorderBackgroundColor_Lambda([]()
				{
					return (FTierGating::GetCurrentTier() == EArcwrightTier::Pro)
						? FSlateColor(ArcwrightColors::GoldAccent)
						: FSlateColor(ArcwrightColors::AccentBlue);
				})
				.Padding(FMargin(10.f, 4.f))
				[
					SNew(STextBlock)
					.Text_Lambda([]()
					{
						return (FTierGating::GetCurrentTier() == EArcwrightTier::Pro)
							? FText::FromString(TEXT("Pro"))
							: FText::FromString(TEXT("Free"));
					})
					.ColorAndOpacity(FLinearColor::White)
					.Font(FCoreStyle::GetDefaultFontStyle("Bold", 13))
				]
			]
		]

		// Available commands line
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 4.f))
		[
			SNew(SHorizontalBox)

			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(FMargin(0.f, 0.f, 6.f, 0.f))
			[
				SNew(STextBlock)
				.Text(LOCTEXT("CheckMark", "\u2713"))
				.ColorAndOpacity(ArcwrightColors::BrightGreen)
				.Font(FCoreStyle::GetDefaultFontStyle("Bold", 13))
			]

			+ SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)
			[
				SNew(STextBlock)
				.Text_Lambda([]()
				{
					if (FTierGating::GetCurrentTier() == EArcwrightTier::Pro)
					{
						return FText::FromString(FString::Printf(TEXT("All %d TCP commands available"), FTierGating::TotalCommands));
					}
					return FText::FromString(FString::Printf(TEXT("%d of %d commands available"),
						FTierGating::GetFreeCommandCount(), FTierGating::TotalCommands));
				})
				.ColorAndOpacity(ArcwrightColors::BodyText)
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 13))
			]
		]

		// MCP tools line
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 4.f))
		[
			SNew(SHorizontalBox)

			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(FMargin(0.f, 0.f, 6.f, 0.f))
			[
				SNew(STextBlock)
				.Text(LOCTEXT("CheckMark2", "\u2713"))
				.ColorAndOpacity_Lambda([]()
				{
					return (FTierGating::GetCurrentTier() == EArcwrightTier::Pro)
						? FSlateColor(ArcwrightColors::BrightGreen)
						: FSlateColor(ArcwrightColors::DimText);
				})
				.Font(FCoreStyle::GetDefaultFontStyle("Bold", 13))
			]

			+ SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)
			[
				SNew(STextBlock)
				.Text_Lambda([]()
				{
					if (FTierGating::GetCurrentTier() == EArcwrightTier::Pro)
					{
						return FText::FromString(FString::Printf(TEXT("All %d MCP tools available"), FTierGating::TotalMCPTools));
					}
					return FText::FromString(TEXT("MCP tools — upgrade to Pro for full access"));
				})
				.ColorAndOpacity(ArcwrightColors::BodyText)
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 13))
			]
		]

		// Divider
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 10.f))
		[
			SNew(SSeparator)
			.Thickness(1.f)
		]

		// License key input label
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 0.f, 0.f, 4.f))
		[
			SNew(STextBlock)
			.Text(LOCTEXT("LicenseLabel", "License Key"))
			.ColorAndOpacity(ArcwrightColors::DimText)
			.Font(FCoreStyle::GetDefaultFontStyle("Regular", 12))
		]

		// License key input + activate button
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 0.f, 0.f, 6.f))
		[
			SNew(SHorizontalBox)

			+ SHorizontalBox::Slot()
			.FillWidth(1.f)
			.Padding(FMargin(0.f, 0.f, 6.f, 0.f))
			[
				SAssignNew(LicenseKeyInput, SEditableTextBox)
				.HintText(LOCTEXT("KeyHint", "Paste your API key"))
				.Text(FText::FromString(FTierGating::ReadApiKey()))
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 12))
			]

			+ SHorizontalBox::Slot()
			.AutoWidth()
			[
				SNew(SButton)
				.OnClicked(this, &SArcwrightDashboardPanel::OnActivateProClicked)
				[
					SNew(SBorder)
					.BorderImage(FAppStyle::GetBrush("WhiteBrush"))
					.BorderBackgroundColor(ArcwrightColors::GoldAccent)
					.Padding(FMargin(12.f, 4.f))
					[
						SNew(STextBlock)
						.Text(LOCTEXT("ActivatePro", "Activate Pro"))
						.ColorAndOpacity(FLinearColor::Black)
						.Font(FCoreStyle::GetDefaultFontStyle("Bold", 12))
					]
				]
			]
		]

		// Status text (shows activation result)
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 0.f, 0.f, 8.f))
		[
			SAssignNew(LicenseStatusText, STextBlock)
			.Text(FText::GetEmpty())
			.ColorAndOpacity(ArcwrightColors::BrightGreen)
			.Font(FCoreStyle::GetDefaultFontStyle("Regular", 12))
		]

		// Upgrade link
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 4.f, 0.f, 0.f))
		[
			SNew(STextBlock)
			.Text_Lambda([]()
			{
				if (FTierGating::GetCurrentTier() == EArcwrightTier::Pro)
				{
					return FText::FromString(FString::Printf(TEXT("Licensed as %s"), *FTierGating::GetMaskedKey()));
				}
				return FText::FromString(TEXT("Upgrade to Pro \u2014 arcwright.app"));
			})
			.ColorAndOpacity_Lambda([]()
			{
				return (FTierGating::GetCurrentTier() == EArcwrightTier::Pro)
					? FSlateColor(ArcwrightColors::DimText)
					: FSlateColor(ArcwrightColors::GoldAccent);
			})
			.Font(FCoreStyle::GetDefaultFontStyle("Regular", 12))
		]

		// Deactivate button (only visible when Pro)
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 8.f, 0.f, 0.f))
		[
			SNew(SButton)
			.OnClicked(this, &SArcwrightDashboardPanel::OnDeactivateClicked)
			.Visibility_Lambda([]()
			{
				return (FTierGating::GetCurrentTier() == EArcwrightTier::Pro)
					? EVisibility::Visible
					: EVisibility::Collapsed;
			})
			[
				SNew(STextBlock)
				.Text(LOCTEXT("DeactivateLicense", "Deactivate License"))
				.ColorAndOpacity(ArcwrightColors::DimText)
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 12))
			]
		];

	return BuildCard(LOCTEXT("TierTitle", "ACCOUNT & TIER"), ArcwrightColors::GoldAccent, Content);
}

FReply SArcwrightDashboardPanel::OnActivateProClicked()
{
	if (!LicenseKeyInput.IsValid()) return FReply::Handled();

	FString Key = LicenseKeyInput->GetText().ToString();
	Key.TrimStartAndEndInline();

	if (Key.IsEmpty())
	{
		if (LicenseStatusText.IsValid())
		{
			LicenseStatusText->SetText(FText::FromString(TEXT("Please enter a license key.")));
			LicenseStatusText->SetColorAndOpacity(ArcwrightColors::BrightRed);
		}
		return FReply::Handled();
	}

	// Show validating state immediately
	if (LicenseStatusText.IsValid())
	{
		LicenseStatusText->SetText(FText::FromString(TEXT("Validating license...")));
		LicenseStatusText->SetColorAndOpacity(ArcwrightColors::GoldAccent);
	}

	// Bind state change listener (only once)
	if (!LicenseStateDelegateHandle.IsValid())
	{
		LicenseStateDelegateHandle = FTierGating::OnLicenseStateChanged.AddLambda(
			[this](ELicenseState State, const FString& Msg) { OnLicenseStateChanged(State, Msg); });
	}

	// Kick off async LemonSqueezy validation
	FTierGating::ValidateKeyAsync(Key);

	return FReply::Handled();
}

FReply SArcwrightDashboardPanel::OnDeactivateClicked()
{
	if (!LicenseStateDelegateHandle.IsValid())
	{
		LicenseStateDelegateHandle = FTierGating::OnLicenseStateChanged.AddLambda(
			[this](ELicenseState State, const FString& Msg) { OnLicenseStateChanged(State, Msg); });
	}

	FTierGating::DeactivateKeyAsync();

	if (LicenseKeyInput.IsValid())
	{
		LicenseKeyInput->SetText(FText::GetEmpty());
	}

	return FReply::Handled();
}

void SArcwrightDashboardPanel::OnLicenseStateChanged(ELicenseState NewState, const FString& Message)
{
	if (!LicenseStatusText.IsValid()) return;

	switch (NewState)
	{
	case ELicenseState::Valid:
		LicenseStatusText->SetText(FText::FromString(Message));
		LicenseStatusText->SetColorAndOpacity(ArcwrightColors::BrightGreen);
		break;
	case ELicenseState::Invalid:
	case ELicenseState::Expired:
		LicenseStatusText->SetText(FText::FromString(Message));
		LicenseStatusText->SetColorAndOpacity(ArcwrightColors::BrightRed);
		break;
	case ELicenseState::OfflineGrace:
		LicenseStatusText->SetText(FText::FromString(Message));
		LicenseStatusText->SetColorAndOpacity(ArcwrightColors::GoldAccent);
		break;
	case ELicenseState::Validating:
		LicenseStatusText->SetText(FText::FromString(Message));
		LicenseStatusText->SetColorAndOpacity(ArcwrightColors::GoldAccent);
		break;
	case ELicenseState::None:
		LicenseStatusText->SetText(FText::FromString(Message));
		LicenseStatusText->SetColorAndOpacity(ArcwrightColors::DimText);
		break;
	}
}

// ── Attribute getters ────────────────────────────────────────

FCommandServer* SArcwrightDashboardPanel::GetServer() const
{
	FArcwrightModule* Module = FModuleManager::GetModulePtr<FArcwrightModule>("Arcwright");
	return Module ? Module->GetCommandServer() : nullptr;
}

FArcwrightStats* SArcwrightDashboardPanel::GetStats() const
{
	FCommandServer* Server = GetServer();
	return Server ? Server->GetStats() : nullptr;
}

// Connection

FText SArcwrightDashboardPanel::GetServerStatusText() const
{
	const FCommandServer* Server = GetServer();
	if (Server && Server->IsRunning())
		return LOCTEXT("StatusRunning", "Running on port 13377");
	return LOCTEXT("StatusOffline", "Offline — server not started");
}

FSlateColor SArcwrightDashboardPanel::GetStatusDotColor() const
{
	const FCommandServer* Server = GetServer();
	if (Server && Server->IsRunning())
		return ArcwrightColors::SuccessGreen;
	return ArcwrightColors::ErrorRed;
}

FText SArcwrightDashboardPanel::GetConnectedClients() const
{
	const FCommandServer* Server = GetServer();
	if (Server && Server->IsRunning())
		return FText::AsNumber(Server->GetConnectedClientCount());
	return FText::FromString(TEXT("—"));
}

FText SArcwrightDashboardPanel::GetUptimeText() const
{
	const FCommandServer* Server = GetServer();
	if (Server && Server->IsRunning())
	{
		double Uptime = Server->GetServerUptimeSeconds();
		return FText::FromString(FormatUptime(Uptime));
	}
	return FText::FromString(TEXT("—"));
}

FText SArcwrightDashboardPanel::GetToggleButtonText() const
{
	const FCommandServer* Server = GetServer();
	if (Server && Server->IsRunning())
		return LOCTEXT("StopServer", "Stop Server");
	return LOCTEXT("StartServer", "Start Server");
}

// Session

FText SArcwrightDashboardPanel::GetSessionCommandsText() const
{
	const FArcwrightStats* S = GetStats();
	return S ? FText::AsNumber(S->GetSessionCommands()) : FText::FromString(TEXT("0"));
}

FText SArcwrightDashboardPanel::GetSessionSuccessText() const
{
	const FArcwrightStats* S = GetStats();
	return S ? FText::AsNumber(S->GetSessionSuccesses()) : FText::FromString(TEXT("0"));
}

FText SArcwrightDashboardPanel::GetSessionFailText() const
{
	const FArcwrightStats* S = GetStats();
	return S ? FText::AsNumber(S->GetSessionErrors()) : FText::FromString(TEXT("0"));
}

FText SArcwrightDashboardPanel::GetSessionSuccessRateText() const
{
	const FArcwrightStats* S = GetStats();
	if (!S) return FText::FromString(TEXT("100%"));
	int32 Cmds = S->GetSessionCommands();
	if (Cmds == 0) return FText::FromString(TEXT("100%"));
	double Rate = (double)S->GetSessionSuccesses() / (double)Cmds * 100.0;
	return FText::FromString(FString::Printf(TEXT("%.1f%%"), Rate));
}

FText SArcwrightDashboardPanel::GetSessionDurationText() const
{
	const FArcwrightStats* S = GetStats();
	if (!S) return FText::FromString(TEXT("0s"));
	double DurSec = (FDateTime::UtcNow() - S->GetSessionStartTime()).GetTotalSeconds();
	return FText::FromString(FormatDuration(DurSec));
}

// Assets (session)

FText SArcwrightDashboardPanel::GetSessionBlueprintsText() const
{
	const FArcwrightStats* S = GetStats();
	// session blueprints is tracked via the JSON path; fall back to full stats json
	if (!S) return FText::FromString(TEXT("0"));
	TSharedPtr<FJsonObject> Json = S->GetStatsJson();
	if (!Json.IsValid()) return FText::FromString(TEXT("0"));
	const TSharedPtr<FJsonObject>* Sess = nullptr;
	if (Json->TryGetObjectField(TEXT("session"), Sess) && Sess->IsValid())
	{
		int32 V = (int32)(*Sess)->GetNumberField(TEXT("blueprints_created"));
		return FText::AsNumber(V);
	}
	return FText::FromString(TEXT("0"));
}

FText SArcwrightDashboardPanel::GetSessionActorsText() const
{
	const FArcwrightStats* S = GetStats();
	if (!S) return FText::FromString(TEXT("0"));
	TSharedPtr<FJsonObject> Json = S->GetStatsJson();
	if (!Json.IsValid()) return FText::FromString(TEXT("0"));
	const TSharedPtr<FJsonObject>* Sess = nullptr;
	if (Json->TryGetObjectField(TEXT("session"), Sess) && Sess->IsValid())
	{
		int32 V = (int32)(*Sess)->GetNumberField(TEXT("actors_spawned"));
		return FText::AsNumber(V);
	}
	return FText::FromString(TEXT("0"));
}

FText SArcwrightDashboardPanel::GetSessionMaterialsText() const
{
	const FArcwrightStats* S = GetStats();
	// Materials applied is lifetime only in current stats; show lifetime delta as approximation
	return S ? FText::AsNumber(S->GetTotalMaterials()) : FText::FromString(TEXT("0"));
}

FText SArcwrightDashboardPanel::GetSessionBTsText() const
{
	const FArcwrightStats* S = GetStats();
	return S ? FText::AsNumber(S->GetTotalBTs()) : FText::FromString(TEXT("0"));
}

FText SArcwrightDashboardPanel::GetSessionDTsText() const
{
	const FArcwrightStats* S = GetStats();
	return S ? FText::AsNumber(S->GetTotalDTs()) : FText::FromString(TEXT("0"));
}

// Lifetime

FText SArcwrightDashboardPanel::GetLifetimeCommandsText() const
{
	const FArcwrightStats* S = GetStats();
	return S ? FText::AsNumber(S->GetTotalCommands()) : FText::FromString(TEXT("0"));
}

FText SArcwrightDashboardPanel::GetLifetimeBlueprintsText() const
{
	const FArcwrightStats* S = GetStats();
	return S ? FText::AsNumber(S->GetTotalBlueprints()) : FText::FromString(TEXT("0"));
}

FText SArcwrightDashboardPanel::GetLifetimeActorsText() const
{
	const FArcwrightStats* S = GetStats();
	return S ? FText::AsNumber(S->GetTotalActors()) : FText::FromString(TEXT("0"));
}

FText SArcwrightDashboardPanel::GetLifetimeBTsText() const
{
	const FArcwrightStats* S = GetStats();
	return S ? FText::AsNumber(S->GetTotalBTs()) : FText::FromString(TEXT("0"));
}

FText SArcwrightDashboardPanel::GetLifetimeDTsText() const
{
	const FArcwrightStats* S = GetStats();
	return S ? FText::AsNumber(S->GetTotalDTs()) : FText::FromString(TEXT("0"));
}

FText SArcwrightDashboardPanel::GetLifetimeMaterialsText() const
{
	const FArcwrightStats* S = GetStats();
	return S ? FText::AsNumber(S->GetTotalMaterials()) : FText::FromString(TEXT("0"));
}

FText SArcwrightDashboardPanel::GetLifetimeSessionsText() const
{
	const FArcwrightStats* S = GetStats();
	return S ? FText::AsNumber(S->GetTotalSessions()) : FText::FromString(TEXT("0"));
}

FText SArcwrightDashboardPanel::GetFirstUseDateText() const
{
	const FArcwrightStats* S = GetStats();
	if (!S) return FText::FromString(TEXT("—"));
	FString D = S->GetFirstUseDate();
	if (D.IsEmpty()) return FText::FromString(TEXT("—"));
	// Truncate ISO 8601 to date only (first 10 chars)
	if (D.Len() > 10) D = D.Left(10);
	return FText::FromString(D);
}

FText SArcwrightDashboardPanel::GetTimeSavedText() const
{
	const FArcwrightStats* S = GetStats();
	if (!S) return FText::FromString(TEXT("—"));
	int64 Sec = S->GetTimeSavedSeconds();
	double Mins = (double)Sec / 60.0;
	if (Mins < 120.0)
		return FText::FromString(FString::Printf(TEXT("%.0f minutes"), Mins));
	double Hours = Mins / 60.0;
	if (Hours < 48.0)
		return FText::FromString(FString::Printf(TEXT("%.1f hours"), Hours));
	double Days = Hours / 24.0;
	return FText::FromString(FString::Printf(TEXT("%.1f days"), Days));
}

// ── Command log ──────────────────────────────────────────────

void SArcwrightDashboardPanel::RefreshCommandLog()
{
	FArcwrightStats* S = GetStats();
	if (!S || !CommandLogBox.IsValid()) return;

	TArray<FArcwrightCommandLogEntry> Log = S->GetCommandLog();

	CommandLogText.Empty(512);
	for (const FArcwrightCommandLogEntry& Entry : Log)
	{
		// [HH:MM:SS] command_name ✓ / [HH:MM:SS] command_name ✗ error
		FString TimeStr = Entry.Timestamp.ToString(TEXT("%H:%M:%S"));
		FString StatusSym = Entry.bSuccess ? TEXT("\u2713") : TEXT("\u2717");
		FString Line = FString::Printf(TEXT("[%s] %s %s"), *TimeStr, *Entry.CommandName, *StatusSym);
		if (!Entry.bSuccess && !Entry.ErrorMessage.IsEmpty())
		{
			// Trim error to 60 chars
			FString Err = Entry.ErrorMessage;
			if (Err.Len() > 60) Err = Err.Left(57) + TEXT("...");
			Line += TEXT("  ") + Err;
		}
		CommandLogText += Line + TEXT("\n");
	}

	CommandLogBox->SetText(FText::FromString(CommandLogText));
}

// ── Server toggle ────────────────────────────────────────────

FReply SArcwrightDashboardPanel::OnToggleServerClicked()
{
	FArcwrightModule* Module = FModuleManager::GetModulePtr<FArcwrightModule>("Arcwright");
	if (!Module) return FReply::Handled();

	FCommandServer* Server = Module->GetCommandServer();
	if (Server && Server->IsRunning())
	{
		Server->Stop();
	}
	else if (Server)
	{
		Server->Start();
	}
	return FReply::Handled();
}

// ── Formatting helpers ───────────────────────────────────────

FString SArcwrightDashboardPanel::FormatUptime(double Seconds) const
{
	return FormatDuration(Seconds);
}

FString SArcwrightDashboardPanel::FormatDuration(double Seconds) const
{
	int32 S   = (int32)Seconds;
	int32 H   = S / 3600;
	int32 M   = (S % 3600) / 60;
	int32 Sec = S % 60;

	if (H > 0)
		return FString::Printf(TEXT("%dh %dm %ds"), H, M, Sec);
	if (M > 0)
		return FString::Printf(TEXT("%dm %ds"), M, Sec);
	return FString::Printf(TEXT("%ds"), Sec);
}

// ── Section: 3D Asset Providers ──────────────────────────────

TSharedRef<SWidget> SArcwrightDashboardPanel::Build3DProvidersSection()
{
	TSharedRef<SWidget> Content =
		SNew(SVerticalBox)

		// Tripo AI
		+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(STextBlock)
				.Text(LOCTEXT("TripoLabel", "Tripo AI"))
				.ColorAndOpacity(ArcwrightColors::BodyText)
				.Font(FCoreStyle::GetDefaultFontStyle("Bold", 13))
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 2)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("TripoDesc", "tripo3d.ai \u2014 Best for characters and organic models"))
				.ColorAndOpacity(ArcwrightColors::DimText)
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 11))
			]
		]

		// Meshy
		+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(STextBlock)
				.Text(LOCTEXT("MeshyLabel", "Meshy"))
				.ColorAndOpacity(ArcwrightColors::BodyText)
				.Font(FCoreStyle::GetDefaultFontStyle("Bold", 13))
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 2)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("MeshyDesc", "meshy.ai \u2014 Best for props and hard-surface models"))
				.ColorAndOpacity(ArcwrightColors::DimText)
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 11))
			]
		]

		// Note
		+ SVerticalBox::Slot().AutoHeight().Padding(0, 4)
		[
			SNew(STextBlock)
			.Text(LOCTEXT("ProviderNote", "Get API keys from these providers directly.\nArcwright bridges them to Unreal Engine.\nSet keys via MCP: mesh3d_set_provider_key"))
			.ColorAndOpacity(ArcwrightColors::DimText)
			.Font(FCoreStyle::GetDefaultFontStyle("Regular", 11))
			.AutoWrapText(true)
		];

	return BuildCard(LOCTEXT("3DProvTitle", "3D ASSET PROVIDERS"), ArcwrightColors::PurpleAccent, Content);
}

// ── Section 6: Feedback / Feature Request ────────────────────

TSharedRef<SWidget> SArcwrightDashboardPanel::BuildFeedbackSection()
{
	// Initialize categories
	FeedbackCategories.Empty();
	FeedbackCategories.Add(MakeShared<FString>(TEXT("Feature Request")));
	FeedbackCategories.Add(MakeShared<FString>(TEXT("Bug Report")));
	FeedbackCategories.Add(MakeShared<FString>(TEXT("Improvement")));
	FeedbackCategories.Add(MakeShared<FString>(TEXT("New Command")));
	SelectedCategory = FeedbackCategories[0];

	TSharedRef<SWidget> Content =
		SNew(SVerticalBox)

		// Multi-line text input
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 0.f, 0.f, 8.f))
		[
			SNew(SBox)
			.HeightOverride(100.f)
			[
				SAssignNew(FeedbackInputBox, SMultiLineEditableTextBox)
				.HintText(LOCTEXT("FeedbackPlaceholder", "Describe the feature, bug, or improvement you'd like to see..."))
				.BackgroundColor(ArcwrightColors::LogBg)
				.ForegroundColor(ArcwrightColors::BodyText)
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 13))
				.AutoWrapText(true)
			]
		]

		// Privacy note
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 0.f, 0.f, 8.f))
		[
			SNew(STextBlock)
			.Text(LOCTEXT("PrivacyNote", "Feedback is sent anonymously. No personal data or project content is included."))
			.ColorAndOpacity(ArcwrightColors::TextDim)
			.Font(FCoreStyle::GetDefaultFontStyle("Italic", 11))
			.AutoWrapText(true)
		]

		// Category dropdown + Submit button row
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 0.f, 0.f, 8.f))
		[
			SNew(SHorizontalBox)

			// Category combo
			+ SHorizontalBox::Slot()
			.AutoWidth()
			.VAlign(VAlign_Center)
			.Padding(FMargin(0.f, 0.f, 8.f, 0.f))
			[
				SNew(SComboBox<TSharedPtr<FString>>)
				.OptionsSource(&FeedbackCategories)
				.OnSelectionChanged(this, &SArcwrightDashboardPanel::OnCategorySelected)
				.OnGenerateWidget(this, &SArcwrightDashboardPanel::GenerateCategoryComboItem)
				.InitiallySelectedItem(SelectedCategory)
				[
					SNew(STextBlock)
					.Text(this, &SArcwrightDashboardPanel::GetSelectedCategoryText)
					.ColorAndOpacity(ArcwrightColors::BodyText)
					.Font(FCoreStyle::GetDefaultFontStyle("Regular", 13))
				]
			]

			// Spacer
			+ SHorizontalBox::Slot()
			.FillWidth(1.f)
			[
				SNew(SSpacer)
			]

			// Submit button
			+ SHorizontalBox::Slot()
			.AutoWidth()
			.VAlign(VAlign_Center)
			[
				SNew(SButton)
				.Text(LOCTEXT("SubmitFeedback", "Submit Feedback"))
				.OnClicked(this, &SArcwrightDashboardPanel::OnSubmitFeedbackClicked)
				.ButtonColorAndOpacity(ArcwrightColors::AccentBlue)
				.ForegroundColor(FLinearColor::White)
			]
		]

		// Confirmation text (hidden until submit)
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(FMargin(0.f, 0.f, 0.f, 4.f))
		[
			SAssignNew(FeedbackConfirmText, STextBlock)
			.Text(FText::GetEmpty())
			.ColorAndOpacity(ArcwrightColors::BrightGreen)
			.Font(FCoreStyle::GetDefaultFontStyle("Bold", 13))
		]

		// Last submitted display
		+ SVerticalBox::Slot()
		.AutoHeight()
		[
			SAssignNew(LastSubmittedText, STextBlock)
			.Text(FText::GetEmpty())
			.ColorAndOpacity(ArcwrightColors::DimText)
			.Font(FCoreStyle::GetDefaultFontStyle("Mono", 11))
			.AutoWrapText(true)
		];

	return BuildCard(LOCTEXT("FeedbackTitle", "REQUEST A FEATURE"), ArcwrightColors::AccentBlue, Content);
}

TSharedRef<SWidget> SArcwrightDashboardPanel::GenerateCategoryComboItem(TSharedPtr<FString> Item)
{
	return SNew(STextBlock)
		.Text(FText::FromString(*Item))
		.ColorAndOpacity(ArcwrightColors::BodyText)
		.Font(FCoreStyle::GetDefaultFontStyle("Regular", 13));
}

void SArcwrightDashboardPanel::OnCategorySelected(TSharedPtr<FString> Item, ESelectInfo::Type /*SelectInfo*/)
{
	SelectedCategory = Item;
}

FText SArcwrightDashboardPanel::GetSelectedCategoryText() const
{
	if (SelectedCategory.IsValid())
		return FText::FromString(*SelectedCategory);
	return LOCTEXT("DefaultCategory", "Feature Request");
}

FReply SArcwrightDashboardPanel::OnSubmitFeedbackClicked()
{
	// Rate limit: 1 per minute
	FDateTime Now = FDateTime::UtcNow();
	if ((Now - LastFeedbackSubmitTime).GetTotalSeconds() < 60.0)
	{
		if (FeedbackConfirmText.IsValid())
		{
			FeedbackConfirmText->SetColorAndOpacity(ArcwrightColors::WarningAmber);
			FeedbackConfirmText->SetText(LOCTEXT("RateLimit", "Please wait a moment before submitting again."));
		}
		return FReply::Handled();
	}

	// Get input text
	FString Message;
	if (FeedbackInputBox.IsValid())
	{
		Message = FeedbackInputBox->GetText().ToString();
	}
	if (Message.TrimStartAndEnd().IsEmpty())
	{
		if (FeedbackConfirmText.IsValid())
		{
			FeedbackConfirmText->SetColorAndOpacity(ArcwrightColors::BrightRed);
			FeedbackConfirmText->SetText(LOCTEXT("EmptyFeedback", "Please enter your feedback before submitting."));
		}
		return FReply::Handled();
	}

	FString Category = SelectedCategory.IsValid() ? *SelectedCategory : TEXT("Feature Request");

	// Build JSON payload
	TSharedRef<FJsonObject> Payload = MakeShared<FJsonObject>();
	Payload->SetStringField(TEXT("type"), TEXT("feedback"));
	Payload->SetStringField(TEXT("category"), Category);
	Payload->SetStringField(TEXT("message"), Message);
	Payload->SetStringField(TEXT("plugin_version"), TEXT("1.0.0"));
	Payload->SetStringField(TEXT("ue_version"), TEXT("5.7"));
	Payload->SetStringField(TEXT("platform"), TEXT("Win64"));
	Payload->SetStringField(TEXT("timestamp"), FDateTime::UtcNow().ToIso8601());

	// Add session stats if available
	const FArcwrightStats* Stats = GetStats();
	if (Stats)
	{
		TSharedRef<FJsonObject> StatsObj = MakeShared<FJsonObject>();
		StatsObj->SetNumberField(TEXT("session_commands"), Stats->GetSessionCommands());
		StatsObj->SetNumberField(TEXT("total_commands"), Stats->GetTotalCommands());
		StatsObj->SetNumberField(TEXT("total_sessions"), Stats->GetTotalSessions());
		Payload->SetObjectField(TEXT("session_stats"), StatsObj);
	}

	// Serialize to string
	FString JsonString;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&JsonString);
	FJsonSerializer::Serialize(Payload, Writer);

	LastFeedbackSubmitTime = Now;

	// Fire-and-forget HTTP POST
	FString Endpoint = GetFeedbackEndpoint();
	if (!Endpoint.IsEmpty())
	{
		FHttpRequestRef HttpRequest = FHttpModule::Get().CreateRequest();
		HttpRequest->SetURL(Endpoint);
		HttpRequest->SetVerb(TEXT("POST"));
		HttpRequest->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
		HttpRequest->SetContentAsString(JsonString);
		HttpRequest->OnProcessRequestComplete().BindRaw(this, &SArcwrightDashboardPanel::OnFeedbackHttpComplete);
		HttpRequest->ProcessRequest();
	}

	// Always save locally as fallback
	SaveFeedbackLocally(JsonString);

	// Show confirmation
	if (FeedbackConfirmText.IsValid())
	{
		FeedbackConfirmText->SetColorAndOpacity(ArcwrightColors::BrightGreen);
		FeedbackConfirmText->SetText(LOCTEXT("FeedbackSent", "Feedback submitted! Thank you."));
	}

	// Show last submitted summary
	if (LastSubmittedText.IsValid())
	{
		FString Truncated = Message;
		if (Truncated.Len() > 80) Truncated = Truncated.Left(77) + TEXT("...");
		LastSubmittedText->SetText(FText::FromString(
			FString::Printf(TEXT("Last: [%s] %s"), *Category, *Truncated)));
	}

	// Clear input
	if (FeedbackInputBox.IsValid())
	{
		FeedbackInputBox->SetText(FText::GetEmpty());
	}

	// Confirmation will be cleared after 5 seconds in OnRefreshTimer
	ConfirmShownTime = FDateTime::UtcNow();

	return FReply::Handled();
}

void SArcwrightDashboardPanel::OnFeedbackHttpComplete(
	FHttpRequestPtr /*Request*/,
	FHttpResponsePtr Response,
	bool bConnectedSuccessfully)
{
	if (!bConnectedSuccessfully || !Response.IsValid() || Response->GetResponseCode() >= 400)
	{
		UE_LOG(LogArcwright, Warning, TEXT("Feedback HTTP POST failed (saved locally). Code: %d"),
			Response.IsValid() ? Response->GetResponseCode() : 0);
	}
}

void SArcwrightDashboardPanel::SaveFeedbackLocally(const FString& JsonPayload)
{
	FString SaveDir = FPaths::ProjectSavedDir() / TEXT("Arcwright");
	FString FilePath = SaveDir / TEXT("pending_feedback.json");

	// Ensure directory exists
	IFileManager::Get().MakeDirectory(*SaveDir, true);

	// Read existing array or create new one
	FString Existing;
	TArray<TSharedPtr<FJsonValue>> FeedbackArray;
	if (FFileHelper::LoadFileToString(Existing, *FilePath))
	{
		TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Existing);
		TSharedPtr<FJsonValue> Parsed;
		if (FJsonSerializer::Deserialize(Reader, Parsed) && Parsed.IsValid() && Parsed->Type == EJson::Array)
		{
			FeedbackArray = Parsed->AsArray();
		}
	}

	// Parse new entry and append
	TSharedRef<TJsonReader<>> NewReader = TJsonReaderFactory<>::Create(JsonPayload);
	TSharedPtr<FJsonValue> NewEntry;
	if (FJsonSerializer::Deserialize(NewReader, NewEntry) && NewEntry.IsValid())
	{
		FeedbackArray.Add(NewEntry);
	}

	// Write back
	FString Output;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Output);
	FJsonSerializer::Serialize(FeedbackArray, Writer);
	FFileHelper::SaveStringToFile(Output, *FilePath, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
}

FString SArcwrightDashboardPanel::GetFeedbackEndpoint() const
{
	FString Endpoint;
	if (GConfig)
	{
		GConfig->GetString(
			TEXT("/Script/Arcwright.ArcwrightSettings"),
			TEXT("FeedbackEndpoint"),
			Endpoint,
			GEngineIni);
	}
	if (Endpoint.IsEmpty())
	{
		Endpoint = TEXT("https://api.arcwright.app/v1/feedback");
	}
	return Endpoint;
}

#undef LOCTEXT_NAMESPACE
