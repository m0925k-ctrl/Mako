Attribute VB_Name = "Console"
Option Explicit

' =============================================================================
' Console  （ダークモード / 疲れにくい配色）
'
' オペレータが「受付 → 情報確認 → 掲示板 → CE 指示（ディスパッチ）」までを
' 1 画面の流れで操作できるコンソールを、眼精疲労を抑えたダークテーマで構築する。
'
' 【配色の根拠（ダークモードの疲労低減）】
'   ・純黒 × 純白を避ける（高コントラストは光のにじみ・残像で疲れる）。
'     背景 = 濃いグレー、文字 = やや暖色のオフホワイト。
'   ・ブルーライトを抑えるため文字・アクセントを暖色寄りに。
'   ・アクセントは 1 系統（ティール）＋実行系は暖色アンバーの 1 点のみ。
'   ・十分な余白・番号付きの明快なステップで視線移動を減らす。
'   ・日本語は丸ゴシック（Yu Gothic UI / Meiryo）で可読性を確保。
'   ・Excel のフォームボタンは配色不可のため、角丸シェイプをボタン化して配色。
'
'   BuildConsole    : コンソールとタブ・ナビ・ボタンをダークテーマで構築
'   ApplyDarkTheme  : 既存の各シートにもダークテーマを適用
'   Console_Receive : ①受付（コンソールの CASE_ID を取得して GetCaseData）
'   Console_RunAll  : ①〜④を一括実行
'   GotoSheet       : タブ（各シート）へジャンプ
' =============================================================================

Private Const CONSOLE_SHEET As String = "コンソール"
Private Const CASEID_CELL As String = "C5"
Private Const SHAPE_PREFIX As String = "cx_"
Private Const UI_FONT As String = "Yu Gothic UI"

