Attribute VB_Name = "Module1"
Option Explicit
 
'//=====================================================================================================
'//
'//     入出荷実績一覧データ出力（オラクル接続）　※通称　５年９組           　　　　　　　　　 Y.FURUTA
'//
'//_____________________________________________________________________________________________________
'//
'// 1)オラクル接続はＡＤＯ　＋　ＯＤＢＣ (Microsoft）　（ORACLE CLIENTを実行環境のＰＣに導入する必要あり）
'// 2)オラクル接続は品目マスタを表示した時、データを読込した都度接続／切断を行う。
'// 3)テスト環境 Windows10PRO EXCEL2007 Oracle client 12c (32bit)
'//_____________________________________________________________________________________________________
'//
'//  (更新履歴）
'//  2020/05/21 1.0   Release
'//  2020/06/02 2.0   所要量履歴テーブルを参照して所要量を出力する
'//  2020/06/08 2.2   内示受注データのＳＱＬを変更（詳細内容を表示できないバグの修正）
'//  2020/09/07 2.3   構成マスタを有効開始日で抜粋する
'//  2022/01/06       安全在庫でオーバーフローするバグを修正
'//  2022/01/27 2.5.1 構成マスタの有効開始日指定するＳＱＬの誤りを修正
'//                   得意先品目検索時に有効開始日を考慮するＳＱＬに変更
'//  2022/02/23 2.5.3 適用日により有効開始日と有効終了日の範囲を決定する。
'//                   ワークブックが開いた時にシステム日付を適用ににセットする
'//                   ※ThisWorkbookにWorkbook_Openを記載
'//  2022/06/02 2.6.0 得意先品目マスタの有効日のチェックをせずに過去の関連する品番も表示していたバグを修正
'//  2022/06/07 2.6.1 構成マスタで有効日が無効のレコードの配下のレコードを出力していたのでSQL文で除外する。
'//  2022/06/30 2.7.0 所要量データと確定発注データから「取消（0.完了）」のデータを除外する
'//                   保管区別品目在庫テーブルから本日分手持ち在庫を取得して表示する
'//  2022/08/05 2.7.1 内作品番検索に失敗した場合は、メッセージボックスを表示する
'//                   確定受注の参照時に内作品番単位で出力から得意先品目単位で出力するように仕様を変更
'//  2022/08/24 2.7.2 本日手持ち在庫の計算誤りを修正（保管区別在庫レコードが複数ある場合）
'//  2022/09/20 2.8.0 得意先品目任意変換値を指定してターゲット品目を決定する
'//                   統合受注も表示をする
'//                   出荷部分の呼び出しを得意先品目から社内品番（内作）に戻す
'//  2022/10/28 2.9.0 手配区分（加工依頼、かんばん）を出力する
'//                   前月以前の確定受注残と確定発注残を出力する
'//  2023/05/11 3.0.0 構成マスタにレベル番号を追加
'//                   仮売上から売上実績を出力する。
'//  2023/05/15 3.0.1 複数の得意先があった場合に最初の得意先しか実績データを取得しないバグを修正
'//  2023/11/16 3.1.0 品目別入庫先保管区（M_ITEM_RCV_WH）を参照して保管区（受入）を工程に表示する
'//  2023/11/17 3.2.0 複数の得意先品番の場合は統合受注の合計行を出力する
'//  2023/11/21 3.2.1 保管区が未登録の場合にNULLでエラーとなるのを抑制
'//=====================================================================================================

'tnsnames.ora ファイルのネットサービス名'
'Const STRDATASOURCE = "hpdb1"
    
'tnsnames.ora を使用しない場合（直接指定）
Const STRDATASOURCE = _
        "(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)" & _
        "(HOST = 192.168.3.204)(PORT = 1521))(CONNECT_DATA = (SID = EXPJ)))"
    
Const USERNAME = "EXPJ"       '接続するデータベースのユーザー名
Const PASSWORD = "EXPJ"       'パスワード

Public oraCon As New ADODB.Connection
Public oraRs As New ADODB.Recordset
Public constr As String


Public ORACLE_OPEN_SW As Integer        'オラクルと接続済みかどうかのスイッチ　１＝接続済み
Dim IX1 As Integer


Public KOTEI_MEISAI(7) As String        '工程の品目情報を保存する。（１件）
Public BK_HINBAN(12) As String          '代替品目情報を保存する MAX=13
Public BK_TEBAN As Integer              '出荷品番の手番
Public BK_ANZEN As Double               '出荷品番の安全在庫

Public total_arry1(31) As Double        '内示受注のトータル用
Public total_arry2(31) As Double        '確定受注のトータル用
Public total_arry3(31) As Double        '統合受注のトータル用
Public total_arry4(31) As Double        '出荷実績のトータル用
Public total_arry5(31) As Double        '売上実績のトータル用
Public CUST_ITEM_CNT As Integer

'//////////////////////////////
'// オラクルとの接続処理
'//////////////////////////////

Public Sub ORACLE_OPEN()
    
    If ORACLE_OPEN_SW <> 1 Then     '既に接続済みの場合は実行しない
    
        constr = "Provider=MSDAORA"
        constr = constr & ";Data Source=" & STRDATASOURCE
        constr = constr & ";User ID=" & USERNAME
        constr = constr & ";Password=" & PASSWORD
    
        oraCon.ConnectionString = constr
        oraCon.Open

        ORACLE_OPEN_SW = 1
    
    End If
    
End Sub

'//////////////////////////////
'// オラクルとの切断処理
'//////////////////////////////

Public Sub ORACLE_CLOSE()

    If ORACLE_OPEN_SW = 1 Then     '接続している場合しか実行しない
    
        oraCon.Close
        Set oraCon = Nothing
    
        ORACLE_OPEN_SW = 0         'オラクル接続スイッチの初期化
    
    End If
    
End Sub

'////////////////////////////////////////////
'// 登録品番（マスタ）情報の表示
'//------------------------------------
'//　※コマンドボタン１で呼び出す
'//
'////////////////////////////////////////////

Sub MAST_DISP()

    '=====================
    'オラクル接続
    '=====================
    Call ORACLE_OPEN
    
    '検索管理年月のセット
    Dim KANRYM As String
    KANRYM = Worksheets("DATA").Range("B6").Value
    
    '内作品番セット
    Dim TKCODE As String    '得意先
    Dim SYUHIN As String    '得意先品目
    Dim HINBAN As String    '内作品番
    Dim HENKAN As String    '得意先品目任意変換値
    TKCODE = Worksheets("DATA").Range("B3").Value
    SYUHIN = Worksheets("DATA").Range("B4").Value
    HENKAN = Worksheets("DATA").Range("B5").Value
    HINBAN = NAISAK_GET(TKCODE, SYUHIN, HENKAN, KANRYM)
    
    If HINBAN = "" Then
        
        MsgBox "内作品目が見つかりません"
    
    Else
        '内作品番をDATAシートに移送
        Worksheets("DATA").Range("B8").Value = HINBAN
    
        '検索品目のセット
        Dim DIX As Integer
        Dim YYMMDD As String
        YYMMDD = Worksheets("DATA").Range("E8").Value
    
        '=====================
        'セルの消去
        '=====================
        Call CELL_CLR1
        
        'トータル行のクリア
        Erase total_arry1
        Erase total_arry2
        Erase total_arry3
        Erase total_arry4
        Erase total_arry5
    
        '代替品目リストの初期化
        Erase BK_HINBAN()
    
        '=====================
        '出荷品番部分出力
        '=====================
        IX1 = 4
        CUST_ITEM_CNT = HINBAN_GET1(HINBAN, HENKAN, YYMMDD)      'ここでM_ITEMを参照して代替品番のリスト（BK_HINBAN）を作る
        
        '複数の出荷品番が存在したらトータル行も出力する
        If CUST_ITEM_CNT > 1 Then
            IX1 = IX1 + 6
            Call TOTAL_LINE_SET '書式のセット
        Else
            IX1 = IX1 + 1
        End If
        
        IX1 = IX1 + 1

        '代替品番も含めてぶら下がっている工程は全て出力する。※但し同一の工程が重複している場合は表示しない
        DIX = 0
        Do Until DIX > 12
    
            If BK_HINBAN(DIX) <> "" Then
        
                '==============================
                '工程/入荷品番部の取得＆表示
                '==============================
                Call KOTEI_GET2(BK_HINBAN(DIX), KANRYM)
            Else
                Exit Do
            End If
            DIX = DIX + 1
        Loop
        
    End If
    
    '=====================
    'オラクル切断
    '=====================
    Call ORACLE_CLOSE
    
    '行の最大値をセルに保持しておく
    Worksheets("DATA").Range("AK3") = IX1

End Sub


'////////////////////////////////////////////
'// 実績データを表示する
'//------------------------------------
'//　※コマンドボタン２で呼び出す
'//
'////////////////////////////////////////////

Sub DATA_DISP()
    
    '検索管理年月のセット
    Dim KANRYM As String
    KANRYM = Worksheets("DATA").Range("B6").Value
    
    '=====================
    'オラクル接続
    '=====================
    Call ORACLE_OPEN
    
    '=====================
    'カレンダ参照
    '=====================
    Call CALEN_SET(KANRYM)
    
    '=====================
    'セルの消去
    '=====================
    Call CELL_CLR2
    
    'トータル行のクリア
    Erase total_arry1
    Erase total_arry2
    Erase total_arry3
    Erase total_arry4
    Erase total_arry5
    
    Dim TKCODE As String    '得意先コード
    Dim SICODE As String    '仕入先コード
    Dim HINBAN As String    '（品番）／（品番＋仕入先）
    
    Dim LIX As Integer
    Dim MAX As Integer
    
    MAX = Val(Worksheets("DATA").Range("AK3").Value)    '最大行数をゲット
    
    LIX = 9
    Do While LIX < MAX
    
        Select Case Worksheets("DATA").Range("A" & LIX).Value
            Case "得意先"
                    
                    TKCODE = CStr(Worksheets("DATA").Range("B" & LIX).Value)          '得意先コード
                    'HINBAN = CStr(Worksheets("DATA").Range("B" & LIX + 2).Value)     '出荷品番
                    HINBAN = CStr(Worksheets("DATA").Range("B8").Value)               '内作品番
                    
                    '================================
                    ' 内示受注データ呼び出し＆出力
                    '================================
                    Call NAIJI_GET1(LIX, TKCODE, HINBAN, KANRYM)
                    
                    '================================
                    ' 確定受注データ呼び出し＆出力
                    '================================
                    Call JUCHUZAN_GET(LIX + 1, TKCODE, HINBAN, KANRYM)
                    Call KAKUTEI_GET1(LIX + 1, TKCODE, HINBAN, KANRYM)
                    
                    '================================
                    ' 統合受注データ呼び出し＆出力
                    '================================
                    Call TOUGOU_GET1(LIX + 2, TKCODE, HINBAN, KANRYM)
                    
                    '================================
                    ' 出荷データ呼び出し＆出力
                    '================================
                    Call SKDATA_GET(LIX + 3, TKCODE, HINBAN, KANRYM)
                    
                    '================================
                    ' 仮売上データ呼び出し＆出力
                    '================================
                    Call URIAGE_GET(LIX + 4, TKCODE, HINBAN, KANRYM)

                    LIX = LIX + 6   '以下の行は、次の行（得意先）が発生するまで跳ばす
            
            Case "ＴＯＴＡＬ"
                    Call TOTAL_PUT(LIX)
                    LIX = LIX + 6   '以下の行は、次の行（得意先）が発生するまで跳ばす
                    
            Case "仕入先"
            
                    SICODE = CStr(Worksheets("DATA").Range("B" & LIX).Value)        '仕入先コード
                    HINBAN = CStr(Worksheets("DATA").Range("B" & LIX + 2).Value)    '入荷品番
                    

                    '================================
                    ' 内示発注データ呼び出し＆出力
                    '================================
                    Call NAIJI_GET2(LIX, SICODE, HINBAN, KANRYM)                    '月次発注ワークの情報
                    '//Call HACDAT_GET1(LIX, SICODE, HINBAN, KANRYM)                '発注残データの参照
                    
                    '================================
                    ' 所要量データ呼び出し＆出力
                    '================================
                    Call SYOYOU_GET(LIX + 1, SICODE, HINBAN, KANRYM)
                    
                    '================================
                    ' 確定発注残データ呼び出し＆出力
                    '================================
                    Call CHUZAN_GET(LIX + 2, SICODE, HINBAN, KANRYM)
                    '================================
                    ' 確定発注データ呼び出し＆出力
                    '================================
                    Call KAKUTEI_GET2(LIX + 2, SICODE, HINBAN, KANRYM)
                    
                    '================================
                    ' 入荷データ呼び出し＆出力
                    '================================
                    Call NYDATA_GET(LIX + 3, SICODE, HINBAN, KANRYM)
        
                    LIX = LIX + 6   '以下の行は、次の行（仕入先）が発生するまで跳ばす
            Case Else
            
                    LIX = LIX + 1   '見つからない場合は、一行づつカウントする
            
        End Select
        
    Loop

    '=====================
    'オラクル切断
    '=====================
    Call ORACLE_CLOSE
    

