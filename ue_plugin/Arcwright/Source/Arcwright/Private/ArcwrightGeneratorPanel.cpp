#include "ArcwrightGeneratorPanel.h"
#include "DSLImporter.h"
#include "BlueprintBuilder.h"
#include "BehaviorTreeBuilder.h"
#include "DataTableBuilder.h"
#include "CommandServer.h"
#include "ArcwrightModule.h"

#include "Widgets/Docking/SDockTab.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/Layout/SSeparator.h"
#include "Widgets/Layout/SWidgetSwitcher.h"
#include "Widgets/Layout/SUniformGridPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/SMultiLineEditableTextBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/SBoxPanel.h"
#include "Framework/Docking/TabManager.h"
#include "Styling/SlateTypes.h"
#include "Styling/AppStyle.h"
#include "Styling/CoreStyle.h"
#include "Styling/SlateColor.h"

#include "SocketSubsystem.h"
#include "Subsystems/AssetEditorSubsystem.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "ObjectTools.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/Paths.h"
#include "Styling/SlateBrush.h"
#include "HAL/PlatformApplicationMisc.h"

#define LOCTEXT_NAMESPACE "ArcwrightGenerator"

using namespace ArcwrightColors;

// Helper to get the command server from the module
static FCommandServer* GetCommandServerFromModule()
{
	FArcwrightModule& Module = FModuleManager::GetModuleChecked<FArcwrightModule>(TEXT("Arcwright"));
	return Module.GetCommandServer();
}


// ============================================================
// Static members
// ============================================================

const FName SArcwrightGeneratorPanel::TabId(TEXT("ArcwrightGeneratorTab"));

// ============================================================
// Tab registration
// ============================================================

void SArcwrightGeneratorPanel::RegisterTab()
{
	FGlobalTabmanager::Get()->RegisterNomadTabSpawner(
		TabId,
		FOnSpawnTab::CreateStatic(&SArcwrightGeneratorPanel::SpawnTab))
		.SetDisplayName(LOCTEXT("TabTitle", "Arcwright"))
		.SetTooltipText(LOCTEXT("TabTooltip", "Arcwright — Architect Your Game from Language"))
		.SetMenuType(ETabSpawnerMenuType::Hidden)
		.SetIcon(FSlateIcon(TEXT("ArcwrightStyle"), TEXT("Arcwright.Icon16"), TEXT("Arcwright.Icon16")));
}

void SArcwrightGeneratorPanel::UnregisterTab()
{
	FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(TabId);
}

TSharedRef<SDockTab> SArcwrightGeneratorPanel::SpawnTab(const FSpawnTabArgs& Args)
{
	return SNew(SDockTab)
		.TabRole(ETabRole::NomadTab)
		.Label(LOCTEXT("TabLabel", "Arcwright"))
		[
			SNew(SArcwrightGeneratorPanel)
		];
}

// ============================================================
// Brand brush loading
// ============================================================

void SArcwrightGeneratorPanel::LoadBrandBrushes()
{
	// Look for Resources in the plugin directory
	FString ResourcesDir = FPaths::Combine(FPaths::ProjectPluginsDir(), TEXT("Arcwright"), TEXT("Resources"));

	auto LoadBrush = [&](const FString& Filename, FVector2D Size) -> TSharedPtr<FSlateDynamicImageBrush>
	{
		FString FilePath = FPaths::Combine(ResourcesDir, Filename);
		if (FPaths::FileExists(FilePath))
		{
			FName BrushName(*FilePath);
			return MakeShareable(new FSlateDynamicImageBrush(BrushName, Size));
		}
		UE_LOG(LogArcwright, Warning, TEXT("Arcwright brand image not found: %s"), *FilePath);
		return nullptr;
	};

	HeroBannerBrush = LoadBrush(TEXT("arcwright_logo.png"), FVector2D(1675, 378));
	LogoBrush = LoadBrush(TEXT("arcwright_logo_small.png"), FVector2D(742, 162));
	Icon40Brush = LoadBrush(TEXT("ArcwrightIcon40.png"), FVector2D(40, 40));
	Icon16Brush = LoadBrush(TEXT("ArcwrightIcon16.png"), FVector2D(16, 16));
}

// ============================================================
// Main construction
// ============================================================

void SArcwrightGeneratorPanel::Construct(const FArguments& InArgs)
{
	LoadBrandBrushes();

	ChildSlot
	[
		SNew(SBorder)
		.BorderBackgroundColor(DeepNavy)
		.Padding(0)
		[
			SNew(SVerticalBox)

			// ── Header with tabs ───────────────────
			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				BuildHeader()
			]

			// ── Tab content area ───────────────────
			+ SVerticalBox::Slot()
			.FillHeight(1.0f)
			[
				SAssignNew(TabSwitcher, SWidgetSwitcher)
				.WidgetIndex(0) // Chat tab

				+ SWidgetSwitcher::Slot()
				[
					BuildChatTab()
				]

				+ SWidgetSwitcher::Slot()
				[
					BuildCreateTab()
				]

				+ SWidgetSwitcher::Slot()
				[
					BuildHistoryTab()
				]
			]

			// ── Log panel (collapsible, above status bar) ──
			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				BuildLogPanel()
			]

			// ── Status bar (always visible) ────────
			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				BuildStatusBar()
			]
		]
	];
}

// ============================================================
// Header bar with logo and tab buttons
// ============================================================

TSharedRef<SWidget> SArcwrightGeneratorPanel::BuildHeader()
{
	return SNew(SVerticalBox)

		// Top bar: logo + mode indicator
		+ SVerticalBox::Slot()
		.AutoHeight()
		[
			SNew(SBorder)
			.BorderBackgroundColor(HeaderBg)
			.Padding(FMargin(16.0f, 10.0f, 16.0f, 6.0f))
			[
				SNew(SHorizontalBox)

				// Logo image (or fallback text)
				+ SHorizontalBox::Slot()
				.AutoWidth()
				.VAlign(VAlign_Center)
				[
					LogoBrush.IsValid()
					? StaticCastSharedRef<SWidget>(
						SNew(SBox)
						.WidthOverride(165.0f)
						.HeightOverride(36.0f)
						[
							SNew(SImage)
							.Image(LogoBrush.Get())
						]
					)
					: StaticCastSharedRef<SWidget>(
						SNew(STextBlock)
						.Text(LOCTEXT("Logo", "A R C W R I G H T"))
						.Font(FCoreStyle::GetDefaultFontStyle("Bold", 14))
						.ColorAndOpacity(BrandBlue)
					)
				]

				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				[
					SNew(SSpacer)
				]

				// Version badge
				+ SHorizontalBox::Slot()
				.AutoWidth()
				.VAlign(VAlign_Center)
				[
					SNew(SBorder)
					.BorderBackgroundColor(GridLines)
					.Padding(FMargin(8.0f, 2.0f))
					[
						SNew(STextBlock)
						.Text(LOCTEXT("Version", "v1.0"))
						.Font(FCoreStyle::GetDefaultFontStyle("Regular", 9))
						.ColorAndOpacity(TextSecondary)
					]
				]
			]
		]

		// Tab row
		+ SVerticalBox::Slot()
		.AutoHeight()
		[
			SNew(SBorder)
			.BorderBackgroundColor(HeaderBg)
			.Padding(FMargin(16.0f, 0.0f, 16.0f, 0.0f))
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 24.0f, 0.0f)
				[
					BuildTabButton(LOCTEXT("TabChat", "Chat"), ETab::Chat)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 24.0f, 0.0f)
				[
					BuildTabButton(LOCTEXT("TabCreate", "Create"), ETab::Create)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				[
					BuildTabButton(LOCTEXT("TabHistory", "History"), ETab::History)
				]
			]
		]

		// Separator line
		+ SVerticalBox::Slot()
		.AutoHeight()
		[
			SNew(SBox)
			.HeightOverride(1.0f)
			[
				SNew(SBorder)
				.BorderBackgroundColor(GridLines)
			]
		];
}

TSharedRef<SWidget> SArcwrightGeneratorPanel::BuildTabButton(const FText& Label, ETab TabType)
{
	// Determine which underline pointer to use
	TSharedPtr<SBorder>* UnderlinePtr = nullptr;
	FOnClicked ClickDelegate;

	switch (TabType)
	{
	case ETab::Chat:
		UnderlinePtr = &TabUnderline_Chat;
		ClickDelegate = FOnClicked::CreateSP(this, &SArcwrightGeneratorPanel::OnTabClicked_Chat);
		break;
	case ETab::Create:
		UnderlinePtr = &TabUnderline_Create;
		ClickDelegate = FOnClicked::CreateSP(this, &SArcwrightGeneratorPanel::OnTabClicked_Create);
		break;
	case ETab::History:
		UnderlinePtr = &TabUnderline_History;
		ClickDelegate = FOnClicked::CreateSP(this, &SArcwrightGeneratorPanel::OnTabClicked_History);
		break;
	}

	bool bIsActive = (TabType == ActiveTab);

	return SNew(SVerticalBox)

		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(0.0f, 4.0f, 0.0f, 4.0f)
		[
			SNew(SButton)
			.ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder"))
			.ContentPadding(FMargin(4.0f, 4.0f))
			.OnClicked(ClickDelegate)
			[
				SNew(STextBlock)
				.Text(Label)
				.Font(FCoreStyle::GetDefaultFontStyle("Bold", 11))
				.ColorAndOpacity(bIsActive
					? FSlateColor(TextPrimary)
					: FSlateColor(TextSecondary))
			]
		]

		// Underline indicator
		+ SVerticalBox::Slot()
		.AutoHeight()
		[
			SAssignNew(*UnderlinePtr, SBorder)
			.BorderBackgroundColor(bIsActive ? BrandBlue : FLinearColor::Transparent)
			.Padding(0)
			[
				SNew(SBox)
				.HeightOverride(2.0f)
			]
		];
}

void SArcwrightGeneratorPanel::SwitchTab(ETab NewTab)
{
	ActiveTab = NewTab;

	if (TabSwitcher.IsValid())
	{
		TabSwitcher->SetActiveWidgetIndex(static_cast<int32>(NewTab));
	}

	// Update underline colors
	auto SetUnderline = [](TSharedPtr<SBorder>& Border, bool bActive)
	{
		if (Border.IsValid())
		{
			Border->SetBorderBackgroundColor(bActive ? BrandBlue : FLinearColor::Transparent);
		}
	};

	SetUnderline(TabUnderline_Chat, NewTab == ETab::Chat);
	SetUnderline(TabUnderline_Create, NewTab == ETab::Create);
	SetUnderline(TabUnderline_History, NewTab == ETab::History);
}

// ============================================================
// Chat tab
// ============================================================

TSharedRef<SWidget> SArcwrightGeneratorPanel::BuildChatTab()
{
	return SNew(SVerticalBox)

		// Message area (fills available space)
		+ SVerticalBox::Slot()
		.FillHeight(1.0f)
		.Padding(0)
		[
			SNew(SBorder)
			.BorderBackgroundColor(DeepNavy)
			.Padding(0)
			[
				SAssignNew(ChatScrollBox, SScrollBox)
				.ScrollBarAlwaysVisible(false)

				+ SScrollBox::Slot()
				.Padding(12.0f, 0.0f, 12.0f, 12.0f)
				[
					SAssignNew(ChatMessageList, SVerticalBox)

					// Hero banner / welcome area
					+ SVerticalBox::Slot()
					.AutoHeight()
					.Padding(0.0f, 0.0f, 0.0f, 16.0f)
					.HAlign(HAlign_Center)
					[
						SNew(SVerticalBox)

						// Hero banner image (or fallback text)
						+ SVerticalBox::Slot()
						.AutoHeight()
						.HAlign(HAlign_Center)
						.Padding(0.0f, 0.0f, 0.0f, 0.0f)
						[
							HeroBannerBrush.IsValid()
							? StaticCastSharedRef<SWidget>(
								SNew(SBox)
								.MaxDesiredWidth(600.0f)
								.HeightOverride(135.0f)
								[
									SNew(SImage)
									.Image(HeroBannerBrush.Get())
								]
							)
							: StaticCastSharedRef<SWidget>(
								SNew(SVerticalBox)

								+ SVerticalBox::Slot()
								.AutoHeight()
								.HAlign(HAlign_Center)
								.Padding(0.0f, 20.0f, 0.0f, 8.0f)
								[
									SNew(STextBlock)
									.Text(LOCTEXT("WelcomeLogo", "A R C W R I G H T"))
									.Font(FCoreStyle::GetDefaultFontStyle("Bold", 18))
									.ColorAndOpacity(BrandBlue)
								]

								+ SVerticalBox::Slot()
								.AutoHeight()
								.HAlign(HAlign_Center)
								[
									SNew(STextBlock)
									.Text(LOCTEXT("WelcomeTagline", "Architect Your Game from Language"))
									.Font(FCoreStyle::GetDefaultFontStyle("Italic", 11))
									.ColorAndOpacity(TextSecondary)
								]
							)
						]

						+ SVerticalBox::Slot()
						.AutoHeight()
						.HAlign(HAlign_Center)
						.Padding(0.0f, 4.0f, 0.0f, 0.0f)
						[
							SNew(STextBlock)
							.Text(LOCTEXT("WelcomeHint",
								"Try: \"Create a health pickup\" or \"Make a patrol behavior tree\""))
							.Font(FCoreStyle::GetDefaultFontStyle("Regular", 10))
							.ColorAndOpacity(TextDim)
						]
					]
				]
			]
		]

		// Input bar
		+ SVerticalBox::Slot()
		.AutoHeight()
		[
			BuildInputBar()
		];
}

