Attribute VB_Name = "CEInstruction"
Option Explicit

' =============================================================================
' CEInstruction
'
' CSC 受付後のワークフローを 1 本にまとめるモジュール。
'
'   1. CASE_ID から受付データを取得（既存 CaseDataRetrieval.GetCaseData を利用）
'   2. 作業履歴を社内 DB（ODBC）から取得し WORK-HISTORY シートへ出力
'   3. 各種掲示板（社内 Web）を、受付情報を差し込んだ URL で自動オープン
'   4. 取得内容をもとに CE（カスタマーエンジニア）への作業指示メールを
'      Outlook で下書き作成（送信は人が確認）
'
' エントリポイント: MakeCEInstruction
'
' 【重要】このモジュールは "ひな形" です。社内固有の値（DSN・表名・列名・
' 掲示板 URL・CE 宛先）は下の設定セクションを実環境に合わせて埋めてください。
' パスワードはリポジトリに残さないため <SET_PASSWORD> のままにしています。
' =============================================================================

' ---- 設定：作業履歴 DB（ODBC / バックエンド = ACROS EUC 想定） ------------------
' 既存の CTSQ / ACROS と同じく ADODB + ODBC で取得します。
' 作業履歴の実体は社内サーバーの "ACROS EUC" データベースを想定。DSN・表名・列名を
' 実環境に合わせて設定してください（DSN 文字列は分かり次第このプレースホルダを置換）。
Private Const WH_CONNECTION As String = _
    "DSN=<WORKHIST_DSN>;DBQ=<WORKHIST_DBQ>;UID=<WORKHIST_UID>;PWD=<SET_PASSWORD>;"

' 参照する表名（スキーマ.表名）
Private Const WH_TABLE As String = "<SCHEMA>.<WORK_HISTORY_TABLE>"

' 絞り込みに使うキー列と、その値の種類（"SITE" = お客様ID / "CASE" = CASE_ID）
Private Const WH_KEY_COLUMN As String = "<KEY_COLUMN>"   ' 例: お客様ID
Private Const WH_KEY_KIND As String = "SITE"             ' "SITE" または "CASE"

' 並び替え用の日付列（新しい順）。空文字なら並び替えしない。
Private Const WH_DATE_COLUMN As String = "<DATE_COLUMN>"  ' 例: 作業日

' メール本文へ載せる履歴件数の上限
Private Const WH_MAX_ROWS As Long = 10

' 取得・表示する列（カンマ区切り。空なら "*" で全列）。
' 例: "作業日,担当,作業区分,内容,結果"
Private Const WH_SELECT_COLUMNS As String = "<COL1>,<COL2>,<COL3>"

' ---- 設定：各種掲示板（社内 Web） ---------------------------------------------
' 参照したい掲示板/ポータルの URL を "|" 区切りで列挙します。
' URL 内の {SITE} は お客様ID（siteFullID）、{CASE} は 12 桁 CASE_ID、
' {SITE7} は サイトID 先頭 7 桁に置換されます。
Private Const BOARD_URLS As String = _
    "https://<board1>/search?id={SITE}" & "|" & _
    "https://<board2>/notice?case={CASE}"

' ---- 設定：CE 作業指示メール --------------------------------------------------
Private Const CE_MAIL_TO As String = "<ce-team@example.co.jp>"   ' 既定の宛先
Private Const CE_MAIL_CC As String = ""                          ' 任意
Private Const MAIL_AUTO_SEND As Boolean = False   ' True で自動送信（既定は下書き表示）

' =============================================================================
' エントリポイント
' =============================================================================
Public Sub MakeCEInstruction()
    ' 1. 受付データ取得（CTSQ/ACROS 取得 + メール作成シートへ割り付けまで実施）
    GetCaseData

    ' 2. 作業履歴を取得
    GetWorkHistory

    ' 3. 掲示板をブラウザで開く（オペレータ参照用）
    OpenBulletinBoards

    ' 4. CE への作業指示メールを Outlook で作成
    CreateCEInstructionMail
End Sub

