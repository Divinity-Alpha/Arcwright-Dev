#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SCheckBox.h"
#include "Widgets/Input/SComboBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSplitter.h"
#include "Widgets/Colors/SColorBlock.h"
#include "ArcwrightGeneratorPanel.h"  // ArcwrightColors

/**
 * SArcwrightUIBuilderPanel
 *
 * Interactive UI Builder for designing game HUDs.
 * Left panel: theme, colors, components. Right panel: live Slate preview.
 * Pro tier feature.
 */
class SArcwrightUIBuilderPanel : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SArcwrightUIBuilderPanel) {}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	static const FName TabId;
	static void RegisterTab();
	static void UnregisterTab();
	static TSharedRef<class SDockTab> SpawnTab(const class FSpawnTabArgs& Args);

	// Paint override for the preview canvas
	virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry,
		const FSlateRect& MyCullingRect, FSlateWindowElementList& OutDrawElements,
		int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const override;

private:
	// ── Section builders ──────────────────────────────────
	TSharedRef<SWidget> BuildHeader();
	TSharedRef<SWidget> BuildControlPanel();
	TSharedRef<SWidget> BuildPreviewPanel();
	TSharedRef<SWidget> BuildStatusBar();

	// ── Theme ─────────────────────────────────────────────
	TArray<TSharedPtr<FString>> ThemeOptions;
	TSharedPtr<FString> SelectedTheme;
	TSharedRef<SWidget> GenerateThemeItem(TSharedPtr<FString> Item);
	void OnThemeSelected(TSharedPtr<FString> Item, ESelectInfo::Type SelectInfo);
	FText GetSelectedThemeText() const;

	// ── Colors ────────────────────────────────────────────
	FLinearColor PrimaryColor;
	FLinearColor AccentColor;
	FLinearColor BgColor;
	void OnPrimaryColorChanged(FLinearColor NewColor);
	void OnAccentColorChanged(FLinearColor NewColor);
	void OnBgColorChanged(FLinearColor NewColor);
	FReply OnResetColorsClicked();
	void LoadThemeColors(const FString& ThemeName);

	// ── Components ────────────────────────────────────────
	struct FComponentEntry
	{
		FString Id;
		FString Name;
		FString Group;
		bool bEnabled = false;
		FVector2D AnchorPos;  // normalized 0-1
	};
	TArray<FComponentEntry> Components;
	void InitComponents();

	// ── Layout ────────────────────────────────────────────
	TArray<TSharedPtr<FString>> LayoutOptions;
	TSharedPtr<FString> SelectedLayout;
	TSharedRef<SWidget> GenerateLayoutItem(TSharedPtr<FString> Item);
	void OnLayoutSelected(TSharedPtr<FString> Item, ESelectInfo::Type SelectInfo);
	FText GetSelectedLayoutText() const;

	// ── Actions ───────────────────────────────────────────
	FReply OnRandomizeClicked();
	FReply OnGenerateClicked();
	FReply OnExportDSLClicked();

	// ── Preview drawing ───────────────────────────────────
	void DrawPreviewComponent(FSlateWindowElementList& Elements, int32& LayerId,
		const FGeometry& Geo, const FComponentEntry& Comp, FVector2D CanvasSize) const;
	void DrawProgressBar(FSlateWindowElementList& Elements, int32& LayerId,
		const FGeometry& Geo, FVector2D Pos, FVector2D Size, float Percent,
		FLinearColor FillColor, FLinearColor BarColor) const;
	void DrawTextLabel(FSlateWindowElementList& Elements, int32& LayerId,
		const FGeometry& Geo, FVector2D Pos, const FString& Text,
		int32 FontSize, FLinearColor Color) const;

	// ── Status ────────────────────────────────────────────
	TSharedPtr<STextBlock> StatusText;
	FString StatusMessage;

	// Preview area widget ref
	TSharedPtr<SBox> PreviewBox;

	// Checkbox state tracking
	TArray<TSharedPtr<SCheckBox>> ComponentCheckboxes;
};