TSharedRef<SWidget> SArcwrightGeneratorPanel::BuildInputBar()
{
	return SNew(SBorder)
		.BorderBackgroundColor(HeaderBg)
		.Padding(FMargin(12.0f, 8.0f))
		[
			SNew(SHorizontalBox)

			// Microphone placeholder button (left)
			+ SHorizontalBox::Slot()
			.AutoWidth()
			.VAlign(VAlign_Center)
			.Padding(0.0f, 0.0f, 8.0f, 0.0f)
			[
				SNew(SBox)
				.WidthOverride(32.0f)
				.HeightOverride(32.0f)
				[
					SNew(SBorder)
					.BorderBackgroundColor(CardBg)
					.Padding(0)
					.HAlign(HAlign_Center)
					.VAlign(VAlign_Center)
					[
						SNew(STextBlock)
						.Text(FText::FromString(FString(TEXT("\xF0\x9F\x8E\x99")))) // mic emoji fallback
						.Font(FCoreStyle::GetDefaultFontStyle("Regular", 12))
						.ColorAndOpacity(TextDim)
					]
				]
			]

			// Text input (multi-line: Enter=send, Shift+Enter=newline)
			+ SHorizontalBox::Slot()
			.FillWidth(1.0f)
			.VAlign(VAlign_Center)
			[
				SNew(SBorder)
				.BorderBackgroundColor(BorderLine)
				.Padding(1.0f) // 1px border
				[
					SNew(SBorder)
					.BorderBackgroundColor(CardBg)
					.Padding(FMargin(10.0f, 6.0f))
					[
						SNew(SBox)
						.MaxDesiredHeight(80.0f)
						[
							SAssignNew(ChatInput, SMultiLineEditableTextBox)
							.HintText(LOCTEXT("ChatHint", "Type a message... (Shift+Enter for newline)"))
							.Font(FCoreStyle::GetDefaultFontStyle("Regular", 11))
							.ForegroundColor(TextPrimary)
							.BackgroundColor(CardBg)
							.AutoWrapText(true)
							.OnKeyDownHandler(this, &SArcwrightGeneratorPanel::OnChatInputKeyDown)
						]
					]
				]
			]

			// Send button (right)
			+ SHorizontalBox::Slot()
			.AutoWidth()
			.VAlign(VAlign_Center)
			.Padding(8.0f, 0.0f, 0.0f, 0.0f)
			[
				SNew(SButton)
				.ButtonColorAndOpacity(BrandBlue)
				.ContentPadding(FMargin(12.0f, 6.0f))
				.OnClicked(this, &SArcwrightGeneratorPanel::OnSendClicked)
				[
					SNew(STextBlock)
					.Text(FText::FromString(FString(TEXT("\u25B6")))) // right-pointing triangle
					.Font(FCoreStyle::GetDefaultFontStyle("Bold", 14))
					.ColorAndOpacity(FSlateColor(FLinearColor::White))
				]
			]
		];
}

// ============================================================
// Chat message construction
// ============================================================

TSharedRef<SWidget> SArcwrightGeneratorPanel::BuildMessageWidget(TSharedPtr<FArcwrightChatMessage> Msg)
{
	if (!Msg.IsValid()) return SNew(SSpacer);

	bool bUser = Msg->bIsUser;
	FLinearColor BubbleBg = bUser ? UserBubble : (Msg->bIsError ? ErrorBg : CardBg);
	EHorizontalAlignment Align = bUser ? HAlign_Right : HAlign_Left;

	// Left border color: user=BrandBlue, error=ErrorRed, assistant=domain color
	FLinearColor BorderColor = bUser ? BrandBlue
		: (Msg->bIsError ? ErrorRed : ArcwrightColors::GetDomainColor(Msg->Domain));

	// Build content
	TSharedRef<SVerticalBox> ContentBox = SNew(SVerticalBox);

	// Assistant header: label + domain tag
	if (!bUser)
	{
		ContentBox->AddSlot()
		.AutoHeight()
		.Padding(0.0f, 0.0f, 0.0f, 4.0f)
		[
			SNew(SHorizontalBox)

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(0.0f, 0.0f, 8.0f, 0.0f)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("AssistantLabel", "ARCWRIGHT"))
				.Font(FCoreStyle::GetDefaultFontStyle("Bold", 8))
				.ColorAndOpacity(Msg->bIsError ? ErrorRed : BrandBlue)
			]

			// Domain indicator tag
			+ SHorizontalBox::Slot()
			.AutoWidth()
			[
				SNew(SBorder)
				.BorderBackgroundColor(GridLines)
				.Padding(FMargin(6.0f, 1.0f))
				[
					SNew(STextBlock)
					.Text(FText::FromString(ArcwrightColors::GetDomainLabel(Msg->Domain)))
					.Font(FCoreStyle::GetDefaultFontStyle("Bold", 7))
					.ColorAndOpacity(ArcwrightColors::GetDomainColor(Msg->Domain))
				]
			]

			// Intent mode badge (only for non-CREATE modes)
			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(4.0f, 0.0f, 0.0f, 0.0f)
			[
				(!Msg->IntentMode.IsEmpty() && Msg->IntentMode != TEXT("CREATE"))
				? StaticCastSharedRef<SWidget>(
					SNew(SBorder)
					.BorderBackgroundColor(GetModeColor(Msg->IntentMode))
					.Padding(FMargin(6.0f, 1.0f))
					[
						SNew(STextBlock)
						.Text(FText::FromString(GetModeLabel(Msg->IntentMode)))
						.Font(FCoreStyle::GetDefaultFontStyle("Bold", 7))
						.ColorAndOpacity(FLinearColor::White)
					]
				)
				: StaticCastSharedRef<SWidget>(SNew(SSpacer).Size(FVector2D::ZeroVector))
			]
		];
	}

	// Message text (selectable + copyable)
	if (!Msg->Text.IsEmpty())
	{
		FLinearColor TextColor = Msg->bIsThinking ? TextDim : TextPrimary;
		if (Msg->bIsError) TextColor = FLinearColor(1.0f, 0.7f, 0.7f, 1.0f);

		ContentBox->AddSlot()
		.AutoHeight()
		[
			SNew(SMultiLineEditableTextBox)
			.Text(FText::FromString(Msg->Text))
			.Font(FCoreStyle::GetDefaultFontStyle("Regular", 11))
			.ForegroundColor(TextColor)
			.BackgroundColor(FLinearColor::Transparent)
			.ReadOnlyForegroundColor(TextColor)
			.IsReadOnly(true)
			.AutoWrapText(true)
			.Padding(FMargin(0.0f))
		];
	}

	// Progress steps
	if (Msg->Steps.Num() > 0)
	{
		ContentBox->AddSlot()
		.AutoHeight()
		.Padding(0.0f, 6.0f, 0.0f, 0.0f)
		[
			BuildStepsWidget(Msg->Steps, Msg->Progress)
		];
	}

	// Asset card
	if (Msg->AssetCard.IsValid())
	{
		ContentBox->AddSlot()
		.AutoHeight()
		.Padding(0.0f, 8.0f, 0.0f, 0.0f)
		[
			BuildAssetCardWidget(Msg->AssetCard)
		];
	}

	// Timestamp
	ContentBox->AddSlot()
	.AutoHeight()
	.Padding(0.0f, 4.0f, 0.0f, 0.0f)
	[
		SNew(STextBlock)
		.Text(FText::FromString(Msg->Timestamp.ToString(TEXT("%H:%M"))))
		.Font(FCoreStyle::GetDefaultFontStyle("Regular", 8))
		.ColorAndOpacity(TextDim)
	];

	// Verbose result details (rich per-mode output from ExecutePlan)
	if (!Msg->ResultDetails.IsEmpty() && !Msg->bIsUser)
	{
		ContentBox->AddSlot()
		.AutoHeight()
		.Padding(0.0f, 6.0f, 0.0f, 0.0f)
		[
			BuildResultDetailsWidget(Msg)
		];
	}

	// Wrap in bubble with 3px colored left border
	float MaxWidth = 700.0f;

	return SNew(SBox)
		.HAlign(Align)
		.Padding(FMargin(0.0f, 0.0f, 0.0f, 8.0f))
		[
			SNew(SBox)
			.MaxDesiredWidth(MaxWidth)
			[
				SNew(SHorizontalBox)

				// 3px domain-colored left border strip
				+ SHorizontalBox::Slot()
				.AutoWidth()
				[
					SNew(SBox)
					.WidthOverride(3.0f)
					[
						SNew(SBorder)
						.BorderBackgroundColor(BorderColor)
					]
				]

				// Bubble content
				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				[
					SNew(SBorder)
					.BorderBackgroundColor(BubbleBg)
					.Padding(FMargin(12.0f, 8.0f))
					[
						ContentBox
					]
				]
			]
		];
}

TSharedRef<SWidget> SArcwrightGeneratorPanel::BuildAssetCardWidget(TSharedPtr<FArcwrightAssetCard> Card)
{
	if (!Card.IsValid()) return SNew(SSpacer);

	// Domain color for accent
	FLinearColor DomainColor = ArcwrightColors::GetDomainColor(Card->Domain);

	// Domain icon character
	FString IconStr;
	switch (Card->Domain)
	{
	case EArcwrightDomain::Blueprint:     IconStr = TEXT("\u2699"); break; // gear
	case EArcwrightDomain::BehaviorTree:  IconStr = TEXT("\u2442"); break; // tree-like
	case EArcwrightDomain::DataTable:     IconStr = TEXT("\u2637"); break; // table-like
	}

	FString StatusStr = Card->bHasError
		? FString::Printf(TEXT("Error: %s"), *Card->ErrorText)
		: TEXT("Compiled \u2713");
	FLinearColor StatusColor = Card->bHasError ? ErrorRed : SuccessGreen;

	FString StatsStr = FString::Printf(TEXT("%d nodes, %d connections"),
		Card->NodeCount, Card->ConnectionCount);

	// Make the asset name clickable
	FString AssetPath = Card->AssetPath;

	return SNew(SHorizontalBox)

		// 3px domain-colored left border
		+ SHorizontalBox::Slot()
		.AutoWidth()
		[
			SNew(SBox)
			.WidthOverride(3.0f)
			[
				SNew(SBorder)
				.BorderBackgroundColor(DomainColor)
			]
		]

		// Card content
		+ SHorizontalBox::Slot()
		.FillWidth(1.0f)
		[
			SNew(SBorder)
			.BorderBackgroundColor(CardHover)
			.Padding(FMargin(10.0f, 8.0f))
			[
				SNew(SHorizontalBox)

				// Icon
				+ SHorizontalBox::Slot()
				.AutoWidth()
				.VAlign(VAlign_Top)
				.Padding(0.0f, 0.0f, 10.0f, 0.0f)
				[
					SNew(SBox)
					.WidthOverride(32.0f)
					.HeightOverride(32.0f)
					[
						SNew(SBorder)
						.BorderBackgroundColor(GridLines)
						.HAlign(HAlign_Center)
						.VAlign(VAlign_Center)
						[
							SNew(STextBlock)
							.Text(FText::FromString(IconStr))
							.Font(FCoreStyle::GetDefaultFontStyle("Regular", 16))
							.ColorAndOpacity(DomainColor)
						]
					]
				]

				// Info
				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				[
					SNew(SVerticalBox)

					// Asset name (clickable, domain color)
					+ SVerticalBox::Slot()
					.AutoHeight()
					[
						SNew(SButton)
						.ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder"))
						.ContentPadding(0)
						.OnClicked_Lambda([AssetPath]() -> FReply
						{
							if (GEditor)
							{
								UObject* Asset = StaticFindObject(UObject::StaticClass(), nullptr, *AssetPath);
								if (Asset)
								{
									GEditor->GetEditorSubsystem<UAssetEditorSubsystem>()->OpenEditorForAsset(Asset);
								}
							}
							return FReply::Handled();
						})
						[
							SNew(STextBlock)
							.Text(FText::FromString(Card->AssetName))
							.Font(FCoreStyle::GetDefaultFontStyle("Bold", 11))
							.ColorAndOpacity(DomainColor)
						]
					]

					// Stats
					+ SVerticalBox::Slot()
					.AutoHeight()
					.Padding(0.0f, 2.0f, 0.0f, 2.0f)
					[
						SNew(STextBlock)
						.Text(FText::FromString(StatsStr))
						.Font(FCoreStyle::GetDefaultFontStyle("Regular", 9))
						.ColorAndOpacity(TextSecondary)
					]

					// Status badge
					+ SVerticalBox::Slot()
					.AutoHeight()
					[
						SNew(STextBlock)
						.Text(FText::FromString(StatusStr))
						.Font(FCoreStyle::GetDefaultFontStyle("Bold", 9))
						.ColorAndOpacity(StatusColor)
					]
				]
			]
		];
}

TSharedRef<SWidget> SArcwrightGeneratorPanel::BuildStepsWidget(const TArray<FArcwrightStep>& Steps, float Progress)
{
	TSharedRef<SVerticalBox> Box = SNew(SVerticalBox);

	for (const FArcwrightStep& Step : Steps)
	{
		FString Icon;
		FLinearColor IconColor;

		switch (Step.Status)
		{
		case EStepStatus::Complete:
			Icon = TEXT("\u2713"); // checkmark
			IconColor = SuccessGreen;
			break;
		case EStepStatus::InProgress:
			Icon = TEXT("\u25CB"); // circle
			IconColor = BrandBlue;
			break;
		case EStepStatus::Failed:
			Icon = TEXT("\u2717"); // X mark
			IconColor = ErrorRed;
			break;
		default:
			Icon = TEXT("\u25A1"); // empty square
			IconColor = TextDim;
			break;
		}

		FLinearColor LabelColor = (Step.Status == EStepStatus::Pending) ? TextDim : TextPrimary;

		Box->AddSlot()
		.AutoHeight()
		.Padding(0.0f, 1.0f)
		[
			SNew(SHorizontalBox)

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(0.0f, 0.0f, 6.0f, 0.0f)
			[
				SNew(STextBlock)
				.Text(FText::FromString(Icon))
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 10))
				.ColorAndOpacity(IconColor)
			]

			+ SHorizontalBox::Slot()
			.FillWidth(1.0f)
			[
				SNew(STextBlock)
				.Text(FText::FromString(Step.Label))
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 10))
				.ColorAndOpacity(LabelColor)
			]
		];
	}

	// Progress bar
	if (Progress > 0.0f)
	{
		Box->AddSlot()
		.AutoHeight()
		.Padding(0.0f, 6.0f, 0.0f, 0.0f)
		[
			SNew(SBox)
			.HeightOverride(4.0f)
			[
				SNew(SOverlay)

				// Background track
				+ SOverlay::Slot()
				[
					SNew(SBorder)
					.BorderBackgroundColor(GridLines)
				]

				// Filled portion
				+ SOverlay::Slot()
				.HAlign(HAlign_Left)
				[
					SNew(SBox)
					.WidthOverride(Progress * 300.0f) // Approximate — scales with bubble width
					[
						SNew(SBorder)
						.BorderBackgroundColor(BrandBlue)
					]
				]
			]
		];
	}

	return Box;
}