End Sub

'//////////////////////////////
'// 工程情報を表示する
'//////////////////////////////

Sub KOTEI_GET2(ByVal HINBAN As String, ByVal KANRYM As String)
    
    
    Dim HEN_YYMMDD As String
    'HEN_YYMMDD = KANRYM & "/01"
    HEN_YYMMDD = Worksheets("DATA").Range("E8").Value
    
    Dim strSQL As String
    
    Dim NAIGAI As String  '内外製区分
    Dim TEBAN As Integer   '手番
    Dim ANZEN As Integer   '安全在庫
    Dim SICODE As Integer  '仕入先コード
    Dim SINAME As String   '仕入先名
       
    
    '//工程情報取得用ＳＱＬ文生成
    strSQL = "SELECT * "
    strSQL = strSQL & " FROM ("
    strSQL = strSQL & "   select"
    strSQL = strSQL & "     LEVEL              as KAISO,"
    strSQL = strSQL & "     ps1.PARENT_ITEM_CD as PARENT_ITEM_CD,"
    strSQL = strSQL & "     ps1.COMP_ITEM_CD as COMP_ITEM_CD,"
    strSQL = strSQL & "     ps1.PS_EDITION as PS_EDITION,"
    strSQL = strSQL & "     ps1.EFF_PHASE_IN_DATE as IN_DATE,"
    strSQL = strSQL & "     ps1.EFF_PHASE_OUT_DATE as OUT_DATE"
    strSQL = strSQL & "  from (select * from M_PS where TO_DATE('" & HEN_YYMMDD & "','YYYY/MM/DD') < = EFF_PHASE_OUT_DATE"
    strSQL = strSQL & "    and EFF_PHASE_IN_DATE <= TO_DATE('" & HEN_YYMMDD & "','YYYY/MM/DD')) ps1 start with ps1.PARENT_ITEM_CD ='" & HINBAN & "'"
    strSQL = strSQL & "       connect by prior ps1.COMP_ITEM_CD = ps1.PARENT_ITEM_CD)"
 
 '   MsgBox (strSQL)
 '   With Worksheets("DATA").Cells(1, 6)
 '           .Interior.ColorIndex = 44
 '           .NumberFormat = "@"
 '           .Value = strSQL
 '   End With
 
    oraRs.Open strSQL, oraCon

    'EOFまでループ
    IX1 = IX1 + 5
    Do Until oraRs.EOF
    
        '既に表示した品番以外を表示する
        If DOUITSU(oraRs!COMP_ITEM_CD) = 0 Then
        
            '===========================
            '品目情報参照
            '===========================
            Call HINBAN_GET2(oraRs!COMP_ITEM_CD)
        
            '===========================
            '仕入先情報参照
            '===========================
            Call SICODE_GET2(oraRs!COMP_ITEM_CD)
        
        
            If KOTEI_MEISAI(5) = "2" Then
                
                '工程情報をシートに移送
                Worksheets("DATA").Cells(IX1, 2) = KOTEI_MEISAI(0)                       '仕入先コード
                Worksheets("DATA").Cells(IX1, 3) = "入荷"                                '得意先/仕入先区分
                Worksheets("DATA").Cells(IX1 + 1, 2) = KOTEI_MEISAI(1)                   '仕入先名
                Worksheets("DATA").Cells(IX1 + 2, 2) = oraRs!COMP_ITEM_CD                '仕入先品番
                Worksheets("DATA").Cells(IX1 + 2, 3) = "'(" & oraRs!KAISO & ")"          '階層
                Worksheets("DATA").Cells(IX1 + 3, 2) = KOTEI_MEISAI(6)                   '発注区分（加工依頼orかんばん）
                Worksheets("DATA").Cells(IX1 + 3, 3) = KOTEI_MEISAI(7)                   '保管区
                Worksheets("DATA").Cells(IX1 + 4, 2) = HINBAN                            '上位品番
                Worksheets("DATA").Cells(IX1 + 4, 5) = funZaikoGET(oraRs!COMP_ITEM_CD)   '手持在庫
                Worksheets("DATA").Cells(IX1 + 5, 2) = KOTEI_MEISAI(3)                   '手番
                Worksheets("DATA").Cells(IX1 + 5, 3) = KOTEI_MEISAI(4)                   '安全在庫
                '===========================
                '工程の書式出力
                '===========================
                Call KOTEI_LINE_SET
            
                IX1 = IX1 + 7
            End If
        
        End If
        oraRs.MoveNext
        
    Loop
    
    'レコードセットＣＬＯＳＥ
    oraRs.Close
    Set oraRs = Nothing

 
End Sub

'//////////////////////////////
'// 既に表示した品番かチェックする
'// 戻り値　0 = ない  1 = 表示済み
'//////////////////////////////
Function DOUITSU(ByVal NYUHIN As String) As Integer

    DOUITSU = 0
    
    Dim DIX As Integer
    
    DIX = 9
    Do While DIX > IX1
        If Worksheets("DATA").RAGE("A" & DIX) = "品番" Then
            If Worksheets("DATA").RAGE("B" & DIX) = NYUHIN Then
                DOUITSU = 1
                Exit Do
        
            End If
        End If
        DIX = DIX + 1
    Loop

End Function

'//////////////////////////////
'// 得意先品番の取得
'//////////////////////////////
Public Function HINBAN_GET1(ByVal HINBAN As String, ByVal HENKAN As String, ByVal HEN_YYMMDD As String) As Integer
    
    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    Dim HINBAN2 As String
    
    HINBAN2 = CStr(HINBAN)
    
    '得意先品番情報取得ＳＱＬ生成
    strSQL2 = "SELECT "
    strSQL2 = strSQL2 & "       M_CUST_ITEM.CUST_CD AS CUST_CD,"
    strSQL2 = strSQL2 & "       M_CUST.CUST_ANAME AS CUST_ANAME,"
    strSQL2 = strSQL2 & "       M_CUST_ITEM.CUST_ITEM_CD AS CUST_ITEM_CD,"
    strSQL2 = strSQL2 & "       M_CUST_ITEM.DLV_LOC_CD AS DLV_CD,"
    strSQL2 = strSQL2 & "       M_CUST_ITEM.ITEM_CD AS ITEM_CD "
    strSQL2 = strSQL2 & " FROM "
    strSQL2 = strSQL2 & "       M_CUST_ITEM , M_CUST"
    strSQL2 = strSQL2 & " WHERE "
    strSQL2 = strSQL2 & "       M_CUST_ITEM.CUST_CD = M_CUST.CUST_CD AND M_CUST_ITEM.DLV_LOC_CD = '*'"
    strSQL2 = strSQL2 & "   AND M_CUST_ITEM.ITEM_CD = '" & HINBAN2 & "'"
    strSQL2 = strSQL2 & "   AND M_CUST_ITEM.ITEM_CD_OPTION_CHANGE_VALUE = '" & HENKAN & "'"
    strSQL2 = strSQL2 & "   AND TO_DATE('" & HEN_YYMMDD & "','YYYY/MM/DD') < = M_CUST_ITEM.EFF_PHASE_OUT_DATE"
    strSQL2 = strSQL2 & "   AND M_CUST_ITEM.EFF_PHASE_IN_DATE <= TO_DATE('" & HEN_YYMMDD & "','YYYY/MM/DD')"
    
    
    oraRs2.Open strSQL2, oraCon

    Dim CNT As Integer
    CNT = 0
    Do Until oraRs2.EOF
    
        '===========================
        '代替品番リストの更新
        '===========================
        Call HINBAN_list(oraRs2!ITEM_CD)
        
        IX1 = IX1 + 6
        Worksheets("DATA").Cells(IX1, 2) = Val(oraRs2!CUST_CD)
        Worksheets("DATA").Cells(IX1, 3) = "出荷"                       '得意先/仕入先区分
        Worksheets("DATA").Cells(IX1 + 1, 2) = oraRs2!CUST_ANAME        '得意先名
        Worksheets("DATA").Cells(IX1 + 2, 2) = oraRs2!CUST_ITEM_CD      '得意先品目番号
        Worksheets("DATA").Cells(IX1 + 4, 2) = BK_TEBAN                 '手番
        Worksheets("DATA").Cells(IX1 + 4, 3) = BK_ANZEN                 '安全在庫
        Worksheets("DATA").Cells(IX1 + 5, 5) = funZaikoGET(HINBAN)      '手持在庫(内作品番で検索）
        
        Call SYUKA_LINE_SET '書式のセット
        
        oraRs2.MoveNext
        CNT = CNT + 1
    Loop
    
    oraRs2.Close
    Set oraRs2 = Nothing
    
    HINBAN_GET1 = CNT
    
End Function



