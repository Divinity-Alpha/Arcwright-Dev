#include "ArcwrightUIBuilderPanel.h"
#include "TierGating.h"
#include "ArcwrightModule.h"
#include "Framework/Docking/TabManager.h"
#include "Widgets/Docking/SDockTab.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/Layout/SSeparator.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "HAL/PlatformApplicationMisc.h"
#include "Styling/AppStyle.h"
#include "Widgets/Colors/SColorPicker.h"

#define LOCTEXT_NAMESPACE "ArcwrightUIBuilder"

const FName SArcwrightUIBuilderPanel::TabId = FName("ArcwrightUIBuilderTab");

// ── Tab registration ────────────────────────────────────────

void SArcwrightUIBuilderPanel::RegisterTab()
{
	FGlobalTabmanager::Get()->RegisterNomadTabSpawner(
		TabId,
		FOnSpawnTab::CreateStatic(&SArcwrightUIBuilderPanel::SpawnTab))
		.SetDisplayName(LOCTEXT("UIBuilderTitle", "Arcwright UI Builder"))
		.SetTooltipText(LOCTEXT("UIBuilderTooltip", "Visually design game UIs with themes and components"))
		.SetMenuType(ETabSpawnerMenuType::Hidden);
}

void SArcwrightUIBuilderPanel::UnregisterTab()
{
	FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(TabId);
}

TSharedRef<SDockTab> SArcwrightUIBuilderPanel::SpawnTab(const FSpawnTabArgs& Args)
{
	return SNew(SDockTab)
		.TabRole(ETabRole::NomadTab)
		[
			SNew(SArcwrightUIBuilderPanel)
		];
}

// ── Construct ───────────────────────────────────────────────

void SArcwrightUIBuilderPanel::Construct(const FArguments& InArgs)
{
	// Init theme options
	ThemeOptions.Add(MakeShareable(new FString(TEXT("Normal"))));
	ThemeOptions.Add(MakeShareable(new FString(TEXT("SciFi"))));
	ThemeOptions.Add(MakeShareable(new FString(TEXT("Medieval"))));
	ThemeOptions.Add(MakeShareable(new FString(TEXT("Racing"))));
	ThemeOptions.Add(MakeShareable(new FString(TEXT("Fighting"))));
	ThemeOptions.Add(MakeShareable(new FString(TEXT("Simulation"))));
	ThemeOptions.Add(MakeShareable(new FString(TEXT("Horror"))));
	ThemeOptions.Add(MakeShareable(new FString(TEXT("Cartoon"))));
	SelectedTheme = ThemeOptions[0];

	// Init layout options
	LayoutOptions.Add(MakeShareable(new FString(TEXT("Standard FPS"))));
	LayoutOptions.Add(MakeShareable(new FString(TEXT("Minimal"))));
	LayoutOptions.Add(MakeShareable(new FString(TEXT("Dense RPG"))));
	LayoutOptions.Add(MakeShareable(new FString(TEXT("Clean Racing"))));
	SelectedLayout = LayoutOptions[0];

	// Init colors from default theme
	LoadThemeColors(TEXT("Normal"));

	// Init components
	InitComponents();

	StatusMessage = TEXT("Ready \u2014 select components and click Generate");

	ChildSlot
	[
		SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("NoBrush"))
		.Padding(0.f)
		[
			SNew(SVerticalBox)

			// Header
			+ SVerticalBox::Slot().AutoHeight()
			[
				BuildHeader()
			]

			// Main body: controls | preview
			+ SVerticalBox::Slot().FillHeight(1.f)
			[
				SNew(SSplitter)
				.Orientation(Orient_Horizontal)

				+ SSplitter::Slot()
				.Value(0.3f)
				[
					BuildControlPanel()
				]

				+ SSplitter::Slot()
				.Value(0.7f)
				[
					BuildPreviewPanel()
				]
			]

			// Status bar
			+ SVerticalBox::Slot().AutoHeight()
			[
				BuildStatusBar()
			]
		]
	];
}

// ── Header ──────────────────────────────────────────────────

