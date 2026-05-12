package com.soma2026.tikitalka.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.runtime.Composable
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import org.jetbrains.compose.resources.Font
import tikitalka.composeapp.generated.resources.Res
import tikitalka.composeapp.generated.resources.pretendard_bold
import tikitalka.composeapp.generated.resources.pretendard_extrabold
import tikitalka.composeapp.generated.resources.pretendard_light
import tikitalka.composeapp.generated.resources.pretendard_medium
import tikitalka.composeapp.generated.resources.pretendard_regular
import tikitalka.composeapp.generated.resources.pretendard_semibold
import tikitalka.composeapp.generated.resources.pretendard_thin

@Composable
internal fun rememberTikiTalkaTypography(): Typography {
    val pretendard = FontFamily(
        Font(Res.font.pretendard_thin,      FontWeight.Thin),
        Font(Res.font.pretendard_light,     FontWeight.Light),
        Font(Res.font.pretendard_regular,   FontWeight.Normal),
        Font(Res.font.pretendard_medium,    FontWeight.Medium),
        Font(Res.font.pretendard_semibold,  FontWeight.SemiBold),
        Font(Res.font.pretendard_bold,      FontWeight.Bold),
        Font(Res.font.pretendard_extrabold, FontWeight.ExtraBold),
    )

    fun tt(
        size: Int,
        line: Int,
        weight: FontWeight = FontWeight.Normal,
        letter: Double = 0.0,
    ) = TextStyle(
        fontFamily    = pretendard,
        fontWeight    = weight,
        fontSize      = size.sp,
        lineHeight    = line.sp,
        letterSpacing = letter.sp,
    )

    return Typography(
        displayLarge  = tt(40, 48, FontWeight.Bold,     -0.5),
        displayMedium = tt(32, 40, FontWeight.Bold,     -0.4),
        displaySmall  = tt(28, 36, FontWeight.Bold,     -0.3),

        headlineLarge  = tt(26, 34, FontWeight.Bold,    -0.3),
        headlineMedium = tt(22, 30, FontWeight.Bold,    -0.2),
        headlineSmall  = tt(20, 28, FontWeight.SemiBold, -0.2),

        titleLarge  = tt(18, 26, FontWeight.SemiBold, -0.1),
        titleMedium = tt(16, 24, FontWeight.SemiBold),
        titleSmall  = tt(14, 20, FontWeight.SemiBold),

        bodyLarge  = tt(16, 24),
        bodyMedium = tt(14, 22),
        bodySmall  = tt(13, 20),

        labelLarge  = tt(14, 20, FontWeight.SemiBold),
        labelMedium = tt(12, 16, FontWeight.Medium, 0.2),
        labelSmall  = tt(11, 14, FontWeight.Medium, 0.3),
    )
}