'// ============================================
'//
'// 得意先品番から社内品番を検索して返す関数
'//
'//  2022.08.05 見つからなかった場合はNULLを返す
'//  2022.09.20 得意先任意変換値の条件に含める（ＧＤＩ４の対応）
'// ============================================
Public Function NAISAK_GET(ByVal TKCODE As String, ByVal HINBAN As String, ByVal HENKAN As String, ByVal KANRYM As String) As String
    
    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    Dim HEN_YYMMDD As String
    'HEN_YYMMDD = KANRYM
    HEN_YYMMDD = Worksheets("DATA").Range("E8").Value   '本日をもって来る（品番有効日を判断する為に）
    NAISAK_GET = ""
    
    '得意先品番情報取得ＳＱＬ生成
    strSQL2 = "SELECT "
    strSQL2 = strSQL2 & "    M_CUST_ITEM.CUST_CD AS 得意先コード,"
    strSQL2 = strSQL2 & "    M_CUST_ITEM.CUST_ITEM_CD AS 得意先品目番号,"
    strSQL2 = strSQL2 & "    M_CUST_ITEM.ITEM_CD AS 品目番号"
    strSQL2 = strSQL2 & " FROM "
    strSQL2 = strSQL2 & "    M_CUST_ITEM "
    strSQL2 = strSQL2 & " WHERE"
    strSQL2 = strSQL2 & "     M_CUST_ITEM.CUST_CD = '" & CStr(TKCODE) & "' "
    strSQL2 = strSQL2 & " AND M_CUST_ITEM.DLV_LOC_CD = '*'"
    strSQL2 = strSQL2 & " AND M_CUST_ITEM.CUST_ITEM_CD = '" & CStr(HINBAN) & "' "
    strSQL2 = strSQL2 & " AND M_CUST_ITEM.ITEM_CD_OPTION_CHANGE_VALUE = '" & CStr(HENKAN) & "' "
    strSQL2 = strSQL2 & " AND TO_DATE('" & HEN_YYMMDD & "','YYYY/MM/DD') < = M_CUST_ITEM.EFF_PHASE_OUT_DATE"
    strSQL2 = strSQL2 & " AND M_CUST_ITEM.EFF_PHASE_IN_DATE <= TO_DATE('" & HEN_YYMMDD & "','YYYY/MM/DD')"
    
    'Worksheets("DATA").Range("J3").Value = strSQL2    'ＳＱＬチェック用
    
    oraRs2.Open strSQL2, oraCon
    
    Do Until oraRs2.EOF
        NAISAK_GET = oraRs2!品目番号
        oraRs2.MoveNext
    Loop
    
    oraRs2.Close
    Set oraRs2 = Nothing
        
End Function

'//////////////////////////////
'// 代替品番の取得 M_ITEMより
'//////////////////////////////
Public Sub HINBAN_list(ByVal HINBAN As String)
    
    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    
    Dim MIX As Integer
    Dim CIX As Integer
    Dim CHK_HINBAN As String
    Dim ITEM As Variant

    '品目マスタ報取得ＳＱＬ生成
    strSQL2 = "SELECT "
    strSQL2 = strSQL2 & "ITEM_CD,"
    strSQL2 = strSQL2 & "ITEM_NAME,"
    strSQL2 = strSQL2 & "HIGH_LEVEL_NO,"
    strSQL2 = strSQL2 & "SUB_ITEM_CD_01,"
    strSQL2 = strSQL2 & "SUB_ITEM_CD_02,"
    strSQL2 = strSQL2 & "SUB_ITEM_CD_03,"
    strSQL2 = strSQL2 & "SUB_ITEM_CD_04,"
    strSQL2 = strSQL2 & "SUB_ITEM_CD_05,"
    strSQL2 = strSQL2 & "FIXED_LT,"
    strSQL2 = strSQL2 & "SAFETY_STOCK,"
    strSQL2 = strSQL2 & "KANBAN_FLG "
    strSQL2 = strSQL2 & "FROM "
    strSQL2 = strSQL2 & "M_ITEM "
    strSQL2 = strSQL2 & "WHERE "
    strSQL2 = strSQL2 & "ITEM_CD = '" & HINBAN & "'"
    oraRs2.Open strSQL2, oraCon

    CIX = 0
    BK_HINBAN(0) = HINBAN   'リストの先頭は代表品目を入れる
    
    Do Until oraRs2.EOF
    
        '手番と安全在庫（完成品）を取得する。
        BK_TEBAN = Val(oraRs2!FIXED_LT)
        BK_ANZEN = Val(oraRs2!SAFETY_STOCK)
        
        '代替品番をリスト化する
        CIX = CIX + 1
        For CIX = 1 To 5
            Select Case CIX
                Case 1
                    If IsNull(oraRs2!SUB_ITEM_CD_01) = False Then
                        CHK_HINBAN = oraRs2!SUB_ITEM_CD_01
                    End If
                Case 2
                    If IsNull(oraRs2!SUB_ITEM_CD_02) = False Then
                        CHK_HINBAN = oraRs2!SUB_ITEM_CD_02
                    End If
                Case 3
                    If IsNull(oraRs2!SUB_ITEM_CD_03) = False Then
                        CHK_HINBAN = oraRs2!SUB_ITEM_CD_03
                    End If
                Case 4
                    If IsNull(oraRs2!SUB_ITEM_CD_04) = False Then
                        CHK_HINBAN = oraRs2!SUB_ITEM_CD_04
                    End If
                Case 5
                    If IsNull(oraRs2!SUB_ITEM_CD_05) = False Then
                        CHK_HINBAN = oraRs2!SUB_ITEM_CD_05
                    End If
            End Select
        
            If CHK_HINBAN <> "" Then
                
                '重複しないようにチェック
                For MIX = 0 To 12
                    If BK_HINBAN(MIX) = CHK_HINBAN Then
                        Exit For
                    Else
                        If BK_HINBAN(MIX) = "" Then
                            BK_HINBAN(MIX) = CHK_HINBAN
                            Exit For
                        End If
                    End If
                Next
            
            End If
        Next
        oraRs2.MoveNext
    Loop
    
    oraRs2.Close
    Set oraRs2 = Nothing
    
    
End Sub


'//////////////////////////////
'// 工程品番の取得
'//////////////////////////////
Sub HINBAN_GET2(ByVal HINBAN As String)

    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    Dim HINBAN2 As String
    Dim HCkbn   As String
    
    HINBAN2 = CStr(HINBAN)
    
    '工程品番情報取得ＳＱＬ生成
    strSQL2 = "SELECT FIXED_LT,SAFETY_STOCK,OUTSIDE_TYP,PROCESS_REQUEST_ISS_TYP,KANBAN_FLG FROM M_ITEM WHERE ITEM_CD = '" & HINBAN2 & "'"
    oraRs2.Open strSQL2, oraCon

    Do Until oraRs2.EOF
        KOTEI_MEISAI(3) = oraRs2!FIXED_LT                   '品目マスタの手番
        KOTEI_MEISAI(4) = oraRs2!SAFETY_STOCK               '品目マスタの安全在庫
        KOTEI_MEISAI(5) = oraRs2!OUTSIDE_TYP                '内外製区分
        
        
        If oraRs2!PROCESS_REQUEST_ISS_TYP = "1" Then         '加工依頼区分
            KOTEI_MEISAI(6) = "加工依頼"
        Else
            If oraRs2!KANBAN_FLG = "1" Then
                KOTEI_MEISAI(6) = "かんばん"                'かんばん発注対象フラグ
            Else
                KOTEI_MEISAI(6) = ""
            End If
        End If
        
        oraRs2.MoveNext
    Loop
    
    oraRs2.Close
    Set oraRs2 = Nothing

End Sub

'//////////////////////////////
'// 仕入先の取得
'// 2023/11/16　参照テーブルを購入単価ヘッダーに変更
'//////////////////////////////
Sub SICODE_GET2(ByVal HINBAN As String)

    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    Dim HINBAN2 As String
    
    HINBAN2 = CStr(HINBAN)
    
    '仕入先情報取得ＳＱＬ生成
    strSQL2 = "SELECT "
    strSQL2 = strSQL2 & "       M_PUCH_UNIT_COST_H.ITEM_CD as ITEM,"        '品目
    strSQL2 = strSQL2 & "       M_PUCH_UNIT_COST_H.VEND_CD as SICODE,"      '仕入先
    strSQL2 = strSQL2 & "       M_VEND_CTRL.VEND_ANAME     as SINAME,"      '仕入先名
    strSQL2 = strSQL2 & "       NVL(M_ITEM_RCV_WH.WH_CD,'？') as HOKANKU"      '保管区 ※NULLの場合は？にする。
    strSQL2 = strSQL2 & "  FROM"
    strSQL2 = strSQL2 & "      ( M_PUCH_UNIT_COST_H LEFT JOIN M_VEND_CTRL"
    strSQL2 = strSQL2 & "        ON M_PUCH_UNIT_COST_H.VEND_CD = M_VEND_CTRL.VEND_CD )"
    strSQL2 = strSQL2 & "       LEFT JOIN M_ITEM_RCV_WH"
    strSQL2 = strSQL2 & "       ON M_PUCH_UNIT_COST_H.ITEM_CD = M_ITEM_RCV_WH.ITEM_CD"
    strSQL2 = strSQL2 & "  WHERE"
    strSQL2 = strSQL2 & "       M_PUCH_UNIT_COST_H.ITEM_CD = '" & HINBAN2 & "'"
    oraRs2.Open strSQL2, oraCon
    
    Do Until oraRs2.EOF
        KOTEI_MEISAI(0) = oraRs2!SICODE
        KOTEI_MEISAI(1) = oraRs2!SINAME
        KOTEI_MEISAI(2) = oraRs2!ITEM
        KOTEI_MEISAI(7) = oraRs2!HOKANKU
        oraRs2.MoveNext
    Loop
    
    oraRs2.Close
    Set oraRs2 = Nothing

End Sub

'//////////////////////////////
'// 内示受注の取得
'//////////////////////////////

Sub NAIJI_GET1(ByVal IX As Integer, ByVal TKCODE As String, ByVal HINBAN As String, ByVal KANRYM As String)

    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    Dim DIX As Integer
    
    '内示受注情報取得ＳＱＬ生成
    strSQL2 = "SELECT "
    strSQL2 = strSQL2 & "CUST_CD AS TKCODE,"
    strSQL2 = strSQL2 & "CUST_ITEM_CD AS SYUHIN,"
    strSQL2 = strSQL2 & "TO_CHAR(UNCNFM_REQUIRED_DATE,'yyyy/mm/dd') AS JUDATE,"
    strSQL2 = strSQL2 & "SUM(UNCNFM_REQUIRED_QTY) AS SURYO,"
    strSQL2 = strSQL2 & "DEL_FLG As DELFLG "
    strSQL2 = strSQL2 & "FROM"
    strSQL2 = strSQL2 & " T_UNCNFM_ODR "
    strSQL2 = strSQL2 & "WHERE"
    strSQL2 = strSQL2 & " CUST_CD = '" & TKCODE & "'"
    strSQL2 = strSQL2 & " AND ITEM_CD = '" & HINBAN & "'"
    strSQL2 = strSQL2 & " AND TO_CHAR(UNCNFM_REQUIRED_DATE,'yyyy/mm/dd') LIKE '" & KANRYM & "%'"
    strSQL2 = strSQL2 & " AND DEL_FLG = '0' "
    strSQL2 = strSQL2 & "Group BY "
    strSQL2 = strSQL2 & "CUST_CD,"
    strSQL2 = strSQL2 & "CUST_ITEM_CD,"
    strSQL2 = strSQL2 & "TO_CHAR(UNCNFM_REQUIRED_DATE,'yyyy/mm/dd'),"
    strSQL2 = strSQL2 & "DEL_FLG"
    'Worksheets("DATA").Range("J3").Value = strSQL2    'ＳＱＬチェック用
    
    oraRs2.Open strSQL2, oraCon
    
    Do Until oraRs2.EOF
        DIX = Val(Mid(oraRs2!JUDATE, 9, 2)) + 6
        With Worksheets("DATA").Cells(IX, DIX)
            .NumberFormat = "#,###"
            .Value = Val(oraRs2!SURYO)
        End With
        
        '集計行用
        DIX = DIX - 6
        total_arry1(DIX) = total_arry1(DIX) + Val(oraRs2!SURYO)
        
        oraRs2.MoveNext
    Loop
    
    oraRs2.Close
    Set oraRs2 = Nothing