// ============================================================
// Verbose result details widget (color-coded per-line output)
// ============================================================

TSharedRef<SWidget> SArcwrightGeneratorPanel::BuildResultDetailsWidget(TSharedPtr<FArcwrightChatMessage> Msg)
{
	if (!Msg.IsValid() || Msg->ResultDetails.IsEmpty())
	{
		return SNew(SSpacer);
	}

	// Build the entire result as a single selectable text block
	// (same approach as the log panel — users can click-drag-select and Ctrl+C)
	FString FullText = Msg->ResultDetails;

	// Append success/failure summary
	if (Msg->SucceededCount > 0 || Msg->FailedCount > 0)
	{
		FullText += TEXT("\n");
		FullText += FString::Printf(TEXT("\u2713 %d succeeded  \u2717 %d failed"),
			Msg->SucceededCount, Msg->FailedCount);
	}

	// Wrap in a background card with a single read-only selectable text box
	return SNew(SBorder)
		.BorderBackgroundColor(FLinearColor(CardBg.R * 0.9f, CardBg.G * 0.9f, CardBg.B * 0.9f, 1.0f))
		.Padding(FMargin(8.0f, 6.0f))
		[
			SNew(SMultiLineEditableTextBox)
			.Text(FText::FromString(FullText))
			.Font(FCoreStyle::GetDefaultFontStyle("Mono", 9))
			.ForegroundColor(TextPrimary)
			.BackgroundColor(FLinearColor::Transparent)
			.ReadOnlyForegroundColor(TextPrimary)
			.IsReadOnly(true)
			.AutoWrapText(true)
			.Padding(FMargin(0.0f))
		];
}

// ============================================================
// Chat message management
// ============================================================

void SArcwrightGeneratorPanel::AddUserMessage(const FString& Text)
{
	TSharedPtr<FArcwrightChatMessage> Msg = MakeShared<FArcwrightChatMessage>();
	Msg->bIsUser = true;
	Msg->Text = Text;
	Msg->Timestamp = FDateTime::Now();
	ChatMessages.Add(Msg);
	RefreshChatList();
}

void SArcwrightGeneratorPanel::AddThinkingMessage()
{
	// Detect domain from the last user message for proper coloring
	EArcwrightDomain Domain = EArcwrightDomain::Blueprint;
	for (int32 i = ChatMessages.Num() - 1; i >= 0; --i)
	{
		if (ChatMessages[i]->bIsUser)
		{
			Domain = DetectDomainFromPrompt(ChatMessages[i]->Text);
			break;
		}
	}

	TSharedPtr<FArcwrightChatMessage> Msg = MakeShared<FArcwrightChatMessage>();
	Msg->bIsUser = false;
	Msg->bIsThinking = true;
	Msg->Text = TEXT("Thinking...");
	Msg->Timestamp = FDateTime::Now();
	Msg->Domain = Domain;
	ChatMessages.Add(Msg);
	RefreshChatList();
}

void SArcwrightGeneratorPanel::AddAssistantMessage(const FString& Text, bool bError)
{
	TSharedPtr<FArcwrightChatMessage> Msg = MakeShared<FArcwrightChatMessage>();
	Msg->bIsUser = false;
	Msg->Text = Text;
	Msg->Timestamp = FDateTime::Now();
	Msg->bIsError = bError;
	ChatMessages.Add(Msg);
	RefreshChatList();
}

void SArcwrightGeneratorPanel::UpdateLastAssistantMessage(const FString& Text, bool bError, TSharedPtr<FArcwrightAssetCard> Card)
{
	// Find the last assistant message
	for (int32 i = ChatMessages.Num() - 1; i >= 0; --i)
	{
		if (!ChatMessages[i]->bIsUser)
		{
			ChatMessages[i]->Text = Text;
			ChatMessages[i]->bIsThinking = false;
			ChatMessages[i]->bIsError = bError;
			if (Card.IsValid())
			{
				ChatMessages[i]->AssetCard = Card;
			}
			break;
		}
	}
	RefreshChatList();
}

void SArcwrightGeneratorPanel::RefreshChatList()
{
	if (!ChatMessageList.IsValid()) return;

	ChatMessageList->ClearChildren();

	// Re-add welcome section at top
	ChatMessageList->AddSlot()
	.AutoHeight()
	.Padding(0.0f, 0.0f, 0.0f, 16.0f)
	.HAlign(HAlign_Center)
	[
		SNew(SVerticalBox)

		+ SVerticalBox::Slot()
		.AutoHeight()
		.HAlign(HAlign_Center)
		.Padding(0.0f, 20.0f, 0.0f, 8.0f)
		[
			SNew(STextBlock)
			.Text(LOCTEXT("WelcomeLogoR", "A R C W R I G H T"))
			.Font(FCoreStyle::GetDefaultFontStyle("Bold", 18))
			.ColorAndOpacity(BrandBlue)
		]

		+ SVerticalBox::Slot()
		.AutoHeight()
		.HAlign(HAlign_Center)
		[
			SNew(STextBlock)
			.Text(LOCTEXT("WelcomeTagR", "Architect Your Game from Language"))
			.Font(FCoreStyle::GetDefaultFontStyle("Italic", 11))
			.ColorAndOpacity(TextSecondary)
		]
	];

	// Add messages
	for (auto& Msg : ChatMessages)
	{
		ChatMessageList->AddSlot()
		.AutoHeight()
		[
			BuildMessageWidget(Msg)
		];
	}

	// Scroll to bottom
	if (ChatScrollBox.IsValid())
	{
		ChatScrollBox->ScrollToEnd();
	}
}

// ============================================================
// Chat input handling
// ============================================================

FReply SArcwrightGeneratorPanel::OnChatInputKeyDown(const FGeometry& Geometry, const FKeyEvent& KeyEvent)
{
	if (KeyEvent.GetKey() == EKeys::Enter && !KeyEvent.IsShiftDown())
	{
		OnSendClicked();
		return FReply::Handled();
	}
	return FReply::Unhandled();
}

FReply SArcwrightGeneratorPanel::OnSendClicked()
{
	if (!ChatInput.IsValid() || bIsGenerating || bAwaitingConfirmation)
	{
		return FReply::Handled();
	}

	FString UserText = ChatInput->GetText().ToString().TrimStartAndEnd();
	if (UserText.IsEmpty())
	{
		return FReply::Handled();
	}

	// Clear input
	ChatInput->SetText(FText::GetEmpty());

	// Add user message
	AddUserMessage(UserText);

	// Add thinking message
	AddThinkingMessage();

	// Force UI update before synchronous generation
	FSlateApplication::Get().Tick();

	// Generate
	GenerateFromChat(UserText);

	return FReply::Handled();
}

// ============================================================
// Domain auto-detection
// ============================================================

EArcwrightDomain SArcwrightGeneratorPanel::DetectDomainFromPrompt(const FString& Prompt) const
{
	FString Lower = Prompt.ToLower();

	// BT keywords
	if (Lower.Contains(TEXT("behavior tree")) || Lower.Contains(TEXT("behaviour tree")) ||
		Lower.Contains(TEXT("patrol")) || Lower.Contains(TEXT("chase")) ||
		Lower.Contains(TEXT(" ai ")) || Lower.Contains(TEXT("bt_")) ||
		Lower.Contains(TEXT("blackboard")) || Lower.Contains(TEXT("selector")) ||
		Lower.Contains(TEXT("sequence node")))
	{
		return EArcwrightDomain::BehaviorTree;
	}

	// DT keywords
	if (Lower.Contains(TEXT("data table")) || Lower.Contains(TEXT("datatable")) ||
		Lower.Contains(TEXT("weapons table")) || Lower.Contains(TEXT("items table")) ||
		Lower.Contains(TEXT("stats table")) || Lower.Contains(TEXT("dt_")) ||
		Lower.Contains(TEXT("inventory")) || Lower.Contains(TEXT("loot table")))
	{
		return EArcwrightDomain::DataTable;
	}

	// Default to Blueprint
	return EArcwrightDomain::Blueprint;
}

// ============================================================
// Chat-based generation
// ============================================================

void SArcwrightGeneratorPanel::GenerateFromChat(const FString& Prompt)
{
	bIsGenerating = true;

	// Classify intent via LLM (or offline fallback)
	FArcwrightIntentPlan Plan = ClassifyIntent(Prompt);

	// Set IntentMode on the current thinking message so the badge renders
	for (int32 i = ChatMessages.Num() - 1; i >= 0; --i)
	{
		if (!ChatMessages[i]->bIsUser)
		{
			ChatMessages[i]->IntentMode = Plan.Mode;
			break;
		}
	}

	// Route based on mode
	if (Plan.Mode == TEXT("CLARIFY"))
	{
		// LLM is asking for more info — display the question
		UpdateLastAssistantMessage(Plan.Summary, false);
		bIsGenerating = false;
		return;
	}

	if (Plan.bRequiresConfirmation)
	{
		// Show plan preview and wait for user confirmation
		DisplayPlanPreview(Plan);
		bIsGenerating = false;
		return;
	}

	// Execute immediately (CREATE, simple QUERY, etc.)
	ExecutePlan(Plan);
	bIsGenerating = false;
}

void SArcwrightGeneratorPanel::DoGenerateBlueprint(const FString& Prompt)
{
	// Extract a Blueprint name from the prompt
	FString BPName = TEXT("BP_Generated");

	// Try to extract a meaningful name from the prompt
	// "Create a health pickup" -> "BP_HealthPickup"
	FString CleanPrompt = Prompt;
	CleanPrompt.ReplaceInline(TEXT("create "), TEXT(""), ESearchCase::IgnoreCase);
	CleanPrompt.ReplaceInline(TEXT("make "), TEXT(""), ESearchCase::IgnoreCase);
	CleanPrompt.ReplaceInline(TEXT("build "), TEXT(""), ESearchCase::IgnoreCase);
	CleanPrompt.ReplaceInline(TEXT("a "), TEXT(""), ESearchCase::IgnoreCase);
	CleanPrompt.ReplaceInline(TEXT("an "), TEXT(""), ESearchCase::IgnoreCase);
	CleanPrompt.ReplaceInline(TEXT("the "), TEXT(""), ESearchCase::IgnoreCase);
	CleanPrompt = CleanPrompt.TrimStartAndEnd();

	if (!CleanPrompt.IsEmpty())
	{
		// CamelCase the words
		TArray<FString> Words;
		CleanPrompt.ParseIntoArray(Words, TEXT(" "), true);
		FString CamelName;
		for (const FString& W : Words)
		{
			if (W.Len() > 0)
			{
				CamelName += W.Left(1).ToUpper() + W.Mid(1).ToLower();
			}
		}
		if (!CamelName.IsEmpty())
		{
			BPName = TEXT("BP_") + CamelName;
		}
	}

	// Build a minimal Blueprint IR
	FString IR = FString::Printf(TEXT(
		"{"
		"  \"metadata\": {"
		"    \"name\": \"%s\","
		"    \"parent_class\": \"Actor\","
		"    \"category\": null"
		"  },"
		"  \"variables\": [],"
		"  \"nodes\": ["
		"    {"
		"      \"id\": \"BeginPlay\","
		"      \"dsl_type\": \"Event_BeginPlay\","
		"      \"params\": {},"
		"      \"ue_class\": \"UK2Node_Event\","
		"      \"ue_event\": \"ReceiveBeginPlay\","
		"      \"position\": [0, 0]"
		"    },"
		"    {"
		"      \"id\": \"Print1\","
		"      \"dsl_type\": \"PrintString\","
		"      \"params\": {\"I\": \"%s created by Arcwright\"},"
		"      \"ue_class\": \"UK2Node_CallFunction\","
		"      \"ue_function\": \"/Script/Engine.KismetSystemLibrary:PrintString\","
		"      \"position\": [300, 0]"
		"    }"
		"  ],"
		"  \"connections\": ["
		"    {"
		"      \"src_node\": \"BeginPlay\","
		"      \"src_pin\": \"Then\","
		"      \"dst_node\": \"Print1\","
		"      \"dst_pin\": \"Execute\""
		"    }"
		"  ]"
		"}"
	), *BPName, *BPName);

	// Parse and build
	FDSLBlueprint DSL;
	if (!FDSLImporter::ParseIRFromString(IR, DSL))
	{
		UpdateLastAssistantMessage(
			FString::Printf(TEXT("Failed to create %s. The IR could not be parsed."), *BPName),
			true);
		return;
	}

	FString PackagePath = TEXT("/Game/BlueprintLLM/Generated");
	FString FullPath = PackagePath / DSL.Name;

	// Delete existing
	UObject* ExistingObj = StaticFindObject(UObject::StaticClass(), nullptr, *FullPath);
	if (ExistingObj)
	{
		TArray<UObject*> ObjsToDelete;
		ObjsToDelete.Add(ExistingObj);
		ObjectTools::ForceDeleteObjects(ObjsToDelete, false);
	}

	UBlueprint* NewBP = FBlueprintBuilder::CreateBlueprint(DSL, PackagePath);
	if (!NewBP)
	{
		AddLogEntry(ELogEntryType::Error, FString::Printf(TEXT("Failed to build Blueprint: %s"), *BPName));
		UpdateLastAssistantMessage(
			FString::Printf(TEXT("Failed to build Blueprint: %s"), *BPName),
			true);
		return;
	}

	AddLogEntry(ELogEntryType::Success, FString::Printf(TEXT("Created Blueprint: %s"), *BPName));

	// Count nodes and connections
	int32 NodeCount = 0;
	int32 ConnCount = 0;
	UEdGraph* EventGraph = FBlueprintEditorUtils::FindEventGraph(NewBP);
	if (EventGraph)
	{
		NodeCount = EventGraph->Nodes.Num();
		for (UEdGraphNode* Node : EventGraph->Nodes)
		{
			for (UEdGraphPin* Pin : Node->Pins)
			{
				ConnCount += Pin->LinkedTo.Num();
			}
		}
		ConnCount /= 2; // Each connection counted twice
	}

	// Create asset card
	TSharedPtr<FArcwrightAssetCard> Card = MakeShared<FArcwrightAssetCard>();
	Card->AssetName = BPName;
	Card->AssetPath = FullPath + TEXT(".") + DSL.Name;
	Card->Domain = EArcwrightDomain::Blueprint;
	Card->NodeCount = NodeCount;
	Card->ConnectionCount = ConnCount;
	Card->bCompiled = true;
	Card->bHasError = false;

	UpdateLastAssistantMessage(
		FString::Printf(TEXT("Created Blueprint \"%s\" with %d nodes."), *BPName, NodeCount),
		false,
		Card);

	// Open in editor
	if (GEditor)
	{
		UAssetEditorSubsystem* Sub = GEditor->GetEditorSubsystem<UAssetEditorSubsystem>();
		if (Sub)
		{
			Sub->OpenEditorForAsset(NewBP);
		}
	}

	UE_LOG(LogArcwright, Log, TEXT("Arcwright Chat: Created Blueprint %s (%d nodes, %d connections)"),
		*BPName, NodeCount, ConnCount);
}

