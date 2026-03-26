// Copyright 2026 Divinity Alpha. All Rights Reserved.
#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SExpandableArea.h"
#include "Widgets/Input/SMultiLineEditableTextBox.h"
#include "Widgets/Input/SComboBox.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Input/SEditableTextBox.h"

#include "ArcwrightStats.h"

// ── Brand colors ─────────────────────────────────────────────
namespace ArcwrightColors
{
	const FLinearColor DeepNavy(0.024f, 0.039f, 0.078f, 1.f);       // #060A14
	const FLinearColor CardBg(0.047f, 0.063f, 0.125f, 1.f);         // #0C1020
	const FLinearColor HeaderBg(0.031f, 0.047f, 0.094f, 1.f);       // #080C18
	const FLinearColor StatusBarBg(0.039f, 0.055f, 0.110f, 1.f);    // #0A0E1C
	const FLinearColor CardHover(0.067f, 0.086f, 0.157f, 1.f);      // #111628
	const FLinearColor BorderLine(0.110f, 0.133f, 0.188f, 1.f);     // #1C2230
	const FLinearColor ErrorBg(0.102f, 0.078f, 0.094f, 1.f);        // #1A1418
	const FLinearColor LogBg(0.031f, 0.039f, 0.071f, 1.f);          // #080A12
	const FLinearColor BrandBlue(0.0103f, 0.1099f, 0.5307f, 1.f);   // #1A5CC0 (linear)
	const FLinearColor DeepBlue(0.0103f, 0.1099f, 0.5307f, 1.f);    // #1A5CC0 (linear)
	const FLinearColor AccentBlue(0.0103f, 0.1099f, 0.5307f, 1.f);  // #1A5CC0 (linear)
	const FLinearColor BrightGreen(0.200f, 0.820f, 0.400f, 1.f);    // #33D166
	const FLinearColor BrightRed(0.949f, 0.251f, 0.302f, 1.f);      // #F2404D
	const FLinearColor GoldAccent(1.000f, 0.780f, 0.200f, 1.f);     // #FFC733
	const FLinearColor PurpleAccent(0.580f, 0.420f, 1.000f, 1.f);   // #946BFF
	const FLinearColor PinkAccent(1.000f, 0.278f, 0.400f, 1.f);     // #FF4766
	const FLinearColor DimText(0.502f, 0.561f, 0.639f, 1.f);        // #808FA3
	const FLinearColor BodyText(0.753f, 0.800f, 0.851f, 1.f);       // #C0CCD9
	const FLinearColor StatNumber(1.f, 1.f, 1.f, 1.f);
	const FLinearColor SuccessGreen = BrightGreen;
	const FLinearColor ErrorRed = BrightRed;
	const FLinearColor WarningAmber = GoldAccent;
	const FLinearColor TextDim = DimText;
}
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"

/**
 * SArcwrightDashboardPanel
 *
 * The default panel shown under Tools → Arcwright → Dashboard.
 * Displays live connection status, session stats, asset counters,
 * lifetime stats, and tier info.  Refreshes every 2 seconds via
 * RegisterActiveTimer.
 *
 * The panel reads directly from FCommandServer (via the module
 * singleton) and from FArcwrightStats — no extra data layer needed.
 */
class SArcwrightDashboardPanel : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SArcwrightDashboardPanel) {}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	/** Tab registration helpers */
	static const FName TabId;
	static void RegisterTab();
	static void UnregisterTab();
	static TSharedRef<class SDockTab> SpawnTab(const class FSpawnTabArgs& Args);

