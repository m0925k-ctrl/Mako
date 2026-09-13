Attribute VB_Name = "Console"
Option Explicit

' =============================================================================
' Console
'
' オペレータが「受付 → 情報確認 → 掲示板 → CE 指示（ディスパッチ）」までを
' 1 画面の流れで操作できるコンソールを構築するモジュール。
'
' 画面はワークシート・タブで切り替える構成:
'   コンソール      … ステップ①〜④のボタンと CASE_ID 入力を集約したホーム画面
'   CTSQ-DATA       … 受付データ（CTSQ）
'   ACROS-DATA      … 構成情報（ACROS）
'   WORK-HISTORY    … 作業履歴（バックエンド = ACROS EUC を想定）
'   メール作成      … CE 作業指示の編集面
'
' 各シート上部に「コンソールへ戻る」ナビを置き、コンソール上部にはタブ切り替え
' （各シートへジャンプ）を並べる。
'
'   BuildConsole    : コンソールと各タブ・ナビ・ボタンを構築（初回セットアップ）
'   Console_RunAll  : ①〜④を一括実行（CASE_ID 取得〜CE 指示メール作成）
'   Console_Receive : ①受付（コンソールの CASE_ID を取得して GetCaseData）
'
' ※ バックエンドの取得（社内サーバー / ODBC）は既存モジュールのまま。本モジュールは
'   その "操作導線（コンソール）" を用意する。
' =============================================================================

Private Const CONSOLE_SHEET As String = "コンソール"
Private Const CASEID_CELL As String = "C4"      ' コンソール上の CASE_ID 入力セル
Private Const NAV_RETURN As String = "▲ コンソールへ戻る"

' タブ切り替え対象（存在するものだけボタン化）
Private Function TabSheets() As Variant
    TabSheets = Array("コンソール", "CTSQ-DATA", "ACROS-DATA", "WORK-HISTORY", "メール作成")
End Function

' =============================================================================
' コンソール構築
' =============================================================================
Public Sub BuildConsole()
    Dim ws As Worksheet
    Dim tabs As Variant
    Dim i As Long
    Dim x As Double

    Set ws = EnsureSheet(CONSOLE_SHEET)
    ThisWorkbook.Sheets(CONSOLE_SHEET).Move Before:=ThisWorkbook.Sheets(1)  ' 先頭タブへ

    ' --- 見た目を整える ---
    ws.Cells.Clear
    RemoveOurButtons ws
    On Error Resume Next
    ThisWorkbook.Windows(1).DisplayGridlines = False
    On Error GoTo 0

    ws.Range("B2").value = "CSC 受付 → CE ディスパッチ コンソール"
    ws.Range("B2").Font.Size = 16
    ws.Range("B2").Font.Bold = True

    ' --- 上部タブ（各シートへジャンプ） ---
    tabs = TabSheets()
    x = PointsOfColumn(ws, 2)   ' B 列の左端
    For i = LBound(tabs) To UBound(tabs)
        If SheetExists(CStr(tabs(i))) Then
            AddNavButton ws, x, PointsOfRow(ws, 4), 110, 22, CStr(tabs(i)), CStr(tabs(i))
            x = x + 116
        End If
    Next i

    ' --- ① 受付 ---
    ws.Range("B7").value = "① 受付"
    ws.Range("B7").Font.Bold = True
    ws.Range("B8").value = "CASE_ID:"
    ws.Range(CASEID_CELL).value = ""          ' 入力欄
    ws.Range(CASEID_CELL).NumberFormat = "@"  ' 文字列として保持
    ws.Range(CASEID_CELL).Interior.Color = RGB(255, 255, 204)
    AddMacroButton ws, "E7", 180, 24, "① 受付データ取得", "Console_Receive"

    ' --- ② 情報確認 ---
    ws.Range("B11").value = "② 情報確認"
    ws.Range("B11").Font.Bold = True
    AddMacroButton ws, "B12", 180, 24, "作業履歴を取得", "GetWorkHistory"
    AddMacroButton ws, "E12", 180, 24, "マッピング反映", "ApplyMapping"

    ' --- ③ 掲示板 ---
    ws.Range("B15").value = "③ 掲示板（社内Web）"
    ws.Range("B15").Font.Bold = True
    AddMacroButton ws, "B16", 180, 24, "掲示板を開く", "OpenBulletinBoards"

    ' --- ④ CE 指示（ディスパッチ） ---
    ws.Range("B19").value = "④ CE 指示（ディスパッチ）"
    ws.Range("B19").Font.Bold = True
    AddMacroButton ws, "B20", 220, 24, "CE 指示メールを作成", "CreateCEInstructionMail"

    ' --- 一括実行 ---
    ws.Range("B23").value = "▼ まとめて実行"
    ws.Range("B23").Font.Bold = True
    AddMacroButton ws, "B24", 260, 28, "① → ④ 一括実行", "Console_RunAll"

    ws.columns("B:E").ColumnWidth = 22

    ' --- 各シートに「コンソールへ戻る」ナビを付与 ---
    For i = LBound(tabs) To UBound(tabs)
        If CStr(tabs(i)) <> CONSOLE_SHEET And SheetExists(CStr(tabs(i))) Then
            AddReturnNav ThisWorkbook.Sheets(CStr(tabs(i)))
        End If
    Next i

    ws.Activate
    ws.Range(CASEID_CELL).Select
    MsgBox "コンソールを構築しました。上部タブで画面を切り替えられます。", vbInformation
