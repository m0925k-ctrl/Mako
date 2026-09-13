Attribute VB_Name = "Mapping"
Option Explicit

' =============================================================================
' Mapping
'
' 「どのカラム（社内サーバー由来の取得値）を、どのセルに、どんな加工で見せるか」を
' コードに直書きせず、Excel シート上の表で管理するためのモジュール。
' 併せて「どのボタンにどのマクロを割り当てるか」もシートで管理できる。
'
' バックエンドは従来どおり社内サーバー（ODBC）から取得する。本モジュールは
' 取得済みデータ（CTSQ-DATA / ACROS-DATA / WORK-HISTORY シート）の
' "割り付け・表示" だけをデータ駆動にする。
'
'   SetupAll           : マッピング表・ボタン設定表を作成し、ボタンも配置（初回セットアップ）
'   SetupMappingSheet  : 「マッピング」シートを作成し、現行の割り付けを初期投入
'   ApplyMapping       : 「マッピング」シートに従って各セルへ値を割り付け（DataPutin の後継）
'   SetupButtonSheet   : 「ボタン設定」シートを作成し、標準のボタン割り当てを初期投入
'   SetupButtons       : 「ボタン設定」シートに従ってワークシート上にボタンを配置
'
' 【加工（TRANSFORM 列）】
'   RAW    … そのまま
'   QUOTE  … 先頭に ' を付与（電話番号など 0 始まりの文字列固定用）
'   SC     … サービスセンタ名を SC 名へ変換（例: 「○○サービスセンタ」→「○○SC」、「沖メ」は例外）
'   LEFT7  … 先頭 7 文字を抜き出し（サイトID など）
'   REP    … 代表連絡先フォーマット（"代表：" & 値 & "　内線：　直通："）
'
' 【参照方法（METHOD 列）】
'   CELL   … ソースシートのセル番地を直接指定（例: B54）。※現行 DataPutin と同じ挙動
'   NAME   … ソースシート A 列の「項目名」で検索し、隣の B 列の値を取得（列位置に依存せず堅牢）
' =============================================================================

Private Const MAP_SHEET As String = "マッピング"
Private Const BTN_SHEET As String = "ボタン設定"

' =============================================================================
' 初回セットアップ
' =============================================================================
Public Sub SetupAll()
    SetupMappingSheet
    SetupButtonSheet
    SetupButtons
    MsgBox "セットアップ完了。" & vbCrLf & _
           "・「" & MAP_SHEET & "」シートで割り付けを編集できます。" & vbCrLf & _
           "・「" & BTN_SHEET & "」シートでボタンとマクロの対応を編集できます。", vbInformation
End Sub

' =============================================================================
' マッピングシートの作成と初期投入
' =============================================================================
Public Sub SetupMappingSheet()
    Dim ws As Worksheet
    Dim r As Long

    Set ws = EnsureSheet(MAP_SHEET)
    ws.Cells.Clear

    ' ヘッダ
    ws.Range("A1:G1").value = Array( _
        "出力先シート", "出力先セル", "ソースシート", "参照方法", "参照キー", "加工", "備考")
    ws.Range("A1:G1").Font.Bold = True

    ' 現行 DataPutin の割り付けを初期値として投入（参照方法=CELL で挙動を再現）
    r = 2
    r = AddMap(ws, r, "メール作成", "D10", "CTSQ-DATA", "CELL", "B54", "RAW", "施設名")
    r = AddMap(ws, r, "メール作成", "D11", "CTSQ-DATA", "CELL", "B56", "SC", "担当SC")
    r = AddMap(ws, r, "メール作成", "D12", "CTSQ-DATA", "CELL", "B35", "LEFT7", "サイトID(7桁)")
    r = AddMap(ws, r, "メール作成", "D13", "CTSQ-DATA", "CELL", "B36", "QUOTE", "ユニットID")
    r = AddMap(ws, r, "メール作成", "D14", "CTSQ-DATA", "CELL", "B42", "RAW", "")
    r = AddMap(ws, r, "メール作成", "D15", "CTSQ-DATA", "CELL", "B74", "RAW", "")
    r = AddMap(ws, r, "メール作成", "D17", "CTSQ-DATA", "CELL", "B33", "RAW", "")
    r = AddMap(ws, r, "メール作成", "D18", "CTSQ-DATA", "CELL", "B2", "RAW", "機種")
    r = AddMap(ws, r, "メール作成", "D20", "ACROS-DATA", "CELL", "B38", "RAW", "")
    r = AddMap(ws, r, "メール作成", "D23", "CTSQ-DATA", "CELL", "B42", "RAW", "")
    r = AddMap(ws, r, "メール作成", "D24", "CTSQ-DATA", "CELL", "B38", "RAW", "")
    r = AddMap(ws, r, "メール作成", "D26", "CTSQ-DATA", "CELL", "B74", "RAW", "")
    r = AddMap(ws, r, "メール作成", "D27", "CTSQ-DATA", "CELL", "B75", "QUOTE", "")
    r = AddMap(ws, r, "メール作成", "D28", "CTSQ-DATA", "CELL", "B78", "RAW", "")
    r = AddMap(ws, r, "メール作成", "D30", "CTSQ-DATA", "CELL", "B49", "REP", "代表連絡先")
    r = AddMap(ws, r, "メール作成", "D32", "CTSQ-DATA", "CELL", "B113", "QUOTE", "")
    r = AddMap(ws, r, "メール作成", "D33", "CTSQ-DATA", "CELL", "B115", "QUOTE", "")
    r = AddMap(ws, r, "メール作成", "D34", "CTSQ-DATA", "CELL", "B117", "QUOTE", "")

    ws.columns("A:G").AutoFit
