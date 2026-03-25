Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$primary = [System.Windows.Forms.Screen]::PrimaryScreen
$width = $primary.Bounds.Width
$height = $primary.Bounds.Height

$bitmap = New-Object System.Drawing.Bitmap($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($primary.Bounds.Location, [System.Drawing.Point]::Empty, $primary.Bounds.Size)

$bitmap.Save('C:\Arcwright\screenshots\editor_panel\full_screen.png', [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
Write-Output "Screenshot saved to C:\Arcwright\screenshots\editor_panel\full_screen.png"