End Sub

'//////////////////////////////
'// 確定受注の取得
'//////////////////////////////

Sub KAKUTEI_GET1(ByVal IX As Integer, ByVal TKCODE As String, ByVal HINBAN As String, ByVal KANRYM As String)

    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    Dim DIX As Integer
    
    '確定受注情報取得ＳＱＬ生成
    strSQL2 = "SELECT "
    strSQL2 = strSQL2 & "T_ODR.CUST_CD AS TKCODE,"
    strSQL2 = strSQL2 & "T_ODR.CUST_ITEM_CD AS SYUHIN,"
    strSQL2 = strSQL2 & "TO_CHAR(T_ODR.DESINATED_DLV_DATE,'yyyy/mm/dd') AS JDATE,"
    strSQL2 = strSQL2 & "SUM(T_ODR.ODR_QTY) AS JSURYO "
    strSQL2 = strSQL2 & " FROM "
    strSQL2 = strSQL2 & "      T_ODR "
    strSQL2 = strSQL2 & "WHERE "
    strSQL2 = strSQL2 & "      T_ODR.CUST_CD = '" & TKCODE & "'"
    strSQL2 = strSQL2 & "  AND T_ODR.ITEM_CD = '" & HINBAN & "'"
    strSQL2 = strSQL2 & "  AND TO_CHAR(T_ODR.DESINATED_DLV_DATE,'yyyy/mm/dd') LIKE '" & KANRYM & "%'"
    strSQL2 = strSQL2 & "  AND T_ODR.DEL_FLG != '1' "
    strSQL2 = strSQL2 & " Group BY "
    strSQL2 = strSQL2 & "    T_ODR.CUST_CD,"
    strSQL2 = strSQL2 & "    T_ODR.CUST_ITEM_CD,"
    strSQL2 = strSQL2 & "    TO_CHAR(T_ODR.DESINATED_DLV_DATE,'yyyy/mm/dd')"
    
    oraRs2.Open strSQL2, oraCon
    
    Do Until oraRs2.EOF
        DIX = Val(Mid(oraRs2!JDATE, 9, 2)) + 6
        With Worksheets("DATA").Cells(IX, DIX)
            .NumberFormat = "#,###"
            .Value = Val(oraRs2!JSURYO)
        End With
        
        '集計行用
        DIX = DIX - 6
        total_arry2(DIX) = total_arry2(DIX) + Val(oraRs2!JSURYO)
        
        oraRs2.MoveNext
    Loop
    
    oraRs2.Close
    Set oraRs2 = Nothing

End Sub

'//////////////////////////////
'// 確定受注(前月以前の有効な受注残取得)
'////////////////////////////

Sub JUCHUZAN_GET(ByVal IX As Integer, ByVal TKCODE As String, ByVal HINBAN As String, ByVal KANRYM As String)

    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    Dim DIX As Integer
    
    '確定受注情報取得ＳＱＬ生成
    strSQL2 = "SELECT "
    strSQL2 = strSQL2 & "            T_ODR.CUST_CD                                   AS TKCODE,"
    strSQL2 = strSQL2 & "            T_ODR.CUST_ITEM_CD                              AS SYUHIN,"
    strSQL2 = strSQL2 & "            SUM(T_ODR.ODR_QTY)                              AS JSURYO,"
    strSQL2 = strSQL2 & "            SUM(T_ODR.TOTAL_SHIP_QTY)                       AS SSURYO,"
    strSQL2 = strSQL2 & "            SUM(T_ODR.ODR_QTY) - SUM(T_ODR.TOTAL_SHIP_QTY)  AS ZANSU"
    strSQL2 = strSQL2 & "      FROM"
    strSQL2 = strSQL2 & "            T_ODR"
    strSQL2 = strSQL2 & "      WHERE"
    strSQL2 = strSQL2 & "            T_ODR.CUST_CD = '" & TKCODE & "'"
    strSQL2 = strSQL2 & "        AND T_ODR.ITEM_CD = '" & HINBAN & "'"
    strSQL2 = strSQL2 & "        AND TO_CHAR(T_ODR.DESINATED_DLV_DATE,'yyyy/mm/dd') <=  '2022/10/01'"
    strSQL2 = strSQL2 & "        AND T_ODR.ODR_CMPLT_FLG !='1'"
    strSQL2 = strSQL2 & "        AND T_ODR.DEL_FLG != '1'"
    strSQL2 = strSQL2 & "      Group BY"
    strSQL2 = strSQL2 & "          T_ODR.CUST_CD,"
    strSQL2 = strSQL2 & "          T_ODR.CUST_ITEM_CD"
    
    oraRs2.Open strSQL2, oraCon
    
    Dim CALC_ZANSU As Long
    Do Until oraRs2.EOF
        CALC_ZANSU = CALC_ZANSU + Val(oraRs2!ZANSU)
        oraRs2.MoveNext
    Loop
    
    With Worksheets("DATA").Cells(IX, 6)
        .NumberFormat = "#,###"
        .Value = CALC_ZANSU
        
        '集計行用
        total_arry2(0) = total_arry2(0) + CALC_ZANSU
        
    End With
    
    oraRs2.Close
    Set oraRs2 = Nothing

End Sub

'//////////////////////////////
'// 統合受注の取得
'//////////////////////////////

Sub TOUGOU_GET1(ByVal IX As Integer, ByVal TKCODE As String, ByVal HINBAN As String, ByVal KANRYM As String)

    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    Dim DIX As Integer
    Dim CHK_DAT As String
        
    '統合受注情報取得ＳＱＬ生成
    strSQL2 = "SELECT "
    strSQL2 = strSQL2 & "  T_UNITE_ODR.CUST_CD                               AS CUST_CD,"
    strSQL2 = strSQL2 & "  T_UNITE_ODR.CUST_ITEM_CD                          AS CUST_ITEM,"
    strSQL2 = strSQL2 & "  T_UNITE_ODR.ITEM_CD                               AS ITEM,"
    strSQL2 = strSQL2 & "  TO_CHAR(T_UNITE_ODR.SHIP_PLAN_DATE,'yyyy/mm/dd')  AS JDATE,"
    strSQL2 = strSQL2 & "  SUM(T_UNITE_ODR.REQUIRED_QTY)                     As JSURYO"
    strSQL2 = strSQL2 & " FROM"
    strSQL2 = strSQL2 & "  T_UNITE_ODR"
    strSQL2 = strSQL2 & " WHERE"
    strSQL2 = strSQL2 & "  T_UNITE_ODR.DEL_FLG = '0'"
    strSQL2 = strSQL2 & "  AND T_UNITE_ODR.CUST_CD = '" & TKCODE & "'"
    strSQL2 = strSQL2 & "  AND T_UNITE_ODR.ITEM_CD = '" & HINBAN & "'"
    strSQL2 = strSQL2 & "  AND TO_CHAR(T_UNITE_ODR.SHIP_PLAN_DATE,'yyyy/mm/dd') LIKE '" & KANRYM & "%'"
    strSQL2 = strSQL2 & " Group BY"
    strSQL2 = strSQL2 & "  T_UNITE_ODR.CUST_CD,"
    strSQL2 = strSQL2 & "  T_UNITE_ODR.CUST_ITEM_CD,"
    strSQL2 = strSQL2 & "  T_UNITE_ODR.ITEM_CD,"
    strSQL2 = strSQL2 & "  TO_CHAR(T_UNITE_ODR.SHIP_PLAN_DATE,'yyyy/mm/dd')"
    
    'Worksheets("DATA").Range("J3").Value = strSQL2    'ＳＱＬチェック用
    
    oraRs2.Open strSQL2, oraCon
    
    Do Until oraRs2.EOF
        CHK_DAT = oraRs2!JDATE
        DIX = Val(Mid(oraRs2!JDATE, 9, 2)) + 6
        With Worksheets("DATA").Cells(IX, DIX)
            .NumberFormat = "#,###"
            .Value = Val(oraRs2!JSURYO)
        End With
        
        '集計行用
        DIX = DIX - 6
        total_arry3(DIX) = total_arry3(DIX) + Val(oraRs2!JSURYO)
        
        oraRs2.MoveNext
    Loop
    
    oraRs2.Close
    Set oraRs2 = Nothing

End Sub

'//////////////////////////////
'// 出荷実績の取得
'//////////////////////////////

Sub SKDATA_GET(ByVal IX As Integer, ByVal TKCODE As String, ByVal HINBAN As String, ByVal KANRYM As String)

    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    Dim DIX As Integer
    
    '出荷実績情報取得ＳＱＬ生成
    strSQL2 = "SELECT "
    strSQL2 = strSQL2 & "T_SHIP.CUST_CD AS TKCODE,"
    strSQL2 = strSQL2 & "T_SHIP.CUST_ITEM_CD AS SYUHIN,"
    strSQL2 = strSQL2 & "TO_CHAR(T_SHIP.SHIP_DATE,'yyyy/mm/dd') AS SDATE,"
    strSQL2 = strSQL2 & "SUM(T_SHIP.SHIP_QTY) AS SSURYO,"
    strSQL2 = strSQL2 & "T_SHIP.ITEM_CD AS HINBAN "
    strSQL2 = strSQL2 & "FROM "
    strSQL2 = strSQL2 & "T_SHIP "
    strSQL2 = strSQL2 & "WHERE "
    strSQL2 = strSQL2 & "T_SHIP.CUST_CD = '" & TKCODE & "'"
    'strSQL2 = strSQL2 & " AND T_SHIP.CUST_ITEM_CD = '" & HINBAN & "'"
    strSQL2 = strSQL2 & " AND T_SHIP.ITEM_CD = '" & HINBAN & "'"
    strSQL2 = strSQL2 & " AND TO_CHAR(T_SHIP.SHIP_DATE,'yyyy/mm/dd') LIKE '" & KANRYM & "%'"
    strSQL2 = strSQL2 & " AND T_SHIP.DEL_FLG != 1 "
    strSQL2 = strSQL2 & "Group BY "
    strSQL2 = strSQL2 & "T_SHIP.CUST_CD,"
    strSQL2 = strSQL2 & "T_SHIP.CUST_ITEM_CD,"
    strSQL2 = strSQL2 & "T_SHIP.ITEM_CD,"
    strSQL2 = strSQL2 & "TO_CHAR(T_SHIP.SHIP_DATE,'yyyy/mm/dd')"
    
    oraRs2.Open strSQL2, oraCon
    
    Do Until oraRs2.EOF
        DIX = Val(Mid(oraRs2!SDATE, 9, 2)) + 6
        With Worksheets("DATA").Cells(IX, DIX)
            .NumberFormat = "#,###"
            .Value = Val(oraRs2!SSURYO)
        End With
    
        '集計行用
        DIX = DIX - 6
        total_arry4(DIX) = total_arry4(DIX) + Val(oraRs2!SSURYO)
        
        oraRs2.MoveNext
    
    Loop
    
    oraRs2.Close
    Set oraRs2 = Nothing

End Sub



'//////////////////////////////
'// 仮売上実績の取得
'// その他売上も含めて確認したいだげな（2023/04/27）
'//////////////////////////////