End Sub

Private Function AddMap(ByVal ws As Worksheet, ByVal r As Long, _
        ByVal outSheet As String, ByVal outCell As String, ByVal srcSheet As String, _
        ByVal method As String, ByVal key As String, ByVal transform As String, _
        ByVal note As String) As Long
    ws.Cells(r, 1).value = outSheet
    ws.Cells(r, 2).value = outCell
    ws.Cells(r, 3).value = srcSheet
    ws.Cells(r, 4).value = method
    ws.Cells(r, 5).value = "'" & key   ' "B54" などが日付/数式に化けないよう文字列固定
    ws.Cells(r, 6).value = transform
    ws.Cells(r, 7).value = note
    AddMap = r + 1
End Function

' =============================================================================
' マッピングの適用（DataPutin のデータ駆動版）
' =============================================================================
Public Sub ApplyMapping()
    Dim wsMap As Worksheet
    Dim lastRow As Long
    Dim r As Long
    Dim outSheet As String, outCell As String, srcSheet As String
    Dim method As String, key As String, transform As String
    Dim rawVal As String
    Dim outVal As String
    Dim appliedCount As Long

    On Error Resume Next
    Set wsMap = ThisWorkbook.Sheets(MAP_SHEET)
    On Error GoTo 0
    If wsMap Is Nothing Then
        MsgBox "「" & MAP_SHEET & "」シートがありません。先に SetupMappingSheet を実行してください。", vbExclamation
        Exit Sub
    End If

    lastRow = wsMap.Cells(wsMap.Rows.Count, 1).End(-4162).Row ' xlUp
    For r = 2 To lastRow
        outSheet = Trim(CStr(wsMap.Cells(r, 1).value))
        outCell = Trim(CStr(wsMap.Cells(r, 2).value))
        srcSheet = Trim(CStr(wsMap.Cells(r, 3).value))
        method = UCase(Trim(CStr(wsMap.Cells(r, 4).value)))
        key = StripLeadingQuote(wsMap.Cells(r, 5).value)
        transform = UCase(Trim(CStr(wsMap.Cells(r, 6).value)))

        If Len(outSheet) = 0 Or Len(outCell) = 0 Or Len(srcSheet) = 0 Or Len(key) = 0 Then
            GoTo ContinueLoop
        End If

        rawVal = LookupValue(srcSheet, method, key)
        outVal = ApplyTransform(rawVal, transform)

        On Error Resume Next
        ThisWorkbook.Sheets(outSheet).Range(outCell).value = outVal
        On Error GoTo 0
        appliedCount = appliedCount + 1
ContinueLoop:
    Next r
End Sub

' ソースから値を取得（CELL=セル番地 / NAME=A列の項目名で検索してB列を返す）
Private Function LookupValue(ByVal srcSheet As String, ByVal method As String, _
        ByVal key As String) As String
    Dim ws As Worksheet
    Dim lastRow As Long, i As Long

    On Error Resume Next
    Set ws = ThisWorkbook.Sheets(srcSheet)
    On Error GoTo 0
    If ws Is Nothing Then Exit Function

    If method = "NAME" Then
        lastRow = ws.Cells(ws.Rows.Count, 1).End(-4162).Row ' xlUp
        For i = 1 To lastRow
            If StripLeadingQuote(ws.Cells(i, 1).value) = key Then
                LookupValue = StripLeadingQuote(ws.Cells(i, 2).value)
                Exit Function
            End If
        Next i
        LookupValue = ""   ' 見つからなければ空
    Else
        ' 既定は CELL
        On Error Resume Next
        LookupValue = StripLeadingQuote(ws.Range(key).value)
        On Error GoTo 0
    End If
End Function

' 加工の適用
Private Function ApplyTransform(ByVal v As String, ByVal transform As String) As String
    Select Case transform
        Case "QUOTE"
            ApplyTransform = "'" & v
        Case "SC"
            If v = "沖メ" Then
                ApplyTransform = "沖メ"
            ElseIf Len(v) > 7 Then
                ApplyTransform = Left(v, Len(v) - 7) & "SC"
            Else
                ApplyTransform = v
            End If
        Case "LEFT7"
            ApplyTransform = Left(v, 7)
        Case "REP"
            ApplyTransform = "代表：" & v & "　内線：　直通："
        Case Else   ' RAW / 空
            ApplyTransform = v
    End Select