TSharedRef<SWidget> SArcwrightUIBuilderPanel::BuildHeader()
{
	return SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("WhiteBrush"))
		.BorderBackgroundColor(ArcwrightColors::HeaderBg)
		.Padding(FMargin(16.f, 10.f))
		[
			SNew(SHorizontalBox)

			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("BuilderLogo", "A R C W R I G H T   U I   B U I L D E R"))
				.ColorAndOpacity(ArcwrightColors::AccentBlue)
				.Font(FCoreStyle::GetDefaultFontStyle("Bold", 16))
			]

			+ SHorizontalBox::Slot().FillWidth(1.f)
			[
				SNullWidget::NullWidget
			]

			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
			[
				SNew(SBorder)
				.BorderImage(FAppStyle::GetBrush("WhiteBrush"))
				.BorderBackgroundColor(ArcwrightColors::GoldAccent)
				.Padding(FMargin(8.f, 3.f))
				[
					SNew(STextBlock)
					.Text(LOCTEXT("ProBadge", "PRO"))
					.ColorAndOpacity(FLinearColor::Black)
					.Font(FCoreStyle::GetDefaultFontStyle("Bold", 11))
				]
			]
		];
}

// ── Control Panel (left) ────────────────────────────────────

TSharedRef<SWidget> SArcwrightUIBuilderPanel::BuildControlPanel()
{
	TSharedRef<SVerticalBox> Controls = SNew(SVerticalBox);

	// Section 1: Theme
	Controls->AddSlot().AutoHeight().Padding(8.f)
	[
		SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 4)
		[
			SNew(STextBlock)
			.Text(LOCTEXT("ThemeLabel", "THEME"))
			.ColorAndOpacity(ArcwrightColors::DimText)
			.Font(FCoreStyle::GetDefaultFontStyle("Bold", 12))
		]
		+ SVerticalBox::Slot().AutoHeight()
		[
			SNew(SComboBox<TSharedPtr<FString>>)
			.OptionsSource(&ThemeOptions)
			.OnSelectionChanged(this, &SArcwrightUIBuilderPanel::OnThemeSelected)
			.OnGenerateWidget(this, &SArcwrightUIBuilderPanel::GenerateThemeItem)
			.InitiallySelectedItem(SelectedTheme)
			[
				SNew(STextBlock)
				.Text(this, &SArcwrightUIBuilderPanel::GetSelectedThemeText)
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 13))
			]
		]
	];

	// Section 2: Colors
	Controls->AddSlot().AutoHeight().Padding(8.f)
	[
		SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 4)
		[
			SNew(STextBlock)
			.Text(LOCTEXT("ColorsLabel", "COLORS"))
			.ColorAndOpacity(ArcwrightColors::DimText)
			.Font(FCoreStyle::GetDefaultFontStyle("Bold", 12))
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0, 2)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 8, 0)
			[
				SNew(STextBlock).Text(LOCTEXT("PrimaryLbl", "Primary")).Font(FCoreStyle::GetDefaultFontStyle("Regular", 12))
				.ColorAndOpacity(ArcwrightColors::BodyText)
			]
			+ SHorizontalBox::Slot().AutoWidth()
			[
				SNew(SColorBlock)
				.Color_Lambda([this]() { return PrimaryColor; })
				.Size(FVector2D(24, 24))
				.OnMouseButtonDown_Lambda([this](const FGeometry&, const FPointerEvent&) -> FReply {
					FColorPickerArgs Args;
					Args.InitialColor = PrimaryColor;
					Args.OnColorCommitted.BindRaw(this, &SArcwrightUIBuilderPanel::OnPrimaryColorChanged);
					OpenColorPicker(Args);
					return FReply::Handled();
				})
			]
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0, 2)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 8, 0)
			[
				SNew(STextBlock).Text(LOCTEXT("AccentLbl", "Accent")).Font(FCoreStyle::GetDefaultFontStyle("Regular", 12))
				.ColorAndOpacity(ArcwrightColors::BodyText)
			]
			+ SHorizontalBox::Slot().AutoWidth()
			[
				SNew(SColorBlock)
				.Color_Lambda([this]() { return AccentColor; })
				.Size(FVector2D(24, 24))
				.OnMouseButtonDown_Lambda([this](const FGeometry&, const FPointerEvent&) -> FReply {
					FColorPickerArgs Args;
					Args.InitialColor = AccentColor;
					Args.OnColorCommitted.BindRaw(this, &SArcwrightUIBuilderPanel::OnAccentColorChanged);
					OpenColorPicker(Args);
					return FReply::Handled();
				})
			]
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0, 4)
		[
			SNew(SButton)
			.OnClicked(this, &SArcwrightUIBuilderPanel::OnResetColorsClicked)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("ResetColors", "Reset to Theme"))
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 11))
				.ColorAndOpacity(ArcwrightColors::DimText)
			]
		]
	];

	// Section 3: Components
	Controls->AddSlot().AutoHeight().Padding(8.f, 8.f, 8.f, 2.f)
	[
		SNew(STextBlock)
		.Text(LOCTEXT("ComponentsLabel", "COMPONENTS"))
		.ColorAndOpacity(ArcwrightColors::DimText)
		.Font(FCoreStyle::GetDefaultFontStyle("Bold", 12))
	];

	// Component checkboxes in a scroll box
	TSharedRef<SScrollBox> CompScroll = SNew(SScrollBox);
	ComponentCheckboxes.Empty();

	FString LastGroup;
	for (int32 i = 0; i < Components.Num(); i++)
	{
		FComponentEntry& C = Components[i];
		if (C.Group != LastGroup)
		{
			LastGroup = C.Group;
			CompScroll->AddSlot().Padding(0, 6, 0, 2)
			[
				SNew(STextBlock)
				.Text(FText::FromString(C.Group))
				.ColorAndOpacity(ArcwrightColors::AccentBlue)
				.Font(FCoreStyle::GetDefaultFontStyle("Bold", 11))
			];
		}

		int32 Idx = i;
		TSharedPtr<SCheckBox> CB;
		CompScroll->AddSlot().Padding(4, 1)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[
				SAssignNew(CB, SCheckBox)
				.IsChecked_Lambda([this, Idx]() { return Components[Idx].bEnabled ? ECheckBoxState::Checked : ECheckBoxState::Unchecked; })
				.OnCheckStateChanged_Lambda([this, Idx](ECheckBoxState State) {
					Components[Idx].bEnabled = (State == ECheckBoxState::Checked);
					Invalidate(EInvalidateWidgetReason::Paint);
				})
			]
			+ SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center).Padding(4, 0, 0, 0)
			[
				SNew(STextBlock)
				.Text(FText::FromString(C.Name))
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 12))
				.ColorAndOpacity(ArcwrightColors::BodyText)
			]
		];
		ComponentCheckboxes.Add(CB);
	}

	Controls->AddSlot().FillHeight(1.f).Padding(8.f, 0.f)
	[
		CompScroll
	];

	// Section 4: Layout
	Controls->AddSlot().AutoHeight().Padding(8.f)
	[
		SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 4)
		[
			SNew(STextBlock)
			.Text(LOCTEXT("LayoutLabel", "LAYOUT"))
			.ColorAndOpacity(ArcwrightColors::DimText)
			.Font(FCoreStyle::GetDefaultFontStyle("Bold", 12))
		]
		+ SVerticalBox::Slot().AutoHeight()
		[
			SNew(SComboBox<TSharedPtr<FString>>)
			.OptionsSource(&LayoutOptions)
			.OnSelectionChanged(this, &SArcwrightUIBuilderPanel::OnLayoutSelected)
			.OnGenerateWidget(this, &SArcwrightUIBuilderPanel::GenerateLayoutItem)
			.InitiallySelectedItem(SelectedLayout)
			[
				SNew(STextBlock)
				.Text(this, &SArcwrightUIBuilderPanel::GetSelectedLayoutText)
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 13))
			]
		]
	];

	// Section 5: Action buttons
	Controls->AddSlot().AutoHeight().Padding(8.f)
	[
		SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight().Padding(0, 2)
		[
			SNew(SSeparator).Thickness(1.f)
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0, 4)
		[
			SNew(SButton).OnClicked(this, &SArcwrightUIBuilderPanel::OnRandomizeClicked)
			[
				SNew(STextBlock).Text(LOCTEXT("Randomize", "Randomize Style"))
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 13)).ColorAndOpacity(ArcwrightColors::BodyText)
			]
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0, 4)
		[
			SNew(SButton).OnClicked(this, &SArcwrightUIBuilderPanel::OnGenerateClicked)
			[
				SNew(SBorder)
				.BorderImage(FAppStyle::GetBrush("WhiteBrush"))
				.BorderBackgroundColor(ArcwrightColors::AccentBlue)
				.Padding(FMargin(0, 4))
				[
					SNew(STextBlock).Text(LOCTEXT("Generate", "Generate Final UI"))
					.Font(FCoreStyle::GetDefaultFontStyle("Bold", 14)).ColorAndOpacity(FLinearColor::White)
					.Justification(ETextJustify::Center)
				]
			]
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0, 4)
		[
			SNew(SButton).OnClicked(this, &SArcwrightUIBuilderPanel::OnExportDSLClicked)
			[
				SNew(STextBlock).Text(LOCTEXT("ExportDSL", "Export DSL"))
				.Font(FCoreStyle::GetDefaultFontStyle("Regular", 13)).ColorAndOpacity(ArcwrightColors::DimText)
			]
		]
	];

	return SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("WhiteBrush"))
		.BorderBackgroundColor(ArcwrightColors::DeepNavy)
		[
			Controls
		];
}