void SArcwrightGeneratorPanel::DoGenerateBehaviorTree(const FString& Prompt)
{
	// For now, create a minimal BT with a Wait task
	FString BTName = TEXT("BT_Generated");

	// Try to extract a name
	FString Lower = Prompt.ToLower();
	if (Lower.Contains(TEXT("patrol")))
		BTName = TEXT("BT_Patrol");
	else if (Lower.Contains(TEXT("chase")))
		BTName = TEXT("BT_Chase");
	else if (Lower.Contains(TEXT("guard")))
		BTName = TEXT("BT_Guard");

	FString IR = FString::Printf(TEXT(
		"{"
		"  \"name\": \"%s\","
		"  \"blackboard_name\": \"BB_%s\","
		"  \"blackboard_keys\": ["
		"    {\"name\": \"TargetActor\", \"type\": \"Object\"}"
		"  ],"
		"  \"root\": {"
		"    \"type\": \"Selector\","
		"    \"name\": \"Root\","
		"    \"children\": ["
		"      {"
		"        \"type\": \"Sequence\","
		"        \"name\": \"MainSequence\","
		"        \"children\": ["
		"          {"
		"            \"type\": \"Task\","
		"            \"task_type\": \"Wait\","
		"            \"name\": \"WaitTask\","
		"            \"params\": {\"WaitTime\": \"3.0\"}"
		"          }"
		"        ]"
		"      }"
		"    ]"
		"  }"
		"}"
	), *BTName, *BTName.Mid(3)); // Strip "BT_" prefix for BB name

	TSharedPtr<FJsonObject> IRJson;
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(IR);
	if (!FJsonSerializer::Deserialize(Reader, IRJson) || !IRJson.IsValid())
	{
		UpdateLastAssistantMessage(TEXT("Failed to create Behavior Tree."), true);
		return;
	}

	FString PackagePath = TEXT("/Game/BlueprintLLM/BehaviorTrees");
	FBehaviorTreeBuilder::FBTBuildResult Result = FBehaviorTreeBuilder::CreateFromIR(IRJson, PackagePath);

	if (!Result.bSuccess)
	{
		AddLogEntry(ELogEntryType::Error, FString::Printf(TEXT("BT error: %s"), *Result.ErrorMessage.Left(150)));
		UpdateLastAssistantMessage(
			FString::Printf(TEXT("Behavior Tree error: %s"), *Result.ErrorMessage),
			true);
		return;
	}

	AddLogEntry(ELogEntryType::Success, FString::Printf(TEXT("Created BT: %s (%d composites, %d tasks)"),
		*BTName, Result.CompositeCount, Result.TaskCount));

	TSharedPtr<FArcwrightAssetCard> Card = MakeShared<FArcwrightAssetCard>();
	Card->AssetName = BTName;
	Card->AssetPath = Result.TreeAssetPath;
	Card->Domain = EArcwrightDomain::BehaviorTree;
	Card->NodeCount = Result.CompositeCount + Result.TaskCount;
	Card->ConnectionCount = Result.DecoratorCount + Result.ServiceCount;
	Card->bCompiled = true;

	UpdateLastAssistantMessage(
		FString::Printf(TEXT("Created Behavior Tree \"%s\" (%d composites, %d tasks, %d decorators)."),
			*BTName, Result.CompositeCount, Result.TaskCount, Result.DecoratorCount),
		false,
		Card);

	// Open in editor
	if (GEditor)
	{
		UObject* Asset = StaticFindObject(UObject::StaticClass(), nullptr, *Result.TreeAssetPath);
		if (Asset)
		{
			GEditor->GetEditorSubsystem<UAssetEditorSubsystem>()->OpenEditorForAsset(Asset);
		}
	}

	UE_LOG(LogArcwright, Log, TEXT("Arcwright Chat: Created BT %s"), *BTName);
}

void SArcwrightGeneratorPanel::DoGenerateDataTable(const FString& Prompt)
{
	FString DTName = TEXT("DT_Generated");

	FString Lower = Prompt.ToLower();
	if (Lower.Contains(TEXT("weapon")))
		DTName = TEXT("DT_Weapons");
	else if (Lower.Contains(TEXT("item")))
		DTName = TEXT("DT_Items");
	else if (Lower.Contains(TEXT("enem")))
		DTName = TEXT("DT_Enemies");

	FString IR = FString::Printf(TEXT(
		"{"
		"  \"table_name\": \"%s\","
		"  \"struct_name\": \"S_%s\","
		"  \"columns\": ["
		"    {\"name\": \"Name\", \"type\": \"String\", \"default\": \"\"},"
		"    {\"name\": \"Value\", \"type\": \"Float\", \"default\": \"0.0\"}"
		"  ],"
		"  \"rows\": ["
		"    {\"row_name\": \"Default\", \"values\": {\"Name\": \"Default\", \"Value\": \"1.0\"}}"
		"  ]"
		"}"
	), *DTName, *DTName.Mid(3));

	TSharedPtr<FJsonObject> IRJson;
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(IR);
	if (!FJsonSerializer::Deserialize(Reader, IRJson) || !IRJson.IsValid())
	{
		UpdateLastAssistantMessage(TEXT("Failed to create Data Table."), true);
		return;
	}

	FString PackagePath = TEXT("/Game/BlueprintLLM/DataTables");
	FDataTableBuilder::FDTBuildResult Result = FDataTableBuilder::CreateFromIR(IRJson, PackagePath);

	if (!Result.bSuccess)
	{
		AddLogEntry(ELogEntryType::Error, FString::Printf(TEXT("DT error: %s"), *Result.ErrorMessage.Left(150)));
		UpdateLastAssistantMessage(
			FString::Printf(TEXT("Data Table error: %s"), *Result.ErrorMessage),
			true);
		return;
	}

	AddLogEntry(ELogEntryType::Success, FString::Printf(TEXT("Created DT: %s (%d cols, %d rows)"),
		*DTName, Result.ColumnCount, Result.RowCount));

	TSharedPtr<FArcwrightAssetCard> Card = MakeShared<FArcwrightAssetCard>();
	Card->AssetName = DTName;
	Card->AssetPath = Result.TableAssetPath;
	Card->Domain = EArcwrightDomain::DataTable;
	Card->NodeCount = Result.ColumnCount;
	Card->ConnectionCount = Result.RowCount;
	Card->bCompiled = true;

	UpdateLastAssistantMessage(
		FString::Printf(TEXT("Created Data Table \"%s\" (%d columns, %d rows)."),
			*DTName, Result.ColumnCount, Result.RowCount),
		false,
		Card);

	if (GEditor)
	{
		UObject* Asset = StaticFindObject(UObject::StaticClass(), nullptr, *Result.TableAssetPath);
		if (Asset)
		{
			GEditor->GetEditorSubsystem<UAssetEditorSubsystem>()->OpenEditorForAsset(Asset);
		}
	}

	UE_LOG(LogArcwright, Log, TEXT("Arcwright Chat: Created DT %s"), *DTName);
}

// ============================================================
// Intent routing (LLM-based)
// ============================================================

FString SArcwrightGeneratorPanel::GetModeLabel(const FString& Mode) const
{
	if (Mode == TEXT("MODIFY")) return TEXT("MODIFY");
	if (Mode == TEXT("QUERY"))  return TEXT("QUERY");
	if (Mode == TEXT("MULTI"))  return TEXT("MULTI");
	if (Mode == TEXT("CLARIFY")) return TEXT("CLARIFY");
	return TEXT("CREATE");
}

FLinearColor SArcwrightGeneratorPanel::GetModeColor(const FString& Mode) const
{
	if (Mode == TEXT("MODIFY")) return SuccessGreen;
	if (Mode == TEXT("QUERY"))  return WarningAmber;
	if (Mode == TEXT("MULTI"))  return Purple;
	if (Mode == TEXT("CLARIFY")) return WarningAmber;
	return BrandBlue;
}

// Translate a command + params into human-readable English for plan preview
static FString DescribeOperation(const FArcwrightOperation& Op)
{
	FString Cmd = Op.Command.ToLower();
	FString Desc;

	auto GetParam = [&](const FString& Key) -> FString
	{
		if (!Op.Params.IsValid()) return TEXT("");
		FString Val;
		if (Op.Params->TryGetStringField(Key, Val)) return Val;
		return TEXT("");
	};

	if (Cmd == TEXT("find_actors"))
	{
		FString Filter = GetParam(TEXT("name_filter"));
		if (Filter.IsEmpty()) Filter = GetParam(TEXT("class_filter"));
		if (Filter.IsEmpty()) Filter = TEXT("all");
		Desc = FString::Printf(TEXT("Find actors matching \"%s\""), *Filter);
	}
	else if (Cmd == TEXT("find_blueprints"))
	{
		FString Filter = GetParam(TEXT("name_filter"));
		if (Filter.IsEmpty()) Filter = TEXT("all");
		Desc = FString::Printf(TEXT("Find blueprints matching \"%s\""), *Filter);
	}
	else if (Cmd == TEXT("find_assets"))
	{
		FString Type = GetParam(TEXT("type"));
		FString Filter = GetParam(TEXT("name_filter"));
		if (!Type.IsEmpty() && !Filter.IsEmpty())
			Desc = FString::Printf(TEXT("Find %s assets matching \"%s\""), *Type, *Filter);
		else if (!Type.IsEmpty())
			Desc = FString::Printf(TEXT("Find %s assets"), *Type);
		else
			Desc = TEXT("Find assets");
	}
	else if (Cmd == TEXT("batch_apply_material"))
	{
		FString Mat = GetParam(TEXT("material_path"));
		if (Mat.IsEmpty()) Mat = GetParam(TEXT("material"));
		if (Mat.IsEmpty()) Mat = TEXT("material");
		Desc = FString::Printf(TEXT("Apply material \"%s\" to found actors"), *Mat);
	}
	else if (Cmd == TEXT("batch_set_variable"))
	{
		FString Var = GetParam(TEXT("variable_name"));
		FString Val = GetParam(TEXT("default_value"));
		if (!Var.IsEmpty())
			Desc = FString::Printf(TEXT("Set %s = %s on found blueprints"), *Var, *Val);
		else
			Desc = TEXT("Set variable defaults on found blueprints");
	}
	else if (Cmd == TEXT("batch_delete_actors"))
	{
		Desc = TEXT("Delete all found actors");
	}
	else if (Cmd == TEXT("batch_set_property"))
	{
		FString Prop = GetParam(TEXT("property"));
		if (Prop.IsEmpty()) Prop = GetParam(TEXT("property_name"));
		if (!Prop.IsEmpty())
			Desc = FString::Printf(TEXT("Set %s on found actors"), *Prop);
		else
			Desc = TEXT("Set properties on found actors");
	}
	else if (Cmd == TEXT("batch_add_component"))
	{
		FString CompType = GetParam(TEXT("component_type"));
		if (!CompType.IsEmpty())
			Desc = FString::Printf(TEXT("Add %s component to found blueprints"), *CompType);
		else
			Desc = TEXT("Add components to found blueprints");
	}
	else if (Cmd == TEXT("batch_replace_material"))
	{
		FString Old = GetParam(TEXT("old_material"));
		FString New = GetParam(TEXT("new_material"));
		Desc = FString::Printf(TEXT("Replace material \"%s\" with \"%s\" everywhere"), *Old, *New);
	}
	else if (Cmd == TEXT("setup_scene_lighting"))
	{
		FString Preset = GetParam(TEXT("preset"));
		if (!Preset.IsEmpty())
			Desc = FString::Printf(TEXT("Set up %s lighting"), *Preset);
		else
			Desc = TEXT("Set up scene lighting");
	}
	else if (Cmd == TEXT("spawn_actor_at"))
	{
		FString Class = GetParam(TEXT("class"));
		if (Class.IsEmpty()) Class = TEXT("actor");
		Desc = FString::Printf(TEXT("Spawn %s in the level"), *Class);
	}
	else if (Cmd == TEXT("create_blueprint") || Cmd == TEXT("generate_dsl"))
	{
		FString Prompt = GetParam(TEXT("prompt"));
		if (!Prompt.IsEmpty())
			Desc = FString::Printf(TEXT("Generate Blueprint from: \"%s\""), *Prompt.Left(60));
		else
			Desc = TEXT("Generate Blueprint");
	}
	else if (Cmd == TEXT("create_behavior_tree"))
	{
		Desc = TEXT("Generate Behavior Tree");
	}
	else if (Cmd == TEXT("create_data_table"))
	{
		Desc = TEXT("Generate Data Table");
	}
	else if (Cmd == TEXT("rename_asset"))
	{
		FString Old = GetParam(TEXT("old_name"));
		FString New = GetParam(TEXT("new_name"));
		Desc = FString::Printf(TEXT("Rename \"%s\" to \"%s\""), *Old, *New);
	}
	else if (Cmd == TEXT("reparent_blueprint"))
	{
		FString Name = GetParam(TEXT("name"));
		FString Parent = GetParam(TEXT("new_parent"));
		Desc = FString::Printf(TEXT("Reparent %s to %s"), *Name, *Parent);
	}
	else if (Cmd == TEXT("modify_blueprint"))
	{
		FString Name = GetParam(TEXT("name"));
		Desc = FString::Printf(TEXT("Modify blueprint %s"), *Name);
	}
	else
	{
		// Fallback: use Op.Description if available, else command name
		if (!Op.Description.IsEmpty())
			Desc = Op.Description;
		else
			Desc = Op.Command;
	}

	return Desc;
}