End Function

' =============================================================================
' ボタン設定シートの作成と初期投入
' =============================================================================
Public Sub SetupButtonSheet()
    Dim ws As Worksheet
    Dim r As Long

    Set ws = EnsureSheet(BTN_SHEET)
    ws.Cells.Clear

    ws.Range("A1:F1").value = Array( _
        "配置シート", "ラベル", "マクロ名", "左(pt)", "上(pt)", "幅(pt)")
    ws.Range("A1:F1").Font.Bold = True

    r = 2
    r = AddBtn(ws, r, "メール作成", "受付→CE指示 実行", "MakeCEInstruction", 10, 10, 160)
    r = AddBtn(ws, r, "メール作成", "データ取得のみ", "GetCaseData", 10, 40, 160)
    r = AddBtn(ws, r, "メール作成", "マッピング反映", "ApplyMapping", 10, 70, 160)
    r = AddBtn(ws, r, "メール作成", "取得データ クリア", "ClearGetData", 10, 100, 160)

    ws.columns("A:F").AutoFit
End Sub

Private Function AddBtn(ByVal ws As Worksheet, ByVal r As Long, ByVal placeSheet As String, _
        ByVal label As String, ByVal macroName As String, _
        ByVal leftPt As Double, ByVal topPt As Double, ByVal widthPt As Double) As Long
    ws.Cells(r, 1).value = placeSheet
    ws.Cells(r, 2).value = label
    ws.Cells(r, 3).value = macroName
    ws.Cells(r, 4).value = leftPt
    ws.Cells(r, 5).value = topPt
    ws.Cells(r, 6).value = widthPt
    AddBtn = r + 1
End Function

' =============================================================================
' ボタン設定シートに従ってボタンを配置（再実行時は既存ボタンを作り直す）
' =============================================================================
Public Sub SetupButtons()
    Dim wsBtn As Worksheet
    Dim ws As Worksheet
    Dim lastRow As Long, r As Long
    Dim placeSheet As String, label As String, macroName As String
    Dim leftPt As Double, topPt As Double, widthPt As Double
    Dim btn As Object
    Dim clearedSheets As String

    On Error Resume Next
    Set wsBtn = ThisWorkbook.Sheets(BTN_SHEET)
    On Error GoTo 0
    If wsBtn Is Nothing Then
        MsgBox "「" & BTN_SHEET & "」シートがありません。先に SetupButtonSheet を実行してください。", vbExclamation
        Exit Sub
    End If

    lastRow = wsBtn.Cells(wsBtn.Rows.Count, 1).End(-4162).Row ' xlUp
    clearedSheets = "|"

    For r = 2 To lastRow
        placeSheet = Trim(CStr(wsBtn.Cells(r, 1).value))
        label = Trim(CStr(wsBtn.Cells(r, 2).value))
        macroName = Trim(CStr(wsBtn.Cells(r, 3).value))
        If Len(placeSheet) = 0 Or Len(label) = 0 Or Len(macroName) = 0 Then GoTo ContinueBtn

        Set ws = Nothing
        On Error Resume Next
        Set ws = ThisWorkbook.Sheets(placeSheet)
        On Error GoTo 0
        If ws Is Nothing Then GoTo ContinueBtn

        ' そのシートを初めて処理するとき、既存のフォームボタンを一旦削除（重複防止）
        If InStr(clearedSheets, "|" & placeSheet & "|") = 0 Then
            ws.Buttons.Delete
            clearedSheets = clearedSheets & placeSheet & "|"
        End If

        leftPt = ValOrDefault(wsBtn.Cells(r, 4).value, 10)
        topPt = ValOrDefault(wsBtn.Cells(r, 5).value, 10)
        widthPt = ValOrDefault(wsBtn.Cells(r, 6).value, 160)

        Set btn = ws.Buttons.Add(leftPt, topPt, widthPt, 24)
        btn.Caption = label
        btn.OnAction = macroName
ContinueBtn:
    Next r
End Sub

' =============================================================================
' 補助関数
' =============================================================================
Private Function ValOrDefault(ByVal v As Variant, ByVal dflt As Double) As Double
    If IsNumeric(v) Then
        ValOrDefault = CDbl(v)
    Else
        ValOrDefault = dflt
    End If
End Function

Private Function StripLeadingQuote(ByVal s As Variant) As String
    Dim t As String
    t = CStr(s)
    If Left(t, 1) = "'" Then t = Mid(t, 2)
    StripLeadingQuote = t
End Function

Private Function EnsureSheet(ByVal sheetName As String) As Worksheet
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets(sheetName)
    On Error GoTo 0
    If ws Is Nothing Then
        Set ws = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.Count))
        ws.Name = sheetName
    End If
    Set EnsureSheet = ws
End Function