// ── Preview Panel (right) ───────────────────────────────────

TSharedRef<SWidget> SArcwrightUIBuilderPanel::BuildPreviewPanel()
{
	return SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("WhiteBrush"))
		.BorderBackgroundColor(FLinearColor(0.02f, 0.03f, 0.05f))
		.Padding(4.f)
		[
			SAssignNew(PreviewBox, SBox)
			.MinDesiredWidth(640)
			.MinDesiredHeight(360)
		];
}

// ── Status Bar ──────────────────────────────────────────────

TSharedRef<SWidget> SArcwrightUIBuilderPanel::BuildStatusBar()
{
	return SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("WhiteBrush"))
		.BorderBackgroundColor(ArcwrightColors::HeaderBg)
		.Padding(FMargin(12.f, 6.f))
		[
			SAssignNew(StatusText, STextBlock)
			.Text_Lambda([this]() { return FText::FromString(StatusMessage); })
			.ColorAndOpacity(ArcwrightColors::DimText)
			.Font(FCoreStyle::GetDefaultFontStyle("Regular", 12))
		];
}

// ── OnPaint — Live Preview ──────────────────────────────────

int32 SArcwrightUIBuilderPanel::OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry,
	const FSlateRect& MyCullingRect, FSlateWindowElementList& OutDrawElements,
	int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const
{
	// First paint children (controls, etc.)
	LayerId = SCompoundWidget::OnPaint(Args, AllottedGeometry, MyCullingRect, OutDrawElements, LayerId, InWidgetStyle, bParentEnabled);

	// Draw preview on the right side
	if (!PreviewBox.IsValid()) return LayerId;

	FGeometry PreviewGeo = PreviewBox->GetCachedGeometry();
	FVector2D PreviewSize = PreviewGeo.GetLocalSize();

	if (PreviewSize.X < 100 || PreviewSize.Y < 100) return LayerId;

	// 16:9 canvas scaled to fit
	float CanvasW = PreviewSize.X - 8;
	float CanvasH = CanvasW * 9.f / 16.f;
	if (CanvasH > PreviewSize.Y - 8)
	{
		CanvasH = PreviewSize.Y - 8;
		CanvasW = CanvasH * 16.f / 9.f;
	}
	FVector2D CanvasSize(CanvasW, CanvasH);

	// Draw each enabled component
	for (const FComponentEntry& Comp : Components)
	{
		if (!Comp.bEnabled) continue;
		const_cast<SArcwrightUIBuilderPanel*>(this)->DrawPreviewComponent(
			OutDrawElements, LayerId, PreviewGeo, Comp, CanvasSize);
	}

	return LayerId;
}

