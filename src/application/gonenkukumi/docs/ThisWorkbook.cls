VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "ThisWorkbook"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Option Explicit
'//////////////////////////////
'// ワークブックｏｐｅｎ
'//////////////////////////////

Private Sub Workbook_Open()
    
    'システム日付を「対象日付」に移送する。
    Worksheets("DATA").Range("E8").Value = Date
    
    '品目任意変換値に初期値「*」をセット
    Worksheets("DATA").Range("B5").Value = "*"
    
End Sub