Sub URIAGE_GET(ByVal IX As Integer, ByVal TKCODE As String, ByVal HINBAN As String, ByVal KANRYM As String)

    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    Dim DIX As Integer
    
    '仮売上取得ＳＱＬ生成
    strSQL2 = "SELECT "
    strSQL2 = strSQL2 & "       T_SALES_TEMP.CUST_CD                          AS TKCODE,"
    strSQL2 = strSQL2 & "       T_SALES_TEMP.ITEM_CD                          AS HINBAN,"
    strSQL2 = strSQL2 & "       TO_CHAR(T_SALES_TEMP.SALES_DATE,'yyyy/mm/dd') AS SDATE,"
    strSQL2 = strSQL2 & "       SUM(T_SALES_TEMP.SALES_QTY)                   As USURYO"
    strSQL2 = strSQL2 & "  FROM T_SALES_TEMP"
    strSQL2 = strSQL2 & "  WHERE"
    strSQL2 = strSQL2 & "      T_SALES_TEMP.CUST_CD = '" & TKCODE & "'"
    strSQL2 = strSQL2 & "  AND T_SALES_TEMP.ITEM_CD = '" & HINBAN & "'"
    strSQL2 = strSQL2 & "  AND TO_CHAR(T_SALES_TEMP.SALES_DATE,'yyyy/mm/dd') LIKE '" & KANRYM & "%'"
    strSQL2 = strSQL2 & "  AND T_SALES_TEMP.DEL_FLG != '1'"
    strSQL2 = strSQL2 & "  AND T_SALES_TEMP.ONEROUS_CONS_SALES_TYP != '1'"
    strSQL2 = strSQL2 & "  Group BY"
    strSQL2 = strSQL2 & "      T_SALES_TEMP.CUST_CD,"
    strSQL2 = strSQL2 & "      T_SALES_TEMP.ITEM_CD,"
    strSQL2 = strSQL2 & "      TO_CHAR(T_SALES_TEMP.SALES_DATE,'yyyy/mm/dd')"
    
    
    'Worksheets("DATA").Range("f2").Value = strSQL2
    
    oraRs2.Open strSQL2, oraCon
    
    Do Until oraRs2.EOF
        DIX = Val(Mid(oraRs2!SDATE, 9, 2)) + 6
        With Worksheets("DATA").Cells(IX, DIX)
            .NumberFormat = "#,###"
            .Value = Val(oraRs2!USURYO)
        End With
        
        '集計行用
        DIX = DIX - 6
        total_arry5(DIX) = total_arry5(DIX) + Val(oraRs2!USURYO)
        
        oraRs2.MoveNext
    Loop
    
    oraRs2.Close
    Set oraRs2 = Nothing

End Sub

'//////////////////////////////
'// 出荷品番のトータル行（数量）出力
'//////////////////////////////
Sub TOTAL_PUT(ByVal IX As Integer)
    
    Dim DIX As Integer
    
    For DIX = 0 To 30
        
        If total_arry1(DIX) > 0 Then
            With Worksheets("DATA").Cells(IX, DIX + 6)
                .NumberFormat = "#,###"
                .Value = total_arry1(DIX)
            End With
        End If

        If total_arry2(DIX) > 0 Then
            With Worksheets("DATA").Cells(IX + 1, DIX + 6)
                .NumberFormat = "#,###"
                .Value = total_arry2(DIX)
            End With
        End If
        
        If total_arry3(DIX) > 0 Then
            With Worksheets("DATA").Cells(IX + 2, DIX + 6)
                .NumberFormat = "#,###"
                .Value = total_arry3(DIX)
            End With
        End If
        
        If total_arry4(DIX) > 0 Then
            With Worksheets("DATA").Cells(IX + 3, DIX + 6)
                .NumberFormat = "#,###"
                .Value = total_arry4(DIX)
            End With
        End If
        
        If total_arry5(DIX) > 0 Then
            With Worksheets("DATA").Cells(IX + 4, DIX + 6)
                .NumberFormat = "#,###"
                .Value = total_arry5(DIX)
            End With
        End If
    
    Next DIX
    
End Sub


'//////////////////////////////
'// 内示発注の取得
'//////////////////////////////

Sub NAIJI_GET2(ByVal IX As Integer, ByVal SICODE As String, ByVal HINBAN As String, ByVal KANRYM As String)

    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    Dim DIX As Integer
    Dim CIX As Integer
    
    Dim NEN As Integer
    Dim TSUKI As Integer
    Dim SURYO As Long
    
    NEN = Val(Mid(KANRYM, 1, 4))
    TSUKI = Val(Mid(KANRYM, 6, 2))
    
    
    '内示発注情報取得ＳＱＬ生成（バックアップより）
    strSQL2 = "SELECT "
    strSQL2 = strSQL2 & "MNGMNT_YEAR,"
    strSQL2 = strSQL2 & "MNGMNT_MONTH,"
    strSQL2 = strSQL2 & "VENDOR_CD AS SICODE,"
    strSQL2 = strSQL2 & "ARRIVAL_ITEM_CD,"
    strSQL2 = strSQL2 & "DAY_01,QTY_01,"
    strSQL2 = strSQL2 & "DAY_02,QTY_02,"
    strSQL2 = strSQL2 & "DAY_03,QTY_03,"
    strSQL2 = strSQL2 & "DAY_04,QTY_04,"
    strSQL2 = strSQL2 & "DAY_05,QTY_05,"
    strSQL2 = strSQL2 & "DAY_06,QTY_06,"
    strSQL2 = strSQL2 & "DAY_07,QTY_07,"
    strSQL2 = strSQL2 & "DAY_08,QTY_08,"
    strSQL2 = strSQL2 & "DAY_09,QTY_09,"
    strSQL2 = strSQL2 & "DAY_10,QTY_10,"
    strSQL2 = strSQL2 & "DAY_11,QTY_11,"
    strSQL2 = strSQL2 & "DAY_12,QTY_12,"
    strSQL2 = strSQL2 & "DAY_13,QTY_13,"
    strSQL2 = strSQL2 & "DAY_14,QTY_14,"
    strSQL2 = strSQL2 & "DAY_15,QTY_15,"
    strSQL2 = strSQL2 & "DAY_16,QTY_16,"
    strSQL2 = strSQL2 & "DAY_17,QTY_17,"
    strSQL2 = strSQL2 & "DAY_18,QTY_18,"
    strSQL2 = strSQL2 & "DAY_19,QTY_19,"
    strSQL2 = strSQL2 & "DAY_20,QTY_20,"
    strSQL2 = strSQL2 & "DAY_21,QTY_21,"
    strSQL2 = strSQL2 & "DAY_22,QTY_22,"
    strSQL2 = strSQL2 & "DAY_23,QTY_23,"
    strSQL2 = strSQL2 & "DAY_24,QTY_24,"
    strSQL2 = strSQL2 & "DAY_25,QTY_25,"
    strSQL2 = strSQL2 & "DAY_26 , QTY_26 "
    strSQL2 = strSQL2 & "FROM "
    strSQL2 = strSQL2 & "T_U_MONTHLY_ODR_WORK "
    strSQL2 = strSQL2 & "WHERE "
    strSQL2 = strSQL2 & "MNGMNT_YEAR = '" & CStr(NEN) & "'"
    strSQL2 = strSQL2 & " AND MNGMNT_MONTH = '" & CStr(TSUKI) & "'"
    strSQL2 = strSQL2 & " AND VENDOR_CD = '" & SICODE & "'"
    strSQL2 = strSQL2 & " AND ARRIVAL_ITEM_CD = '" & HINBAN & "'"
    oraRs2.Open strSQL2, oraCon
    
    Do Until oraRs2.EOF
    
        For CIX = 1 To 26
            
            If IsNull(oraRs2!DAY_01) Then
            
                Exit For
            
            End If
            
            
            Select Case CIX
                Case 1
                    DIX = VALDAY(oraRs2!DAY_01)
                    SURYO = Val(oraRs2!QTY_01)
                Case 2
                    DIX = VALDAY(oraRs2!DAY_02)
                    SURYO = Val(oraRs2!QTY_02)
                Case 3
                    DIX = VALDAY(oraRs2!DAY_03)
                    SURYO = Val(oraRs2!QTY_03)
                Case 4
                    DIX = VALDAY(oraRs2!DAY_04)
                    SURYO = Val(oraRs2!QTY_04)
                Case 5
                    DIX = VALDAY(oraRs2!DAY_05)
                    SURYO = Val(oraRs2!QTY_05)
                Case 6
                    DIX = VALDAY(oraRs2!DAY_06)
                    SURYO = Val(oraRs2!QTY_06)
                Case 7
                    DIX = VALDAY(oraRs2!DAY_07)
                    SURYO = Val(oraRs2!QTY_07)
                Case 8
                    DIX = VALDAY(oraRs2!DAY_08)
                    SURYO = Val(oraRs2!QTY_08)
                Case 9
                    DIX = VALDAY(oraRs2!DAY_09)
                    SURYO = Val(oraRs2!QTY_09)
                Case 10
                    DIX = VALDAY(oraRs2!DAY_10)
                    SURYO = Val(oraRs2!QTY_10)
                Case 11
                    DIX = VALDAY(oraRs2!DAY_11)
                    SURYO = Val(oraRs2!QTY_11)
                Case 12
                    DIX = VALDAY(oraRs2!DAY_12)
                    SURYO = Val(oraRs2!QTY_12)
                Case 13
                    DIX = VALDAY(oraRs2!DAY_13)
                    SURYO = Val(oraRs2!QTY_13)
                Case 14
                    DIX = VALDAY(oraRs2!DAY_14)
                    SURYO = Val(oraRs2!QTY_14)
                Case 15
                    DIX = VALDAY(oraRs2!DAY_15)
                    SURYO = Val(oraRs2!QTY_15)
                Case 16
                    DIX = VALDAY(oraRs2!DAY_16)
                    SURYO = Val(oraRs2!QTY_16)
                Case 17
                    If IsNull(oraRs2!DAY_17) Then
                        SURYO = 0
                    Else
                        DIX = VALDAY(oraRs2!DAY_17)
                        SURYO = Val(oraRs2!QTY_17)
                    End If
                Case 18
                    If IsNull(oraRs2!DAY_18) Then
                        SURYO = 0
                    Else
                        DIX = VALDAY(oraRs2!DAY_18)
                        SURYO = Val(oraRs2!QTY_18)
                    End If
                Case 19
                    If IsNull(oraRs2!DAY_19) Then
                        SURYO = 0
                    Else
                        DIX = VALDAY(oraRs2!DAY_19)
                        SURYO = Val(oraRs2!QTY_19)
                    End If
                Case 20
                    If IsNull(oraRs2!DAY_20) Then
                        SURYO = 0
                    Else
                        DIX = VALDAY(oraRs2!DAY_20)
                        SURYO = Val(oraRs2!QTY_20)
                    End If
                Case 21
                    If IsNull(oraRs2!DAY_21) Then
                        SURYO = 0
                    Else
                        DIX = VALDAY(oraRs2!DAY_21)
                        SURYO = Val(oraRs2!QTY_21)
                    End If
                Case 22
                    If IsNull(oraRs2!DAY_22) Then
                        SURYO = 0
                    Else
                        DIX = VALDAY(oraRs2!DAY_22)
                        SURYO = Val(oraRs2!QTY_22)
                    End If
                Case 23
                    If IsNull(oraRs2!DAY_23) Then
                        SURYO = 0
                    Else
                        DIX = VALDAY(oraRs2!DAY_23)
                        SURYO = Val(oraRs2!QTY_23)
                    End If
                Case 24
                    If IsNull(oraRs2!DAY_24) Then
                        SURYO = 0
                    Else
                        DIX = VALDAY(oraRs2!DAY_24)
                        SURYO = Val(oraRs2!QTY_24)
                    End If
                Case 25
                    If IsNull(oraRs2!DAY_25) Then
                        SURYO = 0
                    Else
                        DIX = VALDAY(oraRs2!DAY_25)
                        SURYO = Val(oraRs2!QTY_25)
                    End If
                Case 26
                    If IsNull(oraRs2!DAY_26) Then
                        SURYO = 0
                    Else
                        DIX = VALDAY(oraRs2!DAY_26)
                        SURYO = Val(oraRs2!QTY_26)
                    End If
            End Select
            
            If DIX <> 0 Then
                DIX = DIX + 6
                With Worksheets("DATA").Cells(IX, DIX)
                        .NumberFormat = "#,###"
                        .Value = SURYO
                End With
            End If
            
        Next
        
        oraRs2.MoveNext
    Loop
    
    oraRs2.Close
    Set oraRs2 = Nothing