void SArcwrightUIBuilderPanel::DrawPreviewComponent(
	FSlateWindowElementList& Elements, int32& LayerId,
	const FGeometry& Geo, const FComponentEntry& Comp, FVector2D CanvasSize) const
{
	FVector2D Pos(Comp.AnchorPos.X * CanvasSize.X, Comp.AnchorPos.Y * CanvasSize.Y);

	if (Comp.Id == TEXT("health_bar"))
	{
		DrawProgressBar(Elements, LayerId, Geo, Pos, FVector2D(200, 16), 0.75f, PrimaryColor, FLinearColor(0.1f, 0.12f, 0.18f));
		DrawTextLabel(Elements, LayerId, Geo, Pos + FVector2D(210, 0), TEXT("75/100"), 12, FLinearColor::White);
	}
	else if (Comp.Id == TEXT("score_panel"))
	{
		DrawTextLabel(Elements, LayerId, Geo, Pos, TEXT("SCORE"), 10, FLinearColor(0.5f, 0.55f, 0.65f));
		DrawTextLabel(Elements, LayerId, Geo, Pos + FVector2D(0, 14), TEXT("12,450"), 22, AccentColor);
	}
	else if (Comp.Id == TEXT("ammo_counter"))
	{
		DrawTextLabel(Elements, LayerId, Geo, Pos, TEXT("24 / 30"), 20, FLinearColor::White);
		DrawTextLabel(Elements, LayerId, Geo, Pos + FVector2D(0, 24), TEXT("M4A1"), 10, FLinearColor(0.5f, 0.55f, 0.65f));
	}
	else if (Comp.Id == TEXT("crosshair"))
	{
		DrawTextLabel(Elements, LayerId, Geo, Pos - FVector2D(6, 10), TEXT("+"), 18, FLinearColor(1, 1, 1, 0.7f));
	}
	else if (Comp.Id == TEXT("shield_bar"))
	{
		DrawProgressBar(Elements, LayerId, Geo, Pos, FVector2D(160, 12), 0.5f, FLinearColor(0.3f, 0.5f, 1.f), FLinearColor(0.1f, 0.12f, 0.18f));
	}
	else if (Comp.Id == TEXT("stamina_bar"))
	{
		DrawProgressBar(Elements, LayerId, Geo, Pos, FVector2D(140, 6), 0.85f, FLinearColor(1.f, 0.78f, 0.2f), FLinearColor(0.1f, 0.12f, 0.18f));
	}
	else if (Comp.Id == TEXT("minimap"))
	{
		// Draw a bordered square
		FSlateDrawElement::MakeBox(Elements, LayerId++,
			Geo.ToPaintGeometry(Pos, FVector2D(120, 120)),
			FAppStyle::GetBrush("WhiteBrush"), ESlateDrawEffect::None,
			FLinearColor(0.15f, 0.18f, 0.25f));
		FSlateDrawElement::MakeBox(Elements, LayerId++,
			Geo.ToPaintGeometry(Pos + FVector2D(2, 2), FVector2D(116, 116)),
			FAppStyle::GetBrush("WhiteBrush"), ESlateDrawEffect::None,
			FLinearColor(0.08f, 0.1f, 0.15f));
		DrawTextLabel(Elements, LayerId, Geo, Pos + FVector2D(55, 55), TEXT("^"), 14, AccentColor);
	}
	else if (Comp.Id == TEXT("timer"))
	{
		DrawTextLabel(Elements, LayerId, Geo, Pos, TEXT("04:32"), 20, FLinearColor::White);
	}
	else if (Comp.Id == TEXT("wave_counter"))
	{
		DrawTextLabel(Elements, LayerId, Geo, Pos, TEXT("WAVE 3/10"), 16, AccentColor);
	}
	else if (Comp.Id == TEXT("boss_health_bar"))
	{
		DrawTextLabel(Elements, LayerId, Geo, Pos, TEXT("DARK KNIGHT"), 14, FLinearColor(0.9f, 0.2f, 0.2f));
		DrawProgressBar(Elements, LayerId, Geo, Pos + FVector2D(0, 18), FVector2D(350, 14), 0.6f,
			FLinearColor(0.85f, 0.15f, 0.15f), FLinearColor(0.1f, 0.12f, 0.18f));
	}
	else
	{
		// Generic: draw component name as label
		DrawTextLabel(Elements, LayerId, Geo, Pos, *Comp.Name, 11, FLinearColor(0.5f, 0.55f, 0.65f));
	}
}

