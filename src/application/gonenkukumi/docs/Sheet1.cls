VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "Sheet1"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Option Explicit

Private Sub CommandButton1_Click()

    '品番情報を表示する
    Call MAST_DISP
    
End Sub

Private Sub CommandButton2_Click()

    '実績データを表示する
    Call DATA_DISP

End Sub

Private Sub Worksheet_Activate()
    Worksheets("DATA").Range("B5").Value = "*"
End Sub