End Sub

'//////////////////////////////
'// 全角の日にちから数字の日にちにする
'// 戻り値 日にち又は0:日にちでない
'//////////////////////////////

Function VALDAY(ByVal DAY As String) As Integer
    
    Dim DAY2 As Variant
    Dim DAY_LENG As Integer
    
    DAY = Replace(DAY, "　", "")    '日付から全角スペースを取り除く
    DAY = Replace(DAY, "日", "")    '日付から"日"を取り除く
    
    DAY2 = StrConv(DAY, vbNarrow)   '全角文字を半角にする
    
    If IsNumeric(DAY2) = True Then
        VALDAY = Val(StrConv(DAY, vbNarrow))
    Else
        VALDAY = 0
    End If
    
End Function

'//////////////////////////////
'// 発注計画の取得（発注残テーブルより）
'//////////////////////////////

Sub HACDAT_GET1(ByVal IX As Integer, ByVal SICODE As String, ByVal HINBAN As String, ByVal KANRYM As String)

    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    Dim DIX As Integer
    
    '確定発注情報取得ＳＱＬ生成
    strSQL2 = "SELECT "
    strSQL2 = strSQL2 & "T_RLSD_PUCH_ODR.VEND_CD AS SICODE,"
    strSQL2 = strSQL2 & "T_RLSD_PUCH_ODR.ITEM_CD AS HINBAN,"
    strSQL2 = strSQL2 & "TO_CHAR(T_RLSD_PUCH_ODR.PUCH_ODR_DLV_DATE,'yyyy/mm/dd') AS HDATE,"
    strSQL2 = strSQL2 & "SUM(T_RLSD_PUCH_ODR.PUCH_ODR_QTY) AS HSURYO,"
    strSQL2 = strSQL2 & "T_RLSD_PUCH_ODR.PUCH_ODR_STS_TYP AS JYOTAI "
    strSQL2 = strSQL2 & "FROM "
    strSQL2 = strSQL2 & "T_RLSD_PUCH_ODR "
    strSQL2 = strSQL2 & "WHERE "
    strSQL2 = strSQL2 & "T_RLSD_PUCH_ODR.VEND_CD = '" & SICODE & "'"
    strSQL2 = strSQL2 & " AND T_RLSD_PUCH_ODR.ITEM_CD = '" & HINBAN & "'"
    strSQL2 = strSQL2 & " AND TO_CHAR(T_RLSD_PUCH_ODR.PUCH_ODR_DLV_DATE,'yyyy/mm/dd') LIKE '" & KANRYM & "%' "
    strSQL2 = strSQL2 & "GROUP BY "
    strSQL2 = strSQL2 & "T_RLSD_PUCH_ODR.VEND_CD,"
    strSQL2 = strSQL2 & "T_RLSD_PUCH_ODR.ITEM_CD,"
    strSQL2 = strSQL2 & "TO_CHAR(T_RLSD_PUCH_ODR.PUCH_ODR_DLV_DATE,'yyyy/mm/dd'),"
    strSQL2 = strSQL2 & "T_RLSD_PUCH_ODR.PUCH_ODR_STS_TYP"
    
    oraRs2.Open strSQL2, oraCon
    
    Do Until oraRs2.EOF
        DIX = Val(Mid(oraRs2!HDATE, 9, 2)) + 6
        With Worksheets("DATA").Cells(IX, DIX)
            .NumberFormat = "#,###"
            .Value = Val(oraRs2!HSURYO)
        End With
        oraRs2.MoveNext
    Loop
        
    'レコードセットＣＬＯＳＥ
    oraRs2.Close
    Set oraRs2 = Nothing

End Sub


'//////////////////////////////
'// 所要量の取得（所要量テーブルより）
'//////////////////////////////

Sub SYOYOU_GET(ByVal IX As Integer, ByVal SICODE As String, ByVal HINBAN As String, ByVal KANRYM As String)

    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    Dim DIX As Integer
    
    '// 所要量情報取得ＳＱＬ生成（所要量テーブル）※有効な分だけ（取消した発注は除く）
    strSQL2 = "SELECT "
    strSQL2 = strSQL2 & "        T_OD.ITEM_CD                            AS NYUHIN,"
    strSQL2 = strSQL2 & "        T_OD.OD_TYP                             AS KUBUN,"
    strSQL2 = strSQL2 & "        TO_CHAR(T_OD.PRD_DUE_DATE,'yyyy/mm/dd') AS KDATE,"
    strSQL2 = strSQL2 & "        SUM(T_OD.DM_QTY)                        AS DEM,"
    strSQL2 = strSQL2 & "        SUM(T_OD.ODR_QTY)                       As ODR"
    strSQL2 = strSQL2 & " FROM"
    strSQL2 = strSQL2 & "        T_OD LEFT OUTER JOIN T_RLSD_PUCH_ODR"
    strSQL2 = strSQL2 & "        ON T_OD.OD_NO = T_RLSD_PUCH_ODR.OD_NO"
    strSQL2 = strSQL2 & " WHERE"
    strSQL2 = strSQL2 & "        T_OD.ITEM_CD = '" & HINBAN & "'"
    strSQL2 = strSQL2 & "    AND TO_CHAR(T_OD.PRD_DUE_DATE,'yyyy/mm/dd') LIKE '" & KANRYM & "%'"
    strSQL2 = strSQL2 & "    AND T_OD.OD_TYP = '2'"
    strSQL2 = strSQL2 & "    AND ( T_RLSD_PUCH_ODR.ODR_CANCEL_SLIP_ISS_FLG IN ('0')"
    strSQL2 = strSQL2 & "          OR T_RLSD_PUCH_ODR.ODR_CANCEL_SLIP_ISS_FLG IS NULL )"
    strSQL2 = strSQL2 & " Group BY"
    strSQL2 = strSQL2 & "        T_OD.ITEM_CD,"
    strSQL2 = strSQL2 & "        T_OD.OD_TYP,"
    strSQL2 = strSQL2 & "        TO_CHAR(T_OD.PRD_DUE_DATE,'yyyy/mm/dd')"
      
    oraRs2.Open strSQL2, oraCon
    
    Do Until oraRs2.EOF
        DIX = Val(Mid(oraRs2!KDATE, 9, 2)) + 6
        With Worksheets("DATA").Cells(IX, DIX)
            .NumberFormat = "#,###"
            .Value = Val(oraRs2!ODR)
        End With
        oraRs2.MoveNext
    Loop
        
    'レコードセットＣＬＯＳＥ
    oraRs2.Close
    Set oraRs2 = Nothing

End Sub

'//////////////////////////////
'// 確定発注（発注残）の取得
'//////////////////////////////

Sub CHUZAN_GET(ByVal IX As Integer, ByVal SICODE As String, ByVal HINBAN As String, ByVal KANRYM As String)

    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    Dim DIX As Integer
    
    '確定の発注残取得ＳＱＬ生成
    strSQL2 = "SELECT "
    strSQL2 = strSQL2 & "            T_RLSD_PUCH_ODR.PUCH_ODR_CD                             AS HCNO,"
    strSQL2 = strSQL2 & "            T_RLSD_PUCH_ODR.VEND_CD                                 AS SICODE,"
    strSQL2 = strSQL2 & "            T_RLSD_PUCH_ODR.ITEM_CD                                 AS HINBAN,"
    strSQL2 = strSQL2 & "            MAX(T_RLSD_PUCH_ODR.PUCH_ODR_QTY)                       AS HCSURYO,"
    strSQL2 = strSQL2 & "            NVL(SUM(T_PAST_INSPC_ACPT.ACPT_QTY),0)                  AS NYSURYO,"
    strSQL2 = strSQL2 & "            MAX(T_RLSD_PUCH_ODR.PUCH_ODR_QTY) - NVL(SUM(T_PAST_INSPC_ACPT.ACPT_QTY),0) AS ZANSU"
    strSQL2 = strSQL2 & "       FROM"
    strSQL2 = strSQL2 & "            T_RLSD_PUCH_ODR"
    strSQL2 = strSQL2 & "            LEFT OUTER JOIN T_PAST_INSPC_ACPT"
    strSQL2 = strSQL2 & "            ON T_RLSD_PUCH_ODR.PUCH_ODR_CD = T_PAST_INSPC_ACPT.PUCH_ODR_CD"
    strSQL2 = strSQL2 & "       WHERE"
    strSQL2 = strSQL2 & "             TO_CHAR(T_RLSD_PUCH_ODR.PUCH_ODR_DLV_DATE,'yyyy/mm/dd') < '" & KANRYM & "'"
    strSQL2 = strSQL2 & "         AND T_RLSD_PUCH_ODR.VEND_CD = '" & SICODE & "'"
    strSQL2 = strSQL2 & "         AND T_RLSD_PUCH_ODR.ITEM_CD = '" & HINBAN & "'"
    strSQL2 = strSQL2 & "         AND T_RLSD_PUCH_ODR.PUCH_ODR_STS_TYP = '2'"
    strSQL2 = strSQL2 & "         AND T_RLSD_PUCH_ODR.ODR_CANCEL_SLIP_ISS_FLG = '0'"
    strSQL2 = strSQL2 & "       Group BY"
    strSQL2 = strSQL2 & "             T_RLSD_PUCH_ODR.PUCH_ODR_CD,"
    strSQL2 = strSQL2 & "             T_RLSD_PUCH_ODR.VEND_CD,"
    strSQL2 = strSQL2 & "             T_RLSD_PUCH_ODR.ITEM_CD"
    
    oraRs2.Open strSQL2, oraCon
    
    Dim CALC_ZANSU As Long
    Do Until oraRs2.EOF
        CALC_ZANSU = CALC_ZANSU + Val(oraRs2!ZANSU)
        oraRs2.MoveNext
    Loop
    
    With Worksheets("DATA").Cells(IX, 6)
        .NumberFormat = "#,###"
        .Value = CALC_ZANSU
    End With
    
    'レコードセットＣＬＯＳＥ
    oraRs2.Close
    Set oraRs2 = Nothing

End Sub

'//////////////////////////////
'// 確定発注の取得
'//////////////////////////////