// ── ClassifyIntent: TCP call to intent server (localhost:13380) ──

static bool TryIntentServerCall(const FString& Prompt, FArcwrightIntentPlan& OutPlan)
{
	ISocketSubsystem* SocketSub = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
	if (!SocketSub)
	{
		UE_LOG(LogArcwright, Warning, TEXT("Arcwright Intent: No socket subsystem"));
		return false;
	}

	TSharedRef<FInternetAddr> Addr = SocketSub->CreateInternetAddr();
	bool bIsValid = false;
	Addr->SetIp(TEXT("127.0.0.1"), bIsValid);
	Addr->SetPort(13380);

	FSocket* Socket = SocketSub->CreateSocket(NAME_Stream, TEXT("ArcwrightIntent"), false);
	if (!Socket)
	{
		UE_LOG(LogArcwright, Warning, TEXT("Arcwright Intent: Failed to create socket"));
		return false;
	}

	Socket->SetNonBlocking(false);
	Socket->SetNoDelay(true);

	if (!Socket->Connect(*Addr))
	{
		UE_LOG(LogArcwright, Log, TEXT("Arcwright Intent: Cannot connect to intent server on 13380"));
		SocketSub->DestroySocket(Socket);
		return false;
	}

	// Send JSON request
	TSharedPtr<FJsonObject> Request = MakeShared<FJsonObject>();
	Request->SetStringField(TEXT("prompt"), Prompt);

	FString RequestStr;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&RequestStr);
	FJsonSerializer::Serialize(Request.ToSharedRef(), Writer);
	RequestStr += TEXT("\n");

	FTCHARToUTF8 UTF8Request(*RequestStr);
	int32 BytesSent = 0;
	Socket->Send((const uint8*)UTF8Request.Get(), UTF8Request.Length(), BytesSent);

	// Read response (wait up to 120 seconds for LLM inference)
	FString ResponseStr;
	uint8 RecvBuf[4096];
	double StartTime = FPlatformTime::Seconds();
	while (FPlatformTime::Seconds() - StartTime < 120.0)
	{
		int32 BytesRead = 0;
		if (Socket->Recv(RecvBuf, sizeof(RecvBuf) - 1, BytesRead))
		{
			if (BytesRead > 0)
			{
				RecvBuf[BytesRead] = 0;
				ResponseStr += UTF8_TO_TCHAR((const char*)RecvBuf);
				if (ResponseStr.Contains(TEXT("\n")))
				{
					break;
				}
			}
			else
			{
				break; // Connection closed
			}
		}
		else
		{
			break;
		}
		FPlatformProcess::Sleep(0.01f);
	}

	SocketSub->DestroySocket(Socket);

	// Parse JSON response
	ResponseStr.TrimStartAndEndInline();
	if (ResponseStr.IsEmpty())
	{
		UE_LOG(LogArcwright, Warning, TEXT("Arcwright Intent: Empty response from intent server"));
		return false;
	}

	TSharedPtr<FJsonObject> ResponseJson;
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(ResponseStr);
	if (!FJsonSerializer::Deserialize(Reader, ResponseJson) || !ResponseJson.IsValid())
	{
		UE_LOG(LogArcwright, Warning, TEXT("Arcwright Intent: Invalid JSON: %s"), *ResponseStr.Left(200));
		return false;
	}

	// Populate plan from JSON
	ResponseJson->TryGetStringField(TEXT("mode"), OutPlan.Mode);
	ResponseJson->TryGetStringField(TEXT("summary"), OutPlan.Summary);
	ResponseJson->TryGetBoolField(TEXT("requires_confirmation"), OutPlan.bRequiresConfirmation);

	const TArray<TSharedPtr<FJsonValue>>* OpsArray;
	if (ResponseJson->TryGetArrayField(TEXT("operations"), OpsArray))
	{
		for (const auto& OpVal : *OpsArray)
		{
			const TSharedPtr<FJsonObject>* OpObj;
			if (OpVal->TryGetObject(OpObj))
			{
				FArcwrightOperation Op;
				double StepD = 0;
				(*OpObj)->TryGetNumberField(TEXT("step"), StepD);
				Op.Step = (int32)StepD;
				(*OpObj)->TryGetStringField(TEXT("command"), Op.Command);
				(*OpObj)->TryGetStringField(TEXT("description"), Op.Description);

				const TSharedPtr<FJsonObject>* ParamsObj;
				if ((*OpObj)->TryGetObjectField(TEXT("params"), ParamsObj))
				{
					Op.Params = MakeShared<FJsonObject>(**ParamsObj);
				}

				double DepD = -1;
				(*OpObj)->TryGetNumberField(TEXT("depends_on"), DepD);
				Op.DependsOn = (int32)DepD;

				OutPlan.Operations.Add(Op);
			}
		}
	}

	UE_LOG(LogArcwright, Log, TEXT("Arcwright Intent: Mode=%s Ops=%d Summary='%s'"),
		*OutPlan.Mode, OutPlan.Operations.Num(), *OutPlan.Summary);
	return true;
}

FArcwrightIntentPlan SArcwrightGeneratorPanel::ClassifyIntent(const FString& Prompt)
{
	FArcwrightIntentPlan Plan;

	AddLogEntry(ELogEntryType::IntentSent, FString::Printf(TEXT("intent_classify: \"%s\""), *Prompt.Left(150)));

	// Try the intent server first
	if (TryIntentServerCall(Prompt, Plan))
	{
		AddLogEntry(ELogEntryType::IntentReceived,
			FString::Printf(TEXT("intent: mode=%s, %d operations, \"%s\""),
				*Plan.Mode, Plan.Operations.Num(), *Plan.Summary.Left(100)));
		return Plan;
	}

	AddLogEntry(ELogEntryType::Info, TEXT("Intent server offline, using CREATE fallback"));

	// Offline fallback: route everything to CREATE with domain detection
	UE_LOG(LogArcwright, Log, TEXT("Arcwright Intent: Using offline CREATE fallback"));

	Plan.Mode = TEXT("CREATE");
	Plan.Summary = TEXT("Offline mode — generating asset from description");
	Plan.bRequiresConfirmation = false;

	FArcwrightOperation CreateOp;
	CreateOp.Step = 1;

	EArcwrightDomain Domain = DetectDomainFromPrompt(Prompt);
	switch (Domain)
	{
	case EArcwrightDomain::BehaviorTree:
		CreateOp.Command = TEXT("create_behavior_tree");
		break;
	case EArcwrightDomain::DataTable:
		CreateOp.Command = TEXT("create_data_table");
		break;
	default:
		CreateOp.Command = TEXT("create_blueprint");
		break;
	}

	CreateOp.Description = TEXT("Generate from description");
	CreateOp.Params = MakeShared<FJsonObject>();
	CreateOp.Params->SetStringField(TEXT("prompt"), Prompt);
	CreateOp.Params->SetStringField(TEXT("domain"),
		Domain == EArcwrightDomain::BehaviorTree ? TEXT("bt") :
		Domain == EArcwrightDomain::DataTable ? TEXT("dt") : TEXT("blueprint"));

	Plan.Operations.Add(CreateOp);

	UE_LOG(LogArcwright, Log, TEXT("Arcwright Intent: OFFLINE fallback → CREATE %s"),
		*ArcwrightColors::GetDomainLabel(Domain));
	return Plan;
}

// ── ExecutePlan: iterate operations, dispatch to command server ──