void SArcwrightUIBuilderPanel::DrawProgressBar(
	FSlateWindowElementList& Elements, int32& LayerId,
	const FGeometry& Geo, FVector2D Pos, FVector2D Size,
	float Percent, FLinearColor FillColor, FLinearColor BarColor) const
{
	// Background
	FSlateDrawElement::MakeBox(Elements, LayerId++,
		Geo.ToPaintGeometry(Pos, Size),
		FAppStyle::GetBrush("WhiteBrush"), ESlateDrawEffect::None, BarColor);
	// Fill
	FSlateDrawElement::MakeBox(Elements, LayerId++,
		Geo.ToPaintGeometry(Pos, FVector2D(Size.X * FMath::Clamp(Percent, 0.f, 1.f), Size.Y)),
		FAppStyle::GetBrush("WhiteBrush"), ESlateDrawEffect::None, FillColor);
}

void SArcwrightUIBuilderPanel::DrawTextLabel(
	FSlateWindowElementList& Elements, int32& LayerId,
	const FGeometry& Geo, FVector2D Pos, const FString& Text,
	int32 FontSize, FLinearColor Color) const
{
	FSlateFontInfo Font = FCoreStyle::GetDefaultFontStyle("Regular", FontSize);
	FSlateDrawElement::MakeText(Elements, LayerId++,
		Geo.ToPaintGeometry(Pos, FVector2D(400, FontSize + 4)),
		Text, Font, ESlateDrawEffect::None, Color);
}