' =============================================================================
' 作業履歴の取得（社内 DB / ODBC）
' =============================================================================
Public Sub GetWorkHistory()
    Dim conn As Object
    Dim rs As Object
    Dim query As String
    Dim selectCols As String
    Dim keyValue As String
    Dim wsCTSQ As Worksheet
    Dim wsWH As Worksheet
    Dim outputRow As Long
    Dim i As Integer
    Dim v As Variant

    ' 未設定（プレースホルダのまま）なら取得をスキップ
    If InStr(WH_CONNECTION, "<") > 0 Or InStr(WH_TABLE, "<") > 0 Then Exit Sub

    Set wsCTSQ = ThisWorkbook.Sheets("CTSQ-DATA")
    Set wsWH = EnsureSheet("WORK-HISTORY")

    ' 絞り込みキーの値を決定
    If UCase(WH_KEY_KIND) = "CASE" Then
        keyValue = GetPaddedCaseID()                           ' 12 桁ゼロ埋め CASE_ID
    Else
        keyValue = BuildSiteFullID(wsCTSQ)                      ' お客様ID = サイトID-ユニットID
    End If

    If Len(keyValue) = 0 Then
        MsgBox "作業履歴の検索キーが取得できませんでした。CTSQ-DATA を確認してください。", vbExclamation
        Exit Sub
    End If

    ' SELECT 句
    If Len(Trim(Replace(WH_SELECT_COLUMNS, "<COL1>,<COL2>,<COL3>", ""))) = 0 Then
        selectCols = "*"
    Else
        selectCols = WH_SELECT_COLUMNS
    End If

    ' クエリ作成
    query = "SELECT " & selectCols & " FROM " & WH_TABLE & _
            " WHERE " & WH_KEY_COLUMN & " = '" & keyValue & "'"
    If Len(WH_DATE_COLUMN) > 0 And InStr(WH_DATE_COLUMN, "<") = 0 Then
        query = query & " ORDER BY " & WH_DATE_COLUMN & " DESC"
    End If

    ' 出力シートをクリア
    wsWH.Cells.Clear

    ' 接続
    Set conn = CreateObject("ADODB.Connection")
    conn.ConnectionString = WH_CONNECTION
    conn.Open

    Set rs = CreateObject("ADODB.Recordset")
    rs.Open query, conn, 1, 1 ' adOpenKeyset, adLockReadOnly

    ' 1 行目にヘッダ（列名）
    For i = 0 To rs.Fields.Count - 1
        wsWH.Cells(1, i + 1).value = rs.Fields(i).Name
    Next i

    ' 2 行目以降にデータ（先頭にシングルクォートを付けて文字列固定）
    outputRow = 2
    Do While Not rs.EOF
        For i = 0 To rs.Fields.Count - 1
            v = rs.Fields(i).value
            If IsNull(v) Then
                wsWH.Cells(outputRow, i + 1).value = ""
            Else
                wsWH.Cells(outputRow, i + 1).value = "'" & CStr(v)
            End If
        Next i
        outputRow = outputRow + 1
        rs.MoveNext
    Loop

    rs.Close
    conn.Close
    Set rs = Nothing
    Set conn = Nothing
End Sub

' =============================================================================
' 掲示板（社内 Web）をブラウザで開く
' =============================================================================
Public Sub OpenBulletinBoards()
    Dim wsCTSQ As Worksheet
    Dim urls() As String
    Dim url As String
    Dim siteFullID As String
    Dim site7 As String
    Dim caseID As String
    Dim i As Long

    If Len(Trim(BOARD_URLS)) = 0 Or InStr(BOARD_URLS, "<board1>") > 0 Then
        ' 未設定のうちは何もしない（誤って外部サイトを開かないように）
        Exit Sub
    End If

    Set wsCTSQ = ThisWorkbook.Sheets("CTSQ-DATA")
    siteFullID = BuildSiteFullID(wsCTSQ)
    site7 = Left(StripLeadingQuote(wsCTSQ.Range("B35").value), 7)
    caseID = GetPaddedCaseID()

    urls = Split(BOARD_URLS, "|")
    For i = LBound(urls) To UBound(urls)
        url = Trim(urls(i))
        If Len(url) > 0 Then
            url = Replace(url, "{SITE}", siteFullID)
            url = Replace(url, "{SITE7}", site7)
            url = Replace(url, "{CASE}", caseID)
            On Error Resume Next
            ThisWorkbook.FollowHyperlink url
            On Error GoTo 0
        End If
    Next i
End Sub

' =============================================================================
' CE への作業指示メールを Outlook で作成
' =============================================================================
Public Sub CreateCEInstructionMail()
    Dim olApp As Object
    Dim olMail As Object
    Dim wsMail As Worksheet
    Dim subject As String
    Dim body As String

    Set wsMail = ThisWorkbook.Sheets("メール作成")

    ' 件名（施設名 + CASE_ID）
    subject = "【CE作業指示】" & CStr(wsMail.Range("D10").value) & _
              "  CASE:" & GetPaddedCaseID()

    body = BuildInstructionBody()

    ' Outlook 起動（起動済みなら取得、無ければ生成）
    On Error Resume Next
    Set olApp = GetObject(, "Outlook.Application")
    On Error GoTo 0
    If olApp Is Nothing Then Set olApp = CreateObject("Outlook.Application")

    Set olMail = olApp.CreateItem(0) ' olMailItem
    With olMail
        .To = CE_MAIL_TO
        If Len(CE_MAIL_CC) > 0 Then .CC = CE_MAIL_CC
        .subject = subject
        .body = body
        If MAIL_AUTO_SEND Then
            .Send
        Else
            .Display   ' 人が確認・修正してから送信
        End If
    End With

    Set olMail = Nothing
    Set olApp = Nothing