void SArcwrightGeneratorPanel::ExecutePlan(const FArcwrightIntentPlan& Plan)
{
	FCommandServer* CmdServer = GetCommandServerFromModule();
	if (!CmdServer || !CmdServer->IsRunning())
	{
		AddLogEntry(ELogEntryType::Error, TEXT("Command server not running"));
		UpdateLastAssistantMessage(TEXT("Command server not running. Cannot execute plan."), true);
		return;
	}

	AddLogEntry(ELogEntryType::Info, FString::Printf(TEXT("Executing plan: %s — %s (%d ops)"),
		*Plan.Mode, *Plan.Summary.Left(100), Plan.Operations.Num()));

	FString ModeLabel = GetModeLabel(Plan.Mode);
	StepResults.Empty();

	// Per-operation result tracking for verbose output
	struct FOpLog { FString Command; FString Desc; bool bOK; FString Detail; };
	TArray<FOpLog> OpLogs;
	int32 TotalSucceeded = 0;
	int32 TotalFailed = 0;

	for (int32 i = 0; i < Plan.Operations.Num(); ++i)
	{
		const FArcwrightOperation& Op = Plan.Operations[i];

		// Update progress
		float Progress = (float)(i + 1) / (float)Plan.Operations.Num();
		FString StepMsg = FString::Printf(TEXT("[%s] Step %d/%d: %s"),
			*ModeLabel, i + 1, Plan.Operations.Num(), *Op.Description);

		// For the last message, update inline; for multi-step, add messages
		if (i == 0)
		{
			UpdateLastAssistantMessage(StepMsg, false);
		}
		else
		{
			AddAssistantMessage(StepMsg);
		}
		FSlateApplication::Get().Tick();

		// Handle CREATE operations: route to DSL generation pipeline
		if (Op.Command == TEXT("create_blueprint") || Op.Command == TEXT("create_behavior_tree") || Op.Command == TEXT("create_data_table"))
		{
			FString Prompt;
			if (Op.Params.IsValid())
			{
				Op.Params->TryGetStringField(TEXT("prompt"), Prompt);
			}
			if (Prompt.IsEmpty()) Prompt = Plan.Summary;

			if (Op.Command == TEXT("create_blueprint"))
			{
				DoGenerateBlueprint(Prompt);
			}
			else if (Op.Command == TEXT("create_behavior_tree"))
			{
				DoGenerateBehaviorTree(Prompt);
			}
			else
			{
				DoGenerateDataTable(Prompt);
			}
			continue;
		}

		// All other commands: resolve step dependencies and dispatch to command server
		{
			// Log the outgoing command
			FString ParamSummary;
			if (Op.Params.IsValid())
			{
				TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&ParamSummary);
				FJsonSerializer::Serialize(Op.Params.ToSharedRef(), Writer);
			}
			AddLogEntry(ELogEntryType::TCPSent, FString::Printf(TEXT("%s: %s"), *Op.Command, *ParamSummary.Left(150)));
		}
		TSharedPtr<FJsonObject> Params = Op.Params.IsValid()
			? MakeShared<FJsonObject>(*Op.Params)
			: MakeShared<FJsonObject>();

		// ── Post-process: deterministic injection of find results into batch commands ──
		// The LLM says "find X, then batch Y" — we handle the plumbing.
		// Any batch_ command gets results injected from the most recent find_ result.
		if (Op.Command.StartsWith(TEXT("batch_")) && i > 0)
		{
			// Find the most recent find_actors / find_blueprints / find_assets result
			TArray<FString> ActorLabels;
			TArray<FString> BlueprintNames;

			// Scan all previous step results (prefer explicit depends_on, fall back to scanning)
			for (int32 PrevStep = i; PrevStep >= 1; --PrevStep)
			{
				int32 StepNum = Plan.Operations[PrevStep - 1].Step;
				if (!StepResults.Contains(StepNum)) continue;
				TSharedPtr<FJsonObject> PrevResult = StepResults[StepNum];
				if (!PrevResult.IsValid()) continue;

				const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
				if (PrevResult->TryGetArrayField(TEXT("actors"), Arr) && Arr && Arr->Num() > 0)
				{
					for (const auto& V : *Arr)
					{
						const TSharedPtr<FJsonObject>* Obj;
						if (V->TryGetObject(Obj))
						{
							FString L; (*Obj)->TryGetStringField(TEXT("label"), L);
							if (!L.IsEmpty()) ActorLabels.Add(L);
						}
					}
					break; // Use the closest find result
				}
				if (PrevResult->TryGetArrayField(TEXT("blueprints"), Arr) && Arr && Arr->Num() > 0)
				{
					for (const auto& V : *Arr)
					{
						const TSharedPtr<FJsonObject>* Obj;
						if (V->TryGetObject(Obj))
						{
							FString N; (*Obj)->TryGetStringField(TEXT("name"), N);
							if (!N.IsEmpty()) BlueprintNames.Add(N);
						}
					}
					break;
				}
			}

			// Helper: extract a string param from flat params or first item of operations[]
			auto ExtractParam = [&Params](const FString& Key) -> FString
			{
				FString Val;
				Params->TryGetStringField(Key, Val);
				if (Val.IsEmpty())
				{
					const TArray<TSharedPtr<FJsonValue>>* Ops = nullptr;
					if (Params->TryGetArrayField(TEXT("operations"), Ops) && Ops && Ops->Num() > 0)
					{
						const TSharedPtr<FJsonObject>* First;
						if ((*Ops)[0]->TryGetObject(First)) (*First)->TryGetStringField(Key, Val);
					}
				}
				return Val;
			};

			// RULE 1: batch_apply_material — inject actor labels + material_path
			if (Op.Command == TEXT("batch_apply_material") && ActorLabels.Num() > 0)
			{
				FString MatPath = ExtractParam(TEXT("material_path"));
				if (MatPath.IsEmpty()) MatPath = ExtractParam(TEXT("material_name"));
				if (MatPath.IsEmpty()) MatPath = ExtractParam(TEXT("material"));

				if (!MatPath.IsEmpty())
				{
					TArray<TSharedPtr<FJsonValue>> NewOps;
					for (const FString& Label : ActorLabels)
					{
						TSharedPtr<FJsonObject> O = MakeShared<FJsonObject>();
						O->SetStringField(TEXT("actor_label"), Label);
						O->SetStringField(TEXT("material_path"), MatPath);
						NewOps.Add(MakeShareable(new FJsonValueObject(O)));
					}
					Params->SetArrayField(TEXT("operations"), NewOps);
					Params->RemoveField(TEXT("material_path"));
					Params->RemoveField(TEXT("material_name"));
					AddLogEntry(ELogEntryType::Info,
						FString::Printf(TEXT("[post-process] Injected %d actors into batch_apply_material (material=%s)"),
							NewOps.Num(), *MatPath));
				}
			}
			// RULE 2: batch_delete_actors — inject actor labels
			else if (Op.Command == TEXT("batch_delete_actors") && ActorLabels.Num() > 0)
			{
				TArray<TSharedPtr<FJsonValue>> Labels;
				for (const FString& L : ActorLabels)
					Labels.Add(MakeShareable(new FJsonValueString(L)));
				Params->SetArrayField(TEXT("labels"), Labels);
				AddLogEntry(ELogEntryType::Info,
					FString::Printf(TEXT("[post-process] Injected %d actors into batch_delete_actors"), ActorLabels.Num()));
			}
			// RULE 3: batch_set_property — inject actor labels into operations
			else if (Op.Command == TEXT("batch_set_property") && ActorLabels.Num() > 0)
			{
				// Keep existing property/value, expand to all actors
				FString Prop; Params->TryGetStringField(TEXT("property"), Prop);
				const TSharedPtr<FJsonValue>* ValField = nullptr;
				TSharedPtr<FJsonValue> PropVal;
				if (Params->Values.Contains(TEXT("value")))
					PropVal = Params->Values[TEXT("value")];

				const TArray<TSharedPtr<FJsonValue>>* ExOps = nullptr;
				if (!Prop.IsEmpty() || (Params->TryGetArrayField(TEXT("operations"), ExOps) && ExOps && ExOps->Num() > 0))
				{
					if (!Prop.IsEmpty() && PropVal.IsValid())
					{
						TArray<TSharedPtr<FJsonValue>> NewOps;
						for (const FString& Label : ActorLabels)
						{
							TSharedPtr<FJsonObject> O = MakeShared<FJsonObject>();
							O->SetStringField(TEXT("actor_label"), Label);
							O->SetStringField(TEXT("property"), Prop);
							O->SetField(TEXT("value"), PropVal);
							NewOps.Add(MakeShareable(new FJsonValueObject(O)));
						}
						Params->SetArrayField(TEXT("operations"), NewOps);
						Params->RemoveField(TEXT("property"));
						Params->RemoveField(TEXT("value"));
						AddLogEntry(ELogEntryType::Info,
							FString::Printf(TEXT("[post-process] Injected %d actors into batch_set_property"), ActorLabels.Num()));
					}
				}
			}
			// RULE 4: batch_set_variable — inject blueprint names
			else if (Op.Command == TEXT("batch_set_variable") && BlueprintNames.Num() > 0)
			{
				FString VarName; Params->TryGetStringField(TEXT("variable_name"), VarName);
				FString VarVal; Params->TryGetStringField(TEXT("default_value"), VarVal);
				if (VarVal.IsEmpty()) Params->TryGetStringField(TEXT("value"), VarVal);

				if (!VarName.IsEmpty())
				{
					TArray<TSharedPtr<FJsonValue>> NewOps;
					for (const FString& BPName : BlueprintNames)
					{
						TSharedPtr<FJsonObject> O = MakeShared<FJsonObject>();
						O->SetStringField(TEXT("blueprint"), BPName);
						O->SetStringField(TEXT("variable_name"), VarName);
						O->SetStringField(TEXT("default_value"), VarVal);
						NewOps.Add(MakeShareable(new FJsonValueObject(O)));
					}
					Params->SetArrayField(TEXT("operations"), NewOps);
					Params->RemoveField(TEXT("variable_name"));
					Params->RemoveField(TEXT("default_value"));
					Params->RemoveField(TEXT("value"));
					AddLogEntry(ELogEntryType::Info,
						FString::Printf(TEXT("[post-process] Injected %d blueprints into batch_set_variable (var=%s)"),
							BlueprintNames.Num(), *VarName));
				}
			}
			// RULE 5: batch_add_component — inject blueprint names
			else if (Op.Command == TEXT("batch_add_component") && BlueprintNames.Num() > 0)
			{
				FString CompType; Params->TryGetStringField(TEXT("component_type"), CompType);
				FString CompName; Params->TryGetStringField(TEXT("component_name"), CompName);

				if (!CompType.IsEmpty())
				{
					TArray<TSharedPtr<FJsonValue>> NewOps;
					for (const FString& BPName : BlueprintNames)
					{
						TSharedPtr<FJsonObject> O = MakeShared<FJsonObject>();
						O->SetStringField(TEXT("blueprint"), BPName);
						O->SetStringField(TEXT("component_type"), CompType);
						if (!CompName.IsEmpty()) O->SetStringField(TEXT("component_name"), CompName);
						const TSharedPtr<FJsonObject>* Props;
						if (Params->TryGetObjectField(TEXT("properties"), Props))
							O->SetObjectField(TEXT("properties"), MakeShared<FJsonObject>(**Props));
						NewOps.Add(MakeShareable(new FJsonValueObject(O)));
					}
					Params->SetArrayField(TEXT("operations"), NewOps);
					Params->RemoveField(TEXT("component_type"));
					Params->RemoveField(TEXT("component_name"));
					Params->RemoveField(TEXT("properties"));
					AddLogEntry(ELogEntryType::Info,
						FString::Printf(TEXT("[post-process] Injected %d blueprints into batch_add_component (type=%s)"),
							BlueprintNames.Num(), *CompType));
				}
			}
		}

		FCommandResult Result = CmdServer->DispatchCommand(Op.Command, Params);

		// Log the response
		if (Result.bSuccess)
		{
			FString DataSummary;
			if (Result.Data.IsValid())
			{
				TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&DataSummary);
				FJsonSerializer::Serialize(Result.Data.ToSharedRef(), Writer);
			}
			AddLogEntry(ELogEntryType::TCPReceived, FString::Printf(TEXT("%s: OK %s"), *Op.Command, *DataSummary.Left(150)));
		}
		else
		{
			AddLogEntry(ELogEntryType::Error, FString::Printf(TEXT("%s: %s"), *Op.Command, *Result.ErrorMessage.Left(150)));
		}

		// Store result for dependent steps
		if (Result.bSuccess && Result.Data.IsValid())
		{
			StepResults.Add(Op.Step, Result.Data);
		}

		// Track per-operation result for verbose output
		if (Result.bSuccess)
		{
			TotalSucceeded++;
			FString Detail;

			// Extract useful info from result data
			if (Result.Data.IsValid())
			{
				// Batch commands: report succeeded/failed counts
				int32 BatchSucc = 0, BatchFail = 0;
				if (Result.Data->TryGetNumberField(TEXT("succeeded"), BatchSucc) &&
					Result.Data->TryGetNumberField(TEXT("failed"), BatchFail))
				{
					Detail = FString::Printf(TEXT("%d succeeded, %d failed"), BatchSucc, BatchFail);

					// Show individual errors if any
					const TArray<TSharedPtr<FJsonValue>>* Errors = nullptr;
					if (Result.Data->TryGetArrayField(TEXT("errors"), Errors) && Errors)
					{
						for (const auto& Err : *Errors)
						{
							FString ErrStr;
							if (Err->TryGetString(ErrStr))
								Detail += TEXT("\n  ! ") + ErrStr.Left(120);
						}
					}
				}
				// Query commands: report item counts
				else
				{
					const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
					if (Result.Data->TryGetArrayField(TEXT("actors"), Arr) && Arr)
						Detail = FString::Printf(TEXT("Found %d actors"), Arr->Num());
					else if (Result.Data->TryGetArrayField(TEXT("blueprints"), Arr) && Arr)
						Detail = FString::Printf(TEXT("Found %d blueprints"), Arr->Num());
					else if (Result.Data->TryGetArrayField(TEXT("assets"), Arr) && Arr)
						Detail = FString::Printf(TEXT("Found %d assets"), Arr->Num());
					else if (Result.Data->HasField(TEXT("name")))
					{
						FString N; Result.Data->TryGetStringField(TEXT("name"), N);
						Detail = N;
					}
					// Batch delete: report deleted count
					int32 DelCount = 0;
					if (Result.Data->TryGetNumberField(TEXT("deleted"), DelCount))
						Detail = FString::Printf(TEXT("%d deleted"), DelCount);
					// Replacements
					int32 RepCount = 0;
					if (Result.Data->TryGetNumberField(TEXT("replacements"), RepCount))
						Detail = FString::Printf(TEXT("%d replacements"), RepCount);
				}
			}
			OpLogs.Add({Op.Command, Op.Description, true, Detail});
		}
		else
		{
			TotalFailed++;
			OpLogs.Add({Op.Command, Op.Description, false, Result.ErrorMessage});

			// Build verbose error output and stop
			FString ErrDetails;
			for (const FOpLog& L : OpLogs)
			{
				FString Prefix = L.bOK ? TEXT("  \u2713 ") : TEXT("  \u2717 ");
				ErrDetails += Prefix + L.Command;
				if (!L.Detail.IsEmpty()) ErrDetails += TEXT(" — ") + L.Detail;
				ErrDetails += TEXT("\n");
			}
			ErrDetails += TEXT("---\n");
			ErrDetails += FString::Printf(TEXT("%d of %d operations completed before failure"),
				TotalSucceeded, Plan.Operations.Num());

			FString ErrTitle = FString::Printf(TEXT("[%s] %s"), *ModeLabel, *Plan.Summary);

			// Update message with verbose error details
			for (int32 mi = ChatMessages.Num() - 1; mi >= 0; --mi)
			{
				if (!ChatMessages[mi]->bIsUser)
				{
					ChatMessages[mi]->Text = ErrTitle;
					ChatMessages[mi]->bIsError = true;
					ChatMessages[mi]->ResultDetails = ErrDetails;
					ChatMessages[mi]->SucceededCount = TotalSucceeded;
					ChatMessages[mi]->FailedCount = TotalFailed;
					break;
				}
			}
			RefreshChatList();
			UE_LOG(LogArcwright, Warning, TEXT("Arcwright Plan: Step %d (%s) failed: %s"),
				Op.Step, *Op.Command, *Result.ErrorMessage);
			return;
		}
	}

	// ══════════════════════════════════════════════════════════════
	// Build verbose final result (all operations succeeded)
	// ══════════════════════════════════════════════════════════════

	FString FinalTitle;
	FString FinalDetails;

	if (Plan.Mode == TEXT("QUERY"))
	{
		// ── QUERY: show found items with details ──
		FinalTitle = FString::Printf(TEXT("[QUERY] %s"), *Plan.Summary);

		// Find the last query result to display items
		for (int32 ri = Plan.Operations.Num() - 1; ri >= 0; --ri)
		{
			int32 StepNum = Plan.Operations[ri].Step;
			if (!StepResults.Contains(StepNum)) continue;
			TSharedPtr<FJsonObject> QResult = StepResults[StepNum];
			if (!QResult.IsValid()) continue;

			const TArray<TSharedPtr<FJsonValue>>* Items = nullptr;
			FString ArrayKey, TypeLabel;

			if (QResult->TryGetArrayField(TEXT("actors"), Items))
			{
				ArrayKey = TEXT("label"); TypeLabel = TEXT("actors");
			}
			else if (QResult->TryGetArrayField(TEXT("blueprints"), Items))
			{
				ArrayKey = TEXT("name"); TypeLabel = TEXT("blueprints");
			}
			else if (QResult->TryGetArrayField(TEXT("assets"), Items))
			{
				ArrayKey = TEXT("name"); TypeLabel = TEXT("assets");
			}

			if (Items && Items->Num() > 0)
			{
				int32 Count = Items->Num();
				FinalTitle = FString::Printf(TEXT("[QUERY] Found %d %s"), Count, *TypeLabel);
				FinalDetails += TEXT("---\n");

				int32 ShowMax = FMath::Min(Count, 25);
				for (int32 j = 0; j < ShowMax; ++j)
				{
					const TSharedPtr<FJsonObject>* ItemObj;
					if ((*Items)[j]->TryGetObject(ItemObj))
					{
						FString Name; (*ItemObj)->TryGetStringField(ArrayKey, Name);
						FString ClassStr; (*ItemObj)->TryGetStringField(TEXT("class"), ClassStr);
						FString LocStr;
						const TSharedPtr<FJsonObject>* LocObj;
						if ((*ItemObj)->TryGetObjectField(TEXT("location"), LocObj))
						{
							double X = 0, Y = 0, Z = 0;
							(*LocObj)->TryGetNumberField(TEXT("x"), X);
							(*LocObj)->TryGetNumberField(TEXT("y"), Y);
							(*LocObj)->TryGetNumberField(TEXT("z"), Z);
							LocStr = FString::Printf(TEXT("  @ (%.0f, %.0f, %.0f)"), X, Y, Z);
						}
						FString ClassSuffix = ClassStr.IsEmpty() ? TEXT("") : FString::Printf(TEXT("  (%s)"), *ClassStr);
						FinalDetails += FString::Printf(TEXT("  %d. %s%s%s\n"), j + 1, *Name, *ClassSuffix, *LocStr);
					}
				}
				if (Count > ShowMax)
				{
					FinalDetails += FString::Printf(TEXT("  ... and %d more\n"), Count - ShowMax);
				}
			}
			else if (Items && Items->Num() == 0)
			{
				FinalTitle = TEXT("[QUERY] No results found");
			}
			break;
		}
	}
	else if (Plan.Mode == TEXT("MODIFY"))
	{
		// ── MODIFY: show per-step results ──
		FinalTitle = FString::Printf(TEXT("[MODIFY] %s"), *Plan.Summary);
		FinalDetails += TEXT("---\n");

		for (int32 li = 0; li < OpLogs.Num(); ++li)
		{
			const FOpLog& L = OpLogs[li];
			FString Prefix = L.bOK ? TEXT("  \u2713 ") : TEXT("  \u2717 ");
			FinalDetails += FString::Printf(TEXT("%sStep %d: %s"), *Prefix, li + 1, *L.Command);
			if (!L.Detail.IsEmpty()) FinalDetails += TEXT(" — ") + L.Detail;
			FinalDetails += TEXT("\n");
		}

		FinalDetails += TEXT("---\n");
		FinalDetails += FString::Printf(TEXT("%d operation(s) completed successfully"), TotalSucceeded);
	}
	else if (Plan.Mode == TEXT("CREATE"))
	{
		// ── CREATE: asset creation details shown via AssetCard ──
		FinalTitle = FString::Printf(TEXT("[CREATE] %s"), *Plan.Summary);
		if (OpLogs.Num() > 0 && !OpLogs.Last().Detail.IsEmpty())
		{
			FinalDetails += TEXT("---\n");
			FinalDetails += TEXT("  \u2713 ") + OpLogs.Last().Detail + TEXT("\n");
		}
	}
	else if (Plan.Mode == TEXT("MULTI"))
	{
		// ── MULTI: numbered step-by-step results ──
		FinalTitle = FString::Printf(TEXT("[MULTI] %s"), *Plan.Summary);
		FinalDetails += TEXT("---\n");

		for (int32 li = 0; li < OpLogs.Num(); ++li)
		{
			const FOpLog& L = OpLogs[li];
			FString Prefix = L.bOK ? TEXT("  \u2713 ") : TEXT("  \u2717 ");
			FinalDetails += FString::Printf(TEXT("%sStep %d: %s"), *Prefix, li + 1, *L.Command);
			if (!L.Desc.IsEmpty()) FinalDetails += TEXT(" — ") + L.Desc;
			if (!L.Detail.IsEmpty()) FinalDetails += TEXT(" (") + L.Detail + TEXT(")");
			FinalDetails += TEXT("\n");
		}

		FinalDetails += TEXT("---\n");
		FinalDetails += FString::Printf(TEXT("%d operations completed, %d failed"), TotalSucceeded, TotalFailed);
	}
	else if (Plan.Mode == TEXT("CLARIFY"))
	{
		FinalTitle = FString::Printf(TEXT("[CLARIFY] %s"), *Plan.Summary);
	}
	else
	{
		FinalTitle = FString::Printf(TEXT("[%s] %s — %d operation(s) completed"),
			*ModeLabel, *Plan.Summary, Plan.Operations.Num());
	}

	// Update the last assistant message with verbose result
	for (int32 mi = ChatMessages.Num() - 1; mi >= 0; --mi)
	{
		if (!ChatMessages[mi]->bIsUser)
		{
			ChatMessages[mi]->Text = FinalTitle;
			ChatMessages[mi]->bIsError = false;
			ChatMessages[mi]->bIsThinking = false;
			ChatMessages[mi]->ResultDetails = FinalDetails;
			ChatMessages[mi]->SucceededCount = TotalSucceeded;
			ChatMessages[mi]->FailedCount = TotalFailed;
			break;
		}
	}
	RefreshChatList();
	UE_LOG(LogArcwright, Log, TEXT("Arcwright Plan: %s — %d ops completed"), *Plan.Mode, Plan.Operations.Num());
}