' ---- ダークパレット（RGB） ----
Private Function C_BG() As Long:      C_BG = RGB(27, 29, 30):     End Function   ' #1B1D1E 背景
Private Function C_SURFACE() As Long: C_SURFACE = RGB(38, 41, 43): End Function  ' #26292B 面（一段明るい）
Private Function C_INPUT() As Long:   C_INPUT = RGB(45, 49, 52):  End Function   ' 入力欄
Private Function C_TXT() As Long:     C_TXT = RGB(218, 214, 207): End Function   ' #DAD6CF 主要文字（暖色オフホワイト）
Private Function C_MUTED() As Long:   C_MUTED = RGB(154, 160, 166): End Function ' 副次文字
Private Function C_ACCENT() As Long:  C_ACCENT = RGB(79, 169, 143): End Function ' ティール（主要操作）
Private Function C_CTA() As Long:     C_CTA = RGB(210, 162, 76):  End Function   ' アンバー（実行系）
Private Function C_ONACC() As Long:   C_ONACC = RGB(20, 22, 23):  End Function   ' アクセント上の文字（暗）
Private Function C_DIVIDER() As Long: C_DIVIDER = RGB(60, 64, 67): End Function  ' 区切り線

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
    Dim x As Double, y As Double

    Set ws = EnsureSheet(CONSOLE_SHEET)
    ThisWorkbook.Sheets(CONSOLE_SHEET).Move Before:=ThisWorkbook.Sheets(1)

    ' --- 初期化：既存の当モジュール製ボタン/シェイプを除去 ---
    On Error Resume Next
    ws.Buttons.Delete
    On Error GoTo 0
    RemoveOurShapes ws

    ' --- ダーク下地 ---
    ws.Cells.Clear
    ws.Cells.Interior.Color = C_BG()
    ws.Cells.Font.Color = C_TXT()
    ws.Cells.Font.Name = UI_FONT
    ws.Cells.Font.Size = 11
    ws.Tab.Color = C_BG()
    ws.Columns("A").ColumnWidth = 2       ' 左余白
    ws.Rows("1").RowHeight = 10           ' 上余白

    ' 視線を整える（グリッド線・見出しを隠す）
    ws.Activate
    On Error Resume Next
    ActiveWindow.DisplayGridlines = False
    ActiveWindow.DisplayHeadings = False
    ActiveWindow.Zoom = 110
    On Error GoTo 0

    ' --- タイトル ---
    With ws.Range("B2")
        .value = "CSC 受付  →  CE ディスパッチ"
        .Font.Size = 18
        .Font.Bold = True
        .Font.Color = C_TXT()
    End With
    With ws.Range("B3")
        .value = "オペレータ・コンソール（ダークモード）"
        .Font.Size = 10
        .Font.Color = C_MUTED()
    End With

    ' --- 上部タブ（各シートへジャンプ） ---
    tabs = TabSheets()
    x = ws.Range("B4").Left
    y = ws.Range("B4").Top + 24
    For i = LBound(tabs) To UBound(tabs)
        If SheetExists(CStr(tabs(i))) Then
            AddButton ws, x, y, 118, 26, CStr(tabs(i)), _
                      "'GotoSheet """ & CStr(tabs(i)) & """'", IIf(i = 0, "accent", "nav")
            x = x + 124
        End If
    Next i

    ' --- カード：① 受付 ---
    y = ws.Range("B7").Top + 6
    DrawSectionTitle ws, "B7", "①  受 付"
    ws.Range("B8").value = "CASE_ID"
    ws.Range("B8").Font.Color = C_MUTED()
    StyleInput ws.Range(CASEID_CELL)
    AddButton ws, ws.Range("E5").Left, ws.Range("E5").Top, 190, 30, _
              "受付データ取得", "Console_Receive", "accent"

    ' --- カード：② 情報確認 ---
    DrawSectionTitle ws, "B10", "②  情 報 確 認"
    AddButton ws, ws.Range("B11").Left, ws.Range("B11").Top, 180, 28, _
              "作業履歴を取得", "GetWorkHistory", "secondary"
    AddButton ws, ws.Range("E11").Left, ws.Range("B11").Top, 180, 28, _
              "マッピング反映", "ApplyMapping", "secondary"

    ' --- カード：③ 掲示板 ---
    DrawSectionTitle ws, "B14", "③  掲 示 板（社内Web）"
    AddButton ws, ws.Range("B15").Left, ws.Range("B15").Top, 180, 28, _
              "掲示板を開く", "OpenBulletinBoards", "secondary"

    ' --- カード：④ CE 指示（ディスパッチ） ---
    DrawSectionTitle ws, "B18", "④  CE 指 示（ディスパッチ）"
    AddButton ws, ws.Range("B19").Left, ws.Range("B19").Top, 220, 30, _
              "CE 指示メールを作成", "CreateCEInstructionMail", "accent"

    ' --- 一括実行（CTA） ---
    DrawDivider ws, "B22"
    AddButton ws, ws.Range("B23").Left, ws.Range("B23").Top, 300, 34, _
              "①  →  ④   一括実行", "Console_RunAll", "cta"

    ' --- 各シートにもダークテーマ＋「戻る」ナビ ---
    For i = LBound(tabs) To UBound(tabs)
        If CStr(tabs(i)) <> CONSOLE_SHEET And SheetExists(CStr(tabs(i))) Then
            ApplyDarkToSheet ThisWorkbook.Sheets(CStr(tabs(i)))
            AddReturnNav ThisWorkbook.Sheets(CStr(tabs(i)))
        End If
    Next i

    ws.Activate
    ws.Range(CASEID_CELL).Select
    MsgBox "ダークモードのコンソールを構築しました。" & vbCrLf & _
           "上部タブで画面を切り替えられます。", vbInformation
End Sub

' 全シート（存在するもの）にダークテーマを適用したいとき
Public Sub ApplyDarkTheme()
    Dim tabs As Variant, i As Long
    tabs = TabSheets()
    For i = LBound(tabs) To UBound(tabs)
        If SheetExists(CStr(tabs(i))) Then
            If CStr(tabs(i)) = CONSOLE_SHEET Then
                BuildConsole
            Else
                ApplyDarkToSheet ThisWorkbook.Sheets(CStr(tabs(i)))
            End If
        End If
    Next i
End Sub

' データシートをダーク化（読みやすさ優先で最小限）
Private Sub ApplyDarkToSheet(ByVal ws As Worksheet)
    ws.Cells.Interior.Color = C_BG()
    ws.Cells.Font.Color = C_TXT()
    ws.Cells.Font.Name = UI_FONT
    ws.Tab.Color = C_BG()
    ' 1 行目（ヘッダらしき行）を面色で強調
    ws.Rows(1).Interior.Color = C_SURFACE()
    ws.Rows(1).Font.Bold = True
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
    GetCaseData
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
    RemoveOurShapes ws
    On Error Resume Next
    ws.Buttons.Delete   ' 旧フォームボタン版の掃除
    On Error GoTo 0
    AddButton ws, 6, 6, 150, 22, "▲ コンソールへ戻る", _
              "'GotoSheet """ & CONSOLE_SHEET & """'", "nav"
End Sub

' =============================================================================
' 描画補助
' =============================================================================

' 角丸シェイプのボタンを配置（kind: accent / cta / secondary / nav）
Private Sub AddButton(ByVal ws As Worksheet, ByVal leftPt As Double, ByVal topPt As Double, _
        ByVal w As Double, ByVal h As Double, ByVal caption As String, _
        ByVal action As String, ByVal kind As String)
    Dim shp As Shape
    Dim fillColor As Long, textColor As Long

    Select Case LCase(kind)
        Case "accent":    fillColor = C_ACCENT(): textColor = C_ONACC()
        Case "cta":       fillColor = C_CTA():    textColor = C_ONACC()
        Case "secondary": fillColor = C_SURFACE(): textColor = C_TXT()
        Case Else:        fillColor = C_SURFACE(): textColor = C_MUTED()   ' nav
    End Select

    Set shp = ws.Shapes.AddShape(msoShapeRoundedRectangle, leftPt, topPt, w, h)
    shp.Name = SHAPE_PREFIX & ws.Shapes.Count & "_" & Int(Rnd * 100000)
    On Error Resume Next
    shp.Adjustments(1) = 0.28   ' やわらかい角丸
    On Error GoTo 0
    shp.Fill.ForeColor.RGB = fillColor
    shp.Line.Visible = msoFalse
    With shp.TextFrame
        .Characters.Text = caption
        .Characters.Font.Color = textColor
        .Characters.Font.Size = 11
        .Characters.Font.Bold = True
        .Characters.Font.Name = UI_FONT
        .HorizontalAlignment = xlHAlignCenter
        .VerticalAlignment = xlVAlignCenter
    End With
    shp.OnAction = action
End Sub

' セクション見出し（アクセントの縦バー + 太字ラベル）
Private Sub DrawSectionTitle(ByVal ws As Worksheet, ByVal anchorCell As String, ByVal label As String)
    Dim rng As Range
    Dim bar As Shape
    Set rng = ws.Range(anchorCell)
    Set bar = ws.Shapes.AddShape(msoShapeRectangle, rng.Left - 8, rng.Top + 2, 4, 16)
    bar.Name = SHAPE_PREFIX & "bar_" & ws.Shapes.Count
    bar.Fill.ForeColor.RGB = C_ACCENT()
    bar.Line.Visible = msoFalse
    With rng
        .value = label
        .Font.Bold = True
        .Font.Size = 12
        .Font.Color = C_TXT()
    End With
End Sub

' 区切り線
Private Sub DrawDivider(ByVal ws As Worksheet, ByVal anchorCell As String)
    Dim rng As Range
    Dim ln As Shape
    Set rng = ws.Range(anchorCell)
    Set ln = ws.Shapes.AddShape(msoShapeRectangle, rng.Left, rng.Top, 520, 1)
    ln.Name = SHAPE_PREFIX & "div_" & ws.Shapes.Count
    ln.Fill.ForeColor.RGB = C_DIVIDER()
    ln.Line.Visible = msoFalse
End Sub

' 入力欄のスタイル
Private Sub StyleInput(ByVal rng As Range)
    rng.value = ""
    rng.NumberFormat = "@"
    rng.Interior.Color = C_INPUT()
    rng.Font.Color = C_TXT()
    rng.Font.Size = 12
    With rng.Borders
        .LineStyle = xlContinuous
        .Color = C_ACCENT()
        .Weight = xlThin
    End With
End Sub

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

' 当モジュールが作ったシェイプ（cx_ 接頭辞）だけ削除
Private Sub RemoveOurShapes(ByVal ws As Worksheet)
    Dim shp As Shape
    Dim i As Long
    For i = ws.Shapes.Count To 1 Step -1
        Set shp = ws.Shapes(i)
        If Left(shp.Name, Len(SHAPE_PREFIX)) = SHAPE_PREFIX Then shp.Delete
    Next i
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
