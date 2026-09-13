Attribute VB_Name = "CaseDataRetrieval"
Option Explicit

' =============================================================================
' CaseDataRetrieval
'
' Excel VBA マクロ群。CASE_ID をもとに CTSQ / ACROS の各データベースから
' 保守情報を取得し、「メール作成」シートへ割り付ける。
'
'   GetCaseData  : メール作成シートの CASE_ID から CTSQ-DATA を取得
'   GetAcrosData : CTSQ-DATA のお客様ID から ACROS-DATA を取得
'   ClearGetData : 取得データ（B列）をクリア
'   DataPutin    : 取得データをメール作成シートへ割り付け
' =============================================================================

Public Sub GetCaseData()
    Dim caseID As String
    Dim paddedCaseID As String
    Dim conn As Object
    Dim rs As Object
    Dim query As String
    Dim i As Integer
    Dim wsInput As Worksheet
    Dim wsOutput As Worksheet
    Dim outputRow As Long
    Dim recordCount As Long
    Dim fieldValue As String

    ' シート参照
    Set wsInput = ThisWorkbook.Sheets("メール作成")
    Set wsOutput = ThisWorkbook.Sheets("CTSQ-DATA")

    ' CASE_ID取得（D4セル）
    caseID = Trim(wsInput.Range("D4").value)

    ' 数値チェック
    If Not IsNumeric(caseID) Then
        MsgBox "D4セルの値が数字ではありません。処理を中止します。", vbExclamation
        Exit Sub
    End If

    ' 12桁ゼロ埋め
    paddedCaseID = Right(String(12, "0") & caseID, 12)

    ' 出力シートクリア
    wsOutput.columns("B").Clear

    ' ODBC接続
    Set conn = CreateObject("ADODB.Connection")
    ' ※ パスワードは直書きせず、DSN 側に保存するか実行環境の資格情報から補うこと。
    conn.ConnectionString = "DSN=CTSQ24;DBQ=nas1033.world;UID=INQ_TSC;PWD=<SET_PASSWORD>;"
    conn.Open

    ' クエリ作成
    query = "SELECT * FROM INQ_TSC.CASE_ALL WHERE CASE_ID = '" & paddedCaseID & "' AND ROWNUM <= 2"

    ' レコードセット取得
    Set rs = CreateObject("ADODB.Recordset")
    rs.Open query, conn, 1, 1 ' adOpenKeyset, adLockReadOnly

    ' データ出力
    outputRow = 1
    recordCount = 0
    Do While Not rs.EOF
        recordCount = recordCount + 1
        For i = 0 To rs.Fields.Count - 1
            wsOutput.Cells(outputRow, 1).value = rs.Fields(i).Name
            ' Nullチェックして文字列化（電話番号など0始まり対応）
            If IsNull(rs.Fields(i).value) Then
                fieldValue = ""
            Else
                fieldValue = "'" & CStr(rs.Fields(i).value) ' 先頭にシングルクォートを付加
            End If

            wsOutput.Cells(outputRow, 2).value = fieldValue

            outputRow = outputRow + 1
        Next i
        rs.MoveNext
    Loop

    ' クローズ
    rs.Close
    conn.Close
    Set rs = Nothing
    Set conn = Nothing

    GetAcrosData     '保守情報取得
    DataPutin    'データ割り付け

    MsgBox "データ取得完了。" & vbCrLf & _
           "取得件数：" & recordCount & " 件", vbInformation
End Sub