// ── Theme handling ──────────────────────────────────────────

TSharedRef<SWidget> SArcwrightUIBuilderPanel::GenerateThemeItem(TSharedPtr<FString> Item)
{
	return SNew(STextBlock).Text(FText::FromString(*Item)).Font(FCoreStyle::GetDefaultFontStyle("Regular", 13));
}

void SArcwrightUIBuilderPanel::OnThemeSelected(TSharedPtr<FString> Item, ESelectInfo::Type SelectInfo)
{
	SelectedTheme = Item;
	LoadThemeColors(*Item.Get());
	Invalidate(EInvalidateWidgetReason::Paint);
}

FText SArcwrightUIBuilderPanel::GetSelectedThemeText() const
{
	return SelectedTheme.IsValid() ? FText::FromString(*SelectedTheme) : FText::GetEmpty();
}

void SArcwrightUIBuilderPanel::LoadThemeColors(const FString& ThemeName)
{
	// Hardcoded theme primaries (matches JSON files)
	if (ThemeName == TEXT("Normal"))       { PrimaryColor = FLinearColor(0.29f, 0.62f, 1.f); AccentColor = FLinearColor(0.2f, 0.82f, 0.4f); BgColor = FLinearColor(0.1f, 0.12f, 0.18f); }
	else if (ThemeName == TEXT("SciFi"))   { PrimaryColor = FLinearColor(0.f, 0.83f, 1.f);   AccentColor = FLinearColor(1.f, 0.23f, 0.36f);  BgColor = FLinearColor(0.04f, 0.09f, 0.16f); }
	else if (ThemeName == TEXT("Medieval")){ PrimaryColor = FLinearColor(0.83f, 0.66f, 0.34f);AccentColor = FLinearColor(0.55f, 0.1f, 0.1f);  BgColor = FLinearColor(0.16f, 0.13f, 0.09f); }
	else if (ThemeName == TEXT("Racing"))  { PrimaryColor = FLinearColor(1.f, 0.84f, 0.f);   AccentColor = FLinearColor(1.f, 0.f, 0.f);       BgColor = FLinearColor(0.04f, 0.04f, 0.04f); }
	else if (ThemeName == TEXT("Fighting")){ PrimaryColor = FLinearColor(0.86f, 0.08f, 0.24f);AccentColor = FLinearColor(0.f, 0.75f, 1.f);    BgColor = FLinearColor(0.05f, 0.05f, 0.05f); }
	else if (ThemeName == TEXT("Simulation")){PrimaryColor = FLinearColor(0.29f, 0.5f, 0.71f);AccentColor = FLinearColor(0.17f, 0.67f, 0.53f); BgColor = FLinearColor(0.1f, 0.11f, 0.14f); }
	else if (ThemeName == TEXT("Horror"))  { PrimaryColor = FLinearColor(0.42f, 0.f, 0.f);   AccentColor = FLinearColor(0.29f, 0.42f, 0.16f); BgColor = FLinearColor(0.03f, 0.03f, 0.03f); }
	else if (ThemeName == TEXT("Cartoon")) { PrimaryColor = FLinearColor(0.27f, 0.53f, 1.f);  AccentColor = FLinearColor(1.f, 0.53f, 0.27f);  BgColor = FLinearColor(1.f, 1.f, 1.f); }
}

void SArcwrightUIBuilderPanel::OnPrimaryColorChanged(FLinearColor NewColor) { PrimaryColor = NewColor; Invalidate(EInvalidateWidgetReason::Paint); }
void SArcwrightUIBuilderPanel::OnAccentColorChanged(FLinearColor NewColor) { AccentColor = NewColor; Invalidate(EInvalidateWidgetReason::Paint); }
void SArcwrightUIBuilderPanel::OnBgColorChanged(FLinearColor NewColor) { BgColor = NewColor; Invalidate(EInvalidateWidgetReason::Paint); }

