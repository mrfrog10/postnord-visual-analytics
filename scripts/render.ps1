param([string]$Twbx, [string]$Png, [int]$Wait = 25)
# Opens one workbook in Tableau Desktop, shows it in presentation mode (F7), saves a screenshot, closes that window only.
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class W2 { [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h); [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int c); [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); [DllImport("user32.dll")] public static extern void keybd_event(byte k,byte s,int f,int e);}
"@
[W2]::SetProcessDPIAware() | Out-Null
$old = @(Get-Process tableau -ErrorAction SilentlyContinue | ForEach-Object Id)
Start-Process "C:\Program Files\Tableau\Tableau 2026.3\bin\tableau.exe" -ArgumentList "`"$Twbx`""
$p = $null; $t = 0
while ($t -lt 120) {
    Start-Sleep 3; $t += 3
    $p = Get-Process tableau -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 -and $old -notcontains $_.Id -and $_.MainWindowTitle -match 'Tableau - ' } | Select-Object -First 1
    if ($p) { break }
}
if (-not $p) { "no window"; exit 1 }
Start-Sleep $Wait
[W2]::keybd_event(0x12, 0, 0, 0); [W2]::ShowWindow($p.MainWindowHandle, 3) | Out-Null; [W2]::SetForegroundWindow($p.MainWindowHandle) | Out-Null; [W2]::keybd_event(0x12, 0, 2, 0)
Start-Sleep 2
[System.Windows.Forms.SendKeys]::SendWait("{F7}")
Start-Sleep 6
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
$g = [System.Drawing.Graphics]::FromImage($bmp); $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size); $bmp.Save($Png); $g.Dispose(); $bmp.Dispose()
[System.Windows.Forms.SendKeys]::SendWait("{ESC}")
Start-Sleep 1
$p.CloseMainWindow() | Out-Null
Start-Sleep 4
if (-not $p.HasExited) { [System.Windows.Forms.SendKeys]::SendWait("n"); Start-Sleep 2 }
"saved $Png"