Sub KAKUTEI_GET2(ByVal IX As Integer, ByVal SICODE As String, ByVal HINBAN As String, ByVal KANRYM As String)

    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    Dim DIX As Integer
    
    '確定発注情報取得ＳＱＬ生成
    strSQL2 = "SELECT "
    strSQL2 = strSQL2 & "T_RLSD_PUCH_ODR.VEND_CD AS SICODE,"
    strSQL2 = strSQL2 & "T_RLSD_PUCH_ODR.ITEM_CD AS HINBAN,"
    strSQL2 = strSQL2 & "TO_CHAR(T_RLSD_PUCH_ODR.PUCH_ODR_DLV_DATE,'yyyy/mm/dd') AS HDATE,"
    strSQL2 = strSQL2 & "SUM(T_RLSD_PUCH_ODR.PUCH_ODR_QTY) AS HSURYO "
    strSQL2 = strSQL2 & "FROM "
    strSQL2 = strSQL2 & "T_RLSD_PUCH_ODR "
    strSQL2 = strSQL2 & "WHERE "
    strSQL2 = strSQL2 & "T_RLSD_PUCH_ODR.VEND_CD = '" & SICODE & "'"
    strSQL2 = strSQL2 & " AND T_RLSD_PUCH_ODR.ITEM_CD = '" & HINBAN & "'"
    strSQL2 = strSQL2 & " AND TO_CHAR(T_RLSD_PUCH_ODR.PUCH_ODR_DLV_DATE,'yyyy/mm/dd') LIKE '" & KANRYM & "%'"
    strSQL2 = strSQL2 & " AND T_RLSD_PUCH_ODR.PUCH_ODR_STS_TYP != '1' "
    strSQL2 = strSQL2 & " AND T_RLSD_PUCH_ODR.ODR_CANCEL_SLIP_ISS_FLG = '0' "
    strSQL2 = strSQL2 & "GROUP BY "
    strSQL2 = strSQL2 & "T_RLSD_PUCH_ODR.VEND_CD,"
    strSQL2 = strSQL2 & "T_RLSD_PUCH_ODR.ITEM_CD,"
    strSQL2 = strSQL2 & "TO_CHAR(T_RLSD_PUCH_ODR.PUCH_ODR_DLV_DATE,'yyyy/mm/dd')"
    
    oraRs2.Open strSQL2, oraCon
    
    Do Until oraRs2.EOF
        DIX = Val(Mid(oraRs2!HDATE, 9, 2)) + 6
        With Worksheets("DATA").Cells(IX, DIX)
            .NumberFormat = "#,###"
            .Value = Val(oraRs2!HSURYO)
        End With
        oraRs2.MoveNext
    Loop
    
    'レコードセットＣＬＯＳＥ
    oraRs2.Close
    Set oraRs2 = Nothing

End Sub

'//////////////////////////////
'// 入荷実績の取得
'//////////////////////////////

Sub NYDATA_GET(ByVal IX As Integer, ByVal SICODE As String, ByVal HINBAN As String, ByVal KANRYM As String)

    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    Dim DIX As Integer
    
    '入荷実績情報取得ＳＱＬ生成
    strSQL2 = "SELECT "
    strSQL2 = strSQL2 & "T_PAST_INSPC_ACPT.VEND_CD AS SICODE,"
    strSQL2 = strSQL2 & "T_PAST_INSPC_ACPT.ITEM_CD AS HINBAN,"
    strSQL2 = strSQL2 & "TO_CHAR(T_PAST_INSPC_ACPT.ACPT_DATE,'yyyy/mm/dd') AS NYDATE,"
    strSQL2 = strSQL2 & "SUM(T_PAST_INSPC_ACPT.ACPT_QTY) AS USURYO,"
    strSQL2 = strSQL2 & "SUM(T_PAST_INSPC_ACPT.INSPC_ACPT_QTY) AS NSURYO "
    strSQL2 = strSQL2 & "FROM "
    strSQL2 = strSQL2 & "T_PAST_INSPC_ACPT "
    strSQL2 = strSQL2 & "WHERE "
    strSQL2 = strSQL2 & "T_PAST_INSPC_ACPT.VEND_CD = '" & SICODE & "'"
    strSQL2 = strSQL2 & " AND T_PAST_INSPC_ACPT.ITEM_CD = '" & HINBAN & "'"
    strSQL2 = strSQL2 & " AND TO_CHAR(T_PAST_INSPC_ACPT.ACPT_DATE,'yyyy/mm/dd') LIKE '" & KANRYM & "%' "
    strSQL2 = strSQL2 & "GROUP BY "
    strSQL2 = strSQL2 & "T_PAST_INSPC_ACPT.VEND_CD,"
    strSQL2 = strSQL2 & "T_PAST_INSPC_ACPT.ITEM_CD,"
    strSQL2 = strSQL2 & "TO_CHAR(T_PAST_INSPC_ACPT.ACPT_DATE,'yyyy/mm/dd') "
    strSQL2 = strSQL2 & "ORDER BY TO_CHAR(T_PAST_INSPC_ACPT.ACPT_DATE,'yyyy/mm/dd')"
    
    'Worksheets("DATA").Range("J3").Value = strSQL2    'ＳＱＬチェック用
    
    oraRs2.Open strSQL2, oraCon
    
    Do Until oraRs2.EOF
        DIX = Val(Mid(oraRs2!NYDATE, 9, 2)) + 6
        With Worksheets("DATA").Cells(IX, DIX)
                .NumberFormat = "#,###"
                .Value = Val(oraRs2!NSURYO)
        End With
        oraRs2.MoveNext
    Loop
    
    'レコードセットＣＬＯＳＥ
    oraRs2.Close
    Set oraRs2 = Nothing

End Sub


'//////////////////////////////
'// カレンダセット
'//////////////////////////////

Sub CALEN_SET(ByVal KANRYM As String)
    
    'カレンダ表示列の消去
    With Worksheets("DATA").Range("G8:AL8")
        .Interior.ColorIndex = 2
        .Value = ""
    End With
    
    Worksheets("DATA").Range(Cells(9, 6), Cells(9, 37)).Clear
    
    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    Dim DIX As Integer
    Dim HOLODAY As String
    
    'カレンダＳＱＬ生成
    strSQL2 = "SELECT "
    strSQL2 = strSQL2 & "CAL_NO,"
    strSQL2 = strSQL2 & "CAL_DATE,"
    strSQL2 = strSQL2 & "HOLIDAY_FLG,"
    strSQL2 = strSQL2 & "CAL_COMMENT "
    strSQL2 = strSQL2 & "FROM "
    strSQL2 = strSQL2 & "M_CAL "
    strSQL2 = strSQL2 & "WHERE "
    strSQL2 = strSQL2 & "M_CAL.CAL_DATE LIKE '" & KANRYM & "%' "
    strSQL2 = strSQL2 & "ORDER BY "
    strSQL2 = strSQL2 & "M_CAL.CAL_DATE ASC"
    
    oraRs2.Open strSQL2, oraCon
    
    If oraRs2.EOF = True Then
            
        MsgBox "カレンダが見つかりません"
    
    Else
        'カレンダ転送
        Do Until oraRs2.EOF
            DIX = Val(Mid(oraRs2!CAL_DATE, 9, 2))
            DIX = DIX + 6
            If oraRs2!HOLIDAY_FLG = "0" Then
                With Worksheets("DATA").Cells(8, DIX)
                    .Interior.ColorIndex = 36
                    .HorizontalAlignment = xlRight
                    .NumberFormat = "@"
                    .Value = Format(oraRs2!CAL_DATE, "mm/dd")
                End With
            Else
                With Worksheets("DATA").Cells(8, DIX)
                    .Interior.ColorIndex = 44
                    .HorizontalAlignment = xlRight
                    .NumberFormat = "@"
                    .Value = Format(oraRs2!CAL_DATE, "mm/dd")
                End With
            End If
            oraRs2.MoveNext
        Loop
    End If
    
    'レコードセットＣＬＯＳＥ
    oraRs2.Close
    Set oraRs2 = Nothing

End Sub

'//////////////////////////////
'// 出荷部分の書式セット
'//////////////////////////////

Sub SYUKA_LINE_SET()
    Worksheets("DATA").Range(Cells(IX1, 1), Cells(IX1, 37)).Borders(xlEdgeTop).LineStyle = xlContinuous
    
    With Worksheets("DATA").Cells(IX1, 1)
            .Interior.ColorIndex = 44
            .NumberFormat = "@"
            .Value = "得意先"
    End With
    With Worksheets("DATA").Cells(IX1 + 1, 1)
            .Interior.ColorIndex = 44
            .NumberFormat = "@"
            .Value = "得意先名"
    End With
    With Worksheets("DATA").Cells(IX1 + 2, 1)
            .Interior.ColorIndex = 44
            .NumberFormat = "@"
            .Value = "得意先品目"
    End With
    With Worksheets("DATA").Cells(IX1 + 3, 1)
            .Interior.ColorIndex = 44
            .NumberFormat = "@"
            .Value = ""
    End With
    With Worksheets("DATA").Cells(IX1 + 4, 1)
            .Interior.ColorIndex = 44
            .NumberFormat = "@"
            .Value = "手番／安全在"
    End With
    With Worksheets("DATA").Cells(IX1 + 5, 1)
            .Interior.ColorIndex = 44
            .NumberFormat = "@"
            .Value = ""
    End With
    
    With Worksheets("DATA").Cells(IX1, 4)
            .NumberFormat = "@"
            .Value = "内示受注"
    End With
    With Worksheets("DATA").Cells(IX1 + 1, 4)
            .NumberFormat = "@"
            .Value = "確定受注"
    End With
    With Worksheets("DATA").Cells(IX1 + 2, 4)
            .NumberFormat = "@"
            .Value = "統合受注"
    End With
    With Worksheets("DATA").Cells(IX1 + 3, 4)
            .NumberFormat = "@"
            .Value = "出荷実績"
    End With
    With Worksheets("DATA").Cells(IX1 + 4, 4)
            .NumberFormat = "@"
            .Value = "売上実績"
    End With
    With Worksheets("DATA").Cells(IX1 + 5, 4)
            .NumberFormat = "@"
            .Value = "本日在庫"
    End With
    
    '合計
    With Worksheets("DATA").Cells(IX1, 5)
            .NumberFormat = "#,###"
            .Formula = "=SUM(F" & CStr(IX1) & ":AK" & CStr(IX1) & ")"
    End With
    With Worksheets("DATA").Cells(IX1 + 1, 5)
            .NumberFormat = "#,###"
            .Formula = "=SUM(F" & CStr(IX1 + 1) & ":AK" & CStr(IX1 + 1) & ")"
    End With
    With Worksheets("DATA").Cells(IX1 + 2, 5)
            .NumberFormat = "#,###"
            .Formula = "=SUM(F" & CStr(IX1 + 2) & ":AK" & CStr(IX1 + 2) & ")"
    End With
    With Worksheets("DATA").Cells(IX1 + 3, 5)
            .NumberFormat = "#,###"
            .Formula = "=SUM(F" & CStr(IX1 + 3) & ":AK" & CStr(IX1 + 3) & ")"
    End With
    With Worksheets("DATA").Cells(IX1 + 4, 5)
            .NumberFormat = "#,###"
            .Formula = "=SUM(F" & CStr(IX1 + 4) & ":AK" & CStr(IX1 + 4) & ")"
    End With
        
    '手持ち在庫
    With Worksheets("DATA").Cells(IX1 + 5, 5)
            .NumberFormat = "#,###"
    End With
        
    'データ部フォントカラー
    Worksheets("DATA").Range("D" & IX1 & ":AK" & IX1).Font.ColorIndex = 18
    Worksheets("DATA").Range("D" & IX1 + 1 & ":AK" & IX1 + 1).Font.ColorIndex = 23
    Worksheets("DATA").Range("D" & IX1 + 2 & ":AK" & IX1 + 2).Font.ColorIndex = 3
    Worksheets("DATA").Range("D" & IX1 + 3 & ":AK" & IX1 + 3).Font.ColorIndex = 1
    Worksheets("DATA").Range("D" & IX1 + 4 & ":AK" & IX1 + 4).Font.ColorIndex = 13
    Worksheets("DATA").Range("D" & IX1 + 5).Font.ColorIndex = 26
    
    '下線を引く
    Worksheets("DATA").Range(Cells(IX1 + 5, 1), Cells(IX1 + 5, 37)).Borders(xlEdgeBottom).LineStyle = xlContinuous

