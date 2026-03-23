#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/Input/SMultiLineEditableTextBox.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Layout/SWidgetSwitcher.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Views/SListView.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SExpandableArea.h"
#include "Styling/SlateBrush.h"

// ============================================================
// Data structures
// ============================================================

/** Generation step status for progress display */
enum class EStepStatus : uint8
{
	Pending,
	InProgress,
	Complete,
	Failed
};

/** A single generation step shown in progress indicators */
struct FArcwrightStep
{
	FString Label;
	EStepStatus Status = EStepStatus::Pending;
};

/** Domain of asset being generated */
enum class EArcwrightDomain : uint8
{
	Blueprint,
	BehaviorTree,
	DataTable
};

/** A single operation in the LLM intent plan */
struct FArcwrightOperation
{
	int32 Step = 0;
	FString Command;
	FString Description;
	TSharedPtr<FJsonObject> Params;
	int32 DependsOn = -1;
};

/** Full intent plan from LLM classification */
struct FArcwrightIntentPlan
{
	FString Mode;	// "CREATE", "MODIFY", "QUERY", "MULTI", "CLARIFY"
	FString Summary;
	bool bRequiresConfirmation = false;
	TArray<FArcwrightOperation> Operations;
};

/** Log entry type for the debug log panel */
enum class ELogEntryType : uint8
{
	Info,
	Success,
	Error,
	TCPSent,
	TCPReceived,
	IntentSent,
	IntentReceived
};

/** A single log entry in the debug log panel */
struct FArcwrightLogEntry
{
	ELogEntryType Type = ELogEntryType::Info;
	FString Message;
	FDateTime Timestamp;
};

/** Info about a created asset, shown as a card in the chat */
struct FArcwrightAssetCard
{
	FString AssetName;
	FString AssetPath;
	EArcwrightDomain Domain = EArcwrightDomain::Blueprint;
	int32 NodeCount = 0;
	int32 ConnectionCount = 0;
	bool bCompiled = false;
	bool bHasError = false;
	FString ErrorText;
};

/** A single chat message (user or assistant) */
struct FArcwrightChatMessage
{
	bool bIsUser = true;
	FString Text;
	FDateTime Timestamp;

	// For assistant messages
	bool bIsThinking = false;
	TArray<FArcwrightStep> Steps;
	float Progress = 0.0f;	// 0-1 for progress bar
	TSharedPtr<FArcwrightAssetCard> AssetCard;
	bool bIsError = false;
	EArcwrightDomain Domain = EArcwrightDomain::Blueprint;
	FString IntentMode;		// "CREATE", "MODIFY", "QUERY", "MULTI", "CLARIFY"

	// Verbose result details (populated by ExecutePlan for rich per-mode output)
	FString ResultDetails;
	int32 SucceededCount = 0;
	int32 FailedCount = 0;
};

// ============================================================
// Brand palette — matches Arcwright logo package
// ============================================================

namespace ArcwrightColors
{
	// Primary accents
	inline const FLinearColor BrandBlue(0.290f, 0.620f, 1.0f, 1.0f);		// #4A9EFF — Blueprint domain
	inline const FLinearColor AccentBlue(0.290f, 0.620f, 1.0f, 1.0f);		// #4A9EFF — alias for BrandBlue
	inline const FLinearColor LightBlue(0.416f, 0.706f, 1.0f, 1.0f);		// #6AB4FF
	inline const FLinearColor DeepBlue(0.102f, 0.361f, 0.753f, 1.0f);		// #1A5CC0 — HeaderBlue
	inline const FLinearColor HeaderBlue(0.102f, 0.361f, 0.753f, 1.0f);	// #1A5CC0 — alias for DeepBlue
	inline const FLinearColor MidBlue(0.165f, 0.416f, 0.749f, 1.0f);		// #2A6ABF
	inline const FLinearColor Purple(0.580f, 0.420f, 1.0f, 1.0f);			// #946BFF — BehaviorTree domain (PurpleAccent)
	inline const FLinearColor PurpleAccent(0.580f, 0.420f, 1.0f, 1.0f);	// #946BFF — alias
	inline const FLinearColor Pink(1.0f, 0.278f, 0.400f, 1.0f);			// #FF4766 — DataTable domain (PinkAccent)
	inline const FLinearColor PinkAccent(1.0f, 0.278f, 0.400f, 1.0f);		// #FF4766 — alias
	inline const FLinearColor GoldAccent(1.0f, 0.780f, 0.200f, 1.0f);		// #FFC733 — lifetime/tier

	// Backgrounds
	inline const FLinearColor DeepNavy(0.024f, 0.039f, 0.078f, 1.0f);		// #060A14
	inline const FLinearColor CardBg(0.055f, 0.067f, 0.133f, 1.0f);		// #0E1122
	inline const FLinearColor CardHover(0.067f, 0.086f, 0.157f, 1.0f);		// #111628
	inline const FLinearColor GridLines(0.071f, 0.125f, 0.227f, 1.0f);		// #12203A
	inline const FLinearColor BorderLine(0.290f, 0.620f, 1.0f, 0.15f);		// rgba(74,158,255,0.15) — subtle dividers
	inline const FLinearColor UserBubble(0.102f, 0.165f, 0.271f, 1.0f);	// #1A2A45
	inline const FLinearColor HeaderBg(0.024f, 0.039f, 0.078f, 1.0f);		// #060A14 — matches DeepNavy
	inline const FLinearColor StatusBarBg(0.024f, 0.039f, 0.078f, 1.0f);	// #060A14 — matches DeepNavy