End Sub

' =============================================================================
' 作業指示メール本文の組み立て
'   ・ヘッダ部は「メール作成」シートの割り付け済みセル（D 列）を利用
'   ・末尾に WORK-HISTORY シートの作業履歴を表形式で添付
' =============================================================================
Public Function BuildInstructionBody() As String
    Dim wsMail As Worksheet
    Dim s As String
    Const NL As String = vbCrLf

    Set wsMail = ThisWorkbook.Sheets("メール作成")

    s = "CE 各位" & NL & NL
    s = s & "下記のとおり作業を依頼します。" & NL
    s = s & "----------------------------------------" & NL
    s = s & "■ 施設名        : " & CStr(wsMail.Range("D10").value) & NL
    s = s & "■ 担当SC        : " & CStr(wsMail.Range("D11").value) & NL
    s = s & "■ サイトID       : " & CStr(wsMail.Range("D12").value) & NL
    s = s & "■ ユニットID     : " & StripLeadingQuote(wsMail.Range("D13").value) & NL
    s = s & "■ 機種           : " & CStr(wsMail.Range("D18").value) & NL
    s = s & "■ 設置場所       : " & CStr(wsMail.Range("D17").value) & NL
    s = s & "■ 代表連絡先     : " & CStr(wsMail.Range("D30").value) & NL
    s = s & "----------------------------------------" & NL & NL
    s = s & "【受付内容 / 依頼事項】" & NL
    s = s & "（ここに受付内容と CE への具体的な指示を記入してください）" & NL & NL
    s = s & AppendWorkHistory(NL)
    s = s & NL & "以上、よろしくお願いいたします。" & NL

    BuildInstructionBody = s
End Function

' WORK-HISTORY シートを読み、直近の履歴をタブ区切りテキストで返す
Private Function AppendWorkHistory(ByVal NL As String) As String
    Dim wsWH As Worksheet
    Dim lastRow As Long, lastCol As Long
    Dim r As Long, c As Long
    Dim line As String
    Dim s As String
    Dim shown As Long

    On Error Resume Next
    Set wsWH = ThisWorkbook.Sheets("WORK-HISTORY")
    On Error GoTo 0
    If wsWH Is Nothing Then Exit Function

    lastRow = wsWH.Cells(wsWH.Rows.Count, 1).End(-4162).Row ' xlUp
    lastCol = wsWH.Cells(1, wsWH.columns.Count).End(-4159).Column ' xlToLeft
    If lastRow < 2 Then
        AppendWorkHistory = "【作業履歴】 該当なし" & NL
        Exit Function
    End If

    s = "【作業履歴（直近）】" & NL

    ' ヘッダ行
    line = ""
    For c = 1 To lastCol
        line = line & CStr(wsWH.Cells(1, c).value)
        If c < lastCol Then line = line & vbTab
    Next c
    s = s & line & NL

    ' データ行（上から WH_MAX_ROWS 件）
    shown = 0
    For r = 2 To lastRow
        If shown >= WH_MAX_ROWS Then Exit For
        line = ""
        For c = 1 To lastCol
            line = line & StripLeadingQuote(wsWH.Cells(r, c).value)
            If c < lastCol Then line = line & vbTab
        Next c
        s = s & line & NL
        shown = shown + 1
    Next r

    AppendWorkHistory = s
End Function

' =============================================================================
' 補助関数
' =============================================================================

' 「メール作成」D4 の CASE_ID を 12 桁ゼロ埋めで返す（GetCaseData と同一仕様）
Private Function GetPaddedCaseID() As String
    Dim caseID As String
    caseID = Trim(StripLeadingQuote(ThisWorkbook.Sheets("メール作成").Range("D4").value))
    If Not IsNumeric(caseID) Or Len(caseID) = 0 Then
        GetPaddedCaseID = ""
    Else
        GetPaddedCaseID = Right(String(12, "0") & caseID, 12)
    End If
End Function

' お客様ID（siteFullID）= サイトID(B35) & "-" & ユニットID(B36)
Private Function BuildSiteFullID(ByVal wsCTSQ As Worksheet) As String
    Dim siteID_11 As String
    Dim unitID_3 As String

    siteID_11 = StripLeadingQuote(wsCTSQ.Range("B35").value)
    unitID_3 = StripLeadingQuote(wsCTSQ.Range("B36").value)

    If Len(siteID_11) = 0 Then
        BuildSiteFullID = ""
    Else
        BuildSiteFullID = siteID_11 & "-" & unitID_3
    End If
End Function

' 先頭のシングルクォートを取り除く（セル値の文字列固定対策）
Private Function StripLeadingQuote(ByVal s As Variant) As String
    Dim t As String
    t = CStr(s)
    If Left(t, 1) = "'" Then t = Mid(t, 2)
    StripLeadingQuote = t
End Function

' 指定名のシートを取得（無ければ作成して返す）
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