private:
	// ── Section builders ───────────────────────────────────────
	TSharedRef<SWidget> BuildHeader();
	TSharedRef<SWidget> BuildSetupSection();
	TSharedRef<SWidget> BuildConnectionSection();
	TSharedRef<SWidget> BuildSessionSection();
	TSharedRef<SWidget> BuildAssetsSection();
	TSharedRef<SWidget> BuildLifetimeSection();
	TSharedRef<SWidget> BuildTierSection();
	TSharedRef<SWidget> BuildFeedbackSection();

	/** Helper: labelled stat row  (label left, value right) */
	TSharedRef<SWidget> BuildStatRow(const FText& Label,
	                                 TAttribute<FText> Value,
	                                 FLinearColor ValueColor = ArcwrightColors::StatNumber);

	/** Helper: section card with brand-colored left border */
	TSharedRef<SWidget> BuildCard(const FText& Title,
	                              FLinearColor AccentColor,
	                              TSharedRef<SWidget> Content);

	// ── Server control ─────────────────────────────────────────
	FReply OnToggleServerClicked();

	// ── Attribute getters (polled every 2 s) ──────────────────

	// Connection
	FText  GetServerStatusText()   const;
	FSlateColor GetStatusDotColor() const;
	FText  GetConnectedClients()   const;
	FText  GetUptimeText()         const;
	FText  GetToggleButtonText()   const;

	// Session
	FText  GetSessionCommandsText()    const;
	FText  GetSessionSuccessText()     const;
	FText  GetSessionFailText()        const;
	FText  GetSessionSuccessRateText() const;
	FText  GetSessionDurationText()    const;

	// Assets (session)
	FText  GetSessionBlueprintsText()  const;
	FText  GetSessionActorsText()      const;
	FText  GetSessionMaterialsText()   const;
	FText  GetSessionBTsText()         const;
	FText  GetSessionDTsText()         const;

	// Lifetime
	FText  GetLifetimeCommandsText()   const;
	FText  GetLifetimeBlueprintsText() const;
	FText  GetLifetimeActorsText()     const;
	FText  GetLifetimeBTsText()        const;
	FText  GetLifetimeDTsText()        const;
	FText  GetLifetimeMaterialsText()  const;
	FText  GetLifetimeSessionsText()   const;
	FText  GetFirstUseDateText()       const;
	FText  GetTimeSavedText()          const;

	// ── Command log ────────────────────────────────────────────
	void   RefreshCommandLog();
	TSharedPtr<SMultiLineEditableTextBox> CommandLogBox;
	FString CommandLogText;   // rebuilt on each tick

	// ── Feedback section ───────────────────────────────────────
	FReply OnSubmitFeedbackClicked();
	void   OnFeedbackHttpComplete(FHttpRequestPtr Request,
	                               FHttpResponsePtr Response,
	                               bool bConnectedSuccessfully);
	void   SaveFeedbackLocally(const FString& JsonPayload);
	TSharedRef<SWidget> GenerateCategoryComboItem(TSharedPtr<FString> Item);
	void   OnCategorySelected(TSharedPtr<FString> Item, ESelectInfo::Type SelectInfo);
	FText  GetSelectedCategoryText() const;

	TSharedPtr<SMultiLineEditableTextBox> FeedbackInputBox;
	TArray<TSharedPtr<FString>>           FeedbackCategories;
	TSharedPtr<FString>                   SelectedCategory;
	TSharedPtr<STextBlock>                FeedbackConfirmText;
	TSharedPtr<STextBlock>                LastSubmittedText;
	FDateTime                             LastFeedbackSubmitTime;
	FDateTime                             ConfirmShownTime;

	// ── Setup section ─────────────────────────────────────────
	FReply OnCopySetupClicked();
	FString GetSetupText() const;
	FString GetServerPyPath() const;
	TSharedPtr<STextBlock> CopyButtonLabel;
	double  CopyConfirmTime = 0.0;

	// ── Timer ─────────────────────────────────────────────────
	EActiveTimerReturnType OnRefreshTimer(double InCurrentTime, float InDeltaTime);

	// ── Helpers ────────────────────────────────────────────────
	class FCommandServer* GetServer() const;
	FArcwrightStats*      GetStats()  const;

	FString FormatUptime(double Seconds) const;
	FString FormatDuration(double Seconds) const;
	FString GetFeedbackEndpoint() const;
};