	// Status — vibrant
	inline const FLinearColor SuccessGreen(0.200f, 0.820f, 0.400f, 1.0f);	// #33D166 — BrightGreen
	inline const FLinearColor BrightGreen(0.200f, 0.820f, 0.400f, 1.0f);	// #33D166 — alias
	inline const FLinearColor WarningAmber(0.902f, 0.659f, 0.090f, 1.0f);	// #E6A817
	inline const FLinearColor ErrorRed(0.949f, 0.251f, 0.302f, 1.0f);		// #F2404D — BrightRed
	inline const FLinearColor BrightRed(0.949f, 0.251f, 0.302f, 1.0f);		// #F2404D — alias
	inline const FLinearColor ErrorBg(0.102f, 0.078f, 0.094f, 1.0f);		// #1A1418

	// Text — brighter
	inline const FLinearColor TextPrimary(0.820f, 0.855f, 0.910f, 1.0f);	// #D1DAE8 — BodyText
	inline const FLinearColor BodyText(0.820f, 0.855f, 0.910f, 1.0f);		// #D1DAE8 — alias
	inline const FLinearColor StatNumber(1.0f, 1.0f, 1.0f, 1.0f);			// #FFFFFF — white for stat values
	inline const FLinearColor TextSecondary(0.502f, 0.561f, 0.639f, 1.0f);	// #808FA3 — DimText (brighter than before)
	inline const FLinearColor DimText(0.502f, 0.561f, 0.639f, 1.0f);		// #808FA3 — alias
	inline const FLinearColor TextDim(0.200f, 0.251f, 0.376f, 1.0f);		// #334060

	// Log panel
	inline const FLinearColor LogBg(0.035f, 0.047f, 0.102f, 1.0f);			// #090C1A — log area bg

	// Log entry color helper
	inline FLinearColor GetLogEntryColor(ELogEntryType Type)
	{
		switch (Type)
		{
		case ELogEntryType::Success:
		case ELogEntryType::TCPReceived:
		case ELogEntryType::IntentReceived:
			return SuccessGreen;
		case ELogEntryType::Error:
			return ErrorRed;
		default:
			return TextSecondary;
		}
	}

	// Log entry arrow prefix
	inline FString GetLogEntryPrefix(ELogEntryType Type)
	{
		switch (Type)
		{
		case ELogEntryType::TCPSent:
		case ELogEntryType::IntentSent:
			return TEXT("\u2192 "); // → right arrow
		case ELogEntryType::TCPReceived:
		case ELogEntryType::IntentReceived:
			return TEXT("\u2190 "); // ← left arrow
		case ELogEntryType::Error:
			return TEXT("\u2717 "); // ✗
		case ELogEntryType::Success:
			return TEXT("\u2713 "); // ✓
		default:
			return TEXT("  ");
		}
	}

	// Domain color helper
	inline FLinearColor GetDomainColor(EArcwrightDomain Domain)
	{
		switch (Domain)
		{
		case EArcwrightDomain::BehaviorTree: return Purple;
		case EArcwrightDomain::DataTable:    return Pink;
		default:                             return BrandBlue;
		}
	}

	inline FString GetDomainLabel(EArcwrightDomain Domain)
	{
		switch (Domain)
		{
		case EArcwrightDomain::BehaviorTree: return TEXT("BEHAVIOR TREE");
		case EArcwrightDomain::DataTable:    return TEXT("DATA TABLE");
		default:                             return TEXT("BLUEPRINT");
		}
	}
}

// ============================================================
// Main panel widget
// ============================================================

class SArcwrightGeneratorPanel : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SArcwrightGeneratorPanel) {}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	static const FName TabId;
	static void RegisterTab();
	static void UnregisterTab();
	static TSharedRef<class SDockTab> SpawnTab(const class FSpawnTabArgs& Args);

