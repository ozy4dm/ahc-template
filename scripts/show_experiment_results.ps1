param(
    [string]$CsvPath = "reports/experiment_results.csv",
    [switch]$NoCsv
)

$ErrorActionPreference = "Stop"
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$experimentDir = Join-Path $repoRoot "docs\experiments"

function Get-Field {
    param([string]$Text, [string]$Label)

    $pattern = "(?m)^-\s+" + [regex]::Escape($Label) + ":\s*(.*)$"
    $match = [regex]::Match($Text, $pattern)
    if (-not $match.Success) { return $null }
    return $match.Groups[1].Value.Trim().Trim('`')
}

function Get-NumberPair {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) { return @($null, $null) }
    $matches = [regex]::Matches($Value, "-?\d+(?:\.\d+)?")
    if ($matches.Count -lt 2) { return @($null, $null) }
    return @(
        [double]::Parse($matches[0].Value, [Globalization.CultureInfo]::InvariantCulture),
        [double]::Parse($matches[1].Value, [Globalization.CultureInfo]::InvariantCulture)
    )
}

function Get-IntegerPair {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) { return @($null, $null) }
    $matches = [regex]::Matches($Value, "\d+")
    if ($matches.Count -lt 2) { return @($null, $null) }
    return @([int]$matches[0].Value, [int]$matches[1].Value)
}

$rows = foreach ($file in Get-ChildItem $experimentDir -Filter "EXP-*.md" | Sort-Object Name) {
    $text = Get-Content $file.FullName -Raw -Encoding UTF8
    $heading = [regex]::Match($text, "(?m)^#\s+(EXP-\d+):\s*(.+)$")
    if (-not $heading.Success) { continue }

    $scoreBase, $scoreCandidate = Get-NumberPair (Get-Field $text "baseline 平均 / 中央値")
    $candidateMean, $candidateMedian = Get-NumberPair (Get-Field $text "candidate 平均 / 中央値")
    $scoreMean = $scoreBase
    $scoreMedian = $scoreCandidate
    $changeImproved, $changeEqual = Get-IntegerPair (Get-Field $text "改善 / 同等 / 悪化ケース数")
    $changeValue = Get-Field $text "改善 / 同等 / 悪化ケース数"
    $changeMatches = if ($changeValue) { [regex]::Matches($changeValue, "\d+") } else { @() }
    $changeWorse = if ($changeMatches.Count -ge 3) { [int]$changeMatches[2].Value } else { $null }

    $successValue = Get-Field $text "成功ケース数"
    $failureValue = Get-Field $text "失敗ケース数"
    $successMatches = if ($successValue) { [regex]::Matches($successValue, "\d+") } else { @() }
    $failureMatches = if ($failureValue) { [regex]::Matches($failureValue, "\d+") } else { @() }

    $runtime = Get-Field $text "実行時間"
    $runtimeMatch = if ($runtime) {
        [regex]::Match($runtime, "baseline平均\s*([0-9.]+)ms・最大\s*([0-9.]+)ms、candidate平均\s*([0-9.]+)ms・最大\s*([0-9.]+)ms")
    } else {
        $null
    }

    $improvementPct = if ($null -ne $scoreMean -and $scoreMean -ne 0 -and $null -ne $candidateMean) {
        [math]::Round((($scoreMean - $candidateMean) / $scoreMean) * 100, 3)
    } else {
        $null
    }

    $relativeSource = "docs/experiments/" + $file.Name
    [pscustomobject][ordered]@{
        "実験ID" = $heading.Groups[1].Value
        "実験名" = $heading.Groups[2].Value.Trim()
        "状態" = Get-Field $text "状態"
        "作成日" = Get-Field $text "作成日"
        "実行日時" = Get-Field $text "実行日時"
        "baseline" = Get-Field $text "baseline solution ID"
        "candidate" = Get-Field $text "candidate solution ID"
        "baseline成功" = if ($successMatches.Count -ge 2) { [int]$successMatches[0].Value } elseif ($successMatches.Count -eq 1) { [int]$successMatches[0].Value } else { $null }
        "candidate成功" = if ($successMatches.Count -ge 2) { [int]$successMatches[1].Value } elseif ($successMatches.Count -eq 1) { [int]$successMatches[0].Value } else { $null }
        "baseline失敗" = if ($failureMatches.Count -ge 2) { [int]$failureMatches[0].Value } else { $null }
        "candidate失敗" = if ($failureMatches.Count -ge 2) { [int]$failureMatches[1].Value } elseif ($failureMatches.Count -eq 1) { [int]$failureMatches[0].Value } else { $null }
        "baseline平均" = $scoreMean
        "candidate平均" = $candidateMean
        "平均改善率_pct" = $improvementPct
        "baseline中央値" = $scoreMedian
        "candidate中央値" = $candidateMedian
        "改善" = $changeImproved
        "同等" = $changeEqual
        "悪化" = $changeWorse
        "baseline平均ms" = if ($runtimeMatch -and $runtimeMatch.Success) { [double]$runtimeMatch.Groups[1].Value } else { $null }
        "baseline最大ms" = if ($runtimeMatch -and $runtimeMatch.Success) { [double]$runtimeMatch.Groups[2].Value } else { $null }
        "candidate平均ms" = if ($runtimeMatch -and $runtimeMatch.Success) { [double]$runtimeMatch.Groups[3].Value } else { $null }
        "candidate最大ms" = if ($runtimeMatch -and $runtimeMatch.Success) { [double]$runtimeMatch.Groups[4].Value } else { $null }
        "実行時間記録" = $runtime
        "判断" = Get-Field $text "判断"
        "理由" = Get-Field $text "理由"
        "記録ファイル" = $relativeSource
    }
}

$displayRows = foreach ($row in $rows) {
    $mean = if ($null -ne $row."baseline平均" -and $null -ne $row."candidate平均") {
        "{0:N2} -> {1:N2}" -f $row."baseline平均", $row."candidate平均"
    } else {
        "-"
    }
    $rate = if ($null -ne $row."平均改善率_pct") { "{0:N3}%" -f $row."平均改善率_pct" } else { "-" }
    $changes = if ($null -ne $row."改善") { "{0}/{1}/{2}" -f $row."改善", $row."同等", $row."悪化" } else { "-" }
    $candidateTime = if ($null -ne $row."candidate平均ms") {
        "{0:N1}/{1:N1}" -f $row."candidate平均ms", $row."candidate最大ms"
    } else {
        "-"
    }

    [pscustomobject][ordered]@{
        "実験" = $row."実験ID"
        "比較" = "{0} -> {1}" -f $row.baseline, $row.candidate
        "平均スコア" = $mean
        "改善率" = $rate
        "改善/同等/悪化" = $changes
        "候補ms 平均/最大" = $candidateTime
        "判断" = $row."判断"
    }
}

$displayRows | Format-Table -AutoSize

if (-not $NoCsv) {
    $outputPath = if ([IO.Path]::IsPathRooted($CsvPath)) {
        [IO.Path]::GetFullPath($CsvPath)
    } else {
        [IO.Path]::GetFullPath((Join-Path $repoRoot $CsvPath))
    }
    $outputDir = Split-Path $outputPath -Parent
    [void][IO.Directory]::CreateDirectory($outputDir)
    $csv = $rows | ConvertTo-Csv -NoTypeInformation
    [IO.File]::WriteAllText($outputPath, ($csv -join "`r`n") + "`r`n", [Text.UTF8Encoding]::new($true))
    Write-Host "CSVを更新しました: $outputPath"
}