Public Sub GetAcrosData()
    Dim siteID_11 As String
    Dim unitID_3 As String
    Dim siteFullID As String
    Dim dateKanjo As String
    Dim conn As Object
    Dim rs As Object
    Dim query As String
    Dim i As Integer
    Dim wsCTSQ As Worksheet
    Dim wsACROS As Worksheet
    Dim outputRow As Long
    Dim fieldValue As String

    ' シート参照
    Set wsCTSQ = ThisWorkbook.Sheets("CTSQ-DATA")
    Set wsACROS = ThisWorkbook.Sheets("ACROS-DATA")

    ' 変数に代入（先頭シングルクォート除去）
    siteID_11 = wsCTSQ.Range("B35").value
    If Left(siteID_11, 1) = "'" Then siteID_11 = Mid(siteID_11, 2)

    unitID_3 = wsCTSQ.Range("B36").value
    If Left(unitID_3, 1) = "'" Then unitID_3 = Mid(unitID_3, 2)

    siteFullID = siteID_11 & "-" & unitID_3
    dateKanjo = Format(Date, "yyyy/MM")

    ' 出力シートクリア
    wsACROS.columns("B").Clear

    ' ODBC接続
    Set conn = CreateObject("ADODB.Connection")
    ' ※ パスワードは直書きせず、DSN 側に保存するか実行環境の資格情報から補うこと。
    conn.ConnectionString = "DSN=NAS1001N02P_MS;DBQ=NAS1001N02P.WORLD;UID=cec;PWD=<SET_PASSWORD>;"
    conn.Open

    ' クエリ作成
    query = "SELECT * FROM ACROS.構成一覧 " & _
            "WHERE お客様ID = '" & siteFullID & "' " & _
            "AND ""状態（ステータス）"" = '有効' " & _
            "AND 勘定月 = '" & dateKanjo & "'"

    ' レコードセット取得
    Set rs = CreateObject("ADODB.Recordset")
    rs.Open query, conn, 1, 1 ' adOpenKeyset, adLockReadOnly

    ' データ出力
    outputRow = 1
    Do While Not rs.EOF
        For i = 0 To rs.Fields.Count - 1
            wsACROS.Cells(outputRow, 1).value = "'" & rs.Fields(i).Name ' カラム名も文字列固定

            ' Nullチェックして文字列化（先頭にシングルクォート）
            If IsNull(rs.Fields(i).value) Then
                fieldValue = "''"
            Else
                fieldValue = "'" & CStr(rs.Fields(i).value)
            End If

            wsACROS.Cells(outputRow, 2).value = fieldValue
            outputRow = outputRow + 1
        Next i
        rs.MoveNext
    Loop

    ' クローズ
    rs.Close
    conn.Close
    Set rs = Nothing
    Set conn = Nothing

End Sub


Public Sub ClearGetData()
    Dim wsCTSQ As Worksheet
    Dim wsACROS As Worksheet

    ' シート参照
    Set wsCTSQ = ThisWorkbook.Sheets("CTSQ-DATA")
    Set wsACROS = ThisWorkbook.Sheets("ACROS-DATA")

    ' 出力シートクリア
    wsCTSQ.columns("B").Clear
    wsACROS.columns("B").Clear

End Sub

Public Sub DataPutin()
    Dim textSC As String
    Dim newSC As String
    Dim textID As String
    Dim newID As String
    Dim wsCTSQ As Worksheet

    ' シート参照
    Set wsCTSQ = ThisWorkbook.Sheets("CTSQ-DATA")

    ' 各サービスセンタの「サービスセンタ」を「SC」に置換
    textSC = wsCTSQ.Range("B56").value
    If textSC = "沖メ" Then
        ' 例外：B56 が「沖縄」の場合
        newSC = "沖メ"
    Else
        ' 通常処理
        newSC = Left(textSC, Len(textSC) - 7) & "SC"
    End If

    ' siteIDの頭7文字抜き出し
    textID = wsCTSQ.Range("B35").value
    newID = Left(textID, 7)


    ' 各セルに出力
    Worksheets("メール作成").Range("D10").value = Worksheets("CTSQ-DATA").Range("B54").value
    Worksheets("メール作成").Range("D11").value = newSC
    Worksheets("メール作成").Range("D12").value = newID
    Worksheets("メール作成").Range("D13").value = "'" & Worksheets("CTSQ-DATA").Range("B36").value
    Worksheets("メール作成").Range("D14").value = Worksheets("CTSQ-DATA").Range("B42").value
    Worksheets("メール作成").Range("D15").value = Worksheets("CTSQ-DATA").Range("B74").value

    Worksheets("メール作成").Range("D17").value = Worksheets("CTSQ-DATA").Range("B33").value
    Worksheets("メール作成").Range("D18").value = Worksheets("CTSQ-DATA").Range("B2").value
    Worksheets("メール作成").Range("D20").value = Worksheets("ACROS-DATA").Range("B38").value
    Worksheets("メール作成").Range("D23").value = Worksheets("CTSQ-DATA").Range("B42").value
    Worksheets("メール作成").Range("D24").value = Worksheets("CTSQ-DATA").Range("B38").value
    Worksheets("メール作成").Range("D26").value = Worksheets("CTSQ-DATA").Range("B74").value
    Worksheets("メール作成").Range("D27").value = "'" & Worksheets("CTSQ-DATA").Range("B75").value
    Worksheets("メール作成").Range("D28").value = Worksheets("CTSQ-DATA").Range("B78").value
    Worksheets("メール作成").Range("D32").value = "'" & Worksheets("CTSQ-DATA").Range("B113").value
    Worksheets("メール作成").Range("D33").value = "'" & Worksheets("CTSQ-DATA").Range("B115").value
    Worksheets("メール作成").Range("D34").value = "'" & Worksheets("CTSQ-DATA").Range("B117").value
    Worksheets("メール作成").Range("D30").value = "代表：" & Worksheets("CTSQ-DATA").Range("B49").value & "　内線：　直通："

End Sub