End Sub


'//////////////////////////////
'// 出荷部分（集計行）の書式セット
'//////////////////////////////

Sub TOTAL_LINE_SET()
    Worksheets("DATA").Range(Cells(IX1, 1), Cells(IX1, 37)).Borders(xlEdgeTop).LineStyle = xlContinuous
    
    With Worksheets("DATA").Cells(IX1, 1)
            .Interior.ColorIndex = 40
            .NumberFormat = "@"
            .Value = "ＴＯＴＡＬ"
    End With
    With Worksheets("DATA").Cells(IX1 + 1, 1)
            .Interior.ColorIndex = 40
            .NumberFormat = "@"
            .Value = ""
    End With
    With Worksheets("DATA").Cells(IX1 + 2, 1)
            .Interior.ColorIndex = 40
            .NumberFormat = "@"
            .Value = ""
    End With
    With Worksheets("DATA").Cells(IX1 + 3, 1)
            .Interior.ColorIndex = 40
            .NumberFormat = "@"
            .Value = ""
    End With
    With Worksheets("DATA").Cells(IX1 + 4, 1)
            .Interior.ColorIndex = 40
            .NumberFormat = "@"
            .Value = ""
    End With
    
    With Worksheets("DATA").Cells(IX1, 4)
            .NumberFormat = "@"
            .Value = "内示受注 計"
    End With
    With Worksheets("DATA").Cells(IX1 + 1, 4)
            .NumberFormat = "@"
            .Value = "確定受注 計"
    End With
    With Worksheets("DATA").Cells(IX1 + 2, 4)
            .NumberFormat = "@"
            .Value = "統合受注 計"
    End With
    With Worksheets("DATA").Cells(IX1 + 3, 4)
            .NumberFormat = "@"
            .Value = "出荷実績 計"
    End With
    With Worksheets("DATA").Cells(IX1 + 4, 4)
            .NumberFormat = "@"
            .Value = "売上実績 計"
    End With
    
    '合計
    With Worksheets("DATA").Cells(IX1, 5)
            .NumberFormat = "#,###"
            .Formula = "=SUM(F" & CStr(IX1) & ":AK" & CStr(IX1) & ")"
    End With
    With Worksheets("DATA").Cells(IX1 + 1, 5)
            .NumberFormat = "#,###"
            .Formula = "=SUM(F" & CStr(IX1 + 1) & ":AK" & CStr(IX1 + 1) & ")"
    End With
    With Worksheets("DATA").Cells(IX1 + 2, 5)
            .NumberFormat = "#,###"
            .Formula = "=SUM(F" & CStr(IX1 + 2) & ":AK" & CStr(IX1 + 2) & ")"
    End With
    With Worksheets("DATA").Cells(IX1 + 3, 5)
            .NumberFormat = "#,###"
            .Formula = "=SUM(F" & CStr(IX1 + 3) & ":AK" & CStr(IX1 + 3) & ")"
    End With
    With Worksheets("DATA").Cells(IX1 + 4, 5)
            .NumberFormat = "#,###"
            .Formula = "=SUM(F" & CStr(IX1 + 4) & ":AK" & CStr(IX1 + 4) & ")"
    End With
        
    'データ部フォントカラー
    Worksheets("DATA").Range("D" & IX1 & ":AK" & IX1).Font.ColorIndex = 18
    Worksheets("DATA").Range("D" & IX1 + 1 & ":AK" & IX1 + 1).Font.ColorIndex = 23
    Worksheets("DATA").Range("D" & IX1 + 2 & ":AK" & IX1 + 2).Font.ColorIndex = 3
    Worksheets("DATA").Range("D" & IX1 + 3 & ":AK" & IX1 + 3).Font.ColorIndex = 1
    Worksheets("DATA").Range("D" & IX1 + 4 & ":AK" & IX1 + 4).Font.ColorIndex = 13
    
    '下線を引く
    Worksheets("DATA").Range(Cells(IX1 + 4, 1), Cells(IX1 + 4, 37)).Borders(xlEdgeBottom).LineStyle = xlContinuous

End Sub


'/////////////////////////////////////////////////
'// 工程ラインの書式セット
'/////////////////////////////////////////////////
Sub KOTEI_LINE_SET()

    '区切りに罫線を引く
    Worksheets("DATA").Range(Cells(IX1, 1), Cells(IX1, 37)).Borders(xlEdgeTop).LineStyle = xlContinuous
    
    With Worksheets("DATA").Cells(IX1, 1)
            .Interior.ColorIndex = 34
            .NumberFormat = "@"
            .Value = "仕入先"
    End With
    With Worksheets("DATA").Cells(IX1 + 1, 1)
            .Interior.ColorIndex = 34
            .NumberFormat = "@"
            .Value = "仕入先名"
    End With
    With Worksheets("DATA").Cells(IX1 + 2, 1)
            .Interior.ColorIndex = 34
            .NumberFormat = "@"
            .Value = "品目番号/階層"
    End With
    With Worksheets("DATA").Cells(IX1 + 3, 1)
            .Interior.ColorIndex = 34
            .NumberFormat = "@"
            .Value = "手配区分/保管区"
    End With
    With Worksheets("DATA").Cells(IX1 + 4, 1)
            .Interior.ColorIndex = 34
            .NumberFormat = "@"
            .Value = "最上位品番"
    End With
    With Worksheets("DATA").Cells(IX1 + 5, 1)
            .Interior.ColorIndex = 34
            .NumberFormat = "@"
            .Value = "手番／安全在庫"
    End With
    
    With Worksheets("DATA").Cells(IX1, 4)
            .NumberFormat = "@"
            .Value = "月初発注"
    End With
    With Worksheets("DATA").Cells(IX1 + 1, 4)
            .NumberFormat = "@"
            .Value = "所要量"
    End With
    With Worksheets("DATA").Cells(IX1 + 2, 4)
            .NumberFormat = "@"
            .Value = "確定発注"
    End With
    With Worksheets("DATA").Cells(IX1 + 3, 4)
            .NumberFormat = "@"
            .Value = "入荷実績"
    End With
    With Worksheets("DATA").Cells(IX1 + 4, 4)
            .NumberFormat = "@"
            .Value = "本日在庫"
    End With
    
    '合計
    With Worksheets("DATA").Cells(IX1, 5)
            .NumberFormat = "#,###"
            .Formula = "=SUM(F" & CStr(IX1) & ":AK" & CStr(IX1) & ")"
    End With
    With Worksheets("DATA").Cells(IX1 + 1, 5)
            .NumberFormat = "#,###"
            .Formula = "=SUM(F" & CStr(IX1 + 1) & ":AK" & CStr(IX1 + 1) & ")"
    End With
    With Worksheets("DATA").Cells(IX1 + 2, 5)
            .NumberFormat = "#,###"
            .Formula = "=SUM(F" & CStr(IX1 + 2) & ":AK" & CStr(IX1 + 2) & ")"
    End With
        
    With Worksheets("DATA").Cells(IX1 + 3, 5)
            .NumberFormat = "#,###"
            .Formula = "=SUM(F" & CStr(IX1 + 3) & ":AK" & CStr(IX1 + 3) & ")"
    End With
    
    '手持在庫
    With Worksheets("DATA").Cells(IX1 + 4, 5)
            .NumberFormat = "#,###"
    End With
        
    'データ部フォントカラー
    Worksheets("DATA").Range("D" & IX1 & ":AK" & IX1).Font.ColorIndex = 18
    Worksheets("DATA").Range("D" & IX1 + 1 & ":AK" & IX1 + 1).Font.ColorIndex = 50
    Worksheets("DATA").Range("D" & IX1 + 2 & ":AK" & IX1 + 2).Font.ColorIndex = 23
    Worksheets("DATA").Range("D" & IX1 + 3 & ":AK" & IX1 + 3).Font.ColorIndex = 1
    Worksheets("DATA").Range("D" & IX1 + 4).Font.ColorIndex = 26
    
    '区切りに罫線を引く
    Worksheets("DATA").Range(Cells(IX1 + 5, 1), Cells(IX1 + 5, 37)).Borders(xlEdgeBottom).LineStyle = xlContinuous

End Sub

'//////////////////////////////
'// 工程部分とデータ部分の消去
'//////////////////////////////

Sub CELL_CLR1()

    '最大行を取得
    IX1 = Worksheets("DATA").Range("AK3").Value
    
    If IX1 = 0 Then
       IX1 = 200         '不運にも消されてしまった時
    End If

    '消去（値と書式）
    Worksheets("DATA").Range(Cells(9, 1), Cells(IX1, 37)).Clear

End Sub

'//////////////////////////////
'// データ部分のみ消去
'//////////////////////////////

Sub CELL_CLR2()

    '最大行を取得
    IX1 = Worksheets("DATA").Range("AK3").Value
    
    If IX1 = 0 Then
       IX1 = 200         '不運にも消されてしまった時
    End If

    '消去（値のみ）
    Worksheets("DATA").Range(Cells(9, 6), Cells(IX1, 37)).ClearContents

End Sub

'// ============================================
'//
'// 保管区別品目在庫の数量
'//
'// ============================================
Public Function funZaikoGET(ByVal HINBAN As String) As Long
    
    funZaikoGET = 0
    
    Dim oraRs2 As New ADODB.Recordset
    Dim strSQL2 As String
    
    '// 保管区別品目在庫の取得
    strSQL2 = "SELECT "
    strSQL2 = strSQL2 & "       T_ITEM_STOCK.ITEM_CD            AS HINMOK,"
    strSQL2 = strSQL2 & "       T_ITEM_STOCK.WH_CD              AS HOKANKU,"
    strSQL2 = strSQL2 & "       T_ITEM_STOCK.STOCK_ON_HAND_QTY  AS ZAIKO"
    strSQL2 = strSQL2 & "  FROM"
    strSQL2 = strSQL2 & "       T_ITEM_STOCK"
    strSQL2 = strSQL2 & "  WHERE"
    strSQL2 = strSQL2 & "       ITEM_CD = '" & HINBAN & "'"
    
    oraRs2.Open strSQL2, oraCon
    
    Do Until oraRs2.EOF
        funZaikoGET = funZaikoGET + Val(oraRs2!ZAIKO)
        oraRs2.MoveNext
    Loop
    
    'レコードセットＣＬＯＳＥ
    oraRs2.Close
    Set oraRs2 = Nothing
    
End Function