End Sub

' =============================================================================
' ① 受付：コンソールの CASE_ID を「メール作成」D4 へ渡して取得
' =============================================================================
Public Sub Console_Receive()
    Dim caseID As String
    caseID = Trim(CStr(ThisWorkbook.Sheets(CONSOLE_SHEET).Range(CASEID_CELL).value))
    If Len(caseID) = 0 Then
        MsgBox "CASE_ID を入力してください（" & CONSOLE_SHEET & " の " & CASEID_CELL & "）。", vbExclamation
        Exit Sub
    End If
    ThisWorkbook.Sheets("メール作成").Range("D4").value = caseID
    GetCaseData   ' CTSQ/ACROS 取得 + 割り付け
End Sub

' =============================================================================
' ①〜④ 一括実行
' =============================================================================
Public Sub Console_RunAll()
    Console_Receive
    GetWorkHistory
    OpenBulletinBoards
    CreateCEInstructionMail
End Sub

' =============================================================================
' ナビゲーション
' =============================================================================
Public Sub GotoSheet(ByVal sheetName As String)
    On Error Resume Next
    ThisWorkbook.Sheets(sheetName).Activate
    On Error GoTo 0
End Sub

Private Sub AddReturnNav(ByVal ws As Worksheet)
    RemoveButtonsByCaption ws, NAV_RETURN
    Dim btn As Object
    Set btn = ws.Buttons.Add(4, 4, 160, 20)
    btn.Caption = NAV_RETURN
    btn.OnAction = "'GotoSheet """ & CONSOLE_SHEET & """'"
End Sub

Private Sub AddNavButton(ByVal ws As Worksheet, ByVal leftPt As Double, ByVal topPt As Double, _
        ByVal w As Double, ByVal h As Double, ByVal caption As String, ByVal targetSheet As String)
    Dim btn As Object
    Set btn = ws.Buttons.Add(leftPt, topPt, w, h)
    btn.Caption = caption
    btn.OnAction = "'GotoSheet """ & targetSheet & """'"
End Sub

' =============================================================================
' ボタン配置補助（セル位置に配置）
' =============================================================================
Private Sub AddMacroButton(ByVal ws As Worksheet, ByVal anchorCell As String, _
        ByVal w As Double, ByVal h As Double, ByVal caption As String, ByVal macroName As String)
    Dim btn As Object
    Dim rng As Range
    Set rng = ws.Range(anchorCell)
    Set btn = ws.Buttons.Add(rng.Left, rng.Top, w, h)
    btn.Caption = caption
    btn.OnAction = macroName
End Sub

Private Function PointsOfColumn(ByVal ws As Worksheet, ByVal col As Long) As Double
    PointsOfColumn = ws.Cells(1, col).Left
End Function

Private Function PointsOfRow(ByVal ws As Worksheet, ByVal row As Long) As Double
    PointsOfRow = ws.Cells(row, 1).Top
End Function

' =============================================================================
' 補助関数
' =============================================================================
Private Function SheetExists(ByVal sheetName As String) As Boolean
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets(sheetName)
    On Error GoTo 0
    SheetExists = Not (ws Is Nothing)
End Function

' コンソール自身のボタン（ジャンプ / マクロ）を全消し。ユーザー作成ボタンは
' 別シートにあるため影響しない（コンソールは本モジュール専用シート）。
Private Sub RemoveOurButtons(ByVal ws As Worksheet)
    On Error Resume Next
    ws.Buttons.Delete
    On Error GoTo 0
End Sub

' 指定キャプションのボタンだけ削除（他シートのユーザーボタンを壊さないため）
Private Sub RemoveButtonsByCaption(ByVal ws As Worksheet, ByVal caption As String)
    Dim b As Object
    On Error Resume Next
    For Each b In ws.Buttons
        If b.Caption = caption Then b.Delete
    Next b
    On Error GoTo 0
End Sub

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