FReply SArcwrightUIBuilderPanel::OnResetColorsClicked()
{
	if (SelectedTheme.IsValid()) LoadThemeColors(*SelectedTheme);
	Invalidate(EInvalidateWidgetReason::Paint);
	return FReply::Handled();
}

// ── Layout ──────────────────────────────────────────────────

TSharedRef<SWidget> SArcwrightUIBuilderPanel::GenerateLayoutItem(TSharedPtr<FString> Item)
{
	return SNew(STextBlock).Text(FText::FromString(*Item)).Font(FCoreStyle::GetDefaultFontStyle("Regular", 13));
}

void SArcwrightUIBuilderPanel::OnLayoutSelected(TSharedPtr<FString> Item, ESelectInfo::Type SelectInfo)
{
	SelectedLayout = Item;
	Invalidate(EInvalidateWidgetReason::Paint);
}

FText SArcwrightUIBuilderPanel::GetSelectedLayoutText() const
{
	return SelectedLayout.IsValid() ? FText::FromString(*SelectedLayout) : FText::GetEmpty();
}

// ── Components ──────────────────────────────────────────────

void SArcwrightUIBuilderPanel::InitComponents()
{
	Components.Empty();
	auto Add = [this](const FString& Id, const FString& Name, const FString& Group, bool bOn, FVector2D Anchor) {
		FComponentEntry E; E.Id = Id; E.Name = Name; E.Group = Group; E.bEnabled = bOn; E.AnchorPos = Anchor;
		Components.Add(E);
	};

	// Essential
	Add(TEXT("health_bar"),    TEXT("Health Bar"),    TEXT("Essential"), true,  FVector2D(0.02f, 0.03f));
	Add(TEXT("score_panel"),   TEXT("Score Counter"), TEXT("Essential"), true,  FVector2D(0.85f, 0.03f));
	Add(TEXT("crosshair"),     TEXT("Crosshair"),     TEXT("Essential"), true,  FVector2D(0.49f, 0.47f));

	// Combat
	Add(TEXT("shield_bar"),    TEXT("Shield Bar"),    TEXT("Combat"), false, FVector2D(0.02f, 0.07f));
	Add(TEXT("stamina_bar"),   TEXT("Stamina Bar"),   TEXT("Combat"), false, FVector2D(0.02f, 0.1f));
	Add(TEXT("ammo_counter"),  TEXT("Ammo Counter"),  TEXT("Combat"), true,  FVector2D(0.82f, 0.85f));
	Add(TEXT("boss_health_bar"),TEXT("Boss Health Bar"),TEXT("Combat"),false, FVector2D(0.2f, 0.05f));
	Add(TEXT("damage_indicator"),TEXT("Damage Flash"), TEXT("Combat"), false, FVector2D(0.0f, 0.0f));

	// Navigation
	Add(TEXT("minimap"),       TEXT("Minimap"),       TEXT("Navigation"), false, FVector2D(0.83f, 0.03f));
	Add(TEXT("compass"),       TEXT("Compass"),       TEXT("Navigation"), false, FVector2D(0.3f, 0.01f));
	Add(TEXT("interaction_prompt"),TEXT("Interact Prompt"),TEXT("Navigation"),false,FVector2D(0.4f, 0.6f));
	Add(TEXT("objective_tracker"),TEXT("Objectives"),  TEXT("Navigation"), false, FVector2D(0.83f, 0.25f));

	// Info
	Add(TEXT("timer"),         TEXT("Timer"),         TEXT("Info"), false, FVector2D(0.45f, 0.03f));
	Add(TEXT("wave_counter"),  TEXT("Wave Counter"),  TEXT("Info"), false, FVector2D(0.4f, 0.08f));
	Add(TEXT("kill_feed"),     TEXT("Kill Feed"),     TEXT("Info"), false, FVector2D(0.82f, 0.15f));
	Add(TEXT("notification_stack"),TEXT("Notifications"),TEXT("Info"),false,FVector2D(0.35f, 0.12f));

	// Racing
	Add(TEXT("speed_display"), TEXT("Speedometer"),   TEXT("Racing"), false, FVector2D(0.82f, 0.8f));
	Add(TEXT("gear_indicator"),TEXT("Gear"),           TEXT("Racing"), false, FVector2D(0.48f, 0.85f));
	Add(TEXT("lap_counter"),   TEXT("Lap Counter"),   TEXT("Racing"), false, FVector2D(0.02f, 0.03f));
	Add(TEXT("position_display"),TEXT("Position"),     TEXT("Racing"), false, FVector2D(0.88f, 0.03f));
}