// ── DisplayPlanPreview: show plan with confirm/cancel buttons ──

void SArcwrightGeneratorPanel::DisplayPlanPreview(const FArcwrightIntentPlan& Plan)
{
	PendingPlan = Plan;
	bAwaitingConfirmation = true;

	FString ModeLabel = GetModeLabel(Plan.Mode);

	// Build clean, readable confirmation preview
	FString PreviewMsg;
	PreviewMsg += FString::Printf(TEXT("%s: %s\n"), *ModeLabel, *Plan.Summary);
	PreviewMsg += TEXT("\n");
	PreviewMsg += FString::Printf(TEXT("Plan (%d step%s):\n"),
		Plan.Operations.Num(),
		Plan.Operations.Num() == 1 ? TEXT("") : TEXT("s"));

	for (const FArcwrightOperation& Op : Plan.Operations)
	{
		FString StepDesc = DescribeOperation(Op);
		PreviewMsg += FString::Printf(TEXT("\n  Step %d: %s"), Op.Step, *StepDesc);
		if (Op.DependsOn > 0)
		{
			PreviewMsg += FString::Printf(TEXT("  (uses results from step %d)"), Op.DependsOn);
		}
	}

	// Update the thinking message with the plan preview
	// Use ResultDetails field so it renders in the selectable text widget
	if (ChatMessages.Num() > 0)
	{
		auto& LastMsg = ChatMessages.Last();
		if (LastMsg.IsValid() && !LastMsg->bIsUser)
		{
			LastMsg->Text = TEXT("");
			LastMsg->ResultDetails = PreviewMsg;
			LastMsg->bIsThinking = false;
			LastMsg->IntentMode = Plan.Mode;
			LastMsg->Domain = DetectDomainFromPrompt(Plan.Summary);
		}
	}

	RefreshChatList();

	// Add confirm/cancel buttons directly to the chat list
	if (ChatMessageList.IsValid())
	{
		ChatMessageList->AddSlot()
		.AutoHeight()
		.Padding(FMargin(16.0f, 8.0f))
		[
			SNew(SHorizontalBox)

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(0.0f, 0.0f, 8.0f, 0.0f)
			[
				SNew(SButton)
				.ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder"))
				.OnClicked(this, &SArcwrightGeneratorPanel::OnConfirmPlanClicked)
				[
					SNew(SBorder)
					.BorderBackgroundColor(SuccessGreen)
					.Padding(FMargin(16.0f, 6.0f))
					[
						SNew(STextBlock)
						.Text(LOCTEXT("ConfirmPlan", "Confirm"))
						.Font(FCoreStyle::GetDefaultFontStyle("Bold", 10))
						.ColorAndOpacity(FLinearColor::White)
					]
				]
			]

			+ SHorizontalBox::Slot()
			.AutoWidth()
			[
				SNew(SButton)
				.ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder"))
				.OnClicked(this, &SArcwrightGeneratorPanel::OnCancelPlanClicked)
				[
					SNew(SBorder)
					.BorderBackgroundColor(ErrorRed)
					.Padding(FMargin(16.0f, 6.0f))
					[
						SNew(STextBlock)
						.Text(LOCTEXT("CancelPlan", "Cancel"))
						.Font(FCoreStyle::GetDefaultFontStyle("Bold", 10))
						.ColorAndOpacity(FLinearColor::White)
					]
				]
			]
		];
	}

	if (ChatScrollBox.IsValid())
	{
		ChatScrollBox->ScrollToEnd();
	}
}

FReply SArcwrightGeneratorPanel::OnConfirmPlanClicked()
{
	if (!bAwaitingConfirmation) return FReply::Handled();
	bAwaitingConfirmation = false;

	AddThinkingMessage();
	FSlateApplication::Get().Tick();

	bIsGenerating = true;
	ExecutePlan(PendingPlan);
	bIsGenerating = false;

	return FReply::Handled();
}

FReply SArcwrightGeneratorPanel::OnCancelPlanClicked()
{
	bAwaitingConfirmation = false;
	AddAssistantMessage(TEXT("Plan cancelled."));
	return FReply::Handled();
}

// ============================================================
// Create tab (DSL direct mode — restyled)
// ============================================================

TSharedRef<SWidget> SArcwrightGeneratorPanel::BuildCreateTab()
{
	return SNew(SBorder)
		.BorderBackgroundColor(DeepNavy)
		.Padding(16.0f)
		[
			SNew(SVerticalBox)

			// Domain selector row
			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 12.0f)
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.VAlign(VAlign_Center)
				.Padding(0.0f, 0.0f, 12.0f, 0.0f)
				[
					SNew(STextBlock)
					.Text(LOCTEXT("CreateDomainLabel", "Domain"))
					.Font(FCoreStyle::GetDefaultFontStyle("Bold", 10))
					.ColorAndOpacity(TextSecondary)
				]

				// Blueprint radio
				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 16.0f, 0.0f)
				[
					SNew(SButton)
					.ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder"))
					.OnClicked_Lambda([this]() { OnDomainSelected(EArcwrightDomain::Blueprint); return FReply::Handled(); })
					[
						SNew(SHorizontalBox)

						+ SHorizontalBox::Slot()
						.AutoWidth()
						.Padding(0.0f, 0.0f, 4.0f, 0.0f)
						[
							SNew(STextBlock)
							.Text_Lambda([this]() {
								return FText::FromString(CreateDomain == EArcwrightDomain::Blueprint ? TEXT("\u25C9") : TEXT("\u25CB"));
							})
							.Font(FCoreStyle::GetDefaultFontStyle("Regular", 12))
							.ColorAndOpacity(BrandBlue)
						]

						+ SHorizontalBox::Slot()
						.AutoWidth()
						[
							SNew(STextBlock)
							.Text(LOCTEXT("DomainBP", "Blueprint"))
							.Font(FCoreStyle::GetDefaultFontStyle("Regular", 10))
							.ColorAndOpacity(TextPrimary)
						]
					]
				]

				// BT radio (purple accent)
				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 16.0f, 0.0f)
				[
					SNew(SButton)
					.ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder"))
					.OnClicked_Lambda([this]() { OnDomainSelected(EArcwrightDomain::BehaviorTree); return FReply::Handled(); })
					[
						SNew(SHorizontalBox)

						+ SHorizontalBox::Slot()
						.AutoWidth()
						.Padding(0.0f, 0.0f, 4.0f, 0.0f)
						[
							SNew(STextBlock)
							.Text_Lambda([this]() {
								return FText::FromString(CreateDomain == EArcwrightDomain::BehaviorTree ? TEXT("\u25C9") : TEXT("\u25CB"));
							})
							.Font(FCoreStyle::GetDefaultFontStyle("Regular", 12))
							.ColorAndOpacity(Purple)
						]

						+ SHorizontalBox::Slot()
						.AutoWidth()
						[
							SNew(STextBlock)
							.Text(LOCTEXT("DomainBT", "BT"))
							.Font(FCoreStyle::GetDefaultFontStyle("Regular", 10))
							.ColorAndOpacity(TextPrimary)
						]
					]
				]

				// DT radio (pink accent)
				+ SHorizontalBox::Slot()
				.AutoWidth()
				[
					SNew(SButton)
					.ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder"))
					.OnClicked_Lambda([this]() { OnDomainSelected(EArcwrightDomain::DataTable); return FReply::Handled(); })
					[
						SNew(SHorizontalBox)

						+ SHorizontalBox::Slot()
						.AutoWidth()
						.Padding(0.0f, 0.0f, 4.0f, 0.0f)
						[
							SNew(STextBlock)
							.Text_Lambda([this]() {
								return FText::FromString(CreateDomain == EArcwrightDomain::DataTable ? TEXT("\u25C9") : TEXT("\u25CB"));
							})
							.Font(FCoreStyle::GetDefaultFontStyle("Regular", 12))
							.ColorAndOpacity(Pink)
						]

						+ SHorizontalBox::Slot()
						.AutoWidth()
						[
							SNew(STextBlock)
							.Text(LOCTEXT("DomainDT", "DT"))
							.Font(FCoreStyle::GetDefaultFontStyle("Regular", 10))
							.ColorAndOpacity(TextPrimary)
						]
					]
				]
			]

			// Separator
			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 12.0f)
			[
				SNew(SBox)
				.HeightOverride(1.0f)
				[
					SNew(SBorder)
					.BorderBackgroundColor(GridLines)
				]
			]

			// DSL input area
			+ SVerticalBox::Slot()
			.FillHeight(1.0f)
			.Padding(0.0f, 0.0f, 0.0f, 8.0f)
			[
				SNew(SBorder)
				.BorderBackgroundColor(BorderLine)
				.Padding(1.0f) // 1px border outline
				[
					SNew(SBorder)
					.BorderBackgroundColor(CardBg)
					.Padding(4.0f)
					[
						SAssignNew(CreateInputBox, SMultiLineEditableTextBox)
						.HintText(LOCTEXT("CreateInputHint",
							"Paste DSL or IR JSON here...\n\n"
							"Blueprint IR: {\"metadata\": {\"name\": \"BP_Example\", ...}, ...}\n"
							"BT IR: {\"name\": \"BT_Example\", \"root\": {...}, ...}\n"
							"DT IR: {\"table_name\": \"DT_Example\", \"columns\": [...], ...}"))
						.Font(FCoreStyle::GetDefaultFontStyle("Mono", 10))
					]
				]
			]

			// Button row
			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 8.0f, 0.0f)
				[
					SNew(SButton)
					.ButtonColorAndOpacity(BrandBlue)
					.ForegroundColor(FLinearColor::Black)
					.ContentPadding(FMargin(24.0f, 8.0f))
					.OnClicked(this, &SArcwrightGeneratorPanel::OnCreateGenerateClicked)
					[
						SNew(STextBlock)
						.Text(LOCTEXT("CreateGenBtn", "Generate"))
						.Font(FCoreStyle::GetDefaultFontStyle("Bold", 11))
						.ColorAndOpacity(FSlateColor(FLinearColor(0.02f, 0.05f, 0.12f, 1.0f)))
					]
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				[
					SNew(SButton)
					.ButtonColorAndOpacity(CardBg)
					.ContentPadding(FMargin(16.0f, 8.0f))
					.OnClicked(this, &SArcwrightGeneratorPanel::OnCreateClearClicked)
					[
						SNew(STextBlock)
						.Text(LOCTEXT("CreateClrBtn", "Clear"))
						.Font(FCoreStyle::GetDefaultFontStyle("Regular", 10))
						.ColorAndOpacity(TextSecondary)
					]
				]

				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				[
					SNew(SSpacer)
				]
			]

			// Status display
			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 12.0f, 0.0f, 0.0f)
			[
				SNew(SBorder)
				.BorderBackgroundColor(CardBg)
				.Padding(FMargin(12.0f, 8.0f))
				[
					SAssignNew(CreateStatusText, STextBlock)
					.Text(LOCTEXT("CreateStatusReady", "Ready. Paste DSL or IR JSON above, select domain, and click Generate."))
					.Font(FCoreStyle::GetDefaultFontStyle("Regular", 10))
					.ColorAndOpacity(TextSecondary)
					.AutoWrapText(true)
				]
			]
		];
}

void SArcwrightGeneratorPanel::OnDomainSelected(EArcwrightDomain NewDomain)
{
	CreateDomain = NewDomain;
}

FReply SArcwrightGeneratorPanel::OnCreateGenerateClicked()
{
	if (!CreateInputBox.IsValid())
	{
		return FReply::Handled();
	}

	FString InputText = CreateInputBox->GetText().ToString().TrimStartAndEnd();
	if (InputText.IsEmpty())
	{
		SetCreateStatus(TEXT("No input provided. Paste DSL or IR JSON above."), ErrorRed);
		return FReply::Handled();
	}

	FString DomainStr;
	switch (CreateDomain)
	{
	case EArcwrightDomain::Blueprint:     DomainStr = TEXT("Blueprint"); break;
	case EArcwrightDomain::BehaviorTree:  DomainStr = TEXT("Behavior Tree"); break;
	case EArcwrightDomain::DataTable:     DomainStr = TEXT("Data Table"); break;
	}
	SetCreateStatus(FString::Printf(TEXT("Creating %s..."), *DomainStr), WarningAmber);
	FSlateApplication::Get().Tick();

	switch (CreateDomain)
	{
	case EArcwrightDomain::Blueprint:     GenerateBlueprintDSL(InputText); break;
	case EArcwrightDomain::BehaviorTree:  GenerateBehaviorTreeDSL(InputText); break;
	case EArcwrightDomain::DataTable:     GenerateDataTableDSL(InputText); break;
	}

	return FReply::Handled();
}