private:
	// ── Tab management ─────────────────────
	enum class ETab : uint8 { Chat, Create, History };
	ETab ActiveTab = ETab::Chat;
	void SwitchTab(ETab NewTab);
	FReply OnTabClicked_Chat()    { SwitchTab(ETab::Chat);    return FReply::Handled(); }
	FReply OnTabClicked_Create()  { SwitchTab(ETab::Create);  return FReply::Handled(); }
	FReply OnTabClicked_History() { SwitchTab(ETab::History); return FReply::Handled(); }

	// ── Header construction ────────────────
	TSharedRef<SWidget> BuildHeader();
	TSharedRef<SWidget> BuildTabButton(const FText& Label, ETab TabType);

	// ── Chat tab ───────────────────────────
	TSharedRef<SWidget> BuildChatTab();
	TSharedRef<SWidget> BuildInputBar();
	TSharedRef<SWidget> BuildMessageWidget(TSharedPtr<FArcwrightChatMessage> Msg);
	TSharedRef<SWidget> BuildAssetCardWidget(TSharedPtr<FArcwrightAssetCard> Card);
	TSharedRef<SWidget> BuildStepsWidget(const TArray<FArcwrightStep>& Steps, float Progress);
	TSharedRef<SWidget> BuildResultDetailsWidget(TSharedPtr<FArcwrightChatMessage> Msg);

	FReply OnSendClicked();
	FReply OnChatInputKeyDown(const FGeometry& Geometry, const FKeyEvent& KeyEvent);
	void AddUserMessage(const FString& Text);
	void AddAssistantMessage(const FString& Text, bool bError = false);
	void AddThinkingMessage();
	void UpdateLastAssistantMessage(const FString& Text, bool bError, TSharedPtr<FArcwrightAssetCard> Card = nullptr);
	void RefreshChatList();

	// ── Create tab ─────────────────────────
	TSharedRef<SWidget> BuildCreateTab();
	FReply OnCreateGenerateClicked();
	FReply OnCreateClearClicked();
	void OnDomainSelected(EArcwrightDomain NewDomain);

	// ── History tab ────────────────────────
	TSharedRef<SWidget> BuildHistoryTab();

	// ── Log panel ──────────────────────────
	TSharedRef<SWidget> BuildLogPanel();
	void AddLogEntry(ELogEntryType Type, const FString& Message);
	void RefreshLogDisplay();
	FReply OnCopyLogClicked();
	FReply OnClearLogClicked();

	// ── Status bar ─────────────────────────
	TSharedRef<SWidget> BuildStatusBar();
	FText GetConnectionStatusText() const;
	FSlateColor GetConnectionDotColor() const;

	// ── Generation logic ───────────────────
	EArcwrightDomain DetectDomainFromPrompt(const FString& Prompt) const;
	void GenerateFromChat(const FString& Prompt);
	void DoGenerateBlueprint(const FString& InputText);
	void DoGenerateBehaviorTree(const FString& InputText);
	void DoGenerateDataTable(const FString& InputText);

	// ── Intent routing (LLM-based) ───────
	FArcwrightIntentPlan ClassifyIntent(const FString& Prompt);
	void ExecutePlan(const FArcwrightIntentPlan& Plan);
	void DisplayPlanPreview(const FArcwrightIntentPlan& Plan);
	FReply OnConfirmPlanClicked();
	FReply OnCancelPlanClicked();
	FString GetModeLabel(const FString& Mode) const;
	FLinearColor GetModeColor(const FString& Mode) const;

	// ── Create tab generation (DSL direct) ─
	void GenerateBlueprintDSL(const FString& DSLText);
	void GenerateBehaviorTreeDSL(const FString& DSLText);
	void GenerateDataTableDSL(const FString& DSLText);

	// ── Status helpers ─────────────────────
	void SetCreateStatus(const FString& Message, const FLinearColor& Color);

	// ── Widget references ──────────────────
	TSharedPtr<SWidgetSwitcher> TabSwitcher;
	TSharedPtr<SScrollBox> ChatScrollBox;
	TSharedPtr<SVerticalBox> ChatMessageList;
	TSharedPtr<SMultiLineEditableTextBox> ChatInput;
	TSharedPtr<SMultiLineEditableTextBox> CreateInputBox;
	TSharedPtr<STextBlock> CreateStatusText;
	TSharedPtr<STextBlock> ConnectionStatusText;

	// Tab button references for underline styling
	TSharedPtr<SBorder> TabUnderline_Chat;
	TSharedPtr<SBorder> TabUnderline_Create;
	TSharedPtr<SBorder> TabUnderline_History;

	// ── Branded image brushes ─────────────
	void LoadBrandBrushes();
	TSharedPtr<FSlateDynamicImageBrush> HeroBannerBrush;
	TSharedPtr<FSlateDynamicImageBrush> LogoBrush;
	TSharedPtr<FSlateDynamicImageBrush> Icon40Brush;
	TSharedPtr<FSlateDynamicImageBrush> Icon16Brush;

	// ── Log panel widgets ─────────────────
	TSharedPtr<SMultiLineEditableTextBox> LogTextBox;
	FString LogFullText;

	// ── State ──────────────────────────────
	TArray<TSharedPtr<FArcwrightChatMessage>> ChatMessages;
	EArcwrightDomain CreateDomain = EArcwrightDomain::Blueprint;
	bool bIsGenerating = false;

	// ── Log state ─────────────────────────
	TArray<FArcwrightLogEntry> LogEntries;
	static const int32 MaxLogEntries = 500;

	// ── Intent routing state ──────────────
	FArcwrightIntentPlan PendingPlan;
	bool bAwaitingConfirmation = false;
	TMap<int32, TSharedPtr<FJsonObject>> StepResults;	// results keyed by step number
};
