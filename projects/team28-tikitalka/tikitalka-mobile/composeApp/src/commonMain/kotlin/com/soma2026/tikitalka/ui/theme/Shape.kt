package com.soma2026.tikitalka.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.ui.unit.dp

val TikiTalkaShapes = Shapes(
    extraSmall = RoundedCornerShape(8.dp),   // 작은 칩, 토스트
    small      = RoundedCornerShape(12.dp),  // 인풋, 작은 버튼
    medium     = RoundedCornerShape(16.dp),  // 카드, 리스트 아이템
    large      = RoundedCornerShape(18.dp),  // 강조 카드
    extraLarge = RoundedCornerShape(22.dp),  // 시트, 큰 다이얼로그
)
