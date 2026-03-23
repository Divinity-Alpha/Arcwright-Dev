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
// Forward declare — full definition in TierGating.h (Private)
enum class ELicenseState : uint8;

#include "ArcwrightGeneratorPanel.h"   // re-use ArcwrightColors namespace
#include "ArcwrightStats.h"
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
	TSharedRef<SWidget> Build3DProvidersSection();
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

	// ── License / tier ────────────────────────────────────────
	FReply OnActivateProClicked();
	FReply OnDeactivateClicked();
	void   OnLicenseStateChanged(ELicenseState NewState, const FString& Message);
	FDelegateHandle LicenseStateDelegateHandle;
	TSharedPtr<SEditableTextBox> LicenseKeyInput;
	TSharedPtr<STextBlock> LicenseStatusText;

	// ── Timer ─────────────────────────────────────────────────
	EActiveTimerReturnType OnRefreshTimer(double InCurrentTime, float InDeltaTime);

	// ── Helpers ────────────────────────────────────────────────
	class FCommandServer* GetServer() const;
	FArcwrightStats*      GetStats()  const;

	FString FormatUptime(double Seconds) const;
	FString FormatDuration(double Seconds) const;
	FString GetFeedbackEndpoint() const;
};
