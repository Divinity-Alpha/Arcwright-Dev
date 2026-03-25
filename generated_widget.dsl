WIDGET: WBP_EngineHUD
THEME: Industrial

CANVAS Root
  PROGRESS_BAR HealthBar
    @anchor: TopLeft
    @offset_x: 20
    @offset_y: 20
    @percent: BIND:EngineHealth/EngineMaxHealth
    @fill_color: $health
    @size_x: 250
    @size_y: 16
  TEXT CashText
    @anchor: TopLeft
    @offset_x: 20
    @offset_y: 50
    @text: BIND:"Cash: {CashAmount}"
    @font_size: 14
    @color: $warning
  TEXT DayText
    @anchor: TopLeft
    @offset_x: 20
    @offset_y: 80
    @text: BIND:"Day: {DayNumber}"
    @font_size: 14
    @color: $text
  TEXT StatusText
    @anchor: TopLeft
    @offset_x: 20
    @offset_y: 110
    @text: BIND:"{StatusMessage}"
    @font_size: 12
    @color: $text_muted