FReply SArcwrightGeneratorPanel::OnCreateClearClicked()
{
	if (CreateInputBox.IsValid())
	{
		CreateInputBox->SetText(FText::GetEmpty());
	}
	SetCreateStatus(TEXT("Ready. Paste DSL or IR JSON above, select domain, and click Generate."), TextSecondary);
	return FReply::Handled();
}

// ============================================================
// Create tab — DSL Direct generation logic (same as before)
// ============================================================

void SArcwrightGeneratorPanel::GenerateBlueprintDSL(const FString& DSLText)
{
	FDSLBlueprint DSL;
	if (!FDSLImporter::ParseIRFromString(DSLText, DSL))
	{
		SetCreateStatus(TEXT("Failed to parse Blueprint IR JSON. Check the format."), ErrorRed);
		return;
	}

	FString PackagePath = TEXT("/Game/BlueprintLLM/Generated");
	FString FullPath = PackagePath / DSL.Name;

	UObject* ExistingObj = StaticFindObject(UObject::StaticClass(), nullptr, *FullPath);
	if (ExistingObj)
	{
		TArray<UObject*> ObjsToDelete;
		ObjsToDelete.Add(ExistingObj);
		ObjectTools::ForceDeleteObjects(ObjsToDelete, false);
	}

	UBlueprint* NewBP = FBlueprintBuilder::CreateBlueprint(DSL, PackagePath);
	if (!NewBP)
	{
		SetCreateStatus(FString::Printf(TEXT("Failed to build Blueprint: %s"), *DSL.Name), ErrorRed);
		return;
	}

	int32 NodeCount = 0;
	UEdGraph* EventGraph = FBlueprintEditorUtils::FindEventGraph(NewBP);
	if (EventGraph) NodeCount = EventGraph->Nodes.Num();

	SetCreateStatus(FString::Printf(TEXT("\u2713 %s created — %d nodes"), *DSL.Name, NodeCount), SuccessGreen);

	if (GEditor)
	{
		UAssetEditorSubsystem* Sub = GEditor->GetEditorSubsystem<UAssetEditorSubsystem>();
		if (Sub) Sub->OpenEditorForAsset(NewBP);
	}
}

void SArcwrightGeneratorPanel::GenerateBehaviorTreeDSL(const FString& DSLText)
{
	TSharedPtr<FJsonObject> IRJson;
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(DSLText);
	if (!FJsonSerializer::Deserialize(Reader, IRJson) || !IRJson.IsValid())
	{
		SetCreateStatus(TEXT("Failed to parse Behavior Tree IR JSON."), ErrorRed);
		return;
	}

	FString PackagePath = TEXT("/Game/BlueprintLLM/BehaviorTrees");
	FBehaviorTreeBuilder::FBTBuildResult Result = FBehaviorTreeBuilder::CreateFromIR(IRJson, PackagePath);

	if (!Result.bSuccess)
	{
		SetCreateStatus(FString::Printf(TEXT("BT error: %s"), *Result.ErrorMessage), ErrorRed);
		return;
	}

	SetCreateStatus(FString::Printf(TEXT("\u2713 BT created — %d composites, %d tasks, %d decorators"),
		Result.CompositeCount, Result.TaskCount, Result.DecoratorCount), SuccessGreen);

	if (GEditor)
	{
		UObject* Asset = StaticFindObject(UObject::StaticClass(), nullptr, *Result.TreeAssetPath);
		if (Asset)
		{
			GEditor->GetEditorSubsystem<UAssetEditorSubsystem>()->OpenEditorForAsset(Asset);
		}
	}
}

void SArcwrightGeneratorPanel::GenerateDataTableDSL(const FString& DSLText)
{
	TSharedPtr<FJsonObject> IRJson;
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(DSLText);
	if (!FJsonSerializer::Deserialize(Reader, IRJson) || !IRJson.IsValid())
	{
		SetCreateStatus(TEXT("Failed to parse Data Table IR JSON."), ErrorRed);
		return;
	}

	FString PackagePath = TEXT("/Game/BlueprintLLM/DataTables");
	FDataTableBuilder::FDTBuildResult Result = FDataTableBuilder::CreateFromIR(IRJson, PackagePath);

	if (!Result.bSuccess)
	{
		SetCreateStatus(FString::Printf(TEXT("DT error: %s"), *Result.ErrorMessage), ErrorRed);
		return;
	}

	SetCreateStatus(FString::Printf(TEXT("\u2713 %s created — %d columns, %d rows"),
		*Result.TableAssetPath, Result.ColumnCount, Result.RowCount), SuccessGreen);

	if (GEditor)
	{
		UObject* Asset = StaticFindObject(UObject::StaticClass(), nullptr, *Result.TableAssetPath);
		if (Asset)
		{
			GEditor->GetEditorSubsystem<UAssetEditorSubsystem>()->OpenEditorForAsset(Asset);
		}
	}
}

void SArcwrightGeneratorPanel::SetCreateStatus(const FString& Message, const FLinearColor& Color)
{
	if (CreateStatusText.IsValid())
	{
		CreateStatusText->SetText(FText::FromString(Message));
		CreateStatusText->SetColorAndOpacity(FSlateColor(Color));
	}
}

// ============================================================
// Log panel (collapsible debug log)
// ============================================================

TSharedRef<SWidget> SArcwrightGeneratorPanel::BuildLogPanel()
{
	return SNew(SVerticalBox)

		// 1px separator line above log
		+ SVerticalBox::Slot()
		.AutoHeight()
		[
			SNew(SBox)
			.HeightOverride(1.0f)
			[
				SNew(SBorder)
				.BorderBackgroundColor(GridLines)
			]
		]

		+ SVerticalBox::Slot()
		.AutoHeight()
		[
			SNew(SExpandableArea)
			.InitiallyCollapsed(true)
			.BorderBackgroundColor(LogBg)
			.Padding(FMargin(0.0f))
			.HeaderPadding(FMargin(8.0f, 4.0f))
			.HeaderContent()
			[
				SNew(SHorizontalBox)

				// "Log" label
				+ SHorizontalBox::Slot()
				.AutoWidth()
				.VAlign(VAlign_Center)
				[
					SNew(STextBlock)
					.Text(LOCTEXT("LogHeader", "Log"))
					.Font(FCoreStyle::GetDefaultFontStyle("Bold", 9))
					.ColorAndOpacity(TextSecondary)
				]

				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				[
					SNew(SSpacer)
				]

				// Entry count badge
				+ SHorizontalBox::Slot()
				.AutoWidth()
				.VAlign(VAlign_Center)
				.Padding(0.0f, 0.0f, 8.0f, 0.0f)
				[
					SNew(STextBlock)
					.Text_Lambda([this]()
					{
						return FText::FromString(FString::Printf(TEXT("%d"), LogEntries.Num()));
					})
					.Font(FCoreStyle::GetDefaultFontStyle("Regular", 8))
					.ColorAndOpacity(TextDim)
				]

				// Copy button
				+ SHorizontalBox::Slot()
				.AutoWidth()
				.VAlign(VAlign_Center)
				.Padding(0.0f, 0.0f, 4.0f, 0.0f)
				[
					SNew(SButton)
					.ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder"))
					.ContentPadding(FMargin(6.0f, 2.0f))
					.OnClicked(this, &SArcwrightGeneratorPanel::OnCopyLogClicked)
					[
						SNew(STextBlock)
						.Text(LOCTEXT("CopyLog", "Copy"))
						.Font(FCoreStyle::GetDefaultFontStyle("Regular", 8))
						.ColorAndOpacity(TextSecondary)
					]
				]

				// Clear button
				+ SHorizontalBox::Slot()
				.AutoWidth()
				.VAlign(VAlign_Center)
				[
					SNew(SButton)
					.ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder"))
					.ContentPadding(FMargin(6.0f, 2.0f))
					.OnClicked(this, &SArcwrightGeneratorPanel::OnClearLogClicked)
					[
						SNew(STextBlock)
						.Text(LOCTEXT("ClearLog", "Clear"))
						.Font(FCoreStyle::GetDefaultFontStyle("Regular", 8))
						.ColorAndOpacity(TextSecondary)
					]
				]
			]
			.BodyContent()
			[
				SNew(SBox)
				.HeightOverride(180.0f)
				[
					SAssignNew(LogTextBox, SMultiLineEditableTextBox)
					.IsReadOnly(true)
					.Font(FCoreStyle::GetDefaultFontStyle("Mono", 8))
					.ForegroundColor(TextSecondary)
					.AutoWrapText(true)
					.Text(FText::GetEmpty())
				]
			]
		];
}

void SArcwrightGeneratorPanel::AddLogEntry(ELogEntryType Type, const FString& Message)
{
	FArcwrightLogEntry Entry;
	Entry.Type = Type;
	Entry.Message = Message.Left(200);
	Entry.Timestamp = FDateTime::Now();
	LogEntries.Add(Entry);

	// FIFO: remove oldest entries beyond limit
	while (LogEntries.Num() > MaxLogEntries)
	{
		LogEntries.RemoveAt(0);
	}

	RefreshLogDisplay();
}

void SArcwrightGeneratorPanel::RefreshLogDisplay()
{
	if (!LogTextBox.IsValid()) return;

	// Build full log text from entries
	LogFullText.Reset();
	for (const FArcwrightLogEntry& Entry : LogEntries)
	{
		FString TimeStr = Entry.Timestamp.ToString(TEXT("%H:%M:%S"));
		FString Prefix = ArcwrightColors::GetLogEntryPrefix(Entry.Type);
		LogFullText += FString::Printf(TEXT("[%s] %s%s\n"), *TimeStr, *Prefix, *Entry.Message);
	}

	LogTextBox->SetText(FText::FromString(LogFullText));

	// Auto-scroll to bottom
	LogTextBox->GoTo(ETextLocation::EndOfDocument);
}

FReply SArcwrightGeneratorPanel::OnCopyLogClicked()
{
	FString Combined;
	for (const FArcwrightLogEntry& Entry : LogEntries)
	{
		FString TimeStr = Entry.Timestamp.ToString(TEXT("%H:%M:%S"));
		FString Prefix = ArcwrightColors::GetLogEntryPrefix(Entry.Type);
		Combined += FString::Printf(TEXT("[%s] %s%s\n"), *TimeStr, *Prefix, *Entry.Message);
	}
	FPlatformApplicationMisc::ClipboardCopy(*Combined);
	return FReply::Handled();
}

FReply SArcwrightGeneratorPanel::OnClearLogClicked()
{
	LogEntries.Empty();
	LogFullText.Reset();
	if (LogTextBox.IsValid())
	{
		LogTextBox->SetText(FText::GetEmpty());
	}
	return FReply::Handled();
}

// ============================================================
// History tab (placeholder)
// ============================================================

TSharedRef<SWidget> SArcwrightGeneratorPanel::BuildHistoryTab()
{
	return SNew(SBorder)
		.BorderBackgroundColor(DeepNavy)
		.Padding(16.0f)
		.HAlign(HAlign_Center)
		.VAlign(VAlign_Center)
		[
			SNew(SVerticalBox)

			+ SVerticalBox::Slot()
			.AutoHeight()
			.HAlign(HAlign_Center)
			.Padding(0.0f, 0.0f, 0.0f, 8.0f)
			[
				SNew(STextBlock)
				.Text(FText::FromString(TEXT("\u23F0"))) // clock icon
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 32))
				.ColorAndOpacity(TextDim)
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.HAlign(HAlign_Center)
			.Padding(0.0f, 0.0f, 0.0f, 4.0f)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("HistoryEmpty", "No history yet"))
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 14))
				.ColorAndOpacity(TextDim)
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.HAlign(HAlign_Center)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("HistoryHint", "Generated assets will appear here"))
				.Font(FCoreStyle::GetDefaultFontStyle("Italic", 10))
				.ColorAndOpacity(TextDim)
			]
		];
}

// ============================================================
// Status bar (always visible at bottom)
// ============================================================

TSharedRef<SWidget> SArcwrightGeneratorPanel::BuildStatusBar()
{
	return SNew(SBorder)
		.BorderBackgroundColor(StatusBarBg)
		.Padding(FMargin(12.0f, 6.0f))
		[
			SNew(SHorizontalBox)

			// Connection indicator (left)
			+ SHorizontalBox::Slot()
			.AutoWidth()
			.VAlign(VAlign_Center)
			.Padding(0.0f, 0.0f, 6.0f, 0.0f)
			[
				SNew(SBox)
				.WidthOverride(8.0f)
				.HeightOverride(8.0f)
				[
					SNew(SBorder)
					.BorderBackgroundColor_Raw(this, &SArcwrightGeneratorPanel::GetConnectionDotColor)
				]
			]

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.VAlign(VAlign_Center)
			.Padding(0.0f, 0.0f, 16.0f, 0.0f)
			[
				SNew(STextBlock)
				.Text_Raw(this, &SArcwrightGeneratorPanel::GetConnectionStatusText)
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 9))
				.ColorAndOpacity(TextSecondary)
			]

			// Model version
			+ SHorizontalBox::Slot()
			.AutoWidth()
			.VAlign(VAlign_Center)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("ModelVer", "Local Builders"))
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 9))
				.ColorAndOpacity(TextDim)
			]

			+ SHorizontalBox::Slot()
			.FillWidth(1.0f)
			[
				SNew(SSpacer)
			]

			// Credits display (right)
			+ SHorizontalBox::Slot()
			.AutoWidth()
			.VAlign(VAlign_Center)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("Credits", "847 / 1,000"))
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 9))
				.ColorAndOpacity(TextSecondary)
			]
		];
}

FText SArcwrightGeneratorPanel::GetConnectionStatusText() const
{
	// The panel always works — it uses local C++ builders directly
	return LOCTEXT("StatusConnected", "Connected");
}

FSlateColor SArcwrightGeneratorPanel::GetConnectionDotColor() const
{
	return FSlateColor(SuccessGreen);
}

#undef LOCTEXT_NAMESPACE