// ── Actions ─────────────────────────────────────────────────

FReply SArcwrightUIBuilderPanel::OnRandomizeClicked()
{
	// Random theme
	int32 Idx = FMath::RandRange(0, ThemeOptions.Num() - 1);
	SelectedTheme = ThemeOptions[Idx];
	LoadThemeColors(*SelectedTheme);

	// Slight color variation
	PrimaryColor.R += FMath::FRandRange(-0.1f, 0.1f);
	PrimaryColor.G += FMath::FRandRange(-0.1f, 0.1f);

	// Random 4-6 components
	for (auto& C : Components) C.bEnabled = false;
	// Always enable health + crosshair
	if (Components.Num() > 0) Components[0].bEnabled = true;  // health
	if (Components.Num() > 2) Components[2].bEnabled = true;  // crosshair

	int32 Extra = FMath::RandRange(2, 4);
	TArray<int32> Candidates;
	for (int32 i = 0; i < Components.Num(); i++)
		if (!Components[i].bEnabled) Candidates.Add(i);

	for (int32 i = 0; i < FMath::Min(Extra, Candidates.Num()); i++)
	{
		int32 Pick = FMath::RandRange(0, Candidates.Num() - 1);
		Components[Candidates[Pick]].bEnabled = true;
		Candidates.RemoveAt(Pick);
	}

	StatusMessage = FString::Printf(TEXT("Randomized: %s theme, %d components"),
		*(*SelectedTheme), Components.FilterByPredicate([](const FComponentEntry& C) { return C.bEnabled; }).Num());

	Invalidate(EInvalidateWidgetReason::Paint);
	return FReply::Handled();
}

FReply SArcwrightUIBuilderPanel::OnGenerateClicked()
{
	// Build DSL from current settings
	FString DSL;
	DSL += FString::Printf(TEXT("WIDGET: WBP_GameHUD\nTHEME: %s\n\nCANVAS Root\n"), *(*SelectedTheme));

	for (const auto& C : Components)
	{
		if (!C.bEnabled) continue;
		// Map component to widget type
		FString WType = TEXT("TEXT");
		if (C.Id.Contains(TEXT("bar")) || C.Id.Contains(TEXT("stamina"))) WType = TEXT("PROGRESS_BAR");
		else if (C.Id == TEXT("minimap") || C.Id == TEXT("damage_indicator")) WType = TEXT("IMAGE");

		FString Anchor = TEXT("TopLeft");
		if (C.AnchorPos.X > 0.7f && C.AnchorPos.Y < 0.3f) Anchor = TEXT("TopRight");
		else if (C.AnchorPos.X > 0.3f && C.AnchorPos.X < 0.7f && C.AnchorPos.Y < 0.3f) Anchor = TEXT("TopCenter");
		else if (C.AnchorPos.X > 0.3f && C.AnchorPos.X < 0.7f && C.AnchorPos.Y > 0.3f) Anchor = TEXT("Center");
		else if (C.AnchorPos.X > 0.7f && C.AnchorPos.Y > 0.7f) Anchor = TEXT("BottomRight");
		else if (C.AnchorPos.X > 0.3f && C.AnchorPos.Y > 0.7f) Anchor = TEXT("BottomCenter");

		DSL += FString::Printf(TEXT("  %s %s\n    @anchor: %s\n"), *WType, *C.Name.Replace(TEXT(" "), TEXT("")), *Anchor);
	}

	// Copy to clipboard for now
	FPlatformApplicationMisc::ClipboardCopy(*DSL);
	StatusMessage = FString::Printf(TEXT("DSL generated (%d components) and copied to clipboard. Use create_widget_from_dsl to build in UE."),
		Components.FilterByPredicate([](const FComponentEntry& C) { return C.bEnabled; }).Num());

	return FReply::Handled();
}

FReply SArcwrightUIBuilderPanel::OnExportDSLClicked()
{
	// Same as generate but just copy
	OnGenerateClicked();
	StatusMessage = TEXT("Widget DSL exported to clipboard.");
	return FReply::Handled();
}

#undef LOCTEXT_NAMESPACE
